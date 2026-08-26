# dataglazer-nfl

NFL data clients, analysis notebooks, and an MCP server — all reading from
ESPN's unofficial API. No API key, no quota, no credentials of any kind.

## Layout

One installable package with three consumers sitting on top of one client layer:

```
                  clients/espn/   ← the only code that talks to ESPN
                   ╱     │     ╲
          mcp/server   plots.py   notebooks/
        (stdio, Claude) (CLI → figures) (import + explore)
```

```
src/dataglazer_nfl/
  clients/espn/     ESPN client: HTTP, disk cache, weekly rollups, games, injuries
  mcp/              MCP server — a thin facade whose docstrings are the tool schemas
  viz/              theme: dataglazer.mplstyle, palette tokens
  config.py         every path, anchored to the repo root
  plots.py          figure generators
notebooks/          numbered, import the package rather than using ../ paths
data/raw/           snapshots you deliberately keep (e.g. an MCP injury pull)
data/processed/     analysis-ready, regenerable from raw
data/external/      third-party data (superbowl-qbs.csv)
data/cache/         machine-managed ESPN HTTP cache — gitignored, safe to delete
reports/figures/    chart output
```

Two rules keep the seams clean:

1. **`clients/espn/` returns plain dicts — never DataFrames.** That is what keeps
   the MCP server a two-dependency install (`mcp`, `requests`). A test enforces it.
2. **The MCP server never touches `data/raw|processed|external`.** Its only disk
   footprint is `data/cache/`. Parking an MCP result in `data/raw/` is a manual,
   deliberate step — that's the handoff between the server and the pipeline.

## Setup

```bash
uv sync
```

Installs the package plus the `notebooks`, `ml` and `dev` groups. The MCP server
alone needs only the two core dependencies.

## The MCP server

```bash
uv run nfl-mcp
```

Eight tools over stdio — weekly rollups (efficiency, workhorse, big plays,
turnovers), single-game tools (scoring summary, drives), and league-wide
injuries joined onto the depth chart. See [docs/mcp-server.md](docs/mcp-server.md)
for the data-source quirks and caching rationale, and
[references/espn-api.md](references/espn-api.md) for the raw endpoints.

Register it with Claude Desktop:

```bash
claude mcp add nfl -- uv run --directory .../dataglazer-nfl nfl-mcp
```

## Common tasks

```bash
make lint          # ruff format --check + ruff check
make format        # autofix + format
make test          # offline tests only
make clean-cache   # drop the ESPN cache; it refetches on demand
```

```bash
uv run pytest -m network   # integration tests against live ESPN
uv run python -m dataglazer_nfl.plots   # regenerate the injury figure
```

## Notebooks

Notebooks import the package, so they run from any working directory:

```python
from dataglazer_nfl.config import EXTERNAL_DATA_DIR, FIGURES_DIR
from dataglazer_nfl.viz.style import apply_style
from dataglazer_nfl.clients import espn

apply_style()  # registers bundled Baloo 2, then the theme
rows = espn.get_efficiency_leaders(1, 2025)
```

Prefer `apply_style()` over `plt.style.use(...)`: it resolves the stylesheet
from the installed package, so a notebook runs the same from any directory.

Fonts come from the system. The stylesheet falls back
`Baloo 2 -> Poppins -> DejaVu Sans -> Arial`, and matplotlib substitutes
silently, so call `viz.style.is_font_active()` when an off-brand render would
matter.

## Provenance

Migrated from `dataglazer/mcp_server/` and `dataglazer-projects/nfl-injuries/`.
The ESPN client was split from a single 1064-line module; the split was verified
by diffing all eight tool outputs against the original — byte-identical.
