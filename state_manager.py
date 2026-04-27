import json
import logging
import re
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS_JSON, GOOGLE_SHEET_ID, SHEET_COLUMNS, State

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

_sheet_cache: gspread.Worksheet | None = None


def _get_sheet() -> gspread.Worksheet:
    global _sheet_cache
    if _sheet_cache is not None:
        return _sheet_cache
    creds_info = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_info, scopes=_SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    _sheet_cache = spreadsheet.sheet1
    return _sheet_cache


def initialise_sheet() -> None:
    """Write column headers on the first row if the sheet is empty.

    Safe to call on every startup — skips silently if headers already exist.
    Logs a warning if row 1 is occupied by unexpected content so the operator
    can investigate without the bot overwriting anything.
    """
    sheet = _get_sheet()
    first_row = sheet.row_values(1)

    if not any(first_row):
        # Sheet is completely empty — write headers
        sheet.update("A1", [SHEET_COLUMNS])
        logger.info("Sheet initialised with %d column headers.", len(SHEET_COLUMNS))
        return

    if first_row[: len(SHEET_COLUMNS)] == SHEET_COLUMNS:
        logger.info("Sheet headers already present — skipping initialisation.")
        return

    logger.warning(
        "Row 1 contains unexpected data and was not overwritten: %s", first_row
    )


def normalise_phone(raw: str) -> str:
    cleaned = re.sub(r"[\s\-()]", "", raw)
    if cleaned.startswith("+"):
        normalised = cleaned
    elif cleaned.startswith("27"):
        normalised = "+" + cleaned
    elif cleaned.startswith("0"):
        normalised = "+27" + cleaned[1:]
    else:
        normalised = "+27" + cleaned
    if not re.match(r"^\+27[6-8]\d{8}$", normalised):
        logger.warning("Phone number may not be valid SA mobile: %s", normalised)
    return normalised


def _row_to_dict(row: list) -> dict:
    padded = row + [""] * (len(SHEET_COLUMNS) - len(row))
    return dict(zip(SHEET_COLUMNS, padded))


def get_lead(phone: str) -> dict | None:
    sheet = _get_sheet()
    all_rows = sheet.get_all_values()
    for idx, row in enumerate(all_rows[1:], start=2):  # skip header
        if row and row[0] == phone:
            lead = _row_to_dict(row)
            lead["_row"] = idx
            return lead
    return None


def upsert_lead(phone: str, data: dict) -> None:
    sheet = _get_sheet()
    existing = get_lead(phone)
    data["timestamp"] = datetime.now(timezone.utc).isoformat()

    if existing:
        row_idx = existing["_row"]
        merged = {**existing, **data}
        merged.pop("_row", None)
        values = [str(merged.get(col, "")) for col in SHEET_COLUMNS]
        sheet.update(f"A{row_idx}", [values])
    else:
        data["phone"] = phone
        values = [str(data.get(col, "")) for col in SHEET_COLUMNS]
        sheet.append_row(values)


def get_all_pending_followups() -> list[dict]:
    sheet = _get_sheet()
    all_rows = sheet.get_all_values()
    results = []
    for idx, row in enumerate(all_rows[1:], start=2):
        lead = _row_to_dict(row)
        lead["_row"] = idx
        if lead.get("state") == State.QUOTE_SENT and lead.get("follow_up_sent", "").upper() != "TRUE":
            results.append(lead)
    return results
