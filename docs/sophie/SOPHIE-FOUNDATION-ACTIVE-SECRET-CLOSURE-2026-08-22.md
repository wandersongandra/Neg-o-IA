# SOPHIE FOUNDATION 0.7 — ACTIVE SECRET CLOSURE

Data da execução: 2026-08-22  
Escopo: revogação/rotação de credenciais ativas, prova de morte e gate final.  
Regra: nenhum valor de segredo, URL completa, cookie ou token é reproduzido.

## 1. Executive Summary

A Foundation 0.7 não conseguiu encerrar os dois incidentes ativos porque o
ambiente contém somente credenciais de runtime, sem autorização administrativa
para Redis Cloud ou NVIDIA.

As provas não destrutivas foram repetidas:

```text
Redis histórico: PING SUCCESS
Redis ACL admin category: 0
NVIDIA histórico: GET /models -> 200
Legacy API key: 401 / 401
```

Conclusão: Redis e NVIDIA continuam aceitando as credenciais históricas. Não
foi executado bypass, alteração destrutiva, delete de recurso, criação de nova
key ou tentativa de adivinhar API administrativa.

O código permanece limpo nos caminhos de source e o build frontend não contém
credenciais Redis/NVIDIA/Supabase. O Gitleaks encontrou 9 matches genéricos em
metadados server-only gerados pelo Next (`previewMode*`/RSC encryption keys),
em `.next` ignorado e não versionado; eles não são roots históricos nem
credenciais de provider.

```text
CODE REMEDIATION: COMPLETE FOR LEGACY API AUTHORITY
PROVIDER INCIDENT CLOSURE: BLOCKED BY EXTERNAL OWNER
FOUNDATION GATE: FAIL
```

## 2. Starting State

| Item | Estado inicial |
| --- | --- |
| Foundation Readiness | 79/100 |
| FRIDAY Readiness | 18/100 |
| Classification | CHATBOT |
| Autonomy | LEVEL 0 — CHAT |
| Foundation Gate | FAIL |
| Historical Gitleaks | 28 occurrences / 4 root groups |
| Redis historical root | ACTIVE |
| NVIDIA historical root | ACTIVE |
| Legacy API key | REMEDIATED as application authority |

## 3. Scope

Executado:

- leitura dos cinco relatórios anteriores;
- inspeção de worktree e branch;
- reconstrução dos quatro roots;
- verificação do provider Redis e das permissões disponíveis;
- verificação do provider NVIDIA com request não destrutivo;
- repetição do legacy bypass em runtime isolado;
- Gitleaks current source/build/history;
- regressão backend, frontend e security supply-chain;
- documentação de external owner actions.

Não executado por estar fora de escopo ou sem autorização:

- Voice, Memory, Agents, Tools, Vision, Desktop, Calendar, Email e Proactivity;
- delete de Redis, alteração de ACL, revogação sem painel oficial;
- criação de replacement key sem necessidade/autorização;
- commit, push, deploy, release ou reescrita de histórico Git.

## 4. Root Secret Inventory

Fingerprints abaixo são SHA-256 truncados calculados localmente. Os valores
originais não foram impressos.

| Secret Root | Provider | Type | Historical Occurrences | Previous Status | Current HEAD | Runtime Status |
| --- | --- | --- | ---: | --- | --- | --- |
| `fp: 51f2b2be4ddf…` | Redis Cloud | credencial de conexão/default user | 2 | ACTIVE | 0 em source | **ACTIVE** |
| `fp: 4b194fc430c6…` | NVIDIA | API key | 2 | ACTIVE | 0 em source | **ACTIVE** |
| `fp: 63edef50737c…` | Sophie | API key global legada | 20 | REMEDIATED | 0 em source | **DENIED / REVOKED AS APP AUTHORITY** |
| `fp: d45184a6fc42…` | Supabase | publishable/anon candidate | 4 | FALSE POSITIVE CANDIDATE | 0 em source | **OWNER CONFIRMATION PENDING** |

### Root 4 classification

O quarto root coincide com `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. O prefixo
`NEXT_PUBLIC_` e o nome publishable indicam uma chave pública/anon, não uma
`service_role`, senha ou JWT secret. Não há evidência de privilégio elevado no
source atual. A classificação é `FALSE POSITIVE CANDIDATE`, confiança MEDIUM,
com confirmação do owner ainda pendente.

Se o owner identificar esse valor como `service_role`, database password,
JWT secret ou token privado, ele deverá ser reclassificado como blocker e
rotacionado.

## 5. Redis Incident

### Provider e necessidade

O root Redis corresponde ao Redis Cloud configurado em `NEGAO_REDIS_URL`. A
SOPHIE ainda utiliza Redis para histórico operacional de conversas, readiness,
eventos, rate limiting e estado de WebSocket/tickets. Portanto, Redis é
necessário para o runtime atual; não é seguro simplesmente apagar a instância.

### Credential type e ambiente

É uma credencial de conexão/default user de uma instância Redis Cloud. Host,
porta, URL e password foram mantidos redigidos.

## 6. Redis Rotation / Revocation

Não há credencial de administração, token de account, painel autenticado ou
permissão ACL administrativa disponível neste ambiente.

Foi deliberadamente não executado:

- `ACL SETUSER`;
- `CONFIG SET`;
- troca de password;
- delete de database/instância;
- qualquer alteração destrutiva no provider.

```text
EXTERNAL OWNER ACTION REQUIRED
Provider: Redis Cloud
Action: rotate/revoke the historical default-user credential in the official provider control plane
Replacement: required if Sophie remains dependent on this instance
Gate impact: BLOCKING
```

## 7. Redis Old Credential Retest

Probe: `backend/tests/tests_integration/foundation_provider_secret_probe.py`.

```text
REDIS_ENV_CREDENTIAL_PING=SUCCESS
REDIS_ENV_CREDENTIAL_WHOAMI=b'default'
REDIS_ENV_ACL_ADMIN_CATEGORY=0
```

Resultado: a credencial antiga continua funcional e não pode ser considerada
morta. A prova de revogação exigida (`AUTH FAILED`) não existe.

## 8. NVIDIA Incident

O root NVIDIA corresponde a `NEGAO_NVIDIA_API_KEY` e ao endpoint configurado
em `NEGAO_NVIDIA_BASE_URL`.

O provider não é obrigatório para o boot da Foundation: o Brain possui modo
local-mock quando a key está ausente. Porém, o runtime atual suporta Brain e
STT NVIDIA quando configurado. A decisão de manter o provider é do owner; esta
fase não cria replacement sem necessidade explícita.

## 9. NVIDIA Revocation

Não foi encontrada credencial de account/project, dashboard administrativo ou
API de gerenciamento autorizada neste ambiente. A API key de inferência não
foi usada para tentar auto-revogação.

```text
EXTERNAL OWNER ACTION REQUIRED
Provider: NVIDIA
Action: revoke the historical API key in the official provider control plane
Replacement: only if NVIDIA remains required after revocation
Gate impact: BLOCKING
```

## 10. NVIDIA Old Credential Retest

Probe: `backend/tests/tests_integration/foundation_provider_secret_probe.py`.

```text
NVIDIA_ENV_CREDENTIAL_MODELS_STATUS=200
```

Resultado: a key antiga continua válida. O resultado esperado para encerramento
seria `401`, `403` ou `INVALID API KEY`; portanto o blocker permanece.

## 11. Legacy API Key Verification

Probe: `backend/tests/tests_integration/foundation_legacy_key_probe.ps1` em
processo isolado com `NEGAO_ENV=production`, PostgreSQL e Redis dedicados.

```text
LEGACY_KEY_SECURITY_STATUS=401
LEGACY_KEY_SERVICE_STATUS=401
```

A antiga `NEGAO_API_KEY` não é mais carregada como autoridade, não autentica
usuário e não autentica serviço. Não foi recriada nem substituída.

## 12. Root Secret 4 Analysis

```text
Secret ID: fp: d45184a6fc42…
Provider: Supabase
Classification: FALSE POSITIVE CANDIDATE / publishable-anon
Evidence: NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY naming; no service_role evidence
Current source exposure: 0
Final status: PENDING OWNER CONFIRMATION
Confidence: MEDIUM
```

O status não é `ACTIVE` comprovado. Ainda assim, confirmação do owner é
necessária para evitar classificar incorretamente uma credencial privilegiada.

## 13. Current HEAD Secret Scan

Probe: `backend/tests/tests_integration/foundation_gitleaks_probe.ps1`.

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

`.env` não é tracked e `.next` não é tracked. Nenhuma credencial privada de
backend foi encontrada no source versionado/current-source auditado.

### Frontend build artifact

```text
BUILD_ARTIFACT_FINDINGS=9
```

Os 9 matches estão exclusivamente em:

- `.next/cache/.previewinfo`;
- `.next/cache/.rscinfo`;
- `.next/prerender-manifest.json`;
- `.next/server/server-reference-manifest.json`;
- cópias equivalentes em `.next/standalone`.

As propriedades detectadas são `previewModeEncryptionKey`,
`previewModeSigningKey`, `previewModeId` e RSC `encryptionKey`: chaves
efêmeras geradas pelo Next para metadados server-only. Não são Redis,
NVIDIA, Supabase, session cookies ou secrets do backend; o diretório é
ignorado por `.gitignore` e `git ls-files frontend/.next` retorna zero.

Isso foi registrado, não allowlisted. O build não expõe os roots históricos em
bundle público.

Busca sanitizada no `.next` por padrões `nvapi-`, `redis://`, `rediss://`,
`NEGAO_NVIDIA_API_KEY`, `NEGAO_REDIS_URL` e `service_role` retornou zero
arquivos.

## 14. Historical Gitleaks Results

```text
HISTORY_FINDINGS=28
UNIQUE_ROOTS=4
```

O histórico não foi reescrito. As ocorrências só poderão ser marcadas como
`HISTORICAL EXPOSURE — REMEDIATED` após prova externa de morte dos roots Redis
e NVIDIA e confirmação do quarto root.

## 15. Secret Storage Validation

As credenciais de runtime são carregadas por variáveis de ambiente. O `.env`
local não é tracked e não foi alterado. Nenhum novo valor foi escrito em:

- source Python/TypeScript;
- frontend bundle público;
- `.env.example`;
- relatório;
- testes ou argumentos de processo.

O `git ls-files .env` retorna zero e o `.env` é ignorado por `.gitignore`.
Essa configuração é aceitável como etapa local, mas a rotação real ainda deve
ser aplicada no secret store/ambiente autorizado do owner.

## 16. Log / Error Redaction

Os probes imprimiram somente status, tipo de provider, fingerprint truncado e
metadados de arquivo. Não foram impressos Redis URL, password, NVIDIA key,
session cookie ou database credential.

O redactor estruturado existente cobre `authorization`, `cookie`, `password`,
`secret`, `token`, `api_key`, `access_token` e `refresh_token`. Semgrep não
encontrou regra de leakage na aplicação.

Resultado observado: PASS. Isso não substitui a revogação provider-side.

## 17. Backend Regression

```text
pytest: 101 passed, 2 skipped, 1 warning
ruff check: PASS
ruff format --check: PASS — 145 files already formatted
mypy: PASS — 119 source files
```

O warning é a depreciação de `httpx` no `starlette.testclient`; não é blocker
de secrets ou autenticação.

## 18. Frontend Regression

```text
npm run lint: PASS
npm run typecheck: PASS
npm run build: PASS
```

O build foi executado sequencialmente para evitar a pressão de memória que
havia produzido `spawn UNKNOWN` quando scanners eram executados em paralelo.

## 19. Security Regression

| Scanner | Resultado |
| --- | --- |
| Semgrep `p/python` | PASS — 0 findings, 119 arquivos, 151 regras |
| pip-audit | PASS — no known vulnerabilities |
| npm audit `--omit=dev --audit-level=high` | PASS — 0 vulnerabilities |
| OSV scanner | PASS — 680 packages, no issues |
| Gitleaks current source | PASS — 0 |
| Gitleaks frontend build metadata | 9 generic matches, framework server-only metadata; não versionado |
| Gitleaks history | 28 ocorrências; incidente ainda aberto |

## 20. Redis Runtime Validation

O Redis dedicado de teste foi reiniciado apenas para a prova isolada do
bypass, usado pelo runtime e desligado após o teste. O Redis compartilhado
existente não foi tocado.

As provas reais anteriores permanecem válidas:

```text
Redis down -> live 200
Redis down -> ready 503
Redis down -> persistence 503
Redis restored -> ready 200
Redis restored -> persistence 200
```

A conexão provider-backed atual também funciona, mas isso é precisamente a
evidência de que o root histórico ainda está ativo:

```text
old Redis credential -> PING SUCCESS
old Redis credential -> ACL WHOAMI default
```

## 21. Authentication Regression

Suíte backend e runtime anterior continuam verdes para:

- login;
- sessão server-side;
- cookie HttpOnly;
- expiração;
- logout;
- revogação;
- replay negado;
- duas sessões do mesmo usuário;
- legacy key sem sessão negada.

O probe 0.7 repetiu a negação da chave legada em produção isolada com `401`.

## 22. Ownership / IDOR Regression

As provas runtime reais da Foundation anterior permanecem:

```text
USER A resource -> USER A allowed
USER B reads A -> denied
USER B updates A -> denied
USER B deletes A -> denied
USER B reads A messages -> denied
USER B sends user_id=A -> ignored/denied
```

Nenhuma mudança desta fase alterou o modelo de ownership.

## 23. Readiness

O comportamento validado anteriormente permanece:

```text
healthy critical dependencies -> /health/live 200, /health/ready 200
critical dependency down -> /health/live 200, /health/ready 503
dependency restored -> /health/ready 200
```

Para a NVIDIA, a sua indisponibilidade não deve derrubar liveness; chamadas
específicas devem falhar com erro de provider. Para Redis, que é dependência
crítica do runtime atual, credencial inválida deve levar readiness a `503`.

## 24. pgvector Operational Requirement

O procedimento operacional permanece:

```text
PRIVILEGED PROVISIONING ROLE
        ↓
CREATE EXTENSION vector
        ↓
MIGRATION ROLE
        ↓
RUNTIME ROLE
```

A role de runtime não deve receber superuser. O provisionamento privilegiado
de `vector` e `pgcrypto` deve ocorrer antes das migrations em ambientes
least-privilege. Este requisito está documentado e não é o blocker 0.7.

## 25. Remaining Risks

### CRITICAL — Redis old credential still works

O owner Redis Cloud deve rotacionar/revogar o default-user credential e provar
que o valor antigo falha. Como Redis ainda é necessário, deve validar a nova
credencial no runtime antes de fechar o incidente.

### CRITICAL — NVIDIA old credential still works

O owner NVIDIA deve revogar a API key. Não criar replacement se NVIDIA não for
mais necessária; se continuar necessária para Brain/Voice, validar uma nova
key sem registrá-la.

### MEDIUM — Supabase root classification pending

Confirmar que o quarto root é somente publishable/anon. Se for privilegiado,
rotacionar e adicionar nova prova de morte.

### INFO — Next generated metadata

O build contém chaves internas efêmeras em artefatos server-only ignorados.
Elas não são credenciais de provider nem aparecem no HEAD; monitorar o destino
de deploy para garantir que `.next` server-only nunca seja servido como asset
público indiscriminado.

## 26. Foundation Readiness

Reavaliação conservadora:

| Área | Nota |
| --- | ---: |
| Identity | 90/100 |
| Authentication | 90/100 |
| Authorization | 88/100 |
| Ownership | 90/100 |
| Sessions | 88/100 |
| Persistence | 85/100 |
| PostgreSQL | 82/100 |
| Redis | 55/100 |
| Secrets | 25/100 |
| Observability | 80/100 |
| Supply Chain | 90/100 |
| Testing | 84/100 |
| Runtime Proof | 84/100 |

```text
FOUNDATION READINESS: 76/100
```

A nota caiu conservadoramente porque a etapa 0.7 repetiu prova positiva de
validade dos dois roots e ainda não possui evidência de revogação. Isso não é
uma penalidade por ausência de feature; é o risco de credencial ativa.

## 27. FRIDAY Readiness

```text
FRIDAY READINESS: 18/100
CLASSIFICATION: CHATBOT
AUTONOMY: LEVEL 0 — CHAT
```

Nenhuma capability FRIDAY foi implementada nesta fase.

## 28. Foundation Gate

```text
FOUNDATION GATE: FAIL
```

Fail automático por:

```text
Redis old credential still works
NVIDIA old credential still works
```

O root Supabase publishable é candidato a falso positivo, mas permanece com
confirmação pendente. A legacy API key está encerrada como autoridade da
aplicação.

## 29. Next Phase

### External owner action — Redis

```text
SECRET ID: fp: 51f2b2be4ddf…
PROVIDER: Redis Cloud
CURRENT STATUS: ACTIVE
ACTION: rotate/revoke in official provider control plane
OLD RETEST REQUIRED: AUTH/PING must fail
REPLACEMENT: required if Redis remains in use
NEW RETEST REQUIRED: connect/PING and Sophie readiness/persistence pass
GATE IMPACT: BLOCKING
```

### External owner action — NVIDIA

```text
SECRET ID: fp: 4b194fc430c6…
PROVIDER: NVIDIA
CURRENT STATUS: ACTIVE
ACTION: revoke in official provider control plane
OLD RETEST REQUIRED: /models must return 401/403/invalid key
REPLACEMENT: not required if provider is retired; otherwise create securely
NEW RETEST REQUIRED: /models 200 and application provider smoke
GATE IMPACT: BLOCKING
```

### External owner action — Root 4

```text
SECRET ID: fp: d45184a6fc42…
PROVIDER: Supabase
CURRENT STATUS: publishable/anon candidate
ACTION: confirm key type is public-only and not service_role/password/JWT secret
PROOF: provider project key classification
GATE IMPACT: blocking if privileged; otherwise false-positive closure
```

Após essas ações, reexecutar Gitleaks current/history, as probes antigas,
runtime Redis/NVIDIA, auth/ownership/IDOR, readiness e toda a regressão.

Somente se todas as credenciais antigas falharem e todos os gates permanecerem
verdes será liberada a próxima fase:

```text
SOPHIE VOICE V1 — REAL END-TO-END VOICE
```

## Credential Matrix

| Secret Root | Provider | Historical Occurrences | Previous Status | Action | Old Credential Retest | Replacement | Final Status |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| `fp: 51f2b2be4ddf…` | Redis Cloud | 2 | ACTIVE | external rotate/revoke required | PING SUCCESS — FAIL | required if retained | ACTIVE / OPEN |
| `fp: 4b194fc430c6…` | NVIDIA | 2 | ACTIVE | external revoke required | `/models` 200 — FAIL | only if retained | ACTIVE / OPEN |
| `fp: 63edef50737c…` | Sophie | 20 | REMEDIATED | no replacement | `401 / 401` — PASS | not needed | CLOSED AS APP AUTHORITY |
| `fp: d45184a6fc42…` | Supabase | 4 | candidate false positive | owner classification | not applicable until classified | only if privileged | PENDING |

## Final Security Matrix

| Control | Result |
| --- | --- |
| Gitleaks HEAD/source | PASS — 0 |
| Gitleaks history | 28 historical occurrences; not closed |
| Redis old credential invalid | FAIL — still works |
| Redis replacement valid | NOT TESTED — no authorized rotation |
| NVIDIA old credential invalid | FAIL — still works |
| NVIDIA replacement valid / not required | NOT TESTED — no rotation |
| Legacy API key bypass denied | PASS — 401/401 |
| Root 4 closed | PENDING owner classification |
| Log redaction | PASS |
| Semgrep | PASS |
| pip-audit | PASS |
| npm audit | PASS |
| OSV | PASS |

## Regression Matrix

| Area | Result |
| --- | --- |
| Backend tests | PASS — 101 passed, 2 skipped |
| Ruff | PASS |
| Formatter | PASS |
| Mypy | PASS |
| Frontend lint | PASS |
| Frontend typecheck | PASS |
| Frontend build | PASS |
| Authentication | PASS |
| Session revocation | PASS |
| Ownership | PASS |
| IDOR | PASS |
| Redis runtime | PASS for test Redis; provider old credential active |
| PostgreSQL smoke | PASS — prior real runtime evidence retained |
| Readiness | PASS — prior failure/recovery evidence retained |

## Terminal Summary

```text
SOPHIE FOUNDATION 0.7
=====================

Foundation Gate: FAIL
Foundation Readiness: 76/100
FRIDAY Readiness: 18/100

Historical Gitleaks occurrences: 28
Unique root secrets: 4

Redis:
Previous status: ACTIVE
Action: EXTERNAL OWNER ACTION REQUIRED
Old credential retest: PING SUCCESS / ACL admin category 0
Replacement: NOT CREATED — no authorized rotation
Final status: ACTIVE / BLOCKING

NVIDIA:
Previous status: ACTIVE
Action: EXTERNAL OWNER ACTION REQUIRED
Old credential retest: /models 200
Replacement: NOT CREATED — no authorized rotation
Final status: ACTIVE / BLOCKING

Legacy API Key:
Bypass: 401 / 401
Final status: REMEDIATED

Root Secret 4:
Classification: Supabase publishable/anon candidate
Final status: PENDING OWNER CONFIRMATION

Current HEAD/source secrets: 0
Frontend generated server-only metadata matches: 9

Backend:
Tests: 101 passed, 2 skipped
Ruff: PASS
Formatter: PASS
Mypy: PASS

Frontend:
Lint: PASS
Typecheck: PASS
Build: PASS

Security:
Semgrep: PASS
pip-audit: PASS
npm audit: PASS
OSV: PASS
Gitleaks HEAD/source: PASS — 0
Gitleaks History: 28 historical occurrences

Runtime:
Redis test runtime: PASS
PostgreSQL: PASS — prior real runtime evidence retained
Authentication: PASS
Revocation: PASS for sessions; provider secrets OPEN
Ownership: PASS
IDOR: PASS
Readiness: PASS — prior failure/recovery evidence retained

Remaining blockers:
- Redis historical credential still authenticates
- NVIDIA historical credential still authenticates
- Supabase root type requires owner confirmation

Next Phase:
Blocked until provider secret closure; then SOPHIE VOICE V1
```

## Post-Claim Rotation Retest

Após a informação do owner de que as credenciais haviam sido rotacionadas,
foi executado um probe adicional que recupera os valores históricos somente em
memória, sem imprimir ou persistir os valores, e os testa contra os providers.

Resultado:

```text
REDIS_OLD_CREDENTIAL_EQUALS_CURRENT=1
OLD_REDIS_CREDENTIAL=STILL_ACCEPTED
NVIDIA_OLD_CREDENTIAL_EQUALS_CURRENT=1
OLD_NVIDIA_CREDENTIAL_MODELS_STATUS=200
```

Essa evidência significa que, neste checkout, o `.env` ainda contém exatamente
os valores históricos e os dois providers continuam aceitando-os. A rotação
pode ter sido feita em outra conta/instância, ou os valores novos ainda não
foram carregados neste ambiente; não há base técnica para encerrar o incidente.

```text
POST-CLAIM ROTATION PROOF: FAIL
REDIS OLD CREDENTIAL DEAD: NO
NVIDIA OLD CREDENTIAL DEAD: NO
FOUNDATION GATE: FAIL
```

Para reabrir a validação, o owner deve atualizar o ambiente ignorado com os
valores novos (sem enviá-los no chat), reiniciar/recarregar o runtime e repetir
o probe. O resultado mínimo exigido é `OLD_REDIS_CREDENTIAL=REJECTED`, status
NVIDIA `401`/`403`, e os probes das credenciais atuais com sucesso.

## Owner Decision — Revocation Declined

O owner informou que não deseja revogar as credenciais históricas neste
momento. Essa decisão foi respeitada: nenhum provider foi alterado, nenhuma
credencial foi revogada e nenhum segredo foi exposto.

A decisão não satisfaz os critérios objetivos do Foundation Gate. As
credenciais antigas continuam utilizáveis e o risco permanece aberto:

```text
OWNER REVOCATION DECISION: DECLINED
REDIS HISTORICAL CREDENTIAL: ACTIVE
NVIDIA HISTORICAL CREDENTIAL: ACTIVE
SECURITY RISK ACCEPTANCE: EXPLICITLY ACCEPTED BY OWNER IN CHAT
FOUNDATION GATE: FAIL
```

O owner autorizou a continuidade assumindo expressamente o risco. Essa
autorização libera a progressão operacional para a próxima etapa, mas não
altera o veredito técnico do gate: as credenciais históricas continuam
utilizáveis e a Foundation permanece `FAIL`.
