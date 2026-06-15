output "runtime_service_account" {
  description = "Attach to webhook + recon_job at deploy time."
  value       = google_service_account.runtime.email
}

output "deployer_service_account" {
  description = "GitHub Actions secret: GCP_SERVICE_ACCOUNT."
  value       = google_service_account.deployer.email
}

output "workload_identity_provider" {
  description = "GitHub Actions secret: GCP_WORKLOAD_IDENTITY_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "exports_bucket" {
  value       = google_storage_bucket.exports.name
  description = "Bucket for /export download links."
}

output "artifact_registry" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}"
  description = "Image push target."
}

output "secret_ids" {
  description = "Containers created — add values with: gcloud secrets versions add <id> --data-file=-"
  value       = local.secret_ids
}

output "next_steps" {
  value = <<-EOT
    1. Add secret values:  gcloud secrets versions add <secret_id> --data-file=-
    2. Set GitHub Actions secrets: GCP_PROJECT_ID, GCP_SERVICE_ACCOUNT (deployer), GCP_WORKLOAD_IDENTITY_PROVIDER.
    3. Deploy app (webhook + recon_job) via gcp-deploy; attach runtime SA: ${google_service_account.runtime.email}
    4. Set recon_job_url in tfvars to the deployed function URL, then re-apply to create the Scheduler job.
  EOT
}
