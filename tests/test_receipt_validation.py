"""Pure-logic tests — no GCP/Twilio needed. Cover the receipt schema validation rules."""
from src.models.receipt import Receipt


def _base(**kw):
    data = {
        "merchant": "Home Depot",
        "date": "2026-06-16",
        "total": 143.50,
        "subtotal": 132.50,
        "tax": 11.00,
        "confidence": 0.95,
        "line_items": [
            {"description": "Copper pipe", "amount": 131.50, "is_business": True,
             "category_guess": "Plumbing Supplies"},
            {"description": "Tape measure", "amount": 12.00, "is_business": False,
             "category_guess": "Tools"},
        ],
    }
    data.update(kw)
    return data


def test_clean_receipt_not_flagged():
    r = Receipt.model_validate(_base())
    assert not r.needs_review
    assert r.total == 143.50


def test_math_mismatch_flags_review():
    r = Receipt.model_validate(_base(subtotal=100.0, tax=10.0, total=200.0))
    assert r.needs_review
    assert r.confidence <= 0.5


def test_low_confidence_flags_review():
    r = Receipt.model_validate(_base(confidence=0.3))
    assert r.needs_review


def test_personal_item_preserved():
    r = Receipt.model_validate(_base())
    personal = [li for li in r.line_items if not li.is_business]
    assert len(personal) == 1
    assert personal[0].description == "Tape measure"
