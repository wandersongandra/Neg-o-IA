# Redis — configuração segura

Este documento não armazena credenciais. A URL deve ser fornecida somente por
`NEGAO_REDIS_URL`/`SOPHIE_REDIS_URL` em um secret manager ou `.env` ignorado.

## Teste local

```bash
python -c "import os, redis; url=os.environ['NEGAO_REDIS_URL']; print(redis.from_url(url).ping())"
```

Para o backend, a ausência ou indisponibilidade do Redis deve aparecer como
`readyz=503`; não há fallback silencioso para confirmar persistência.

## Operação

```bash
redis-cli -u "$NEGAO_REDIS_URL" ping
```

Nunca copie uma URL com senha para documentação, terminal compartilhado,
issue, commit ou log. Credenciais previamente expostas exigem revogação e
rotação pelo proprietário externo do serviço.

## Variáveis esperadas

```env
NEGAO_REDIS_URL=redis://usuario:SENHA_REDACTED@host:6379/0
```
