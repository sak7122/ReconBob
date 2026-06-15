---
name: cost-guardrails
description: Cap and monitor ReconBob infra cost — GCP budget alerts, Vertex AI quota limits, app-level rate limits, Twilio/Plaid spend controls. Use when setting up billing budgets, quota caps, per-user throttles, or kill-switches to prevent runaway charges.
---

# Cost Guardrails

Stop runaway spend. Layered: billing alerts (detect) → quotas (hard cap) → app limits (per-user) → kill-switch.

## 1. GCP budget alert (detect, not block)
Budgets notify, they do **not** auto-stop billing. Set low for hackathon.
```bash
# requires billing account id
gcloud billing budgets create \
  --billing-account=BILLING_ACCT_ID \
  --display-name="reconbob-monthly" \
  --budget-amount=50USD \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0 \
  --filter-projects=projects/GCP_PROJECT_ID
```
Alerts at 50 / 90 / 100%. Wire Pub/Sub on the budget → Cloud Function kill-switch (§5) for auto-action.

## 2. Vertex AI quota cap (hard limit on Gemini spend)
Gemini is the main GCP cost. Cap requests/min so a bug-loop can't drain credit.
- Console → IAM & Admin → **Quotas** → filter `aiplatform.googleapis.com` → set low limit on generate-content requests per minute/region.
- Or via `gcloud services` quota override. Set generously above expected (e.g. beta: 60/min) but finite.

## 3. App-level limits (cheapest, most effective)
Enforce in code before any paid call:
- **Per-user daily cap** on receipts/messages (mirror RAGaaS quota pattern: e.g. 100 receipts/user/day → reject with friendly WhatsApp reply). Store counter in Firestore `users/{phone}.daily_count`, reset by Scheduler.
- **Global daily ceiling** on Gemini calls — env var `MAX_GEMINI_CALLS_DAY`; halt + alert when hit.
- **Route to Flash by default**, escalate to Pro only when OCR confidence low — biggest cost lever.
- **Dedupe**: hash incoming media; skip re-processing identical receipt.
- **Cap output tokens** (`max_output_tokens`) on every Gemini call.

## 4. Third-party caps
- **Twilio**: set a Twilio **Usage Trigger** (alert/suspend at $ threshold) in console. Keep WhatsApp **sandbox** through beta = free.
- **Plaid**: stay in **sandbox** (free) until prod-ready. Sandbox cannot bill.
- **Stripe**: no infra cost; only per-charge fee. No cap needed.

## 5. Kill-switch (auto-stop)
Budget Pub/Sub topic → Cloud Function that, at 100%:
- flips a Firestore `system/flags.spend_paused = true`; orchestrator checks flag and refuses paid calls, replies "service paused".
- (extreme) detaches billing: `gcloud billing projects unlink GCP_PROJECT_ID` — stops all billable GCP. Use only as last resort; breaks the app.

## Defaults for hackathon
- Budget $50/mo, alerts 50/90/100%.
- Vertex quota: finite, ~60 req/min beta.
- Per-user: 100 receipts/day. Global: cap Gemini calls/day.
- Twilio + Plaid: sandbox until paid launch. See [[gcp-deploy]], [[agent-orchestration]].
