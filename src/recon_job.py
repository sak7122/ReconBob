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
    """Reconcile one user; return number of orphan prompts sent. Never raises."""
    try:
        orphans = reconcile_user(phone)
    except Exception:
        log.exception("reconcile_user failed", extra={"phone": phone})
        return 0

    if not orphans:
        return 0

    # Queue all orphans in a single session so answers stay in order.
    # The first orphan becomes the active context; the rest sit in `queue`.
    first, *rest = orphans
    ctx = {
        "txn_id": first["txn_id"],
        "amount": first["amount"],
        "merchant": first["merchant"],
        "queue": [{"txn_id": t["txn_id"], "amount": t["amount"], "merchant": t["merchant"]}
                  for t in rest],
    }
    store.open_session(phone, "need_receipt", ctx)

    # Send a WhatsApp message for every orphan so the user sees them all at once.
    for txn in orphans:
        try:
            send_message(phone, _prompt_text(txn))
        except Exception:
            log.warning("send_message failed for orphan", extra={"phone": phone,
                                                                   "txn_id": txn["txn_id"]})

    log.info("recon done", extra={"phone": phone, "orphans": len(orphans)})
    return len(orphans)


@functions_framework.http
def recon_job(request):
    """Scheduler hits this. Iterates active users (M2: all users with a profile)."""
    users = [d.id for d in store.db().collection("users").stream()]
    total = sum(run_for_user(phone) for phone in users)
    return ({"users": len(users), "orphan_prompts": total}, 200)
