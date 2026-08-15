# Roteiro do vídeo pitch (até 4 minutos)

## Antes de gravar

Deixe essas abas/janelas já abertas, nesta ordem (alterna entre elas com Alt+Tab durante a gravação, não precisa abrir nada na hora):

1. VS Code, com a pasta `loja-veloz` aberta e o arquivo `README.md` visível
2. Terminal, na pasta do projeto (`cd ~/projects/loja-veloz`)
3. Navegador com 4 abas: `localhost:8001/docs` (Pedidos), a aba de Actions do seu repositório no GitHub, `localhost:16686` (Jaeger) e `localhost:9090/targets` (Prometheus)

Confirme antes de começar que tudo está de pé:

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml ps
```

Todos os serviços devem aparecer `Up`. Se algo não estiver rodando, suba de novo:

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

Ferramenta de gravação: grave a tela inteira (não só uma janela), assim as trocas de aba ficam naturais. Fale olhando pra tela, não precisa aparecer no vídeo.

---

## Script

### 0:00 – 0:20 — Abertura (tela: README no VS Code)

> "Esse é o projeto da Loja Veloz, um e-commerce fictício que estava sofrendo com deploys arriscados e dificuldade de escalar. Minha proposta foi migrar de um ambiente local em Docker Compose pra Kubernetes, com pipeline de CI/CD e observabilidade de ponta a ponta. Vou mostrar tudo funcionando de verdade, não só o código."

### 0:20 – 1:00 — Arquitetura (tela: VS Code, pasta `services/`)

> "O sistema tem quatro serviços: um Gateway que recebe todo o tráfego, e três serviços internos — Pedidos, Estoque e Pagamentos — cada um com seu próprio código, isolado dos outros. Quando um pedido é criado, o serviço de Pedidos reserva o item no Estoque, processa o pagamento, e se algo falhar no meio do caminho, ele desfaz a reserva automaticamente. Isso já é uma diferença importante de um monolito: cada peça pode falhar, escalar e ser atualizada sem derrubar o resto."

Aponte rapidamente pras pastas `services/gateway`, `services/pedidos`, `services/estoque`, `services/pagamentos` enquanto fala.

### 1:00 – 1:50 — Ambiente local funcionando (tela: terminal + navegador)

No terminal:

```bash
docker compose ps
```

> "Esse é o ambiente local: cinco containers, o Postgres e os quatro serviços, tudo sobe com um único comando, `docker compose up`. Vou criar um pedido de verdade."

Troque pra aba `localhost:8001/docs`, clique em `POST /pedidos` → **Try it out**, preencha e clique **Execute**:

```json
{"cliente":"Maria","sku":"SKU-001","quantidade":2,"valor":150.00}
```

> "Pedido criado, status confirmado. Por trás disso, o serviço de Pedidos chamou o Estoque pra reservar o item e o Pagamentos pra processar a cobrança — tudo validado."

### 1:50 – 2:30 — Kubernetes (tela: terminal)

```bash
kubectl get pods -n loja-veloz
```

> "Essa mesma aplicação também roda em Kubernetes — validei isso num cluster local antes de considerar pronto. Nove pods: o Postgres e duas réplicas de cada serviço, pra já nascer tolerante a falha. Os manifests definem CPU e memória, sondas de saúde, e os containers rodam sem privilégio de root, com o sistema de arquivos somente leitura — reduz bastante a superfície de ataque."

Opcional, se der tempo: mostre rapidamente o arquivo `k8s/base/gateway.yaml` no VS Code, apontando pro `securityContext` e pro `HorizontalPodAutoscaler`.

### 2:30 – 3:00 — CI/CD (tela: aba do GitHub Actions)

> "Todo push pra main dispara o pipeline: lint, testes automatizados com um banco de dados real, e só depois disso passar, ele builda e publica as quatro imagens. Esse é o último run, todo verde."

Mostre a lista de jobs (test + build-and-push) todos com o check verde.

### 3:00 – 3:40 — Observabilidade (tela: Jaeger, depois Prometheus)

Na aba do Jaeger, busque um trace recente do serviço `gateway`:

> "Isso aqui é um trace distribuído — o pedido que acabei de criar, atravessando os quatro serviços e as consultas no banco, tudo correlacionado num único ID. Numa arquitetura de microsserviços, sem isso, rastrear onde uma falha aconteceu vira quase impossível."

Troque pra aba do Prometheus:

> "E aqui, as métricas de cada serviço sendo coletadas em tempo real — latência, taxa de erro, tudo alimentando os dashboards do Grafana."

### 3:40 – 4:00 — Fechamento (tela: README ou câmera, se aparecer)

> "Resumindo: ambiente local reproduzível, Kubernetes com segurança e escalonamento automático, CI/CD validando cada mudança antes de publicar, e observabilidade completa pra diagnosticar problemas rápido. É exatamente o que a Loja Veloz precisava pra parar de temer os próprios deploys."

---

## Se passar do tempo

Corte primeiro a parte de Kubernetes (1:50–2:30) reduzindo pra só `kubectl get pods` sem abrir o YAML — dá pra economizar uns 20 segundos aí sem perder o essencial.
