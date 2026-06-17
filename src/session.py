"""Conversational state machine for inbound text replies. One open decision per user.

Pure routing over Firestore session state — keeps main.py thin. See agent-orchestration skill.
"""
from __future__ import annotations

import logging

from src.store import firestore as store

log = logging.getLogger("reconbob.session")

_GREETING = "Send me a photo of a receipt and I'll log it. 📸"
_BUSINESS_WORDS = {"business", "yes", "b", "work"}
_PERSONAL_WORDS = {"personal", "no", "p", "me"}


def handle_text(phone: str, body: str) -> str:
    """Resolve the user's text against any open session. Returns the reply body."""
    session = store.get_session(phone)
    if not session:
        log.debug("no session for %s — sending greeting", phone)
        return _GREETING

    pending = session.get("pending_action")
    ctx = session.get("context", {})
    text = body.strip().lower()

    log.info("session dispatch", extra={"phone": phone, "pending": pending})

    if pending == "confirm_split":
        return _resolve_split(phone, ctx, text)
    if pending == "need_receipt":
        return _resolve_need_receipt(phone, ctx, body)

    log.warning("unknown pending_action=%r — clearing stale session", pending)
    store.clear_session(phone)
    return _GREETING


def _resolve_split(phone: str, ctx: dict, text: str) -> str:
    if text in _BUSINESS_WORDS:
        is_business = True
    elif text in _PERSONAL_WORDS:
        is_business = False
    else:
        return "Reply 'business' or 'personal' so I can file it right."

    receipt_id = ctx.get("receipt_id", "")
    line_index = int(ctx.get("line_index", 0))
    updated = store.set_line_item_business(phone, receipt_id, line_index, is_business)
    if not updated:
        log.warning("set_line_item_business: index %d not found in receipt %s", line_index, receipt_id)

    store.clear_session(phone)
    store.log_agent_step({"agent": "orchestrator", "phone": phone, "action": "confirm_split",
                          "autonomous": False, "is_business": is_business})
    log.info("split resolved", extra={"phone": phone, "is_business": is_business,
                                       "receipt_id": receipt_id})
    label = "Tools (business)" if is_business else "personal — left off the books"
    return f"Done — filed '{ctx.get('description', 'that item')}' as {label}. ✅"


def _resolve_need_receipt(phone: str, ctx: dict, body: str) -> str:
    """User explained a debit with text (no image) -> unverified expense memo, clearly flagged.

    If the session has a `queue` of additional orphans, advances to the next one instead of
    clearing the session, so each orphan gets resolved in order.
    """
    txn_id = ctx["txn_id"]
    memo_id = store.create_unverified_memo(phone, txn_id, note=body.strip())
    store.log_agent_step({"agent": "orchestrator", "phone": phone, "action": "memo",
                          "autonomous": False, "txn_id": txn_id, "memo_id": memo_id})
    log.info("memo created", extra={"phone": phone, "txn_id": txn_id, "memo_id": memo_id})

    reply = (f"Got it — noted '{body.strip()}' for the {ctx.get('amount', '')} "
             f"{ctx.get('merchant', '')} charge as an unverified memo for your accountant. ✅")

    queue: list[dict] = list(ctx.get("queue") or [])
    if queue:
        next_ctx = {**queue[0], "queue": queue[1:]}
        store.open_session(phone, "need_receipt", next_ctx)
        nxt = queue[0]
        log.info("advancing to next orphan in queue", extra={"phone": phone,
                                                              "txn_id": nxt["txn_id"]})
        reply += (f"\n\nNext: I also see {nxt['amount']:.2f} at '{nxt['merchant']}'. "
                  "Snap a photo or tell me what it was for?")
    else:
        store.clear_session(phone)

    return reply
