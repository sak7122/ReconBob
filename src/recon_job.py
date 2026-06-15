"""Proactive reconciliation loop — Cloud Scheduler target (daily). Flow B trigger.

Deploy as a separate Cloud Function (functions-framework target=recon_job), invoked by
Cloud Scheduler. For each active user: reconcile, then WhatsApp-prompt every orphan debit.
"""
from __future__ import annotations

import logging
import sys

import functions_framework

from src.agents.recon_agent import reconcile_user
from src.store import firestore as store
from src.twilio_client import send_message

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
log = logging.getLogger("reconbob.recon_job")


def _prompt_text(txn: dict) -> str:
    return (
        f"Hey, I see a charge for {txn['amount']:.2f} at '{txn['merchant']}' "
        f"on {txn['date']}, but I don't have a receipt for it. "
        "Snap a photo or tell me what it was for?"
    )


def run_for_user(phone: str) -> int:
    orphans = reconcile_user(phone)
    for txn in orphans:
        # one open decision at a time — last orphan wins the current session
        store.open_session(phone, "need_receipt", {"txn_id": txn["txn_id"],
                                                    "amount": txn["amount"],
                                                    "merchant": txn["merchant"]})
        send_message(phone, _prompt_text(txn))  # proactive => approved template in prod
    log.info("recon done", extra={"phone": phone, "orphans": len(orphans)})
    return len(orphans)


@functions_framework.http
def recon_job(request):
    """Scheduler hits this. Iterates active users (M2: all users with a profile)."""
    users = [d.id for d in store.db().collection("users").stream()]
    total = sum(run_for_user(phone) for phone in users)
    return ({"users": len(users), "orphan_prompts": total}, 200)
