# 🔴 REDIS NA NUVEM — Credenciais e Testes

**Status:** ✅ CONFIGURADO NO `.env`

---

## 📊 Credenciais Redis

```
Host:       potato-tail-supermodern-53945.db.redis.io
Porta:      15412
Usuário:    default
Senha:      fxopEpoaJsGw3fjuKMoLhKc1ydNm3tZI
URL:        redis://default:REDACTED@potato-tail-supermodern-53945.db.redis.io:15412/0
```

---

## ✅ Testar Conexão

### Opção 1: redis-cli (Local)
```bash
# Instalar redis-cli
# Windows: choco install redis-64
# Mac: brew install redis
# Linux: apt-get install redis-tools

# Testar conexão
redis-cli -u "redis://default:REDACTED@potato-tail-supermodern-53945.db.redis.io:15412/0" ping
```

**Esperado:** `PONG`

### Opção 2: Python
```bash
pip install redis
python
```

```python
import redis

r = redis.from_url(
    "redis://default:REDACTED@potato-tail-supermodern-53945.db.redis.io:15412/0"
)
print(r.ping())  # True
print(r.set("test", "negao"))  # True
print(r.get("test"))  # b'negao'
```

### Opção 3: Curl (teste HTTP)
```bash
# Redis expõe interface HTTP em algumas plataformas
curl -u default:fxopEpoaJsGw3fjuKMoLhKc1ydNm3tZI \
  redis://potato-tail-supermodern-53945.db.redis.io:15412
```

### Opção 4: Backend (automático)
```bash
# Quando o backend iniciar, ele conectará automaticamente
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Verifique os logs:
# [INFO] Redis connection established
```

---

## 🧪 Testar com Backend

### STEP 1: Iniciar Backend
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Espere por:** `Uvicorn running on http://0.0.0.0:8000`

### STEP 2: Verificar Logs
Procure por:
```
[INFO] Redis connection established
[INFO] Redis cache ready
```

### STEP 3: Testar Redis via API
```bash
# Criar uma conversa (isso usa Redis para cache)
curl -X POST http://localhost:8000/api/v1/conversation/start \
  -H "X-API-Key: negao-dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "teste"}'

# Resposta esperada:
# {"session_id": "uuid", "user_id": "teste", "created_at": "..."}
```

### STEP 4: Verificar Cache
```bash
# Conectar ao Redis e verificar chaves criadas
redis-cli -u "redis://default:REDACTED@potato-tail-supermodern-53945.db.redis.io:15412/0"

> KEYS *
> GET "conversation:uuid"
```

---

## 📝 Arquivo `.env` Atualizado

```env
NEGAO_REDIS_URL=REDACTED
```

Está em: `C:.env`

---

## ⚠️ SEGURANÇA

🚨 **NÃO COMMITE** esse arquivo no Git!

✅ Já está em `.gitignore`

```bash
# Verificar
cat .gitignore | grep .env
```

**Esperado:** `.env` está listado

---

## 🔗 Integração com Backend

O backend automaticamente:

1. Conecta ao Redis na nuvem
2. Usa Redis para:
   - Cache de conversas
   - Cache de configurações
   - Sessions de WebSocket
   - Rate limiting
   - Fila de jobs (futura)

---

## 📊 O Que o Redis Armazena?

| Chave | Descrição | TTL |
|-------|-----------|-----|
| `conversation:{session_id}` | Histórico de mensagens | 7 dias |
| `agent:config` | Configuração do NEGÃO | 1 hora |
| `rate_limit:{ip}` | Rate limiting | 1 minuto |
| `ws:session:{session_id}` | Conexão WebSocket ativa | Session |

---

## 🚀 Próximos Passos

1. ✅ Redis em nuvem configurado
2. ⏳ PostgreSQL (está local? ou também é nuvem?)
3. ⏳ Iniciar Backend + Frontend
4. ⏳ Testar conversa
5. ⏳ Phase 4+: Polish & Optimize

---

## 🎯 Quick Test

```bash
# Tudo junto
redis-cli -u "redis://default:REDACTED@potato-tail-supermodern-53945.db.redis.io:15412/0" PING
# Deve retornar: PONG
```

**Se vir `PONG`, Redis está OK! ✅**

---

## 📚 Referências

- Redis CLI: https://redis.io/commands/
- Python Redis: https://redis-py.readthedocs.io/
- DB.redis.io: https://app.redislabs.com/
