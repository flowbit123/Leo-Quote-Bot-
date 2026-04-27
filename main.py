import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import conversation
import whatsapp
import scheduler
from state_manager import normalise_phone, initialise_sheet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialise_sheet()
    scheduler.start_scheduler()
    yield
    scheduler.stop_scheduler()


app = FastAPI(title="WhatsApp Quote Bot", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "ok"})

    messages = body.get("messages", [])
    contacts = body.get("contacts", [])

    if not messages:
        return JSONResponse({"status": "ok"})

    for message in messages:
        msg_type = message.get("type")

        if msg_type == "text":
            text = message.get("text", {}).get("body", "").strip()
        elif msg_type == "interactive":
            # Button tap — extract the button ID as the text input
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                text = interactive["button_reply"]["id"]
            else:
                continue
        else:
            continue

        raw_phone = message.get("from", "")
        if not raw_phone or not text:
            continue

        try:
            phone = normalise_phone(raw_phone)
        except Exception as exc:
            logger.warning("Could not normalise phone %s: %s", raw_phone, exc)
            continue

        name = "there"
        if contacts:
            try:
                name = contacts[0]["profile"]["name"]
            except (KeyError, IndexError, TypeError):
                pass

        try:
            reply = conversation.handle_message(phone, name, text)
            if isinstance(reply, dict) and reply.get("type") == "buttons":
                whatsapp.send_buttons(phone, reply["body"], reply["buttons"])
            elif reply:
                body = reply if isinstance(reply, str) else reply.get("body", "")
                if body:
                    whatsapp.send_message(phone, body)
        except Exception as exc:
            logger.error("Error handling message from %s: %s", phone, exc)

    return JSONResponse({"status": "ok"})
