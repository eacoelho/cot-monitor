# config.py — COT Monitor Configuration

# ── Telegram ────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID   = "YOUR_TELEGRAM_CHAT_ID"

# ── Groq ─────────────────────────────────────────────────────────────────────
GROQ_API_KEY = "YOUR_GROQ_API_KEY"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ── Data window ───────────────────────────────────────────────────────────────
LOOKBACK_WEEKS = 52   # ~12 months of COT history

# ── Commodity definitions ─────────────────────────────────────────────────────
# cftc_name   : exact market_and_exchange_names value in the CFTC dataset
# yf_ticker   : Yahoo Finance continuous-contract ticker
# display_name: label used in charts and analyst text
COMMODITIES = [
    {
        "cftc_name":    "SOYBEANS - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZS=F",
        "display_name": "Soja",
    },
    {
        "cftc_name":    "CORN - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZC=F",
        "display_name": "Milho",
    },
    {
        "cftc_name":    "WHEAT - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZW=F",
        "display_name": "Trigo SRW",
    },
    {
        "cftc_name":    "SOYBEAN MEAL - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZM=F",
        "display_name": "Farelo de Soja",
    },
    {
        "cftc_name":    "SOYBEAN OIL - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZL=F",
        "display_name": "Óleo de Soja",
    },
    {
        "cftc_name":    "COTTON NO. 2 - ICE FUTURES U.S.",
        "yf_ticker":    "CT=F",
        "display_name": "Algodão",
    },
    {
        "cftc_name":    "COFFEE C - ICE FUTURES U.S.",
        "yf_ticker":    "KC=F",
        "display_name": "Café",
    },
    {
        "cftc_name":    "SUGAR NO. 11 - ICE FUTURES U.S.",
        "yf_ticker":    "SB=F",
        "display_name": "Açúcar",
    },
    {
        "cftc_name":    "COCOA - ICE FUTURES U.S.",
        "yf_ticker":    "CC=F",
        "display_name": "Cacau",
    },
]

# ── Chart output ──────────────────────────────────────────────────────────────
CHART_DPI     = 180       # higher = sharper image on mobile
CHART_FIGSIZE = (14, 8)   # width x height in inches per commodity chart

# ── CFTC Socrata API ──────────────────────────────────────────────────────────
# Disaggregated Commitments of Traders – Futures and Options Combined
CFTC_API_URL  = "https://publicreporting.cftc.gov/resource/kh3c-gbw2.json"
CFTC_PAGE_SIZE = 5000   # rows per request (Socrata max = 50000)