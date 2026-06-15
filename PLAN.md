# ReconBob — Build Plan

Agentic bookkeeping & receipt auditor for tradespeople. Chat-first, WhatsApp/SMS-native, multi-agent on Google Cloud + Gemini. Built on GitHub. GCP integration patterns reused from the RAGaaS project (WIF, Cloud Run deploy, Firebase, CI/CD).

> Spec: **[PRD_v2.md](PRD_v2.md)** (current, amended). Original [prd.txt](prd.txt) kept as source record. Market: US for hackathon, India-ready by design.

## 1. Architecture (from PRD §3)

```
User (WhatsApp/SMS)
   │  Twilio webhook (signed)
   ▼
Cloud Function: ingest  ──► Firestore (state, sessions, ledger)
   │
   ▼
Vertex AI Agent Orchestrator
   ├─ Agent 1: Multimodal OCR        (Gemini 1.5 Pro)   → structured receipt JSON
   ├─ Agent 2: Bank Reconciliation   (Gemini 1.5 Flash) → Plaid match, ±3-day fuzzy
   └─ Agent 3: Anomaly / Fraud Audit (Gemini 1.5 Pro)   → price-variance flags
   │
   ▼
Cloud Function: reply  ──► Twilio outbound (TwiML / REST)
```

Background loop: scheduled Cloud Function (Cloud Scheduler) pulls Plaid feed daily → Agent 2 finds unmatched debits → proactive WhatsApp prompt.

## 2. Tech stack

| Concern            | Choice                                              |
|--------------------|-----------------------------------------------------|
| Messaging          | Twilio WhatsApp/SMS API + webhook                   |
| Compute            | Cloud Functions (gen2) / Cloud Run                  |
| LLM / agents       | Vertex AI, Gemini 1.5 Pro + Flash                   |
| State / DB         | Firestore                                           |
| Bank feed          | `BankFeed` interface — MockBankFeed default (Plaid blocked in India) |
| Payments           | Stripe Payment Links                                |
| Logging / evidence | Cloud Logging (step-by-step agent traces)           |
| Export             | CSV / Excel (Schedule C), signed GCS download link  |
| Secrets / deploy   | GCP Secret Manager, Workload Identity Federation    |
| CI/CD              | GitHub Actions (lint/test → deploy on main)         |

Language: Python (Cloud Functions + Vertex AI SDK), mirrors RAGaaS backend conventions.

## 3. Data model (Firestore)

- `users/{phone}` — profile, tier, Plaid item token, session state
- `users/{phone}/receipts/{id}` — extracted JSON (merchant, date, subtotal, tax, total, line_items[])
- `users/{phone}/transactions/{id}` — Plaid debit, match status, linked receipt id
- `users/{phone}/sessions/{id}` — conversational state for smart-prompt loop
- `users/{phone}/audit_flags/{id}` — anomaly events with evidence
- `agent_logs/{id}` — execution traces (hackathon product evidence)

## 4. Milestones (maps to PRD §5)

- **M1 Weeks 1–3 — Core build:** GCP project + WIF, Firestore schema, Twilio webhook (Cloud Function), Gemini OCR prompt chain, structured-JSON validation. Echo confirmation reply.
- **M2 Weeks 4–6 — Agent loops + beta:** orchestrator wiring, Plaid sandbox ingest + reconciliation agent, proactive prompt loop (Cloud Scheduler), line-item splitter, anomaly agent. 5-user closed beta.
- **M3 Weeks 7–10 — Commercial:** Stripe Payment Links in-chat, `/export` → signed CSV/QuickBooks link, tier gating ($29/$49), hyper-local acquisition.
- **M4 Weeks 11–12 — Submission:** agent-log dashboard, API usage + MRR metrics export, 3-min demo video.

## 5. Non-functional targets

- Latency < 15s receipt→reply (PRD §4.2). Use Gemini Flash where possible; async ack then enrich.
- PII/financial data encrypted at rest + in transit; Secret Manager for all keys; Twilio signature validation on every webhook.
- > 90% autonomous decision ratio (judging metric) — log human-vs-AI decision counts.

## 5a. Cost guardrails (see `cost-guardrails` skill)

- GCP budget $50/mo, alerts at 50/90/100% → Pub/Sub → kill-switch Cloud Function.
- Vertex AI quota cap (~60 req/min beta) so a bug-loop can't drain credit.
- App-level: per-user 100 receipts/day, global daily Gemini-call ceiling, dedupe by media hash, `max_output_tokens` on every call, Flash-by-default / Pro-on-low-confidence.
- Twilio Usage Trigger + WhatsApp sandbox through beta; Plaid sandbox until paid launch.
- Kill-switch: Firestore `system/flags.spend_paused` checked before any paid call.

## 6. Claude Code skills added (`.claude/skills/`)

| Skill                     | Purpose                                                        |
|---------------------------|----------------------------------------------------------------|
| `gemini-receipt-ocr`      | Vertex AI multimodal extraction, receipt JSON schema, retries  |
| `twilio-whatsapp`         | Webhook handling, media download, signature validation, TwiML  |
| `agent-orchestration`     | Multi-agent loop, Firestore state, handoffs, decision logging  |
| `plaid-reconciliation`    | Plaid sandbox, ±3-day fuzzy matching, proactive prompt trigger |
| `gcp-deploy`              | Cloud Functions/Run, WIF, Secret Manager, GitHub Actions CI/CD |
| `cost-guardrails`         | Budget alerts, Vertex quota caps, per-user limits, kill-switch |

Plus built-in skills already available: `code-review`, `security-review`, `verify`, `run`.

## 7. MCP servers (see `.claude/settings.json`)

| Server     | Use                                                      |
|------------|----------------------------------------------------------|
| github     | repo, PRs, issues, CI/CD (project lives on GitHub)       |
| firebase   | Firestore inspection/admin, emulators for local dev      |
| cloudrun   | deploy & inspect Cloud Run / Functions services          |
| stripe     | Payment Links, subscriptions, revenue (MRR) evidence     |
| playwright | exercise `/export` download link + evidence dashboard    |
| filesystem | scoped repo file access                                  |
| memory     | cross-session project memory                             |
| fetch      | pull API docs (Twilio, Plaid, Vertex)                    |

No first-party MCP for **Twilio** or **Plaid** — integrate via their Python SDKs directly; use `fetch` MCP for their API docs.

## 8. Open decisions

- Cloud Functions vs Cloud Run for orchestrator (Run better for >60s + concurrency).
- Vertex AI Agent Engine vs hand-rolled orchestration loop in Python.
- Anomaly history store: Firestore aggregation vs BigQuery (BigQuery if price-trend analytics grow).
