"""Reconciliation agent tests. Bank feed + store faked — no Vertex, no Firestore."""
import datetime as dt

import src.agents.recon_agent as recon
from src.bank.feed import Transaction
from src.bank.matcher import MatchMethod

D = dt.date(2026, 6, 16)


def test_best_match_picks_auto():
    t = Transaction("t1", D, 143.50, "Home Depot", "HOMEDEPOT #4112")
    receipts = [{"id": "r1", "total": 143.50, "merchant": "Home Depot", "date": "2026-06-16"}]
    m = recon._best_match(t, receipts)
    assert m.method is MatchMethod.AUTO
    assert m.best_receipt_id == "r1"


def test_best_match_none_when_no_receipts():
    t = Transaction("t1", D, 143.50, "Home Depot", "HOMEDEPOT")
    assert recon._best_match(t, []) is None


class FakeStore:
    def __init__(self, receipts):
        self._receipts = receipts
        self.links = []
        self.logs = []

    def list_receipts(self, phone):
        return self._receipts

    def upsert_transaction(self, phone, txn):
        return True  # all new

    def link_match(self, phone, txn_id, rid, method):
        self.links.append((txn_id, rid, method))

    def log_agent_step(self, payload):
        self.logs.append(payload)


def test_reconcile_links_match_and_returns_orphan(monkeypatch):
    # MockBankFeed dates its debits relative to today (today-1), so the receipt must
    # be clock-relative too — a hardcoded date drifts out of the matcher's ±3-day window.
    txn_date = dt.date.today() - dt.timedelta(days=1)
    receipts = [{"id": "r1", "total": 143.50, "merchant": "Home Depot", "date": txn_date.isoformat()}]
    fake = FakeStore(receipts)
    monkeypatch.setattr(recon, "store", fake)

    orphans = recon.reconcile_user("whatsapp:+1")

    assert ("mock-whatsapp:+1-1", "r1", "auto") in fake.links     # Home Depot auto-matched
    assert any(o["merchant"] == "City Electric" for o in orphans)  # orphan surfaced for Flow B
    assert all(o["merchant"] != "Home Depot" for o in orphans)
