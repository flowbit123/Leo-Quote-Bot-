from config import CONTRACTOR_NAME, CONTRACTOR_PROFILE

_MENU_BUTTONS = [
    {"id": "1", "title": "Get a quote"},
    {"id": "2", "title": "More questions"},
    {"id": "3", "title": "Speak to someone"},
]


def ask_faq(question: str = "") -> dict:
    p = CONTRACTOR_PROFILE
    body = (
        f"Here's some info about {CONTRACTOR_NAME}:\n\n"
        f"🔨 Services: {p['trades']}\n"
        f"📍 Areas: {p['areas_covered']}\n"
        f"🕐 Hours: {p['working_hours']}\n"
        f"💳 Payment: {p['payment_methods']}\n"
        f"✅ Guarantee: {p['guarantee']}\n"
        f"⏱ Turnaround: {p['turnaround']}\n\n"
        "Can I help you with anything else?"
    )
    return {"type": "buttons", "body": body, "buttons": _MENU_BUTTONS}
