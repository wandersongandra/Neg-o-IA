# SOPHIE VOICE V1 — DISCOVERY REPORT

Data: 2026-08-22  
Escopo: reconhecimento da base existente antes de qualquer evolução de voz.  
Regra: nenhuma feature nova foi implementada nesta etapa.

## 1. Decisão de continuidade

O owner autorizou a continuidade assumindo o risco das credenciais históricas
Redis/NVIDIA ainda utilizáveis. O `FOUNDATION GATE` técnico permanece `FAIL`;
essa autorização não altera a classificação de segurança.

## 2. Estado as-built encontrado

```text
Browser microphone
    ↓ MediaDevices + MediaRecorder
audio/webm;codecs=opus chunks
    ↓ WebSocket /ws/voice + short-lived ticket
FastAPI voice router
    ↓ turn.end: áudio completo em memória
NVIDIA /audio/transcriptions
    ↓ transcript.final
ConversationService
    ↓ resposta textual completa
edge-tts
    ↓ áudio completo em memória
Browser Audio element / setSinkId
```

## 3. Evidências no código

| Capability | Estado atual | Evidência | Confiança |
| --- | --- | --- | --- |
| Captura de microfone | FUNCTIONAL | `frontend/components/voice/voice-panel.tsx` usa `getUserMedia` e `MediaRecorder` | HIGH |
| Formato de entrada | FUNCTIONAL | `audio/webm` e `audio/webm;codecs=opus` | HIGH |
| Transporte | FUNCTIONAL | `backend/app/modules/voice/router.py` expõe `/ws/voice` | HIGH |
| Autenticação WS | FUNCTIONAL | ticket e `authenticate_ws`; sessão é conferida contra owner | HIGH |
| STT real | FUNCTIONAL | `NvidiaTranscriptionAdapter` chama `/audio/transcriptions` após `turn.end` | HIGH |
| TTS real | FUNCTIONAL | `EdgeTTSAdapter` usa voz `pt-BR` configurada | HIGH |
| Conversa | FUNCTIONAL | transcript é encaminhado ao `ConversationService` existente | HIGH |
| Seleção de entrada | FUNCTIONAL | `BrowserAudioDeviceManager.selectInput` | HIGH |
| Seleção de saída | PARTIAL | `setSinkId` quando o navegador suporta; caso contrário usa saída padrão | HIGH |
| Bluetooth | ARCHITECTURAL-ONLY | o navegador/SO fornece o headset; não há bridge Bluetooth própria | HIGH |
| Streaming de STT/TTS | NOT IMPLEMENTED | adapters recebem/produzem o áudio completo por turno | HIGH |
| VAD | NOT IMPLEMENTED | não há detector de atividade de voz | HIGH |
| Barge-in | NOT IMPLEMENTED | playback não cancela um turno em andamento | HIGH |
| Full-duplex | NOT IMPLEMENTED | fluxo é push-to-talk sequencial | HIGH |
| Wake word | NOT IMPLEMENTED | nenhum detector local/servidor encontrado | HIGH |

## 4. Testes existentes

`backend/tests/tests_unit/test_voice.py` cobre contratos, máquina de estados,
limites de payload, ticket e integração simulada com `FakeSTTAdapter`/`FakeTTSAdapter`.

Esses testes não provam microfone físico, headset Bluetooth, STT NVIDIA real,
TTS real ou reprodução em navegador. O teste físico permanece:

```text
PHYSICAL VOICE TEST: NOT TESTED — ENVIRONMENT BLOCKED
```

## 5. Gaps críticos para Voice V1

1. Provar fluxo real no navegador com microfone autorizado.
2. Provar STT real com áudio `webm` em português brasileiro.
3. Provar TTS real e reprodução no dispositivo de saída selecionado.
4. Medir latência: captura → STT → LLM → TTS → first audio.
5. Definir tratamento de falha/timeout de STT, TTS e ConversationService.
6. Garantir que o áudio bruto não seja persistido nem registrado.
7. Testar desconexão, reconexão e encerramento de sessão.
8. Manter explicitamente fora desta etapa: VAD, streaming verdadeiro,
   barge-in, full-duplex e wake word.

## 6. Critério proposto para Voice V1

```text
LOGIN
  ↓
conversation session owned by user
  ↓
WS ticket accepted
  ↓
microphone capture
  ↓
real STT transcript
  ↓
ConversationService response
  ↓
real TTS audio
  ↓
selected browser output/headset
```

O critério só será `PASS` com runtime real. Unit tests, mocks e build não são
suficientes.

## 7. Próxima ação autorizada

Executar primeiro um smoke E2E real do fluxo acima, preservando o core de
conversa e sem adicionar novos providers ou alterar o modelo de identidade.
Após essa prova, corrigir somente os blockers encontrados no fluxo Voice V1.

```text
FOUNDATION GATE: FAIL — RISK ACCEPTED BY OWNER
VOICE V1 DISCOVERY: COMPLETE
VOICE V1 IMPLEMENTATION: NOT STARTED
```
