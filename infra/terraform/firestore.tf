# Native-mode Firestore — app state, receipts, transactions, sessions, agent_logs.
resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.enabled]
}
