# Voz, oído y visión

Todo gratis, sin claves de pago. Coste: 0 €.

Verificado el 2026-11-22 en los dos nodos (PC `asus-tuf` e inspiron 24/7) con el intérprete
real que usa el gateway, no con un Python cualquiera.

---

## Voz que habla (TTS) — Edge TTS

```yaml
tts:
  provider: "edge"
  edge:
    voice: "es-ES-AlvaroNeural"

voice:
  auto_tts: true
  auto_tts_mode: "text_and_voice"
```

- **Edge TTS** no necesita clave ni cuenta. Es la razón de haberlo elegido.
- Voz: `es-ES-AlvaroNeural` (español de España, masculina).
- `auto_tts: true` → el agente manda nota de voz además del texto.
- `auto_tts_mode`: `text_and_voice` (texto + voz) o `voice_only` (solo voz). Los dos nodos
  quedaron en `text_and_voice` para que se lea y se escuche.
- Instalación: `hermes pm install --extra edge-tts`.
- Verificado: generó un MP3 de 38 880 bytes y de 33 120 bytes en el inspiron.

---

## Oído (STT) — faster-whisper local

```yaml
stt:
  enabled: true
  local:
    model: "base"        # tiny | base | small | medium | large-v3 | turbo
  language: "es"
```

- **faster-whisper** en local, sin API. Modelo `base`, CPU, `int8`.
- `language: "es"` forzado en los dos nodos.
- Instalación: `hermes pm install --extra stt-whisper` (arrastra `ctranslate2` y `av`).
- Verificado de punta a punta: Edge TTS generó «Hola señor. Prueba de oído y voz…» y
  faster-whisper lo transcribió en español («oído y voce» en el inspiron: error menor del
  modelo `base`). Si se quiere más precisión, subir a `small`; cuesta más RAM y tiempo.
- El modelo se descarga de Hugging Face la primera vez; ya está precalentado en ambos nodos.

### Alternativa: contenedor `whisper` (solo inspiron)

En el inspiron hay un contenedor escuchando en `127.0.0.1:8451` (y en la tailnet) con:

- `/asr` — transcribir
- `/detect-language` — detectar idioma

En el PC **no** existe. El STT local es el camino normal; el contenedor es el plan B.

---

## Visión (ver imágenes)

El modelo principal (`nvidia/nemotron-3-ultra-550b-a55b:free`) es **solo texto**. La imagen
entra por el router auxiliar de visión:

```yaml
auxiliary:
  free_only: true
  vision:
    provider: "openrouter"
    model: "nvidia/nemotron-3.5-super-vl:free"
    timeout: 60
```

- Modelo **gratis** de OpenRouter con entrada de imagen. `free_only: true` impide que caiga
  en un modelo de pago si el free falla.
- La herramienta es `vision_analyze` (y `video_analyze`, pero no hay vídeo gratis).
- Verificado por la vía real del agente: `hermes -z "Usa vision_analyze con /tmp/vision-test.png…"`
  devolvió `4271`, el número de la imagen.
- Aviso: los modelos `:free` de OpenRouter se limitan por IP y a veces devuelven 429. El
  reintento lo maneja Hermes; si insiste, es saturación del proveedor, no configuración.
- Para una foto que llega por Telegram o WhatsApp no hay que hacer nada: el adaptador la baja,
  la normaliza y llama a `vision_analyze`.

---

## Imágenes que genera (opcional)

Plugin incluido en el propio árbol de Hermes:
`~/.hermes/hermes-agent/plugins/image_gen/pollinations/__init__.py`.

```yaml
image_gen:
  provider: "pollinations"
```

- Gratis, **sin clave**.
- **No pasar `model` en la URL**: si se pasa, activa el muro de pago (402). Sin `model`
  responde con `sana`.
- **Límite: 1 imagen cada 45 s por IP.** A veces devuelve 503; el plugin reintenta respetando
  `Retry-After`.
- Genera en `~/.hermes/cache/generated/images/`.

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

Sin eso, cualquier grabación sale en silencio. (Esto afecta al micro del PC, no a las notas
de voz que llegan por Telegram/WhatsApp.)

---

## Dónde quedan instalados los extras

`hermes pm install` crea un entorno versionado y el lanzador elige el más reciente:

```
~/.hermes/installs/<id>/environments/<hash>/venv/lib/python3.14/site-packages/
```

Comprobar con el intérprete real, no con `python3` del sistema:

```bash
PY=/home/gabo/.hermes/tools/python-3.14.9+20261021-linux-x64/bin/python3
HERMES_HOME=$HOME/.hermes "$PY" -I -c '
import sys; sys.path.insert(0, "/home/gabo/.hermes/hermes-agent")
import hermes_bootstrap, importlib.util as u
for m in ("faster_whisper","edge_tts","ctranslate2","av"):
    print(m, bool(u.find_spec(m)))'
```

Si algo sale `False`, reinstalar con `hermes pm install --extra <nombre>` y reiniciar el
gateway (`systemctl --user restart hermes-gateway`).
