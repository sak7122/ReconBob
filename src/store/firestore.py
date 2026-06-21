"""Firestore access: state, receipts, agent logs. Thin wrapper so callers don't touch the client directly."""
from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any, Optional

from google.cloud import firestore

log = logging.getLogger("reconbob.store")

# Named Firestore database (not "(default)") so ReconBob data stays isolated when
# sharing a GCP project with other apps. Must match infra/terraform firestore_database.
_DATABASE = os.getenv("FIRESTORE_DB", "reconbob")

_client: Optional[firestore.Client] = None


def db() -> firestore.Client:
    global _client
    if _client is None:
        _client = firestore.Client(database=_DATABASE)
    return _client


def _today() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%d")


def user_ref(phone: str):
    return db().collection("users").document(phone)


def save_receipt(phone: str, receipt: dict[str, Any], media_hash: str) -> str:
    doc = user_ref(phone).collection("receipts").document()
    doc.set({**receipt, "media_hash": media_hash, "created_at": firestore.SERVER_TIMESTAMP})
    return doc.id


def find_receipt_by_hash(phone: str, media_hash: str) -> Optional[str]:
    """Dedupe guard — return existing receipt id if this exact image was already processed."""
    q = (
        user_ref(phone)
        .collection("receipts")
        .where("media_hash", "==", media_hash)
        .limit(1)
        .stream()
    )
    for d in q:
        return d.id
    return None


def increment_daily_count(phone: str) -> int:
    """Per-user daily receipt counter (resets by date key). Returns new count."""
    ref = user_ref(phone).collection("counters").document(_today())
    ref.set({"receipts": firestore.Increment(1)}, merge=True)
    snap = ref.get()
    return int(snap.to_dict().get("receipts", 0))


def spend_paused() -> bool:
    snap = db().collection("system").document("flags").get()
    return bool(snap.exists and snap.to_dict().get("spend_paused"))


def log_agent_step(payload: dict[str, Any]) -> None:
    """Append agent execution trace — hackathon product evidence + autonomous-ratio metric."""
    db().collection("agent_logs").add({**payload, "ts": firestore.SERVER_TIMESTAMP})


# ---- M2: transactions, matching, memos, sessions ----

def upsert_transaction(phone: str, txn: dict[str, Any]) -> bool:
    """Idempotent ingest keyed by txn_id. Returns True if newly created."""
    ref = user_ref(phone).collection("transactions").document(txn["txn_id"])
    if ref.get().exists:
        return False
    ref.set({**txn, "matched_receipt_id": None, "status": "unmatched",
             "created_at": firestore.SERVER_TIMESTAMP})
    return True


def list_receipts(phone: str) -> list[dict[str, Any]]:
    return [{**d.to_dict(), "id": d.id} for d in user_ref(phone).collection("receipts").stream()]


def list_unmatched_transactions(phone: str) -> list[dict[str, Any]]:
    q = user_ref(phone).collection("transactions").where("status", "==", "unmatched").stream()
    return [{**d.to_dict(), "id": d.id} for d in q]


def link_match(phone: str, txn_id: str, receipt_id: str, method: str) -> None:
    user_ref(phone).collection("transactions").document(txn_id).update(
        {"matched_receipt_id": receipt_id, "status": "matched", "match_method": method}
    )


def create_unverified_memo(phone: str, txn_id: str, note: str) -> str:
    """Flow B fallback: user explains a debit but sends no receipt image.

    Stored as an UNVERIFIED expense memo (clearly flagged) — never a fabricated receipt.
    """
    doc = user_ref(phone).collection("receipts").document()
    doc.set({
        "source": "unverified_memo",
        "verified": False,
        "note": note,
        "linked_txn_id": txn_id,
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    user_ref(phone).collection("transactions").document(txn_id).update(
        {"matched_receipt_id": doc.id, "status": "memo"}
    )
    return doc.id


def set_line_item_business(phone: str, receipt_id: str, index: int, is_business: bool) -> None:
    ref = user_ref(phone).collection("receipts").document(receipt_id)
    data = ref.get().to_dict() or {}
    items = data.get("line_items", [])
    if 0 <= index < len(items):
        items[index]["is_business"] = is_business
        ref.update({"line_items": items})


def open_session(phone: str, pending_action: str, context: dict[str, Any]) -> None:
    user_ref(phone).collection("sessions").document("current").set(
        {"pending_action": pending_action, "context": context,
         "updated_at": firestore.SERVER_TIMESTAMP}
    )


def get_session(phone: str) -> Optional[dict[str, Any]]:
    snap = user_ref(phone).collection("sessions").document("current").get()
    return snap.to_dict() if snap.exists else None


def clear_session(phone: str) -> None:
    user_ref(phone).collection("sessions").document("current").delete()
