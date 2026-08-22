# SOPHIE Foundation — arquitetura as-built

Data da verificação: 2026-08-22  
Escopo: identidade, autenticação, autorização, ownership, persistência,
readiness, observabilidade e gates de segurança. Nenhuma capacidade FRIDAY
foi adicionada.

## Fluxo atual

```text
Browser / BFF Next.js
        │ cookie HttpOnly sophie_session ou Bearer
        ▼
FastAPI
        │ require_authenticated_user
        ├── PostgreSQL identity.users
        ├── PostgreSQL identity.devices
        └── PostgreSQL identity.sessions (somente hash do token)
                │
                ▼
        AuthResult(user_id, session_id, device_id)
                │
                ▼
        Router + ownership por user_id
                │
                ├── Redis conversation:sessions:user:{user_id}
                ├── Redis conv:{session_id}:meta/messages
                ├── Brain / provider NVIDIA (quando configurado)
                └── Voice batch / WebSocket ticket curto
```

API key não representa mais usuário final. A compatibilidade `X-API-Key` só
existe fora de produção e é marcada como `service_api_key`; em produção o
fluxo de usuário exige sessão persistida.

## Identidade e ownership

- Usuário: `identity.users`, com `password_hash` scrypt nullable para permitir
  migração de usuários legados sem inventar credenciais.
- Dispositivo: `identity.devices`, ligado ao usuário e atualizado no login.
- Sessão: `identity.sessions`, token opaco, hash SHA-256 persistido, expiração,
  `last_seen_at` e revogação.
- Conversa: metadado Redis contém `user_id`; leitura, alteração, reset,
  exclusão e listagem usam `get_owned_session`/índice por usuário.
- WebSocket: ticket de uso único, TTL de 60 segundos, purpose explícito,
  origin validada em produção e verificação de ownership para voice.

## Persistência e falhas

O histórico de conversa permanece em Redis, com TTL de 24 horas. Escritas de
criação, append, reset e exclusão usam pipeline transacional quando envolvem
mais de uma chave. Erro de Redis gera `503`/erro explícito; não há fallback
RAM que responda como se tivesse salvado.

Isso não é memória longa: é histórico operacional de curto prazo com TTL.

## Health

- `/health/live` e `/healthz`: processo vivo, sem depender de DB/Redis.
- `/health/ready` e `/readyz`: `200` somente com PostgreSQL, Redis e tabelas
  `identity.users`/`identity.sessions`; caso contrário `503`.
- `/events/health`: estado do Redis do barramento.

## Observabilidade

Cada request recebe `request_id`, `trace_id` e `correlation_id`, propagados em
headers de resposta e contexto estruturado. Logs não devem transportar
Authorization, cookie, password, API key ou tokens; o processador central
redige esses campos.

## Migrations e deploy

`0001_initial_schema` + `0002_identity_sessions` formam uma única cadeia até
`head`. O Dockerfile agora copia `migrations/`; deploys abortam se a migration
falhar e o healthcheck operacional usa readiness exposto pelo nginx.

A execução contra PostgreSQL real não foi feita neste ambiente: Docker,
PostgreSQL e Redis locais não estavam disponíveis.
