"""Deterministic receipt<->transaction matching. Pure logic, no network/LLM — unit-testable.

Strategy (see bank-reconciliation skill):
  1. Candidate filter: ±3-day window + amount within tolerance.
  2. Score: amount closeness + merchant-name similarity + date proximity.
  3. Classify: AUTO (single confident) / AMBIGUOUS (let LLM disambiguate aliases) / UNMATCHED.
  4. Tie-break: on equal scores, prefer the most recent transaction.
"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum

from src.bank.feed import Transaction

log = logging.getLogger("reconbob.matcher")

DATE_WINDOW_DAYS = 3
AUTO_THRESHOLD = 0.82          # min score to auto-match
AMBIGUOUS_MARGIN = 0.08        # if top two are within this, don't auto-match


class MatchMethod(str, Enum):
    AUTO = "auto"
    AMBIGUOUS = "ambiguous"   # needs LLM alias reasoning
    UNMATCHED = "unmatched"


@dataclass
class Candidate:
    txn: Transaction
    score: float


@dataclass
class MatchResult:
    method: MatchMethod
    best: Candidate | None
    candidates: list[Candidate]


def _parse_date(value: str | dt.date) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.datetime.strptime(value, "%Y-%m-%d").date()


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _amount_tolerance(total: float) -> float:
    return max(0.50, 0.01 * abs(total))


def score(receipt_total: float, receipt_merchant: str, receipt_date: dt.date,
          txn: Transaction) -> float:
    days = abs((txn.date - receipt_date).days)
    amount_diff = abs(txn.amount - receipt_total)
    amount_close = max(0.0, 1.0 - amount_diff / max(receipt_total, 1.0))
    date_close = max(0.0, 1.0 - days / DATE_WINDOW_DAYS)
    # compare receipt merchant against both clean name and raw bank descriptor
    name_close = max(
        _name_similarity(receipt_merchant, txn.merchant),
        _name_similarity(receipt_merchant, txn.raw_name),
    )
    return 0.5 * amount_close + 0.35 * name_close + 0.15 * date_close


def match_receipt(receipt_total: float, receipt_merchant: str,
                  receipt_date: str | dt.date, txns: list[Transaction]) -> MatchResult:
    rdate = _parse_date(receipt_date)
    tol = _amount_tolerance(receipt_total)

    cands: list[Candidate] = []
    for t in txns:
        if abs((t.date - rdate).days) > DATE_WINDOW_DAYS:
            continue
        if abs(t.amount - receipt_total) > tol:
            continue
        cands.append(Candidate(t, score(receipt_total, receipt_merchant, rdate, t)))

    # Tie-break: equal scores prefer the most recent transaction.
    cands.sort(key=lambda c: (c.score, c.txn.date), reverse=True)
    if not cands:
        return MatchResult(MatchMethod.UNMATCHED, None, [])

    best = cands[0]
    runner = cands[1].score if len(cands) > 1 else 0.0
    if best.score >= AUTO_THRESHOLD and (best.score - runner) >= AMBIGUOUS_MARGIN:
        method = MatchMethod.AUTO
    else:
        method = MatchMethod.AMBIGUOUS

    log.debug(
        "match result",
        extra={
            "receipt_merchant": receipt_merchant,
            "receipt_total": receipt_total,
            "method": method.value,
            "best_score": round(best.score, 3),
            "runner_score": round(runner, 3),
            "top_candidates": [
                {"txn_id": c.txn.txn_id, "score": round(c.score, 3)} for c in cands[:3]
            ],
        },
    )

    return MatchResult(method, best, cands)
