"""Agent 2: bank reconciliation. Syncs the (simulated) feed, matches debits to receipts,
and surfaces orphan debits for the proactive Flow B prompt. See bank-reconciliation skill.

Deterministic matcher does the work; Gemini Flash is an optional alias-disambiguation fallback
for AMBIGUOUS cases only (kept thin so the core stays unit-testable without Vertex).
"""
from __future__ import annotations

import datetime as dt
import logging

from src.bank.feed import Transaction, get_bank_feed
from src.bank.matcher import MatchMethod, match_receipt
from src.store import firestore as store

log = logging.getLogger("reconbob.recon")


def _receipt_total(r: dict) -> float:
    return float(r.get("total") or 0.0)


def reconcile_user(phone: str) -> list[dict]:
    """Sync feed, match each new debit to a stored receipt, return orphan debits (no receipt).

    Orphans are what drive the proactive prompt loop (handled by the caller / scheduler job).
    """
    feed = get_bank_feed()
    txns = feed.sync(phone)

    receipts = [r for r in store.list_receipts(phone) if r.get("source") != "unverified_memo"]
    orphans: list[dict] = []

    for t in txns:
        newly = store.upsert_transaction(phone, _txn_dict(t))
        if not newly:
            continue  # idempotent: already ingested

        result = _best_match(t, receipts)
        if result and result.method is MatchMethod.AUTO:
            rid = result.best_receipt_id
            store.link_match(phone, t.txn_id, rid, "auto")
            store.log_agent_step({"agent": "recon", "phone": phone, "txn_id": t.txn_id,
                                  "autonomous": True, "method": "auto", "receipt_id": rid})
        else:
            method = result.method.value if result else "unmatched"
            store.log_agent_step({"agent": "recon", "phone": phone, "txn_id": t.txn_id,
                                  "autonomous": False, "method": method})
            orphans.append(_txn_dict(t))
    return orphans


def _txn_dict(t: Transaction) -> dict:
    return {"txn_id": t.txn_id, "date": t.date.isoformat(), "amount": t.amount,
            "merchant": t.merchant, "raw_name": t.raw_name}


class _Match:
    def __init__(self, method: MatchMethod, best_receipt_id: str | None):
        self.method = method
        self.best_receipt_id = best_receipt_id


def _best_match(t: Transaction, receipts: list[dict]) -> _Match | None:
    """Match a debit against the user's receipts (inverse of match_receipt's framing).

    Score each receipt as if matching it to this single txn; pick the best.
    """
    best_id, best_method, best_score = None, MatchMethod.UNMATCHED, 0.0
    for r in receipts:
        res = match_receipt(_receipt_total(r), r.get("merchant", ""), r.get("date", ""), [t])
        if res.best and res.best.score > best_score:
            best_score, best_id, best_method = res.best.score, r["id"], res.method
    if best_id is None:
        return None
    return _Match(best_method, best_id if best_method is MatchMethod.AUTO else None)
