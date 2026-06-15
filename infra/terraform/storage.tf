# Bucket for /export files — short-lived, served via signed download links.
resource "google_storage_bucket" "exports" {
  project                     = var.project_id
  name                        = "${var.project_id}-reconbob-exports"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  labels                      = var.labels

  lifecycle_rule {
    condition { age = var.export_retention_days }
    action { type = "Delete" }
  }

  depends_on = [google_project_service.enabled]
}

# Runtime SA can write/read export objects (object-level, not bucket admin).
resource "google_storage_bucket_iam_member" "runtime_exports" {
  bucket = google_storage_bucket.exports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

# Artifact Registry for container images (Cloud Run / Functions gen2 builds).
resource "google_artifact_registry_repository" "app" {
  project       = var.project_id
  location      = var.region
  repository_id = "reconbob"
  format        = "DOCKER"
  description   = "ReconBob app images"
  labels        = var.labels

  depends_on = [google_project_service.enabled]
}
