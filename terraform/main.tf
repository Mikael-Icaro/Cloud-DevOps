provider "kubernetes" {
  config_path = var.kubeconfig_path
}

# Esqueleto de IaC: o objetivo aqui nao e reescrever os manifests que ja
# existem em k8s/base (mantidos como YAML puro, mais faceis de revisar em PR
# e de aplicar manualmente durante o MVP), e sim mostrar como a
# infraestrutura em volta da aplicacao -- namespace, cotas de recursos --
# passaria a ser declarada e versionada assim que o time crescer.
#
# Evolucao natural pra producao: trocar isso por um modulo que aplica os
# YAMLs de k8s/base via kubectl_manifest ou kubernetes_manifest, e adicionar
# os recursos de infraestrutura gerenciada do provedor de nuvem escolhido
# (cluster gerenciado, registry, rede) como providers adicionais.

resource "kubernetes_namespace" "loja_veloz" {
  metadata {
    name = var.namespace

    labels = {
      "pod-security.kubernetes.io/enforce" = "baseline"
      "pod-security.kubernetes.io/audit"   = "restricted"
      "pod-security.kubernetes.io/warn"    = "restricted"
    }
  }
}

resource "kubernetes_resource_quota" "loja_veloz" {
  metadata {
    name      = "loja-veloz-quota"
    namespace = kubernetes_namespace.loja_veloz.metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = "2"
      "requests.memory" = "2Gi"
      "limits.cpu"      = "4"
      "limits.memory"   = "4Gi"
      "pods"            = "30"
    }
  }
}
