# cot_chart.py — Generates one PNG per commodity

import logging
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from config import CHART_DPI, CHART_FIGSIZE

logger = logging.getLogger(__name__)

# ── Colour palette ────────────────────────────────────────────────────────────
BG_COLOR       = "#0D1117"
PANEL_COLOR    = "#161B22"
TEXT_COLOR     = "#E6EDF3"
SUBTEXT_COLOR  = "#8B949E"
GRID_COLOR     = "#21262D"
ZERO_COLOR     = "#6E7681"
POSITIVE_COLOR = "#2EA043"   # green  — net long area
NEGATIVE_COLOR = "#DA3633"   # red    — net short area
NET_LINE_COLOR = "#58A6FF"   # blue   — net position line
PRICE_COLOR    = "#F0C030"   # yellow — price line

# ── Font sizes (tuned for smartphone readability) ─────────────────────────────
FS_TITLE    = 17
FS_LABEL    = 13
FS_TICK     = 12
FS_LEGEND   = 12
FS_ANNOT    = 12
FS_FOOTER   = 10

OUTPUT_DIR = Path("charts")


def _fmt_thousands(x, _):
    if abs(x) >= 1_000:
        return f"{x/1000:.0f}k"
    return f"{x:.0f}"


def generate_charts(data: dict[str, dict]) -> dict[str, str]:
    """
    Generates one PNG per commodity.
    Returns dict[display_name → file_path].
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    plt.rcParams.update({
        "axes.prop_cycle":  plt.cycler(color=[NET_LINE_COLOR]),
        "figure.facecolor": BG_COLOR,
        "axes.facecolor":   PANEL_COLOR,
        "text.color":       TEXT_COLOR,
        "axes.labelcolor":  TEXT_COLOR,
        "xtick.color":      TEXT_COLOR,
        "ytick.color":      TEXT_COLOR,
    })

    paths = {}

    for name, commodity_data in data.items():
        cot_df   = commodity_data["cot"].copy()
        price_df = commodity_data["price"].copy()

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
            logger.warning(f"Empty merged data for {name}, skipping.")
            continue

        dates = merged["date"].values
        net   = merged["net_position"].values
        price = merged["close"].values

        # ── Figure & axes ─────────────────────────────────────────────────────
        fig, ax_net = plt.subplots(figsize=CHART_FIGSIZE, facecolor=BG_COLOR)
        ax_net.set_facecolor(PANEL_COLOR)
        ax_price = ax_net.twinx()
        ax_price.set_facecolor(PANEL_COLOR)

        # ── Net position: filled area + line ──────────────────────────────────
        ax_net.fill_between(dates, net, 0,
                            where=(net >= 0),
                            color=POSITIVE_COLOR, alpha=0.35, linewidth=0,
                            zorder=2)
        ax_net.fill_between(dates, net, 0,
                            where=(net < 0),
                            color=NEGATIVE_COLOR, alpha=0.35, linewidth=0,
                            zorder=2)
        ax_net.plot(dates, net,
                    color=NET_LINE_COLOR,
                    linewidth=2.8, alpha=1.0,
                    zorder=3, label="Net Position (Fundos)")
        ax_net.axhline(0, color=ZERO_COLOR, linewidth=1.2,
                       linestyle="--", zorder=1)

        # ── Price line ────────────────────────────────────────────────────────
        ax_price.plot(dates, price,
                      color=PRICE_COLOR,
                      linewidth=2.8, alpha=1.0,
                      zorder=4, label="Preço")

        # ── Spines & ticks ────────────────────────────────────────────────────
        for ax in (ax_net, ax_price):
            for spine in ax.spines.values():
                spine.set_edgecolor(GRID_COLOR)
                spine.set_linewidth(1.2)
            ax.tick_params(labelsize=FS_TICK, length=5, width=1.2, pad=6)

        ax_net.tick_params(axis="y",   colors=NET_LINE_COLOR)
        ax_net.tick_params(axis="x",   colors=TEXT_COLOR)
        ax_price.tick_params(axis="y", colors=PRICE_COLOR)

        # ── Y-axis labels ─────────────────────────────────────────────────────
        ax_net.set_ylabel("Net Position (contratos)",
                          color=NET_LINE_COLOR, fontsize=FS_LABEL, labelpad=10)
        ax_price.set_ylabel("Preço (contrato contínuo)",
                             color=PRICE_COLOR,   fontsize=FS_LABEL, labelpad=10)

        ax_net.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_thousands))

        # ── X-axis ────────────────────────────────────────────────────────────
        ax_net.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
        ax_net.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax_net.xaxis.get_majorticklabels(),
                 rotation=30, ha="right", color=TEXT_COLOR, fontsize=FS_TICK)

        # ── Grid ──────────────────────────────────────────────────────────────
        ax_net.grid(True, color=GRID_COLOR, linewidth=0.8,
                    linestyle=":", zorder=0)
        ax_net.set_axisbelow(True)

        # ── Latest-value annotations ──────────────────────────────────────────
        latest_net   = float(net[-1])
        latest_price = float(price[-1])
        sign = "+" if latest_net >= 0 else ""

        _annot_style = dict(
            boxstyle="round,pad=0.25",
            facecolor=PANEL_COLOR,
            edgecolor=GRID_COLOR,
            alpha=0.90,
        )

        ax_net.annotate(
            f"{sign}{latest_net/1000:.1f}k",
            xy=(dates[-1], latest_net),
            xytext=(8, 0), textcoords="offset points",
            color=NET_LINE_COLOR, fontsize=FS_ANNOT, fontweight="bold",
            va="center", bbox=_annot_style,
        )
        ax_price.annotate(
            f"{latest_price:,.2f}",
            xy=(dates[-1], latest_price),
            xytext=(8, 0), textcoords="offset points",
            color=PRICE_COLOR, fontsize=FS_ANNOT, fontweight="bold",
            va="center", bbox=_annot_style,
        )

        # ── Title ─────────────────────────────────────────────────────────────
        report_date = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        ax_net.set_title(
            f"{name}  ·  COT Managed Money  ·  {report_date}",
            color=TEXT_COLOR, fontsize=FS_TITLE, fontweight="bold",
            pad=14, loc="left",
        )

        # ── Legend ────────────────────────────────────────────────────────────
        lines_net,   labels_net   = ax_net.get_legend_handles_labels()
        lines_price, labels_price = ax_price.get_legend_handles_labels()
        ax_net.legend(
            lines_net + lines_price,
            labels_net + labels_price,
            loc="upper left",
            fontsize=FS_LEGEND,
            facecolor="#1C2128",
            edgecolor=GRID_COLOR,
            labelcolor=TEXT_COLOR,
            framealpha=0.92,
            handlelength=2.0,
            handleheight=1.2,
        )

        # ── Footer ────────────────────────────────────────────────────────────
        fig.text(
            0.5, -0.01,
            "Fonte: CFTC Disaggregated COT (Managed Money, Fut+Opt) · Yahoo Finance",
            ha="center", fontsize=FS_FOOTER, color=SUBTEXT_COLOR,
        )

        # ── Save ──────────────────────────────────────────────────────────────
        safe_name   = name.replace(" ", "_").replace("/", "-")
        output_path = OUTPUT_DIR / f"cot_{safe_name}.png"

        plt.tight_layout(pad=1.8)
        plt.savefig(output_path, dpi=CHART_DPI, bbox_inches="tight",
                    facecolor=BG_COLOR, pad_inches=0.20)
        plt.close(fig)

        paths[name] = str(output_path)
        logger.info(f"Chart saved → {output_path}")

    plt.rcParams.update(plt.rcParamsDefault)

    return paths
