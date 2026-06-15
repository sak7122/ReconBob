"""Provider-agnostic bank feed. Matching logic depends only on this interface, never a vendor SDK.

Plaid does not onboard India-based entities, so MockBankFeed is the default for dev/beta/demo.
PlaidBankFeed is an optional later impl behind the same interface. See bank-reconciliation skill.
"""
from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Transaction:
    txn_id: str          # stable id from the provider (idempotent ingest)
    date: dt.date
    amount: float        # positive = debit
    merchant: str
    raw_name: str        # provider's raw descriptor, e.g. "HOMEDEPOT #4112"


class BankFeed(Protocol):
    def sync(self, user_phone: str) -> list[Transaction]:
        """Return new debits for the user since the last sync. Must be idempotent by txn_id."""
        ...


class MockBankFeed:
    """Deterministic fake feed for dev / beta / hackathon demo. No signup, no cost.

    Emits a mix of debits that match seeded receipts and 'orphan' debits with no receipt,
    so the proactive reconciliation loop (Flow B) is demonstrable.
    """

    def __init__(self, today: dt.date | None = None) -> None:
        self._today = today or dt.date.today()

    def sync(self, user_phone: str) -> list[Transaction]:
        d = self._today
        return [
            Transaction(f"mock-{user_phone}-1", d - dt.timedelta(days=1), 143.50,
                        "Home Depot", "HOMEDEPOT #4112"),
            # orphan debit -> should trigger a 'missing receipt' WhatsApp prompt
            Transaction(f"mock-{user_phone}-2", d - dt.timedelta(days=1), 320.00,
                        "City Electric", "CITY ELECTRIC SUPPLY"),
        ]


class PlaidBankFeed:
    """Optional real-feed impl. Only usable with a US/EU/CA Plaid entity. Not used in India dev."""

    def sync(self, user_phone: str) -> list[Transaction]:  # pragma: no cover
        raise NotImplementedError("PlaidBankFeed not wired — set BANK_FEED=mock for dev")


def get_bank_feed() -> BankFeed:
    provider = os.getenv("BANK_FEED", "mock").lower()
    if provider == "plaid":
        return PlaidBankFeed()
    return MockBankFeed()
