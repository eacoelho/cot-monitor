#!/usr/bin/env python3
# cot_runner.py — Main orchestrator: collect → chart → analyse → notify

import logging
import sys
from datetime import datetime
from pathlib import Path

from config import CHART_OUTPUT_PATH
from cot_analyst import generate_analysis
from cot_chart import generate_chart
from cot_collector import collect_all
from cot_notifier import notify

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


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"COT Monitor pipeline started at {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 1 — Collect data
    try:
        data = collect_all()
    except Exception as e:
        logger.exception(f"Data collection failed: {e}")
        sys.exit(1)

    if not data:
        logger.error("No data collected. Aborting.")
        sys.exit(1)

    # 2 — Generate chart
    try:
        chart_path = generate_chart(data, output_path=CHART_OUTPUT_PATH)
    except Exception as e:
        logger.exception(f"Chart generation failed: {e}")
        sys.exit(1)

    # 3 — Generate analysis
    try:
        analysis = generate_analysis(data)
    except Exception as e:
        logger.exception(f"Analysis generation failed: {e}")
        analysis = "⚠️ Análise automática indisponível. Verifique os logs."

    # 4 — Send via Telegram
    try:
        success = notify(chart_path, analysis)
        if not success:
            logger.error("Notification failed (partial or complete).")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Notification failed: {e}")
        sys.exit(1)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Pipeline completed successfully in {elapsed:.1f}s")


if __name__ == "__main__":
    run()
