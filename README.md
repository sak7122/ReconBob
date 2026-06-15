# ReconBob

Agentic, zero-UI bookkeeping & receipt auditor for tradespeople. Interact entirely over WhatsApp/SMS. Multi-agent on Google Cloud + Gemini. See [PLAN.md](PLAN.md) for full architecture and milestones; [prd.txt](prd.txt) for the spec.

## Status

**M1 (Weeks 1–3) — done.** Flow A: Twilio webhook → guardrails → Gemini OCR → Firestore → confirmation.
**M2 (Weeks 4–6) — done.** Reconciliation matcher, recon agent (simulated feed), proactive Flow B loop, text-reply session state machine.

```
src/
  main.py              # Twilio webhook (functions-framework HTTP entry)
  recon_job.py         # Cloud Scheduler target: daily reconcile + Flow B prompts
  session.py           # text-reply state machine (confirm_split, need_receipt)
  config.py            # env config + prod startup validation
  guardrails.py        # spend pause, per-user daily cap, media dedupe
  twilio_client.py     # signature validation, media fetch, reply
  agents/
    ocr_agent.py       # Agent 1: Gemini multimodal receipt OCR
    recon_agent.py     # Agent 2: bank reconciliation (uses BankFeed)
  bank/
    feed.py            # BankFeed interface + MockBankFeed (Plaid-free)
    matcher.py         # deterministic ±3-day fuzzy matcher (stdlib only)
  models/receipt.py    # receipt schema + validation rules
  store/firestore.py   # state, receipts, transactions, sessions, memos, logs
tests/                 # 24 pure-logic tests (no GCP/Twilio/Vertex needed)
```

## Local dev

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # fill values

# unit tests (no cloud creds needed)
python -m pytest -q

# run webhook locally
functions-framework --target=webhook --debug
# expose to Twilio sandbox via ngrok, point the WhatsApp webhook at the URL
```

### Live local smoke test

```bash
# 1. Firestore emulator (firebase CLI brings its own jar; needs Java). Runs on 8085.
firebase emulators:start --only firestore --project reconbob-local

# 2. Webhook server (separate shell), pointed at the emulator
export ENV=development GCP_PROJECT_ID=reconbob-local FIRESTORE_EMULATOR_HOST=127.0.0.1:8085 PYTHONPATH=.
.venv/Scripts/functions-framework --target=webhook --source=src/main.py --port=8088

# 3. Fire a request (PowerShell helper)
pwsh scripts/smoke.ps1
```

Note: gcloud's `cloud-firestore-emulator` component won't auto-install non-interactively — use the firebase CLI emulator (above). Port 8085 chosen to avoid a conflict on 8080.

## Secrets

`${VAR}` placeholders only in committed files. Real values: env vars locally, GCP Secret Manager in prod. Never commit `.env` or SA keys (`.gitignore` enforces). Deploy auth via Workload Identity Federation — see [gcp-deploy skill](.claude/skills/gcp-deploy/SKILL.md).

## Cost

Dev/beta ≈ free (sandbox + GCP credit). Guardrails: $50/mo budget alert, Vertex quota cap, per-user 100 receipts/day, Flash-by-default. See [cost-guardrails skill](.claude/skills/cost-guardrails/SKILL.md).

## Next (M3 — Weeks 7–10)

Stripe Payment Links in-chat, `/export` (signed CSV/QuickBooks link, Schedule C), tier gating ($29/$49), anomaly agent (Agent 3, same-merchant SKU variance). Plus: deploy `recon_job` as scheduled Cloud Function, CI/CD workflows, Firestore emulator wiring.
