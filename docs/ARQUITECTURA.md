# Arquitectura

Dos máquinas, una sola vida digital. Nada de esto es simétrico: cada una tiene su trabajo.

---

## Las máquinas

### `gabo-Inspiron-5720` — el servidor

Es la que **nunca se apaga**. Corre el agente 24/7.

| Servicio | Dónde | Qué hace |
|---|---|---|
| `hermes-gateway` | systemd `--user` | El agente Hermes 24/7: crons, voz, MCP, webapp; **Telegram como relevo** |
| `llama-router` | systemd `--user` | Servidor de modelos local en `127.0.0.1:8004/v1` |
| `kilo-serve` | systemd `--user` | Puerto 44002, el agente de código |
| `ocshepherd`, `ocshepherd-kilo` | systemd `--user` | Escoltas de OpenCode |
| `opencode-serve` | systemd sistema | Puerto 44001 |

- Webapp Hermes: `127.0.0.1:9120`
- Público por Tailscale: `https://gabo-inspiron-5720.tail7deabb.ts.net:9443`
- Login del dashboard: usuario `gabo`, contraseña **en el `.env` del inspiron** (no está aquí)
- `sudo` del inspiron: la clave la tiene el usuario, no se guarda en el repo
- Telegram: **no lo atiende mientras el PC esté encendido**. El PC es el dueño y el inspiron
  toma el bot en ~30 s si el PC cae, por `telegram-failover.timer`. Ver
  [HERMES.md](HERMES.md#dos-nodos-pc-principal-inspiron-de-relevo)

**El gateway arranca con `enabled` + `Linger=yes`**, así sobrevive a reinicios y a logout.
Directorio de trabajo: `/home/gabo`.

### `asus-tuf` — el portátil

Es donde está el usuario. Corre la interfaz.

| Servicio | Qué hace |
|---|---|
| Hyprland 0.57 | Compositor Wayland |
| `hermes-gateway` | El agente Hermes local: **dueño principal de Telegram** y del MCP del dashboard |
| `backup-local.timer` | Copia diaria a `~/backups/` (PC + homelab) |
| `jarvis-sync.timer` | Este repo, cada 5 minutos |
| `study-platform` | Dashboard académico "Bisa" en `127.0.0.1:3100` (Zig + SQLite) |
| Hermes Desktop (oficial) | La ventana de la app, contra el gateway local |
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
- `ssh asus-tuf` también funciona desde el inspiron (`BatchMode`), y es lo que consulta el
  relevo de Telegram.
- Los dos ejecutan el agente. Solo uno atiende Telegram a la vez: el PC manda y el inspiron
  espera; `telegram-failover.sh` (en el inspiron, cada 15 s) hace el relevo.
- El gateway del inspiron escucha en `0.0.0.0`, así que el portátil lo alcanza por Tailscale.

### El dashboard del portátil visto desde el inspiron

El dashboard escucha solo en `127.0.0.1:3100` del portátil. Para que el agente lo use sin
abrir puertos a la LAN, el portátil publica **solo en la tailnet**:

```
inspiron ──Tailscale──► 100.115.62.97:3101 ──tailscale serve (TCP)──► 127.0.0.1:3100
```

```bash
# en el portátil, una vez; persiste tras reiniciar
tailscale serve --bg --tcp=3101 tcp://127.0.0.1:3100
```

Se eligió TCP crudo y no HTTPS por nombre porque el inspiron **no resuelve MagicDNS**
(`/etc/resolv.conf` inmutable) y su `sudo` pide contraseña. El 443 sigue con
`tailscale serve --bg 3100` para el navegador. El MCP del dashboard exige `X-API-Key`;
la clave está en `~/.hermes/.env` del inspiron y el `config.yaml` la referencia como
`${STUDY_PLATFORM_MCP_KEY}`. Detalle en [MCP.md](MCP.md#study-platform--el-dashboard-bisa).

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