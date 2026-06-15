variable "project_id" {
  type        = string
  description = "Target GCP project id."
}

variable "region" {
  type        = string
  description = "Default region for regional resources."
  default     = "us-central1"
}

variable "firestore_location" {
  type        = string
  description = "Firestore location (multi-region like 'nam5' or region like 'us-central1'). Cannot be changed after creation."
  default     = "nam5"
}

variable "github_owner" {
  type        = string
  description = "GitHub org/user that owns the repo (for Workload Identity Federation)."
}

variable "github_repo" {
  type        = string
  description = "GitHub repo name (without owner). WIF is restricted to this repo."
}

variable "export_retention_days" {
  type        = number
  description = "Days to keep generated /export files before lifecycle deletion."
  default     = 7
}

variable "recon_job_url" {
  type        = string
  description = "HTTPS URL of the deployed recon_job function. Empty until first deploy; Scheduler job is created only when set."
  default     = ""
}

variable "scheduler_cron" {
  type        = string
  description = "Cron for the daily reconciliation sweep (UTC unless time_zone set)."
  default     = "0 13 * * *"
}

variable "enable_budget" {
  type        = bool
  description = "Create a billing budget + alerts. Requires billing_account and org billing perms."
  default     = false
}

variable "billing_account" {
  type        = string
  description = "Billing account id (XXXXXX-XXXXXX-XXXXXX). Required if enable_budget=true."
  default     = ""
}

variable "budget_amount" {
  type        = number
  description = "Monthly budget ceiling in USD (cost-guardrails default $50)."
  default     = 50
}

variable "labels" {
  type        = map(string)
  description = "Labels applied to supported resources."
  default     = { app = "reconbob", managed_by = "terraform" }
}
