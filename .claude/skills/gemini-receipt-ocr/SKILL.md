---
name: gemini-receipt-ocr
description: Extract structured receipt JSON from images using Gemini multimodal via Vertex AI. Use when parsing receipt/invoice photos (JPG/PNG/HEIC), building the OCR ingestion agent, defining the receipt schema, or handling blurry/crumpled/grease-stained receipts in ReconBob.
---

# Gemini Receipt OCR (Agent 1)

Multimodal ingestion agent. Turns a receipt image into validated structured JSON.

## Engine
- Gemini 1.5 Pro via Vertex AI SDK (`vertexai.generative_models`). Pro for accuracy on degraded images; Flash only if latency budget (<15s end-to-end) is tight.
- Use `response_mime_type="application/json"` + a `response_schema` so output is parseable — never regex-scrape free text.

## Input handling
- Accept JPG, PNG, HEIC. Convert HEIC → JPEG before sending (`pillow-heif`); Gemini does not take HEIC natively.
- Download media from Twilio URL (auth with account SID/token), pass bytes as `Part.from_data(mime_type=..., data=...)`.
- Strip/validate size before upload; reject non-image MIME.

## Output schema
```json
{
  "merchant": "string",
  "merchant_branch": "string|null",
  "date": "YYYY-MM-DD",
  "currency": "string",
  "subtotal": 0.0,
  "tax": 0.0,
  "total": 0.0,
  "line_items": [
    {"description": "string", "sku": "string|null", "qty": 1, "unit_price": 0.0, "amount": 0.0,
     "category_guess": "Plumbing Supplies|Tools|Fuel|Personal|...", "is_business": true}
  ],
  "confidence": 0.0
}
```

## Rules
- Validate: `abs(subtotal + tax - total) < 0.02` tolerance. On mismatch, set low `confidence` and flag for user confirmation rather than guessing.
- Never invent line items not visible. Missing field → `null`, not a fabricated value.
- `category_guess` is a suggestion; final categorization confirmed by user (smart-prompt loop) — see [[agent-orchestration]].
- Detect likely-personal items (e.g. snacks) → `is_business:false` so the line-item splitter can confirm.
- Log raw model response + token usage to `agent_logs` for hackathon evidence.

## Failure modes
- Unreadable image → reply asking for a re-shot, don't store garbage.
- Retry once on transient Vertex errors with backoff; surface persistent failures to user politely.
