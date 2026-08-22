# SOPHIE FOUNDATION REPORT

Data: 2026-08-22  
Repositório auditado: `C:\Users\User\Meu Drive\PROJETOS-GANDRA-TECNOLOGIA\sophie`  
Escopo: Fase 0 — hardening P0/P1.  
Regra de escopo: não foram implementados wake word, full-duplex, streaming de
áudio, visão, memória longa, agentes, tools externas, Spotify, calendário,
e-mail, desktop control, automações ou proatividade.

## 1. Executive Summary

A SOPHIE continua sendo um monólito web de chat com voz batch/parcial. Nesta
intervenção foi criada a fundação de identidade e sessão server-side:
usuários possuem senha derivada com scrypt, sessões opacas persistidas somente
por hash, dispositivos lógicos, expiração e revogação. O frontend agora usa
um BFF com cookie HttpOnly e a API deixa de tratar uma API key global como
identidade de usuário.

Ownership foi aplicado às conversas Redis: cada sessão carrega `user_id`, há
índice por usuário e endpoints de leitura, alteração, reset, exclusão e chat
verificam o proprietário. Escritas de conversa passaram a falhar
explicitamente quando Redis falha; operações multi-chave usam pipeline
transacional.

Readiness agora retorna `503` quando PostgreSQL, Redis ou tabelas críticas de
identidade não estão disponíveis. Liveness permanece independente. Requests
recebem request/trace/correlation IDs, errors têm envelope seguro e logs
estruturados possuem redaction de credenciais.

O resultado não é PASS. O histórico Git ainda contém 28 achados Gitleaks e há
credenciais plausíveis no `.env` ignorado local, cuja rotação não foi executada.
O frontend também tem 4 vulnerabilidades altas no `npm audit`; PostgreSQL,
Redis e Docker não estavam disponíveis para testes reais de migration,
login, revogação, restart, readiness e E2E multiusuário. Portanto:

```text
FOUNDATION GATE: FAIL
```

## 2. Original Audit Findings

| Finding | Severidade original | Root cause | Fechamento nesta fase |
| --- | --- | --- | --- |
| Segredos em arquivos/histórico | P0 | credenciais em docs/scripts e histórico | **PARTIAL** — working tree sanitizado; histórico/rotação pendentes |
| API key global como identidade | P0 | `InMemorySecurityService` retornava principal compartilhado | **PARTIAL** — sessão real implementada; fallback de serviço só dev |
| Sem ownership de sessão/conversa | P0 | Redis global sem vínculo confiável a usuário | **FUNCTIONAL** — ownership Redis e testes adversariais adicionados |
| Persistência falsa/degradada | P0 | exceções Redis eram engolidas/fallback RAM | **FUNCTIONAL** — fail-closed e pipeline transacional |
| Readiness mentia com HTTP 200 | P1 | `/readyz` retornava estado degradado como sucesso | **FUNCTIONAL** — 200/503 por dependências críticas |
| Observabilidade insuficiente | P1 | sem correlação ponta a ponta/redaction central | **FUNCTIONAL** — IDs, headers, logs e redaction |
| WS aceito antes da autenticação | HIGH | `accept()` precedia validação em WS genérico | **FUNCTIONAL** — autenticação antes do handshake |
| Migrations não entravam na imagem | HIGH | Dockerfile copiava somente `app/` | **FUNCTIONAL** — `COPY migrations` e comando explícito |
| Deploy continuava após migration falhar | HIGH | `|| echo warning` em setup VPS | **FUNCTIONAL** — aborta em falha |
| Dependências vulneráveis | HIGH | versões transitivas sem remediation | **BLOCKED/OPEN** — audit executado; upgrade major não aplicado |

## 3. Baseline

Baseline executado antes das mudanças:

```text
tests: 93 passed, 1 skipped
ruff check: PASS
ruff format --check: FAIL — 36 arquivos não formatados
mypy app: PASS — 118 arquivos
frontend lint: PASS — warning ESLint 9 sobre .eslintignore
frontend typecheck: NÃO EXISTIA script
frontend build: compilação observada; gate formal ainda não estava no CI
migration: não executada contra DB real
secret scan: FAIL — Gitleaks git encontrou 28 achados em 52 commits
pip-audit: indisponível no ambiente
npm audit: FAIL — 4 vulnerabilidades HIGH
Docker/PostgreSQL/Redis: indisponíveis localmente
```

## 4. Changes Implemented

- `UserORM.password_hash`, `DeviceORM` e `AuthSessionORM`.
- Migration `0002_identity_sessions` com FKs, índices, unique token hash e
  unique device por usuário/nome/tipo.
- Registro/login/logout/status/WS-ticket em `security/router.py`.
- scrypt com salt aleatório para senhas e token opaco CSPRNG para sessões.
- Cookie `sophie_session` HttpOnly, SameSite Lax e Secure em produção.
- BFF Next.js para login, logout, me, registro e proxy autenticado.
- AuthGuard e tela de login.
- API key global retirada do fluxo de usuário; `X-API-Key` ficou explícita como
  service auth e somente fallback de desenvolvimento para compatibilidade.
- Ownership e índices Redis por usuário.
- `ConversationPersistenceError` e respostas `503` quando o storage falha.
- Liveness/readiness separados.
- Correlation IDs e error envelopes.
- Redaction de campos sensíveis em logs estruturados.
- Gitleaks, OSV/npm audit, pip-audit, migrations e typecheck adicionados aos
  gates de CI; o gate falha quando a ferramenta encontra vulnerabilidades.
- Dockerfile e scripts de deploy corrigidos para carregar e executar migrations.

## 5. Secrets Remediation

### Evidência

- `gitleaks git --redact --no-banner --exit-code 1 .`: **FAIL**, 28 achados,
  52 commits.
- A auditoria anterior identificou ocorrências históricas em `b812556` e
  `d3f5900`, incluindo credenciais Redis/Supabase/NVIDIA plausíveis.
- `git grep` no working tree atual não encontrou os padrões de credenciais
  plausíveis após a sanitização dos arquivos versionados.
- `gitleaks dir` no workspace local encontrou 24 achados exclusivamente em
  `.env`, `backend/.venv`, `frontend/.next` e `frontend/.vercel`; são artefatos
  ignorados/localmente gerados, não devem ser usados como fonte de secrets em
  CI.

### Ações aplicadas

- Removidos valores de Redis, NVIDIA, Supabase e API key dos docs/scripts
  versionados.
- `test_redis.py` e `test_redis_simple.py` agora exigem
  `SOPHIE_REDIS_URL`/`NEGAO_REDIS_URL` fora do código.
- `.env.example` contém somente placeholders.
- Compose de produção exige `POSTGRES_PASSWORD` e
  `NEGAO_SERVICE_API_KEY`, sem default inseguro.
- CI ganhou scanner Gitleaks no checkout limpo.

### Estado

```text
CLASSIFICATION: POTENTIALLY ACTIVE / UNKNOWN
STATUS: PARTIAL
EXTERNAL OWNER ACTION REQUIRED
```

Remover o valor do working tree não revoga o segredo histórico. É necessária
rotação no Redis provider, Supabase, NVIDIA e qualquer serviço que tenha usado
as credenciais expostas. Não houve acesso autorizado para executar essa
rotação; nenhum valor foi impresso ou armazenado neste relatório.

## 6. Authentication Architecture

Implementação em `backend/app/modules/security/application/identity.py` e
`backend/app/modules/security/router.py`:

```text
POST /security/register  (development/test only)
        ↓
identity.users.password_hash (scrypt)

POST /security/login
        ↓
opaque token + identity.sessions(token_hash, exp, revoked_at)
        ↓
Bearer ou cookie sophie_session
        ↓
AuthResult(sub/user_id, session_id, device_id)
```

Tokens não são JWT e não carregam autoridade no cliente. A sessão é validada
no banco em cada request protegido; logout grava `revoked_at`. A senha nunca
é persistida em plaintext. O modelo de refresh token separado ainda não
existe; o access/session token tem TTL configurável de 8 horas nesta fase.

## 7. Authorization Architecture

Autenticação e autorização foram separadas:

- `require_authenticated_user`: identidade de usuário/sessão.
- `require_service_auth`: credencial explícita para endpoints administrativos
  de database.
- Produção rejeita `X-API-Key` como identidade de usuário.
- WebSockets não usam API key fallback em produção.
- Cookie em requests mutáveis de produção exige Origin permitido.
- Não existe ainda RBAC/ABAC/capability registry. O nível atual é
  `READ_ONLY`; capabilities futuras continuam architectural-only.

## 8. Resource Ownership

Ownership é derivado de `AuthResult.effective_user_id`, nunca de
`user_id` enviado pelo frontend. O store Redis grava:

```text
conversation:sessions:user:{user_id}
conv:{session_id}:meta -> user_id
conv:{session_id}:messages
```

`get_owned_session` exige correspondência sessão + usuário. Listagem usa o
índice do usuário. Endpoints não-owner retornam 404 sem confirmar existência
do recurso. WS voice ainda verifica que a sessão do ticket pertence ao dono
antes de iniciar o turno.

## 9. Session Security

- `identity.sessions.id` UUID.
- `token_hash` SHA-256 unique; token bruto não é persistido.
- Expiração e `revoked_at` são verificadas.
- `last_seen_at` é atualizado na autenticação.
- `device_id` opcional liga sessão ao dispositivo lógico.
- WS ticket: CSPRNG, TTL 60s, `GETDEL`/uso único, purpose e session binding.
- Origin WebSocket é rejeitada em produção quando não pertence à allowlist.
- Replay de ticket é coberto por teste unitário existente.

Não foi possível provar logout/expiração contra PostgreSQL real no ambiente.

## 10. Persistence Architecture

O histórico de conversa continua em Redis, não em PostgreSQL. A persistência
é funcional para curto prazo e depende da disponibilidade/configuração de
Redis; TTL atual é 24 horas. Falha de conexão, JSON inválido ou pipeline
falho gera `ConversationPersistenceError` e não confirma sucesso.

Operações multi-chave agora usam pipeline transacional: criação, append,
reset e delete. Isso reduz partial writes, mas não constitui uma transação
distribuída com LLM/event bus. Eventos de observabilidade ainda são
best-effort e não são tratados como prova de persistência.

## 11. Database Integrity

Migration chain verificada offline:

```text
<base> -> 0001_initial_schema -> 0002_identity_sessions (head)
```

`0001` foi corrigida para usar limites de partição com datas literais na
geração da migration; `0002` cria `password_hash`, devices e sessions com
FKs/indexes. O Dockerfile copia `migrations/` e os scripts usam
`alembic -c migrations/alembic.ini upgrade head`.

Teste executado:

```text
python -m alembic -c migrations/alembic.ini upgrade head --sql: PASS
python -m alembic -c migrations/alembic.ini heads: 0002_identity_sessions
```

Teste bloqueado: upgrade real em banco vazio e upgrade de banco
production-like, pois não havia PostgreSQL/Docker disponível. A CI agora
provisiona PostgreSQL pgvector para executar esse gate.

## 12. Health / Liveness / Readiness

`/health/live` e `/healthz` retornam `200 {"status":"alive"}` sem consultar
dependências. `/health/ready` e `/readyz` consultam PostgreSQL, Redis e
existência de `identity.users`/`identity.sessions`; `ready` retorna 200 e
`not_ready` retorna 503.

Testes unitários com dependências simuladas comprovaram ambos os códigos.
Teste contra serviços reais ficou bloqueado.

## 13. Observability

- `request_id`, `trace_id` e `correlation_id` em cada request.
- Headers de resposta: `x-request-id`, `x-trace-id`,
  `x-correlation-id`.
- Logs de access com método, path, status e duração.
- Métricas Prometheus de requests/duração/conexões/eventos.
- OpenTelemetry é inicializado quando configurado; endpoint não é logado
  integralmente.
- Redaction central para authorization, cookie, password, secret, token,
  api_key e access/refresh token.

Trace ponta a ponta em produção não foi testado sem deployment/collector.

## 14. Error Handling

Respostas internas não retornam stack trace. O envelope inclui código e
request ID, com categorias para authentication, authorization, validation,
not found, conflict, rate limit, dependency unavailable e internal error.

Banco/Redis requerido indisponível retorna 503. O backend não converte falha
de storage em `200 saved`.

## 15. CI/CD Security Gates

`.github/workflows/ci.yml` agora inclui:

- Ruff check.
- mypy.
- pytest.
- PostgreSQL pgvector + Redis de serviço.
- Alembic upgrade head em banco limpo.
- pip-audit.
- frontend lint, typecheck, build.
- npm audit production.
- Gitleaks no checkout de trabalho.

O workflow deliberadamente falhará enquanto as vulnerabilidades npm e
segredos históricos não forem tratados.

## 16. Adversarial Testing

| Teste | Resultado |
| --- | --- |
| Hash scrypt, senha errada e hash adulterado | PASS |
| Token opaco CSPRNG e unicidade | PASS |
| Usuário B lê mensagens da sessão A | PASS — negado |
| Usuário B é reconhecido como owner da sessão A | PASS — falso |
| Redis indisponível ao criar sessão | PASS — erro explícito |
| Ticket WS single-use | PASS |
| Ticket WS purpose mismatch/malformed | PASS |
| WS conversation sem credencial | PASS — policy close |
| Voice WS sem ticket antes de accept | PASS |
| Rotas HTTP sem auth fora da allowlist | PASS |
| Header/tokens nos logs | cobertura estrutural adicionada; captura em produção não testada |
| Token expirado/revogado contra PostgreSQL real | NOT TESTED — ENVIRONMENT BLOCKED |
| IDOR E2E com dois usuários reais | NOT TESTED — ENVIRONMENT BLOCKED |

## 17. Regression Results

Estado final local:

```text
pytest -q: 100 passed, 1 skipped
unit: 95 passed
e2e smoke ASGI: 5 passed
integration DB: 1 skipped — sem NEGAO_TEST_DATABASE_URL
ruff check app tests: PASS
mypy app: PASS — 119 arquivos
ruff format --check: FAIL — 37 arquivos; debt preexistente, sem reformat global
frontend npm run lint: PASS, warning ESLintIgnoreWarning
frontend npm run typecheck: PASS
frontend npm run build: PASS
Semgrep p/python: 0 findings em 119 arquivos / 151 regras
OSV scanner: FAIL — 4 pacotes, 7 vulnerabilidades conhecidas
npm audit --omit=dev --audit-level=high: FAIL — 4 HIGH
Gitleaks git: FAIL — 28 achados históricos
```

## 18. Remaining Findings

### FINDING FND-001

```text
ID: FND-001
AREA: Secrets / Git history
SEVERITY: CRITICAL
STATUS: PARTIAL
DESCRIPTION: Credenciais plausíveis permanecem em 52 commits históricos.
EVIDENCE: gitleaks git --redact encontrou 28 achados.
FILES: histórico Git; ocorrências históricas identificadas pela auditoria em b812556 e d3f5900.
RUNTIME TEST: não aplicável sem rotação autorizada.
RESULT: FAIL
IMPACT: possível acesso a Redis/Supabase/NVIDIA.
FRIDAY IMPACT: impede confiar microfone, memória e ações futuras.
RECOMMENDATION: revogar/rotacionar providers; avaliar limpeza de histórico com política do repositório.
CONFIDENCE: HIGH
```

### FINDING FND-002

```text
ID: FND-002
AREA: Dependency security
SEVERITY: HIGH
STATUS: OPEN
DESCRIPTION: nanoid, postcss e sharp transitivos vulneráveis; OSV encontrou também serialize-javascript dev.
EVIDENCE: npm audit: 4 HIGH; osv-scanner: 7 vulnerabilidades em 4 pacotes.
FILES: frontend/package-lock.json.
RUNTIME TEST: build PASS, exploração não testada.
RESULT: FAIL no security gate.
IMPACT: risco de XSS/path traversal/disclosure conforme advisory.
FRIDAY IMPACT: superfície BFF/frontend não pronta para credenciais pessoais.
RECOMMENDATION: atualizar versões compatíveis; avaliar upgrade major do Next isoladamente.
CONFIDENCE: HIGH
```

### FINDING FND-003

```text
ID: FND-003
AREA: Runtime integration
SEVERITY: HIGH
STATUS: BLOCKED
DESCRIPTION: fluxo real login -> sessão -> Redis/Postgres -> restart não foi executado.
EVIDENCE: Docker, PostgreSQL e Redis não estão instalados/disponíveis.
FILES: backend/app/modules/security, conversation, migrations.
RUNTIME TEST: NOT TESTED — ENVIRONMENT BLOCKED.
RESULT: sem prova live.
IMPACT: não permite afirmar autenticação/ownership de produção.
FRIDAY IMPACT: fundação não comprovada para dispositivos e memória pessoal.
RECOMMENDATION: executar ambiente isolado com dois usuários e DB/Redis reais.
CONFIDENCE: HIGH
```

### FINDING FND-004

```text
ID: FND-004
AREA: Formatting / CI
SEVERITY: MEDIUM
STATUS: OPEN
DESCRIPTION: formatter check continua falhando em 37 arquivos.
EVIDENCE: ruff format --check app tests.
FILES: backend/app e backend/tests.
RUNTIME TEST: não aplicável.
RESULT: lint semântico PASS; formatting FAIL.
IMPACT: ruído de revisão e gate incompleto.
FRIDAY IMPACT: indireto.
RECOMMENDATION: abrir mudança mecânica separada; não misturar com auth.
CONFIDENCE: HIGH
```

## 19. Environment-Blocked Tests

```text
NOT TESTED — ENVIRONMENT BLOCKED

Faltam:
- Docker/Compose.
- PostgreSQL pgvector isolado.
- Redis isolado.
- ambiente de teste com NEGAO_TEST_DATABASE_URL.
- provider NVIDIA autorizado para chamadas reais.
- deployment/collector para trace ponta a ponta.

Necessário posteriormente:
- alembic upgrade head em DB vazio;
- seed de User A/User B;
- login de ambos;
- create/read/update/delete cruzado;
- logout, expiração e revogação;
- restart da API e recuperação da conversa;
- DB/Redis outage e recovery;
- readiness 503 -> 200;
- WS ticket replay/origin/session binding.
```

## 20. External Owner Actions

1. Revogar e rotacionar credenciais Redis, Supabase e NVIDIA plausivelmente
   expostas no histórico/documentação anterior.
2. Confirmar por evidência do provider que as credenciais antigas estão
   inválidas.
3. Decidir, com política do repositório, se o histórico será reescrito; nunca
   tratar rewrite como substituto da rotação.
4. Atualizar dependências npm vulneráveis e reexecutar npm audit/OSV.
5. Disponibilizar ambiente isolado para fechar testes live.

## 21. Foundation Scores

```text
IDENTITY        68/100  — modelo e código implementados; live DB não provado
AUTHENTICATION  64/100  — sessão server-side; revogação/expiração live bloqueadas
AUTHORIZATION   58/100  — ownership aplicado; capability/RBAC ainda não existe
OWNERSHIP       72/100  — Redis user index + IDOR unitário; E2E real bloqueado
PERSISTENCE     62/100  — fail-closed/atomicidade local; Redis TTL, sem DB live
OBSERVABILITY   66/100  — IDs, métricas e redaction; trace live não provado
SECURITY        48/100  — código endurecido, mas histórico/secrets/deps abertos
TESTING         70/100  — 100 pass e gates estáticos; integração real bloqueada

FOUNDATION READINESS: 63/100
```

## 22. Foundation Gate

```text
FOUNDATION GATE: FAIL
```

Motivos bloqueantes: segredo histórico não rotacionado/confirmado revogado,
vulnerabilidades HIGH no frontend e ausência de prova runtime de DB/Redis,
login, revogação, restart e isolamento multiusuário real.

## 23. Updated FRIDAY Readiness

```text
FRIDAY READINESS: 18/100
CLASSIFICATION: CHATBOT
AUTONOMY: LEVEL 0 — CHAT
```

A nota não foi aumentada artificialmente: esta fase melhorou confiança da
fundação, mas não adicionou percepção, memória longa, tools, presença,
proatividade ou controle de dispositivos.

## 24. Recommended Next Phase

Depois de fechar o gate, a próxima fase é **SOPHIE VOICE V1 — TRUE E2E VOICE**:

```text
FOUNDATION
    ↓
VOICE E2E batch comprovado em ambiente isolado
    ↓
TRUE STREAMING
    ↓
VAD / BARGE-IN / FULL DUPLEX
    ↓
MEMORY com ownership e retention explícitos
    ↓
TOOLS / ACTION ENGINE / policy confirmation
    ↓
VISION
    ↓
DEVICE BRIDGE
    ↓
PROACTIVITY
    ↓
AMBIENT AI
```

Não iniciar Voice V1 antes de: rotação externa comprovada, npm audit resolvido,
migrations reais executadas e E2E de dois usuários verde.

## 25. Test Matrix Final

| Área | Testes | PASS | FAIL | SKIP | Blocked |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unit | 95 | 95 | 0 | 0 | 0 |
| E2E smoke ASGI | 5 | 5 | 0 | 0 | 0 |
| Integration DB | 1 | 0 | 0 | 1 | 1 |
| Authentication | unit/route coverage | PASS local | 0 | 0 | live DB |
| Authorization | ownership/route coverage | PASS local | 0 | 0 | live DB |
| Ownership | cross-user Redis store | PASS | 0 | 0 | E2E real |
| Persistence | fail-closed/pipeline | PASS local | 0 | 0 | Redis outage live |
| Health | liveness/readiness unit | PASS | 0 | 0 | dependency recovery live |
| Security | Semgrep/Gitleaks/npm/OSV | Semgrep | Gitleaks/npm/OSV | 0 | rotation/pip-audit |
| Frontend | lint/typecheck/build | 3 | 0 | 0 | 0 |

## 26. Before / After

```text
BEFORE
Global API key podia representar todos os usuários
Sessões/conversas sem ownership confiável
Falha Redis podia aparentar sucesso
Readiness podia responder 200 degradado
Sem request correlation consistente
Segredos plausíveis em docs/scripts e histórico
Migrations não eram copiadas para a imagem backend

AFTER (working tree)
Sessão server-side por usuário, com hash, expiração e revogação
Ownership derivado da identidade e índice Redis por usuário
Persistência requerida falha explicitamente e usa pipeline transacional
Liveness separado de readiness 200/503
request_id, trace_id, correlation_id e redaction
Arquivos versionados sanitizados; histórico/rotação continuam blockers
Dockerfile copia migrations e deploy aborta quando migration falha
```

## 27. Foundation Criteria Audit

```text
FOUNDATION-01 Secrets: FAIL — histórico e rotação externa pendentes
FOUNDATION-02 Authentication: PARTIAL — código implementado, live DB bloqueado
FOUNDATION-03 Authorization: PASS local / live BLOCKED
FOUNDATION-04 Ownership: PASS unitário / E2E BLOCKED
FOUNDATION-05 Session isolation: PARTIAL — migration/live DB bloqueados
FOUNDATION-06 Persistence: PASS local fail-closed
FOUNDATION-07 Failure mode: PASS unitário; outage real BLOCKED
FOUNDATION-08 Readiness: PASS unitário; recovery real BLOCKED
FOUNDATION-09 Liveness: PASS
FOUNDATION-10 Logging correlation: PASS estrutural
FOUNDATION-11 Secret redaction: PASS estrutural; produção BLOCKED
FOUNDATION-12 Error handling: PASS estrutural
FOUNDATION-13 Tests: PASS local com 100/1; formatter/deps pendentes
FOUNDATION-14 Adversarial: PASS unitário; E2E BLOCKED
FOUNDATION-15 Build: PASS lint/typecheck/build/mypy
FOUNDATION-16 Migrations: PASS offline/CI preparado; DB local BLOCKED
FOUNDATION-17 Documentation: PASS — este relatório + AS-BUILT
```
