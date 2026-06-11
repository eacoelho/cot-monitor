# cot_chart.py — Generates one PNG per commodity

import logging
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from config import COMMODITIES

logger = logging.getLogger(__name__)

# ── Style ─────────────────────────────────────────────────────────────────────
BG_COLOR       = "#0D1117"
PANEL_COLOR    = "#161B22"
TEXT_COLOR     = "#E6EDF3"
GRID_COLOR     = "#21262D"
ZERO_COLOR     = "#555E6A"
POSITIVE_COLOR = "#2EA043"
NEGATIVE_COLOR = "#DA3633"
PRICE_COLOR    = "#F0C030"

OUTPUT_DIR = Path("charts")


def _fmt_thousands(x, _):
    if abs(x) >= 1_000:
        return f"{x/1000:.0f}k"
    return f"{x:.0f}"


def _commodity_color(name: str) -> str:
    for c in COMMODITIES:
        if c["display_name"] == name:
            return c["color"]
    return "#AAAAAA"


def generate_charts(data: dict[str, dict]) -> dict[str, str]:
    """
    Generates one PNG per commodity.

    Returns
    -------
    dict[display_name → file_path]
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    paths = {}

    for commodity in COMMODITIES:
        name = commodity["display_name"]
        if name not in data:
            logger.warning(f"No data for {name}, skipping chart.")
            continue

        cot_df   = data[name]["cot"].copy()
        price_df = data[name]["price"].copy()

        # ── Normalise datetime resolution before merge ────────────────────────
        cot_df["date"]   = cot_df["date"].astype("datetime64[s]")
        price_df["date"] = price_df["date"].astype("datetime64[s]")

        merged = pd.merge_asof(
            cot_df.sort_values("date"),
            price_df.sort_values("date"),
            on="date",
            direction="nearest",
            tolerance=pd.Timedelta("7 days"),
        ).dropna()

        if merged.empty:
            logger.warning(f"Empty merged data for {name}, skipping chart.")
            continue

        dates = merged["date"].values
        net   = merged["net_position"].values
        price = merged["close"].values

        # ── Figure ────────────────────────────────────────────────────────────
        fig, ax_pos = plt.subplots(figsize=(12, 5), facecolor=BG_COLOR)
        ax_pos.set_facecolor(PANEL_COLOR)
        ax_price = ax_pos.twinx()

        # ── Net position fill ─────────────────────────────────────────────────
        ax_pos.fill_between(dates, net, 0,
                            where=(net >= 0),
                            color=POSITIVE_COLOR, alpha=0.45, linewidth=0)
        ax_pos.fill_between(dates, net, 0,
                            where=(net < 0),
                            color=NEGATIVE_COLOR, alpha=0.45, linewidth=0)
        ax_pos.plot(dates, net,
                    color=_commodity_color(name), linewidth=1.6, alpha=0.95,
                    label="Net Position (Fundos)")
        ax_pos.axhline(0, color=ZERO_COLOR, linewidth=0.9, linestyle="--")

        # ── Price line ────────────────────────────────────────────────────────
        ax_price.plot(dates, price,
                      color=PRICE_COLOR, linewidth=2.0, alpha=0.90,
                      label="Preço")

        # ── Axis formatting ───────────────────────────────────────────────────
        ax_pos.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_thousands))
        ax_pos.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
        ax_pos.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax_pos.xaxis.get_majorticklabels(), rotation=30, ha="right",
                 color=TEXT_COLOR, fontsize=9)

        for ax in (ax_pos, ax_price):
            ax.tick_params(colors=TEXT_COLOR, labelsize=9)
            for spine in ax.spines.values():
                spine.set_edgecolor(GRID_COLOR)

        ax_pos.tick_params(axis="y",   labelcolor=_commodity_color(name))
        ax_price.tick_params(axis="y", labelcolor=PRICE_COLOR)
        ax_pos.grid(True, color=GRID_COLOR, linewidth=0.6, linestyle=":")
        ax_pos.set_axisbelow(True)

        ax_pos.set_ylabel("Net Position (contratos)", color=TEXT_COLOR, fontsize=10)
        ax_price.set_ylabel("Preço (contrato contínuo)", color=PRICE_COLOR, fontsize=10)

        # ── Title ─────────────────────────────────────────────────────────────
        latest_net   = net[-1]
        latest_price = price[-1]
        sign = "+" if latest_net >= 0 else ""
        report_date  = datetime.now().strftime("%d/%m/%Y")

        fig.suptitle(
            f"{name}   |   Net: {sign}{latest_net/1000:.1f}k contratos   |   "
            f"Preço: {latest_price:,.2f}   |   {report_date}",
            fontsize=12, fontweight="bold",
            color=TEXT_COLOR, y=1.01,
        )

        # ── Legend ────────────────────────────────────────────────────────────
        lines_pos,  labels_pos  = ax_pos.get_legend_handles_labels()
        lines_price, labels_price = ax_price.get_legend_handles_labels()
        ax_pos.legend(
            lines_pos + lines_price,
            labels_pos + labels_price,
            loc="upper left",
            fontsize=8,
            facecolor=PANEL_COLOR,
            edgecolor=GRID_COLOR,
            labelcolor=TEXT_COLOR,
            framealpha=0.85,
        )

        # ── Footer ────────────────────────────────────────────────────────────
        fig.text(
            0.5, -0.04,
            "Fonte: CFTC Disaggregated COT (Managed Money, Fut+Opt) · Yahoo Finance",
            ha="center", fontsize=7.5, color="#484F58",
        )

        # ── Save ──────────────────────────────────────────────────────────────
        safe_name = name.replace(" ", "_").replace("/", "-")
        output_path = OUTPUT_DIR / f"cot_{safe_name}.png"

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
        plt.close(fig)

        paths[name] = str(output_path)
        logger.info(f"Chart saved → {output_path}")

    return paths
