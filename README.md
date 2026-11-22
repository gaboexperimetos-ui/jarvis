# jarvis — copia de seguridad viva de `asus-tuf`

Espejo automático **bidireccional** del home de `gabo` contra GitHub.
Cada 5 minutos baja lo que cambió en GitHub, lo aplica al PC, sube lo que cambió en el PC,
y deja constancia de cualquier choque.

Además hay **copia local en el PC y en el homelab**, todos los días: GitHub es la tercera
copia, la remota. Ver [`docs/COPIAS.md`](docs/COPIAS.md).

**Repo:** `git@github.com:gaboexperimetos-ui/jarvis.git` · rama `main`

---

## Estado verificado (2026-11-21)

| Cosa | Valor |
|---|---|
| Repo local | `/home/gabo/jarvis` |
| Ficheros versionados | 1460 |
| Temporizador sync | `jarvis-sync.timer` (systemd `--user`), activo, cada 5 min |
| Copia local | `backup-local.timer`, activo, diaria a las 04:00 (PC + homelab) |
| Última pasada | ver `jarvis/sync.log` y `~/backups/backup.log` |
| Secretos versionados | **0** (verificado por búsqueda) |
| Cambios pendientes | ninguno |

---

## Documentación

| Documento | Qué cuenta |
|---|---|
| [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Las dos máquinas, la red, qué corre dónde y por qué |
| [`docs/HERMES.md`](docs/HERMES.md) | El agente Hermes: modelo, gateway, crons, memoria, plugins |
| [`docs/VOZ-IMAGENES.md`](docs/VOZ-IMAGENES.md) | TTS, STT e imágenes, con la configuración real y los límites |
| [`docs/MCP.md`](docs/MCP.md) | Todos los servidores MCP, los que funcionan y los que piden credenciales |
| [`docs/SINCRONIZACION.md`](docs/SINCRONIZACION.md) | Cómo funciona el sync, qué se restaura, cómo resuelve conflictos |
| [`docs/COPIAS.md`](docs/COPIAS.md) | Las tres copias: PC, homelab y GitHub; qué guarda cada una y cómo restaurar |
| [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) | Qué se excluye y por qué; cómo se revisó |
| [`docs/RESTAURAR.md`](docs/RESTAURAR.md) | Cómo reconstruir el portátil desde cero con este repo |
| [`docs/PENDIENTES.md`](docs/PENDIENTES.md) | Lo que falta y qué necesita de cada servicio |
| [`docs/HANDOFF-AGENTE.md`](docs/HANDOFF-AGENTE.md) | Encargo para el otro agente que revisa y propone cambios |

Y en la raíz, [`AGENTS.md`](AGENTS.md): las reglas que debe seguir cualquier agente que trabaje aquí.

---

## Qué hay dentro

| Ruta | Contenido |
|---|---|
| `hermes/` | Config del agente Hermes: `config.yaml`, `SOUL.md`, `ui-preferences.json` |
| `opencode/` | Agentes, skills, comandos, plugins y `opencode.json` de OpenCode |
| `system/` | `hyprland.conf`, `kitty.conf`, `pacman.conf`, servicios systemd, lspci/lsusb |
| `skills/` | Inventario de skills de Hermes |
| `jarvis-sync.sh` | El script de sincronización |
| `backup-local.sh` | Copia local diaria al PC y al homelab |
| `healthcheck.sh` | Revisión de salud del sistema, solo lectura |
| `sync.log` | Últimas 200 líneas del sync |

## Qué NO está, a propósito

- **Secretos**: `.ssh/`, `.env`, tokens, `auth.json`, `gateway-connections.json`. Ni una clave.
- **Pesado regenerable**: `Descargas/` (31 GB), `.local/` (22 GB), `olliecode-sandbox/` (16 GB),
  `Vídeos/`, `.cache/`, `.npm/`, `android-sdk/`.
- **Proyectos**: `proyectos/`, `dev/`, `ECC/`, `freellmapi/` y los 21 repos con `.git` propio.
  Cada uno es su repo; meterlos aquí los rompería.
- **Volátil**: locks, caches, logs, bases de datos de sesión, `Singleton*` de Chromium.

---

## Uso diario

```bash
./jarvis-sync.sh                  # forzar una pasada a GitHub
systemctl --user start backup-local.service   # copia local ahora (PC + homelab)
./healthcheck.sh                  # revisión de salud, solo lectura
tail -f sync.log                  # ver qué hizo el sync
cat ~/backups/backup.log          # ver qué hizo la copia local
systemctl --user list-timers jarvis-sync.timer backup-local.timer
```

`healthcheck.sh` no cambia nada: comprueba sync, temporizador, secretos, disco, servicios
fallidos, las copias locales, y en el inspiron el gateway, los límites de memoria y los MCP
activos. Termina con un recuento (`24 OK · 0 avisos · 0 fallos`).

Si dos sitios tocan el mismo fichero, el del PC manda y el de GitHub queda en
`~/.jarvis/pending/` con marca de tiempo. Se avisa en el log como `CONFLICTO`.