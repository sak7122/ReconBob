"""Matcher tests — pure logic, no GCP/LLM. Covers window, tolerance, auto/ambiguous/unmatched."""
import datetime as dt

from src.bank.feed import Transaction
from src.bank.matcher import MatchMethod, match_receipt

D = dt.date(2026, 6, 16)


def _txn(tid, amount, merchant, raw, day_offset=0):
    return Transaction(tid, D + dt.timedelta(days=day_offset), amount, merchant, raw)


def test_auto_match_clean():
    txns = [_txn("t1", 143.50, "Home Depot", "HOMEDEPOT #4112", -1)]
    r = match_receipt(143.50, "Home Depot", "2026-06-16", txns)
    assert r.method is MatchMethod.AUTO
    assert r.best.txn.txn_id == "t1"


def test_unmatched_outside_date_window():
    txns = [_txn("t1", 143.50, "Home Depot", "HOMEDEPOT", -10)]
    r = match_receipt(143.50, "Home Depot", "2026-06-16", txns)
    assert r.method is MatchMethod.UNMATCHED


def test_unmatched_amount_out_of_tolerance():
    txns = [_txn("t1", 999.00, "Home Depot", "HOMEDEPOT", 0)]
    r = match_receipt(143.50, "Home Depot", "2026-06-16", txns)
    assert r.method is MatchMethod.UNMATCHED


def test_alias_raw_name_still_scores():
    # receipt says "City Electric", bank raw is "CITY ELECTRIC SUPPLY"
    txns = [_txn("t1", 320.00, "City Electric", "CITY ELECTRIC SUPPLY", -1)]
    r = match_receipt(320.00, "City Electric", "2026-06-16", txns)
    assert r.method is MatchMethod.AUTO


def test_ambiguous_two_close_candidates():
    txns = [
        _txn("t1", 143.50, "Home Depot", "HOMEDEPOT", 0),
        _txn("t2", 143.50, "Home Depot", "HOMEDEPOT", -1),
    ]
    r = match_receipt(143.50, "Home Depot", "2026-06-16", txns)
    assert r.method is MatchMethod.AMBIGUOUS
    assert len(r.candidates) == 2


def test_tiebreak_prefers_most_recent_transaction():
    # Both transactions are identical except date; more recent (day_offset=0) should rank first.
    txns = [
        _txn("older", 143.50, "Home Depot", "HOMEDEPOT #4112", -3),
        _txn("newer", 143.50, "Home Depot", "HOMEDEPOT #4112", 0),
    ]
    r = match_receipt(143.50, "Home Depot", "2026-06-16", txns)
    # When scores differ (due to date proximity), newer wins and should be best candidate.
    assert r.candidates[0].txn.txn_id == "newer"
