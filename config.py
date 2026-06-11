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
# cftc_name   : substring that uniquely identifies the market in CFTC data
# yf_ticker   : Yahoo Finance continuous-contract ticker
# display_name: label used in charts and analyst text
COMMODITIES = [
    {
        "cftc_name":    "SOYBEANS - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZS=F",
        "display_name": "Soja",
        "color":        "#2196F3",
    },
    {
        "cftc_name":    "CORN - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZC=F",
        "display_name": "Milho",
        "color":        "#FFC107",
    },
    {
        "cftc_name":    "WHEAT - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZW=F",
        "display_name": "Trigo SRW",
        "color":        "#FF9800",
    },
    {
        "cftc_name":    "SOYBEAN MEAL - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZM=F",
        "display_name": "Farelo de Soja",
        "color":        "#795548",
    },
    {
        "cftc_name":    "SOYBEAN OIL - CHICAGO BOARD OF TRADE",
        "yf_ticker":    "ZL=F",
        "display_name": "Óleo de Soja",
        "color":        "#CDDC39",
    },
    {
        "cftc_name":    "COTTON NO. 2 - ICE FUTURES U.S.",
        "yf_ticker":    "CT=F",
        "display_name": "Algodão",
        "color":        "#9C27B0",
    },
    {
        "cftc_name":    "COFFEE C - ICE FUTURES U.S.",
        "yf_ticker":    "KC=F",
        "display_name": "Café",
        "color":        "#6D4C41",
    },
    {
        "cftc_name":    "SUGAR NO. 11 - ICE FUTURES U.S.",
        "yf_ticker":    "SB=F",
        "display_name": "Açúcar",
        "color":        "#E91E63",
    },
    {
        "cftc_name":    "COCOA - ICE FUTURES U.S.",
        "yf_ticker":    "CC=F",
        "display_name": "Cacau",
        "color":        "#4E342E",
    },
]

# ── Chart output ──────────────────────────────────────────────────────────────
CHART_OUTPUT_PATH = "cot_report.png"
CHART_DPI         = 150        # higher = sharper image on mobile
CHART_FIGSIZE     = (20, 22)   # width x height in inches (portrait A4-ish)

# ── CFTC Socrata API ──────────────────────────────────────────────────────────
# Disaggregated Commitments of Traders – Futures and Options Combined
CFTC_API_URL = (
    "https://publicreporting.cftc.gov/resource/jun7-fc8e.json"
)
CFTC_PAGE_SIZE = 5000   # rows per request (Socrata max = 50000)
