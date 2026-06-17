"""Agent 1: multimodal receipt OCR via Vertex AI Gemini. See .claude/skills/gemini-receipt-ocr."""
from __future__ import annotations

import io
import json
import logging
import time

from src.config import config
from src.models.receipt import RECEIPT_RESPONSE_SCHEMA, Receipt

# vertexai is imported lazily inside functions: keeps webhook cold-start light and lets
# the text/session path run without the heavy aiplatform stack installed.

log = logging.getLogger("reconbob.ocr")

_PROMPT = (
    "You are a receipt-parsing agent for a tradesperson's bookkeeping system. "
    "Extract structured data from this receipt image. Extract only what is visibly present — "
    "use null for missing fields, never invent values. For each line item, guess a business "
    "expense category (e.g. Plumbing Supplies, Tools, Fuel, Personal) and whether it is a "
    "business expense (is_business). Set confidence 0..1 reflecting image legibility. "
    "Respond with JSON only."
)

_inited = False


def _init() -> None:
    global _inited
    if not _inited:
        import vertexai

        vertexai.init(project=config.gcp_project_id, location=config.gcp_region)
        _inited = True


def _to_jpeg(data: bytes, content_type: str) -> tuple[bytes, str]:
    """Gemini takes JPEG/PNG, not HEIC. Convert HEIC -> JPEG."""
    if "heic" in content_type.lower() or "heif" in content_type.lower():
        import pillow_heif  # noqa: F401  (registers HEIF opener)
        from PIL import Image

        img = Image.open(io.BytesIO(data)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue(), "image/jpeg"
    return data, content_type


def extract_receipt(image_bytes: bytes, content_type: str) -> Receipt:
    """Image -> validated Receipt. Retries once on transient model errors."""
    from vertexai.generative_models import GenerationConfig, GenerativeModel, Part

    _init()
    img, mime = _to_jpeg(image_bytes, content_type)
    model = GenerativeModel(config.gemini_ocr_model)
    gen_cfg = GenerationConfig(
        response_mime_type="application/json",
        response_schema=RECEIPT_RESPONSE_SCHEMA,
        max_output_tokens=2048,
        temperature=0,
    )
    parts = [Part.from_data(mime_type=mime, data=img), Part.from_text(_PROMPT)]

    last_err: Exception | None = None
    for attempt in range(2):
        t0 = time.time()
        try:
            resp = model.generate_content(parts, generation_config=gen_cfg)

            # Guard against empty or refused responses before parsing.
            candidates = getattr(resp, "candidates", None) or []
            if not candidates:
                raise RuntimeError("Gemini returned no candidates (possible content refusal)")
            raw = getattr(resp, "text", None)
            if not raw or not raw.strip():
                finish = getattr(candidates[0], "finish_reason", "unknown")
                raise RuntimeError(f"Gemini returned empty text (finish_reason={finish})")

            try:
                receipt = Receipt.model_validate(json.loads(raw))
            except Exception as parse_err:
                # Parse/validation errors are not transient — don't retry.
                raise RuntimeError(f"OCR response failed validation: {parse_err}") from parse_err

            usage = getattr(resp, "usage_metadata", None)
            log.info(
                "ocr ok",
                extra={
                    "model": config.gemini_ocr_model,
                    "latency_ms": int((time.time() - t0) * 1000),
                    "confidence": receipt.confidence,
                    "needs_review": receipt.needs_review,
                    "prompt_tokens": getattr(usage, "prompt_token_count", None),
                    "output_tokens": getattr(usage, "candidates_token_count", None),
                    "total_tokens": getattr(usage, "total_token_count", None),
                },
            )
            return receipt
        except RuntimeError:
            # RuntimeErrors from the parse/validation guard above are not retryable.
            raise
        except Exception as e:  # transient Vertex / network error
            last_err = e
            log.warning("ocr attempt %d failed (transient): %s", attempt + 1, e)
            time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1.0s
    raise RuntimeError(f"OCR failed after retries: {last_err}")
