---
name: gcp-deploy
description: Deploy and secure ReconBob on Google Cloud — Cloud Functions/Run, Secret Manager, Workload Identity Federation, GitHub Actions CI/CD. Use when setting up infra, deploying, managing secrets, or wiring CI/CD. Mirrors the RAGaaS project's proven GCP patterns.
---

# GCP Deploy & Security

Infra + deploy. Reuses RAGaaS's battle-tested GCP setup (WIF, Cloud Run, GitHub Actions — no key files).

## Compute
- **Inbound webhook + orchestrator:** Cloud Run (concurrency, >60s, warm min-instances for the <15s latency target) or Cloud Functions gen2.
- **Background reconciliation:** Cloud Function gen2 triggered by **Cloud Scheduler** (daily Plaid sync). See [[plaid-reconciliation]].

## Secrets (never in code/repo)
- GCP **Secret Manager** for: Twilio SID/Auth token, Plaid client/secret + access tokens, Stripe secret key, Vertex SA scope.
- Mount secrets as env vars at deploy; reference `${VAR}` in `.claude/settings.json`, real values in Secret Manager + GitHub Actions secrets.
- Encrypt PII/financial fields at rest in Firestore where feasible; everything in transit over TLS (PRD §4.2).

## Auth — Workload Identity Federation (no service-account JSON keys)
- GitHub Actions authenticates to GCP via WIF (`google-github-actions/auth` with `workload_identity_provider` + `service_account`).
- Required GitHub secrets (from RAGaaS pattern): `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `GCP_PROJECT_ID`, plus app secrets (`TWILIO_*`, `PLAID_*`, `STRIPE_*`).

## CI/CD (GitHub Actions)
- `ci.yml`: on PR/push → `pytest`, lint, build. Block merge on failure.
- `deploy.yml`: on push to `main` → `gcloud run deploy` / `gcloud functions deploy` + scheduler setup, authenticated via WIF.

## Local dev
- Firebase emulators for Firestore; `functions-framework` to run a function locally; Twilio Sandbox + ngrok/Cloud Run preview for webhook testing.

## Project
- Set real `GCP_PROJECT_ID` + region (RAGaaS used `us-central1`). Confirm Vertex AI, Firestore, Secret Manager, Cloud Scheduler APIs enabled.
