"""ESPN NFL client.

Re-exports the full public surface so callers import from one place:

    from dataglazer_nfl.clients import espn
    espn.get_efficiency_leaders(1, 2025)

The modules below are an organisational split of a single former module; the
function names, signatures and return shapes are unchanged.
"""

from .cache import CACHE_DIR, cache_stats, clear_disk_cache
from .colors import get_team_colors
from .games import (
    CATEGORIES,
    classify_scoring_play,
    get_game_drives,
    get_game_scoring_summary,
)
from .http import CORE, POSTSEASON, PRESEASON, REGULAR_SEASON, SITE
from .injuries import get_league_injuries, get_team_injuries
from .schedule import (
    clear_cache,
    get_game_summary,
    get_week_event_ids,
    get_week_events,
    get_week_summaries,
    is_completed,
)
from .teams import get_depth_chart, get_team_roster, get_teams, resolve_team_id
from .weekly import (
    RETURN_PLAY_TYPES,
    SCRIMMAGE_PLAY_TYPES,
    get_big_play_board,
    get_efficiency_leaders,
    get_turnover_tracker,
    get_workhorse_leaders,
    nfl_passer_rating,
)

__all__ = [
    "CACHE_DIR",
    "CATEGORIES",
    "CORE",
    "POSTSEASON",
    "PRESEASON",
    "REGULAR_SEASON",
    "RETURN_PLAY_TYPES",
    "SCRIMMAGE_PLAY_TYPES",
    "SITE",
    "cache_stats",
    "classify_scoring_play",
    "clear_cache",
    "clear_disk_cache",
    "get_big_play_board",
    "get_depth_chart",
    "get_efficiency_leaders",
    "get_game_drives",
    "get_game_scoring_summary",
    "get_game_summary",
    "get_league_injuries",
    "get_team_colors",
    "get_team_injuries",
    "get_team_roster",
    "get_teams",
    "get_turnover_tracker",
    "get_week_event_ids",
    "get_week_events",
    "get_week_summaries",
    "get_workhorse_leaders",
    "is_completed",
    "nfl_passer_rating",
    "resolve_team_id",
]
