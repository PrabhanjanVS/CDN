terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"  # Use version 5.x
    }
  }
}

provider "google" {
  credentials = file("C:/Terraform/sodium-bliss-476806-p0-e0c5c2ea631b.json")
  project = var.project_id
  region  = var.region
}