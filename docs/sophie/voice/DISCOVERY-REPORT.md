# SOPHIE BLUETOOTH VOICE — DISCOVERY REPORT

**Data:** 2026-08-21  
**Fase:** Discovery somente leitura  
**Escopo:** voz no desktop/browser com fone Bluetooth tratado pelo sistema operacional  
**Implementação nesta entrega:** nenhuma

## 1. Veredicto da descoberta

**NOT READY**

Existe uma base funcional de voz, mas ela ainda não entrega a experiência pedida. O estado atual é:

- STT e TTS existem como endpoints REST batch.
- Há um WebSocket `/ws/voice`, porém ele não chama o Conversation Engine nem é usado pelo frontend.
- O chat textual já usa WebSocket, `ConversationService` e o mesmo `BrainService`.
- O browser captura o microfone padrão via `getUserMedia`/`MediaRecorder`, mas não há seleção explícita de entrada/saída, `devicechange`, VAD ou sessão contínua.
- Não existe `MediaController`, adapter Spotify, controle de mídia do sistema ou Permission Engine de tools.
- Não há app desktop ou mobile nativo; o cliente atual é Next.js/PWA.
- O teste físico Bluetooth não foi executado. Na inspeção deste Windows existem dispositivos Bluetooth pareados, mas não foi exposto um endpoint de áudio Bluetooth em `Win32_SoundDevice`.

O menor caminho para V0 é reutilizar o WebSocket e o `ConversationService` existentes, evoluindo o módulo `voice`; não criar um segundo cérebro, WebRTC, Electron/Tauri, mobile nativo ou Spotify nesta etapa.

## 2. Baseline do worktree

### 2.1 Estado do repositório

O primeiro comando executado foi `git status --short --branch`.

- Branch: `main`.
- Relação com remoto: `ahead 25, behind 27`.
- Estado: **BLOCKED** para uma implementação segura sem revisão de ownership, porque há alterações locais em 61 arquivos rastreados, mudanças em `backend/app/modules/voice`, `frontend/components/voice`, autenticação, WebSocket, frontend e infraestrutura.
- Existem também `docs/sophie/` e três arquivos RPM não rastreados.
- Nenhuma alteração de implementação foi feita nesta auditoria. Foi criado somente este relatório novo em `docs/sophie/voice/`.

### 2.2 Stack observada

| Área | Evidência | Status |
|---|---|---|
| Backend | Python 3.13.9, FastAPI, Pydantic Settings, SQLAlchemy async, Redis, HTTPX | PASS |
| STT | NVIDIA NIM compatível com `/audio/transcriptions`, modelo `nvidia/parakeet-tdt-0.6b-v2` | PASS |
| TTS | `edge-tts`, voz `pt-BR-FranciscaNeural`, saída MP3 | PASS |
| Frontend | Next.js 15.1.6, React 19, TypeScript, PWA | PASS |
| Transporte textual | WebSocket `/ws/conversation` | PASS |
| Infraestrutura | Docker Compose + Nginx + scripts de VPS | PASS |
| Render | Não há evidência no repositório de deploy Render | NOT APPLICABLE |

### 2.3 Gates executados

| Check | Resultado | Evidência/limitação |
|---|---|---|
| `python -m ruff check app tests` | PASS | Nenhum erro reportado |
| `python -m pytest -q` | BLOCKED | Coleta interrompida por `ModuleNotFoundError` para `structlog` e `fakeredis`; o ambiente também avisou que `asyncio_mode` não está instalado/reconhecido |
| `python -m mypy app` | BLOCKED | `mypy` não está instalado no Python usado |
| `npx tsc --noEmit` | PASS | Processo concluído sem saída de erro |
| `npm run lint` | BLOCKED | Ficou sem conclusão/saída por mais de 40 segundos e foi interrompido; exibiu apenas o aviso de `.eslintignore` legado |
| `npm run build` | NOT TESTED | Não executado nesta discovery |
| Teste real de fone Bluetooth | BLOCKED | Nenhum endpoint de áudio Bluetooth apareceu no inventário de áudio do Windows durante a auditoria |

Os resultados acima são do worktree atual e substituem qualquer baseline histórico citado em documentos anteriores.

## 3. Respostas obrigatórias

### 3.1 Como Sophie trata voz hoje?

O módulo `backend/app/modules/voice` possui `VoiceService`, contratos de domínio, adapters reais/fake, eventos e router.

O fluxo que o frontend realmente usa é:

```text
getUserMedia({ audio: true })
  → MediaRecorder em audio/webm
  → POST /api/proxy/voice/transcribe
  → POST /voice/transcribe
  → NVIDIA STT
  → texto no frontend
  → usuário envia o texto ao chat
  → /ws/conversation
  → ConversationService
  → BrainService
  → POST /api/proxy/voice/synthesize
  → edge-tts
  → HTMLAudioElement / new Audio
```

As implementações estão em `frontend/components/voice/voice-panel.tsx:158-211,227-316` e `frontend/components/chat/chat-panel.tsx:267-363,576-640`. Isso é push-to-talk em turnos isolados, não conversa de voz contínua.

O WebSocket `/ws/voice` atual acumula frames binários entre `start` e `end` e responde com `transcript`; também aceita `speak` para TTS. Ele está em `backend/app/modules/voice/router.py:138-255`, mas não há cliente frontend conectado a ele.

**Status: PASS para voz batch isolada; FAIL para o objetivo Bluetooth Voice contínuo.**

### 3.2 Existe STT?

Sim.

- Contrato: `STTAdapter.transcribe(audio_bytes, content_type)` em `backend/app/modules/voice/domain/__init__.py:33-36`.
- Implementação: `NvidiaTranscriptionAdapter` em `backend/app/modules/voice/infrastructure/__init__.py:23-47`.
- Provider: NVIDIA NIM em `${nvidia_base_url}/audio/transcriptions`.
- Modelo: `settings.brain_stt_model`, por padrão `nvidia/parakeet-tdt-0.6b-v2`.
- Timeout atual: 30 segundos.
- A chave `nvidia_api_key` é obrigatória para transcrever.

Limitações relevantes: não existe `stream()`, o áudio é enviado inteiro, não há limite de bytes por turno no router, não há VAD e o WebSocket fixa o content-type em `audio/webm`.

**Status: PASS para STT batch; FAIL para STT streaming.**

### 3.3 Existe TTS?

Sim.

- Contrato: `TTSAdapter.synthesize(text)` em `backend/app/modules/voice/domain/__init__.py:39-42`.
- Implementação: `EdgeTTSAdapter` em `backend/app/modules/voice/infrastructure/__init__.py:50-74`.
- Provider: Microsoft Edge Neural via `edge-tts`, sem chave local configurada.
- Voz padrão: `pt-BR-FranciscaNeural`.
- Saída: MP3, acumulado integralmente em `bytearray` antes de retornar.

Não há `stream()`, chunks de playback, cancelamento de síntese nem barge-in.

**Status: PASS para TTS batch; FAIL para TTS streaming/interrompível.**

### 3.4 Existe WebSocket?

Sim, em três caminhos distintos:

| Endpoint | Uso atual | Status |
|---|---|---|
| `/ws` | Heartbeat/lifecycle | PASS |
| `/ws/conversation` | Sessão textual, tokens e `done` | PASS |
| `/ws/voice` | Acumula áudio, STT batch e TTS batch | FAIL para integração real; endpoint órfão no frontend |

O protocolo de `/ws/voice` é legado e não é versionado: usa `start`, frames binários, `end`, `speak`, `transcript`, `audio` e `error` (`backend/app/modules/voice/router.py:181-215`). Não existem os eventos pedidos, como `voice.session.started`, `voice.audio.chunk`, `voice.transcript.final` ou `voice.response.completed`.

O Nginx suporta upgrade WebSocket em `infra/nginx/conf.d/negao.conf:41-49`, mas o arquivo só declara listener HTTP na porta 80 (`:10`). WSS/TLS não está comprovado pelo repositório.

**Status: PASS para WebSocket textual; FAIL para protocolo realtime de voz V0.**

### 3.5 Existe Conversation Engine reutilizável?

Sim, e deve ser reutilizado.

`ConversationService.chat()` em `backend/app/modules/conversation/application/__init__.py:90-130`:

1. persiste a mensagem do usuário;
2. carrega o contexto da sessão;
3. inclui o `SYSTEM_PROMPT`;
4. chama `BrainService.complete()` com `TaskType.CHAT`, `session_id` e `user_id`;
5. persiste a resposta da Sophie;
6. retorna `ChatResult`.

O contexto está limitado a `conversation_max_context_messages`, padrão 20 (`backend/app/modules/configuration/settings.py:58-60`). O Brain único é exposto por `get_brain_service()` e o `ModelRouter` já possui retry/circuit breaker/cache no caminho textual.

O Voice atual não chama `ConversationService.chat()`. Portanto, a conversa por voz não preserva contexto hoje.

**Status: PASS para reutilização; FAIL para integração voice → conversation.**

### 3.6 Existe Permission Engine?

Não.

O módulo `tool_manager` é scaffolding não montado. Não há capability engine, consentimento de tool, `MediaController` ou dispatch estruturado de comandos de mídia. A autenticação existente é uma API key compartilhada com nível plano `READ_ONLY`, não uma política de permissões por usuário/dispositivo.

Há autenticação de rotas HTTP por `require_api_key` e ticket WebSocket de uso único em `backend/app/modules/security/infrastructure/__init__.py:50-90`. O ticket possui TTL de 60 segundos e é resgatado via `getdel`, mas o modelo atual não vincula o ticket a um usuário real do produto nem a uma sessão de voz específica.

**Status: FAIL para Permission Engine/capabilities; PASS somente para o mecanismo técnico de API key/ticket existente.**

### 3.7 Como controlar mídia no ambiente atual?

Não há implementação.

Busca no código não encontrou `MediaController`, `SystemMediaController`, Spotify, MPRIS, Windows Media Session, `MediaSession` browser, `setVolume`, `next_track`, `previous_track` ou ações equivalentes. Não existe adapter de sistema nem tool estruturada.

O controle de mídia deve ser uma fase posterior à V0 de conversa e deve usar:

```text
MediaController
  → SystemMediaController (primeiro ambiente comprovado)
  → SpotifyMediaController (futuro, OAuth e capability própria)
```

Não usar shell/PowerShell disparado pelo modelo para ações simples.

**Status: NOT TESTED como integração, porque não existe adapter para executar.**

### 3.8 Como detectar dispositivos de áudio?

Hoje não há detecção própria de dispositivos.

O frontend usa `navigator.mediaDevices.getUserMedia({ audio: true })`, sem `enumerateDevices`, sem `deviceId`, sem listener `devicechange` e sem seleção independente de input/output. A saída usa o dispositivo padrão do navegador/sistema via `<audio>` ou `new Audio()`.

O Bluetooth é corretamente responsabilidade do sistema operacional. O cliente Sophie deve apenas selecionar os dispositivos de áudio que o browser expõe. Para uma evolução futura, o contrato recomendado é:

```text
AudioDeviceManager
  listInputDevices()
  listOutputDevices()
  selectInput(deviceId)
  selectOutput(deviceId)
  watchChanges()
```

No snapshot do Windows, `Get-PnpDevice -Class Bluetooth` mostrou dispositivos pareados, mas `Win32_SoundDevice` mostrou somente Realtek/NVIDIA e nenhum endpoint Bluetooth de áudio. Isso não prova que o hardware não exista; prova apenas que o endpoint não estava exposto/conectado para o teste nesta sessão.

**Status: FAIL para AudioDeviceManager; BLOCKED para prova física Bluetooth.**

### 3.9 Quais arquivos precisam mudar para V0?

Mudanças mínimas recomendadas, após aprovação da discovery:

| Área | Arquivos prováveis | Objetivo |
|---|---|---|
| Contrato voice | `backend/app/modules/voice/domain/__init__.py`, `events.py` | adicionar sessão, turn, IDs, eventos versionados e limites tipados |
| Orquestração voice | `backend/app/modules/voice/application/__init__.py` | ligar STT → `ConversationService.chat` → TTS sem criar cérebro paralelo |
| Transporte voice | `backend/app/modules/voice/router.py` | evoluir `/ws/voice`, autenticar, limitar chunks/turnos, controlar estado e cleanup |
| Providers | `backend/app/modules/voice/infrastructure/__init__.py` | manter batch V0, preparar portas `stream()` sem acoplar ao provider |
| Configuração | `backend/app/modules/configuration/settings.py` | limites de bytes, duração, idle timeout, concorrência e timeouts nomeados |
| Segurança | `backend/app/modules/security/infrastructure`, `security/router.py` | vincular ticket à sessão/principal e eliminar fallback inadequado no cliente web |
| Cliente | `frontend/components/voice/voice-panel.tsx`, `frontend/lib/types.ts` | estados de sessão, PTT, eventos, playback e indicador `LISTENING` |
| Cliente novo | `frontend/lib/audio-devices.ts`, `frontend/lib/voice-protocol.ts` | isolamento de device manager e protocolo tipado |
| Proxy/infra | `frontend/app/api/ws-info/route.ts`, Nginx/compose somente se necessário | manter segredo server-side e comprovar WSS/limites |
| Testes | `backend/tests/tests_unit/test_voice.py`, novos contract/E2E e testes frontend | provar contrato, auth, limites, contexto e playback com fakes |

V0 não exige migration se a sessão puder permanecer em memória/conversa existente. Se for decidido persistir `voice_sessions`, será obrigatória migration retrocompatível antes de qualquer alteração de schema.

### 3.10 Quais arquivos não devem ser alterados agora?

- `backend/app/modules/brain/*` para criar uma segunda lógica de voz; o Brain atual já é o cérebro único.
- Migrações aplicadas e modelos de banco, enquanto V0 não exigir persistência nova.
- `tool_manager`, módulos vision, automação, IoT, wake word, smart glasses e smartwatch.
- `frontend` nativo inexistente; não adicionar Electron, Tauri, React Native ou Capacitor nesta prova desktop/browser.
- Integração Spotify, OAuth de mídia e pesquisa de música específica.
- Arquivos de rebrand, artefatos RPM e mudanças concorrentes já presentes no worktree, salvo ownership explícito e revisão do diff.
- `infra/scripts/vps-setup.sh` e outros scripts de deploy, exceto se a validação provar que o transporte WSS/limites da V0 dependem deles.

### 3.11 Quais riscos existem?

#### Segurança e privacidade

1. O endpoint Next `/api/ws-info` é acessível pelo browser sem autenticação de usuário e recebe um ticket usando a API key server-side (`frontend/app/api/ws-info/route.ts:6-29`). O ticket não expõe a chave mestre, mas ainda concede acesso à sessão WebSocket sob o principal compartilhado atual.
2. O WebSocket aceita fallback por `?api_key=` (`backend/app/modules/security/infrastructure/__init__.py:83-90`) e faz `accept()` antes da autenticação (`backend/app/modules/voice/router.py:233-242`). Para a V0 web, manter somente ticket curto, bound-to-session e fail-closed.
3. `/ws/voice` acumula bytes sem `MAX_AUDIO_CHUNK`, `MAX_TURN_BYTES`, codec allowlist ou validação robusta de frame (`backend/app/modules/voice/router.py:138-154`). Isso permite abuso de memória e flood.
4. Há rate limit de abertura por IP, mas não há limite específico demonstrado para bytes de áudio, STT, TTS ou sessões abandonadas. O limiter atual é janela fixa (`backend/app/modules/api/rate_limit.py:22-98`), não sliding window por usuário.
5. Não existe autorização por capability para áudio/media. A V0 deve limitar-se a `audio.input.read` e `audio.output.write` dentro de uma sessão explicitamente iniciada.
6. Áudio bruto não é persistido pelo caminho atual; fica em memória até transcrição. Isso é positivo, mas deve virar contrato explícito: `CAPTURE → PROCESS → DISCARD`.
7. Quando o Voice for ligado à conversa, o transcript seguirá a política existente de conversa; não deve ser automaticamente promovido a memória longa.
8. Erros do provider incluem texto bruto de resposta HTTP em exceções (`backend/app/modules/voice/infrastructure/__init__.py:37-43`) e podem acabar em logs/respostas. A implementação deve redigir corpos externos e nunca registrar áudio, tokens, API keys ou transcript integral.

#### Confiabilidade e UX

1. O browser atualmente usa o dispositivo padrão, não o Bluetooth escolhido pelo usuário.
2. Alguns headsets mudam de A2DP para HFP/HSP quando o microfone é ativado; a perda de qualidade deve ser documentada como limitação do perfil, não tratada automaticamente como falha.
3. O TTS atual só toca após o MP3 completo; a latência percebida inclui STT, Brain, TTS inteiro e download.
4. Não há cancelamento de TTS, barge-in, echo cancellation controlada ou full-duplex.
5. Desconexão WebSocket não possui protocolo voice de reconnect/idempotência. Uma ação futura não pode ser repetida após reconnect sem `interaction_id` e deduplicação.
6. Não há métricas voice específicas de STT/TTS/turno/bytes/desconexão.

#### Infraestrutura

1. O repositório suporta WebSocket pelo Nginx, mas não comprova TLS/WSS em produção.
2. O arquivo `infra/scripts/vps-setup.sh` referencia `COMPOSE_FILE` sem defini-lo no próprio script; isso é um risco operacional independente que deve ser corrigido/validado antes de depender dele para o rollout.
3. A configuração `client_max_body_size 25m` do Nginx é um teto global e não substitui limites por sessão/chunk no backend.

### 3.12 Qual o menor caminho para V0?

```text
1. Corrigir o ambiente de testes e confirmar worktree/ownership
2. Manter PTT/Start Session; não começar por wake word
3. Reutilizar /ws/voice, sem criar WebRTC
4. Criar protocolo versionado de controle JSON + frames binários
5. Capturar um turno limitado no browser com o dispositivo OS selecionado
6. STT batch no provider atual
7. Enviar o texto como UserMessage ao ConversationService.chat()
8. Usar o Brain atual com session_id/user_id existentes
9. TTS batch no provider atual
10. Enviar metadata + áudio ao browser e tocar no output padrão do OS
11. Exibir IDLE/CONNECTING/LISTENING/TRANSCRIBING/THINKING/SPEAKING/ERROR
12. Adicionar limites, ticket bound-to-session, timeout e cleanup
13. Testar com fakes, contract test e browser real
14. Só então executar teste físico com headset Bluetooth conectado
```

O caminho acima prova a experiência de conversa antes de introduzir streaming real. Depois da V0, as portas `STTAdapter`/`TTSAdapter` podem ganhar `stream()` e a máquina de estados pode evoluir para V1 sem trocar o Conversation Engine.

## 4. Arquitetura atual observada

```text
Browser/PWA
  ├─ voice-panel → REST transcribe/synthesize (voz isolada)
  └─ chat-panel  → WS conversation (texto) + REST synthesize (resposta)
        ↓
Next BFF /api/proxy e /api/ws-info
        ↓
FastAPI
  ├─ /voice/status, /voice/transcribe, /voice/synthesize
  ├─ /ws/voice                  [órfão no cliente]
  └─ /ws/conversation            [caminho textual ativo]
        ↓
VoiceService / adapters
ConversationService
BrainService / ModelRouter
        ↓
NVIDIA NIM / edge-tts / Redis / Postgres
```

## 5. Arquitetura alvo mínima para V0

```text
OS pareia Bluetooth
        ↓
Browser Sophie
  AudioDeviceManager + PTT + estado LISTENING
        ↓ WSS, ticket curto e bound-to-session
/ws/voice v1
  controle JSON versionado + frames binários limitados
        ↓
STTAdapter batch
        ↓ UserMessage
ConversationService.chat(session_id, user_id)
        ↓
BrainService existente
        ↓ Semantic/TextResponse
TTSAdapter batch
        ↓
metadata JSON + áudio binário
        ↓
HTMLAudioElement no output Bluetooth escolhido pelo OS
```

Media control fica fora da V0. Em V1, o fluxo deverá ser:

```text
transcript → FastCommandRouter → MediaController estruturado → ack curto
                                   ↘ Conversation/Brain somente como fallback
```

## 6. Definição de pronto proposta

### V0

**NOT READY** até cumprir todos os itens:

- sessão autenticada inicia e encerra;
- microfone do headset/OS é capturado;
- áudio chega ao backend com limites e formato explícitos;
- STT produz transcript;
- transcript entra no `ConversationService` existente;
- resposta preserva `session_id` e contexto;
- TTS produz áudio;
- áudio toca no output Bluetooth/OS;
- estados visíveis e erros amigáveis;
- sem armazenamento de áudio bruto;
- testes unit/contract/E2E passam;
- teste físico de headset passa.

### V1

Ainda **NOT READY**. Depende da V0 e acrescenta:

- conversação contínua;
- reconnect bounded e idempotência;
- `play`, `pause`, `next`, `previous`, `volume`, `current_track`;
- `MediaController` com capability e validação enum;
- métricas e tracing sem transcript como label;
- teste real de desconexão/reconexão e mídia.

## 7. Status final da discovery

| Item | Status |
|---|---|
| Arquitetura existente descoberta | PASS |
| STT existente | PASS |
| TTS existente | PASS |
| Conversation Engine reutilizável | PASS |
| WebSocket textual reutilizável | PASS |
| WebSocket voice integrado ao core | FAIL |
| Streaming STT/TTS | FAIL |
| AudioDeviceManager | FAIL |
| Bluetooth físico testado | BLOCKED |
| MediaController | NOT TESTED |
| Permission Engine de tools | FAIL |
| Baseline completo de testes | BLOCKED |
| V0 pronta para implementação | NOT READY |

**Próxima ação autorizada:** revisar este relatório e, somente após aprovação, iniciar o baseline reproduzível/contratos da V0 em uma mudança incremental isolada.
