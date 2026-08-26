"""On-disk cache of completed-game ESPN payloads.

Owned by the client layer, not the analysis pipeline: everything here is
machine-written and refetchable, which is why it lives under `data/cache/`
rather than `data/raw/`.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any
import uuid

from dataglazer_nfl.config import CACHE_DIR

# One gzipped JSON file per event, ~56 KB a game, so a full season
# (~334 games) is ~19 MB. Relocate with NFL_CACHE_DIR; set it empty to
# disable the disk cache entirely (CACHE_DIR is then None).


def _cache_path(event_id: str | int) -> Path | None:
    if CACHE_DIR is None:
        return None
    # Event IDs are numeric, but never let one escape the cache directory.
    name = str(event_id).strip()
    if not name.isdigit():
        return None
    return CACHE_DIR / f"{name}.json.gz"


def _read_cached(path: Path) -> dict[str, Any] | None:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, EOFError, ValueError):
        # A damaged entry should cost one refetch, not break every caller.
        return None


def _write_cached(path: Path, game: dict[str, Any]) -> None:
    """Write via a unique temp file + atomic rename.

    Summaries are fetched from a thread pool, so a partially written file must
    never be visible under its real name.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with gzip.open(tmp, "wt", encoding="utf-8") as fh:
                json.dump(game, fh, separators=(",", ":"))
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
    except OSError:
        pass  # an unwritable cache is a slow path, not a failure


def clear_disk_cache(event_id: str | int | None = None) -> int:
    """Delete cached summary payloads; returns how many files were removed.

    Pass an `event_id` to drop a single game — useful if ESPN corrects a
    boxscore after the fact — or omit it to clear the whole store, which is the
    thing to do when a field name drifts and stale payloads no longer parse.
    """
    if CACHE_DIR is None or not CACHE_DIR.exists():
        return 0
    if event_id is not None:
        path = _cache_path(event_id)
        if path is None or not path.exists():
            return 0
        path.unlink()
        return 1
    removed = 0
    for path in CACHE_DIR.glob("*.json.gz"):
        path.unlink()
        removed += 1
    return removed


def cache_stats() -> dict[str, Any]:
    """{dir, games, bytes} for the disk cache."""
    if CACHE_DIR is None:
        return {"dir": None, "games": 0, "bytes": 0}
    files = list(CACHE_DIR.glob("*.json.gz")) if CACHE_DIR.exists() else []
    return {
        "dir": str(CACHE_DIR),
        "games": len(files),
        "bytes": sum(f.stat().st_size for f in files),
    }
