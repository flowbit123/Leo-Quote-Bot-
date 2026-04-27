import json
import logging

import state_manager
import quote_engine
import faq
import whatsapp
from config import (
    CONTRACTOR_NAME,
    CONTRACTOR_PHONE,
    CONTRACTOR_PROFILE,
    PRICING_CONFIG,
    State,
)

logger = logging.getLogger(__name__)

# ── Button helpers ─────────────────────────────────────────────────────────────

def _btn(body: str, buttons: list[tuple[str, str]]) -> dict:
    """Build a button response dict. buttons = [(id, title), ...]"""
    return {
        "type": "buttons",
        "body": body,
        "buttons": [{"id": bid, "title": title} for bid, title in buttons],
    }

def _retry(msg) -> dict | str:
    """Re-send a prompt prefixed with an apology. Works on both strings and button dicts."""
    prefix = "Sorry, I didn't catch that! 🙏\n\n"
    if isinstance(msg, dict) and msg.get("type") == "buttons":
        return _btn(prefix + msg["body"], [(b["id"], b["title"]) for b in msg["buttons"]])
    return prefix + str(msg)

# ── Prompt functions ───────────────────────────────────────────────────────────

def _main_menu(name: str) -> dict:
    return _btn(
        f"Hi {name}! Welcome to {CONTRACTOR_NAME} 👋\n\nHow can we help you today?",
        [("1", "Get a quote"), ("2", "Ask a question"), ("3", "Speak to someone")],
    )

def _trade_type_prompt() -> dict:
    return _btn(
        "What type of work do you need a quote for?",
        [("1", "Painting"), ("2", "Tiling"), ("3", "Building work")],
    )

def _painting_q1() -> dict:
    return _btn(
        "What needs painting?",
        [("1", "Walls only"), ("2", "Ceiling only"), ("3", "Walls & ceiling")],
    )

def _painting_q2() -> dict:
    return _btn(
        "Any prep work needed? (peeling paint, cracks or damp)",
        [("1", "Yes - prep needed"), ("2", "No - looks good")],
    )

_PAINTING_Q3 = "How many rooms? (reply with a number e.g. *2*)"

def _tiling_q1() -> dict:
    return _btn(
        "What type of tiling?",
        [("1", "Floor tiling"), ("2", "Wall tiling"), ("3", "Floor & wall")],
    )

def _tiling_q2() -> dict:
    return _btn(
        "Is there existing tiling to remove?",
        [("1", "Yes - remove tiles"), ("2", "No - fresh surface")],
    )

_TILING_Q3 = "How many rooms or areas? (reply with a number e.g. *2*)"

def _building_q1() -> dict:
    return _btn(
        "What type of building work?",
        [("1", "Brickwork"), ("2", "Plastering"), ("3", "Both")],
    )

_BUILDING_Q2 = "Is this new work or a repair? (please type your answer)"

def _dimensions_q() -> dict:
    return _btn(
        "Do you know the size of the area in m²?\n\n"
        "If yes, just type the number (e.g. *20*)\n"
        "If not, tap the button below 👇",
        [("NO", "Not sure")],
    )

def _dimension_method_prompt(trade: str) -> dict:
    cfg = PRICING_CONFIG[trade]
    size_guide = cfg["size_guide"]
    if trade == "painting":
        rate = cfg["walls_per_m2"]
    elif trade == "tiling":
        rate = cfg["labour_per_m2"]
    else:
        rate = cfg.get("brickwork_per_m2", cfg.get("plastering_per_m2", 0))
    examples = " | ".join(f"{m}m²=R{int(m * rate):,}" for m in [20, 30, 50])
    body = (
        f"No problem! Choose an option or type your own m².\n\n"
        f"Size guide:\n"
        f"  Small (~{size_guide['small']}m²) — bedroom\n"
        f"  Medium (~{size_guide['medium']}m²) — lounge\n"
        f"  Large (~{size_guide['large']}m²) — open plan\n\n"
        f"Rate: R{rate}/m²  |  {examples}"
    )
    return _btn(body, [("1", "Pick a size"), ("2", "See rate / m2")])

def _size_picker_prompt(trade: str) -> dict:
    cfg = PRICING_CONFIG[trade]["size_guide"]
    return _btn(
        "Which size best describes the area?",
        [
            ("1", f"Small (~{cfg['small']}m2)"),
            ("2", f"Medium (~{cfg['medium']}m2)"),
            ("3", f"Large (~{cfg['large']}m2)"),
        ],
    )

def _format_quote_message(name: str, trade: str, quote: dict, area_m2: float) -> dict:
    lines = [f"Hi {name}, here is your labour quote:\n"]
    lines.append(f"Job: {quote['summary']}")
    lines.append(f"Area: {area_m2}m²\n")
    for item in quote["line_items"]:
        lines.append(f"- {item['label']}: R{int(item['amount']):,}")
    lines.append(f"\n*Total labour: R{int(quote['total']):,}*")
    lines.append("(Materials excluded)\n")
    lines.append("_Quote based on dimensions provided.\nFinal price confirmed on site if needed._")
    return _btn("\n".join(lines), [("YES", "Accept quote")])

# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_int(text: str) -> int | None:
    try:
        return int(text.strip())
    except ValueError:
        return None

def _parse_float(text: str) -> float | None:
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None

def _load_job_details(lead: dict) -> dict:
    raw = lead.get("job_details", "")
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return {}

# ── State handlers ─────────────────────────────────────────────────────────────

def _handle_trade_selection(name: str, text: str) -> tuple[dict, dict | str]:
    choice = _parse_int(text)
    trade_map = {1: "painting", 2: "tiling", 3: "building"}
    if choice not in trade_map:
        return {}, _retry(_trade_type_prompt())
    trade = trade_map[choice]
    updates = {"trade": trade, "state": State.AWAITING_JOB_DETAILS, "job_details": json.dumps({"step": 1})}
    reply = {"painting": _painting_q1, "tiling": _tiling_q1, "building": _building_q1}[trade]()
    return updates, reply


def _handle_job_details_painting(job: dict, text: str) -> tuple[dict | None, dict | str]:
    step = job.get("step", 1)

    if step == 1:
        choice = _parse_int(text)
        surfaces_map = {1: ["walls"], 2: ["ceiling"], 3: ["walls", "ceiling"]}
        if choice not in surfaces_map:
            return None, _retry(_painting_q1())
        job["surfaces"] = surfaces_map[choice]
        job["step"] = 2
        return {"job_details": json.dumps(job)}, _painting_q2()

    if step == 2:
        choice = _parse_int(text)
        if choice not in (1, 2):
            return None, _retry(_painting_q2())
        job["prep"] = choice == 1
        job["step"] = 3
        return {"job_details": json.dumps(job)}, _PAINTING_Q3

    if step == 3:
        rooms = _parse_int(text)
        if not rooms or rooms < 1:
            return None, "Please reply with the number of rooms (e.g. *2*)"
        job["rooms"] = rooms
        return {"job_details": json.dumps(job), "state": State.AWAITING_DIMENSIONS}, _dimensions_q()

    return None, _retry(_painting_q1())


def _handle_job_details_tiling(job: dict, text: str) -> tuple[dict | None, dict | str]:
    step = job.get("step", 1)

    if step == 1:
        choice = _parse_int(text)
        type_map = {1: "floor", 2: "wall", 3: "floor and wall"}
        if choice not in type_map:
            return None, _retry(_tiling_q1())
        job["tiling_type"] = type_map[choice]
        job["step"] = 2
        return {"job_details": json.dumps(job)}, _tiling_q2()

    if step == 2:
        choice = _parse_int(text)
        if choice not in (1, 2):
            return None, _retry(_tiling_q2())
        job["removal"] = choice == 1
        job["step"] = 3
        return {"job_details": json.dumps(job)}, _TILING_Q3

    if step == 3:
        rooms = _parse_int(text)
        if not rooms or rooms < 1:
            return None, "Please reply with the number of rooms or areas (e.g. *2*)"
        job["rooms"] = rooms
        return {"job_details": json.dumps(job), "state": State.AWAITING_DIMENSIONS}, _dimensions_q()

    return None, _retry(_tiling_q1())


def _handle_job_details_building(job: dict, text: str) -> tuple[dict | None, dict | str]:
    step = job.get("step", 1)

    if step == 1:
        choice = _parse_int(text)
        work_map = {1: ["brickwork"], 2: ["plastering"], 3: ["brickwork", "plastering"]}
        if choice not in work_map:
            return None, _retry(_building_q1())
        job["work_type"] = work_map[choice]
        job["step"] = 2
        return {"job_details": json.dumps(job)}, _BUILDING_Q2

    if step == 2:
        if not text.strip():
            return None, _BUILDING_Q2
        job["job_nature"] = text.strip()
        return {"job_details": json.dumps(job), "state": State.AWAITING_DIMENSIONS}, _dimensions_q()

    return None, _retry(_building_q1())


def _handle_job_details(lead: dict, text: str) -> tuple[dict, dict | str]:
    trade = lead.get("trade", "")
    job = _load_job_details(lead)
    handlers = {
        "painting": _handle_job_details_painting,
        "tiling": _handle_job_details_tiling,
        "building": _handle_job_details_building,
    }
    handler = handlers.get(trade)
    if not handler:
        return {"state": State.AWAITING_TRADE_TYPE}, _retry(_trade_type_prompt())
    updates, reply = handler(job, text)
    return (updates or {}), reply


def _handle_dimensions(lead: dict, text: str) -> tuple[dict, dict | str]:
    trade = lead.get("trade", "")
    t = text.strip().lower()

    if t in ("no", "nope", "n", "not sure", "unsure", "don't know", "dont know"):
        return {"state": State.AWAITING_DIMENSION_METHOD}, _dimension_method_prompt(trade)

    area = _parse_float(text)
    if area and area > 0:
        return _finalise_quote(lead, area)

    return {}, _retry(_dimensions_q())


def _handle_dimension_method(lead: dict, text: str) -> tuple[dict, dict | str]:
    trade = lead.get("trade", "")
    t = text.strip()
    choice = _parse_int(t)

    if choice == 1:
        return {"job_details": _inject_pending_size(lead)}, _size_picker_prompt(trade)

    if choice == 2:
        cfg = PRICING_CONFIG[trade]
        if trade == "painting":
            rate = cfg["walls_per_m2"]
        elif trade == "tiling":
            rate = cfg["labour_per_m2"]
        else:
            rate = cfg.get("brickwork_per_m2", cfg.get("plastering_per_m2", 0))
        reply = (
            f"Our rate is R{rate} per m².\n\n"
            "Examples:\n"
            + "\n".join(f"  {m}m² = R{int(m * rate):,}" for m in [10, 20, 30, 50])
            + "\n\nJust reply with your estimated m² to get your quote."
        )
        return {"state": State.AWAITING_DIMENSIONS}, reply

    size_map = {"1": "small", "2": "medium", "3": "large",
                "small": "small", "medium": "medium", "large": "large"}
    size_label = size_map.get(t.lower())
    if size_label:
        area = quote_engine.size_from_label(trade, size_label)
        return _finalise_quote(lead, area)

    area = _parse_float(t)
    if area and area > 0:
        return _finalise_quote(lead, area)

    return {}, _retry(_dimension_method_prompt(trade))


def _inject_pending_size(lead: dict) -> str:
    job = _load_job_details(lead)
    job["_awaiting_size_pick"] = True
    return json.dumps(job)


def _finalise_quote(lead: dict, area_m2: float) -> tuple[dict, dict | str]:
    trade = lead.get("trade", "")
    name = lead.get("name", "there")
    job = _load_job_details(lead)
    job.pop("_awaiting_size_pick", None)

    try:
        result = quote_engine.calculate_quote(trade, job, area_m2)
    except Exception as exc:
        logger.error("Quote calculation failed: %s", exc)
        return {"state": State.AWAITING_MENU_SELECTION}, _main_menu(name)

    reply = _format_quote_message(name, trade, result, area_m2)
    updates = {
        "area_m2": str(area_m2),
        "quote_amount": str(int(result["total"])),
        "state": State.QUOTE_SENT,
        "follow_up_sent": "FALSE",
    }
    return updates, reply


def _handle_quote_response(lead: dict, text: str) -> tuple[dict, dict | str]:
    t = text.strip().lower()
    name = lead.get("name", "there")
    if t in ("yes", "y", "ja", "yep", "yup", "ok", "okay", "sure", "accept", "confirmed"):
        updates = {"state": State.ACCEPTED, "accepted": "TRUE"}
        return updates, f"Great! We will be in touch shortly to confirm your booking. Thank you {name} 👍"
    trade = lead.get("trade", "").capitalize() or "your job"
    return {}, _btn(
        f"Would you like to accept your {trade} quote? 😊\nOr call us directly to discuss.",
        [("YES", "Accept quote")],
    )


# ── Escalation ────────────────────────────────────────────────────────────────

_ESCALATION_KEYWORDS = {
    "agent", "human", "person", "speak to someone", "call me",
    "help", "stop", "cancel", "operator", "representative",
}

def _is_escalation(text: str) -> bool:
    t = text.strip().lower()
    return any(kw in t for kw in _ESCALATION_KEYWORDS)


def _do_escalate(lead: dict, phone: str, name: str, text: str) -> tuple[dict, str]:
    hours = CONTRACTOR_PROFILE.get("working_hours", "during business hours")
    client_reply = (
        f"No problem, I'm connecting you to someone from our team now 🙏\n\n"
        f"They will be in touch shortly. Our working hours are {hours}."
    )
    alert = (
        f"🚨 Escalation Request\n"
        f"Client: {name}\n"
        f"Phone: {phone}\n"
        f"Was at stage: {lead.get('state', 'unknown')}\n"
        f"Last message: {text}\n\n"
        "Please follow up directly."
    )
    if CONTRACTOR_PHONE:
        whatsapp.send_message(CONTRACTOR_PHONE, alert)
    return {"state": State.ESCALATED, "escalated": "TRUE"}, client_reply


# ── Menu selection ─────────────────────────────────────────────────────────────

def _handle_menu_selection(lead: dict, name: str, text: str) -> tuple[dict, dict | str]:
    choice = _parse_int(text)
    if choice == 1:
        return {"state": State.AWAITING_TRADE_TYPE}, _trade_type_prompt()
    if choice == 2:
        return {}, faq.ask_faq()
    if choice == 3:
        hours = CONTRACTOR_PROFILE.get("working_hours", "during business hours")
        reply = (
            "No problem! Someone from our team will be in touch with you shortly 🙏\n\n"
            f"Our working hours are {hours}.\n\n"
            "Is there anything specific you'd like them to know before they call?"
        )
        return {"state": State.AWAITING_HANDOFF_MESSAGE}, reply
    return {}, _retry(_main_menu(name))


# ── Handoff message collection ─────────────────────────────────────────────────

def _handle_handoff_message(lead: dict, phone: str, name: str, text: str) -> tuple[dict, str]:
    note = text.strip()
    if note.lower() in ("no", "nothing", "n", "nope", "none", "no thanks"):
        note = "No specific message"
    alert = (
        f"📞 Contact Request\n"
        f"Client: {name}\n"
        f"Phone: {phone}\n"
        f"Message: {note}\n\n"
        "Please follow up directly."
    )
    if CONTRACTOR_PHONE:
        whatsapp.send_message(CONTRACTOR_PHONE, alert)
    return {"state": State.ESCALATED, "escalated": "TRUE"}, "Got it! We'll be in touch soon 👍"


# ── Main entry point ───────────────────────────────────────────────────────────

def handle_message(phone: str, name: str, text: str) -> dict | str:
    lead = state_manager.get_lead(phone)

    if lead is None:
        lead = {col: "" for col in state_manager.SHEET_COLUMNS}
        lead["phone"] = phone
        lead["name"] = name
        lead["state"] = State.NEW

    if name and name != "there":
        lead["name"] = name

    current_state = lead.get("state", State.NEW)

    # Keyword escalation — runs before all state logic
    if current_state not in (State.ESCALATED, State.ACCEPTED, State.CLOSED):
        if _is_escalation(text):
            updates, reply = _do_escalate(lead, phone, name, text)
            state_manager.upsert_lead(phone, updates)
            return reply

    if current_state == State.NEW:
        state_manager.upsert_lead(phone, {"name": name, "state": State.AWAITING_MENU_SELECTION})
        return _main_menu(name)

    if current_state == State.AWAITING_MENU_SELECTION:
        choice = _parse_int(text.strip())
        if choice not in (1, 2, 3):
            # Free-text at menu → show info card
            return faq.ask_faq()
        updates, reply = _handle_menu_selection(lead, name, text)

    elif current_state == State.AWAITING_TRADE_TYPE:
        updates, reply = _handle_trade_selection(name, text)

    elif current_state == State.AWAITING_JOB_DETAILS:
        updates, reply = _handle_job_details(lead, text)

    elif current_state == State.AWAITING_DIMENSIONS:
        updates, reply = _handle_dimensions(lead, text)

    elif current_state == State.AWAITING_DIMENSION_METHOD:
        updates, reply = _handle_dimension_method(lead, text)

    elif current_state == State.AWAITING_HANDOFF_MESSAGE:
        updates, reply = _handle_handoff_message(lead, phone, name, text)

    elif current_state in (State.QUOTE_SENT, State.FOLLOW_UP_SENT):
        updates, reply = _handle_quote_response(lead, text)

    elif current_state == State.ESCALATED:
        return ""  # silent while human handles the lead

    elif current_state == State.ACCEPTED:
        reply = "Your booking is already confirmed 👍 We'll be in touch soon!"
        updates = {}

    elif current_state == State.CLOSED:
        reply = "This quote has been closed. Feel free to message us anytime for a new quote!"
        updates = {}

    else:
        updates = {"state": State.AWAITING_MENU_SELECTION}
        reply = _main_menu(name)

    if updates:
        state_manager.upsert_lead(phone, updates)

    return reply
