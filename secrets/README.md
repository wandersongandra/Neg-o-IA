# Runtime secrets

Este diretório contém apenas a documentação do mecanismo de segredos. Os
arquivos reais são ignorados pelo Git e devem existir somente no host de
produção, com permissões restritas.

Arquivos esperados pelo `infra/docker/compose/prod.yml`:

- `postgres_password`: senha do usuário PostgreSQL.
- `redis_password`: senha do Redis.
- `database_url`: URL SQLAlchemy completa do backend, incluindo a senha.
- `redis_url`: URL Redis completa do backend, incluindo a senha.
- `app_secret_key`: segredo principal da Sophie, aleatório e independente.
- `internal_proxy_key`: segredo compartilhado apenas entre Next BFF e FastAPI.

Exemplo de preparação no host:

```bash
install -d -m 700 secrets
umask 077
openssl rand -hex 32 > secrets/app_secret_key
openssl rand -hex 32 > secrets/internal_proxy_key
```

As senhas/URLs de banco e Redis devem ser geradas pelo processo de
provisionamento autorizado. Não copie valores de exemplo para produção.

Antes do deploy, valide que os arquivos pertencem ao usuário administrativo
correto e não são legíveis por outros usuários do host.
