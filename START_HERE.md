# 🚀 START HERE — ACORDAR O NEGÃO (Copie & Cole)

## ⚡ SUPER RÁPIDO (5 minutos)

### Terminal 1: Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend
```bash
cd frontend
npm install
npm run dev
```

### Navegador
```
http://localhost:3000
→ Clique em "Conversa"
→ Digite: "Olá NEGÃO!"
→ Pressione Enter
→ 🎉 PRONTO!
```

---

## ⚠️ PRÉ-REQUISITOS

Se não tiver um desses, instale AGORA:

### Python 3.13+
```bash
python --version
```
**Não tem?** https://www.python.org/downloads/

### Node.js 18+
```bash
node --version
```
**Não tem?** https://nodejs.org/

### PostgreSQL + Redis

**OPÇÃO 1: Docker (Recomendado)**
```bash
docker-compose up -d
```

**OPÇÃO 2: Local**
Instale PostgreSQL e Redis manualmente.

---

## ✅ VERIFICAR TUDO FUNCIONOU

Abra uma **NOVA aba do terminal** e rode:

```bash
# Backend respondendo?
curl http://localhost:8000/health

# IA pronta?
curl http://localhost:8000/api/v1/brain/status -H "X-API-Key: negao-dev-api-key"

# Database OK?
psql -U negao -h localhost -d negao -c "SELECT 1;"
```

---

## 🎯 PRONTO!

Se todos os 3 testes acima passaram, o NEGÃO está ACORDADO! 🚀

**Próximas etapas:** Ver `INTEGRATION_README.md` para testes completos.

---

## ❌ NÃO FUNCIONOU?

### ❌ "Connection refused"
```
Backend não tá rodando!
Verifique Terminal 1 — tem mensagem de erro?
```

### ❌ "Database connection error"
```
PostgreSQL não está rodando!
Tente: docker-compose up -d
```

### ❌ "API key invalid"
```
Chave NVIDIA pode estar incorreta.
Verifique .env: NEGAO_NVIDIA_API_KEY
```

### ❌ Outra coisa?
Leia: `API_INTEGRATION_GUIDE.md` (guia completo)

---

## 💬 AGORA É HORA DE POLIR!

Quando o NEGÃO responder, vamos:
1. ✅ Phase 4: Responsive Design
2. ✅ Phase 5: Performance
3. ✅ Phase 6-10: Visual Polish

**Objetivo:** Interface digna de bilhões de dólares 💎

---

**Dúvidas? Confira:**
- `INTEGRATION_README.md` — Resumo (60 segundos)
- `API_INTEGRATION_GUIDE.md` — Completo (tudo detalho)
- `TESTING_GUIDE.md` — Testes (curl, bash, browser)
- `SETUP_STATUS.md` — Checklist (what's done)
