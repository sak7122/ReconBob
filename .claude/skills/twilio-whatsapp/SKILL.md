---
name: twilio-whatsapp
description: Handle Twilio WhatsApp/SMS webhooks and outbound replies for ReconBob's zero-UI flow. Use when building the inbound webhook Cloud Function, downloading media, validating Twilio signatures, sending proactive messages, or shaping reply copy.
---

# Twilio WhatsApp/SMS

Transport layer for the zero-UI agent. Inbound webhook → orchestrator; outbound replies + proactive prompts.

## Inbound webhook
- Twilio POSTs `application/x-www-form-urlencoded`. Key fields: `From`, `To`, `Body`, `NumMedia`, `MediaUrl{N}`, `MediaContentType{N}`, `MessageSid`.
- **Always validate the signature** before doing work: `twilio.request_validator.RequestValidator(auth_token).validate(url, params, x_twilio_signature)`. Reject (403) on failure — webhook is public.
- Media URLs require HTTP Basic auth (Account SID / Auth Token) to fetch the image bytes.

## Outbound
- Two paths:
  - **Synchronous TwiML** reply from the webhook (fast ack) — fine for "Got it!" confirmations.
  - **REST API** (`client.messages.create`) for proactive/async messages (reconciliation loop, anomaly flags). Required when replying outside the 24h session window or from a background job.
- WhatsApp 24-hour window: outside it, only approved template messages send. Plan proactive prompts as templates.

## Latency pattern (PRD <15s)
- Webhook should ack fast. For heavy OCR, send immediate "Working on it…" or run the pipeline within budget; if it risks >15s, ack synchronously then push the result via REST.
- Keep Cloud Function warm (min instances) to avoid cold-start blowing the budget.

## Reply copy
- Conversational, contractor-friendly, one decision per message. Example: `Got it! Logged $143.50 at Home Depot for Plumbing Supplies. The $12 tape measure — file as Tools? (yes/no)`
- Map yes/no/short replies back to pending session state — see [[agent-orchestration]].

## Numbers / sandbox
- Dev: Twilio WhatsApp Sandbox (`whatsapp:+14155238886`, join code).
- Prod: approved WhatsApp Business sender. Store SID/token in GCP Secret Manager — never in code. See [[gcp-deploy]].
