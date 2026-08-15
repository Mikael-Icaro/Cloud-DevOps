# Relatório Técnico — Loja Veloz

Cloud DevOps Engineering — migração da plataforma de pedidos de Docker Compose para Kubernetes, com CI/CD e observabilidade

## 1. Visão geral

O sistema "Pedidos Veloz" foi dividido em quatro serviços — Gateway, Pedidos, Estoque e Pagamentos — mais um banco PostgreSQL compartilhado. O Gateway concentra o tráfego de entrada e encaminha pra cada serviço interno; o serviço de Pedidos orquestra o fluxo de compra, chamando Estoque (reserva de item) e Pagamentos (processamento) de forma síncrona via HTTP.

A escolha por HTTP síncrono entre os serviços, em vez de mensageria assíncrona desde o início, foi deliberada: com quatro serviços e um único fluxo de negócio (criar pedido), a complexidade operacional de um broker não se paga ainda. O evento `PedidoCriado` já fica registrado numa tabela de log dentro do próprio Postgres, prontinho pra virar publicação num broker quando surgir um segundo consumidor (ex.: notificação por e-mail, atualização de um painel de BI). Documentar essa fronteira é mais importante do que adicionar RabbitMQ só porque o enunciado menciona.

## 2. Ambiente local com Docker Compose

Os cinco serviços (quatro aplicações + Postgres) sobem com `docker compose up --build -d`, um único comando, conforme exigido. O compose usa nomes de imagem totalmente qualificados (`docker.io/library/postgres:16-alpine`) em vez de nomes curtos — isso evita ambiguidade de registry (o Podman, usado aqui como motor de containers, se recusa a resolver nomes curtos sem confirmação interativa) e também reduz a superfície pra ataques de typosquatting em nomes de imagem parecidos com os oficiais.

Rede isolada (`loja-veloz`, driver bridge) conecta os serviços entre si por nome de serviço (DNS interno do Compose); só o Gateway expõe porta pro host (`8080`). Variáveis de ambiente diferenciam segredo (senha do banco, vinda de `.env`, fora do controle de versão) de configuração (URLs internas dos serviços). O Postgres tem healthcheck via `pg_isready`, e os serviços dependentes usam `depends_on: condition: service_healthy` pra não tentar conectar antes do banco estar pronto — mesmo assim, cada serviço implementa retry com backoff na inicialização (`_connect_com_retry`), porque em produção não existe "esperar o banco subir primeiro" — os pods podem reiniciar em qualquer ordem.

Validação: o fluxo completo (criar pedido → reservar estoque → processar pagamento → confirmar ou compensar) foi testado manualmente via `curl` contra o Gateway, incluindo o caminho de erro (estoque insuficiente retorna 409, pagamento recusado devolve o item reservado ao estoque).

## 3. Conteinerização e versionamento

Cada serviço tem um Dockerfile multi-stage com três estágios: `base` (imagem Python enxuta), `deps` (instala dependências isoladas em `--user`) e o estágio final, que copia só o necessário do estágio de dependências — o resultado não carrega compilador nem cache do pip na imagem final.

Práticas de segurança aplicadas em todos os quatro Dockerfiles:

- Usuário não-root dedicado (`appuser`, UID 10001) — a imagem nunca roda como root, nem em desenvolvimento nem em produção, o que elimina uma classe inteira de escalonamento de privilégio caso o processo da aplicação seja comprometido.
- Imagem base fixada por tag e totalmente qualificada (`docker.io/library/python:3.12-slim`), reduzindo a superfície de dependências desnecessárias em relação a uma imagem completa.
- `HEALTHCHECK` embutido, batendo em `/healthz`.

As imagens são versionadas com duas tags no pipeline de CI/CD: `latest` e o SHA do commit — a segunda garante rastreabilidade exata entre uma imagem rodando em produção e o código que a gerou, algo que `latest` sozinho nunca oferece.

## 4. Kubernetes — produção mínima

Os manifests ficam em `k8s/base/`, organizados um arquivo por recurso lógico (namespace, configmap, secret, um arquivo por serviço com Deployment + Service, e um arquivo de HPA). Validados de ponta a ponta num cluster kind local antes de considerar a entrega pronta — os nove pods (Postgres + 2 réplicas de cada um dos quatro serviços) sobem, ficam prontos, e o fluxo de criação de pedido funciona via `kubectl port-forward` no Gateway, com o mesmo resultado observado no Compose.

**ConfigMap e Secret.** Dados não sensíveis (nomes de banco, URLs internas) ficam no ConfigMap `loja-veloz-config`; credenciais (senha do Postgres, string de conexão completa) ficam no Secret `loja-veloz-secrets`. O repositório inclui só um `secret.example.yaml` como referência — o Secret real é criado via `kubectl create secret` ou, num pipeline de produção, injetado por um cofre externo (Vault, Sealed Secrets).

**Probes.** Todos os serviços de aplicação definem `readinessProbe` em `/readyz` (que confere conexão com o banco) e `livenessProbe` em `/healthz` (checagem rasa, sem tocar dependências externas — evita que uma falha no Postgres derrube desnecessariamente um pod que ainda está de pé). O Postgres usa `pg_isready` como probe.

**Segurança e Pod Security Admission.** Os quatro serviços de aplicação rodam com `runAsNonRoot`, UID fixo (10001), `readOnlyRootFilesystem: true`, todas as capabilities do Linux removidas (`drop: ["ALL"]`) e `allowPrivilegeEscalation: false`. O namespace usa o perfil `baseline` do Pod Security Admission, não `restricted` — a exceção documentada é o container de inicialização do Postgres (`ajustar-permissoes`), que precisa rodar como root uma única vez pra corrigir a posse do diretório de dados montado por um provisionador de volume que cria o diretório como `root:root`. Essa é uma limitação conhecida de rodar Postgres self-hosted em Kubernetes sob políticas restritivas — em produção, a alternativa mais comum é usar um banco gerenciado pelo provedor de nuvem justamente pra não herdar esse tipo de problema operacional.

**Escalabilidade.** HPA baseado em CPU (alvo 70% de utilização) nos Deployments de Gateway e Pedidos — os dois pontos que mais sentem um pico de campanha promocional, já que concentram, respectivamente, todo o tráfego de entrada e a orquestração do fluxo de compra. Estoque e Pagamentos ficam fixos em 2 réplicas no MVP; entram no HPA se o padrão de tráfego observado em produção justificar.

## 5. CI/CD

O pipeline (`.github/workflows/ci-cd.yml`) roda em dois jobs:

1. **`test`**, em matriz por serviço (gateway, pagamentos, estoque, pedidos), com um Postgres como serviço do próprio job do GitHub Actions. Cada serviço é testado isoladamente: `ruff check` pra lint, depois `pytest`. Isolar por serviço significa que uma falha de teste no Estoque não impede validar o Gateway — o feedback chega mais rápido e mais específico do que rodar tudo como um monólito de CI.
2. **`build-and-push`**, que só roda depois que `test` passa e só em push pra `main` (não em pull request, pra não publicar imagem de código ainda em revisão). Builda e publica as quatro imagens no GitHub Container Registry com duas tags (`latest` e SHA do commit), e roda uma varredura de vulnerabilidades com Trivy contra a imagem recém-publicada.

Segredos do pipeline usam o `GITHUB_TOKEN` padrão do Actions (com permissão `packages: write`), sem precisar cadastrar credencial adicional pra publicar no GHCR.

## 6. Observabilidade

A camada de observabilidade roda separada do compose principal (`docker-compose.observability.yml`), evitando obrigar quem só quer rodar a aplicação a subir Prometheus, Grafana e Jaeger junto.

- **Métricas**: cada serviço expõe `/metrics` em formato Prometheus (via `prometheus-fastapi-instrumentator`) — latência por rota, contagem de requisições por status HTTP. O Prometheus faz scrape dos quatro serviços a cada 10 segundos.
- **Tracing distribuído**: instrumentado com OpenTelemetry (não é só conceitual) — cada requisição HTTP, chamada entre serviços e query no Postgres vira um span, exportado via OTLP pro Jaeger. Um pedido criado através do Gateway gera um único trace com 25 spans atravessando os quatro serviços, incluindo as queries de reserva de estoque e o registro do pedido no banco — validado diretamente na API do Jaeger antes de considerar essa parte pronta.
- **Logs**: seguem a convenção de container (stdout, capturados por `docker compose logs` ou `kubectl logs`). Não foi montado um agregador dedicado (Loki, ELK) nesta fase — com quatro serviços e o volume de tráfego de um MVP, correlacionar logs manualmente por `trace_id` (já presente nos logs de acesso do Uvicorn) é suficiente; um agregador central se justifica quando o número de instâncias tornar `kubectl logs` inviável.

## 7. Estratégia de deploy

`Deployment` do Kubernetes já aplica rolling update por padrão — a estratégia escolhida para este MVP. Blue-green e canary foram descartados por ora: os dois exigem manter infraestrutura duplicada (ou um proxy de roteamento por peso de tráfego) que não se justifica antes de existir volume de produção real para medir o risco de um rollout. Rolling update, combinado com as readiness probes já configuradas, já garante que o Kubernetes só direciona tráfego pra um pod novo depois que ele passa a responder `/readyz` — o suficiente pra reduzir o risco de indisponibilidade durante deploy, que era justamente um dos problemas relatados pela Loja Veloz.

## 8. Infraestrutura como código

Esqueleto em `terraform/`, usando OpenTofu em vez de Terraform (mesma linguagem HCL; o Fedora não empacota mais o Terraform depois da mudança de licença pra BUSL em 2023, e o OpenTofu resolve isso sem trocar de sintaxe). O esqueleto atual declara o namespace do Kubernetes e uma `ResourceQuota` — os manifests de aplicação continuam em YAML puro em `k8s/base/`, por serem mais simples de revisar num pull request do que expressos como recursos Terraform. A evolução natural, conforme o time crescer, é migrar esses YAMLs para o provider `kubernetes` do Terraform/OpenTofu e adicionar os recursos de infraestrutura gerenciada do provedor de nuvem escolhido (cluster gerenciado, registry, rede) como providers adicionais no mesmo esqueleto.

## 9. O que fica para depois

- Mensageria dedicada, quando existir um segundo consumidor do evento `PedidoCriado`.
- Agregador de logs centralizado, quando o número de instâncias tornar `kubectl logs` operacionalmente inviável.
- Banco de dados gerenciado (RDS/Cloud SQL ou equivalente), pra não depender de rodar Postgres self-hosted sob Pod Security restritivo.
- Ingress com TLS na frente do Gateway — o MVP usa `port-forward` pra demonstração; produção precisa de um Ingress Controller e certificado.
