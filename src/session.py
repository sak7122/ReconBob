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
        return _GREETING

    pending = session.get("pending_action")
    ctx = session.get("context", {})
    text = body.strip().lower()

    if pending == "confirm_split":
        return _resolve_split(phone, ctx, text)
    if pending == "need_receipt":
        return _resolve_need_receipt(phone, ctx, body)

    store.clear_session(phone)
    return _GREETING


def _resolve_split(phone: str, ctx: dict, text: str) -> str:
    if text in _BUSINESS_WORDS:
        is_business = True
    elif text in _PERSONAL_WORDS:
        is_business = False
    else:
        return "Reply 'business' or 'personal' so I can file it right."

    store.set_line_item_business(phone, ctx["receipt_id"], int(ctx["line_index"]), is_business)
    store.clear_session(phone)
    store.log_agent_step({"agent": "orchestrator", "phone": phone, "action": "confirm_split",
                          "autonomous": False, "is_business": is_business})
    label = "Tools (business)" if is_business else "personal — left off the books"
    return f"Done — filed '{ctx.get('description', 'that item')}' as {label}. ✅"


def _resolve_need_receipt(phone: str, ctx: dict, body: str) -> str:
    """User explained a debit with text (no image) -> unverified expense memo, clearly flagged."""
    memo_id = store.create_unverified_memo(phone, ctx["txn_id"], note=body.strip())
    store.clear_session(phone)
    store.log_agent_step({"agent": "orchestrator", "phone": phone, "action": "memo",
                          "autonomous": False, "txn_id": ctx["txn_id"], "memo_id": memo_id})
    return (f"Got it — noted '{body.strip()}' for the {ctx.get('amount', '')} "
            f"{ctx.get('merchant', '')} charge as an unverified memo for your accountant. ✅")
