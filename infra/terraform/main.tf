resource "google_project_service" "kubernetes" {
  project            = var.projeto_gcp
  service            = "container.googleapis.com"
  disable_on_destroy = false
}

resource "google_compute_network" "principal" {
  name                    = "${var.nome_cluster}-rede"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "principal" {
  name          = "${var.nome_cluster}-subrede"
  region        = var.regiao
  network       = google_compute_network.principal.id
  ip_cidr_range = "10.10.0.0/20"

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.faixa_pods
  }

  secondary_ip_range {
    range_name    = "servicos"
    ip_cidr_range = var.faixa_servicos
  }
}

resource "google_container_cluster" "principal" {
  name                = var.nome_cluster
  location            = var.regiao
  project             = var.projeto_gcp
  enable_autopilot    = true
  deletion_protection = var.proteger_exclusao
  network             = google_compute_network.principal.id
  subnetwork          = google_compute_subnetwork.principal.id
  resource_labels     = var.rotulos

  release_channel {
    channel = "STABLE"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "servicos"
  }

  workload_identity_config {
    workload_pool = "${var.projeto_gcp}.svc.id.goog"
  }

  depends_on = [google_project_service.kubernetes]
}
