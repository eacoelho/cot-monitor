#!/usr/bin/env python3
# cot_runner.py — Main orchestrator: collect → chart → analyse → notify

import logging
import sys
from datetime import datetime
from pathlib import Path

from cot_analyst import generate_analysis
from cot_chart import generate_charts
from cot_collector import collect_all
from cot_notifier import notify_all

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "cot_monitor.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("cot_runner")


def run():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"COT Monitor pipeline started at {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 1 — Collect
    try:
        data = collect_all()
    except Exception as e:
        logger.exception(f"Data collection failed: {e}")
        sys.exit(1)

    if not data:
        logger.error("No data collected. Aborting.")
        sys.exit(1)

    # 2 — Charts (one per commodity)
    try:
        chart_paths = generate_charts(data)
    except Exception as e:
        logger.exception(f"Chart generation failed: {e}")
        sys.exit(1)

    if not chart_paths:
        logger.error("No charts generated. Aborting.")
        sys.exit(1)

    # 3 — Analysis (one paragraph per commodity)
    try:
        analyses = generate_analysis(data)
    except Exception as e:
        logger.exception(f"Analysis generation failed: {e}")
        analyses = {}

    # 4 — Send via Telegram (one message per commodity)
    try:
        notify_all(chart_paths, analyses)
    except Exception as e:
        logger.exception(f"Notification failed: {e}")
        sys.exit(1)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Pipeline completed in {elapsed:.1f}s — {len(chart_paths)} commodities sent.")


if __name__ == "__main__":
    run()
