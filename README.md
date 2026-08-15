# Loja Veloz — Pedidos

Plataforma de pedidos em microsserviços da Loja Veloz, migrando de um ambiente local em Docker Compose para produção em Kubernetes, com pipeline de CI/CD e observabilidade.

## Arquitetura

```
                    ┌─────────────┐
   cliente ───────► │   Gateway   │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  ┌───────────┐     ┌────────────┐     ┌─────────────┐
  │  Pedidos  │────►│  Estoque   │     │ Pagamentos  │
  └─────┬─────┘     └─────┬──────┘     └─────────────┘
        │                 │                    ▲
        └────────────►────┴────────────────────┘
        ▼
  ┌───────────┐
  │ PostgreSQL│
  └───────────┘
```

O Gateway expõe uma única porta externa e encaminha requisições para os serviços internos (`/api/pedidos/...`, `/api/estoque/...`, `/api/pagamentos/...`). O serviço de Pedidos orquestra a criação de um pedido: reserva o item no Estoque, processa o pagamento e grava o resultado no Postgres, incluindo um evento `PedidoCriado` numa tabela de log (ver seção Mensageria).

## Rodando localmente

Requisitos: Podman + podman-compose (ou Docker + Docker Compose, ambos funcionam com o mesmo `docker-compose.yml`).

```bash
cp .env.example .env
docker compose up --build -d
```

Isso sobe os 5 serviços com um único comando. Confira o status com `docker compose ps` — todos devem aparecer como `Up`.

Testando o fluxo:

```bash
curl http://localhost:8080/api/estoque/itens/SKU-001

curl -X POST http://localhost:8080/api/pedidos/pedidos \
  -H "Content-Type: application/json" \
  -d '{"cliente":"Maria","sku":"SKU-001","quantidade":2,"valor":150.00}'

curl http://localhost:8080/api/pedidos/pedidos/<id-retornado>
```

Pagamentos recusa cerca de 10% das transações de propósito, pra dar sinal de vida ao fluxo de compensação (o item reservado volta pro estoque quando o pagamento falha).

Pra derrubar tudo: `docker compose down` (ou `docker compose down -v` pra apagar também o volume do Postgres).

### Nota sobre Podman

Como o Podman exige o nome completo da imagem pra evitar ambiguidade entre registries (ex.: `docker.io/library/postgres:16-alpine` em vez de só `postgres:16-alpine`), todas as imagens neste repositório já estão qualificadas — evita tanto o prompt interativo do Podman quanto ataques de typosquatting em nomes curtos de imagem.

## Serviços

| Serviço | Porta interna | Responsabilidade |
|---|---|---|
| gateway | 8000 (exposta em 8080) | Roteamento HTTP pros serviços internos |
| pedidos | 8000 | Orquestra criação de pedido, grava no Postgres |
| estoque | 8000 | Reserva e reposição de itens |
| pagamentos | 8000 | Simula integração com gateway de pagamento externo |
| postgres | 5432 | Persistência de pedidos, estoque e eventos |

Cada serviço tem `/healthz` (liveness) e `/readyz` (readiness).

## Mensageria

O evento `PedidoCriado` é gravado hoje numa tabela `eventos` no próprio Postgres, não num broker dedicado (RabbitMQ/Kafka). Pra um único consumidor (o próprio serviço de Pedidos, no MVP), um broker adicionaria complexidade operacional sem ganho real. Fica documentado como próximo passo assim que surgir um segundo consumidor do evento (ex.: um serviço de notificação por e-mail).

## Kubernetes, CI/CD, observabilidade, Terraform

Ver `k8s/`, `.github/workflows/`, `terraform/` e `docs/relatorio-tecnico.md` para o restante da entrega.
