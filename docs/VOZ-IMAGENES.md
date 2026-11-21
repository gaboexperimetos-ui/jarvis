# Voz e imágenes

Todo gratis, sin claves. Coste: 0 €.

---

## Voz que habla (TTS) — Edge TTS

```yaml
tts:
  provider: "edge"
  edge:
    voice: "es-ES-AlvaroNeural"

voice:
  auto_tts: true
  auto_tts_mode: "voice_only"
```

- **Edge TTS** no necesita clave ni cuenta. Es la razón de haberlo elegido.
- Voz: `es-ES-AlvaroNeural` (español de España, masculina).
- `auto_tts: true` → el agente habla por defecto.
- `auto_tts_mode: voice_only` → responde **solo con voz**, sin texto. Cambiar a
  `text_and_voice` si se quiere también el texto en Telegram.
- Instalación: `hermes pm install --extra edge-tts`.
- Verificado: el proveedor responde `edge` y genera audio.

---

## Oído (STT) — faster-whisper local

```yaml
stt:
  enabled: true
  local:
    model: "base"        # tiny | base | small | medium | large-v3 | turbo
  language: "es"
```

- **faster-whisper** corriendo en local, sin API.
- `language: "es"` forzado. Si se deja en blanco, cae a `HERMES_LOCAL_STT_LANGUAGE` y
  luego a autodetección.
- **Tarda ~21 s por clip** en el inspiron. Es lo que hay sin GPU dedicada al STT.
- Verificado: transcripción correcta en español.
- Instalación: `hermes pm install --extra stt-whisper`.

### Atajo: el contenedor `whisper`

Hay un contenedor escuchando en `127.0.0.1:8451` con dos rutas:

- `/asr` — transcribir
- `/detect-language` — detectar idioma

Existe como alternativa al STT local del agente. Si el STT local va lento, es el camino.

---

## Imágenes — plugin Pollinations

Plugin propio: `plugins/image_gen/pollinations/__init__.py` (en el inspiron).

```yaml
image_gen:
  provider: "pollinations"
```

- Gratis, **sin clave**.
- **No pasar `model` en la URL**: si se pasa, activa el muro de pago (402). Sin `model`
  responde con el modelo `sana`.
- **Límite: 1 imagen cada 45 s por IP.** A veces devuelve 503.
- El plugin reintenta respetando `Retry-After`.
- Genera en `~/.hermes/cache/generated/images/`. Ejemplos reales:
  `pollinations_20261121_092943_3085d9e0.jpg`.
- Verificado por la vía real del agente, no con una llamada a mano.

---

## Vídeo — no hay, y no es un descuido

Descartado porque **no existe opción gratuita**:

- Los ~30 modelos de vídeo de OpenRouter son **de pago**.
- Los modelos `free` de OpenRouter son solo texto.
- Generar vídeo con fal.ai, DeepInfra o xAI necesita clave de pago.

Si algún día se quiere vídeo, hace falta dinero o una clave. No hay truco gratis.

---

## Audio del sistema

Mezcla de altavoz + micro con ffmpeg: `~/.local/bin/hermes-fundido.sh`.

Ojo al estado medido del portátil:

| Elemento | Estado |
|---|---|
| Sink `C-Media 58` | **0 %** de volumen |
| Micro `59` | **MUTED** |

Subir el volumen y quitar el mute:

```bash
pactl set-sink-volume 58 60%
pactl set-source-mute 59 0
```

Sin eso, cualquier grabación sale en silencio.