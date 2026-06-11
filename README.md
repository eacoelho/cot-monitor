# COT Monitor 🌾

Automated weekly report that fetches **Commitment of Traders (COT)** data from the CFTC, combines it with commodity futures prices from Yahoo Finance, generates a one-page chart, and delivers an AI-written analysis in Brazilian Portuguese via Telegram.

---

## What it does

Every Friday evening (after CFTC publishes the weekly report), the pipeline:

1. **Collects** managed-money net positions (futures + options) from the [CFTC Disaggregated COT](https://publicreporting.cftc.gov/) for the last 52 weeks
2. **Collects** weekly closing prices for each commodity from Yahoo Finance
3. **Generates** a 3×3 dark-themed PNG with net positions (area chart) and price (line) on a dual Y-axis per commodity
4. **Analyses** the data via Groq (Llama 3.3) and produces a structured commentary in PT-BR
5. **Sends** the image + text to a Telegram chat or channel

### Covered commodities

| Commodity | CFTC Market | Yahoo Finance |
|---|---|---|
| Soja | SOYBEANS – CBOT | ZS=F |
| Milho | CORN – CBOT | ZC=F |
| Trigo SRW | WHEAT – CBOT | ZW=F |
| Farelo de Soja | SOYBEAN MEAL – CBOT | ZM=F |
| Óleo de Soja | SOYBEAN OIL – CBOT | ZL=F |
| Algodão | COTTON NO. 2 – ICE | CT=F |
| Café | COFFEE C – ICE | KC=F |
| Açúcar | SUGAR NO. 11 – ICE | SB=F |
| Cacau | COCOA – ICE | CC=F |

---

## Requirements

- Python 3.11+
- VPS or server with internet access (tested on Ubuntu 22.04 LTS)
- Telegram bot token and chat/channel ID
- Free [Groq API key](https://console.groq.com/)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/cot-monitor.git
cd cot-monitor

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
nano .env   # fill in your keys
```

### Configure credentials in `config.py`

Open `config.py` and replace the placeholder values:

```python
TELEGRAM_BOT_TOKEN = "your_token_here"
TELEGRAM_CHAT_ID   = "your_chat_id_here"
GROQ_API_KEY       = "your_groq_key_here"
```

> **Security note**: If this repository is public, prefer loading credentials from environment variables. See the `.env.example` for reference and adapt `config.py` to use `os.getenv()`.

---

## Running manually

```bash
source venv/bin/activate
python cot_runner.py
```

Logs are written to `logs/cot_monitor.log` and to stdout.

---

## Automated weekly execution (systemd)

This is the recommended approach for VPS deployment.

```bash
# 1. Edit the service file — replace YOUR_VPS_USER with your actual username
nano cot-monitor.service

# 2. Copy service and timer files
sudo cp cot-monitor.service /etc/systemd/system/
sudo cp cot-monitor.timer   /etc/systemd/system/

# 3. Enable and start the timer
sudo systemctl daemon-reload
sudo systemctl enable --now cot-monitor.timer

# 4. Verify
sudo systemctl list-timers --all | grep cot
```

The timer fires every **Friday at 21:30 UTC** (approximately one hour after the CFTC publishes, which occurs around 20:30 UTC / 15:30 ET).

### Useful commands

```bash
# Check last run status
sudo systemctl status cot-monitor.service

# View logs
journalctl -u cot-monitor.service -n 50 --no-pager

# Run immediately (for testing)
sudo systemctl start cot-monitor.service

# Tail live log file
tail -f logs/cot_monitor.log
```

---

## Project structure

```
cot-monitor/
├── config.py            # All settings: credentials, commodities, chart params
├── cot_collector.py     # CFTC API + Yahoo Finance data collection
├── cot_chart.py         # Matplotlib 3×3 PNG generation
├── cot_analyst.py       # Groq LLM prompt builder + analysis
├── cot_notifier.py      # Telegram Bot API delivery
├── cot_runner.py        # Pipeline orchestrator (entry point)
├── requirements.txt
├── cot-monitor.service  # systemd service unit
├── cot-monitor.timer    # systemd timer unit (weekly Friday)
├── .env.example         # Credential template
├── .gitignore
└── README.md
```

---

## Data sources

| Source | Data | Access |
|---|---|---|
| [CFTC Socrata API](https://publicreporting.cftc.gov/resource/jun7-fc8e.json) | Disaggregated COT – Managed Money | Free, no auth required |
| [Yahoo Finance (yfinance)](https://github.com/ranaroussi/yfinance) | Continuous futures prices | Free, no auth required |
| [Groq](https://console.groq.com/) | Llama 3.3 inference | Free tier available |
| [Telegram Bot API](https://core.telegram.org/bots/api) | Message delivery | Free |

---

## Known limitations

- **Yahoo Finance** does not guarantee data continuity for futures tickers. If a ticker stops returning data, update `yf_ticker` in `config.py`.
- **CFTC API** occasionally returns stale or delayed data around holidays. The pipeline logs warnings but does not block execution.
- **Groq free tier** has rate limits. The analyst module includes retry logic with exponential backoff.
- The one-page image is generated at 150 DPI (~3000×3300 px). Telegram compresses images; if quality degrades, increase `CHART_DPI` in `config.py` or send as a document instead (requires a minor change in `cot_notifier.py`).

---

## Sending as document instead of compressed image

In `cot_notifier.py`, replace `sendPhoto` with `sendDocument`:

```python
# In _send_photo(), change:
response = requests.post(
    f"{BASE_URL}/sendDocument",
    data={"chat_id": TELEGRAM_CHAT_ID},
    files={"document": img},
    timeout=60,
)
```

This preserves full resolution but requires the recipient to open it manually.

---

## License

MIT
