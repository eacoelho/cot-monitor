# cot_chart.py — Generates the 3×3 one-page PNG report

import logging
from datetime import datetime

import matplotlib
matplotlib.use("Agg")   # non-interactive backend — must be set before pyplot import

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from config import CHART_DPI, CHART_FIGSIZE, CHART_OUTPUT_PATH, COMMODITIES

logger = logging.getLogger(__name__)

GRID_ROWS = 3
GRID_COLS = 3

# ── Colour palette ────────────────────────────────────────────────────────────
BG_COLOR      = "#0D1117"   # dark background
PANEL_COLOR   = "#161B22"   # subplot background
TEXT_COLOR    = "#E6EDF3"   # primary text
GRID_COLOR    = "#21262D"   # subtle grid lines
ZERO_COLOR    = "#484F58"   # zero-line on net position axis
POSITIVE_COLOR = "#238636"  # net long fill
NEGATIVE_COLOR = "#DA3633"  # net short fill
PRICE_COLOR   = "#F0C030"   # price line


def _commodity_color(name: str) -> str:
    for c in COMMODITIES:
        if c["display_name"] == name:
            return c["color"]
    return "#AAAAAA"


def _format_thousands(x, _pos):
    if abs(x) >= 1_000:
        return f"{x/1000:.0f}k"
    return f"{x:.0f}"


def generate_chart(data: dict[str, dict], output_path: str = CHART_OUTPUT_PATH) -> str:
    """
    Generates a 3×3 grid PNG.  Each subplot shows:
      - Left Y-axis : net managed-money position (area fill, green/red)
      - Right Y-axis: commodity price (yellow line)

    Parameters
    ----------
    data : output of cot_collector.collect_all()
    output_path : file path for the saved PNG

    Returns
    -------
    str : resolved output_path
    """
    names = [c["display_name"] for c in COMMODITIES if c["display_name"] in data]

    fig, axes = plt.subplots(
        GRID_ROWS, GRID_COLS,
        figsize=CHART_FIGSIZE,
        facecolor=BG_COLOR,
    )
    fig.subplots_adjust(hspace=0.45, wspace=0.35)

    # ── Header ────────────────────────────────────────────────────────────────
    report_date = datetime.now().strftime("%d/%m/%Y")
    fig.suptitle(
        f"COT Report — Managed Money Net Position + Price   |   {report_date}",
        fontsize=14,
        fontweight="bold",
        color=TEXT_COLOR,
        y=0.98,
    )

    flat_axes = axes.flatten()

    for idx, name in enumerate(names):
        ax_pos  = flat_axes[idx]
        ax_price = ax_pos.twinx()

        cot_df   = data[name]["cot"]
        price_df = data[name]["price"]

        # ── Align by merging on nearest week ──────────────────────────────────
        merged = pd.merge_asof(
            cot_df.sort_values("date"),
            price_df.sort_values("date"),
            on="date",
            direction="nearest",
            tolerance=pd.Timedelta("7 days"),
        ).dropna()

        if merged.empty:
            ax_pos.set_visible(False)
            ax_price.set_visible(False)
            continue

        dates      = merged["date"].values
        net        = merged["net_position"].values
        price      = merged["close"].values

        # ── Panel background ──────────────────────────────────────────────────
        ax_pos.set_facecolor(PANEL_COLOR)

        # ── Net position area fill ────────────────────────────────────────────
        ax_pos.fill_between(
            dates, net, 0,
            where=(net >= 0),
            color=POSITIVE_COLOR,
            alpha=0.55,
            linewidth=0,
        )
        ax_pos.fill_between(
            dates, net, 0,
            where=(net < 0),
            color=NEGATIVE_COLOR,
            alpha=0.55,
            linewidth=0,
        )
        ax_pos.plot(dates, net, color=_commodity_color(name), linewidth=1.2, alpha=0.9)
        ax_pos.axhline(0, color=ZERO_COLOR, linewidth=0.8, linestyle="--")

        # ── Price line ────────────────────────────────────────────────────────
        ax_price.plot(dates, price, color=PRICE_COLOR, linewidth=1.5, alpha=0.85)

        # ── Axes styling ──────────────────────────────────────────────────────
        for ax in (ax_pos, ax_price):
            ax.tick_params(colors=TEXT_COLOR, labelsize=7)
            for spine in ax.spines.values():
                spine.set_edgecolor(GRID_COLOR)

        ax_pos.yaxis.set_major_formatter(mticker.FuncFormatter(_format_thousands))
        ax_pos.tick_params(axis="y", labelcolor=_commodity_color(name), labelsize=7)
        ax_pos.tick_params(axis="x", labelcolor=TEXT_COLOR, labelsize=7)
        ax_price.tick_params(axis="y", labelcolor=PRICE_COLOR, labelsize=7)

        ax_pos.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
        ax_pos.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax_pos.xaxis.get_majorticklabels(), rotation=30, ha="right")

        ax_pos.grid(True, color=GRID_COLOR, linewidth=0.5, linestyle=":")
        ax_pos.set_axisbelow(True)

        # ── Latest values annotation ──────────────────────────────────────────
        latest_net   = net[-1]
        latest_price = price[-1]
        sign = "+" if latest_net >= 0 else ""
        ax_pos.set_title(
            f"{name}\n"
            f"Net: {sign}{latest_net/1000:.1f}k  |  Price: {latest_price:,.2f}",
            fontsize=8.5,
            fontweight="bold",
            color=TEXT_COLOR,
            pad=4,
        )

        # ── Y-axis labels ─────────────────────────────────────────────────────
        ax_pos.set_ylabel("Net position (contratos)", fontsize=6.5, color=TEXT_COLOR, labelpad=4)
        ax_price.set_ylabel("Preço", fontsize=6.5, color=PRICE_COLOR, labelpad=4)

    # ── Hide unused subplots if < 9 commodities ───────────────────────────────
    for idx in range(len(names), GRID_ROWS * GRID_COLS):
        flat_axes[idx].set_visible(False)

    # ── Legend ────────────────────────────────────────────────────────────────
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=POSITIVE_COLOR, alpha=0.7, label="Net Long (Fundos)"),
        Patch(facecolor=NEGATIVE_COLOR, alpha=0.7, label="Net Short (Fundos)"),
        Line2D([0], [0], color=PRICE_COLOR, linewidth=1.5, label="Preço (contrato contínuo)"),
    ]
    fig.legend(
        handles=legend_elements,
        loc="lower center",
        ncol=3,
        fontsize=8,
        facecolor=PANEL_COLOR,
        edgecolor=GRID_COLOR,
        labelcolor=TEXT_COLOR,
        framealpha=0.9,
        bbox_to_anchor=(0.5, 0.01),
    )

    # ── Footer ────────────────────────────────────────────────────────────────
    fig.text(
        0.5, 0.005,
        "Fonte: CFTC (Disaggregated COT – Managed Money, Futures + Options) · Yahoo Finance",
        ha="center",
        fontsize=7,
        color="#484F58",
    )

    plt.savefig(output_path, dpi=CHART_DPI, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)

    logger.info(f"Chart saved → {output_path}")
    return output_path
