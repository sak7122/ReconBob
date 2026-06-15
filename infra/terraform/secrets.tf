# Secret Manager CONTAINERS only. Values are added out-of-band (never in Terraform/state):
#   gcloud secrets versions add reconbob-twilio-auth-token --data-file=-
locals {
  secret_ids = [
    "reconbob-twilio-account-sid",
    "reconbob-twilio-auth-token",
    "reconbob-twilio-whatsapp-from",
    "reconbob-stripe-secret-key",
  ]
}

resource "google_secret_manager_secret" "app" {
  for_each  = toset(local.secret_ids)
  project   = var.project_id
  secret_id = each.value
  labels    = var.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

# Runtime SA may read each secret (least privilege — per-secret, not project-wide).
resource "google_secret_manager_secret_iam_member" "runtime_access" {
  for_each  = google_secret_manager_secret.app
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}
