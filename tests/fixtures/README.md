Trimmed ESPN `/summary` payloads for the big-play geometry tests.

`data/cache/` is gitignored, so these live here instead to keep the tests
runnable on a fresh clone. Each file is a real payload cut down to the fields
the big-play board reads — header competitors, `boxscore.teams` (for
abbreviations and brand colours) and `drives.previous[].plays[]` — with every
play reduced to the keys the code touches.

- `401873290` — NO @ LAR, 2026 preseason week 3. A. Cook's 100-yard pick-six,
  where the play text states every yard line.
- `401873285` — SF @ LAC, same week. Jacob Cowing's 83-yard punt return, which
  ESPN collapses into a scoring-summary row with no yard lines at all, forcing
  the catch point to be back-solved.

Regenerate by re-trimming a fresh `get_game_summary(event_id)`.
