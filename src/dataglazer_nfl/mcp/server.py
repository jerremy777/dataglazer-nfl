"""Local MCP server exposing NFL stat tools, all read from ESPN.

No API key is required and there is no request quota. The endpoints are
undocumented, so field names were verified against live data rather than a spec.

Single-week rollups — these back the four recurring dataglazer series:
  - list_week_games            : the week's games and whether they are final
  - get_week_efficiency_leaders: passer rating, that week only
  - get_week_workhorse_leaders : carries + rushing yards, that week only
  - get_week_big_plays         : the week's longest plays
  - get_week_turnover_tracker  : team takeaway/giveaway differential

Single-game tools (take an `event_id` from list_week_games):
  - get_game_scoring_summary   : every scoring play, split offense/defense/ST
  - get_game_drives            : drive-by-drive log

Roster tools:
  - list_injuries              : injured players by team or league-wide, each
                                 with their depth-chart rank so a starter is
                                 distinguishable from a backup.

All real work happens in `dataglazer_nfl.clients.espn`; the modules under
`tools/` are a thin facade whose docstrings are the schemas the model sees.

Run as a stdio MCP server:  uv run nfl-mcp
"""

from .app import mcp

# Imported for their registration side effects — each module decorates `mcp`.
from .tools import games, injuries, weekly  # noqa: F401  (isort:skip)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
