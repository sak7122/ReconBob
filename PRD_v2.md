# PRD v2 — Agentic Bookkeeping & Receipt Auditor (ReconBob)

> Revision of the original [prd.txt](prd.txt) (kept as source record). Reformatted, deduped, and amended with 12 fixes from the build review. Market decision: **US-targeted for the hackathon, India-ready by design.**
>
> **Target Category:** Small Business Services · **Hackathon:** Build with Gemini XPRIZE

## Changelog vs original PRD

1. Gemini 1.5 → current Gemini (2.x) family — 1.5 is retired.
2. Plaid → provider-agnostic **simulated bank feed** (Plaid unobtainable for India entities).
3. Latency unified to **<15s** with async-ack fallback (was 10s vs 15s contradiction).
4. Market fixed: **US** (USD, Schedule C) with **pluggable currency + tax-category layer** so India (INR, GST/ITR) slots in later.
5. "Dummy receipt" → **"unverified expense memo"** (avoids implying fabricated tax docs).
6. Anomaly agent scoped to **same-merchant same-SKU variance** with graceful cold-start.
7. Added **WhatsApp Business template approval** to Week 1 (proactive msgs need it).
8. Added **§6 Compliance & Disclaimers** (consent, retention, not-an-accountant, webhook signature validation).
9. "Zero-UI" → **"chat-first, minimal-UI"** (export link + metrics dashboard exist).
10. Identity model clarified: **single-owner MVP**, apprentices later.
11. Pricing kept US ($29/$49); India pricing deferred with market layer.
12. **Submission-honesty** note: bank feed is simulated; receipts + Stripe revenue are real.

---

## 1. Executive Summary

### 1.1 Objective
AI-native, **chat-first** financial operations agent that automates bookkeeping, receipt reconciliation, and expense auditing for independent tradespeople (plumbers, electricians, contractors). Operates inside WhatsApp/SMS — no app, no spreadsheets.

### 1.2 Problem
Tradespeople lose money in unclaimed deductions, double-billed invoices, and unbilled materials because receipts live in truck dashboards. QuickBooks/Xero demand disciplined manual upkeep busy contractors avoid.

### 1.3 Solution
Autonomous multi-agent system on Google Cloud + **Gemini (2.x)**. A proactive virtual accountant: snap a receipt photo, the AI extracts line items, matches to the bank feed, flags anomalies, and reconciles autonomously — over text.

### 1.4 Market scope
- **Hackathon market: United States** — USD, IRS Schedule C categories, Home Depot persona.
- **India-ready by design:** currency and tax-category mapping are a config layer (see §3.4). Switching to INR + GST/ITR is configuration, not a rebuild.

---

## 2. Personas & UX

### 2.1 Persona — "Dave the Plumber" (US)
On the move, drives between jobs, 1–2 apprentices, bills nights/weekends, hates software. **Need:** every business expense logged for tax write-offs in <5 seconds.

### 2.2 Core flows (chat-first)

**Flow A — Real-time receipt submission**
1. Dave buys copper pipe at Home Depot, gets a paper receipt.
2. Snaps a photo to the business WhatsApp number.
3. AI replies (target <15s; sends an instant ack if extraction runs long):
   > "Got it! Logged $143.50 at Home Depot for Plumbing Supplies. Noticed a $12 tape measure — file as Tools, or personal? (business/personal)"
4. Dave: "business." Transaction reconciled.

**Flow B — Proactive reconciliation loop (agentic trigger)**
1. Daily bank-feed sync detects a $320.00 debit at "City Electric" with no receipt.
2. AI proactively messages (via approved WhatsApp template):
   > "Hey Dave, $320.00 at 'City Electric' yesterday — no receipt yet. Snap a photo or tell me what it was for?"
3. Dave sends a photo or replies "Smith job wire."
4. AI updates the ledger; if no receipt image, creates an **unverified expense memo** (clearly flagged) for the accountant.

---

## 3. Architecture & Technical Spec

```
User (WhatsApp/SMS)
   │  Twilio webhook (signature-validated)
   ▼
Cloud Function: ingest ──► Firestore (state, sessions, ledger, agent_logs)
   │
   ▼
Vertex AI Agent Orchestrator
   ├─ Agent 1: Multimodal OCR        (Gemini Pro)    → structured receipt JSON
   ├─ Agent 2: Bank Reconciliation   (Gemini Flash)  → match vs simulated feed, ±3-day
   └─ Agent 3: Anomaly / Fraud Audit (Gemini Pro)    → same-merchant SKU price variance
   │
   ▼
Cloud Function: reply ──► Twilio outbound (TwiML / REST template)
```
Background: Cloud Scheduler → daily bank-feed sync → Agent 2 finds orphan debits → Flow B prompt.

### 3.1 Agents
- **Agent 1 — OCR (Gemini Pro via Vertex AI):** parses image/text → JSON: merchant, branch, date, subtotal, tax, total, line items (SKU, description, qty, amount, category guess, is_business). Confidence + math-check; low confidence → user confirmation, never fabricate.
- **Agent 2 — Reconciliation (Gemini Flash):** deterministic fuzzy match (amount + merchant-name + ±3-day window) augmented by LLM for merchant aliases. Source = **`BankFeed` interface** (MockBankFeed default).
- **Agent 3 — Anomaly/Audit (Gemini Pro):** **MVP = same-merchant, same-SKU unit-price variance** vs that user's history. Cold-start: no flag until ≥2 observations; seed demo history. Cross-merchant comparison is post-MVP (needs SKU normalization).

### 3.2 Storage & logging
- **Firestore:** `users/{phone}`, `…/receipts`, `…/transactions`, `…/sessions`, `…/audit_flags`, `…/counters`; global `agent_logs` + `system/flags`.
- **Cloud Logging:** step-by-step agent traces (hackathon product evidence). Each agent logs decision + `autonomous` bool + latency + tokens.

### 3.3 Bank feed (simulated, pluggable)
- `BankFeed` interface; **MockBankFeed** (deterministic seeded debits incl. orphan) is default for dev/beta/**demo**. Selected via `BANK_FEED=mock|plaid`.
- Plaid is an optional later impl (needs US/EU/CA entity). India real data = RBI Account Aggregator (Setu/Finvu), post-hackathon.

### 3.4 Currency & tax-category layer (US default, India-ready)
- Single config maps line-item categories → tax buckets. **US default = IRS Schedule C.** India profile = GST/ITR (deferred).
- Currency from profile (USD default). All money stored with currency code.

---

## 4. Functional Requirements

### 4.1 MVP scope
- **Multimodal text-to-bookkeeper:** accept JPG, PNG, HEIC (HEIC → JPEG before Gemini).
- **Line-item splitter:** separate personal vs business items on one receipt from text instructions.
- **Bank-feed reconciliation:** daily simulated ingest, ±3-day fuzzy match vs logged receipts.
- **Smart prompting engine:** proactive, context-aware loops for missing inputs; one open decision per user.
- **Export:** `/export` → secure signed download link, accountant-ready CSV/Excel mapped to tax categories (Schedule C for US profile).

### 4.2 Non-functional
- **Latency:** receipt → confirmation **<15s**. Async ack if extraction runs long. Warm min-instances.
- **Security:** PII + financial data encrypted at rest and in transit. Secrets in GCP Secret Manager. **Twilio webhook signature validated on every request.** Deploy via Workload Identity Federation (no key files).
- **Autonomy metric:** AI resolves >90% of parse/categorize/validate actions without human input (logged).

---

## 5. 90-Day Go-To-Market

- **Weeks 1–3 — Core build:** GCP infra + WIF, Firestore schema, Twilio webhook, Gemini OCR chain, output validation. **Start WhatsApp Business + template approval now** (lead time). Use Twilio sandbox for dev.
- **Weeks 4–6 — Agent loops + beta:** orchestrator, reconciliation vs simulated feed, proactive loop (Scheduler), line-item splitter, anomaly agent. Recruit 5 US tradespeople for unbilled closed beta.
- **Weeks 7–10 — Commercial:** Stripe Payment Links in-chat, `/export`, tier gating. Launch **$29/mo Basic Ledger** / **$49/mo Pro Auditor**. Hyper-local acquisition.
- **Weeks 11–12 — Submission:** agent-log + metrics dashboard, API-usage records, Stripe P&L export, 3-min live-agent demo video.

### 5.1 Success metrics (judging)
- **AI-native ops:** human-to-AI decision ratio (target AI >90% autonomous).
- **Business viability:** MRR growth + daily text engagement.
- **Category impact:** hours saved/contractor/week (target 4h → ~0).

### 5.2 Submission honesty
Bank feed is **simulated** — do not claim live bank integration. Receipts processed and Stripe revenue are **real**. State this plainly in the submission.

---

## 6. Compliance & Disclaimers (new)

- **Not a licensed accountant/tax advisor.** Output is assistance, not filed advice; user/accountant verifies. Show disclaimer at onboarding.
- **Consent:** explicit opt-in to process receipts + (simulated) financial data; record consent timestamp.
- **Data retention:** stated policy; user can request export/delete (`/export`, `/delete`).
- **Liability:** categorization is a suggestion; user confirms before tax use. `unverified expense memo` clearly labeled as unverified.
- **Webhook integrity:** reject unsigned/invalid Twilio requests (public endpoint).
- **Least privilege:** scoped service accounts; secrets only in Secret Manager.

---

## 7. Open decisions
- Orchestrator host: Cloud Run (concurrency, >60s) vs Cloud Function gen2.
- Vertex AI Agent Engine vs hand-rolled Python loop (default: explicit loop for log fidelity).
- Anomaly history store: Firestore aggregation vs BigQuery if price-trend analytics grow.
- GCP region: us-central1 (US market). asia-south1 when India profile activates.
