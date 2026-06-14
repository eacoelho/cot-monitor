#!/usr/bin/env python3
# cot_runner.py — Main orchestrator: wait → collect → chart → analyse → notify

import logging
import requests
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from cot_analyst import build_summary, generate_analysis
from cot_chart import generate_charts
from cot_collector import collect_all
from cot_notifier import notify_all, send_summary
from config import CFTC_API_URL

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

# ── CFTC release polling config ───────────────────────────────────────────────
POLL_INTERVAL_SEC = 300    # check every 5 minutes
MAX_WAIT_SEC      = 14400  # give up after 4 hours


def _expected_report_date() -> date:
    """
    COT reports are 'as of' close of business on Tuesday.
    Returns the date of the most recent Tuesday (the current reporting week).

    Formula: (weekday - 1) % 7 gives the number of days since last Tuesday.
      Friday (4)   → 3 days back → this Tuesday ✓
      Saturday (5) → 4 days back → this Tuesday ✓
      Monday (0)   → 6 days back → last Tuesday ✓
    """
    today = datetime.now(timezone.utc).date()
    days_back = (today.weekday() - 1) % 7
    return today - timedelta(days=days_back)


def _wait_for_cot_release() -> bool:
    """
    Polls the CFTC Socrata API every POLL_INTERVAL_SEC seconds until the
    current week's COT report is published, or MAX_WAIT_SEC is exceeded.

    Handles CFTC delays from US federal holidays, government shutdowns,
    or technical issues. Returns True when data is available, False on timeout.

    On non-Friday runs (manual execution), skips the wait entirely.
    """
    today = datetime.now(timezone.utc).date()

    if today.weekday() != 4:  # 4 = Friday
        logger.warning(
            f"Today is {today.strftime('%A %Y-%m-%d')} — not the usual CFTC release day. "
            "Skipping wait and proceeding directly."
        )
        return True

    expected     = _expected_report_date()
    expected_str = expected.strftime("%Y-%m-%d")
    deadline     = time.monotonic() + MAX_WAIT_SEC

    logger.info(
        f"Polling CFTC for COT report dated {expected_str} "
        f"(poll every {POLL_INTERVAL_SEC // 60} min, timeout in {MAX_WAIT_SEC // 3600}h)."
    )

    while time.monotonic() < deadline:
        try:
            resp = requests.get(
                CFTC_API_URL,
                params={
                    "$where": (
                        f"report_date_as_yyyy_mm_dd='{expected_str}'"
                        f" AND futonly_or_combined='Combined'"
                    ),
                    "$select": "report_date_as_yyyy_mm_dd",
                    "$limit":  1,
                },
                timeout=15,
            )
            resp.raise_for_status()
            if resp.json():
                logger.info(f"COT report for {expected_str} is now available. Proceeding.")
                return True
        except Exception as e:
            logger.warning(f"CFTC availability check error: {e}")

        remaining_min = max(0, int((deadline - time.monotonic()) / 60))
        logger.info(
            f"Report not yet available — "
            f"retrying in {POLL_INTERVAL_SEC // 60} min "
            f"({remaining_min} min until timeout)."
        )
        time.sleep(POLL_INTERVAL_SEC)

    logger.error(
        f"CFTC did not publish the COT report for {expected_str} "
        f"within {MAX_WAIT_SEC // 3600}h. "
        "Likely cause: US federal holiday, government shutdown, or CFTC technical issue. "
        "Skipping this week — the next Friday run will resume normally."
    )
    return False


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"COT Monitor pipeline started at {start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)

    # 0 — Wait for CFTC to publish this week's report
    if not _wait_for_cot_release():
        logger.info("Exiting gracefully — no data published this week.")
        sys.exit(0)

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

    # 5 — Send summary (one text message with all commodities)
    try:
        send_summary(build_summary(data))
    except Exception as e:
        logger.exception(f"Summary message failed: {e}")

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Pipeline completed in {elapsed:.1f}s — {len(chart_paths)} commodities sent.")


if __name__ == "__main__":
    run()
