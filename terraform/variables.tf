variable "kubeconfig_path" {
  description = "Caminho do kubeconfig do cluster onde a Loja Veloz vai rodar"
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Namespace onde os recursos da aplicacao sao criados"
  type        = string
  default     = "loja-veloz"
}

variable "image_tag" {
  description = "Tag das imagens publicadas pelo pipeline de CI/CD (normalmente o SHA do commit)"
  type        = string
  default     = "latest"
}

variable "replicas" {
  description = "Numero minimo de replicas por servico, antes de o HPA entrar em acao"
  type        = map(number)
  default = {
    gateway    = 2
    pedidos    = 2
    estoque    = 2
    pagamentos = 2
  }
}
