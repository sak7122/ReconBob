"""Inbound Twilio webhook — M1 entry point. functions-framework HTTP function.

Flow A (M1 slice): receipt image -> guardrails -> OCR agent -> save -> WhatsApp confirmation.
Reconciliation / anomaly / smart-prompt loops land in M2.
"""
from __future__ import annotations

import logging
import sys

import functions_framework

from src.agents.ocr_agent import extract_receipt
from src.config import config
from src.guardrails import GuardrailBlock, check_before_processing, media_hash
from src.session import handle_text
from src.store import firestore as store
from src.twilio_client import fetch_media, twiml_reply, validate_signature

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
log = logging.getLogger("reconbob.main")

config.validate()

_TWIML = {"Content-Type": "application/xml"}


def _confirmation(receipt, sender: str, receipt_id: str) -> str:
    """Build the reply and open a session if a decision is pending (one decision at a time)."""
    biz = [li for li in receipt.line_items if li.is_business]
    cat = biz[0].category_guess if biz else "Uncategorized"
    msg = f"Got it! Logged {receipt.currency} {receipt.total:.2f} at {receipt.merchant} for {cat}."

    for idx, li in enumerate(receipt.line_items):
        if not li.is_business:
            store.open_session(sender, "confirm_split",
                               {"receipt_id": receipt_id, "line_index": idx,
                                "description": li.description})
            msg += (f" Noticed {receipt.currency} {li.amount:.2f} for '{li.description}' — "
                    "personal, or business? (reply: business/personal)")
            return msg
    return msg


@functions_framework.http
def webhook(request):
    """Twilio posts form-encoded inbound messages here."""
    params = request.form.to_dict()
    signature = request.headers.get("X-Twilio-Signature", "")
    if config.is_prod and not validate_signature(request.url, params, signature):
        log.warning("rejected unsigned webhook")
        return ("forbidden", 403)

    sender = params.get("From", "")
    if not sender:
        # Not a Twilio inbound message (e.g. browser GET, health check, uptime probe).
        return ("ReconBob webhook is up. POST Twilio messages here.", 200)

    num_media = int(params.get("NumMedia", "0"))

    if num_media == 0:
        body = params.get("Body", "")
        return (twiml_reply(handle_text(sender, body)), 200, _TWIML)

    try:
        check_before_processing(sender)
    except GuardrailBlock as g:
        return (twiml_reply(g.user_message), 200, _TWIML)

    try:
        image, content_type = fetch_media(params["MediaUrl0"])
        mh = media_hash(image)

        existing = store.find_receipt_by_hash(sender, mh)
        if existing:
            return (twiml_reply("Already logged that receipt. ✅"), 200, _TWIML)

        receipt = extract_receipt(image, content_type)
        receipt_id = store.save_receipt(sender, receipt.model_dump(), mh)

        store.log_agent_step(
            {
                "agent": "ocr",
                "phone": sender,
                "receipt_id": receipt_id,
                "autonomous": not receipt.needs_review,
                "confidence": receipt.confidence,
            }
        )

        # If this photo answers a proactive "need receipt" prompt (Flow B), link it to the debit.
        session = store.get_session(sender)
        if session and session.get("pending_action") == "need_receipt":
            txn_id = session["context"]["txn_id"]
            store.link_match(sender, txn_id, receipt_id, "receipt_reply")
            store.clear_session(sender)
            return (twiml_reply(f"Thanks! Matched that to the {receipt.merchant} charge. ✅"),
                    200, _TWIML)

        return (twiml_reply(_confirmation(receipt, sender, receipt_id)), 200, _TWIML)

    except Exception as e:  # don't store garbage; ask for a re-shot
        log.exception("processing failed: %s", e)
        return (
            twiml_reply("Couldn't read that one — can you snap a clearer photo? 📷"),
            200,
            _TWIML,
        )
