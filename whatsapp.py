import logging
import requests
from config import DIALOG360_API_KEY

logger = logging.getLogger(__name__)

_BASE_URL = "https://waba.360dialog.io/v1/messages"
_HEADERS = {
    "D360-API-KEY": DIALOG360_API_KEY,
    "Content-Type": "application/json",
}


def send_message(phone: str, text: str) -> bool:
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }
    try:
        response = requests.post(_BASE_URL, json=payload, headers=_HEADERS, timeout=10)
        if response.ok:
            return True
        logger.error("360dialog error %s: %s", response.status_code, response.text)
        return False
    except requests.RequestException as exc:
        logger.error("Failed to send WhatsApp message to %s: %s", phone, exc)
        return False


def send_buttons(phone: str, text: str, buttons: list[dict]) -> bool:
    """Send an interactive button message. buttons: [{"id": "1", "title": "Label"}]
    WhatsApp allows 1–3 buttons; titles max 20 characters."""
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                    for b in buttons
                ]
            },
        },
    }
    try:
        response = requests.post(_BASE_URL, json=payload, headers=_HEADERS, timeout=10)
        if response.ok:
            return True
        logger.error("360dialog buttons error %s: %s", response.status_code, response.text)
        return False
    except requests.RequestException as exc:
        logger.error("Failed to send WhatsApp buttons to %s: %s", phone, exc)
        return False
