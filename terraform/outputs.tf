output "namespace" {
  value = kubernetes_namespace.loja_veloz.metadata[0].name
}
