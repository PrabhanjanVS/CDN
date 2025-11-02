output "cluster_name" {
  description = "The name of the GKE cluster"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "The endpoint of the GKE cluster"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "cluster_location" {
  description = "The location of the GKE cluster"
  value       = google_container_cluster.primary.location
}

output "cluster_ca_certificate" {
  description = "The CA certificate of the GKE cluster"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "node_pool_name" {
  description = "The name of the node pool"
  value       = google_container_node_pool.primary_nodes.name
}

output "autoscaling_config" {
  description = "Autoscaling configuration for the node pool"
  value = {
    min_node_count = google_container_node_pool.primary_nodes.autoscaling[0].min_node_count
    max_node_count = google_container_node_pool.primary_nodes.autoscaling[0].max_node_count
  }
}

output "kubeconfig_command" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${google_container_cluster.primary.location} --project ${var.project_id}"
}