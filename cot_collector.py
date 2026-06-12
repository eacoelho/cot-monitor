# cot_collector.py — Fetches COT data from CFTC and price data from Yahoo Finance

import logging
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import yfinance as yf

from config import CFTC_API_URL, CFTC_PAGE_SIZE, COMMODITIES, LOOKBACK_WEEKS

logger = logging.getLogger(__name__)


# ── CFTC ──────────────────────────────────────────────────────────────────────

def fetch_cot_data() -> dict[str, pd.DataFrame]:
    """
    Fetch Disaggregated COT (Futures + Options Combined) from CFTC Socrata API
    for the last LOOKBACK_WEEKS weeks.

    Returns a dict keyed by display_name → DataFrame with columns:
        date, net_position (managed money long - short)
    """
    cutoff     = datetime.now(timezone.utc) - timedelta(weeks=LOOKBACK_WEEKS)
    cutoff_str = cutoff.strftime("%Y-%m-%d")   # text field — date string only

    results: dict[str, pd.DataFrame] = {}

    for commodity in COMMODITIES:
        name      = commodity["display_name"]
        cftc_name = commodity["cftc_name"]

        logger.info(f"Fetching COT for {name} ({cftc_name})")

        rows   = []
        offset = 0

        while True:
            # futonly_or_combined = 'Combined' ensures futures + options rows only
            where_clause = (
                f"market_and_exchange_names='{cftc_name}' "
                f"AND report_date_as_yyyy_mm_dd >= '{cutoff_str}' "
                f"AND futonly_or_combined='Combined'"
            )

            params = {
                "$where":  where_clause,
                "$select": (
                    "report_date_as_yyyy_mm_dd,"
                    "m_money_positions_long_all,"
                    "m_money_positions_short_all"
                ),
                "$order":  "report_date_as_yyyy_mm_dd ASC",
                "$limit":  CFTC_PAGE_SIZE,
                "$offset": offset,
            }

            try:
                resp = requests.get(CFTC_API_URL, params=params, timeout=30)
                resp.raise_for_status()
                batch = resp.json()
            except Exception as e:
                logger.error(f"CFTC request failed for {name}: {e}")
                break

            if not batch:
                break

            rows.extend(batch)
            offset += len(batch)

            if len(batch) < CFTC_PAGE_SIZE:
                break

            time.sleep(0.3)

        if not rows:
            logger.warning(f"No COT data returned for {name} — check cftc_name in config.py")
            continue

        df = pd.DataFrame(rows)
        df["date"]  = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
        df["long"]  = pd.to_numeric(df["m_money_positions_long_all"],  errors="coerce")
        df["short"] = pd.to_numeric(df["m_money_positions_short_all"], errors="coerce")
        df["net_position"] = df["long"] - df["short"]
        df = (
            df[["date", "net_position"]]
            .dropna()
            .sort_values("date")
            .reset_index(drop=True)
        )

        results[name] = df
        logger.info(f"  → {len(df)} weeks of COT data for {name}")

    return results


# ── Yahoo Finance ─────────────────────────────────────────────────────────────

def fetch_price_data() -> dict[str, pd.DataFrame]:
    """
    Fetch weekly closing prices from Yahoo Finance for each commodity.

    Returns a dict keyed by display_name → DataFrame with columns:
        date, close
    """
    cutoff    = datetime.now(timezone.utc) - timedelta(weeks=LOOKBACK_WEEKS + 4)
    start_str = cutoff.strftime("%Y-%m-%d")

    results: dict[str, pd.DataFrame] = {}

    for commodity in COMMODITIES:
        name   = commodity["display_name"]
        ticker = commodity["yf_ticker"]

        logger.info(f"Fetching prices for {name} ({ticker})")

        try:
            raw = yf.download(
                ticker,
                start=start_str,
                interval="1wk",
                auto_adjust=True,
                progress=False,
            )
        except Exception as e:
            logger.error(f"yfinance failed for {name}: {e}")
            continue

        if raw.empty:
            logger.warning(f"No price data for {name} ({ticker})")
            continue

        df = raw[["Close"]].copy()
        df.columns = ["close"]
        df.index.name = "date"
        df = df.reset_index()
        df["date"]  = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna().sort_values("date").reset_index(drop=True)

        results[name] = df
        logger.info(f"  → {len(df)} weeks of price data for {name}")

    return results


# ── Diagnostic helper ─────────────────────────────────────────────────────────

def validate_cftc_names():
    """
    Utility: prints the exact market_and_exchange_names available in the
    CFTC dataset for each commodity keyword. Run once to verify config.py names.

    Usage:
        python -c "from cot_collector import validate_cftc_names; validate_cftc_names()"
    """
    keywords = [
        "SOYBEAN", "CORN", "WHEAT", "COTTON", "COFFEE", "SUGAR", "COCOA"
    ]
    for kw in keywords:
        params = {
            "$where":  f"market_and_exchange_names like '%{kw}%' AND futonly_or_combined='Combined'",
            "$select": "market_and_exchange_names",
            "$group":  "market_and_exchange_names",
            "$limit":  20,
        }
        try:
            resp = requests.get(CFTC_API_URL, params=params, timeout=15)
            resp.raise_for_status()
            for row in resp.json():
                print(row["market_and_exchange_names"])
        except Exception as e:
            print(f"Error for {kw}: {e}")
        print()


# ── Combined ──────────────────────────────────────────────────────────────────

def collect_all() -> dict[str, dict]:
    """
    Returns a unified dict:
    {
        display_name: {
            "cot":   DataFrame(date, net_position),
            "price": DataFrame(date, close),
        }
    }
    """
    logger.info("=== Starting data collection ===")
    cot_data   = fetch_cot_data()
    price_data = fetch_price_data()

    combined = {}
    for commodity in COMMODITIES:
        name = commodity["display_name"]
        if name not in cot_data or name not in price_data:
            logger.warning(f"Skipping {name}: missing COT or price data")
            continue
        combined[name] = {
            "cot":   cot_data[name],
            "price": price_data[name],
        }

    logger.info(f"=== Collection complete: {len(combined)}/{len(COMMODITIES)} commodities ===")
    return combined
