---
name: terraform
description: Author and run Terraform IaC for ReconBob's GCP infra. Use when creating/modifying anything under infra/terraform — APIs, Firestore, service accounts, Workload Identity Federation, Secret Manager, buckets, Cloud Scheduler, billing budgets — or running plan/apply.
---

# Terraform (GCP infra)

Provisions ReconBob's **infrastructure** only. App code (webhook, recon_job) deploys separately via gcloud/GitHub Actions — see [[gcp-deploy]]. Keeps infra and app lifecycles independent.

## Layout
`infra/terraform/` — flat module: `apis.tf`, `firestore.tf`, `iam.tf`, `wif.tf`, `secrets.tf`, `storage.tf`, `scheduler.tf`, `budget.tf`, plus `variables.tf`, `providers.tf`, `versions.tf`, `outputs.tf`, `terraform.tfvars.example`.

## Rules
- **No secret values in Terraform.** Create Secret Manager *containers* only; add versions out-of-band (`gcloud secrets versions add`). Never put tokens in `.tfvars` or state.
- **No service-account JSON keys.** GitHub Actions auth via **Workload Identity Federation** (keyless). TF creates the pool/provider + deployer SA binding.
- **Least privilege.** Runtime SA gets only what the app needs (Vertex user, Firestore user, per-secret accessor, log writer, export-bucket object admin). Deployer SA gets deploy roles + actAs runtime SA.
- `terraform.tfvars` is gitignored; commit only `terraform.tfvars.example`.
- State holds project metadata — use a **remote GCS backend** for any shared/real use (commented in `versions.tf`); local state is fine for a solo first apply.

## Workflow
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # fill project_id, github repo, billing acct
terraform init
terraform fmt && terraform validate
terraform plan -out tf.plan
terraform apply tf.plan
```
- First apply enables APIs; if a resource races an API, re-run apply (dependencies declared but propagation can lag).
- `recon_job_url` is empty until the function is first deployed; the Scheduler job is created only once that var is set (re-apply after deploy).
- Budget needs `enable_budget=true` + a `billing_account` and org-level billing perms.

## After apply
Outputs list the GitHub Actions secrets to set (WIF provider, deployer SA, project id) and the secret containers awaiting `gcloud secrets versions add`. Wire those, then deploy app via [[gcp-deploy]].
