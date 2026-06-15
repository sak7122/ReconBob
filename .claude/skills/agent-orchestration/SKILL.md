---
name: agent-orchestration
description: Coordinate ReconBob's multi-agent loop (OCR, reconciliation, anomaly) with Firestore state and conversational sessions. Use when wiring the Vertex AI orchestrator, managing session/dialog state, handling agent handoffs, the smart-prompt loop, or logging human-vs-AI decisions.
---

# Multi-Agent Orchestration

Coordinates the three agents and the conversational state machine. The "brain" between Twilio and the agents.

## Agents
1. **OCR** (Gemini 1.5 Pro) — receipt image → JSON. See [[gemini-receipt-ocr]].
2. **Reconciliation** (Gemini 1.5 Flash) — match receipt ↔ Plaid debit. See [[plaid-reconciliation]].
3. **Anomaly/Audit** (Gemini 1.5 Pro) — price-variance vs history → flags.

## Routing
- Inbound has media → OCR agent. Reply text resolving a pending question → resume that session. Bare command (`/export`) → tool handler. Background tick → reconciliation sweep.
- Keep routing deterministic (rules) where possible; use the LLM for ambiguity, not for plumbing.

## Session state (Firestore `users/{phone}/sessions`)
- `pending_action`: `confirm_category | need_receipt | confirm_split | none`
- `context`: ids of receipt/transaction in question, options offered
- Resolve a session when the user answers; expire stale sessions (e.g. 48h).
- One open decision at a time per user to keep the zero-UI thread coherent.

## Handoffs
- OCR result → reconciliation attempt → if matched, confirm; if anomaly found, raise flag in same or follow-up message.
- Each agent writes its output + the decision it made (auto vs needs-human) to `agent_logs`.

## Decision logging (judging metric: >90% autonomous)
- Every agent action records `{decision, autonomous: bool, agent, latency_ms, tokens}`.
- Autonomous = resolved without asking the user. Track the ratio — it's a scored hackathon metric.

## Orchestrator host
- Cloud Run (better for concurrency + >60s) or Cloud Function gen2. See [[gcp-deploy]].
- Consider Vertex AI Agent Engine vs a hand-rolled Python loop — default to explicit Python loop for debuggability and log fidelity.
