"""Cost guardrails enforced before any paid call. See .claude/skills/cost-guardrails."""
from __future__ import annotations

import hashlib
import logging

from src.config import config
from src.store import firestore as store

log = logging.getLogger("reconbob.guardrails")


class GuardrailBlock(Exception):
    """Raised when a guardrail rejects the request. Carries a user-facing message."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


def media_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_before_processing(phone: str) -> None:
    """Run all gates before spending on Gemini. Raise GuardrailBlock with a friendly reply on reject."""
    if store.spend_paused():
        raise GuardrailBlock("Service is paused for maintenance — back shortly. 🛠️")

    count = store.increment_daily_count(phone)
    if count > config.max_receipts_per_user_day:
        raise GuardrailBlock(
            f"Daily limit reached ({config.max_receipts_per_user_day} receipts). "
            "Resets tomorrow — your logged items are safe."
        )
    log.info("guardrails passed", extra={"phone": phone, "daily_count": count})
