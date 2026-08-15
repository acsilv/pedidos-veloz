variable "projeto_gcp" {
  description = "Identificador do projeto no Google Cloud."
  type        = string
}

variable "regiao" {
  description = "Região do cluster GKE Autopilot."
  type        = string
  default     = "southamerica-east1"
}

variable "nome_cluster" {
  description = "Nome do cluster Kubernetes."
  type        = string
  default     = "pedidos-veloz"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,38}$", var.nome_cluster))
    error_message = "O nome deve começar com letra minúscula e usar apenas letras, números e hífen."
  }
}

variable "faixa_pods" {
  description = "Faixa secundária reservada aos pods."
  type        = string
  default     = "10.20.0.0/16"
}

variable "faixa_servicos" {
  description = "Faixa secundária reservada aos Services."
  type        = string
  default     = "10.30.0.0/20"
}

variable "proteger_exclusao" {
  description = "Bloqueia exclusões acidentais. Use false apenas no laboratório."
  type        = bool
  default     = true
}

variable "rotulos" {
  description = "Rótulos aplicados aos recursos compatíveis."
  type        = map(string)
  default = {
    sistema  = "pedidos-veloz"
    ambiente = "academico"
    gerencia = "terraform"
  }
}
