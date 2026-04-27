"""
Quick local test — simulates WhatsApp messages hitting the webhook.
Run with: python test_webhook.py
The uvicorn server must be running first: python -m uvicorn main:app --reload
"""

import requests

BASE = "http://127.0.0.1:8000"


def send(text: str, phone: str = "+27821234567", name: str = "Test User"):
    """Simulate an inbound WhatsApp text message."""
    payload = {
        "messages": [
            {
                "from": phone.lstrip("+"),
                "type": "text",
                "text": {"body": text},
            }
        ],
        "contacts": [{"profile": {"name": name}, "wa_id": phone.lstrip("+")}],
    }
    r = requests.post(f"{BASE}/webhook", json=payload)
    print(f">>> {text!r:30s}  →  HTTP {r.status_code}  body={r.json()}")


def tap(button_id: str, phone: str = "+27821234567", name: str = "Test User"):
    """Simulate a button tap."""
    payload = {
        "messages": [
            {
                "from": phone.lstrip("+"),
                "type": "interactive",
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {"id": button_id, "title": ""},
                },
            }
        ],
        "contacts": [{"profile": {"name": name}, "wa_id": phone.lstrip("+")}],
    }
    r = requests.post(f"{BASE}/webhook", json=payload)
    print(f">>> tap({button_id!r:25s})  →  HTTP {r.status_code}  body={r.json()}")


if __name__ == "__main__":
    print("\n── Health check ──────────────────────────────")
    print(requests.get(f"{BASE}/health").json())

    print("\n── Full painting quote flow ──────────────────")
    send("Hi")          # new lead → main menu
    tap("1")            # Get a quote → trade type
    tap("1")            # Painting → surfaces
    tap("3")            # Walls & ceiling
    tap("2")            # No prep needed
    send("2")           # 2 rooms
    send("25")          # 25m²
    tap("YES")          # Accept quote

    print("\n── FAQ / info card ───────────────────────────")
    send("Hi", phone="+27831234568", name="FAQ User")
    tap("2", phone="+27831234568", name="FAQ User")   # Ask a question

    print("\n── Speak to someone ──────────────────────────")
    send("Hi", phone="+27841234569", name="Handoff User")
    tap("3", phone="+27841234569", name="Handoff User")        # Speak to someone
    send("Please call after 3pm", phone="+27841234569")        # their note

    print("\n── Keyword escalation ────────────────────────")
    send("Hi", phone="+27851234560", name="Angry User")
    send("I want to speak to a human", phone="+27851234560")   # triggers escalation
