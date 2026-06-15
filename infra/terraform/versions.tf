terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
  }

  # Remote state for shared/real use. Create the bucket first, then uncomment + `terraform init -migrate-state`.
  # backend "gcs" {
  #   bucket = "reconbob-tfstate"
  #   prefix = "infra"
  # }
}
