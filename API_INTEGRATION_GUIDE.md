# 🤖 GUIA DE INTEGRAÇÃO — ACORDAR O NEGÃO

**Status:** ⚠️ IA NÃO RESPONDENDO AINDA  
**Objetivo:** Conectar backend + frontend + IA  
**Tempo Estimado:** 15-30 minutos  

---

## 📋 CHECKLIST DE INTEGRAÇÃO

### STEP 1: Configurar Variáveis de Ambiente

#### Backend (`.env` na raiz ou `backend/.env`)
```bash
# Essenciais para IA responder:
NEGAO_ENV=development
NEGAO_DEBUG=true
NEGAO_API_KEY=REDACTED

# Database (use docker compose ou servidor local)
NEGAO_DATABASE_URL=postgresql://negao:negao@localhost:5432/negao
NEGAO_REDIS_URL=REDACTED

# IA (NVIDIA — obrigatório para funcionar)
NEGAO_NVIDIA_API_KEY=REDACTED
NEGAO_NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NEGAO_BRAIN_CHAT_MODEL=nvidia/gpt-oss-120b
NEGAO_BRAIN_FALLBACK_MODEL=nvidia/llama-3.1-8b-instruct
NEGAO_BRAIN_TEMPERATURE=0.3
NEGAO_BRAIN_MAX_TOKENS=1024

# Voz (TTS)
NEGAO_TTS_VOICE=pt-BR-FranciscaNeural
NEGAO_TTS_RATE=+0%

# Frontend acesso
NEGAO_CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

#### Frontend (`.env.local` na pasta `frontend/`)
```bash
# Como o frontend acessa o backend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEGAO_API_URL=http://localhost:8000
NEGAO_API_KEY=REDACTED
```

---

### STEP 2: Verificar Dependências

#### Backend precisa de:
```
✅ Python 3.13+
✅ FastAPI
✅ PostgreSQL (ou Docker)
✅ Redis (ou Docker)
✅ NVIDIA API Key (grátis em build.nvidia.com)
```

#### Frontend precisa de:
```
✅ Node.js 18+
✅ npm/yarn/pnpm
✅ Next.js 15+
```

---

### STEP 3: Iniciar Backend

#### Opção A: Docker Compose (RECOMENDADO)
```bash
cd negao_negao
docker compose up -d

# Verificar se está rodando
curl http://localhost:8000/health
# Esperado: { "status": "ok" }
```

#### Opção B: Manual (sem Docker)
```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # ou: venv\Scripts\activate (Windows)

# Instalar dependências
pip install -e .
pip install -e .[dev]

# Configurar DB
export NEGAO_DATABASE_URL="postgresql://negao:negao@localhost:5432/negao"
export NEGAO_REDIS_URL="redis://localhost:6379/0"

# Migrations
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### STEP 4: Verificar Endpoints do Backend

```bash
# Status da API
curl http://localhost:8000/health

# Status do Brain (IA)
curl http://localhost:8000/api/v1/brain/status

# Info do WebSocket
curl http://localhost:8000/api/v1/ws-info

# Dashboard
curl http://localhost:8000/api/v1/dashboard
```

---

### STEP 5: Iniciar Frontend

```bash
cd frontend

# Instalar dependências (se não fez ainda)
npm install

# Iniciar servidor de desenvolvimento
npm run dev

# Acessar em http://localhost:3000
```

---

### STEP 6: Testar Integração

#### No Browser:
1. Abra http://localhost:3000
2. Clique no ícone de Conversa
3. Digite uma mensagem
4. Aperte Enter
5. ✅ NEGÃO deve responder!

#### Via API (teste rápido):
```bash
# Criar uma conversa
curl -X POST http://localhost:8000/api/v1/conversation/start \
  -H "X-API-Key: negao-dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"user": "teste"}'

# Enviar mensagem
curl -X POST http://localhost:8000/api/v1/conversation/message \
  -H "X-API-Key: negao-dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sua-session-id-aqui",
    "message": "Olá NEGÃO! Como você está?"
  }'
```

---

## 🔧 TROUBLESHOOTING

### ❌ "Connection refused" ao tentar conectar
**Solução:** Verifique se o backend está rodando
```bash
ps aux | grep uvicorn
# Ou
lsof -i :8000
```

### ❌ "API key invalid"
**Solução:** Verifique se `NEGAO_API_KEY` está configurado corretamente
```bash
echo $NEGAO_API_KEY  # Backend
echo $NEGAO_API_KEY  # Frontend (via env.local)
```

### ❌ "Database connection error"
**Solução:** Configure DATABASE_URL corretamente
```bash
# Testar conexão
psql -U negao -h localhost -d negao -c "SELECT 1;"
```

### ❌ "NVIDIA API key not found"
**Solução:** 
1. Vá a https://build.nvidia.com
2. Crie uma conta
3. Gere API key
4. Configure em `.env`: `NEGAO_NVIDIA_API_KEY=sua-chave`

### ❌ "WebSocket connection failed"
**Solução:** Verifique se backend permite WebSocket
```bash
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/api/v1/ws
```

---

## 📊 ARQUITETURA DA INTEGRAÇÃO

```
┌─────────────────────────────────────────────────────────────┐
│                    NEGÃO AI STACK                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frontend (Next.js)          Backend (FastAPI)             │
│  ┌──────────────────┐       ┌──────────────────────────┐   │
│  │ React Components │       │ FastAPI Server (8000)    │   │
│  │ Chat Interface   │◄─────►│ WebSocket Handler        │   │
│  │ Voice UI         │ HTTP  │ Proxy Routes             │   │
│  │ Dashboard        │ WS    │                          │   │
│  └──────────────────┘       │ Services:                │   │
│       Port 3000              │ • Brain (LLM - NVIDIA)   │   │
│                             │ • Conversation (DB)      │   │
│                             │ • Voice (STT/TTS)        │   │
│                             │ • Memory (Redis)         │   │
│                             └──────────────────────────┘   │
│                                     ▲                       │
│                   ┌─────────────────┴──────────────────┐   │
│                   ▼                                    ▼   │
│            ┌────────────────┐            ┌──────────────┐  │
│            │ PostgreSQL     │            │ Redis        │  │
│            │ (Conversation) │            │ (Cache)      │  │
│            └────────────────┘            └──────────────┘  │
│                                                             │
│                   ┌──────────────────────────┐             │
│                   │ NVIDIA API (Cloud)       │             │
│                   │ • gpt-oss-120b           │             │
│                   │ • llama-3.1-8b-instruct  │             │
│                   │ • parakeet-tdt (STT)     │             │
│                   └──────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 FLUXO DE MENSAGEM

```
1. User digita mensagem no Chat
   ↓
2. Frontend envia via WebSocket
   ↓
3. Backend recebe em /conversation/message
   ↓
4. Backend envia para NVIDIA API (LLM)
   ↓
5. NVIDIA retorna resposta da IA
   ↓
6. Backend processa e salva em DB
   ↓
7. Backend envia resposta via WebSocket
   ↓
8. Frontend mostra resposta no chat
   ↓
9. (Opcional) Frontend pede TTS para falar a resposta
```

---

## ✅ CHECKLIST FINAL

- [ ] Backend `.env` configurado com NVIDIA_API_KEY
- [ ] Frontend `.env.local` configurado com API_URL e API_KEY
- [ ] PostgreSQL rodando e migrações executadas
- [ ] Redis rodando
- [ ] Backend iniciado (uvicorn rodando)
- [ ] Frontend iniciado (npm run dev rodando)
- [ ] Teste manual: enviar mensagem no chat
- [ ] ✅ NEGÃO responde!

---

## 🎯 PRÓXIMOS PASSOS (APÓS FUNCIONAR)

1. **Testar todos os endpoints** (/brain, /conversation, /voice, /memory)
2. **Verificar WebSocket** em tempo real
3. **Testar TTS** (text-to-speech)
4. **Testar STT** (speech-to-text) na página de Voz
5. **Monitore Performance** (Lighthouse, Chrome DevTools)
6. **Deploy em produção** (Docker, Kubernetes, etc.)

---

**Status:** ⏳ AGUARDANDO CONFIGURAÇÃO  
**Próximo:** Conectar NVIDIA API + Iniciar backend + Testar

🚀 VAMOS ACORDAR O NEGÃO!
