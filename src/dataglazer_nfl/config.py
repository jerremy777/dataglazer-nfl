"""Project-wide paths and season constants.

Every path is derived from the repo root rather than from the caller's working
directory, so a notebook, a script and the MCP server all resolve the same file
regardless of where they were launched from.
"""

from __future__ import annotations

import os
from pathlib import Path

# src/dataglazer_nfl/config.py -> src/dataglazer_nfl -> src -> <repo root>
PROJ_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

MODELS_DIR = PROJ_ROOT / "models"
REPORTS_DIR = PROJ_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
REFERENCES_DIR = PROJ_ROOT / "references"

# Matplotlib stylesheet for @dataglazer visuals. The fonts it names are
# expected to be installed on the system.
STYLE_FILE = Path(__file__).resolve().parent / "viz" / "dataglazer.mplstyle"


def _resolve_cache_dir() -> Path | None:
    """Where completed-game ESPN payloads are cached on disk.

    `NFL_CACHE_DIR` relocates it; setting it to an empty string disables disk
    caching entirely, which is why this can return None.
    """
    override = os.getenv("NFL_CACHE_DIR")
    if override is None:
        return DATA_DIR / "cache" / "espn"
    if not override.strip():
        return None
    return Path(override).expanduser()


CACHE_DIR = _resolve_cache_dir()

# Season the weekly tools assume when a caller does not name one. ESPN imposes
# no per-season limit, so this is only a default, overridable per call.
CURRENT_SEASON = 2026

# The season in a depth-chart URL is a formality — every year returns today's
# chart, see `clients.espn.teams.get_depth_chart` — so injury lookups pin one
# rather than threading a parameter through for a value that changes nothing.
# This differing from CURRENT_SEASON is therefore not a bug.
DEPTH_CHART_SEASON = 2025
