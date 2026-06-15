---
name: bank-reconciliation
description: Match receipts against bank transactions for ReconBob. Use when building the reconciliation agent, the daily bank-feed ingest, the ±3-day fuzzy matching algorithm, the BankFeed provider abstraction, or the proactive "missing receipt" prompt loop.
---

# Bank Reconciliation (Agent 2)

Pairs extracted receipts with bank debits and drives the proactive reconciliation loop.

## Bank feed = provider-agnostic interface (mock-first)
**Plaid does not onboard India-based entities — sandbox keys are often unobtainable there.** Don't hard-depend on Plaid. The PRD specifies a *simulated* feed anyway.

- Define a `BankFeed` interface: `sync(user) -> list[Transaction]`. Matching logic depends only on this, never on a vendor SDK.
- **Default impl `MockBankFeed`** (use for dev, beta, and hackathon demo): seeds deterministic fake debits into Firestore — some with matching receipts, some "orphan" debits to trigger Flow B. Zero signup, zero cost, fully reproducible for the demo video.
- `PlaidBankFeed` is an *optional* impl for later, only if a US/EU/Canada entity is available. Same interface, no logic change. Plaid flow if used: Link token → public token → exchange `access_token`, store per user; pull `/transactions/sync` (cursor); sandbox creds `user_good`/`pass_good`.
- India real-data path (post-hackathon): RBI Account Aggregator (e.g. Setu/Finvu) — heavy onboarding, out of scope for the 90-day build.
- Select impl via env `BANK_FEED=mock|plaid`. Schedule daily via Cloud Scheduler → background Cloud Function regardless of impl.

## Matching algorithm
Deterministic first, LLM second:
1. **Candidate filter:** debits within **±3 days** of receipt date, amount within tolerance (`abs(txn.amount - receipt.total) <= max(0.5, 1% of total)`).
2. **Score:** amount closeness + merchant-name fuzzy ratio (`rapidfuzz`) + date proximity.
3. **Auto-match** if single high-confidence candidate. Else hand the shortlist to Gemini Flash to reason about merchant aliases (e.g. "HOMEDEPOT #4112" ↔ "Home Depot") and pick/abstain.
4. Record match + score + method (`auto`/`llm`/`unmatched`) to `transactions/{id}` and `agent_logs`.

## Proactive loop (Flow B)
- After each sync, find debits with **no matched receipt**.
- Trigger a WhatsApp prompt: `Hey Dave, $320.00 at 'City Electric' yesterday — no receipt yet. Snap a photo or tell me what it was for?` See [[twilio-whatsapp]].
- Open a `need_receipt` session ([[agent-orchestration]]). On reply with a photo → OCR + re-match. On text-only → create an internal memo/dummy receipt for the accountant and mark reconciled.

## Notes
- Never block on Plaid latency in the inbound path — reconciliation is async/background.
- Idempotent: store the sync cursor; don't double-ingest transactions.
