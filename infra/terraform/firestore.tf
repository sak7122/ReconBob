# Named Firestore database — isolates ReconBob data from other apps (e.g. RAGaaS)
# sharing this project, which owns the project's single "(default)" database.
# App selects it via firestore.Client(database="reconbob") / FIRESTORE_DB env var.
resource "google_firestore_database" "reconbob" {
  project     = var.project_id
  name        = var.firestore_database
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.enabled]
}

# Dev database — same project, separate named DB so dev test writes never touch
# prod data. Selected by FIRESTORE_DB=reconbob-dev in the dev deploy workflow.
resource "google_firestore_database" "reconbob_dev" {
  project     = var.project_id
  name        = var.firestore_database_dev
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.enabled]
}
