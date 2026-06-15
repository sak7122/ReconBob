# Daily reconciliation sweep -> recon_job (Flow B). Created only once recon_job_url is set
# (the function must be deployed first). Invokes with an OIDC token as the runtime SA.
resource "google_cloud_scheduler_job" "recon" {
  count = var.recon_job_url == "" ? 0 : 1

  project   = var.project_id
  region    = var.region
  name      = "reconbob-daily-recon"
  schedule  = var.scheduler_cron
  time_zone = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = var.recon_job_url

    oidc_token {
      service_account_email = google_service_account.runtime.email
      audience              = var.recon_job_url
    }
  }

  retry_config {
    retry_count = 1
  }

  depends_on = [google_project_service.enabled]
}
