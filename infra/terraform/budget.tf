# Cost guardrail: monthly billing budget with alert thresholds (cost-guardrails skill).
# Alerts notify; they do not auto-stop billing. Wire the budget's Pub/Sub to a kill-switch for auto-action.
resource "google_billing_budget" "monthly" {
  count = var.enable_budget ? 1 : 0

  provider        = google-beta
  billing_account = var.billing_account
  display_name    = "reconbob-monthly"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_amount)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
}
