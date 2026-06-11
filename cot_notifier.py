# cot_notifier.py — Sends the chart image and analysis text via Telegram Bot API

import logging
from pathlib import Path

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _send_photo(image_path: str, caption: str = "") -> bool:
    """
    Send a photo with an optional short caption (≤1024 chars).
    For longer text, send the image first then a separate message.
    """
    url = f"{BASE_URL}/sendPhoto"
    try:
        with open(image_path, "rb") as img:
            response = requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption[:1024]},
                files={"photo": img},
                timeout=60,
            )
        response.raise_for_status()
        logger.info("Photo sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to send photo: {e}")
        return False


def _send_message(text: str) -> bool:
    """
    Send a plain text message with Markdown parse mode.
    Automatically splits messages > 4096 chars (Telegram limit).
    """
    url    = f"{BASE_URL}/sendMessage"
    chunks = _split_message(text, max_len=4096)

    for chunk in chunks:
        try:
            response = requests.post(
                url,
                json={
                    "chat_id":    TELEGRAM_CHAT_ID,
                    "text":       chunk,
                    "parse_mode": "Markdown",
                },
                timeout=30,
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send message chunk: {e}")
            return False

    logger.info(f"Message sent ({len(chunks)} chunk(s)).")
    return True


def _split_message(text: str, max_len: int = 4096) -> list[str]:
    """Split long text at paragraph boundaries to stay within Telegram limits."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""
    for paragraph in text.split("\n\n"):
        block = paragraph + "\n\n"
        if len(current) + len(block) > max_len:
            if current:
                chunks.append(current.rstrip())
            current = block
        else:
            current += block

    if current:
        chunks.append(current.rstrip())

    return chunks or [text[:max_len]]


def notify(image_path: str, analysis_text: str) -> bool:
    """
    Full notification sequence:
      1. Send the chart image (no caption — image speaks for itself)
      2. Send the analysis text as a separate message

    Returns True if both sends succeeded.
    """
    if not Path(image_path).exists():
        logger.error(f"Image file not found: {image_path}")
        return False

    ok_photo   = _send_photo(image_path)
    ok_message = _send_message(analysis_text)

    return ok_photo and ok_message
