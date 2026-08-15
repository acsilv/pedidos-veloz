output "nome_cluster" {
  description = "Nome do cluster criado."
  value       = google_container_cluster.principal.name
}

output "regiao" {
  description = "Região usada pelo cluster."
  value       = google_container_cluster.principal.location
}

output "comando_credenciais" {
  description = "Comando para configurar o kubectl depois da criação."
  value       = "gcloud container clusters get-credentials ${google_container_cluster.principal.name} --region ${google_container_cluster.principal.location} --project ${var.projeto_gcp}"
}
