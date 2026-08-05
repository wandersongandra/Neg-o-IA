# ROADMAP NEGÃO AI — Visão de 10 Anos (2026–2036)

*Relatório de planejamento do Arquiteto Principal. Sem código — apenas estratégia, escopo, critérios verificáveis e cronograma.*

---

## 1. Princípios e Decisões de Arquitetura (justificadas)

| Decisão | Escolha | Justificativa |
|---|---|---|
| Repositório | Monorepo (apps, packages, infra, docs) | Uma única fonte de verdade; mudanças atômicas entre API, agentes e frontend; CI simples |
| Banco relacional | PostgreSQL 17 | Transações ACID para memória e conhecimento; maturidade; menos infra |
| Embeddings | pgvector (dentro do Postgres) | **Escolhido sobre Qdrant na fundação**: 1 banco só, backup/restore único, custo operacional menor. Qdrant fica como adaptador opcional futuro (interface de vetor plugável) |
| Cache/memória curta | Redis 7 | TTL natural para memória de trabalho; pub/sub para eventos leves; Redis Streams para fila de eventos na fundação (sem adicionar broker na v0) |
| API | FastAPI (async) + WebSockets | Streaming de respostas, alta concorrência, OpenAPI gratuito |
| ORM/migração | SQLAlchemy 2.0 (async) + Alembic | Padrão de mercado, migrações auditáveis |
| Modelos | NVIDIA API + GPT-OSS-120B atrás de **Model Router** | Zero lock-in: qualquer provedor entra como um adaptador; roteamento por custo/latência/capacidade |
| Observabilidade | OpenTelemetry + Prometheus/Grafana/Loki + Sentry | Métricas, logs e traces correlacionados desde o dia 1 |
| Frontend | Next.js + React + Tailwind + TypeScript | Ecossistema maduro; SSR para dashboard; mesma tipagem via OpenAPI gerado |
| Deploy | Docker Compose → VPS Linux → Kubernetes | Progressão natural: Compose na fundação (simples), K8s só na v5 (quando houver escala real) |
| Config | pydantic-settings + secrets via env | Configuração versionada, segredos fora do repositório |
| Segurança | API keys + RBAC por nível (v3) + sandbox de execução | Tool Manager só nasce com níveis de autorização |

**Princípio central:** uma única inteligência, memória única, evolução contínua. Toda feature nova precisa de memória, evento e observabilidade — nada é "cola".

---

## 2. Visão Geral das Versões

| Versão | Tema | Período | Duração | Resumo |
|---|---|---|---|---|
| v0.x | Fundação | ago/2026 – nov/2026 | ~4 meses | Infra, API, banco, eventos, observabilidade, deploy |
| v1.0 | Núcleo Vivo | dez/2026 – mai/2027 | ~6 meses | Conversa natural, Model Router, memória, planner básico, dashboard v0 |
| v2.0 | Cérebro que Aprende | jun/2027 – jan/2028 | ~8 meses | Aprendizado contínuo, Knowledge Vault, memórias episódica/procedural, agendador, automações simples |
| v3.0 | Mãos | fev/2028 – nov/2028 | ~10 meses | Tool Manager, plugins, autorização granular, execução com confirmação |
| v4.0 | Sentidos | dez/2028 – nov/2029 | ~12 meses | Voz, visão, observação de ambiente, multimodalidade |
| v5.0 | Maturidade | dez/2029 – mai/2031 | ~18 meses | Autonomia com validação, automações complexas, K8s, multi-usuário, custo otimizado |
| v6.0+ | Evolução Contínua | jun/2031 – 2036 | contínuo | Auto-melhoria, metacognição, inteligência ambiental 24/7 |

---

## 3. Roadmap Detalhado por Versão

### v0.x — FUNDAÇÃO (ago/2026 – nov/2026)

**Objetivo central:** ter o sistema **rodando e observável** em produção (VPS), com todas as bases sólidas para receber inteligência.

**Escopo por módulo:**
- **Infraestrutura:** monorepo, Docker Compose (dev/prod), Makefile/task runner, GitHub Actions (lint, testes, build, push de imagem).
- **API:** FastAPI com health check, autenticação por API key, rate limiting, WebSockets (ping/pong, eventos de vida).
- **Database:** PostgreSQL 17 + pgvector + Redis, SQLAlchemy async, Alembic com migração inicial, backups automáticos.
- **Events:** barramento de eventos (Redis Streams), contrato de eventos versionado, dead-letter.
- **Configuration:** pydantic-settings, ambientes dev/staging/prod, secrets via env.
- **Security:** criptografia de segredos, HTTPS, firewall UFW, fail2ban, auditoria básica de acesso.
- **Monitoring:** OpenTelemetry, métricas de API/cache/banco, logs estruturados (JSON), Loki/Grafana, alertas (webhook), Sentry.
- **Deploy:** script `deploy.sh` idempotente, health checks pós-deploy, rollback por tag de imagem.

**Pronto = quando:**
- `docker compose up` sobe o ambiente completo em < 10 min com 1 comando, sem erros.
- P95 de resposta da API de health < 100ms; uptime da VPS ≥ 99% por 2 semanas consecutivas.
- > 90% do código de infra coberto por testes de integração (subir/derrubar stack, migração de cima pra baixo).
- 100% dos eventos publicados em prod possuem métrica e log correlacionados (trace ID).
- Restauração de backup validada: banco restaurado em < 30 min com perda de dados = 0 (teste executado 1x).
- Deploy completo (code → prod) < 15 min, automatizado, sem passos manuais.

**Dependências:** nenhuma (é a fundação).

**Riscos e mitigação:**

| Risco | Mitigação |
|---|---|
| VPS insuficiente p/ IA | Teste de carga na v0.5; plano de upgrade e cota de recursos no Compose |
| Perda de dados | Backups diários + WAL arquivado + teste de restauração mensal |
| Scope creep de infra | Non-goals rígidos; qualquer feature "legal" entra na lista da v1 |
| Falha de migração em prod | Alembic com `downgrade` testado, deploy azul-verde desde o início |

**Non-goals (fora da v0.x):** nenhum ML, nenhum modelo, nenhuma conversa, nenhuma UI rica, sem tooling, sem voz/visão, sem multi-usuário, sem K8s, sem autenticação por email/senha (só API key).

---

### v1.0 — NÚCLEO VIVO (dez/2026 – mai/2027)

**Objetivo central:** o NEGÃO **conversa naturalmente**, lembra de você e de conversas anteriores, e planeja tarefas simples — tudo servido por um Model Router plugável.

**Escopo por módulo:**
- **Configuration:** catálogo de modelos (NVIDIA API + GPT-OSS-120B), chaves por provedor, seleção de modelo padrão.
- **Brain (Model Router):** adaptadores plugáveis, timeout, retry, circuit breaker, fallback automático, roteamento por heurística (tarefa → custo/latência → modelo), cache de respostas.
- **Memory:** memória de curto prazo (Redis, TTL 24h — contexto da sessão); memória de longo prazo (pgvector, embeddings); extração de fatos da conversa; consolidação noturna.
- **Conversation:** gestão de sessões (retomável), contexto limitado por tokens, persona do NEGÃO, streaming de respostas via WebSocket, respostas em PT-BR.
- **Planner:** parser de planos (JSON estruturado a partir de LLM), planos de 2–3 passos executados por pipeline interno (sem tools externos), reavaliação após falha.
- **Learning (mínimo):** registro de interações para replay (base do aprendizado futuro).
- **Events/API/Database/Monitoring:** extensões dos contratos da v0.
- **Dashboard v0 (Next.js):** chat funcional, histórico de conversas, status do router, métricas simples.

**Pronto = quando:**
- Conversa ponta-a-ponta (envio → primeira token → resposta completa) com **p95 < 2,5s**.
- Recall de memória de longo prazo: informação gravada ontem recuperada em **p95 < 300ms** com precisão@10 ≥ 0,85 em dataset de avaliação (100 perguntas).
- Continuidade: conversa interrompida retomada com contexto intacto em ≥ 95% dos casos.
- Fallback: falha do provedor primário → resposta em < 5s via secundário, com alerta emitido.
- Custo médio por conversa < US$ 0,05 (monitorado por sessão).
- 80% das tarefas de 2–3 passos do benchmark de 50 tarefas concluídas com sucesso.
- Dashboard carrega em < 2s e exibe todas as métricas do router.

**Dependências:** v0.x (infra, eventos, observabilidade).

**Riscos e mitigação:**

| Risco | Mitigação |
|---|---|
| Modelo instável/indisponível | Fallback + circuit breaker + cache semântico |
| Custo fora de controle | Budget por sessão/dia, roteamento econômico, alerta de gasto |
| Memória poluída (fatos errados) | Confiança mínima, extração com curadoria na v2 |
| Latência alta em VPS | Teste de carga, priorização de modelos rápidos, possível upgrade |

**Non-goals:** sem execução de ferramentas externas, sem voz/visão, sem aprendizado contínuo automático, sem Knowledge Vault, sem agendador, sem multi-usuário, sem K8s, sem observação de ambiente.

---

### v2.0 — CÉREBRO QUE APRENDE (jun/2027 – jan/2028)

**Objetivo central:** o NEGÃO **aprende sozinho** com cada interação, constrói uma base de conhecimento permanente e começa a agir no tempo (agendador) com automações simples.

**Escopo por módulo:**
- **Learning:** loop contínuo (captura → extração → validação → persistência), aprendizagem por reforço leve (feedback explícito do usuário), deduplicação e fusão de fatos.
- **Knowledge:** Knowledge Vault (documentos, notas, projetos do usuário), ingestão de PDFs/Markdown/URLs autorizadas, embeddings + chunking, busca semântica, citações de fonte.
- **Memory:** memória episódica (eventos passados — "ontem você fez X"), memória procedural (como fazer tarefas repetidas, lições aprendidas).
- **Scheduler:** agendador de tarefas (horário, recorrência, one-shot), persistência, recuperação pós-reboot, notificação de execução.
- **Automation:** automações simples (regras "quando X → faça Y" restritas ao mundo interno: responder, resumir, lembrar, consultar knowledge).
- **Events/Monitoring:** métricas do loop de aprendizado (fatos/dia, precisão de extração), auditoria de automações.
- **Planner:** planos mais longos com memória procedural como contexto.

**Pronto = quando:**
- ≥ 5 fatos úteis extraídos por dia de uso real, com ≥ 80% de precisão validada por amostragem semanal (50 fatos/semana revisados).
- Knowledge Vault: pergunta sobre documento ingerido respondida com **p95 < 1s** e citação da fonte correta em ≥ 90% dos casos.
- Pergunta "o que fizemos no projeto X em junho?" respondida a partir da memória episódica em ≥ 85% dos casos.
- 0 tarefas agendadas perdidas por reboot (recuperação em < 1 min); atraso de execução < 5s.
- Precisão de deduplicação: < 5% de fatos duplicados no vault.
- 90% das automações simples completadas com sucesso e auditáveis (log de execução completo).

**Dependências:** v1.0 (conversa + memórias são a fonte do aprendizado).

**Riscos e mitigação:**

| Risco | Mitigação |
|---|---|
| Aprendizado tóxico (fatos errados se propagam) | Filtros de extração, revisão amostral, rollback por fato |
| Vault cresce sem controle | Política de TTL/importância, arquivamento, limites de ingestão |
| Agendador falho em reinício | Journaling + recuperação, teste de reboot automatizado |
| Automação surpreendente | Todas as automações da v2 são informativas (nunca destrutivas) |

**Non-goals:** sem plugins/ferramentas externas (sem GitHub, sem terminal, sem Docker), sem voz/visão, sem observação de ambiente, sem autonomia, sem multi-usuário, sem automações que modificam sistemas externos.

---

### v3.0 — MÃOS (fev/2028 – nov/2028)

**Objetivo central:** o NEGÃO **executa no mundo real** — com autorização granular e confirmação — via Tool Manager e plugin: GitHub, Docker, SSH, Cloudflare, Coolify, arquivos e terminal.

**Escopo por módulo:**
- **Tool Manager:** registro/descoberta de ferramentas, schema de chamada (JSON Schema), validação de argumentos, sandbox de execução, timeout e retry, histórico de execução.
- **Plugins v1:** arquivos (ler/escrever/renomear), terminal (comandos aprovados), HTTP/API (requisições autorizadas), GitHub (PRs, issues, deploys), Docker (containers, compose), SSH (hosts autorizados), Cloudflare/Coolify (DNS, deploy).
- **Security:** níveis de autorização (ler / executar / destrutivo), matriz por ferramenta, confirmação obrigatória para ações destrutivas, auditoria completa (quem/o quê/quando), escopo por host.
- **Authorization Flow:** pedido de permissão assíncrono (chat/dashboard), token de sessão de execução, revogação.
- **Planner:** planos longos multi-passos com uso de ferramentas, rollback de plano em falha.
- **Automation:** automações que usam ferramentas (com política de aprovação por tipo de ação).
- **Monitoring:** métricas por ferramenta (sucesso, latência, frequência), alerta de anomalia de execução.

**Pronto = quando:**
- 100% das ações destrutivas (delete, overwrite, deploy, shell) exigem confirmação explícita; 0 exceções em auditoria.
- Taxa de sucesso de execução de ferramentas ≥ 95% (benchmark de 200 chamadas por ferramenta).
- Execução "ler terminal/GitHub/arquivos" ≤ 3s p95; ações com confirmação completa em ≤ 30s.
- Sandbox: comando malicioso em terminal não alcança o host (teste de segurança automatizado, 20 payloads).
- Auditoria 100%: toda execução possui registro com resultado e hash do estado; consultável em < 500ms.
- Revogação de autorização refletida em < 5s (sem nova execução permitida).
- Plugin novo conectado em < 1 dia de trabalho (SDK + exemplo documentado).

**Dependências:** v2.0 (memória procedural dá contexto de execução; agendador dispara automações).

**Riscos e mitigação:**

| Risco | Mitigação |
|---|---|
| **Execução destrutiva por engano** | Confirmação obrigatória + allowlist por host + sandbox + dry-run padrão |
| Token/credenciais vazando | Secret vault, nunca logar segredos, rotação automática |
| Loop infinito de ações | Orçamento de passos por plano, limit de execução por minuto |
| Plugin quebrado quebrando o core | Plugin roda em processo isolado (subprocess/container leve) |

**Non-goals:** sem voz/visão, sem observação de ambiente (IDE/terminal), sem autonomia (tudo relevante pede confirmação), sem multi-usuário, sem K8s, sem auto-deploy do próprio NEGÃO.

---

### v4.0 — SENTIDOS (dez/2028 – nov/2029)

**Objetivo central:** o NEGÃO **vê e ouve** — voz, visão e observação do ambiente do usuário (IDE, terminal, docs), tornando as interações multimodais.

**Escopo por módulo:**
- **Voice:** STT (transcrição em PT-BR), TTS (resposta falada), sessões de voz via WebSocket, comutação voz↔texto, hotword de ativação.
- **Vision:** análise de imagens (prints, capturas autorizadas, uploads), OCR, descrição e Q&A sobre imagens, leitura de código de tela.
- **Observation:** captura autorizada de contexto do ambiente — janela do IDE, terminal, documento ativo, clipboard — com políticas de privacidade estritas (opt-in por janela), resumos periódicos.
- **Memory multimodal:** álbum de imagens, clips de áudio na memória episódica, busca por imagem/texto.
- **Learning:** aprendizado a partir de observações (padrões de trabalho do usuário), sem cruzar a linha da vigilância — regras de consentimento explícitas.
- **Automation/Planner:** tarefas com entradas multimodais (ex: "leia esse print e crie a issue").
- **Dashboard:** player de voz, histórico de observações autorizadas, gestão de permissões de sensores.

**Pronto = quando:**
- STT em PT-BR com WER ≤ 10% em ambiente silencioso; STT→resposta→TTS com **p95 < 4s**.
- Análise de imagem: Q&A sobre screenshot com precisão ≥ 85% em benchmark de 100 imagens; OCR de código com erro < 2%.
- Observação: contexto do ambiente capturado e resumido em < 5s quando solicitado; 0 capturas sem autorização explícita (auditável).
- 95% das sessões de voz sobrevivem à interrupção (retomada com contexto).
- Privacidade: 100% das capturas registradas com consentimento e revogação em < 10s.

**Dependências:** v3.0 (voz que executa precisa de ferramentas; ex: "mexa naquele arquivo que estou vendo").

**Riscos e mitigação:**

| Risco | Mitigação |
|---|---|
| Privacidade/consentimento violado | Opt-in por sensor/janela, indicador visual de captura, revogação instantânea |
| Latência de voz | Modelos STT locais (whisper pequeno) + TTS em streaming |
| Custo de visão | Roteamento: modelo barato para OCR, caro para raciocínio |
| Sobrecarga de observação | Amostragem, resumos, política de retenção (TTL) |

**Non-goals:** sem autonomia (observa, não age sem pedir), sem câmera de vídeo contínua, sem vigilância de e-mail/mensagens pessoais, sem multi-usuário, sem K8s.

---

### v5.0 — MATURIDADE (dez/2029 – mai/2031)

**Objetivo central:** o NEGÃO **opera com autonomia validada** — executa tarefas complexas de ponta a ponta, escala para múltiplos usuários/instâncias, custa pouco e continua evoluindo.

**Escopo por módulo:**
- **Autonomy:** execução autônoma com **validação por políticas** (níveis de autonomia por domínio/tool), auto-verificação (dry-run → simulação → execução), plano de auto-auditoria, "human-in-the-loop" apenas para ações de alto risco.
- **Automation (complexa):** automações multi-passo com estado, retry inteligente, compensação/rollback, grafos de automação versionados.
- **Infra:** Kubernetes (produção), auto-scaling horizontal, rollout/rollback automático, multi-região opcional.
- **Multi-usuário/Multi-instância:** tenancy por usuário com memória isolada, ou multi-instância com orquestração central; quotas e custo por tenant.
- **Cost optimization:** roteamento econômico (cascata de modelos por dificuldade), cache semântico global, batching, compressão de memória, relatório mensal de custo por funcionalidade.
- **Learning/Memory:** compressão e poda de memória (importância decrescente), memória em camadas (hot/warm/cold).
- **Events/API/Monitoring:** API pública documentada, webhooks de saída, SLIs/SLOs formais.

**Pronto = quando:**
- ≥ 80% das tarefas do benchmark complexo (100 tarefas multi-passo) concluídas **sem intervenção humana**; 100% das aprovadas em simulação executadas sem efeito colateral não previsto.
- K8s: deploy canário com rollback em < 5 min; escalar de 1 → 10 instâncias sem downtime.
- Multi-usuário: 10 usuários simultâneos com isolamento completo (0 vazamentos em teste de invasão); latência p95 degradada em < 15% vs single-user.
- Custo por interação reduzido ≥ 40% vs v4 (via roteamento econômico + cache).
- SLA: uptime ≥ 99,5% mensal; p95 de conversa < 3s mesmo com carga alta.
- Tempo de recuperação de falha (MTTR) < 30 min com auto-healing.

**Dependências:** v3.0 (ferramentas), v4.0 (sentidos), v2.0 (aprendizado), v1.0 (conversa).

**Riscos e mitigação:**

| Risco | Mitigação |
|---|---|
| Autonomia com efeito colateral grave | Níveis de autonomia por domínio, simulação obrigatória, kill-switch por ferramenta |
| Multi-tenant com vazamento de memória | Isolamento lógico + testes de invasão contínuos |
| Complexidade K8s | Migração gradual (Compose → K8s), documentação, runbooks |
| Custo explode com escala | Quotas, orçamento por tenant, roteamento econômico obrigatório |

**Non-goals:** sem AGI/consciência (NEGÃO continua ferramenta com políticas), sem SaaS público multi-tenant na nuvem de terceiros (self-hosted), sem treinar modelo próprio, sem acesso não autorizado a terceiros.

---

### v6.0+ — EVOLUÇÃO CONTÍNUA (jun/2031 – 2036)

**Objetivo central:** o NEGÃO **evolui sozinho** dentro de limites seguros: auto-melhoria, metacognição e inteligência ambiental 24/7.

**Escopo (direções, refináveis ao longo do caminho):**
- Auto-melhoria supervisionada: o NEGÃO propõe melhorias em suas próprias automações e prompts, executadas com revisão.
- Metacognição: auto-avaliação de confiança, pedido de ajuda quando a incerteza é alta, explicação do próprio raciocínio.
- Inteligência ambiental: antecipar necessidades ("amanhã você tem reunião, preparei o resumo").
- Expansão de sentidos: contexto de tela contínuo autorizado, sentidos novos (fala natural com timbre próprio).
- Sustentação de todo o stack: adoção de modelos novos conforme o mercado muda.

**Pronto = quando:** definido ano a ano via OKRs; princípios fixos: segurança nunca diminui, memória do usuário é inviolável, custo por interação cai todo ano, 0 incidentes críticos não detectados.

---

## 4. Milestones da v1.0 — Sequência Semana a Semana (24 semanas)

| Semana | Entregável | Critério de saída |
|---|---|---|
| 1–2 | Monorepo + CI/CD completos (lint, typecheck, testes, build) + ambiente dev local | `make dev` sobe tudo; CI verde em 100% dos PRs |
| 3–4 | Camada de dados: PostgreSQL+pgvector, Redis, SQLAlchemy async, Alembic com migração base e rollback | `alembic upgrade head && downgrade base` sem erro; testes de integração de dados verdes |
| 5–6 | API Core: FastAPI, auth API key, rate limiting, WebSockets, schemas Pydantic, testes de contrato | API aceita 100 req/s com p95 < 150ms (teste de carga); WS conecta/desconecta estável |
| 7–8 | **Model Router v0**: adaptadores NVIDIA API e GPT-OSS-120B, timeout, retry, circuit breaker, fallback, cache | Falha injetada do primário → resposta em < 5s via fallback; cache hit < 200ms |
| 9–11 | **Memory**: curto prazo (Redis TTL) + longo prazo (pgvector), extração de fatos, consolidação noturna | Recall de fato de ontem p95 < 300ms, precisão@10 ≥ 0,85 (dataset de 100 perguntas) |
| 12–13 | **Conversation**: sessões retomáveis, persona, streaming de resposta, contexto por tokens | Retomada com contexto ≥ 95%; p95 ponta-a-ponta < 2,5s |
| 14–15 | **Planner v0**: parser de plano JSON, pipeline de execução interna (2–3 passos), retry e reavaliação | 80% de sucesso no benchmark de 50 tarefas |
| 16–17 | **Events + Monitoring**: eventos de conversa/memória/router, métricas OTel, logs JSON, dashboards, alertas | Toda ação tem trace ID; alerta de latência/custo/erro configurado e disparando |
| 18–19 | **Scheduler v0**: agendamento interno (APScheduler) com persistência e recuperação | Tarefa agendada executa no segundo previsto; pós-reboot recupera 100% |
| 20–21 | **Dashboard v0** (Next.js): chat, histórico, métricas, configuração do router | UI navegável; dashboard carrega < 2s |
| 22–23 | **Segurança/hardening**: secrets, auditoria, hardening Docker, testes de carga final | Sem segredo em repositório; auditoria de acesso completa |
| 24 | **Beta fechado + UAT**: 2 semanas de uso real, tuning, critérios de aceitação da v1.0 | Todos os critérios da v1.0 verificados; decisão de release |

---

## 5. Diagrama Mermaid — Gantt do Roadmap

```mermaid
gantt
    title ROADMAP NEGÃO AI - Visão 2026-2036
    dateFormat YYYY-MM-DD
    axisFormat %b/%Y

    section v0.x - Fundacao (4 meses)
    Monorepo + CI/CD                   :v01, 2026-08-01, 21d
    Docker Compose dev/prod            :v02, 2026-08-22, 21d
    API FastAPI + WebSockets + auth    :v03, 2026-09-12, 30d
    PostgreSQL + Alembic + Redis + pgvector :v04, 2026-10-12, 30d
    Eventos + Config + Observabilidade :v05, 2026-11-01, 29d
    Marco v0.5 operacional             :milestone, v0m, 2026-11-30, 0d

    section v1.0 - Nucleo Vivo (6 meses)
    Model Router v0 (adapters + fallback) :v11, 2026-12-01, 30d
    Memoria curto prazo (Redis)        :v12, 2026-12-31, 21d
    Memoria longo prazo (pgvector)     :v13, 2027-01-21, 42d
    Conversacao + sessoes + streaming  :v14, 2027-03-04, 42d
    Planner v0 + execucao interna      :v15, 2027-04-15, 30d
    Dashboard v0 (Next.js)             :v16, 2027-05-15, 16d
    Marco v1.0                         :milestone, v1m, 2027-05-31, 0d

    section v2.0 - Cerebro que Aprende (8 meses)
    Knowledge Vault + ingestao         :v21, 2027-06-01, 60d
    Aprendizado continuo + curadoria   :v22, 2027-08-01, 60d
    Memoria episodica + procedural     :v23, 2027-09-30, 60d
    Scheduler + automacoes simples     :v24, 2027-11-29, 45d
    Feedback loop + avaliacoes         :v25, 2028-01-13, 18d
    Marco v2.0                         :milestone, v2m, 2028-01-31, 0d

    section v3.0 - Maos (10 meses)
    Tool Manager + protocolo plugins   :v31, 2028-02-01, 60d
    Plugins: arquivos + terminal + HTTP :v32, 2028-04-01, 60d
    Plugins: GitHub + Docker + SSH     :v33, 2028-05-31, 75d
    Plugins: Cloudflare + Coolify      :v34, 2028-08-14, 45d
    Autorizacao granular + confirmacao :v35, 2028-09-28, 45d
    Sandbox + auditoria + hardening    :v36, 2028-11-12, 18d
    Marco v3.0                         :milestone, v3m, 2028-11-30, 0d

    section v4.0 - Sentidos (12 meses)
    Voz STT/TTS (PT-BR)                :v41, 2028-12-01, 75d
    Visao (imagens + screenshots)      :v42, 2029-02-14, 75d
    Observacao de ambiente (IDE/terminal/docs) :v43, 2029-04-30, 90d
    Entrada multimodal integrada       :v44, 2029-07-29, 60d
    Memoria multimodal (album/audio)   :v45, 2029-09-27, 45d
    Dashboard + permissoes de sensores :v46, 2029-11-12, 18d
    Marco v4.0                         :milestone, v4m, 2029-11-30, 0d

    section v5.0 - Maturidade (18 meses)
    Autonomia com validacao humana     :v51, 2029-12-01, 120d
    Automacoes complexas multi-passo   :v52, 2030-03-31, 90d
    Kubernetes + auto-scaling          :v53, 2030-06-29, 120d
    Multi-usuario / multi-instancia    :v54, 2030-10-27, 105d
    Custo otimizado (router economico) :v55, 2031-02-09, 75d
    Evolucao continua + SLOs formais   :v56, 2031-04-25, 36d
    Marco v5.0                         :milestone, v5m, 2031-05-31, 0d

    section v6.0+ - Evolucao Continua (2031-2036)
    Auto-melhoria supervisionada       :v61, 2031-06-01, 240d
    Metacognicao + auto-avaliacao      :v62, 2032-01-27, 240d
    Inteligencia ambiental 24/7        :v63, 2032-09-23, 240d
    Sustentacao e novos sentidos       :v64, 2033-05-21, 1137d
    Marco: NEGAO 10 anos               :milestone, v6m, 2036-07-31, 0d
```

---

## 6. KPIs de Sucesso por Versão

| Versão | KPI | Meta |
|---|---|---|
| **v0.x** | Uptime de produção / Deploy automatizado / Cobertura de testes de infra / Restauração de backup | ≥ 99% / < 15 min, sem passos manuais / ≥ 90% / < 30 min, 0 perda |
| **v1.0** | Latência de conversa (p95) / Recall de memória (p95) / Precisão de retomada de sessão / Custo por conversa / Sucesso de planos | < 2,5s / < 300ms, precisão@10 ≥ 0,85 / ≥ 95% / < US$ 0,05 / ≥ 80% |
| **v2.0** | Fatos aprendidos/dia / Precisão de extração / Resposta do Vault com citação / Tarefas agendadas perdidas / Dedup de fatos | ≥ 5 / ≥ 80% / ≥ 90%, p95 < 1s / 0 (recuperação < 1 min) / < 5% duplicados |
| **v3.0** | Sucesso de execução de tools / Ações destrutivas não confirmadas / Latência de execução / Auditoria consultável / Tempo de plugin novo | ≥ 95% / **0** / leitura ≤ 3s p95, com confirmação ≤ 30s / 100% / < 1 dia |
| **v4.0** | WER STT PT-BR / Latência voz (p95) / Precisão Q&A de imagem / Capturas não autorizadas / Retenção de sessão de voz | ≤ 10% / < 4s / ≥ 85% / **0** / ≥ 95% |
| **v5.0** | Tarefas complexas sem intervenção / Isolamento multi-tenant / Custo vs v4 / Uptime SLA / MTTR | ≥ 80% / 0 vazamentos / −40% / ≥ 99,5% / < 30 min |
| **v6.0+** | Incidentes críticos não detectados / Custo por interação (anual) / Automações propostas e aceitas / Satisfação do usuário | 0 / caindo todo ano / ≥ 60% aceitas / ≥ 90% |

---

## 7. Resumo Executivo

- **10 anos, 7 fases**, cada uma com objetivo único e non-goals explícitos — o escopo de cada versão cabe numa frase.
- **A fundação (v0) não tem IA** — infra e observabilidade primeiro, porque tudo depois depende disso.
- **Memória vem antes de mãos e sentidos** (v1 → v2 → v3 → v4): o NEGÃO só executa (v3) e percebe (v4) o que pode lembrar (v1/v2) e planejar.
- **Autonomia (v5) só depois de ferramentas, sentidos e aprendizado maduros**, sempre com validação por política — a segurança é pré-condição não negociável.
- **Cada aceitação é numérica e testável**; cada versão tem KPI e benchmark de saída — "pronto" nunca é opinião.

Próximos passos sugeridos: validar este roadmap com stakeholders, então gerar o documento de ADRs (registros de decisão) por camada e o backlog técnico da v0.x em issues.
