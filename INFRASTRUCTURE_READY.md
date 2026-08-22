# SOPHIE — infraestrutura

Este documento é um checklist operacional sanitizado. Nenhuma credencial,
token, senha ou URL privada deve ser versionada aqui.

## Dependências

| Dependência | Configuração | Prova necessária |
| --- | --- | --- |
| PostgreSQL | `NEGAO_DATABASE_URL`/`SOPHIE_DATABASE_URL` | `health/ready` 200 e migrations aplicadas |
| Redis | `NEGAO_REDIS_URL`/`SOPHIE_REDIS_URL` | `health/ready` 200 e teste de persistência |
| NVIDIA | `NEGAO_NVIDIA_API_KEY`/`SOPHIE_NVIDIA_API_KEY` | chamada autorizada, sem registrar a chave |
| Frontend | `NEGAO_API_URL`/`SOPHIE_API_URL` | login BFF e build |

## Inicialização local

1. Copie `.env.example` para um arquivo ignorado.
2. Preencha os secrets usando um gerenciador local/ambiente autorizado.
3. Execute as migrations do backend.
4. Inicie a API e valide `/health/live` e `/health/ready`.
5. Crie um usuário em ambiente de desenvolvimento e valide login, sessão e
   ownership com dois usuários.

## Critério operacional

`/health/live` responde somente se o processo está vivo. `/health/ready`
responde `200` apenas quando PostgreSQL, Redis e as tabelas de identidade
necessárias estão disponíveis; caso contrário responde `503`.

## Segurança

Segredos encontrados em documentação ou histórico devem ser tratados como
comprometidos: remover do HEAD não substitui rotação no provider externo.
