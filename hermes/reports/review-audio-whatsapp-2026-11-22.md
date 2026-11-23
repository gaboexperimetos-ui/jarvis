# Revisión: audio, voz y acceso a WhatsApp de Hermes

Fecha: 2026-11-22 22:2x (America/Guayaquil)
Ámbito: `~/.hermes` (Hermes), puente Baileys, plugin `whatsapp-triage`, `study-platform` (NOVA) sin cambios.

## Resumen de los 5 puntos

| # | Queja | Causa real | Estado |
|---|-------|-----------|--------|
| 1 | No entiende mis audios | STT local en GPU: `CUDA failed with error out of memory` (GPU de 6 GB ocupada por el modelo local). El audio no se transcribía. | **Corregido**: STT forzado a CPU + int8; transcripción verificada. |
| 2 | Manda audio siempre + texto adicional | `voice.auto_tts: true` y `auto_tts_mode: text_and_voice` (valor **inválido**, caía a `all`): cada respuesta generaba nota de voz **y** texto. | **Corregido**: `auto_tts: false` (solo texto). |
| 3 | La voz es muy robótica | Voz Edge `es-ES-AlvaroNeural` (España). | **Mitigado**: audio automático apagado; si se reactiva, voz `es-EC-LuisNeural` (Ecuador). |
| 4 | Dice no tener acceso a mi WhatsApp | El puente usa **Baileys**, que no persiste historial (`createBoundedMessageStore(512)`, en memoria). No existe lista de chats ni historial del teléfono. Hermes solo ve lo que llega en vivo. | **Aclarado + acceso real**: instrucciones en `SOUL.md` y buscador del registro `wa-recent.py`. |
| 5 | Revisión completa | — | Este documento. |

## Detalle técnico

### 1. Audios (STT)
- Log: `ERROR tools.transcription_tools: Local transcription failed: CUDA failed with error out of memory`.
- `faster-whisper 1.2.1` está instalado en el venv gestionado `installs/84b19cb788e60403/environments/9606d827cd4b49858a6ef6daa23bc9f3/venv`.
- La RTX 3060 (6 GB) no tiene margen con el modelo local cargado; el intento de cargar Whisper en CUDA fallaba.
- Cambio en `config.yaml`:
  ```yaml
  stt:
    enabled: true
    provider: "local"
    language: "es"
    local:
      model: "base"
      device: "cpu"
      compute_type: "int8"
  ```
- Verificación con el propio código de Hermes (`tools.transcription_tools.transcribe_audio`) sobre un audio español generado:
  - `success: True`, `provider: local`
  - Texto: «Hola, esto es una prueba de transcripción en español. Recuerda entregar los deberes de matemáticas el viernes.»
- Coste: 0 €, sin nube.

### 2 y 3. Audio saliente y voz
- Antes:
  ```yaml
  tts:
    provider: edge
    edge:
      voice: es-ES-AlvaroNeural
  voice:
    auto_tts: true
    auto_tts_mode: text_and_voice   # inválido -> warning y fallback a "all"
  ```
- El gateway registraba: `WARNING gateway.run: Invalid voice.auto_tts_mode='text_and_voice'; falling back to 'all'`.
- Valores válidos: `all` (audio con cada respuesta) y `voice_only` (audio solo tras audio entrante). **No existe** un modo «solo audio»: cuando hay TTS, el texto también se envía.
- Ahora:
  ```yaml
  tts:
    provider: edge
    edge:
      voice: es-EC-LuisNeural
  voice:
    auto_tts: false
    auto_tts_mode: voice_only
  ```
- Resultado: respuestas **solo en texto**, sin nota de voz ni duplicado. Si más adelante quiere voz, hay dos caminos:
  - `auto_tts: true` + `auto_tts_mode: voice_only` → voz solo cuando usted manda audio (seguirá acompañada de texto).
  - Pedir la nota de voz explícitamente en el chat.
- Voz `es-EC-LuisNeural` verificada (genera MP3 correctamente). Alternativa femenina: `es-EC-AndreaNeural`.

### 4. «No tengo acceso a mi WhatsApp»
- El puente (`scripts/whatsapp-bridge/bridge.js`) usa **Baileys** (`makeWASocket`), no whatsapp-web.js. Baileys es un socket en vivo: **no guarda historial** ni expone la lista de chats del teléfono. `messageStore` es un buffer en memoria de 512 mensajes.
- Conclusión honesta: Hermes **no puede** leer conversaciones anteriores ni la lista de chats del teléfono. Sí recibe en vivo todo lo admitido (DMs y grupos) y lo registra.
- Lo que se añadió para que el agente responda con la verdad y sea útil:
  - `~/.hermes/logs/whatsapp-inbox.jsonl`: registro persistente de cada mensaje admitido (lo escribe el plugin `whatsapp-triage`).
  - `~/.hermes/scripts/wa-recent.py`: buscador de solo lectura.
    - `wa-recent.py --chats`
    - `wa-recent.py --chat 10mo --since 24h --limit 50`
    - `wa-recent.py --since 7d --json`
  - `SOUL.md`: sección «WhatsApp (acceso real, verificado)» con estas capacidades y sus límites.
- Nota: en modo `bot`, el puente descarta los mensajes que usted envía desde su propio teléfono (`FORWARD_OWNER_MESSAGES`), así que el registro contiene lo **recibido**, no lo que usted escribe.

## Cambios aplicados

- `~/.hermes/config.yaml`: `stt.provider`, `stt.local.device`, `stt.local.compute_type`, `tts.edge.voice`, `voice.auto_tts`, `voice.auto_tts_mode`.
  - Respaldo: `config.yaml.bak-audio-20261122-222058`.
- `~/.hermes/SOUL.md`: sección de WhatsApp.
- `~/.hermes/scripts/wa-recent.py`: nuevo (solo lectura, ejecutable).
- Sin cambios en `study-platform` ni en la base de datos de NOVA.

## Verificación ejecutada

- `systemctl --user is-active hermes-gateway` → `active`.
- `journalctl` tras reinicio: `[whatsapp-triage] plugin registrado`, `[Whatsapp] Bridge ready (status: connected)`, **sin** warnings de `auto_tts_mode`.
- Transcripción de prueba: `success: True` con texto correcto.
- `wa-recent.py --chats` y `--chat 10mo` devuelven los mensajes del registro.
- Puente con `WHATSAPP_ALLOWED_USERS=*`, `WHATSAPP_DM_POLICY=open`, `WHATSAPP_GROUP_POLICY=open`.

## Límites y riesgos

- Historial anterior a la instalación del plugin: **no disponible**. Solo existe desde que se activó el registro (2026-11-22 ~21:37).
- No hay lista de chats del teléfono ni estados/no leídos.
- El modo «solo audio» no existe en Hermes; si se activa TTS, el texto también se envía.
- El STT en CPU es más lento que en GPU, pero no compite con el modelo local ni falla por memoria. Si se libera VRAM, se puede volver a `device: auto`.
- Cambiar la voz no garantiza que deje de parecer sintética: Edge TTS es neuronal, pero no es una voz humana clonada. Para una voz clonada haría falta otro proveedor (coste > 0).

## Recomendaciones

1. Usar el registro (`wa-recent.py`) para preguntas sobre lo recibido; asumir que el historial previo no existe.
2. Si quiere voz solo al mandar audio: `auto_tts: true` + `voice_only` y probar `es-EC-AndreaNeural` frente a `es-EC-LuisNeural`.
3. Si más adelante quiere historial completo, habría que cambiar de estrategia (por ejemplo, capturar y persistir los mensajes en el puente desde ahora, o usar la API oficial de WhatsApp Business con su propio historial). Baileys no lo da.
4. Mantener el modelo local y Whisper fuera de la GPU a la vez en esta máquina de 6 GB.
