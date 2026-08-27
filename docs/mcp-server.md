# NFL MCP Server

A local [MCP](https://modelcontextprotocol.io) server exposing NFL stat tools,
all read from ESPN's unofficial site and core APIs
(`https://site.api.espn.com/.../football/nfl`) — no key, no quota. The weekly
rollups back the four recurring dataglazer series and the aggregation lives in
[`clients/espn/`](../src/dataglazer_nfl/clients/espn/).

## Weekly tools

These answer "what happened in week N", which ESPN exposes no endpoint for —
the rollups are computed locally. All take `(week, year, season_type)`, where
`year` is the season (2025 = the 2025-26 season) and `season_type` is
`1` preseason / `2` regular season / `3` postseason.

| Tool | Series | Returns |
| --- | --- | --- |
| `list_week_games(week, year, season_type)` | — | `{id, name, status, completed, date}` per game. |
| `get_week_efficiency_leaders(week, year, season_type, min_attempts, top_n)` | Efficiency Leaders | `{name, team, rating, comp, att, yards, td, int}` |
| `get_week_workhorse_leaders(week, year, season_type, min_carries, top_n)` | Workhorse Watch | `{name, team, carries, yards, td, long}` |
| `get_week_big_plays(week, year, season_type, top_n, min_yards, include_returns)` | Big Play Board | `{plays, derived_count}` — see [Big-play geometry](#big-play-geometry) |
| `get_week_turnover_tracker(week, year, season_type)` | Turnover Tracker | `{team, opponent, giveaways, takeaways, diff}` |

## Single-game tools

These take an `event_id` — the `id` from `list_week_games` — which already
encodes the season, week and matchup, so there are no `week`/`year` arguments.

| Tool | Returns |
| --- | --- |
| `get_game_scoring_summary(event_id, strict=True)` | `{event_id, name, completed, scoring_plays, team_totals, team_colors, final_score, reconciles, warnings}` |
| `get_game_drives(event_id)` | `{event_id, name, completed, drives, team_colors}` |

`scoring_plays` is chronological, one entry per scoring play:
`{team, quarter, clock, points, category, play_type, description}`, where
`category` is `offense` / `defense` / `special_teams`. `team_totals` rolls that
up per team as `{offense_points, defense_points, special_teams_points,
total_points}`.

Each drive is `{team, quarter_started, description, result, result_detail,
yards, plays, time_of_possession, is_score}`. `result` is ESPN's short code
(`TD`, `FG`, `PUNT`, `INT`, `DOWNS`, `END OF HALF`) and `result_detail` its
spelled-out form (`Touchdown`, `Downs`, …).

### How the offense/defense/special-teams split is computed

Two things about ESPN's payload dictate the approach, and both were verified
against live data:

- **Points come from the running score, not a per-play-type table.** ESPN folds
  the try into the touchdown play — `"…TOUCHDOWN. T.Loop extra point is GOOD"`
  is *one* play whose score snapshot jumps 7 — and emits no separate extra-point
  or two-point scoring plays. Scoring 6/3/1/2 by play type therefore
  under-counts every converted touchdown. Taking the delta of
  `awayScore`/`homeScore` across consecutive scoring plays also absorbs missed
  extra points (6) and two-point tries (8) for free.
- **The scoring team is whichever side's score moved, not the drive's team.** A
  pick-six or punt-return touchdown is recorded inside the drive of the team
  that *lost* the ball, so `drive.team` names the wrong side on exactly the
  non-offensive scores this tool exists to isolate.

Together these make the rollup reconcile by construction; it is checked against
the header's official final score, and `strict=True` (the default) raises on a
finished game that doesn't add up rather than returning wrong numbers. A game
still in progress is flagged in `warnings` instead of raising.

Classification keys off ESPN's `type.text`, with the play text disambiguating
the types that cover two units — a fumble recovered on a kickoff is typed
`Fumble Return Touchdown` but is a special-teams score. A try attached to a
defensive or special-teams touchdown counts in that category, since ESPN reports
it as one play. Unknown play types fall back to possession (points scored by the
team without the ball are never offensive) plus kicking-play wording.

Note that `is_score` on a drive is ESPN's own flag and means *the drive ended in
a score*, including one by the defense — the `INT TD` drive above belongs to the
team that threw the interception. Use `get_game_scoring_summary` for who scored.

### Caching of raw payloads

Every tool here funnels through `get_game_summary`, which caches the raw
summary JSON to disk — one gzipped file per event under `.espn_cache/`
(git-ignored). **Only finished games are stored**, since a completed game's
summary is immutable; anything live or scheduled is always refetched. That is
the same rule the in-memory week cache already applies.

This is a deliberate departure from HTTP caching: ESPN sends no `ETag` and no
`Last-Modified`, and marks the endpoint `Cache-Control: max-age=1` because it
also serves live games — so there is nothing to revalidate against, and a
cache library that honours those headers would be a no-op. Game state is the
only reliable cacheability signal.

Costs about **56 KB a game**, so a full season (~334 games including pre- and
postseason) is roughly **19 MB**. The full payload is stored rather than a
trimmed subset: dropping everything but `header`/`boxscore`/`drives` saves only
a third, and costs a refetch the first time you want a field that was trimmed.

| Helper | Purpose |
| --- | --- |
| `cache_stats()` | `{dir, games, bytes}` for the store. |
| `clear_disk_cache(event_id=None)` | Drop one game, or the whole store. Returns the number of files removed. |
| `clear_cache()` | Drop the in-process week cache only. |

Set `NFL_CACHE_DIR` to relocate the store, or to an empty string to disable
disk caching entirely. `get_game_summary(event_id, use_cache=False)` bypasses
it for a single call — worth doing if ESPN corrects a boxscore after the fact,
or use `clear_disk_cache(event_id)`.

If ESPN drifts a field name, clear the store (`clear_disk_cache()`) so stale
payloads aren't masking the change — though the stored copies are also the
easiest way to diff old shape against new.

Rate limiting is not a practical concern for single-game or single-week use —
the endpoint is unauthenticated, publishes no rate-limit headers, and shows no
throttling at the 8-way concurrency used here. A multi-season backfill is the
one pattern worth being polite about: lower `_MAX_WORKERS` for that run, and
note the cache makes it a one-time cost.

### Team colours

Both tools return `team_colors` as `{team: {primary, alternate}}`. ESPN stores
these bare (`"0085ca"`); they come back `'#'`-prefixed and upper-cased
(`"#0085CA"`), ready for matplotlib or CSS. Both keys are always present: when
`alternateColor` is missing, malformed, or identical to `color`, `alternate`
falls back to black or white by luma contrast, so chart scripts never have to
null-check. `get_game_drives` returns it once at the top level rather than on
every drive.

### How the weekly rollups work

ESPN has no "week N leaders" endpoint, so each series is aggregated locally:
pull the week's scoreboard for event IDs, pull each event's boxscore summary,
then roll up across games. Summaries are fetched in parallel (~1s for a full
week) and cached per `(week, year, season_type)` for the life of the process,
so building all four series costs one pull of ~16 requests.

Details worth knowing:

- **Completed games only.** A week still in progress yields partial numbers;
  call `list_week_games` first to check. Only fully-finished weeks are cached.
- **Passer rating** uses ESPN's own `RTG` where present, and falls back to
  computing the standard formula.
- **Workhorse Watch ranks by carries, then yards** — it's a usage board, so the
  leader is the most-fed back, not necessarily the most productive.
- **Big Play Board excludes kicks.** ESPN puts a field goal's kick distance and
  a kickoff's distance in the same `statYardage` field as a run or catch, so
  ranking raw yardage produces a board of FGs and kickoffs. The board is
  restricted to plays from scrimmage; `include_returns=True` adds
  interception/fumble/punt/kick returns, credited to the returning team.

## Big-play geometry

`get_week_big_plays` returns `{plays, derived_count}`. Each play keeps the
original `{event_id, yardage, text, team, type, touchdown, quarter}` and adds
labelling fields — `clock`, `game_name`, `opponent`, `player`, `unit`
(`offense` / `defense` / `special_teams`), `team_colors` — plus a `segments`
path that can be drawn straight onto a single 0-100 field.

**The frame is the team that put the ball in play** (`frame: "snapping_team"`).
They attack toward 100; 0 is the goal line they defend. On a kickoff the kicking
team takes that role, so kick and punt returns behave like every other return.

That convention is the point of the whole thing: direction encodes what
happened. Explosive offensive plays run left to right; interception, fumble,
punt and kick returns run right to left with a negative `net`. A pick-six draws
as a short forward stub hinged into a long backward sweep and is legible as a
pick-six before the reader has looked at a colour or a label. Normalizing to the
credited team instead would point every arrow rightward and throw that away.

The underlying rule is really "possession changed", not "the defense did it" — a
sack or a tackle for loss also points left. That is fine on a board with a
20-yard floor, but the direction annotation is only safe while it stays
explosives-only.

A segment is `{from, to, kind, by, origin_source}`, chronological. `kind` is one
of `pass`, `run`, `punt`, `kick`, `return`, `lateral`, `sack`. `by` is the team
that moved the ball on that leg, which is not always the snapping team — on a
pick-six the return leg belongs to the defense. A play from scrimmage has
exactly one segment; anything where the ball changed hands has two, so a
renderer can draw the pre-turnover legs thin and the return thick.

Punts and kickoffs include the kick itself as a segment rather than starting at
the catch. Drawing the ball downfield and then most of the way back is honest
but doubles the ink — emitting the leg leaves that as a rendering decision
rather than a data one.

**`origin_source` flags inference.** ESPN collapses some plays into a summary
row with no field position anywhere in the text (`"Jacob Cowing 83 Yd Punt
Return (Eddy Pineiro Kick)"`). The catch point is then back-solved from the
credited yardage and the scoring end zone, and that segment is marked
`"derived"` instead of `"play_text"`, so a chart can dash or footnote it. Never
draw an inference as a measurement. `derived_count` gives the total at a glance.

Three yardage numbers, deliberately separate:

| Key | Meaning |
| --- | --- |
| `yardage` | ESPN's credited stat. What the play is "worth", and what the board sorts on. |
| `path_yards` | Sum of `abs(to - from)` across segments. 135 on an 83-yard punt return, because the punt travelled 52. Stops a chart labelling an arrow "83" while drawing it 135 long. |
| `net` | Signed displacement, first segment's `from` to last segment's `to`. Negative on every return. Drives arrow direction. |

Worked example — Cowing's 83-yard punt return (`event_id` 401873285):

```json
{
  "yardage": 83, "path_yards": 135, "net": -31,
  "unit": "special_teams", "player": "Jacob Cowing",
  "segments": [
    {"from": 31, "to": 83, "kind": "punt",   "by": "LAC", "origin_source": "play_text"},
    {"from": 83, "to": 0,  "kind": "return", "by": "SF",  "origin_source": "derived"}
  ]
}
```

LAC snapped at their own 31 and punted 52 yards; Cowing caught it at the 83 and
ran it back into LAC's end zone.
- **Turnover differential** reads each team's takeaways off its opponent's
  giveaways in the same game, so a week's differentials sum to zero.

## Setup

No credentials to configure — every endpoint the server uses is unauthenticated.

```sh
uv sync
```

Run the server directly with:

```sh
uv run nfl-mcp
```

## Register with Claude Code

This repo ships the server only; register it yourself with either approach.

**CLI:**

```sh
claude mcp add nfl -- uv run --directory .../dataglazer-nfl nfl-mcp
```

**Or a project `.mcp.json`:**

```json
{
  "mcpServers": {
    "nfl": {
      "command": "uv",
      "args": ["run", "--directory", ".../dataglazer-nfl", "nfl-mcp"]
    }
  }
}
```

## Notes & limitations

- **Auth and quota:** neither. The endpoints are unauthenticated and publish no
  rate limits.
- **Team IDs are ESPN's own.** Kansas City is 12, and 1 is Atlanta. They match
  no other NFL data source, so resolve a name rather than reusing an ID from
  elsewhere.
- **Client-side filters:** ESPN offers no `status` or `position` filter on its
  roster payload, so `list_injuries` applies both after fetching.
- **Season:** defaults to `2025`; override via the `year` / `season` argument.
- **Undocumented endpoints.** They have drifted before; field names here were
  verified against live data. If a series comes back empty, dump one summary and
  check the labels (`"C/ATT"`, `"CAR"`, the `turnovers` team stat) and that
  plays are still under `drives.previous[].plays[]`.

## Smoke test (no MCP client needed)

```sh
uv run python -c "from dataglazer_nfl.clients import espn as e; \
s = e.get_week_summaries(3, 2025); \
print(e.get_efficiency_leaders(3, 2025, summaries=s)[:3]); \
print(e.get_workhorse_leaders(3, 2025, summaries=s)[:3]); \
print(e.get_big_play_board(3, 2025, summaries=s)); \
print(e.get_turnover_tracker(3, 2025, summaries=s)[:3])"
```

The single-game tools need only an event ID:

```sh
uv run python -c "from dataglazer_nfl.clients import espn as e; \
g = e.get_game_summary('401873285'); \
out = e.get_game_scoring_summary('401873285', game=g); \
print(out['team_totals']); print(out['team_colors']); print(out['reconciles']); \
print(e.get_game_drives('401873285', game=g)['drives'][:3])"
```
