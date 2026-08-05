# NEGÃO AI

> **Uma única inteligência. Uma única memória. Uma evolução contínua.**

**NEGÃO AI** é um **Sistema Operacional de Inteligência Artificial (AI Operating System)** desenvolvido para ser um assistente pessoal permanente, capaz de aprender continuamente, construir memória de longo prazo, organizar conhecimento, automatizar tarefas e evoluir ao longo dos anos.

Diferente das arquiteturas tradicionais baseadas em múltiplos agentes independentes, o **NEGÃO AI** foi projetado como **uma única inteligência**.

Todos os componentes internos representam partes do mesmo cérebro.

Não existem personalidades diferentes.

Não existem agentes concorrentes.

Existe apenas **o NEGÃO**.

---

# Filosofia

O NEGÃO foi inspirado em uma ideia simples:

> **Uma inteligência deveria crescer junto com seu usuário durante toda a vida.**

Seu objetivo não é apenas responder perguntas.

Ele deve:

* aprender continuamente;
* compreender contexto;
* construir conhecimento;
* lembrar decisões;
* organizar informações;
* automatizar processos;
* evoluir sem perder identidade.

---

# Princípios Fundamentais

* Uma única inteligência.
* Uma única memória.
* Um único núcleo cognitivo.
* Aprendizagem contínua.
* Arquitetura modular.
* Evolução permanente.
* Segurança em primeiro lugar.
* Total observabilidade.
* Controle sempre nas mãos do usuário.

---

# Arquitetura

O NEGÃO utiliza uma arquitetura modular baseada em **Clean Architecture**, **DDD**, **Event Driven Architecture** e **SOLID**.

Os módulos não representam agentes.

São órgãos especializados pertencentes ao mesmo cérebro.

```text
                    NEGÃO AI

                       Brain
                         │
 ┌───────────────────────┼────────────────────────┐
 │                       │                        │
Memory              Knowledge              Learning
 │                       │                        │
Planner          Reasoning Engine      Tool Manager
 │                       │                        │
Voice               Vision            Automation
 │                       │                        │
Events            Scheduler          API Gateway
 │
Database
```

Cada módulo possui responsabilidades claras, baixo acoplamento e alta coesão.

Toda comunicação ocorre por eventos internos.

---

# Stack Tecnológica

| Camada          | Tecnologia              |
| --------------- | ----------------------- |
| Linguagem       | Python 3.13             |
| Backend         | FastAPI                 |
| ORM             | SQLAlchemy 2.0 Async    |
| Banco           | PostgreSQL 17           |
| Busca Semântica | pgvector                |
| Cache           | Redis 7                 |
| Frontend        | Next.js 15              |
| UI              | React 19 + Tailwind CSS |
| Observabilidade | OpenTelemetry           |
| Métricas        | Prometheus              |
| Dashboards      | Grafana                 |
| Logs            | Loki                    |
| Containers      | Docker                  |
| Deploy          | Docker Compose          |
| Proxy           | Nginx                   |
| Infraestrutura  | VPS Linux               |

---

# Estrutura do Projeto

```text
negao-ai/

backend/
    app/
        brain/
        memory/
        learning/
        knowledge/
        planner/
        reasoning/
        tools/
        voice/
        vision/
        automation/
        events/
        database/
        security/
        monitoring/

frontend/

infra/

docs/

tests/

scripts/

backups/

.env.example

Makefile
```

---

# Memória

O NEGÃO possui um sistema de memória inspirado na memória humana.

### Memória de Curto Prazo

Redis

Armazena contexto temporário.

---

### Memória de Longo Prazo

PostgreSQL

Registra fatos permanentes.

---

### Memória Semântica

pgvector

Permite compreender relações entre conhecimentos.

---

### Memória Episódica

Registra acontecimentos importantes.

---

### Memória Procedural

Aprende hábitos.

Preferências.

Fluxos de trabalho.

Padrões.

---

# Knowledge Vault

O Knowledge Vault é o centro de conhecimento do sistema.

Armazena:

* documentação
* código
* projetos
* decisões
* normas
* livros
* artigos
* conversas
* pesquisas
* arquitetura
* histórico

Nada é perdido.

Tudo pode ser pesquisado.

---

# Modelo de IA

O núcleo utiliza um **Model Router**.

Modelo principal:

* NVIDIA API
* GPT-OSS-120B

A arquitetura permite adicionar novos modelos futuramente sem alterar o restante do sistema.

---

# Observabilidade

Todo componente gera telemetria.

O sistema possui:

* métricas
* tracing distribuído
* logs estruturados
* health checks
* auditoria
* monitoramento em tempo real

---

# Infraestrutura

Todo o projeto foi pensado para execução contínua em VPS Linux.

Componentes:

* PostgreSQL
* Redis
* Backend
* Frontend
* Nginx
* Grafana
* Prometheus
* Loki

Todos executando em containers Docker.

---

# Desenvolvimento

## Pré-requisitos

* Docker
* Docker Compose v2
* Git
* Make (opcional)

---

## Configuração

```bash
cp .env.example .env
```

Configure todas as variáveis antes de iniciar.

---

## Desenvolvimento

```bash
make dev
```

Serviços disponíveis:

Frontend

http://localhost:3000

Backend

http://localhost:8000

Swagger

http://localhost:8000/docs

Grafana

http://localhost:9091

Prometheus

http://localhost:9090

---

# Comandos

```bash
make dev

make dev-build

make prod

make stop

make logs

make lint

make test

make backup

make restore

make db-migrate

make db-upgrade
```

---

# Roadmap

### v0.x

Fundação

Infraestrutura

Docker

Observabilidade

Banco

Deploy

---

### v1.x

Brain

Conversa

Memória

Model Router

Knowledge Vault

---

### v2.x

Aprendizagem contínua

Automação

Ferramentas

Observação

---

### v3.x

Voz

Visão

Pesquisa

Planejamento avançado

---

### v4.x

Execução autônoma supervisionada

---

### v5.x

Escalabilidade

Cluster

Kubernetes

Alta disponibilidade

---

# Segurança

O projeto segue o princípio do menor privilégio.

* autenticação
* autorização
* auditoria
* criptografia
* HTTPS obrigatório
* segredos fora do Git
* backups automáticos
* restauração validada

---

# Visão

O objetivo do NEGÃO não é apenas responder perguntas.

O objetivo é criar uma inteligência capaz de acompanhar seu usuário durante anos, aprendendo continuamente, preservando conhecimento e tornando-se um verdadeiro parceiro de trabalho.

**Uma única inteligência. Uma única memória. Uma evolução contínua.**
