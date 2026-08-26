"""Week scoreboards and per-game summary fetching."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Any

from .cache import _cache_path, _read_cached, _write_cached
from .http import _MAX_WORKERS, REGULAR_SEASON, _get


def get_week_events(
    week: int, year: int, season_type: int = REGULAR_SEASON
) -> list[dict[str, Any]]:
    """Scoreboard rows for a week: {id, name, status, completed, date}.

    NOTE: the scoreboard's season selector is `dates`, not `year`. Passing
    `year=` is silently ignored and you get the *current* season back.

    Raw payload (~135 KB), openable in a browser:
        https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week=1&dates=2025&seasontype=2

    Each `events[]` entry carries {competitions, date, id, links, name, season,
    shortName, status, uid, week}; `competitions[0]` is where scores, venue,
    odds and broadcast data live.
    """
    data = _get("scoreboard", week=week, dates=year, seasontype=season_type)
    events = []
    for event in data.get("events", []):
        status = (event.get("status") or {}).get("type") or {}
        events.append(
            {
                "id": event.get("id"),
                "name": event.get("shortName"),
                "status": status.get("name"),
                "completed": bool(status.get("completed")),
                "date": event.get("date"),
            }
        )
    return events


def get_week_event_ids(week: int, year: int, season_type: int = REGULAR_SEASON) -> list[str]:
    return [e["id"] for e in get_week_events(week, year, season_type)]


def is_completed(game: dict[str, Any]) -> bool:
    """True once a game is final (its summary payload stops changing)."""
    comp = (game.get("header", {}).get("competitions") or [{}])[0]
    status = (comp.get("status") or {}).get("type") or {}
    return bool(status.get("completed"))


def get_game_summary(event_id: str | int, use_cache: bool = True) -> dict[str, Any]:
    """Full boxscore + drives/play-by-play for one game.

    A finished game's summary is immutable, so it is cached to disk under
    `CACHE_DIR` indefinitely — there is nothing to revalidate against anyway, as
    ESPN sends no ETag or Last-Modified and marks the endpoint `max-age=1`
    because it also serves live games. Games in progress or not yet played are
    always refetched, which is the same rule `get_week_summaries` applies to its
    in-memory cache.

    Args:
        event_id: ESPN event ID.
        use_cache: Set False to bypass the disk cache for this call (the fresh
            response still replaces the stored copy once the game is final).

    Raw payload (~400 KB — the richest endpoint here), openable in a browser:
        https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=401772510

    This client reads `header`, `boxscore`, `drives` and `scoringPlays`. Also
    present and currently unused: againstTheSpread, article, broadcasts, format,
    gameInfo, injuries, leaders, meta, news, odds, pickcenter, standings,
    videos, winprobability — `winprobability` and `leaders` are the obvious
    candidates for new tools.
    """
    path = _cache_path(event_id)
    if use_cache and path is not None and path.exists():
        cached = _read_cached(path)
        if cached is not None:
            return cached

    game = _get("summary", event=event_id)
    if path is not None and is_completed(game):
        _write_cached(path, game)
    return game


_summary_cache: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
_cache_lock = threading.Lock()


def get_week_summaries(
    week: int,
    year: int,
    season_type: int = REGULAR_SEASON,
    completed_only: bool = True,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Fetch every game summary for a week (~16 requests, run in parallel).

    Cached per (week, year, season_type) for the life of the process, so the
    four series can be built from one pull. Pass `use_cache=False` to refetch
    a week that was still in progress when it was first pulled.
    """
    key = (week, year, season_type)
    if use_cache:
        with _cache_lock:
            hit = _summary_cache.get(key)
        if hit is not None:
            return hit

    all_events = get_week_events(week, year, season_type)
    events = [e for e in all_events if e["completed"]] if completed_only else all_events
    ids = [e["id"] for e in events]
    if not ids:
        return []

    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(ids))) as pool:
        summaries = list(pool.map(get_game_summary, ids))

    # Only cache a finished week; one still in progress will keep changing.
    if use_cache and all_events and all(e["completed"] for e in all_events):
        with _cache_lock:
            _summary_cache[key] = summaries
    return summaries


def clear_cache() -> None:
    """Drop the in-process week cache (does not touch the disk cache)."""
    with _cache_lock:
        _summary_cache.clear()
