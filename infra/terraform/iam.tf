# Runtime service account — used by the webhook + recon_job at run time. Least privilege.
resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = "reconbob-runtime"
  display_name = "ReconBob runtime (webhook + recon_job)"
  depends_on   = [google_project_service.enabled]
}

locals {
  runtime_roles = [
    "roles/aiplatform.user",   # call Gemini via Vertex
    "roles/datastore.user",    # Firestore read/write
    "roles/logging.logWriter", # agent execution traces
  ]
}

resource "google_project_iam_member" "runtime" {
  for_each = toset(local.runtime_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.runtime.email}"
}

# Deployer service account — assumed by GitHub Actions via WIF (no key files). See wif.tf.
resource "google_service_account" "deployer" {
  project      = var.project_id
  account_id   = "reconbob-deployer"
  display_name = "ReconBob CI/CD deployer (GitHub Actions via WIF)"
  depends_on   = [google_project_service.enabled]
}

locals {
  deployer_roles = [
    "roles/run.admin",
    "roles/cloudfunctions.admin",
    "roles/artifactregistry.writer",
    "roles/cloudscheduler.admin",
    "roles/iam.serviceAccountUser", # act as the runtime SA when deploying
  ]
}

resource "google_project_iam_member" "deployer" {
  for_each = toset(local.deployer_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.deployer.email}"
}
