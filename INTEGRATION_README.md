# 🤖 NEGÃO AI — Guia de Integração (60 segundos)

## ✅ O que foi feito?

- ✅ `.env` criado com **NVIDIA API Key**
- ✅ `frontend/.env.local` criado
- ✅ Script `quick-start.bat` para Windows
- ✅ Guia completo de integração
- ✅ Teste de integração documentado

---

## 🚀 Como acordar o NEGÃO? (3 passos)

### PASSO 1: Backend (Terminal 1)
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Espere por:** `Uvicorn running on http://0.0.0.0:8000`

### PASSO 2: Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

**Espere por:** `Local: http://localhost:3000`

### PASSO 3: Testar (Navegador)
```
http://localhost:3000
→ Clique em "Conversa"
→ Digite: "Olá NEGÃO!"
→ Pressione Enter
→ 🎉 NEGÃO responde!
```

---

## 📋 Pré-requisitos

- ✅ Python 3.13+
- ✅ Node.js 18+
- ✅ PostgreSQL rodando (localhost:5432)
- ✅ Redis rodando (localhost:6379)
- ✅ NVIDIA API Key (já configurada em `.env`)

### Não tem PostgreSQL/Redis?

#### Opção 1: Docker Compose
```bash
docker-compose up -d
```

#### Opção 2: Instalar Local
- PostgreSQL: https://www.postgresql.org/download/
- Redis: https://redis.io/download/

---

## 📊 Verificação Rápida

```bash
# Backend está OK?
curl http://localhost:8000/health

# Brain está pronto?
curl http://localhost:8000/api/v1/brain/status \
  -H "X-API-Key: negao-dev-api-key"

# Database conectado?
psql -U negao -h localhost -d negao -c "SELECT 1;"
```

---

## 🔧 Troubleshooting

| Problema | Solução |
|----------|---------|
| "Connection refused" | Backend não está rodando. Execute PASSO 1 acima |
| "API key invalid" | Verifique `.env` tem `NEGAO_API_KEY=negao-dev-api-key` |
| "Database error" | PostgreSQL não está rodando. Execute `docker-compose up -d` |
| "NVIDIA error" | NVIDIA API Key inválida ou expirada. Gere nova em build.nvidia.com |
| "WebSocket failed" | Backend ou Frontend não tá respondendo. Verifique os logs |

---

## 📁 Arquivos Importantes

| Arquivo | Descrição |
|---------|-----------|
| `.env` | Configurações backend (NVIDIA KEY aqui!) |
| `frontend/.env.local` | Configurações frontend |
| `quick-start.bat` | Script de inicialização (Windows) |
| `API_INTEGRATION_GUIDE.md` | Guia detalhado (leia se der problema) |
| `SETUP_STATUS.md` | Checklist de status |
| `TESTING_GUIDE.md` | Testes completos |

---

## 🎯 Próximas Etapas (Quando NEGÃO responder)

1. **Phase 4:** Responsive Design Testing
2. **Phase 5:** Performance Optimization
3. **Phase 6-10:** Visual Polish

---

## 💬 NEGÃO Pronto?

Quando você ver a resposta do NEGÃO no chat:

```
USER: Olá NEGÃO!
NEGÃO: Olá! Tudo bem com você? Em que posso ajudar?
```

**Aí sim, NEGÃO ACORDOU! 🚀**

Próximas melhorias são design + performance (Phase 4+).

---

**Precisa de ajuda?** Veja `API_INTEGRATION_GUIDE.md` para tudo detalhado.
