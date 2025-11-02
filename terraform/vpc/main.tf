# VPC Network - Fully public
resource "google_compute_network" "vpc" {
  name                    = "${var.project_id}-vpc"
  auto_create_subnetworks = false
}

# Public subnet for everything
resource "google_compute_subnetwork" "main" {
  name          = "${var.project_id}-main-subnet"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.0.1.0/24"

  # DISABLE private IP access - make everything public
  private_ip_google_access = false

  # Secondary ranges for GKE pods & services
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/20"
  }
}

# Allow ALL inbound traffic (HTTP/HTTPS)
resource "google_compute_firewall" "allow_http" {
  name    = "${var.project_id}-allow-http"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "5000", "6379"]  # Added Redis port 6379
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gke-node", "redis-node"]
}


# Allow ALL TCP traffic (full freedom)
resource "google_compute_firewall" "allow_all_tcp" {
  name    = "${var.project_id}-allow-all-tcp"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]  # All TCP ports
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gke-node", "redis-node"]
}

# Allow ALL UDP traffic
resource "google_compute_firewall" "allow_all_udp" {
  name    = "${var.project_id}-allow-all-udp"
  network = google_compute_network.vpc.name

  allow {
    protocol = "udp"
    ports    = ["0-65535"]  # All UDP ports
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gke-node", "redis-node"]
}

# Allow ICMP (ping)
resource "google_compute_firewall" "allow_icmp" {
  name    = "${var.project_id}-allow-icmp"
  network = google_compute_network.vpc.name

  allow {
    protocol = "icmp"
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gke-node", "redis-node"]
}

