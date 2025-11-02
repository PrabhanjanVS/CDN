# Get VPC info from the VPC we created
data "google_compute_network" "vpc" {
  name = var.vpc_name
}

data "google_compute_subnetwork" "main" {
  name   = var.subnet_name
  region = var.region
}

resource "google_container_cluster" "primary" {
  name     = "${var.project_id}-gke"
  location = var.region
  
  # Use the VPC and subnet we created
  network    = data.google_compute_network.vpc.name
  subnetwork = data.google_compute_subnetwork.main.name

  # Start with minimal initial nodes
  remove_default_node_pool = true
  initial_node_count       = 1

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  # Use the secondary IP ranges from our VPC subnet
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Enable HTTP load balancing (for future LoadBalancer services)
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
  }

  # Disable vertical pod autoscaling to reduce complexity
  vertical_pod_autoscaling {
    enabled = false
  }

  # Use regular channel for stability
  release_channel {
    channel = "REGULAR"
  }

  # Reduce master node size (cheaper)
  node_locations = [
    "${var.region}-a"  # Use only one zone to reduce cost
  ]
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "primary-node-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.initial_node_count

  # Start with minimal autoscaling
  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  # Management settings
  management {
    auto_repair  = true
    auto_upgrade = true
  }

  # Conservative upgrade settings
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }

  node_config {
    preemptible  = true  # Cost saving
    machine_type = var.machine_type
    
    # Tags for firewall rules
    tags = ["gke-node"]
    
    # Service account
    service_account = var.service_account_email
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # EXACTLY 18GB disk as requested - using STANDARD disk (HDD) not SSD
    disk_size_gb = 18
    disk_type    = "pd-standard"  # Changed from pd-ssd to pd-standard
    
    # Labels
    labels = {
      environment = "production"
      workload    = "general"
    }

    # Resource reservations (optional - helps with scheduling)
    # resources {
    #   requests = {
    #     cpu    = "250m"
    #     memory = "512Mi"
    #   }
    # }
  }
}