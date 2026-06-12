# cot_notifier.py — Sends one image + text message per commodity via Telegram

import logging
import time
from pathlib import Path

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _send_photo_with_caption(image_path: str, caption: str) -> bool:
    """Sends a photo with caption (Telegram limit: 1024 chars)."""
    if len(caption) > 1024:
        caption = caption[:1020] + "…"

    try:
        img_bytes = open(image_path, "rb").read()
    except OSError as e:
        logger.error(f"Cannot read image {image_path}: {e}")
        return False

    try:
        response = requests.post(
            f"{BASE_URL}/sendPhoto",
            data={
                "chat_id":    TELEGRAM_CHAT_ID,
                "caption":    caption,
                "parse_mode": "Markdown",
            },
            files={"photo": (Path(image_path).name, img_bytes, "image/png")},
            timeout=60,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram request failed for {image_path}: {e}")
        return False


def notify_all(chart_paths: dict[str, str], analyses: dict[str, str]) -> None:
    """
    Sends one Telegram message (image + caption) per commodity.

    Parameters
    ----------
    chart_paths : dict[display_name → file_path]  from cot_chart.generate_charts()
    analyses    : dict[display_name → text]        from cot_analyst.generate_analysis()
    """
    names = list(chart_paths.keys())
    total = len(names)

    for idx, name in enumerate(names, start=1):
        image_path = chart_paths.get(name)
        text       = analyses.get(name, f"*{name}*\n⚠️ Análise indisponível.")

        if not image_path or not Path(image_path).exists():
            logger.error(f"[{idx}/{total}] Image not found for {name}: {image_path}")
            continue

        logger.info(f"[{idx}/{total}] Sending {name}...")
        ok = _send_photo_with_caption(image_path, text)

        if ok:
            logger.info(f"  → Sent successfully.")
        else:
            logger.error(f"  → Failed.")

        # Avoid Telegram rate limit (30 messages/sec, but 1/sec is safe for bots)
        if idx < total:
            time.sleep(1.5)
