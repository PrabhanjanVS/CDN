output "vpc_name" {
  value = google_compute_network.vpc.name
}

output "vpc_id" {
  value = google_compute_network.vpc.id
}

output "private_subnet_name" {
  value = google_compute_subnetwork.main.name
}