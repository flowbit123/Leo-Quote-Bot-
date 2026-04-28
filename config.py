import os
from dotenv import load_dotenv

load_dotenv()

DIALOG360_API_KEY = os.getenv("D360_API_KEY", "")
WHATSAPP_NUMBER = os.getenv("D360_WHATSAPP_NUMBER", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
CONTRACTOR_NAME = os.getenv("CONTRACTOR_NAME", "Your Contractor")
CONTRACTOR_PHONE = os.getenv("CONTRACTOR_PHONE", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


class State:
    NEW = "NEW"
    AWAITING_MENU_SELECTION = "AWAITING_MENU_SELECTION"
    AWAITING_TRADE_TYPE = "AWAITING_TRADE_TYPE"
    AWAITING_JOB_DETAILS = "AWAITING_JOB_DETAILS"
    AWAITING_DIMENSIONS = "AWAITING_DIMENSIONS"
    AWAITING_DIMENSION_METHOD = "AWAITING_DIMENSION_METHOD"
    AWAITING_HANDOFF_MESSAGE = "AWAITING_HANDOFF_MESSAGE"
    QUOTE_SENT = "QUOTE_SENT"
    ACCEPTED = "ACCEPTED"
    FOLLOW_UP_SENT = "FOLLOW_UP_SENT"
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"


SHEET_COLUMNS = [
    "phone",
    "name",
    "trade",
    "job_details",
    "area_m2",
    "quote_amount",
    "state",
    "timestamp",
    "follow_up_sent",
    "accepted",
    "escalated",
]

CONTRACTOR_PROFILE = {
    "areas_covered": "Centurion, Pretoria East, Midrand, Faerie Glen",
    "working_hours": "Monday to Friday 7am - 5pm, Saturday 8am - 1pm",
    "payment_methods": "EFT, cash",
    "guarantee": "All work guaranteed for 6 months",
    "turnaround": "Most jobs quoted and scheduled within 48 hours",
    "trades": "Painting, tiling, general building work",
}

PRICING_CONFIG = {
    "painting": {
        "walls_per_m2": 45,
        "ceiling_per_m2": 35,
        "prep_per_m2": 20,
        "size_guide": {
            "small": 15,
            "medium": 25,
            "large": 45,
        },
    },
    "tiling": {
        "labour_per_m2": 120,
        "removal_per_m2": 60,
        "size_guide": {
            "small": 10,
            "medium": 20,
            "large": 35,
        },
    },
    "building": {
        "brickwork_per_m2": 280,
        "plastering_per_m2": 95,
        "size_guide": {
            "small": 10,
            "medium": 25,
            "large": 50,
        },
    },
}
