# SOPHIE — Auditoria extrema de capacidades

**Data:** 22/08/2026  
**Escopo:** estado as-built do worktree atual em `C:\Users\User\Meu Drive\PROJETOS-GANDRA-TECNOLOGIA\sophie`  
**Regra aplicada:** nenhuma nova feature, módulo, integração ou refactor de produto foi implementado durante a auditoria.

## 1. Executive summary

A Sophie atual é um **monólito modular web de conversa**, composto por FastAPI/Python no backend e Next.js/React no frontend. O núcleo real é: autenticação por uma única API key, sessões em Redis, uma janela de contexto textual, um adaptador LLM compatível com OpenAI/NVIDIA, fallback de modelo no mesmo provider e uma camada de voz batch com WebSocket de turno completo.

O fluxo textual fecha localmente: uma sessão pode ser criada, uma mensagem pode ser enviada e uma resposta pode ser retornada pelo modo `local-mock` quando não há credencial NVIDIA. Os testes unitários, lint, typecheck e build passam. Isso prova qualidade estrutural do checkout, não disponibilidade de banco, Redis, provider de IA ou readiness de produção.

Existe código real de STT batch, TTS batch e WebSocket de voz V1. Porém, no ambiente auditado o STT aparece indisponível por ausência de credencial NVIDIA; não há prova de áudio real com provider, microfone, câmera ou Bluetooth. A experiência é push-to-talk: o usuário clica, grava, encerra o turno, aguarda STT → LLM → TTS e recebe uma resposta completa. Não há VAD, wake word, streaming de áudio, full-duplex ou barge-in.

Não existe evidência runtime de tools executáveis, agentes, planner, reasoning engine, memória de longo prazo, memória semântica/episódica, visão, controle de desktop, Spotify, calendário, e-mail, notificações entregues, automações ou proatividade. Há routers vazios, dependências, opções de configuração e textos de UI que representam intenção arquitetural; eles não foram classificados como capacidade.

Os riscos mais graves são de segurança e veracidade operacional:

1. há credencial de banco em texto claro em dois arquivos rastreados e a história Git contém achados de segredo;
2. a autenticação runtime usa uma única API key e atribui todo acesso ao principal literal `api_key`, sem identidade real, ownership de sessão, RBAC/ABAC ou capability policy;
3. endpoints de conversa não validam que o `session_id` pertence ao chamador;
4. o dashboard apresenta integrações e métricas estáticas como se fossem estado operacional;
5. Redis/DB ausentes deixam operações retornando sucesso enquanto a persistência desaparece, e `/events/health` pode declarar saúde sem verificar Redis.

O índice FRIDAY calculado é **18/100 — CHATBOT**, com camada experimental de voz batch. A nota baixa não ignora o trabalho existente; ela reflete as dependências necessárias para uma assistente pessoal: identidade segura, memória durável, percepção contínua, ações autorizadas, dispositivos e proatividade ainda não fecham.

Se apenas uma coisa puder ser feita agora, deve ser a fundação de **identidade, autorização e ownership de dados**, acompanhada da remoção/rotação dos segredos expostos. Adicionar ferramentas ou controle de dispositivos antes disso ampliaria o risco de vazamento e ação cruzada entre usuários.

## 2. Escopo, método e limitações

### 2.1 Estado auditado

O worktree estava sujo antes dos testes, com dezenas de arquivos modificados e novos arquivos de produto/teste/documentação. A auditoria considerou o **estado presente no worktree**, não apenas `HEAD`. Não foram usados `reset`, `checkout`, `clean`, stage, commit ou push.

O repositório estava em `main`, `ahead 25, behind 27` em relação ao remoto. `git diff --check` terminou sem erro de whitespace; os avisos observados são apenas conversão LF/CRLF do Git.

### 2.2 Evidências executadas

| Evidência | Resultado |
|---|---|
| `python -m pytest -q` em `backend` | **93 passed, 1 skipped** |
| `ruff check app tests` | **All checks passed** |
| `mypy app` | **Success: no issues found in 118 source files** |
| `npm run lint` | Passou; ESLint 9 emitiu aviso sobre `.eslintignore` legado |
| `npm run build` | Passou; Next 15.5.22 gerou as rotas previstas |
| Backend local sem DB/Redis | `/healthz` 200; `/readyz` 200 com `degraded`; persistência perdida |
| Backend local sem NVIDIA key | Brain respondeu `local-mock`; `/voice/status` reportou `stt_available: false` |
| WebSocket de conversa com API key | Abriu, criou sessão e entregou mensagens `tokens`/`done` |
| WebSocket de voz sem ticket | Rejeitado no handshake com HTTP 403 |
| Browser real em `/`, `/voz`, `/conversa`, `/config` | UI renderizada; React hydration error #418; `/brain/config` respondeu 500 em degradação |
| Gitleaks no histórico | 28 achados redacted em 52 commits |
| Semgrep `p/python` | 1 achado em expressão de rate-limit, não confirmado como vulnerabilidade |

### 2.3 Ambiente bloqueado

Não havia Docker/Docker Compose disponível, nem PostgreSQL ou Redis locais ativos, nem credencial NVIDIA, microfone, câmera, Bluetooth físico, dispositivo mobile ou desktop bridge. Portanto, testes de provider, persistência real, carga distribuída, hardware e rede de produção são classificados como **NOT TESTED — ENVIRONMENT BLOCKED**, nunca como passados.

## 3. Sophie as-built architecture

### 3.1 Estrutura real

```text
SOPHIE
├── backend
│   ├── app
│   │   ├── core
│   │   ├── domain
│   │   ├── infrastructure
│   │   └── modules
│   │       ├── api              (HTTP infra, rate limit, WebSocket helpers)
│   │       ├── brain            (prompt, adapter LLM, retry, cache, fallback)
│   │       ├── conversation     (sessões, mensagens, contexto textual)
│   │       ├── voice            (STT batch, TTS batch, Voice WS V1)
│   │       ├── memory           (Redis short-term memory)
│   │       ├── security         (API key, WS ticket)
│   │       ├── database         (SQLAlchemy/Alembic, status, config)
│   │       ├── events           (Redis Streams/event envelope)
│   │       ├── monitoring       (logs, Prometheus, OTel adapters)
│   │       ├── automation       (router vazio)
│   │       ├── planner          (router vazio)
│   │       ├── reasoning        (router vazio)
│   │       ├── scheduler        (router vazio)
│   │       ├── tool_manager     (router vazio)
│   │       ├── vision           (router vazio)
│   │       ├── knowledge        (estrutura sem pipeline ativo)
│   │       └── learning         (estrutura sem fluxo ativo)
│   ├── migrations
│   └── tests
├── frontend
│   ├── app                   (/, /conversa, /voz, /monitor, /config)
│   ├── components            (chat, voice, dashboard, avatar, UI)
│   ├── app/api               (dashboard, proxy BFF, WS ticket info)
│   └── public                (manifest, service worker, offline page)
├── infra
│   ├── docker/compose        (dev, prod, observability)
│   ├── nginx                 (proxy HTTP e WS)
│   ├── scripts               (deploy, VPS, backup, restore)
│   └── k8s/README.md         (somente documentação; sem manifests)
├── docs
├── .github/workflows/ci.yml
└── scripts/testes auxiliares e artefatos RPM
```

**Não encontrados no projeto:** diretório mobile nativo, Electron/Tauri/desktop bridge, worker separado, serviço realtime separado, agente executável, vector table/retrieval pipeline, object storage, manifests Kubernetes, infraestrutura Terraform/Pulumi, integração Spotify/Gmail/Calendar/GitHub/Drive/Slack/Discord/WhatsApp/Telegram/Home Assistant.

### 3.2 Diagrama lógico real

```text
NAVEGADOR Next.js / PWA
  ├── REST via BFF /api/proxy/[...path]
  ├── WebSocket textual /ws/conversation
  └── WebSocket de voz /ws/voice
          │
          ▼
FastAPI monólito modular
  ├── API key ou WS ticket
  ├── rate limit em Redis ou fallback local
  ├── ConversationService
  │     ├── Redis conv:{session}:messages
  │     ├── janela de até 20 mensagens
  │     └── SYSTEM_PROMPT fixo
  ├── VoiceService
  │     └── upload WebM/Opus → STT batch → ConversationService → TTS batch
  ├── BrainService / ModelRouter
  │     ├── NVIDIA OpenAI-compatible API, quando configurada
  │     ├── fallback de modelo no mesmo endpoint/provider
  │     └── local-mock sem provider
  ├── Redis
  │     ├── sessões/conversas
  │     ├── short-term memory
  │     ├── WS tickets
  │     ├── cache do brain
  │     └── Redis Streams de eventos
  └── PostgreSQL/pgvector planejado
        └── migration identity/events/config; sem dados de conversa/memória
```

### 3.3 Tipo de sistema

**Classificação:** Tipo A — um LLM com uma camada de conversa e superfícies de voz.  
**Não comprovado:** Tipo B, C ou D. Os módulos planner/reasoning/automation/tool-manager não têm fluxo runtime; `ModelRouter` apenas escolhe modo local/NVIDIA e modelo fallback.

## 4. Technology inventory

| Área | Encontrado | Evidência as-built | Estado |
|---|---|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn | `backend/pyproject.toml`, `backend/app/main.py` | FUNCTIONAL |
| API | HTTP JSON, FastAPI OpenAPI | 25 paths HTTP expostos em `/api/v1/openapi.json` | FUNCTIONAL |
| Texto realtime | WebSocket `/ws/conversation` | `backend/app/modules/conversation/router.py:166-258` | PARTIAL |
| Voz realtime | WebSocket `/ws/voice` | `backend/app/modules/voice/router.py` | PARTIAL |
| Frontend | Next.js 15, React 19, Tailwind | `frontend/package.json` | FUNCTIONAL |
| PWA | manifest, service worker, offline page | `frontend/public`, `next-pwa` | PARTIAL |
| Banco | PostgreSQL + SQLAlchemy async + Alembic | `backend/app/infrastructure`, `backend/migrations` | ARCHITECTURAL-ONLY no ambiente |
| pgvector | dependência/extensão na migration | migration 0001 | ARCHITECTURAL-ONLY |
| Redis | cliente async, cache, sessão, streams | `backend/app/infrastructure/redis.py` | FUNCTIONAL somente com serviço |
| Fila | Redis Streams | `backend/app/modules/events/infrastructure` | ARCHITECTURAL-ONLY no app |
| LLM | NVIDIA OpenAI-compatible, `deepseek-ai/deepseek-v4-flash` default | `backend/app/modules/brain` | PARTIAL |
| Fallback | `meta/llama-3.1-8b-instruct` no mesmo provider | `ModelRouter` | FUNCTIONAL limitado |
| STT | NVIDIA `/audio/transcriptions`, Parakeet default | `backend/app/modules/voice/infrastructure` | PARTIAL |
| TTS | `edge-tts`, vozes pt-BR | `backend/app/modules/voice/infrastructure` | FUNCTIONAL limitado |
| Observabilidade | structlog, Prometheus, OTel, Sentry não encontrado | `backend/app/modules/monitoring` | PARTIAL |
| Proxy | Nginx HTTP/WS | `infra/nginx/conf.d/negao.conf` | PARTIAL |
| Deploy | Docker Compose + scripts VPS | `infra/docker/compose`, `infra/scripts` | PARTIAL/BROKEN em scripts |
| CI | GitHub Actions lint/typecheck/test/build | `.github/workflows/ci.yml` | FUNCTIONAL incompleto |
| Mobile | nenhum app nativo | ausência de diretório/manifest mobile | NOT IMPLEMENTED |
| Desktop | nenhum bridge nativo | ausência de Electron/Tauri/native | NOT IMPLEMENTED |
| Vision | router vazio | `backend/app/modules/vision/router.py` | ARCHITECTURAL-ONLY |

## 5. Sophie Core

| Componente exigido | Evidência real | Status | Confiança |
|---|---|---|---|
| Session Manager | Redis cria sessão e mantém índice/metadata | PARTIAL | HIGH |
| Conversation Manager | `ConversationService` persiste user/assistant e recupera janela | FUNCTIONAL | HIGH |
| Context Manager | system prompt + últimas 20 mensagens | PARTIAL | HIGH |
| Intent Resolver | nenhum resolver explícito; texto é enviado ao LLM | NOT IMPLEMENTED | HIGH |
| Reasoning Engine | módulo/router vazio, sem chamada | ARCHITECTURAL-ONLY | HIGH |
| Prompt Manager | prompt constante em `brain/identity.py`; config pode ser salva | PARTIAL | HIGH |
| Model Router | local mock vs NVIDIA e modelo fallback | PARTIAL | HIGH |
| Tool Router | nenhuma tool executável | NOT IMPLEMENTED | HIGH |
| Agent Router | nenhum agente ativo | NOT IMPLEMENTED | HIGH |
| Memory Manager | serviço Redis STM isolado, não memória pessoal | PARTIAL | HIGH |
| Identity Manager | identidade estática “Sophie” e “Wanderson” no prompt | PARTIAL | HIGH |
| Policy Engine | validação básica de ambiente/API key; não há policy de ação | PARTIAL | HIGH |
| Permission Engine | nível flat `READ_ONLY`, sem scopes/capabilities efetivos | DANGEROUS | HIGH |
| Event Manager | envelope/Redis Streams existem; consumers não estão ativos no app | ARCHITECTURAL-ONLY | HIGH |
| Action Engine | não encontrado | NOT IMPLEMENTED | HIGH |

A configuração exposta em `/brain/config` e na tela de configuração inclui tools, prompt, modelo e tokens, mas o caminho efetivo de conversa usa `SYSTEM_PROMPT` e settings; não há prova de que as opções salvas governem uma execução de tool ou mudem o prompt efetivo. A tela é, portanto, uma superfície de configuração parcial, não um control plane real.

## 6. LLM, modelos e agentes

### 6.1 Model layer

| Item | Resultado |
|---|---|
| Provider primário | NVIDIA NIM/OpenAI-compatible, condicionado a `NVIDIA_API_KEY` |
| Modelo principal default | `deepseek-ai/deepseek-v4-flash` |
| Modelo fallback | `meta/llama-3.1-8b-instruct` |
| Provider fallback independente | Não existe; ambos usam a mesma base NVIDIA |
| Embeddings | Não há chamada ativa, dimensão ou pipeline de indexação |
| Reranking | Não encontrado |
| Vision model | Não encontrado |
| STT | `nvidia/parakeet-tdt-0.6b-v2`, batch |
| TTS | Microsoft Edge TTS via `edge-tts`, batch no contrato HTTP/WS |
| Streaming LLM | Não existe `stream=true` nem async iterator do provider |
| Retries | Existem para falhas retryable, incluindo HTTP 529 |
| Circuit breaker | Existe no Brain, mas sem provider secundário independente |
| Timeout | Há constantes de timeout por camada |
| Rate limit | Redis/fallback local, sem rate limit por identidade real |
| Custo/tokens | Não há telemetria confiável; valores do dashboard são estáticos |

O `ModelRouter` não escolhe modelo por complexidade, custo, latência, modalidade, contexto ou disponibilidade multidimensional. Ele é um selector de provider local/NVIDIA com fallback de modelo.

### 6.2 Agentes

| Agent | Responsabilidade | Modelo | Tools | Entrada | Saída | Status |
|---|---|---|---|---|---|---|
| Sophie/Brain | responder conversa | NVIDIA ou local-mock | nenhuma | mensagens | texto | FUNCTIONAL |
| Research | não encontrado | — | — | — | — | NOT IMPLEMENTED |
| Coding | não encontrado | — | — | — | — | NOT IMPLEMENTED |
| Device | não encontrado | — | — | — | — | NOT IMPLEMENTED |
| Vision | router vazio | — | — | — | — | ARCHITECTURAL-ONLY |
| Communications | não encontrado | — | — | — | — | NOT IMPLEMENTED |
| Planning | router vazio | — | — | — | — | ARCHITECTURAL-ONLY |
| Memory | STM Redis isolada | — | — | — | JSON com TTL | PARTIAL |
| Automation | router vazio | — | — | — | — | ARCHITECTURAL-ONLY |

**Conclusão:** não há sistema multiagente nem contexto compartilhado entre agentes.

## 7. Tools, ações e permissões

### 7.1 Tools encontradas

Não há schemas runtime ou adapters para web, filesystem, terminal, browser automation, Spotify, e-mail, calendário, GitHub, Drive, câmera, desktop ou notificações.

A lista da UI em `frontend/app/config/page.tsx:22-30` oferece “Busca Web”, “Execução de Código”, “Operações de Arquivo”, “Memória de Longo Prazo”, “Calendário”, “E-mail” e “Clima”. Isso é **ARCHITECTURAL-ONLY**: não há backend correspondente. O dashboard também marca GitHub, Docker, VS Code, SSH, Cloudflare, Coolify e Google Drive como `ok: true` em `frontend/components/panels.tsx:249-259`, sem adapter ou health check.

### 7.2 Autorização

`InMemorySecurityService` compara uma única chave e retorna o principal literal `api_key` (`backend/app/modules/security/infrastructure/__init__.py:21-43`). O nível default é `READ_ONLY`; não há user identity efetiva, scopes, capability registry, RBAC, ABAC ou confirmação de ação.

Os endpoints de conversa recebem API key, mas `GET`, `PATCH`, `DELETE` e POST de mensagens aceitam o `session_id` diretamente e não verificam ownership (`backend/app/modules/conversation/router.py:107-163`). Em uma instalação multiusuário, uma chave válida pode acessar uma sessão conhecida de outro usuário. Isso é **DANGEROUS**.

O endpoint de rename retorna `get_settings().redis_url` no campo `updated_at` (`backend/app/modules/conversation/router.py:122-131`), expondo configuração interna ao chamador autenticado.

### 7.3 WS tickets

Há ticket de uso único com TTL de 60 segundos e `GETDEL` (`backend/app/modules/security/infrastructure/__init__.py:51-124`). A unidade de ticket é boa como delegação curta, mas o principal ainda é compartilhado e o ticket não está ligado a um usuário/dispositivo real.

O WebSocket de conversa faz `accept()` antes de autenticar (`backend/app/modules/conversation/router.py:166-184`) e aceita fallback `?api_key`. O teste adversarial sem credencial observou handshake aceito seguido de fechamento por policy. O WebSocket de voz autentica antes do aceite e, sem ticket, foi rejeitado com HTTP 403.

## 8. Memória

| Tipo | Evidência | Status | Resultado |
|---|---|---|---|
| Working memory | janela da conversa atual | PARTIAL | prompt + até 20 mensagens |
| Short-term | `stm:{session_id}:{key}` em Redis com TTL default 24h | PARTIAL | módulo real, dependente de Redis |
| Long-term | nenhuma tabela/API integrada | NOT IMPLEMENTED | sem prova |
| Semantic | pgvector apenas como extensão; sem embedding/retrieval | ARCHITECTURAL-ONLY | sem prova |
| Episodic | nenhum evento consolidado consultável | NOT IMPLEMENTED | sem prova |
| Procedural | nenhum workflow salvo/executável | NOT IMPLEMENTED | sem prova |
| Relationship | nenhum grafo/entidade | NOT IMPLEMENTED | sem prova |
| Vector memory | nenhuma tabela/chunk/index/retrieval ativo | NOT IMPLEMENTED | sem prova |

### Testes de memória

**MEMORY-01:** foi criada sessão e enviada mensagem sem Redis/DB. O POST retornou 200 e uma resposta local-mock, porém o GET subsequente retornou `messages: []` e a lista de sessões voltou vazia. Isso comprova que o caminho degradado pode aparentar sucesso sem persistir. Não comprova persistência entre sessões.

**MEMORY-02/MEMORY-03:** não há API de memória pessoal ou storage persistente disponível no ambiente; não executados como teste positivo. A alteração de preferência não tem fluxo implementado.

**Veredito:** a Sophie tem histórico de sessão/working context quando Redis está saudável; não tem memória pessoal durável.

## 9. Identidade

Existe uma persona estática em `backend/app/modules/brain/identity.py`: nome Sophie, português brasileiro, tom inspirado em JARVIS e usuário Wanderson/“chefe”. Há também prompt default duplicado na tela de configuração (`frontend/app/config/page.tsx:8`).

Isso fornece identidade de resposta, mas não um Identity Manager. Não há perfil persistente, resolução de múltiplos usuários, identidade por dispositivo, isolamento por usuário ou prova de consistência entre clientes. A configuração salva pode não alterar o prompt efetivo do `ConversationService`, que importa o prompt constante (`backend/app/modules/conversation/application/__init__.py:77-87`).

**Status:** PARTIAL. **Confidence:** HIGH.

## 10. Voice architecture

```text
Browser MediaRecorder (WebM/Opus)
  ↓ chunks do turno
WS /ws/voice + ticket de curta duração
  ↓ buffer completo em memória
NVIDIA STT batch /audio/transcriptions
  ↓ transcript
ConversationService → BrainService
  ↓ texto completo
edge-tts batch
  ↓ um frame binário de áudio
Browser playback / dispositivo de áudio selecionado
```

| Capacidade | Status | Evidência/teste |
|---|---|---|
| Captura de microfone | PARTIAL | `getUserMedia`/MediaRecorder no navegador; hardware não testado |
| STT batch | PARTIAL | adapter real; `/voice/status` marcou `stt_available:false` sem NVIDIA key |
| TTS batch | FUNCTIONAL limitado | adapter edge-tts; status por dependência, provider real não testado |
| STT streaming | NOT IMPLEMENTED | endpoint é upload batch |
| TTS streaming | NOT IMPLEMENTED no contrato | adapter faz stream interno, mas acumula bytes antes de devolver |
| VAD | NOT IMPLEMENTED | nenhum WebRTC VAD/Silero/provider realtime |
| Wake word | NOT IMPLEMENTED | nenhum Porcupine/openWakeWord/model local |
| Full-duplex | NOT IMPLEMENTED | estado é push-to-talk, um turno por vez |
| Barge-in | NOT IMPLEMENTED | não há cancelamento do TTS/playback em fala concorrente |
| Interrupção “Para” | NOT IMPLEMENTED | sem escuta enquanto áudio é reproduzido |
| Diarização/timestamps/robustez de ruído | NOT IMPLEMENTED | sem evidência de suporte |

O browser real mostrou em `/voz`: “VOICE V1”, “STT INDISPONÍVEL · TTS OK”, “Push-to-talk: fale, pare e aguarde a resposta”. Isso confirma a UX atual e contradiz qualquer leitura de conversação ambiente contínua.

### Bluetooth

O frontend enumera dispositivos de entrada/saída e usa `setSinkId` quando suportado. O pareamento Bluetooth fica sob controle do SO/navegador; não há Bluetooth API, mobile bridge ou reconnect de dispositivo no repositório. Sem headset físico, o cenário não foi executado.

**Status:** PARTIAL, apenas como capability indireta do browser/OS. **Não é integração Bluetooth da Sophie.**

## 11. Realtime transport e segurança WebSocket

O texto usa WebSocket com heartbeat, reconexão no frontend e mensagens `tokens`/`done`. A implementação backend chama o Brain e só depois divide o texto em blocos de três palavras (`conversation/router.py:239-258`). Isso é **pseudo-streaming de transporte**, não streaming LLM.

O Voice WS tem protocolo V1, limites de chunk/turno/sessão, ticket e contador de conexões por processo. O contador não é distribuído; múltiplas réplicas podem ultrapassar o limite global pretendido.

| Teste | Resultado |
|---|---|
| ticket expirado/inválido | falha segura na unidade e no fluxo inválido |
| ticket reutilizado | protegido pelo `GETDEL` no código; teste live Redis bloqueado |
| purpose incorreto | validação presente; teste unitário coberto |
| voice sem ticket | handshake HTTP 403 |
| conversation sem auth | handshake é aceito antes da validação e depois fecha 1008/policy |
| API key na query string | fallback permitido em conversation; risco de logs/referrer/telemetria |
| binding usuário/dispositivo | não existe; principal é global |

## 12. Mobile, desktop, vision e context engine

### Mobile

Existe PWA, manifest, service worker e interface responsiva. Não existe React Native, Expo, Flutter, Android ou iOS. Não há prova de execução em background, microphone persistente, câmera, Bluetooth, localização, background audio ou push entregue.

**Status:** PARTIAL como PWA web; NOT IMPLEMENTED como cliente mobile operacional.

### Desktop/control

Não existe Electron, Tauri, native bridge ou capability local para processo, janela, filesystem, clipboard, teclado, mouse, screenshot ou execução de comando. O LLM não tem shell, e isso é positivo do ponto de vista de segurança; a capacidade de agir, contudo, é inexistente.

**Status:** NOT IMPLEMENTED.

### Vision

O módulo `vision` expõe apenas router vazio. Não existe upload de imagem conectado ao LLM, webcam, snapshot, frames periódicos, OCR, object detection, screen capture ou screen vision.

**Status:** ARCHITECTURAL-ONLY/NOT IMPLEMENTED.

### Context sources

| Fonte | Existe | Atualização | Persistência | Entra no LLM |
|---|---|---|---|---|
| Texto da conversa | Sim | por turno | Redis, sujeito à saúde do serviço | Sim |
| Data/hora/timezone | não provado | — | — | Não |
| Localização | Não | — | — | Não |
| Device identity | Não | — | — | Não |
| Bateria/rede/app ativo/tela | Não | — | — | Não |
| Música atual | Não | — | — | Não |
| Calendário | Não | — | — | Não |
| Memória pessoal | Não | — | — | Não |

## 13. Cross-device, action, plan e proatividade

Não há session sync, device identity, memória compartilhada entre clientes ou revogação por dispositivo. A mesma persona textual pode aparecer em web/conversa/voz, mas não há prova de uma “Uma Sophie” operacional.

O fluxo atual é **responder**, não **agir**. Não existe `INTENT → PLAN → AUTHORIZATION → EXECUTION → VALIDATION`. Os routers planner, reasoning, automation, scheduler e tool-manager são vazios. Não há scheduler, cron de aplicação, event subscriptions ativas, webhooks, notification engine ou consumer de eventos iniciado no lifespan.

`EventBus` usa Redis Streams e possui deduplicação/retry/DLQ em código, mas `/events/status` mostrou zero streams/handlers ativos. `/events/health` retornou 200 `bus_available:true` mesmo com Redis indisponível; o sinal de saúde verifica estado local do bus, não conectividade real.

**Proatividade:** NOT IMPLEMENTED. A Sophie é REACTIVE.

**Notificações:** há cliente PWA (`frontend/lib/push.ts`), mas ele chama `/api/proxy/push/subscribe` e `/unsubscribe`; não há endpoint backend correspondente/allowlist funcional. Classificação PROTOTYPE/BROKEN.

## 14. Integrações

| Integração | Auth | Read | Write | Realtime | Status |
|---|---|---:|---:|---:|---|
| NVIDIA NIM LLM | env key | Sim, se configurado | — | Não | PARTIAL |
| NVIDIA STT | env key | Sim, batch | — | Não | PARTIAL |
| edge-tts | serviço/dependência | — | áudio batch | interno, não entregue incrementalmente | FUNCTIONAL limitado |
| PostgreSQL | URL/env | estrutura | estrutura | Não | ARCHITECTURAL-ONLY no teste |
| Redis | URL/env | cache/sessão | cache/sessão/streams | Streams | FUNCTIONAL com serviço |
| Spotify | Não | Não | Não | Não | NOT IMPLEMENTED |
| Google Calendar | Não | Não | Não | Não | NOT IMPLEMENTED |
| Gmail/e-mail | Não | Não | Não | Não | NOT IMPLEMENTED |
| GitHub | Não | Não | Não | Não | NOT IMPLEMENTED |
| Google Drive | Não | Não | Não | Não | NOT IMPLEMENTED |
| Slack/Discord/WhatsApp/Telegram | Não | Não | Não | Não | NOT IMPLEMENTED |
| Home Assistant | Não | Não | Não | Não | NOT IMPLEMENTED |

## 15. Database, pgvector, Redis e filas

### PostgreSQL

A migration 0001 cria extensões `vector` e `pgcrypto`, schemas/tabelas de `identity.users`, `identity.api_keys`, `events.audit_events` particionada e `config.app_config`. Não cria tabelas de conversations, messages, memories, embeddings, agents, devices, permissions ou automations.

As tabelas de usuários/API keys não são o caminho de autenticação runtime, que continua sendo `InMemorySecurityService`. Isso cria uma divisão perigosa entre o schema pretendido e a autoridade real.

`/database/status` no ambiente sem banco retornou 200 com `connected:false` e uma identificação interna do host/porta do engine. Em produção, readiness deveria falhar de forma inequívoca; o contrato atual mascara indisponibilidade.

### pgvector

Há extensão/dependência e referência documental a HNSW, mas nenhuma dimensão de embedding, chunking, index, filtro metadata, retrieval ou ranking ativo. Não existe teste de qualidade de recuperação.

### Redis

Usos encontrados: sessões, mensagens, short-term memory, brain cache, WS ticket, rate limit e Redis Streams. TTLs existem em vários envelopes. Sem Redis real, o sistema entra em degradação silenciosa e pode responder sucesso sem persistência.

### Filas

O único mecanismo é Redis Streams. Não há BullMQ, Celery, RabbitMQ, Kafka ou SQS. O consumer loop existe na infraestrutura, mas não há handlers de negócio registrados nem evidência de execução no lifespan.

## 16. Observabilidade e performance

Há structlog, métricas Prometheus e scaffolding OpenTelemetry. Porém:

- o middleware de acesso não alimenta de forma comprovada `MonitoringService.record_request`;
- `setup_telemetry` é chamado sem anexar explicitamente a aplicação FastAPI;
- não há trace ponta a ponta de uma conversa;
- não há prompt version, token count confiável, cost, tool call audit ou provider usage;
- dashboard exibe valores fixos como `1.4s`, `12.4K` e `$0.021` (`frontend/components/panels.tsx:146-151`).

### Baseline observado

| Fluxo | Medição | Veredito |
|---|---|---|
| `/healthz` local | sub-segundo | não representa produção |
| `/readyz` sem DB/Redis | 200 após aproximadamente 2,1s, status JSON `degraded` | contrato de readiness inadequado |
| Brain local-mock | resposta local | útil só para smoke |
| Chat WS sem Redis | resposta sujeita a timeouts de publicação/eventos | degradado e lento |
| LLM NVIDIA | não medido | provider/credencial ausentes |
| STT/TTS real | não medido | provider/hardware/rede ausentes |
| TTFT/first audio | não medido | pipeline não é streaming |
| carga 5/10/50 | não executado | Docker/serviços ausentes |

Os limiares humanos (<700 ms, 700–1500 ms etc.) não podem ser aplicados ao fluxo real sem provider e hardware. O código atual, por desenho, aguarda STT e resposta completa antes do TTS, logo não atende o objetivo de first audio conversacional.

## 17. Resiliência e fallback

Existe fallback gracioso do Brain para uma resposta de erro, retries e circuit breaker. O fallback de modelo não é fallback de provider. Não há fallback independente de STT/TTS.

Teste com Redis indisponível mostrou:

- `/readyz` continua HTTP 200 apesar de `degraded`;
- criação e envio de mensagem podem retornar 200;
- GET de mensagens/sessões não encontra o que acabou de ser aceito;
- `/brain/config` respondeu 500;
- eventos são publicados/logados com falhas, mas não impedem todos os fluxos;
- `/events/health` permaneceu falso-positivo.

Isso é degradação inconsistente: algumas partes falham rápido, outras apresentam sucesso sem durabilidade.

## 18. Segurança, privacidade e segredos

### Achados de segredo

`test_supabase.py:24` e `test_supabase_ssl.py:22` contêm uma senha de banco em texto claro em arquivos rastreados. O valor foi deliberadamente omitido deste relatório. `gitleaks git --redact` encontrou 28 achados em 52 commits, incluindo `generic-api-key` e headers de autenticação em documentação/histórico.

**Não é suficiente apagar o valor do working tree:** a credencial precisa ser revogada/rotacionada e o histórico tratado conforme a política de incidente.

### Auth/isolation

O principal literal `api_key`, ausência de ownership de sessão e tabelas de identidade não conectadas tornam isolamento de usuário não comprovado. Isso bloqueia qualquer tool de leitura/escrita, memória pessoal, e-mail, filesystem ou ação de dispositivo.

### Conteúdo não confiável / prompt injection

Não há tools externas ativas para testar uma cadeia WEB → conteúdo malicioso → e-mail. Também não há camada de trust boundary, marcação de conteúdo não confiável, tool policy ou confirmação de ação. O risco é arquiteturalmente aberto para a próxima fase.

### Container/network

O backend Docker roda como usuário não-root e possui healthcheck, o que é positivo. Compose não demonstra filesystem read-only, cap-drop, secrets manager, isolamento de rede forte ou rotação de segredo. Nginx expõe apenas `listen 80`; não há configuração TLS/443, embora o proxy de WebSocket esteja preparado. `client_max_body_size 25m` excede o limite de turno de voz de 10 MB.

### Infra scripts

- `infra/scripts/vps-setup.sh:49-51` usa `COMPOSE_FILE` sem defini-lo e continua após falha de migration;
- `infra/scripts/vps-setup.sh:15` tenta chmod em caminho diferente do keyring criado;
- scripts VPS fazem `git reset --hard origin/main`, operação destrutiva em deploy;
- o repositório/paths ainda carregam nomes antigos `Neg-o-IA`/`negao`, aumentando risco de configuração errada.

## 19. Testes existentes e CI/CD

| Área | Existência | Resultado |
|---|---|---|
| Backend unit | 19 arquivos/estrutura pytest | 93 pass, 1 skip |
| Backend integration live | presentes | não executados como integração real sem DB/Redis/provider |
| E2E browser | não há suíte Playwright no CI | smoke manual com browser real |
| Security | testes de auth/ticket existem | sem DAST, secrets gate ou multiusuário real |
| Performance/load | não encontrado | não executado |
| Frontend lint | CI/local | passou com warning ESLintIgnore |
| Frontend build | CI/local | passou |
| Typecheck backend | mypy local | passou |
| Migration gate | deploy chama Alembic | CI não valida DB limpo/rollback |
| Secret scanning | não está no workflow | ausente |
| Docker build | não está comprovado no CI auditado | ambiente sem Docker |

O CI prova compilabilidade e testes unitários. Não prova runtime completo, RLS/ownership, storage, Redis, WebSocket multiusuário, voz, PWA push, TLS, DR ou provider.

## 20. Capability matrix

Readiness é uma estimativa de capacidade comprovada no estado atual, não uma promessa de implementação futura.

| Capability | Status | Evidência | Readiness |
|---|---|---|---:|
| Chat | FUNCTIONAL | REST/WS + local-mock | 70% |
| Streaming Chat | PARTIAL | chunks após resposta completa | 35% |
| Memory | PARTIAL | janela de sessão + Redis STM | 25% |
| Long-Term Memory | NOT IMPLEMENTED | sem storage/retrieval integrado | 0% |
| Semantic Memory | ARCHITECTURAL-ONLY | pgvector/extensão sem pipeline | 5% |
| Episodic Memory | NOT IMPLEMENTED | sem eventos consolidados consultáveis | 0% |
| Tools | ARCHITECTURAL-ONLY | opções de UI, nenhum adapter | 5% |
| Agents | NOT IMPLEMENTED | nenhum agente ativo | 0% |
| Voice STT | PARTIAL | adapter batch, sem provider disponível | 35% |
| Voice TTS | FUNCTIONAL | edge-tts batch; sem teste provider/hardware | 40% |
| Streaming Voice | NOT IMPLEMENTED | uma resposta binária completa | 0% |
| Full Duplex | NOT IMPLEMENTED | push-to-talk | 0% |
| Barge-In | NOT IMPLEMENTED | sem cancelamento concorrente | 0% |
| Wake Word | NOT IMPLEMENTED | nenhum detector | 0% |
| Bluetooth | PARTIAL | seleção de devices via browser/OS | 20% |
| Spotify | NOT IMPLEMENTED | nenhum OAuth/API | 0% |
| Camera | NOT IMPLEMENTED | sem captura | 0% |
| Vision | ARCHITECTURAL-ONLY | router vazio | 0% |
| Screen Vision | NOT IMPLEMENTED | sem captura/OCR/model | 0% |
| Desktop Control | NOT IMPLEMENTED | sem bridge | 0% |
| Mobile | PARTIAL | PWA, sem app/background | 20% |
| Notifications | PROTOTYPE | cliente push sem backend | 10% |
| Automations | ARCHITECTURAL-ONLY | router vazio | 0% |
| Proactivity | NOT IMPLEMENTED | sem scheduler/triggers | 0% |
| Calendar | ARCHITECTURAL-ONLY | opção de config apenas | 0% |
| Email | ARCHITECTURAL-ONLY | opção de config apenas | 0% |
| GitHub | NOT IMPLEMENTED | claim estático na UI | 0% |
| Cross Device | NOT IMPLEMENTED | sem sync/device identity | 0% |
| Context Engine | PARTIAL | contexto textual da sessão | 25% |
| Permissions | DANGEROUS | API key global, sem capability policy | 5% |
| Observability | PARTIAL | logs/metrics/OTel incompletos | 30% |
| Security | DANGEROUS | segredo exposto e isolamento não provado | 15% |

Nenhuma capability crítica recebeu `PRODUCTION-READY`.

## 21. Friday Readiness Index

### Five pillars

```text
INTELLIGENCE   34/100
MEMORY          8/100
PERCEPTION     16/100
ACTION          2/100
PRESENCE       17/100
```

### Índice global

**FRIDAY READINESS INDEX: 18/100 — CHATBOT.**

Pesos usados: Intelligence 30%, Memory 20%, Perception 20%, Action 15%, Presence 15%. A experiência atual é superior a uma tela estática porque há conversa real, WebSocket e uma camada de voz batch; ainda assim, sem memória durável, ações, visão, identidade multi-dispositivo e proatividade, ela não entra no nível AI Assistant/Agentic Assistant de forma comprovada.

## 22. Cenários de aceitação

| Cenário | O que funciona hoje | Veredito |
|---|---|---|
| A — “Sophie”, Bluetooth, música, Eminem | nenhum wake word; PTT exige clique; seleção de áudio fica com browser/OS; Spotify não existe | NOT IMPLEMENTED/PARTIAL |
| B — agenda amanhã e “qual é a primeira?” | conversa textual pode manter referência nas últimas 20 mensagens; calendário não existe | PARTIAL |
| C — problema de ontem no SGS | sem memória episódica ou histórico durável pessoal | NOT IMPLEMENTED |
| D — câmera “olha isso” | sem camera/vision endpoint | NOT IMPLEMENTED |
| E — olha minha tela | sem screen capture/OCR/vision | NOT IMPLEMENTED |
| F — abrir SGS e VS Code | sem desktop bridge/OS action | NOT IMPLEMENTED |
| G — aviso de reunião em 15 minutos | sem scheduler, calendar integration ou notification delivery | NOT IMPLEMENTED |

## 23. Testes implícitos, interrupção e aprendizado

| Teste | Resultado |
|---|---|
| Referência textual “ele/a empresa dele” | o LLM pode receber janela textual no mesmo turno/sessão; não há teste provider real nem garantia de resolução |
| Contexto de device/volume | sem device identity ou mídia atual |
| Ambiguidade “João” | sem contacts/entity resolver |
| Workflow “modo trabalho” | sem procedural memory, tool registry ou action engine |
| Fala durante TTS | pipeline não escuta de modo concorrente; barge-in não implementado |
| Interação sem botão | wake word/VAD não implementados |

## 24. Findings

### F-001

```text
ID: F-001
AREA: Secrets / Credential Management
SEVERITY: CRITICAL
STATUS: DANGEROUS
DESCRIPTION: Credencial de banco em texto claro está em arquivos rastreados e há achados no histórico Git.
EVIDENCE: gitleaks git --redact encontrou 28 achados em 52 commits; password literal em test_supabase.py:24 e test_supabase_ssl.py:22.
FILES: test_supabase.py:24; test_supabase_ssl.py:22; histórico Git.
RUNTIME TEST: scanner de segredo executado com redaction.
RESULT: achados confirmados; valor omitido.
IMPACT: risco de acesso a banco e comprometimento histórico.
FRIDAY IMPACT: bloqueia memória, tools, integrações e qualquer ação com dados pessoais.
RECOMMENDATION: revogar/rotacionar imediatamente, remover do código/histórico conforme processo de incidente, adicionar secret scanning no CI.
CONFIDENCE: HIGH
```

### F-002

```text
ID: F-002
AREA: Authentication / Authorization / Data Isolation
SEVERITY: CRITICAL
STATUS: DANGEROUS
DESCRIPTION: Toda autenticação efetiva usa uma única API key e o principal literal api_key; sessões não têm ownership validado.
EVIDENCE: InMemorySecurityService:21-43; conversation router:107-163.
FILES: backend/app/modules/security/infrastructure/__init__.py:21-43; backend/app/modules/conversation/router.py:107-163.
RUNTIME TEST: requests autenticados acessaram os endpoints; sem DB/Redis, a identidade permaneceu global.
RESULT: não há prova de isolamento por usuário/dispositivo.
IMPACT: acesso cruzado a conversa e futura escalada de tool.
FRIDAY IMPACT: impede com segurança memória pessoal e ações autorizadas.
RECOMMENDATION: conectar autenticação persistente a users/sessions, impor ownership em toda query, criar RBAC/capability policy e revogação por device.
CONFIDENCE: HIGH
```

### F-003

```text
ID: F-003
AREA: Reliability / Persistence
SEVERITY: HIGH
STATUS: BROKEN
DESCRIPTION: Em DB/Redis indisponíveis, endpoints podem responder sucesso sem durabilidade; readiness continua HTTP 200.
EVIDENCE: /readyz 200 com database/redis degraded; POST de mensagem 200 seguido de GET vazio; database/status connected=false.
FILES: backend/app/main.py; backend/app/modules/conversation; backend/app/modules/api/router.py.
RUNTIME TEST: backend local sem PostgreSQL/Redis.
RESULT: degradação inconsistente e perda aparente de sessão/mensagem.
IMPACT: confiança operacional, recuperação e integridade de conversa.
FRIDAY IMPACT: memória e continuidade não podem ser fundação segura.
RECOMMENDATION: tornar readiness não-2xx quando necessário, definir contratos fail-closed/fail-safe por endpoint e não confirmar writes não persistidos.
CONFIDENCE: HIGH
```

### F-004

```text
ID: F-004
AREA: Product Truth / Observability
SEVERITY: HIGH
STATUS: DANGEROUS
DESCRIPTION: Dashboard apresenta métricas e integrações estáticas como estado real.
EVIDENCE: Math.random para CPU/RAM/etc.; valores fixos de custo/tokens/latência; tools GitHub/Docker/VS Code/SSH/Cloudflare/Coolify/Drive com ok=true.
FILES: frontend/components/panels.tsx:33-36, 63-107, 146-151, 198-259; frontend/components/sections.tsx.
RUNTIME TEST: browser real mostrou cards e timeline sem adapters correspondentes.
RESULT: UI sugere capacidades não comprovadas.
IMPACT: diagnóstico e decisões de segurança/produção baseados em dados falsos.
FRIDAY IMPACT: mascara a distância real entre chatbot e agente operacional.
RECOMMENDATION: remover claims estáticos ou marcá-los como demo; alimentar somente por health/telemetry real.
CONFIDENCE: HIGH
```

### F-005

```text
ID: F-005
AREA: Voice / Realtime
SEVERITY: HIGH
STATUS: PARTIAL
DESCRIPTION: Existe voz batch/turn-based, mas não conversação natural por voz.
EVIDENCE: Voice V1 exige turno completo; STT indisponível no runtime; TTS é acumulado antes do envio; não há VAD, wake word, duplex ou barge-in.
FILES: backend/app/modules/voice/router.py; backend/app/modules/voice/infrastructure; frontend/components/voice/voice-panel.tsx.
RUNTIME TEST: `/voice/status` marcou STT false; `/voz` mostrou “Push-to-talk” e “STT INDISPONÍVEL · TTS OK”.
RESULT: caminho de código existe, provider/hardware não foram provados.
IMPACT: latência e naturalidade insuficientes.
FRIDAY IMPACT: bloqueia presença ambiente.
RECOMMENDATION: primeiro fechar provider/observabilidade batch; depois streaming STT/LLM/TTS, VAD e barge-in.
CONFIDENCE: HIGH
```

### F-006

```text
ID: F-006
AREA: WebSocket Security
SEVERITY: HIGH
STATUS: DANGEROUS
DESCRIPTION: Conversation WebSocket aceita o handshake antes de autenticar e permite API key na query string.
EVIDENCE: conversation router:166-184; authenticate_ws:127-141.
RUNTIME TEST: conexão sem credencial abriu handshake e depois recebeu fechamento por policy; voice sem ticket foi rejeitado antes do aceite.
RESULT: superfícies e semânticas de segurança são inconsistentes.
IMPACT: logs/proxies podem registrar credencial; recursos podem ser consumidos antes da auth.
FRIDAY IMPACT: ameaça qualquer bridge realtime.
RECOMMENDATION: autenticar antes do accept quando possível, preferir ticket obrigatório, origin validation, rate limit por identidade real e binding device/session.
CONFIDENCE: HIGH
```

### F-007

```text
ID: F-007
AREA: Tools / Policy
SEVERITY: HIGH
STATUS: ARCHITECTURAL-ONLY
DESCRIPTION: UI e config declaram web search, code exec, file ops, memory, calendar e e-mail, mas não existe execution path.
EVIDENCE: frontend/app/config/page.tsx:22-30; routers tool-manager/planner/reasoning vazios; OpenAPI não expõe tools.
RUNTIME TEST: inventário OpenAPI e browser `/config`.
RESULT: nenhuma chamada de tool real encontrada.
IMPACT: confusão de produto hoje; risco elevado se um executor for adicionado sem policy.
FRIDAY IMPACT: action score permanece 2/100.
RECOMMENDATION: implementar registry/policy/audit/confirmation antes de qualquer adapter.
CONFIDENCE: HIGH
```

### F-008

```text
ID: F-008
AREA: Memory / Database
SEVERITY: HIGH
STATUS: ARCHITECTURAL-ONLY
DESCRIPTION: pgvector está presente como extensão/dependência, mas não há tabela, embedding, retrieval ou filtro de isolamento.
EVIDENCE: migration 0001 e ausência de entidades/módulos ativos de knowledge.
RUNTIME TEST: MEMORY-01 sem Redis não persistiu; MEMORY-02/03 não têm API executável.
RESULT: nenhuma memória longa comprovada.
IMPACT: não há continuidade histórica ou aprendizado seguro.
FRIDAY IMPACT: impede personalização real.
RECOMMENDATION: definir contrato de memória, ownership, retenção, deleção e avaliação antes de escolher índice/modelo.
CONFIDENCE: HIGH
```

### F-009

```text
ID: F-009
AREA: Observability
SEVERITY: MEDIUM
STATUS: PARTIAL
DESCRIPTION: Instrumentação existe, mas não há prova de trace/conversa/custo ponta a ponta e o health do event bus é falso-positivo com Redis fora.
EVIDENCE: setup OTel/Prometheus sem ligação completa; events/health 200 com Redis indisponível.
FILES: backend/app/modules/monitoring; backend/app/modules/events/infrastructure/__init__.py:272+.
RUNTIME TEST: endpoints `/metrics`, `/monitoring/metrics`, `/events/health`.
RESULT: sinais básicos existem, prova operacional é incompleta.
IMPACT: incidentes e custo de IA não são auditáveis.
FRIDAY IMPACT: evolução sem regressão fica sem medição.
RECOMMENDATION: correlation id, model/prompt/token/cost/tool spans e checks reais de dependências.
CONFIDENCE: HIGH
```

### F-010

```text
ID: F-010
AREA: Deployment
SEVERITY: HIGH
STATUS: BROKEN
DESCRIPTION: script one-shot usa COMPOSE_FILE não definido, continua após falha de migration e possui divergências de path/repositório.
EVIDENCE: vps-setup.sh:15, 31, 49-51.
RUNTIME TEST: revisão estática; Docker indisponível para execução.
RESULT: deploy não foi aceito como comprovadamente seguro.
IMPACT: release parcial ou banco incompatível.
FRIDAY IMPACT: impede confiança em voice/memory/action em produção.
RECOMMENDATION: corrigir script, fail closed em migration, remover reset destrutivo automático e validar Docker em CI/staging.
CONFIDENCE: HIGH
```

### F-011

```text
ID: F-011
AREA: Transport Security
SEVERITY: HIGH
STATUS: DANGEROUS
DESCRIPTION: Configuração Nginx auditada tem apenas HTTP port 80, sem listen 443 ssl/TLS.
EVIDENCE: infra/nginx/conf.d/negao.conf:9-18; proxy WS sem evidência de WSS terminando ali.
RUNTIME TEST: ambiente local HTTP; produção não acessível.
RESULT: TLS de produção não comprovado.
IMPACT: credenciais/tickets/áudio podem transitar sem proteção se expostos diretamente.
FRIDAY IMPACT: bloqueia microfone, memória e ações remotas.
RECOMMENDATION: provar TLS externo e interno conforme threat model, HSTS e origin policy.
CONFIDENCE: HIGH para o arquivo; MEDIUM para ambiente real.
```

### F-012

```text
ID: F-012
AREA: Notifications
SEVERITY: MEDIUM
STATUS: BROKEN
DESCRIPTION: Cliente PWA tenta registrar push, mas não há backend de subscribe/unsubscribe comprovado.
EVIDENCE: frontend/lib/push.ts:46-75; paths OpenAPI não contêm push.
RUNTIME TEST: inventário OpenAPI e build; push físico não executado.
RESULT: fluxo não fecha.
IMPACT: proatividade e alertas não entregam.
FRIDAY IMPACT: bloqueia presença proativa.
RECOMMENDATION: só exibir capacidade quando backend, VAPID, storage, revogação e entrega forem provados.
CONFIDENCE: HIGH.
```

### F-013

```text
ID: F-013
AREA: Frontend Runtime
SEVERITY: MEDIUM
STATUS: BROKEN
DESCRIPTION: páginas renderizadas no browser real emitiram React minified error #418, indicando mismatch/hydration problem.
EVIDENCE: console do Playwright em `/`, `/voz`, `/conversa` e `/config`.
RUNTIME TEST: browser real com build servido por Next.
RESULT: UI aparece, mas com erro de runtime; `/config` também recebeu HTTP 500 de `/api/proxy/brain/config` quando Redis estava fora.
IMPACT: instabilidade de UX e estado divergente SSR/cliente.
FRIDAY IMPACT: reduz confiança na superfície realtime.
RECOMMENDATION: reproduzir em modo não-minificado e corrigir a origem do mismatch antes de adicionar presença contínua.
CONFIDENCE: HIGH para o erro; LOW para causa sem stack dev.
```

## 25. KEEP / IMPROVE / REFACTOR / REPLACE / REMOVE

### KEEP

- separação modular FastAPI/Next;
- contratos Pydantic e tipagem Python;
- limites explícitos de áudio, sessão, timeout e retry;
- ticket WS de uso único com TTL e purpose;
- adapter OpenAI-compatible isolado do Brain;
- testes unitários existentes e CI básico;
- backend Docker non-root/healthcheck;
- PWA e seleção de dispositivos como fundação de cliente web.

### IMPROVE

- ConversationService e janela de contexto;
- Redis STM, transformando-o em componente com contrato de retenção/deleção;
- voice batch, antes de tentar streaming;
- eventos/Prometheus/OTel;
- Nginx/proxy e health checks;
- configuração da persona/modelo, conectando-a ao caminho efetivo.

### REFACTOR

- SecurityService para identidade persistente e capabilities;
- ownership de sessões/mensagens e camada de autorização;
- ModelRouter para política explícita de custo/latência/fallback;
- EventBus para lifecycle real, handlers, DLQ observável e health real;
- dashboard para remover dados sintéticos e consumir contratos de telemetry.

### REPLACE

- autenticação global em API key por um sistema de identidade/session/device;
- pseudo-streaming por streaming real ou, enquanto não houver, nomenclatura honesta;
- status de dependências baseado em flags locais por checks reais;
- script VPS one-shot atual por pipeline fail-closed e reversível.

### REMOVE

- credenciais rastreadas e qualquer valor de teste que pareça segredo;
- claims de integração `ok: true` sem adapter;
- métricas fake de custo/tokens/latência;
- opções de tools que não tenham backend ou marcar explicitamente como “planejado”.

## 26. Dependency graph para evolução FRIDAY

```text
IDENTITY + AUTHORIZATION + DATA OWNERSHIP
├── user/session/device identity
├── capability policy
├── confirmation/audit
└── secret rotation + TLS
        ↓
CORE RELIABLE
├── DB/Redis contracts
├── truthful readiness
├── conversation persistence
├── prompt/model policy
└── end-to-end observability
        ↓
VOICE V1 REAL
├── provider STT/TTS comprovado
├── audio format/limits
└── browser/mobile E2E
        ↓
VOICE NATURAL
├── streaming STT
├── streaming LLM
├── streaming TTS
├── VAD
└── barge-in/cancelamento
        ↓
MEMORY
├── profile/preferences
├── episodic events
├── semantic embeddings/retrieval
├── retention/deletion
└── cross-device sync
        ↓
VISION
├── snapshot upload
├── screenshot/camera consent
├── OCR/vision model
└── periodic/streaming frames
        ↓
ACTION
├── tool registry
├── action request
├── policy check
├── user confirmation
├── device bridge sandboxed
└── validation/idempotency
        ↓
PROACTIVITY
├── scheduler/event subscriptions
├── rules/context
├── notification delivery
└── supervised autonomy
        ↓
AMBIENT AI
├── mobile/desktop bridges
├── multiple devices
├── wake word/background rules
└── revocation/privacy controls
```

## 27. Roadmap adaptado às evidências

### Fase 0 — Foundation fixes / P0

1. revogar e rotacionar segredos expostos;
2. implementar identidade real, ownership e autorização por capability;
3. conectar o auth ao schema persistente ou substituir o schema por um contrato coerente;
4. tornar readiness, writes e degradação honestos;
5. provar TLS, logs redacted e audit trail;
6. remover dashboard fake;
7. adicionar secret scanning, migration check e browser smoke ao CI.

### Sophie V1 — Voice batch comprovada

1. provider STT/TTS configurado em ambiente de teste;
2. testes de frase curta/longa/PT-BR/ruído com latência;
3. browser permission/device tests;
4. persistência correta do transcript e resposta;
5. contrato explícito de push-to-talk.

### Sophie V2 — Voice realtime natural

1. streaming STT/LLM/TTS;
2. VAD;
3. cancelamento de playback;
4. barge-in;
5. ticket/device binding e métricas TTFA.

### Sophie V3 — Memory

1. perfil/preferências com consentimento e deleção;
2. memória episódica baseada em eventos;
3. memória semântica com embeddings, filtros e avaliação;
4. retenção, poisoning defense e isolamento por usuário;
5. continuidade cross-device.

### Sophie V4 — Vision

1. snapshot consentido;
2. documento/OCR;
3. screenshot de janela selecionada;
4. visão periódica somente com política explícita;
5. nunca deixar câmera always-on por default.

### Sophie V5 — Action

1. tools read-only de baixo risco;
2. action request → policy → confirmation → bridge;
3. calendar/email/Spotify com OAuth e scopes mínimos;
4. idempotência, audit e rollback;
5. desktop bridge sandboxed; nenhum shell irrestrito.

### Sophie V6 — Proactive/ambient

1. scheduler/event engine;
2. push/voice notifications realmente entregues;
3. supervisão e quiet hours;
4. mobile/desktop bridges;
5. wake word/background com consentimento e indicadores claros.

## 28. Prioridade imediata

### Se fosse possível implementar apenas uma coisa

**Fundação de identidade, autorização e ownership de dados, junto com rotação dos segredos expostos.**

Motivo: sem isso, memória pessoal, e-mail, calendário, filesystem, desktop e dispositivos não podem ser adicionados com segurança. É a dependência que protege todas as fases posteriores.

### Segunda coisa

**Fechar a confiabilidade do core:** persistência real em ambiente controlado, readiness fail-closed, contratos de degradação e observabilidade ponta a ponta.

### Terceira coisa

**Fechar Voice V1 batch com provider e browser E2E reais**, medindo STT → LLM → TTS, antes de tentar full-duplex.

## 29. Blockers

```text
BLOCKER: Identidade e isolamento de dados não são reais.
SEVERITY: CRITICAL
AREA: Security / Memory / Actions
CURRENT EVIDENCE: API key única, principal api_key, sem ownership de session_id.
WHY IT BLOCKS FRIDAY: qualquer memória ou tool pessoal pode cruzar usuário.
REQUIRED FIX: identity/session/device model, authorization capabilities e ownership em queries.
MINIMUM PROOF REQUIRED: teste multiusuário negativo/positivo, revogação, auditoria e zero cross-tenant/session.
```

```text
BLOCKER: Segredos versionados.
SEVERITY: CRITICAL
AREA: Secrets / Infrastructure
CURRENT EVIDENCE: dois arquivos rastreados com senha e 28 achados Gitleaks no histórico.
WHY IT BLOCKS FRIDAY: credenciais e dados pessoais podem ser comprometidos.
REQUIRED FIX: revoke/rotate, history remediation, CI secret gate.
MINIMUM PROOF REQUIRED: scanner sem findings reais/redacted e evidência de rotação.
```

```text
BLOCKER: Persistência e readiness inconsistentes.
SEVERITY: HIGH
AREA: Reliability / Memory
CURRENT EVIDENCE: 200 degraded, POST 200 seguido de GET vazio, health de events falso-positivo.
WHY IT BLOCKS FRIDAY: continuidade e memória não são confiáveis.
REQUIRED FIX: contratos fail-closed/fail-safe, DB/Redis probes e não confirmar writes perdidos.
MINIMUM PROOF REQUIRED: chaos tests DB/Redis, recovery, replay/idempotência e alerta correto.
```

```text
BLOCKER: Voz não é realtime natural.
SEVERITY: HIGH
AREA: Voice / Presence
CURRENT EVIDENCE: batch STT/TTS, PTT, STT indisponível, sem VAD/duplex/barge-in.
WHY IT BLOCKS FRIDAY: não há conversa ambiente ou interrupção humana.
REQUIRED FIX: provider comprovado, streaming, VAD e cancelamento.
MINIMUM PROOF REQUIRED: TTFA medida, testes de interrupção, ruído, silêncio e reconnect.
```

```text
BLOCKER: Nenhum action/tool engine seguro.
SEVERITY: HIGH
AREA: Action / Policy
CURRENT EVIDENCE: routers vazios; tools existem somente como opções de UI.
WHY IT BLOCKS FRIDAY: Sophie não consegue agir e não há autorização para fazê-lo.
REQUIRED FIX: registry + policy + confirmation + sandboxed device bridge.
MINIMUM PROOF REQUIRED: matriz de permissões, prompt/tool injection tests, audit e idempotência.
```

## 30. Quick wins (não implementados nesta auditoria)

- remover ou marcar como demo todas as métricas/integrations estáticas do dashboard;
- adicionar Gitleaks ao CI e bloquear novos segredos;
- corrigir o retorno `updated_at` que expõe `redis_url`;
- alterar `/readyz` para refletir de forma consistente indisponibilidade;
- tornar `/events/health` dependente de ping real;
- remover API key de query string da documentação de produção;
- corrigir `COMPOSE_FILE` e o `|| echo ... continuing` do script VPS;
- adicionar browser smoke para `/`, `/conversa`, `/voz`, `/config`;
- substituir o rótulo “streaming” por “chunked response” até existir streaming real;
- marcar explicitamente STT/TTS como dependentes de provider no frontend.

## 31. Technical debt prioritization

### P0

- secrets/histórico;
- identidade global e ownership;
- ausência de capability policy;
- TLS não comprovado;
- deploy que pode continuar após migration falhar;
- readiness/persistência falsa.

### P1

- observabilidade real de AI;
- voice provider/runtime E2E;
- streaming/VAD/barge-in;
- memory contract e cross-device;
- remoção de claims falsos da UI.

### P2

- pgvector/retrieval com avaliação;
- event handlers/DLQ operacionais;
- PWA push completo;
- CI Docker/migration/E2E/performance;
- separar nomes/legado `NEGÃO`/`Sophie`.

### P3

- refinamento visual, dashboards históricos, cache de TTS, melhorias de onboarding e redução de hydration noise.

## 32. FinOps

**NÃO MENSURÁVEL COM EVIDÊNCIA ATUAL.**

O repositório não possui provider real configurado no ambiente auditado, contagem confiável de tokens, preço versionado, volume diário, uso de STT/TTS, embedding ou métricas de retenção. Existem valores fixos de custo na UI, mas eles não são telemetria e foram classificados como não confiáveis.

O que deve ser medido antes da estimativa por usuário/dia ou 1.000 interações: tokens input/output por modelo, cache hit, retries/fallbacks, segundos de STT/TTS, embeddings, armazenamento, egress, uptime, Redis/Postgres e observabilidade. Sem isso, qualquer cifra seria inventada.

## 33. UX da assistente

Hoje a Sophie se apresenta mais como **chatbot com painel de comando** do que como assistente:

- precisa abrir a aplicação;
- conversa textual exige conexão/sessão;
- voz exige clique e turno completo;
- não inicia interações;
- não conhece calendário, app/device, tela, música ou localização;
- parte do dashboard simula presença operacional sem backend;
- browser real mostrou hydration error e config 500 em degradação.

O caminho para “presença disponível através dos dispositivos autorizados” ainda não foi implementado. A PWA é uma fundação de distribuição, não uma presença ambiente.

## 34. Resposta final: o que preservar, substituir e em que sequência

Eu preservaria a modularização FastAPI/Next, os contratos tipados, o `ConversationService` como facade, o adapter OpenAI-compatible, a infraestrutura de limites/tickets e o PWA como superfície inicial. Também preservaria o Voice V1 batch como prova de transporte, depois de torná-lo honesto e testável.

Eu substituiria a API key global por identidade/session/device, a autorização flat por capability policy, a falsa telemetria por estado real, o pseudo-streaming por streaming verdadeiro quando houver provider, e os scripts de deploy fail-open por pipeline verificável. Não reescreveria o core textual inteiro antes de corrigir esses limites.

A sequência tecnicamente correta é:

```text
SOPHIE CURRENT STATE: monólito web de chat + voice batch parcial
        ↓
FOUNDATION FIXES: secrets, identity, ownership, policy, TLS, readiness, telemetry
        ↓
VOICE: batch comprovado → streaming → VAD → barge-in
        ↓
MEMORY: profile + episodic + semantic + retention + cross-device
        ↓
VISION: snapshot → screen/document → periodic com consentimento
        ↓
ACTION: tools read-only → policy/confirmation → device bridges sandboxed
        ↓
PROACTIVITY: events, scheduler, notifications, supervised autonomy
        ↓
AMBIENT AI: mobile/desktop/múltiplos dispositivos, wake/background sob consentimento
```

## 35. Final verdict

```text
CLASSIFICATION: CHATBOT
FRIDAY READINESS: 18/100
AUTONOMY LEVEL: LEVEL 0 — Chat
```

A Sophie tem uma base funcional de conversa e componentes reais de voz batch, mas não há evidência de tools, agentes, memória pessoal, percepção visual, controle de dispositivos ou proatividade. A arquitetura permite evolução, desde que a fundação de segurança/identidade e a confiabilidade sejam corrigidas antes de conceder qualquer poder de ação ao modelo.

**Confidence geral:** HIGH para o inventário estrutural e código estático; MEDIUM para comportamento dependente de Redis/DB/provider; LOW para qualquer afirmação sobre produção, hardware, Bluetooth físico, mobile nativo ou custos, pois esses ambientes não estavam disponíveis.
