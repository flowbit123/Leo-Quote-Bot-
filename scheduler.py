import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

import state_manager
import whatsapp
from config import State

logger = logging.getLogger(__name__)

_FOLLOWUP_DELAY_HOURS = 24
_scheduler: BackgroundScheduler | None = None


def run_followups() -> None:
    logger.info("Running follow-up check...")
    pending = state_manager.get_all_pending_followups()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_FOLLOWUP_DELAY_HOURS)

    for lead in pending:
        ts_raw = lead.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_raw)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            logger.warning("Unparseable timestamp for %s: %s", lead.get("phone"), ts_raw)
            continue

        if ts > cutoff:
            continue  # not old enough yet

        phone = lead.get("phone", "")
        name = lead.get("name", "there")
        trade = lead.get("trade", "your job").capitalize()

        message = (
            f"Hi {name}, just following up on your quote for {trade} 😊\n\n"
            "Still interested? Reply *YES* to confirm or let us know if you have any questions."
        )
        sent = whatsapp.send_message(phone, message)
        if sent:
            state_manager.upsert_lead(phone, {
                "state": State.FOLLOW_UP_SENT,
                "follow_up_sent": "TRUE",
            })
            logger.info("Follow-up sent to %s", phone)
        else:
            logger.error("Failed to send follow-up to %s", phone)


def start_scheduler() -> None:
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(run_followups, "interval", hours=1, id="followup_job")
    _scheduler.start()
    logger.info("Scheduler started — follow-up job runs every 60 minutes")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
