"""Receipt schema + validation. Single source of truth for OCR output shape."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# JSON schema passed to Gemini for controlled generation (response_schema).
RECEIPT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "merchant": {"type": "string"},
        "merchant_branch": {"type": "string", "nullable": True},
        "date": {"type": "string", "description": "YYYY-MM-DD"},
        "currency": {"type": "string"},
        "subtotal": {"type": "number"},
        "tax": {"type": "number"},
        "total": {"type": "number"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "sku": {"type": "string", "nullable": True},
                    "qty": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "amount": {"type": "number"},
                    "category_guess": {"type": "string"},
                    "is_business": {"type": "boolean"},
                },
                "required": ["description", "amount", "is_business"],
            },
        },
        "confidence": {"type": "number"},
    },
    "required": ["merchant", "date", "total", "line_items", "confidence"],
}


class LineItem(BaseModel):
    description: str
    sku: Optional[str] = None
    qty: float = 1
    unit_price: float = 0.0
    amount: float = 0.0
    category_guess: Optional[str] = None
    is_business: bool = True

    @field_validator("amount", "unit_price", mode="before")
    @classmethod
    def clamp_non_negative(cls, v: float) -> float:
        """Receipts never have negative line amounts; clamp any bad OCR output."""
        return max(0.0, float(v or 0.0))


class Receipt(BaseModel):
    merchant: str
    merchant_branch: Optional[str] = None
    date: str
    currency: str = "USD"
    subtotal: float = 0.0
    tax: float = 0.0
    total: float
    line_items: list[LineItem] = Field(default_factory=list)
    confidence: float = 0.0

    # set by validation, not the model
    needs_review: bool = False

    @field_validator("date", mode="before")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Ensure OCR-extracted date is valid ISO format (YYYY-MM-DD)."""
        if not v:
            return v
        try:
            dt.datetime.strptime(str(v), "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"date must be YYYY-MM-DD, got {v!r}") from exc
        return str(v)

    @field_validator("total", "subtotal", "tax", mode="before")
    @classmethod
    def clamp_totals_non_negative(cls, v: float) -> float:
        return max(0.0, float(v or 0.0))

    @model_validator(mode="after")
    def flag_math_mismatch(self) -> "Receipt":
        """subtotal + tax should equal total. On mismatch, flag for user confirmation, don't reject."""
        if self.subtotal or self.tax:
            if abs((self.subtotal + self.tax) - self.total) > 0.02:
                self.needs_review = True
                self.confidence = min(self.confidence, 0.5)
        if self.confidence < 0.6:
            self.needs_review = True
        return self
