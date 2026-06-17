"""Twilio I/O: signature validation, media fetch, outbound reply. See .claude/skills/twilio-whatsapp."""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from src.config import config

log = logging.getLogger("reconbob.twilio")

_SEND_RETRIES = 3
_SEND_BACKOFF = (1.0, 2.0, 4.0)  # seconds between retries


def validate_signature(url: str, params: dict[str, str], signature: str) -> bool:
    """Reject any webhook that isn't genuinely from Twilio — endpoint is public."""
    validator = RequestValidator(config.twilio_auth_token)
    return validator.validate(url, params, signature or "")


def fetch_media(media_url: str) -> tuple[bytes, str]:
    """Download an inbound media attachment. Twilio media requires HTTP Basic auth."""
    resp = requests.get(
        media_url,
        auth=(config.twilio_account_sid, config.twilio_auth_token),
        timeout=10,
    )
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    return resp.content, content_type


def send_message(to: str, body: str) -> None:
    """Outbound REST message (proactive / async path). Retries on transient errors."""
    client = Client(config.twilio_account_sid, config.twilio_auth_token)
    last_err: Exception | None = None
    for attempt, backoff in enumerate((*_SEND_BACKOFF, None), start=1):
        try:
            client.messages.create(from_=config.twilio_whatsapp_from, to=to, body=body)
            return
        except Exception as e:
            last_err = e
            log.warning("send_message attempt %d failed: %s", attempt, e)
            if backoff is not None:
                time.sleep(backoff)
    raise RuntimeError(f"send_message failed after {_SEND_RETRIES} attempts: {last_err}")


def twiml_reply(body: str) -> str:
    """Synchronous TwiML reply for the fast-ack path."""
    from twilio.twiml.messaging_response import MessagingResponse

    resp = MessagingResponse()
    resp.message(body)
    return str(resp)
