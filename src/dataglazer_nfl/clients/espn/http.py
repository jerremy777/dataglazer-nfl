"""HTTP transport for ESPN's two unofficial NFL hosts.

No API key is required and there is no published rate limit. The endpoints are
undocumented; field names were verified against live 2025 regular-season data.
"""

from __future__ import annotations

import threading
from typing import Any

import requests

SITE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
# Depth charts live on ESPN's *core* API — a different host with a different
# shape, which references players by URL rather than embedding them.
CORE = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"

# Season types as ESPN numbers them.
PRESEASON, REGULAR_SEASON, POSTSEASON = 1, 2, 3

_TIMEOUT = 30
_MAX_WORKERS = 8

_local = threading.local()


def _session() -> requests.Session:
    """One requests.Session per thread (Session is not thread-safe)."""
    sess = getattr(_local, "session", None)
    if sess is None:
        sess = _local.session = requests.Session()
    return sess


def _get(path: str, **params: Any) -> dict[str, Any]:
    resp = _session().get(f"{SITE}/{path}", params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _core_get(path: str, **params: Any) -> dict[str, Any]:
    resp = _session().get(f"{CORE}/{path}", params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()
