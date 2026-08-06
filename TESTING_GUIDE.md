# 🧪 TESTE DE INTEGRAÇÃO — NEGÃO AI

Depois que o backend e frontend estiverem rodando, use esse documento para testar tudo.

---

## ✅ TESTE 1: Backend está respondendo?

### 1.1 Health Check
```bash
curl http://localhost:8000/health
```

**Esperado:**
```json
{"status": "ok"}
```

### 1.2 Brain Status
```bash
curl http://localhost:8000/api/v1/brain/status \
  -H "X-API-Key: negao-dev-api-key"
```

**Esperado:**
```json
{
  "status": "ready",
  "model": "nvidia/gpt-oss-120b",
  "temperature": 0.3,
  "max_tokens": 1024
}
```

---

## ✅ TESTE 2: Criar uma Conversação

```bash
curl -X POST http://localhost:8000/api/v1/conversation/start \
  -H "X-API-Key: negao-dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "teste-user"}'
```

**Esperado:**
```json
{
  "session_id": "uuid-aqui",
  "user_id": "teste-user",
  "created_at": "2024-12-19T10:00:00Z"
}
```

**Salve o `session_id`!** Você vai precisar para os próximos testes.

---

## ✅ TESTE 3: Enviar uma Mensagem (HTTP)

```bash
curl -X POST http://localhost:8000/api/v1/conversation/message \
  -H "X-API-Key: negao-dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SEU_SESSION_ID_AQUI",
    "text": "Olá NEGÃO! Qual é o seu nome?"
  }'
```

**Esperado:**
```json
{
  "session_id": "seu-session-id",
  "role": "assistant",
  "text": "Olá! Meu nome é NEGÃO, assistente pessoal de inteligência artificial...",
  "timestamp": "2024-12-19T10:00:01Z"
}
```

---

## ✅ TESTE 4: WebSocket (Chat em Tempo Real)

Use o `wscat` ou teste diretamente no Frontend.

### 4.1 Instalar wscat (opcional)
```bash
npm install -g wscat
```

### 4.2 Conectar ao WebSocket
```bash
wscat -c "ws://localhost:8000/api/v1/ws/conversation/SEU_SESSION_ID_AQUI"
```

### 4.3 Enviar Mensagem
```json
{"text": "Qual é a capital do Brasil?"}
```

**Esperado:** NEGÃO responde em tempo real com streaming de tokens.

---

## ✅ TESTE 5: Frontend (o grande teste!)

### 5.1 Abrir no Navegador
```
http://localhost:3000
```

### 5.2 Testes Manuais
1. Clique no ícone **Conversa** (chat)
2. Digite: `"Olá NEGÃO, como você está?"`
3. Pressione **Enter**
4. 🎉 Esperado: NEGÃO responde em tempo real!

### 5.3 Testes Adicionais
- [ ] Teste em Desktop (1920x1080)
- [ ] Teste em Tablet (768x1024)
- [ ] Teste em Mobile (375x812)
- [ ] Teste múltiplas mensagens
- [ ] Teste com mensagens longas
- [ ] Teste com emojis
- [ ] Teste com código
- [ ] Teste com URLs

---

## 🔊 TESTE 6: Voz (TTS)

### 6.1 Teste no Frontend
1. Vá para página de **Voz**
2. Fale algo no microfone
3. NEGÃO deve responder em áudio

### 6.2 Teste via API
```bash
curl -X POST http://localhost:8000/api/v1/voice/tts \
  -H "X-API-Key: negao-dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Olá! Eu sou o NEGÃO.",
    "voice": "pt-BR-FranciscaNeural",
    "rate": "+0%"
  }' \
  --output audio.mp3
```

**Esperado:** Arquivo `audio.mp3` gerado.

---

## 📊 TESTE 7: Dashboard

### 7.1 Abrir Dashboard
```
http://localhost:3000
```

### 7.2 Verificar
- [ ] Mostra status do Brain
- [ ] Mostra últimas conversas
- [ ] Mostra estatísticas
- [ ] Mostra modelo da IA
- [ ] Mostra temperatura

---

## 🐛 DEBUG - Se Algo Não Funcionar

### Erro: "Connection refused"
```bash
# Verificar se backend está rodando
curl http://localhost:8000/health

# Se não responder, veja os logs do backend
# Terminal onde rodou uvicorn deve mostrar erros
```

### Erro: "API key invalid"
```bash
# Verificar se a chave está no .env
cat .env | grep NEGAO_API_KEY

# Deve ser: negao-dev-api-key
```

### Erro: "NVIDIA API error"
```bash
# Verificar a chave NVIDIA
cat .env | grep NEGAO_NVIDIA_API_KEY

# Certifique-se que não há espaços em branco
```

### Erro: "Database connection error"
```bash
# Verificar PostgreSQL
psql -U negao -h localhost -d negao -c "SELECT 1;"

# Ou no Docker
docker compose exec db psql -U negao -d negao -c "SELECT 1;"
```

### Erro: "WebSocket connection failed"
```bash
# Verificar logs do backend
# Pode ser problema de CORS ou timeout

# Tente:
curl -i -N http://localhost:8000/api/v1/ws/conversation/test
```

---

## 📈 TESTE 8: Performance

### 8.1 Chrome DevTools
1. Abra `http://localhost:3000`
2. Pressione `F12` (DevTools)
3. Vá em **Performance**
4. Clique em Record
5. Envie uma mensagem no chat
6. Parar recording
7. Analise:
   - Tempo de resposta
   - FPS
   - Mem usage

### 8.2 Lighthouse
1. DevTools > **Lighthouse**
2. Clique em "Analyze page load"
3. Verifique:
   - Performance > 90
   - Accessibility > 90
   - Best Practices > 90
   - SEO > 90

### 8.3 Network
1. DevTools > **Network**
2. Envie mensagem
3. Observe requisições:
   - Tamanho das respostas
   - Tempo de resposta
   - Quantidade de requisições

---

## ✅ CHECKLIST FINAL

```
Backend Tests:
- [ ] Health check OK
- [ ] Brain status OK
- [ ] Conversa criada com sucesso
- [ ] Mensagem enviada e resposta recebida
- [ ] WebSocket conectado
- [ ] TTS funcionando

Frontend Tests:
- [ ] Page carrega
- [ ] Chat panel aberto
- [ ] Mensagem enviada
- [ ] Resposta recebida
- [ ] Responsive em mobile
- [ ] Responsive em tablet
- [ ] Performance > 90
- [ ] Acessibilidade > 90

Voice Tests:
- [ ] TTS funcionando
- [ ] STT funcionando (se disponível)

Dashboard Tests:
- [ ] Status do Brain visível
- [ ] Histórico de conversas visível
- [ ] Estatísticas visíveis
```

---

## 🎉 SE TUDO PASSOU!

**PARABÉNS! NEGÃO ESTÁ ACORDADO! 🚀**

Próximos passos:
1. ✅ Phase 4: Responsive Design Testing (Já feito, mas validar)
2. ✅ Phase 5: Performance Optimization
3. ✅ Phase 6-10: Polish Final
4. 🚀 Deploy em Produção

---

**Quando os testes passarem, você está pronto para:**
- Melhorar a responsividade
- Otimizar performance
- Polir a interface
- Deploy em produção

**Status:** ⏳ AGUARDANDO EXECUÇÃO DOS TESTES
