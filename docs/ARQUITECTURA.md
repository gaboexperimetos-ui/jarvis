# Arquitectura

Dos máquinas, una sola vida digital. Nada de esto es simétrico: cada una tiene su trabajo.

---

## Las máquinas

### `gabo-Inspiron-5720` — el servidor

Es la que **nunca se apaga**. Corre el agente 24/7.

| Servicio | Dónde | Qué hace |
|---|---|---|
| `hermes-gateway` | systemd `--user` | El agente Hermes: Telegram, voz, MCP, crons, webapp |
| `llama-router` | systemd `--user` | Servidor de modelos local en `127.0.0.1:8004/v1` |
| `kilo-serve` | systemd `--user` | Puerto 44002, el agente de código |
| `ocshepherd`, `ocshepherd-kilo` | systemd `--user` | Escoltas de OpenCode |
| `opencode-serve` | systemd sistema | Puerto 44001 |

- Webapp Hermes: `127.0.0.1:9120`
- Público por Tailscale: `https://gabo-inspiron-5720.tail7deabb.ts.net:9443`
- Login del dashboard: usuario `gabo`, contraseña **en el `.env` del inspiron** (no está aquí)
- `sudo` del inspiron: la clave la tiene el usuario, no se guarda en el repo

**El gateway arranca con `enabled` + `Linger=yes`**, así sobrevive a reinicios y a logout.
Directorio de trabajo: `/home/gabo`.

### `asus-tuf` — el portátil

Es donde está el usuario. Corre la interfaz.

| Servicio | Qué hace |
|---|---|
| Hyprland 0.57 | Compositor Wayland |
| `jarvis-sync.timer` | Este repo, cada 5 minutos |
| Hermes Desktop (oficial) | La ventana de la app, apuntando al gateway del inspiron |
| llama.cpp local | `/home/gabo/llama.cpp-new/build-cuda/bin` |

GPU: **RTX 3060 Laptop, 6 GB VRAM**, ~289 GB/s reales de ancho de banda.
RAM: 14 GB. **No caben dos modelos grandes a la vez.**

---

## Cómo se hablan

```
portátil (asus-tuf)  ──SSH──►  inspiron  (clave ~/.ssh/id_ed25519_opencode)
                   ──Tailscale──►  100.115.62.97
```

- `ssh homelab` funciona sin contraseña desde el portátil (clave + `~/.ssh/config`).
- El portátil es **cliente remoto**: no ejecuta el agente, solo lo mira y le habla.
- El gateway del inspiron escucha en `0.0.0.0`, así que el portátil lo alcanza por Tailscale.

### Por qué el modelo local del inspiron se expone en `0.0.0.0:8004`

El agente del inspiron lo usa como fallback 1. Si estuviera solo en `127.0.0.1` el fallback
no lo vería desde fuera. El endpoint que apunta el portátil es `http://100.115.62.97:8004/v1`.

---

## Cadena de modelos

Elegida por **coste cero** y en este orden:

| Orden | Modelo | Dónde | Coste |
|---|---|---|---|
| Principal | `baidu/ernie-5.5-flash-preview:free` | OpenRouter | 0 € |
| Fallback 1 | `deepseek-v4pro` (local) | llama.cpp del inspiron `:8004` | 0 € (paga la luz) |
| Fallback 2 | otro free de OpenRouter | OpenRouter | 0 € |
| Visión | `nvidia/nemotron-3.5-super-vl:free` | OpenRouter | 0 € |

**Presupuesto total: 0 €.** Ningún servicio de pago está configurado.

### El modelo local, medido (no estimado)

| Métrica | Valor |
|---|---|
| Prefill | ~160 tok/s |
| Generación | **75,8 tok/s** (48 tokens en 0,63 s) |
| Streaming | ~13 ms/token |
| Contexto | 204800 |
| KV | `q4_0` siempre (con q8_0 no cabe el contexto) |

Detalles de por qué está así en [`HERMES.md`](HERMES.md#el-modelo-local).

---

## Jerarquía de arranque

1. Enciende el inspiron.
2. `hermes-gateway` y `llama-router` arrancan solos (`enabled` + `Linger=yes`).
3. El agente queda conectado a Telegram y esperando.
4. En el portátil, `hermes-desktop-remote` abre la app apuntando al gateway remoto.
5. `jarvis-sync.timer` mantiene este repo al día cada 5 minutos.

Si el inspiron se apaga, el portátil sigue vivo pero el agente no responde: **el agente
vive en el inspiron, no en el portátil**. Es deliberado.

---

## Decisiones que no se cambian sin motivo

- **La app de escritorio es la oficial de Nous Research.** Compilada desde
  `NousResearch/hermes-agent`, commit `caafe5389a`, v0.23.3. Sin parches locales.
  Se descartó Wine y se descartó la web.
- **`HERMES_DESKTOP_DISABLE_GPU=1`** es obligatorio: sin eso la app muere con
  `FATAL ... GPU process isn't usable. Goodbye.`
- **El sync es bidireccional.** Unidireccional perdía cambios; la versión actual
  resuelve los choques guardando el del PC y avisando.