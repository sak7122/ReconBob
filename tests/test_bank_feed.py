"""Bank-feed selection + mock determinism. No vendor SDK, no network."""
import datetime as dt

from src.bank.feed import MockBankFeed, PlaidBankFeed, get_bank_feed


def test_default_is_mock(monkeypatch):
    monkeypatch.delenv("BANK_FEED", raising=False)
    assert isinstance(get_bank_feed(), MockBankFeed)


def test_plaid_selectable(monkeypatch):
    monkeypatch.setenv("BANK_FEED", "plaid")
    assert isinstance(get_bank_feed(), PlaidBankFeed)


def test_mock_is_deterministic_and_has_orphan():
    feed = MockBankFeed(today=dt.date(2026, 6, 16))
    a = feed.sync("whatsapp:+1")
    b = feed.sync("whatsapp:+1")
    assert [t.txn_id for t in a] == [t.txn_id for t in b]  # reproducible for demo
    assert any(t.merchant == "City Electric" for t in a)   # orphan -> Flow B trigger
