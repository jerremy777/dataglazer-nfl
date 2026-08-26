"""Figures for the @dataglazer NFL injury posts."""

import collections
import json
from pathlib import Path

from loguru import logger
import matplotlib.pyplot as plt
import typer

from dataglazer_nfl.config import FIGURES_DIR, RAW_DATA_DIR
from dataglazer_nfl.viz.palette import (
    BG,
    CYAN,
    FOOTNOTE,
    GOLD,
    MUTED,
    ORANGE,
    RED,
    SPINE,
    SURFACE,
    TEXT,
    TICK_BRIGHT,
    TICK_SUB,
)
from dataglazer_nfl.viz.style import apply_style

app = typer.Typer()

DEFAULT_INPUT = RAW_DATA_DIR / "nfl_injuries_2026-08-24.json"

# Designations that describe availability rather than an injury
NON_INJURY = {"Undisclosed", "Suspension", "Personal", "Illness"}

STATUS_ORDER = ["Injured Reserve", "Out", "Doubtful", "Questionable"]
STATUS_COLOR = {
    "Injured Reserve": RED,
    "Out": ORANGE,
    "Doubtful": GOLD,
    "Questionable": CYAN,
}

# Knee sub-types shown as their own columns, indented under the combined bar
KNEE_SUBS = [
    ("__UNSPEC__", "· unspecified"),
    ("Knee - ACL", "· ACL"),
    ("Knee - MCL", "· MCL"),
    ("Knee - ACL + MCL", "· ACL+MCL"),
    ("Knee - PCL", "· PCL"),
    ("Knee - Meniscus", "· Meniscus"),
]


def base(injury_type: str | None) -> str:
    """Collapse "Knee - ACL" and friends down to "Knee"."""
    return (injury_type or "Undisclosed").split(" - ")[0].strip()


def load_records(input_path: Path = DEFAULT_INPUT) -> list[dict]:
    """Read the injury snapshot, dropping non-injury designations."""
    with open(input_path) as f:
        payload = json.load(f)
    records = [
        r
        for r in payload["records"]
        if base(r.get("injury_type")) not in NON_INJURY and r.get("status") in STATUS_COLOR
    ]
    logger.info(f"Loaded {len(records)} injury records from {input_path.name}")
    return records


def build_columns(records: list[dict], top_n: int = 14) -> list[tuple[str, callable, bool]]:
    """Column spec: (label, predicate, is_breakout)."""
    totals = collections.Counter(base(r["injury_type"]) for r in records)

    cols = [("Knee (combined)", lambda r: base(r["injury_type"]) == "Knee", False)]
    for raw, label in KNEE_SUBS:
        v = "Knee" if raw == "__UNSPEC__" else raw
        # default arg binds the loop variable at definition time
        cols.append((label, lambda r, q=v: r["injury_type"] == q, True))
    for t, _ in totals.most_common(top_n):
        if t != "Knee":
            cols.append((t, lambda r, v=t: base(r["injury_type"]) == v, False))
    return cols


def injury_status_stack(records: list[dict], top_n: int = 14):
    """Stacked bars of injury count by body part, split by availability status."""
    apply_style()
    plt.rcParams["savefig.bbox"] = "standard"

    cols = build_columns(records, top_n=top_n)
    labels = [c[0] for c in cols]
    is_sub = [c[2] for c in cols]
    counts = {
        s: [sum(1 for r in records if pred(r) and r["status"] == s) for _, pred, _ in cols]
        for s in STATUS_ORDER
    }

    fig, ax = plt.subplots(figsize=(13.5, 10.8))
    fig.subplots_adjust(left=0.075, right=0.975, top=0.845, bottom=0.255)

    fig.text(
        0.5,
        0.955,
        "Where NFL Camps Are Breaking Down",
        ha="center",
        va="top",
        fontsize=31,
        fontweight="bold",
        color=TEXT,
    )
    fig.text(
        0.5,
        0.910,
        "2026 preseason · active injury reports by body part and status",
        ha="center",
        va="top",
        fontsize=14.5,
        color=MUTED,
    )

    x = range(len(cols))
    bottom = [0] * len(cols)
    for status in STATUS_ORDER:
        vals = counts[status]
        ax.bar(
            x,
            vals,
            bottom=bottom,
            width=0.72,
            label=status,
            color=[STATUS_COLOR[status]] * len(cols),
            alpha=1.0,
            edgecolor=SURFACE,
            linewidth=1.1,
            zorder=3,
        )
        for i, v in enumerate(vals):
            if v >= 3:
                ax.text(
                    i,
                    bottom[i] + v / 2,
                    str(v),
                    ha="center",
                    va="center",
                    fontsize=10.5,
                    fontweight="bold",
                    color=SURFACE,
                    zorder=4,
                )
        bottom = [b + v for b, v in zip(bottom, vals)]

    # Hatch the breakout columns so they read as subsets, not new totals
    for i, sub in enumerate(is_sub):
        if sub:
            ax.bar(
                i,
                bottom[i],
                width=0.72,
                fill=False,
                edgecolor=BG,
                linewidth=0,
                hatch="///",
                zorder=3.5,
            )

    for i, total in enumerate(bottom):
        ax.text(
            i,
            total + 0.9,
            str(total),
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
            color=MUTED if is_sub[i] else TEXT,
            zorder=4,
        )

    ax.axvspan(-0.5, len(KNEE_SUBS) + 0.5, color=CYAN, alpha=0.028, zorder=0)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=14.5)
    for tick, sub in zip(ax.get_xticklabels(), is_sub):
        tick.set_color(TICK_SUB if sub else TICK_BRIGHT)
    ax.set_ylabel("Players on the injury report", color=MUTED, fontsize=13)
    ax.set_ylim(0, max(bottom) * 1.13)
    ax.grid(axis="y", visible=True)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="y", labelsize=14)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(SPINE)

    leg = ax.legend(
        loc="upper right",
        fontsize=12.5,
        frameon=True,
        facecolor=SURFACE,
        edgecolor=SPINE,
        labelcolor=TICK_BRIGHT,
    )
    leg.set_zorder(5)

    fig.text(
        0.075,
        0.035,
        "Hatched columns are sub-types of Knee (combined), not additional players. "
        "Snapshot of players listed as injured\non Aug 24, 2026. "
        "Excludes undisclosed designations and suspensions.",
        ha="left",
        va="bottom",
        fontsize=10.5,
        color=FOOTNOTE,
        linespacing=1.5,
    )

    return fig, ax, list(zip(labels, bottom))


@app.command()
def main(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = FIGURES_DIR / "injury_status_by_type.png",
    top_n: int = 14,
):
    """Render the injury-status stacked bar chart to reports/figures/."""
    logger.info("Generating plot from data...")
    records = load_records(input_path)
    fig, _, totals = injury_status_stack(records, top_n=top_n)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=100, pad_inches=0)
    plt.close(fig)

    logger.info(f"cols: {totals}")
    logger.success(f"Plot saved to {output_path}")


if __name__ == "__main__":
    app()
