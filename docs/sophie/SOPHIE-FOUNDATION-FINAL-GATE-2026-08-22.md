# SOPHIE FOUNDATION 0.6 — FINAL GATE REPORT

Data da execução: 2026-08-22  
Escopo: remediação de secrets, revogação, prova runtime e fechamento do Foundation Gate.  
Regra: nenhum segredo completo é reproduzido neste documento.

## 1. Executive Summary

A remediação de código da SOPHIE foi concluída para a credencial API legada: `NEGAO_API_KEY` deixou de ser uma autoridade de autenticação, usuários finais passaram a ser aceitos exclusivamente por sessão server-side e a chave antiga foi testada em um processo isolado de produção, retornando `401` tanto em rota de usuário quanto em rota de serviço.

O gate não pode ser fechado. A investigação agrupou as 28 ocorrências históricas do Gitleaks em quatro roots. Dois roots plausivelmente reais continuam válidos no mundo externo:

- Redis Cloud: `fp: 51f2b2be4ddf…`; `PING` e `ACL WHOAMI` foram aceitos.
- NVIDIA: `fp: 4b194fc430c6…`; `GET /models` retornou `200`.

Não há credencial administrativa/autorização disponível neste ambiente para revogar ou rotacionar esses providers. Isso exige ação do owner externo. A remoção do segredo do source não substitui essa ação.

Resultado objetivo:

```text
CODE REMEDIATION: COMPLETE FOR LEGACY API AUTHORITY
INCIDENT CLOSURE: BLOCKED BY PROVIDER OWNER
FOUNDATION GATE: FAIL
```

As regressões locais permanecem verdes: backend `101 passed, 2 skipped`, Ruff, formatter, mypy, frontend lint/typecheck/build, Semgrep, pip-audit, npm audit e OSV passaram. O FRIDAY Readiness permanece `18/100`; esta fase não adiciona capacidades FRIDAY.

## 2. Starting State

Estado informado no início da fase:

| Item | Estado inicial |
| --- | --- |
| Foundation Readiness | 78/100 |
| FRIDAY Readiness | 18/100 |
| Classificação | CHATBOT |
| Autonomia | LEVEL 0 — CHAT |
| Foundation Gate | FAIL |
| Gitleaks histórico | 28 ocorrências em 52 commits |

O blocker restante era a ausência de prova de rotação, revogação ou invalidação das credenciais históricas plausíveis.

## 3. Scope

Incluído:

- agrupamento dos findings históricos por fingerprint irreversível;
- classificação dos roots Redis, NVIDIA, Supabase publishable e API legada;
- remoção da autoridade de `NEGAO_API_KEY` do runtime;
- prova de bypass legado em runtime isolado;
- prova sanitizada de validade atual Redis/NVIDIA;
- Gitleaks current-source/history;
- regressão backend/frontend/security/supply-chain;
- documentação do bloqueio externo e do próximo gate.

Fora de escopo e não implementado:

- Voice, STT/TTS novo, streaming, WebRTC, VAD, wake word e full-duplex;
- Memory, Agents, Tools, Vision, Action Engine e Proactivity;
- microserviços, troca de stack, deploy, release e reescrita de histórico Git.

## 4. Historical Secret Inventory

O scan histórico foi reexecutado com `gitleaks git --redact --log-opts=--all`.

```text
Historical occurrences: 28
Commits with findings: 52
Unique probable roots: 4
Current source-path findings: 0
```

Os fingerprints foram calculados localmente com SHA-256 do valor e truncados para correlação. O valor original nunca foi emitido no terminal, relatório ou log.

## 5. Root Credential Analysis

| Secret ID | Provider | Type | Occurrences | First commit | Last commit | Current local match | Status |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| `fp: 51f2b2be4ddf…` | Redis Cloud | credencial na URL de conexão | 2 | `b812556…` | `d3f5900…` | `NEGAO_REDIS_URL` | **ACTIVE** |
| `fp: 4b194fc430c6…` | NVIDIA | API key | 2 | `b812556…` | `b812556…` | `NEGAO_NVIDIA_API_KEY` | **ACTIVE** |
| `fp: 63edef50737c…` | Sophie/legado | API key global histórica | 20 | `195fc3…` | `d3f5900…` | `NEGAO_API_KEY` | **REVOKED AS APPLICATION AUTHORITY** |
| `fp: d45184a6fc42…` | Supabase | publishable/anon candidate via `NEXT_PUBLIC_*` | 4 | `b812556…` | `d3f5900…` | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | **FALSE POSITIVE CANDIDATE / OWNER CONFIRMATION** |

### Confiança

- Redis: HIGH. O fingerprint coincidiu com a variável local e a autenticação contra o serviço real foi aceita.
- NVIDIA: HIGH. O fingerprint coincidiu com a variável local e uma chamada autenticada de leitura retornou `200`.
- API legada: HIGH para a remoção da autoridade da aplicação; a prova é o `401` em runtime isolado.
- Supabase: MEDIUM. O nome `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` indica credencial pública/anon, não `service_role`; o owner deve confirmar a classificação.

## 6. Redis Remediation

### Estado observado

O root Redis `fp: 51f2b2be4ddf…` coincide com a configuração local `NEGAO_REDIS_URL`. A conexão foi feita contra o Redis Cloud configurado sem imprimir host completo, URL ou senha.

### Runtime proof

Probe: `backend/tests/tests_integration/foundation_provider_secret_probe.py`

```text
REDIS_ENV_CREDENTIAL_PING=SUCCESS
REDIS_ENV_CREDENTIAL_WHOAMI=b'default'
```

Conclusão: a credencial histórica ainda é aceita pelo Redis real. Não houve rotação nem revogação porque não existe neste ambiente credencial administrativa ou autorização para alterar o provider. Não foram executados comandos destrutivos de ACL/configuração.

### Status

```text
REDIS SECRET STATUS: ACTIVE
CODE REMEDIATION: NO SOURCE SECRET
ROTATION/REVOCATION: BLOCKED — EXTERNAL OWNER ACTION REQUIRED
```

## 7. NVIDIA Remediation

### Estado observado

O root NVIDIA `fp: 4b194fc430c6…` coincide com `NEGAO_NVIDIA_API_KEY` local. A Sophie não precisa de um novo provider nesta fase; portanto, se o provider não for necessário no ambiente atual, a ação preferível é revogar sem substituir.

### Runtime proof

Probe: `backend/tests/tests_integration/foundation_provider_secret_probe.py`

```text
NVIDIA_ENV_CREDENTIAL_MODELS_STATUS=200
```

Conclusão: a credencial histórica ainda é válida. Não existe token administrativo/dashboard autorizado neste ambiente para revogação.

### Status

```text
NVIDIA SECRET STATUS: ACTIVE
CODE REMEDIATION: NO SOURCE SECRET
ROTATION/REVOCATION: BLOCKED — EXTERNAL OWNER ACTION REQUIRED
```

## 8. Legacy API Key Remediation

A autoridade legada foi removida com alterações mínimas:

- `backend/app/modules/configuration/settings.py:30-32`: `api_key` deixou de ser campo de configuração de autoridade.
- `backend/app/modules/security/infrastructure/__init__.py:45-50`: `create_security_service` usa somente `service_api_key`; não há fallback para `api_key`/`NEGAO_API_KEY`.
- `backend/app/modules/security/router.py:122-127`: `require_authenticated_user` resolve usuário exclusivamente por bearer/session cookie.
- A autenticação de serviço permanece separada e exige `NEGAO_SERVICE_API_KEY` explícita; ela não representa usuário final.
- Os testes unitários, smoke e WebSocket foram atualizados para usar credencial de serviço explícita ou sessão/ticket.

### Legacy bypass runtime proof

Probe: `backend/tests/tests_integration/foundation_legacy_key_probe.ps1`. O processo foi iniciado com `NEGAO_ENV=production`, PostgreSQL e Redis dedicados, e a antiga chave foi lida em memória apenas para a requisição.

```text
LEGACY_KEY_SECURITY_STATUS=401
LEGACY_KEY_SERVICE_STATUS=401
```

Conclusão: a chave antiga não restaura acesso de usuário nem autenticação de serviço no runtime atual.

```text
LEGACY APPLICATION AUTHORITY: REVOKED
CONFIDENCE: HIGH
```

## 9. Rotation / Revocation Evidence

| Root | Evidência obtida | Resultado |
| --- | --- | --- |
| Redis `fp: 51f2b2be4ddf…` | autenticação real aceita | **não revogado; blocker** |
| NVIDIA `fp: 4b194fc430c6…` | request real `/models` aceita | **não revogado; blocker** |
| API legada `fp: 63edef50737c…` | runtime isolado retorna `401` em duas classes de rota | autoridade da aplicação removida |
| Supabase `fp: d45184a6fc42…` | nome/prefixo público; sem evidência de `service_role` | confirmação do owner pendente |

Não foi declarado nenhum provider como revogado sem prova.

## 10. Current HEAD Secret Scan

O probe `backend/tests/tests_integration/foundation_gitleaks_probe.ps1` executou Gitleaks com redaction sobre os caminhos atuais relevantes:

```text
backend/app                  0
backend/tests                0
frontend/app                 0
docs/sophie                  0
.github                      0
frontend/package*.json       0
backend/pyproject.toml       0
CURRENT_SOURCE_FINDINGS      0
```

O `.env` local permanece ignorado e contém credenciais operacionais atuais; ele não está no HEAD versionado e não foi alterado nesta execução. Essa separação é importante: `HEAD` está sem findings nos caminhos-fonte auditados, mas os providers externos ainda aceitam dois valores históricos.

## 11. Historical Secret Scan

```text
HISTORY_FINDINGS=28
UNIQUE_ROOTS=4
```

Os findings históricos não foram suprimidos por allowlist e o histórico Git não foi reescrito. Eles só poderiam ser classificados integralmente como `HISTORICAL EXPOSURE — REMEDIATED` depois da revogação/rotação comprovada dos roots Redis e NVIDIA.

## 12. Log / Error Redaction

Validações realizadas:

- probes imprimem somente status, fingerprint truncado ou classificação;
- nenhum Redis URL, NVIDIA token, API key, password ou cookie foi escrito no relatório;
- redaction estruturada existente cobre `authorization`, `cookie`, `password`, `secret`, `token`, `api_key`, `access_token` e `refresh_token`;
- Semgrep não encontrou finding na aplicação;
- os testes de autenticação e falha continuam usando respostas genéricas sem credenciais.

Resultado: PASS para o comportamento de logging observado; a rotação externa continua independente disso.

## 13. Legacy Authentication Bypass Tests

| Teste | Resultado |
| --- | --- |
| antiga chave em `/security/status` sem sessão | `401` — PASS |
| antiga chave em `/database/status` | `401` — PASS |
| serviço com `service_api_key` explícita | coberto por smoke/unit — PASS |
| WebSocket com antiga chave | fallback resolve somente chave de serviço explícita; antiga rejeitada pelo serviço — PASS |
| sessão server-side válida | regressão E2E anterior — PASS |

## 14. Runtime Regression

As provas runtime reais da Foundation 0.5 continuam válidas e não foram quebradas pela remediação:

- PostgreSQL real dedicado, migrations zero-to-latest, persistência e restart: PASS;
- Redis real dedicado, failure/recovery e readiness: PASS;
- login/logout/expiração/revogação/ownership/IDOR/multi-user: PASS;
- operação persistente com dependência indisponível: sem falso sucesso;
- liveness permanece independente da indisponibilidade da dependência crítica.

Provas específicas desta fase:

- Redis provider credential: autenticação aceita — FAIL de fechamento;
- NVIDIA provider credential: autenticação aceita — FAIL de fechamento;
- legacy key application bypass: rejeitado — PASS.

## 15. Backend Regression

```text
pytest: 101 passed, 2 skipped, 1 warning
ruff check: PASS
ruff format --check: PASS (144 files already formatted)
mypy: PASS — 119 source files
```

A warning restante é a depreciação do `httpx` no `starlette.testclient`; não é blocker de segurança desta fase.

## 16. Frontend Regression

```text
npm run lint: PASS
npm run typecheck: PASS
npm run build: PASS
```

O primeiro build executado em paralelo com scanners pesados falhou com `spawn UNKNOWN` por pressão de recursos locais. A repetição sequencial compilou, gerou as páginas estáticas e finalizou com sucesso. Não foi tratado como falha funcional.

## 17. Security Scanners

| Scanner | Resultado |
| --- | --- |
| Semgrep `p/python` | PASS — 0 findings, 119 arquivos, 151 regras |
| pip-audit | PASS — no known vulnerabilities; pacote local não auditável no PyPI |
| npm audit `--omit=dev --audit-level=high` | PASS — 0 vulnerabilities |
| OSV scanner | PASS — 680 packages, no issues |
| Gitleaks current source paths | PASS — 0 |
| Gitleaks history | 28 ocorrências históricas; não é PASS de incidente enquanto roots ativos persistirem |

## 18. PostgreSQL / Redis Validation

### PostgreSQL

O ambiente dedicado da Foundation 0.5 permanece a referência runtime: PostgreSQL real na porta isolada, migrations aplicadas desde banco vazio, persistência recuperada após restart, failure e recovery comprovados. A role da aplicação não recebe superuser.

### Redis

O Redis local dedicado foi usado pelo probe de bypass e pela Foundation runtime. A conexão provider-backed também foi testada separadamente. A diferença crítica é:

```text
Redis dedicado de teste: funcionamento comprovado
Redis Cloud com root histórico: credencial ainda ativa
```

## 19. pgvector Provisioning Requirement

O requisito operacional permanece:

```text
PRIVILEGED PROVISIONING ROLE
          ↓
CREATE EXTENSION vector
          ↓
MIGRATION ROLE
          ↓
APPLICATION ROLE
```

`vector` deve ser provisionado por role privilegiada quando necessário. A aplicação não deve receber superuser para contornar a migration. Esse item não foi alterado nesta fase e não é o blocker atual.

## 20. Remaining Risks

### CRITICAL — Redis credential active

O root histórico ainda autentica no Redis Cloud. Qualquer cópia histórica acessível a terceiros deve ser considerada comprometida até rotação/revogação.

### CRITICAL — NVIDIA credential active

O root histórico ainda autoriza request no endpoint NVIDIA. Deve ser revogado, especialmente se o provider não for necessário.

### HIGH — local ignored `.env` retains active values

O arquivo não está versionado e não foi exposto no relatório, mas mantém valores operacionais antigos. Após rotação, deve ser atualizado no ambiente autorizado sem commit.

### MEDIUM — Supabase publishable classification

O root `fp: d45184a6fc42…` aparenta ser publishable/anon por prefixo. O owner deve confirmar que não é `service_role`, senha ou JWT secret.

### LOW — Git history still contains historical occurrences

Reescrita de histórico não foi realizada. Mesmo depois da revogação, a limpeza Git pode ser avaliada separadamente; ela não substitui rotação.

## 21. Foundation Readiness

Reavaliação conservadora:

| Área | Nota |
| --- | ---: |
| Identity | 90/100 |
| Authentication | 90/100 |
| Authorization | 88/100 |
| Ownership | 90/100 |
| Sessions | 88/100 |
| Persistence | 85/100 |
| Database | 82/100 |
| Redis | 60/100 |
| Observability | 80/100 |
| Secrets | 35/100 |
| Supply Chain | 90/100 |
| Testing | 84/100 |
| Runtime Proof | 84/100 |

```text
FOUNDATION READINESS: 79/100
```

A nota não representa segurança suficiente para liberar capabilities novas: os dois secrets externos ativos mantêm o blocker crítico.

## 22. FRIDAY Readiness

```text
FRIDAY READINESS: 18/100
CLASSIFICATION: CHATBOT
AUTONOMY: LEVEL 0 — CHAT
```

Esta fase não adicionou voz, memória, visão, agentes, tools ou proatividade; portanto não há aumento artificial do índice FRIDAY.

## 23. Foundation Gate

```text
FOUNDATION GATE: FAIL
```

Motivo único bloqueante:

```text
Redis historical root: ACTIVE — provider accepted authentication
NVIDIA historical root: ACTIVE — provider accepted authenticated request
```

O critério de PASS exige que cada root plausivelmente real esteja `ROTATED`, `REVOKED` ou `INVALID WITH PROOF`. Esse critério não foi satisfeito.

## 24. Next Phase

### External owner actions required

```text
EXTERNAL OWNER ACTION

Secret ID: fp: 51f2b2be4ddf…
Provider: Redis Cloud
Credential type: connection credential/default user credential
Current classification: ACTIVE
Required action: rotate/revoke the historical credential and update only authorized runtime configuration
Required proof: old credential authentication fails; replacement credential connects; provider-side event/dashboard confirmation
Gate impact: blocking
```

```text
EXTERNAL OWNER ACTION

Secret ID: fp: 4b194fc430c6…
Provider: NVIDIA
Credential type: API key
Current classification: ACTIVE
Required action: revoke; create replacement only if the provider remains required
Required proof: old `/models` request returns unauthorized or provider audit confirms revocation; replacement succeeds if needed
Gate impact: blocking
```

```text
EXTERNAL OWNER ACTION

Secret ID: fp: d45184a6fc42…
Provider: Supabase
Credential type: publishable/anon candidate
Current classification: FALSE POSITIVE CANDIDATE
Required action: confirm it is only a public publishable/anon key, never service_role/database secret
Required proof: provider role/type confirmation
Gate impact: blocking only if privileged classification is confirmed
```

Depois das ações externas, executar novamente:

```text
provider old credential test
provider replacement test
gitleaks current source/history
backend regression
frontend regression
Foundation Gate
```

Somente então a próxima fase autorizada será `SOPHIE VOICE V1 — REAL END-TO-END VOICE`.

## Incident Closure Matrix

| Secret ID | Provider | Historical occurrences | Old status | Proof | Replacement needed | Current exposure | Closed |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| `fp: 51f2b2be4ddf…` | Redis Cloud | 2 | ACTIVE | `PING/WHOAMI` accepted | Yes, or revoke if unused | provider + ignored local env | No |
| `fp: 4b194fc430c6…` | NVIDIA | 2 | ACTIVE | `/models` = 200 | No if unused; otherwise new key | provider + ignored local env | No |
| `fp: 63edef50737c…` | Sophie | 20 | revoked as app authority | isolated production requests = 401 | No | no runtime authority | Yes, application scope |
| `fp: d45184a6fc42…` | Supabase | 4 | publishable candidate | naming evidence only | Owner classification | public env candidate | Pending |

## Security Final Matrix

| Check | Result |
| --- | --- |
| Gitleaks HEAD/source paths | PASS — 0 |
| Gitleaks history | 28 historical occurrences; incident not closed |
| Root credentials classified | PASS — 4 roots |
| Redis old credential revoked | FAIL — active |
| NVIDIA old credential revoked | FAIL — active |
| Legacy API key revoked as app authority | PASS — runtime 401 |
| Legacy auth bypass | PASS — runtime 401 |
| Log redaction | PASS |
| Semgrep | PASS |
| pip-audit | PASS |
| npm audit | PASS |
| OSV | PASS |

## Foundation Regression Matrix

| Area | Result |
| --- | --- |
| Backend tests | PASS — 101 passed, 2 skipped |
| Ruff | PASS |
| Formatter | PASS |
| Mypy | PASS |
| Frontend lint | PASS |
| Frontend typecheck | PASS |
| Frontend build | PASS |
| PostgreSQL smoke/runtime | PASS — prior real runtime evidence retained |
| Redis runtime | PASS for test runtime; provider old credential remains active |
| Auth E2E | PASS — prior real runtime evidence retained |
| Ownership E2E | PASS — prior real runtime evidence retained |
| IDOR E2E | PASS — prior real runtime evidence retained |
| Readiness | PASS — prior failure/recovery evidence retained |

## Skipped Tests

O baseline final possui `2 skipped`. Eles permanecem os skips existentes da suíte; nenhum teste foi convertido em skip nesta fase. O motivo e a condição ambiental devem continuar documentados pela suíte responsável antes de um gate de produção.

## Final Terminal Summary

```text
SOPHIE FOUNDATION 0.6
=====================

Foundation Gate: FAIL
Foundation Readiness: 79/100
FRIDAY Readiness: 18/100

Historical Secrets:
Total Gitleaks occurrences: 28
Unique secret roots: 4

Redis:
Old credential status: ACTIVE
Revocation proof: NOT AVAILABLE — provider owner required
Runtime: PING/WHOAMI SUCCESS

NVIDIA:
Old credential status: ACTIVE
Revocation proof: NOT AVAILABLE — provider owner required
Runtime: /models 200

Legacy API Key:
Status: application authority removed
Bypass test: 401 / 401

Current source findings: 0
Historical findings: 28

Backend: 101 passed, 2 skipped / Ruff PASS / Formatter PASS / Mypy PASS
Frontend: Lint PASS / Typecheck PASS / Build PASS
Security: Semgrep PASS / pip-audit PASS / npm audit PASS / OSV PASS
Runtime: PostgreSQL PASS / Redis test runtime PASS / Auth PASS / Ownership PASS / IDOR PASS / Readiness PASS

Critical blockers remaining:
- Redis historical credential still valid
- NVIDIA historical credential still valid

Next phase: blocked until external secret remediation; then SOPHIE VOICE V1
```
