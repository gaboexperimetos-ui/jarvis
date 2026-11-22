# El agente Hermes

Hermes es el agente 24/7. Vive en el inspiron (`~/.hermes`), se controla por Telegram,
habla, oye, genera imágenes y tiene MCPs. Esta es su ficha completa.

- **Versión:** v0.23.3 (commit `caafe5389a` de `NousResearch/hermes-agent`)
- **Instalación oficial:** `install.sh` + `hermes desktop`. No hay `.deb`, `.rpm` ni AppImage.
- **Directorio de trabajo:** `/home/gabo`
- **Configuración real:** `~/.hermes/config.yaml` **en el inspiron** (2521 líneas)

> **Ojo:** el `hermes/config.yaml` que hay en este repo es el del **portátil**, que es casi
> todo plantilla comentada. El bueno, el que tiene la voz, los MCP y el dashboard,
> está en el inspiron y **no se versiona aquí** porque lleva contraseñas. Para verlo:
> `ssh homelab 'grep -A4 "^mcp_servers:" ~/.hermes/config.yaml'`

---

## Arrancarlo

```bash
systemctl --user status hermes-gateway     # estado
systemctl --user restart hermes-gateway    # reiniciar (tarda ~35 s en quedar listo)
journalctl --user -u hermes-gateway -n 50  # últimas líneas
```

`hermes "texto"` **no funciona**. Hay que usar `hermes -z "texto"`.

---

## Modelo

```yaml
model:
  default: "baidu/ernie-5.5-flash-preview:free"
  provider: "openrouter"
  supports_vision: false
  base_url: "https://openrouter.ai/api/v1"
  api_mode: chat_completions
```

- `supports_vision: false` en el principal, pero hay un modelo de visión aparte:
  `nvidia/nemotron-3.5-super-vl:free`, verificado.
- OpenRouter puede devolver **429** (rate limit) al probar en caliente. Reintentar o usar fallback.

### Aprobaciones: desactivadas

```yaml
approvals:
  mode: false
  timeout: 300
```

El usuario quiere que el agente **actúe sin preguntar** y le avise después. Las aprobaciones
de código se delegan a Kilo/OpenCode vía la skill `coding-orchestrator`.

---

## Personalidad

`~/.hermes/SOUL.md`. Trato de **«maestro» o «señor»**, de usted, en español, directo, sin
relleno, respuestas cortas. Interpreta las erratas del usuario en vez de corregirlas.
Avisa de todo lo que hace.

La sección de voz e imágenes del `SOUL.md` dice: hay TTS e imágenes, **no hay vídeo**, y el
límite de Pollinations es 1 imagen cada 45 s por IP.

---

## Memoria

`~/.hermes/memories/`

| Fichero | Contenido |
|---|---|
| `MEMORY.md` | Mapa del entorno: máquinas, servicios, puertos, decisiones |
| `USER.md` | Perfil del usuario: trato, preferencias, proyectos |

La compresión de contexto está afinada para que la memoria sobreviva a sesiones largas.

### Límites (2026-11-21)

Los de fábrica eran demasiado pequeños y el agente avisaba en cada arranque:

```
WARNING tools.memory_tool: USER.md exceeds its char limit on load: 3797/1375 chars.
WARNING tools.memory_tool: MEMORY.md exceeds its char limit on load: 4664/2200 chars.
```

Con el aviso, **el agente no puede guardar nada nuevo** hasta bajar del límite. Se arregló
subiendo los límites en `~/.hermes/config.yaml`:

```yaml
memory:
  memory_char_limit: 6000   # antes 2200
  user_char_limit:   4500   # antes 1375
```

Y quitando el bloque de `MEMORY.md` que duplicaba `USER.md`. Ahora:
`MEMORY.md` 3387 caracteres, `USER.md` 3797 — los dos con margen.

**Si vuelve a pasar, subir el límite antes de recortar contenido:** son ~4.000 tokens en total
sobre un contexto de 200k, no es un problema de presupuesto.

---

## Crons

`~/.hermes/cron/jobs.json` — 2 trabajos, los dos activos:

| id | Expresión | Nombre | Qué hace |
|---|---|---|---|
| `cab0d39e08f0` | `0 9 * * *` | `resumen-diario` | Resumen a las 9:00 |
| `607bbfcfd5b5` | `0 15 * * 1-5` | `seguimiento-mikareno` | Seguimiento de Mikareno, L-V a las 15:00 |

Estado: los dos en `ok`.

---

## Plugins instalados

```
oc-free-provider
opencode-free-acp
opencode-shepherd   (+ comando ocshepherd)
pollinations        (imágenes)
edge-tts            (voz)
stt-whisper         (oído)
```

Instalación de extras:

```bash
hermes pm install --extra edge-tts
hermes pm install --extra stt-whisper
```

---

## Puertos y servicios que toca

| Puerto | Servicio | Máquina |
|---|---|---|
| 8004 | llama.cpp router (`/v1`) | inspiron, `0.0.0.0` |
| 9120 | Webapp / dashboard Hermes | inspiron, `127.0.0.1` |
| 9443 | Webapp público por Tailscale | inspiron |
| 44001 | `opencode-serve` | inspiron |
| 44002 | `kilo-serve` | inspiron |
| 8451 | contenedor `whisper` (`/asr`, `/detect-language`) | inspiron |

---

## El modelo local

Router `deepseek-v4pro` en `/home/gabo/models/router.ini`, servicio `llama-router`.

```bash
systemctl --user status llama-router
curl "http://127.0.0.1:8004/metrics?model=deepseek-v4pro"
```

Lo que hay que saber antes de tocarlo:

- **`batch-size = 512` / `ubatch-size = 512`**: subió el prefill de 1520 a 2894 tok/s (+90 %)
  sin tocar generación ni contexto. Bajar a 32 parte la velocidad de prefill.
- **`ExecStart` del servicio NO debe llevar `-b` / `-ub`**: el CLI pisa el preset y anula el cambio.
- **KV siempre `q4_0`**: con `q8_0` no cabe el contexto.
- **`top-p = 0.0`** es deliberado. El valor neutro (1.0) cuesta una pasada sobre 248k logits y
  duplicaba el uso de CPU (14,7 → 6,9 ms/token) sin ganar velocidad. La calidad la controlan
  `top-k 50` y `temp 0.4`.
- **CUDA parcheado para no quemar CPU**: `ggml/src/ggml-cuda/ggml-cuda.cu` pide
  `cudaDeviceScheduleBlockingSync`. Sin el parche, `cudaStreamSynchronize` giraba un core
  entero (100 %). Con el parche: ~14 % de un core. **Si recompilas desde cero o haces
  `git checkout` de ese archivo, el parche se pierde y vuelve el 100 %.**
- **`--sleep-idle-seconds 3600`**: no descarga el modelo, así el caché de prompt sobrevive y
  los mensajes van a 0,4 s.
- El pensamiento está apagado (`enable_thinking:false`). No reactivarlo sin medir el coste.
- La generación **cae al llenar el contexto**: 78 tok/s a 4k, 47 a 28k. Cada token relee todo el KV.
- Ancho de banda medido: **314 GB/s** (copia D2D), 336 teóricos. Reloj de memoria a 7001 MHz.
  Techo realista ~90-95 tok/s sin cambiar de GPU.

### Qué hay en disco

```
/opt/models/qwen3.5-4b-dsv4-unc-gguf/DeepSeek-V4-Pro-Qwen3.5-4B-UNCENSORED-heretic.Q4_K_M.gguf  (2,78 GB)
```

Borrados a propósito y **no hay que volver a descargarlos sin que se pida**: Qwen3.8
(daba respuestas raras), MiMo oficial y heretic, Ornith, Qwen2.5-coder, Spark, LFM3 Q4.

---

## La app de escritorio

Binario oficial compilado:

```
~/.hermes/hermes-agent/apps/desktop/release/linux-unpacked/Hermes
```

Lanzador: `~/.local/bin/hermes-desktop-remote`. Entrada `.desktop` en
`~/.local/share/applications/`, con `StartupWMClass=com.nousresearch.hermes`.

El lanzador hace, en orden:

1. Exporta `HERMES_DESKTOP_REMOTE_URL` (Tailscale del inspiron) y `_REMOTE_TOKEN`
   (lo lee de `~/.hermes/.desktop-token` del inspiron por SSH).
2. `HERMES_DESKTOP_IGNORE_EXISTING=1` — no arranca backend local.
3. `HERMES_DESKTOP_DISABLE_GPU=1` — imprescindible o muere.
4. Regla de Hyprland: `workspace="4 silent"` — abre en el ws 4 **sin robar foco**.
5. Arranca con `--ozone-platform=wayland --disable-setuid-sandbox --disable-gpu`.

### Temas de la app

- Claro y oscuro integrados.
- **Ctrl+K → «Instalar tema…»** importa temas del VS Code Marketplace.
- Temas propios en `localStorage` bajo la clave `hermes-desktop-user-themes-v1`.
- Modo simple/avanzado en la clave `interface-mode`.

### El registro de conexiones

`~/.hermes/gateway-connections.json` (v2) tiene dos entradas: `primary: inspiron` (remoto,
token en claro) y `local`. Con el primario remoto el arranque es `Remote Hermes backend is ready`.

**La app reescribe `connection.json` a `mode local`** cada vez que arranca. El primario del
registro es lo que vale. Si algún día el arranque dice `service_identity_unverified`, es que
está usando el gateway local: revisar el registro.

---

## Configuración de usuario de Electron

```
~/.config/Hermes/    connection.json, active-profile.json
~/.hermes/           ui-preferences.json
```

`ui-preferences.json` tiene `generation`/`revision` y valores como
`hermes.desktop.showAllProfiles: "true"`. Es el fichero que el sync restaura al home, y
conviene tratarlo con cuidado: si GitHub trae una versión vieja, la app la pisa.

---

## Audio: el cuello de botella del portátil

Estado medido:

- Sink `C-Media 58` al **0 %**
- Micro `59` **MUTED**

Por eso cualquier captura de audio sale en silencio salvo que se suba el volumen. Está
documentado y se puede arreglar:

```bash
pactl set-sink-volume 58 60%
pactl set-source-mute 59 0
```

`~/.local/bin/hermes-fundido.sh` mezcla el monitor del altavoz con el micrófono usando
ffmpeg. Probado y funciona.

---

## Estado de los crons y verificaciones

Regla de oro del proyecto, aprendida a golpes: **no afirmar nada sin leerlo en la conversación.**

```bash
ls          # el fichero existe
cat         # su contenido
systemctl   # el servicio corre
curl        # el endpoint responde
```