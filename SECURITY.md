# Política de Segurança

A Sophie integra autenticação, memória, voz, visão, ferramentas governadas, automações, PostgreSQL e Redis. Mudanças nessas áreas são tratadas como mudanças sensíveis e devem passar pelos gates de segurança do CI antes de promoção.

## Relato de vulnerabilidades

Não publique em issues públicas credenciais, tokens, dados pessoais, prompts privados, detalhes de exploração, dumps, cookies ou vulnerabilidades ainda não corrigidas.

Ao identificar uma possível falha, utilize um canal privado de contato com o mantenedor indicado no perfil do GitHub e informe, quando possível:

- componente afetado;
- descrição objetiva do problema;
- passos mínimos para reprodução;
- impacto potencial;
- evidências sem dados sensíveis;
- sugestão de mitigação ou correção.

## Identidade e sessões

- Senhas são derivadas com Argon2id.
- Tokens de sessão são opacos e somente o hash SHA-256 do token é persistido.
- Em produção, o navegador usa cookie `__Host-sophie_session`, com `Secure`, `HttpOnly`, `Path=/` e `SameSite=Strict`.
- Sessões possuem expiração absoluta e expiração por inatividade.
- O número de sessões simultâneas por usuário é limitado; sessões mais antigas são revogadas ao exceder o limite.
- Requisições mutáveis autenticadas por cookie validam a origem em produção.
- O BFF também valida Fetch Metadata (`Sec-Fetch-Site`/`Sec-Fetch-Dest`) em chamadas sensíveis.
- O usuário pode listar sessões ativas, revogar sessões específicas e encerrar todas as outras sessões.
- Hosts aceitos pelo FastAPI são allowlisted; em produção não é permitido wildcard.
- Login aplica rate limit por IP e por conta. Em produção, indisponibilidade do Redis não degrada para um limiter local mais permissivo: a proteção falha fechada.

## WebSockets

Tickets WebSocket são:

- aleatórios e armazenados no Redis apenas pelo hash;
- de uso único;
- de curta duração;
- vinculados à finalidade (`conversation` ou `voice`);
- vinculados à sessão de conversa quando aplicável;
- vinculados à sessão de autenticação que os originou;
- rejeitados se a sessão de autenticação estiver revogada, expirada ou inativa;
- sujeitos a validação de `Origin` e rate limiting em produção.

A chave de serviço via query string permanece permitida apenas fora de produção para compatibilidade de testes e scripts locais.

## Auditoria tamper-evident

Novos registros em `events.audit_events` recebem uma assinatura HMAC-SHA256 sobre os campos imutáveis do evento e seu payload canônico.

Eventos anteriores à migration `0006_audit_integrity` permanecem válidos como histórico legado, mas aparecem como `unsigned_legacy`.

A rota administrativa `/database/audit/integrity` resume eventos verificados, inválidos e legados. Ela permanece atrás do escopo de serviço `database:admin`.

### Rotação da chave de auditoria

É recomendado usar uma chave dedicada em produção:

- `SOPHIE_AUDIT_INTEGRITY_KEY` (ou alias legado `NEGAO_AUDIT_INTEGRITY_KEY`);
- durante uma rotação, mantenha a chave anterior em `SOPHIE_AUDIT_INTEGRITY_PREVIOUS_KEYS`, separada por vírgula;
- após o período de retenção/transição desejado, remova a chave antiga.

Quando uma chave dedicada não é definida, a chave de aplicação é usada como fallback compatível.

## Segredos e integrações

A chave bootstrap de serviço fica desabilitada por padrão em produção. Para provisionamento inicial, habilite `SOPHIE_SERVICE_BOOTSTRAP_ENABLED=true` (ou alias `NEGAO_*`) apenas temporariamente, crie uma chave persistida e rotacionável e desabilite o bootstrap novamente.

Credenciais de APIs, chaves de modelo, tokens, arquivos `.env`, URLs privadas de banco, cookies, chaves de sessão e dados de produção não devem ser versionados.

Para segredos suportados, produção pode usar `SOPHIE_<NOME>_FILE`/ `NEGAO_<NOME>_FILE` com caminho absoluto. O loader rejeita arquivo ausente, vazio, inválido, grande demais e configuração ambígua com valor direto + `*_FILE`. Isso permite montar Docker/Kubernetes secrets sem colocar o conteúdo do segredo no ambiente do processo de origem.

Variáveis de exemplo devem conter apenas placeholders fictícios.

IA externa e Vision permanecem fail-closed: o envio de dados a provedores externos só ocorre quando a integração externa está explicitamente habilitada e as credenciais/modelos necessários estão configurados.

Em produção, `SOPHIE_NVIDIA_BASE_URL`/ `NEGAO_NVIDIA_BASE_URL` precisa usar HTTPS na porta 443, sem credenciais, query string ou fragmento, e o hostname deve estar explicitamente presente em `SOPHIE_EXTERNAL_AI_ALLOWED_HOSTS`/ `NEGAO_EXTERNAL_AI_ALLOWED_HOSTS`. Isso reduz risco de SSRF/exfiltração por alteração de endpoint do provedor.

## Rede e containers

O Compose de produção separa a rede de dados da rede da aplicação:

- PostgreSQL e Redis ficam somente na rede interna `data`;
- apenas o backend participa da rede `data`;
- frontend e Nginx não possuem caminho direto para PostgreSQL ou Redis;
- containers de aplicação utilizam `no-new-privileges`, limites de processos e capabilities reduzidas onde compatível;
- backend, frontend e Nginx usam filesystem raiz somente leitura em produção;
- diretórios graváveis são limitados a `tmpfs` explícitos e com `nosuid`, `nodev` e `noexec` quando compatível.

O Nginx aplica TLS 1.2/1.3, suites TLS 1.2 modernas, HSTS, limites de conexão/requisição, timeouts contra conexões lentas, proteção de dotfiles e headers de isolamento do navegador.

## Dependências e supply chain

O CI inclui:

- Ruff lint e formatter;
- mypy strict;
- pytest;
- migrations em PostgreSQL limpo;
- Semgrep com versão fixa;
- pip-audit com versão fixa;
- npm audit;
- Gitleaks em histórico completo;
- OSV dependency review em pull requests, independente do Dependency Graph do GitHub;
- CodeQL para Python e JavaScript/TypeScript;
- build/typecheck do frontend;
- validação do Nginx;
- validação da topologia Docker Compose de produção;
- geração de SBOM CycloneDX 1.6 reproduzível para backend Python e frontend npm;
- validação estrutural dos SBOMs e publicação dos artefatos com `SHA256SUMS`.

Actions externas do GitHub devem permanecer pinadas por commit SHA. Checkouts do CI não persistem credenciais Git após o checkout.

## Divulgação

Detalhes técnicos de vulnerabilidades devem permanecer privados até que exista correção ou mitigação adequada.
