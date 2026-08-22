# SOPHIE FOUNDATION 0.5 — GATE CLOSURE REPORT

Data da execução: 2026-08-22  
Escopo: fechamento de blockers P0/P1 da Foundation, sem implementação de capacidades FRIDAY.  
Ambiente de runtime: Windows + WSL Ubuntu 2, PostgreSQL 16 dedicado na porta 55432, Redis 7 dedicado na porta 6380 e API FastAPI local na porta 8766.

## 1. Executive Summary

A Foundation foi exercitada contra uma API real, PostgreSQL real e Redis real. Login, sessão server-side, cookie HttpOnly, expiração, logout, revogação, ownership multiusuário, IDOR, persistência Redis, restart do processo, falha/recovery de PostgreSQL e Redis, readiness/liveness e redaction de logs foram validados em runtime.

Foram corrigidos dois defeitos encontrados durante a própria prova: o health check de PostgreSQL usava incorretamente o contexto assíncrono de conexão e podia deixar conexões em estado inválido; e falhas nativas de conexão do driver durante autenticação escapavam como HTTP 500. Agora ambos os caminhos falham de forma explícita e segura.

O supply chain frontend foi remediado com atualização controlada de Next.js e overrides pinados. `npm audit --omit=dev`, OSV e o build final ficaram verdes. Ruff format foi aplicado ao backend e o gate foi adicionado à CI, juntamente com Semgrep.

O gate permanece **FAIL** por um blocker de incidente de credenciais: Gitleaks continua encontrando 28 ocorrências históricas em 52 commits, agrupadas em credenciais plausíveis de Redis, NVIDIA e autenticação legada, sem prova de rotação ou revogação. Nenhuma rotação externa foi executada porque não havia autorização nem credenciais administrativas dos providers.

Conclusão: a implementação local da Foundation está substancialmente mais confiável e possui runtime proof real, mas não pode ser declarada segura para PASS enquanto os roots históricos plausivelmente ativos não forem tratados pelo proprietário externo.

## 2. Scope

Incluído:

- secrets e histórico Git;
- dependências frontend e Python;
- PostgreSQL, Redis e migrations;
- autenticação, sessões, cookies e revogação;
- authorization, ownership e IDOR;
- persistência, restart, falhas e recovery;
- readiness, liveness, request/correlation IDs e logs;
- formatter, Semgrep, Gitleaks, auditorias de dependências e regressão.

Explicitamente fora do escopo: voz realtime, STT/TTS novos, WebRTC, VAD, wake word, câmera, visão, memória longa, agents, tools, Spotify, calendário, e-mail, desktop control e proatividade.

## 3. Original Blockers

| Blocker | Resultado 0.5 |
| --- | --- |
| Historical secrets | **BLOCKED**: 28 findings históricos, sem rotação/revogação comprovada |
| Frontend dependencies | **CLOSED**: audit de produção e OSV sem issues após atualização controlada |
| Runtime PostgreSQL/Redis | **CLOSED WITH PREREQUISITE**: testados em instâncias dedicadas reais |
| Real E2E | **CLOSED** para os fluxos executados |
| Formatter | **CLOSED**: backend inteiro formatado e check verde |

## 4. Baseline

Baseline inicial desta fase, antes das correções:

```text
Backend tests: 100 passed, 1 skipped
Ruff: PASS
Mypy: PASS
Frontend lint: PASS
Frontend typecheck: PASS
Frontend build: PASS
Formatter: FAIL — 37 files would be reformatted
Semgrep: execução inicial inválida por path incorreto; rerun posterior PASS
Gitleaks history: 28 findings em 52 commits
npm audit production: 4 HIGH
OSV: 7 issues em 4 packages
Migrations offline: PASS
```

Resultado final local:

```text
Backend tests: 100 passed, 2 skipped, 1 warning
Ruff check: PASS
Ruff format --check: PASS — 144 files already formatted
Mypy: PASS — 119 source files
Frontend lint: PASS
Frontend typecheck: PASS
Frontend build: PASS — Next.js 15.5.23
Semgrep: PASS — 0 findings em 119 files / 151 rules
pip-audit: PASS — no known vulnerabilities
npm audit --omit=dev: PASS — 0 vulnerabilities
OSV: PASS — no issues found
Migration current: 0002_identity_sessions (head)
```

## 5. Historical Secret Investigation

Comando executado:

```text
gitleaks git --redact --no-banner --verbose
```

Resultado: 28 findings em 52 commits, sem exposição dos valores no terminal ou no relatório.

As ocorrências históricas concentram-se em documentação antiga (`REDIS_CLOUD_CONFIG.md`, `START_HERE.md`, `TESTING_GUIDE.md`, `API_INTEGRATION_GUIDE.md`, `INTEGRATION_README.md` e `INFRASTRUCTURE_READY.md`). O histórico também registra explicitamente que a infraestrutura antiga usava Redis Cloud, Supabase e NVIDIA.

O scan do código atual foi segmentado para evitar falsos positivos de ambientes locais e dependências geradas:

```text
backend/app: PASS — no leaks found
backend/migrations: PASS — no leaks found
backend/tests: PASS — no leaks found
frontend/app: PASS — no leaks found
docs/sophie: PASS — no leaks found
```

O scan bruto do diretório de trabalho local não é um gate de source confiável porque inclui `.env`, `.venv`, `.next` e `.vercel`, que não são versionados; após a instalação do `pip-audit` ele encontrou 224 matches em artefatos locais/dependências. Esses matches foram separados dos arquivos de produto e não foram tratados como secrets do HEAD.

## 6. Credential Root Matrix

Os valores foram sempre redigidos. A correlação abaixo é por provider, contexto, regra Gitleaks e arquivo; não é uma tentativa de reconstruir o segredo.

| Credential root | Provider/contexto | Histórico | Current HEAD | Rotated/revoked | Gate |
| --- | --- | ---: | --- | --- | --- |
| Redis Cloud auth | Redis; `curl -u` em documentação histórica | 2+ matches relacionados | não detectado no source atual | não comprovado | **BLOCKER** |
| Legacy shared API key | X-API-Key/API key nos exemplos antigos | múltiplas ocorrências repetidas em 52 commits | API key não é identidade de usuário em produção; exemplos atuais estão redigidos | não comprovado | **BLOCKER** |
| NVIDIA API key | `NEGAO_NVIDIA_API_KEY` em documentação/histórico e `.env` local | ocorrência histórica plausível | ausente do source versionado; `.env` local preservado e não exibido | não comprovado | **BLOCKER** |
| Supabase publishable/anon key | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | ocorrências históricas | não detectado no source atual | publishable/anon não foi tratado como `service_role`; status externo não verificado | **REVIEW REQUIRED** |

Classificação operacional: Redis, NVIDIA e API key legado são **POTENTIALLY ACTIVE / UNKNOWN**. A chave Supabase foi classificada como **public publishable/anon candidate**, mas requer confirmação do owner para excluir definitivamente um uso indevido de service role, JWT secret ou password. Não há evidência nesta execução de `service_role`, private key ou database password versionados no HEAD.

## 7. Rotation / Revocation Proof

Nenhuma rotação ou revogação externa foi executada. Não havia autoridade administrativa nem acesso seguro aos providers para fazê-la.

```text
Status: EXTERNAL OWNER ACTION REQUIRED
```

Para fechar o blocker, o owner deve:

1. revogar/rotacionar o root Redis histórico;
2. revogar/rotacionar o root NVIDIA histórico;
3. invalidar a API key legada compartilhada, se ainda existir em qualquer ambiente;
4. confirmar a natureza e o status da chave Supabase publishable/anon;
5. fornecer prova operacional sem expor novos valores: timestamp, provider, identificador parcial e evidência de que o valor antigo não autentica mais.

Reescrever o Git history, se desejado, é ação posterior e não substitui rotação.

## 8. Dependency Security

O baseline revelou 4 vulnerabilidades HIGH no frontend, incluindo caminhos envolvendo `nanoid`, `postcss` e `sharp`, além de issues transitivas capturadas por OSV.

Remediação aplicada em `frontend/package.json` e `package-lock.json`:

```text
next: ^15.1.6 -> ^15.5.23
eslint-config-next: ^15.1.6 -> ^15.5.23
nanoid override: 3.3.18
postcss override: 8.5.23
serialize-javascript override: 7.0.5
sharp override: 0.35.0
```

Não foi utilizado `npm audit fix --force`.

Provas:

- `npm ci --ignore-scripts`: PASS;
- `npm audit --omit=dev --audit-level=high`: 0 vulnerabilities;
- `osv-scanner scan source --lockfile=package-lock.json`: no issues found;
- `npm run lint`: PASS;
- `npm run typecheck`: PASS;
- `npm run build`: PASS.

Warnings de pacotes deprecated transitivos permanecem informativos, sem advisory HIGH/CRITICAL explorável identificado pelos scanners executados.

## 9. PostgreSQL Runtime Validation

Foi criada uma instância PostgreSQL 16 dedicada na porta 55432, separada do cluster existente na porta 5432. O banco e role de teste eram dedicados à Foundation 0.5.

Provas executadas:

- conexão real com `asyncpg`/SQLAlchemy;
- migrations até `0002_identity_sessions`;
- consulta real das tabelas `identity.users` e `identity.sessions`;
- `SELECT` direto após login para validar `session.user_id`;
- outage real do cluster dedicado;
- recovery real sem reiniciar a API.

Resultado:

```text
Migration current: 0002_identity_sessions (head)
DB down -> /health/live 200
DB down -> /health/ready 503
DB down -> authenticated status 503
DB restored -> /health/ready 200
DB restored -> authenticated status 200
```

Limitação importante: a migration cria a extensão `vector`, que exige privilégio de superuser. A execução como role de aplicação não superuser falhou com `permission denied to create extension "vector"`; as extensões `vector` e `pgcrypto` foram então provisionadas pelo DBA da instância dedicada e a migration schema-zero-to-head passou. A CI atual usa a imagem pgvector com role de serviço superuser. O provisionamento explícito por DBA deve ser formalizado antes de usar uma role de aplicação least-privilege para migrations.

## 10. Redis Runtime Validation

Foi iniciado Redis 7 dedicado na porta 6380, database 14, sem tocar no Redis compartilhado existente.

O Redis é dependência crítica atual para:

- sessões/eventos de autenticação publicados;
- readiness;
- histórico de conversas;
- rate/event state.

Provas:

```text
Redis down -> /health/live 200
Redis down -> /health/ready 503
Redis down -> criação persistente 503
Redis restored -> /health/ready 200
Redis restored -> criação persistente 200
```

## 11. Migration Validation

Comando final:

```text
python -m alembic -c migrations/alembic.ini current
0002_identity_sessions (head)
```

O caminho real de banco vazio foi executado contra PostgreSQL dedicado com as extensões necessárias previamente provisionadas. A migration é transacional e não houve reexecução indevida no `current`.

## 12. Authentication E2E

Arquivo de prova: `backend/tests/tests_integration/test_foundation_runtime_e2e.py`.

Resultado real: `1 passed in 1.58s` contra FastAPI, PostgreSQL e Redis reais.

| Teste | Resultado |
| --- | --- |
| Login A/B | PASS |
| Sessão server-side criada | PASS |
| Cookie `HttpOnly` | PASS |
| `SameSite=Lax` | PASS |
| Cookie de sessão aceito pelo backend | PASS |
| Acesso autenticado | PASS |
| Sem sessão | 401 PASS |
| Sessão inválida | 401 PASS |
| Expiração real no banco | 401 PASS |
| Logout | 204 PASS |
| Revogação server-side | PASS |
| Replay após revogação | 401 PASS |
| Cookie `Secure` | dependente de `env=production`; não exercitado em HTTP local |

## 13. Authorization E2E

Autenticação e autorização continuam separadas. A API não usa `user_id` enviado no payload como fonte de autoridade.

Resultado real: PASS para os fluxos cobertos. Falhas de banco durante a autenticação agora retornam 503, não 500 nem 401 falso.

## 14. Ownership / IDOR E2E

| Ataque | Esperado | Resultado |
| --- | --- | --- |
| B lê conversa de A | deny | 404 PASS |
| B altera conversa de A | deny | 404 PASS |
| B exclui conversa de A | deny | 404 PASS |
| B lê mensagens de A | deny | 404 PASS |
| B envia `user_id=A` ao criar | ignorar/deny | recurso ficou de B PASS |
| A acessa recurso próprio | allow | 200 PASS |
| Session row de A | `user_id=A` no banco | PASS |
| Session row de B | separado de A | PASS |

O comportamento 404 evita revelar desnecessariamente a existência de recurso de outro usuário.

## 15. Persistence Tests

A arquitetura real atual não grava conversas no PostgreSQL. Usuários, devices e sessões ficam no PostgreSQL; conversas e mensagens ficam no Redis com TTL de 24 horas.

Provas:

- `POST /conversation/sessions` com Redis disponível: 200;
- mensagem marcador persistida: 200;
- consulta direta ao Redis encontrou `conv:{session_id}:meta` com owner correto;
- consulta direta ao Redis encontrou a mensagem marcador;
- Redis indisponível: 503, sem falso sucesso;
- PostgreSQL indisponível: 503 em operações autenticadas que dependem de identidade.

Portanto, a prova é de persistência real em Redis para conversa e de persistência real em PostgreSQL para identidade/sessão. Não deve ser interpretada como persistência de histórico de conversa em PostgreSQL.

## 16. Restart Tests

Arquivo: `backend/tests/tests_integration/foundation_runtime_restart_probe.ps1`.

O teste criou usuário, sessão, conversa e mensagem, encerrou o processo Uvicorn, iniciou outro processo, fez login novamente e recuperou a mensagem pelo mesmo conversation ID.

```text
RESTART_READY=1
RESTART_PERSISTED=1
RESTART_HISTORY_STATUS=200
RESTART_OWNER_VALIDATED=1
```

## 17. Recovery Tests

Arquivo: `backend/tests/tests_integration/foundation_runtime_failure_probe.ps1`.

```text
READY_BEFORE=200
PERSISTENCE_BEFORE=200
REDIS_DOWN_LIVE=200
REDIS_DOWN_READY=503
REDIS_DOWN_PERSISTENCE=503
REDIS_RESTORED_READY=200
REDIS_RESTORED_PERSISTENCE=200
DB_DOWN_LIVE=200
DB_DOWN_READY=503
DB_DOWN_AUTH=503
DB_RESTORED_READY=200
DB_RESTORED_AUTH=200
```

Durante a primeira execução foi encontrado e corrigido um bug de readiness causado pelo uso de `await asyncio.wait_for(engine.connect(), ...)` dentro de `async with`. A implementação final usa timeout externo ao contexto `async with engine.connect()`, evitando conexão já iniciada e warning de conexão não devolvida ao pool.

## 18. Health / Readiness

Implementação final:

- `/health/live`: responde pelo estado do processo e não depende de PostgreSQL/Redis;
- `/health/ready`: verifica ambos os serviços críticos;
- pronto: 200 com `{"status":"ready"}`;
- indisponível: 503 com `{"status":"not_ready"}` e checks individuais.

Runtime proof confirmou que readiness não mente durante as duas quedas controladas e recupera depois.

## 19. Observability Validation

Runtime logs estruturados contêm `request_id`, `correlation_id`, rota, método, status e duração. O fluxo E2E confirmou `x-request-id` em resposta de operação de conversa e os logs da API registraram o mesmo tipo de correlação.

Eventos de autenticação e falhas de dependência são registrados com contexto seguro. O conteúdo de mensagens não foi usado como log de auditoria durante os probes.

## 20. Log Redaction Validation

Não foram impressos tokens, passwords, URLs de banco, URLs Redis ou valores de API key nos comandos e relatórios. Os logs de runtime não registraram o valor completo de cookie ou `Authorization`.

Stack traces de dependências foram mantidos apenas no log interno do processo; a resposta HTTP de falha retornou código e mensagem genéricos. O primeiro 500 de banco observado antes da correção foi convertido em 503 e não permanece no fluxo final.

## 21. Formatter Remediation

O formatter inicial indicava 37 arquivos fora do padrão em `app`/`tests`. A normalização foi executada mecanicamente. O teste E2E adicionado posteriormente e dois arquivos de migration também foram normalizados.

Resultado final:

```text
ruff format --check backend: PASS
144 files already formatted
```

Não houve refactor funcional associado à formatação.

## 22. Security Scanners

| Scanner | Resultado |
| --- | --- |
| Semgrep `p/python` em `backend/app` | 0 findings, 0 blocking |
| Gitleaks source segmentado | no leaks em app, migrations, tests, frontend/app e docs/sophie |
| Gitleaks histórico | 28 findings; blocker externo permanece |
| Ruff | PASS |
| pip-audit | no known vulnerabilities |
| npm audit production | 0 vulnerabilities |
| OSV lockfile | no issues found |

## 23. Dependency Audit

| Package/path | Antes | Depois | Resultado |
| --- | --- | --- | --- |
| `next` | `^15.1.6` | `^15.5.23` | build/lint/typecheck PASS |
| `eslint-config-next` | `^15.1.6` | `^15.5.23` | PASS |
| `nanoid` transitivo | vulnerável | override `3.3.18` | OSV PASS |
| `postcss` transitivo | vulnerável | override `8.5.23` | OSV PASS |
| `serialize-javascript` transitivo | advisory medium | override `7.0.5` | OSV PASS |
| `sharp` | vulnerável | override `0.35.0` | npm audit PASS |

## 24. Regression Suite

```text
pytest: 100 passed, 2 skipped, 1 warning
ruff check: PASS
ruff format --check: PASS
mypy: PASS
frontend lint: PASS
frontend typecheck: PASS
frontend build: PASS
Semgrep: PASS
pip-audit: PASS
npm audit: PASS
OSV: PASS
```

Os dois skips são ambientais/testes que não constituem prova de runtime; a prova real foi executada separadamente com o servidor e as dependências reais.

## 25. Remaining Risks

1. **P0 — credentials historical incident:** sem prova de rotação/revogação, o gate não pode passar.
2. **P1 — migration privilege contract:** `vector` exige provisionamento privilegiado; formalizar migration runner/DBA antes de executar com role de aplicação restrita.
3. **P1 — conversation durability:** o histórico está no Redis com TTL de 24h; não é memória longa nem persistência PostgreSQL. Durabilidade depende da política real de Redis, ainda não validada em produção.
4. **P1 — production cookie proof:** `Secure=True` depende de `NEGAO_ENV=production`; não foi testado em domínio/TLS real.
5. **P2 — observability backend:** há logs estruturados e métricas Prometheus básicas, mas não houve validação de collector/dashboard/alerta externo.
6. **P2 — Redis authentication/ACL:** o Redis isolado de teste foi local; ACL/TLS e least privilege do ambiente externo continuam sem prova.
7. **Known capability gaps:** pseudo-streaming, providers de IA, voice batch/realtime, agents, tools, memory longa, vision e proatividade permanecem fora desta fase.

## 26. Environment-Blocked Tests

Os seguintes testes não foram executados em ambiente de produção e não foram simulados como PASS:

| Teste | Status | Falta |
| --- | --- | --- |
| rotação Redis/Supabase/NVIDIA | NOT TESTED — ENVIRONMENT BLOCKED | acesso autorizado aos providers/owners |
| TLS, HSTS e cookie Secure em domínio real | NOT TESTED — ENVIRONMENT BLOCKED | domínio e endpoint HTTPS autorizado |
| PostgreSQL/Redis de produção | NOT TESTED — ENVIRONMENT BLOCKED | ambiente de homologação autorizado |
| collector/alertas Sentry/OTel | NOT TESTED — ENVIRONMENT BLOCKED | infraestrutura de observabilidade |
| NVIDIA real | NOT TESTED — ENVIRONMENT BLOCKED | provider e credencial autorizados |
| hardware de microfone/câmera/Bluetooth | fora do escopo | próxima fase |

## 27. External Owner Actions

```text
Provider: Redis
Secret ID: historical Redis auth root, redacted
Reason: historical Gitleaks findings without revocation proof
Required action: revoke/rotate and confirm old credential invalid
Proof required: provider audit/event evidence with value redacted
Gate impact: blocking

Provider: NVIDIA
Secret ID: historical NVIDIA API key root, redacted
Reason: plausible historical API key without status proof
Required action: revoke/rotate and update only the external secret store
Proof required: provider evidence that old key is invalid
Gate impact: blocking

Provider: Sophie legacy auth
Secret ID: historical shared X-API-Key root, redacted
Reason: shared service/user credential appeared in old docs
Required action: invalidate if still accepted anywhere; confirm service-only scope
Proof required: negative authentication test in supported environments
Gate impact: blocking until classified

Provider: Supabase
Secret ID: publishable/anon candidate, redacted
Reason: determine whether it is public client key or privileged secret
Required action: confirm type and rotate if not strictly publishable
Proof required: project key classification and old-key status
Gate impact: review; blocking if privileged
```

## 28. Foundation Readiness Score

| Área | Score |
| --- | ---: |
| Identity | 90 |
| Authentication | 88 |
| Authorization | 86 |
| Ownership | 88 |
| Session security | 86 |
| Persistence | 72 |
| Database | 74 |
| Cache/runtime dependency | 78 |
| Observability | 72 |
| Security | 58 |
| CI/CD | 78 |
| Runtime proof | 88 |

```text
FOUNDATION READINESS: 78/100
```

O score não é 100 porque o incidente histórico de secrets, o contrato de privilégio de `vector`, a durabilidade Redis e a ausência de ambiente externo comprovado permanecem.

## 29. Updated FRIDAY Readiness

```text
FRIDAY READINESS: 18/100
CLASSIFICATION: CHATBOT
AUTONOMY: LEVEL 0 — CHAT
```

Esta fase melhorou confiabilidade, não adicionou percepção, ação, memória longa, presença ou proatividade. Portanto, não há justificativa técnica para aumentar artificialmente o índice FRIDAY.

## 30. Foundation Gate

```text
FOUNDATION GATE: FAIL
```

Motivo bloqueante: há 28 findings históricos em 52 commits e nenhum proof de rotação/revogação para os roots potencialmente ativos de Redis, NVIDIA e autenticação legada. O critério de fail automático do Foundation 0.5 exige que toda credencial plausivelmente ativa tenha sido rotacionada/revogada ou formalmente encerrada pelo owner.

Os critérios de runtime, ownership, persistência fail-closed, readiness, liveness, redaction, formatter, scanners e regressão executados nesta máquina foram satisfeitos. Isso não supera o blocker de credenciais externas.

## 31. Next Recommended Phase

Não iniciar Voice V1 ainda como gate de segurança global. Primeiro fechar as ações externas acima e formalizar o provisionamento de `vector` para o runner de migrations least-privilege.

Após obter:

```text
old secrets revoked/rotated
historical incident acknowledged
migration privilege contract documented and tested in CI/homologation
```

a próxima fase recomendada é:

```text
SOPHIE VOICE V1 — REAL END-TO-END VOICE
MICROPHONE -> REAL STT -> SOPHIE CORE -> REAL TTS -> HEADSET
```

Sequência preservada:

```text
FOUNDATION
    ↓
FOUNDATION GATE CLOSURE
    ↓
VOICE E2E
    ↓
REALTIME VOICE
    ↓
MEMORY
    ↓
TOOLS / ACTIONS
    ↓
VISION
    ↓
DEVICE BRIDGE
    ↓
PROACTIVITY
    ↓
AMBIENT AI
```

## Evidence Index

| Evidência | Localização |
| --- | --- |
| DB health timeout fix | `backend/app/infrastructure/db.py` |
| Auth dependency fail-closed fix | `backend/app/modules/security/router.py` |
| Real auth/ownership/revocation E2E | `backend/tests/tests_integration/test_foundation_runtime_e2e.py` |
| Redis/DB outage and recovery probe | `backend/tests/tests_integration/foundation_runtime_failure_probe.ps1` |
| Restart persistence probe | `backend/tests/tests_integration/foundation_runtime_restart_probe.ps1` |
| CI formatter/Semgrep gates | `.github/workflows/ci.yml` |
| Dependency remediation | `frontend/package.json`, `frontend/package-lock.json` |
