# MEMORY.md — notas del agente sobre este entorno

## Máquina donde corre el agente
- Host `gabo-Inspiron-5720`, usuario `gabo` (uid 1000), Ubuntu 26.04.1 LTS, kernel 7.0.0-43.
- 4 núcleos, 7,1 GB RAM (~3,2 GB usados), disco `/dev/sda2` 110 GB en `/` (47 GB usados, 58 GB libres).
- IP LAN 192.168.1.65 / 192.168.1.83; Tailscale `100.92.172.48`; tailnet `gruposalas2025@`, 6 dispositivos.
- Zona horaria `America/Lima` (UTC-5). No suspende: tapa ignorada (`HandleLidSwitch=ignore`) y `Linger=yes`.
- Sin GPU. Todo el cómputo es CPU.

## Segunda máquina
- `asus-tuf`, el portátil. Tailscale `100.115.62.97`. SSH por clave: `ssh asus-tuf` desde el inspiron.
- Corre el router llama.cpp en `0.0.0.0:8004` (preset `deepseek-v4pro`, alias `chat`).
- Se apaga a menudo: si el SSH falla, está apagado o sin red. No asumir que está disponible.

## Proyectos en disco (`/home/gabo`)
| Directorio | Qué es |
|---|---|
| `dropkiller-clone` | Backend Next.js/Node + Postgres; espía anuncios FB/TikTok. Container `dropkiller-clone-backend-1` en 8090 |
| `AdLibrarySpy` | Next.js, spy de anuncios. Servicio `adlibraryspy` en 3001 |
| `study-platform` | SQLite con backup diario 03:15 (`backup-db.sh`, retención 14 días) |
| `freellmapi` | Router Node de LLMs free. Servicio `freellmapi` en 3003 |
| `periodic-words` | Rust/Actix en 4000, arranca por crontab `@reboot` |

## Containers Docker (10) y sus puertos
| Contenedor | Puerto host | Servicio |
|---|---|---|
| gitea | 3000 (ssh 2222) | Git |
| vikunja | 3001 | Tareas |
| homepage | 3002 | Dashboard |
| pihole | 8081 (DNS 53) | DNS |
| qbittorrent | 8083 (torrent 6881) | Torrents |
| speedtest-tracker | 8088 | Velocidad de red |
| jellyfin | 8096 | Media |
| whisper | 8451 (interno 9000) | STT |
| adls-postgres | 5432 (localhost) | Postgres |
| dropkiller backend | 8090 | API propia (network_mode host) |

Puertos internos: OpenCode serve 44001, Kilo serve 44002, FreeLLMAPI 8453 (GenOffice MCP), Mikareno MCP, OpenCode serve del sistema.

## Servicios systemd de usuario
`hermes-gateway` (el agente), `ocshepherd` (vigila OpenCode 44001), `kilo-serve` (44002), `ocshepherd-kilo` (vigila Kilo), `genoffice-mcp`, `mikareno-mcp`, `freellmapi`, `adlibraryspy`. Todos `enabled` + `Linger=yes`.

## Herramientas disponibles
`ffmpeg`, `yt-dlp`, `libreoffice`, `imagemagick`, `pdftotext`, `sqlite3` 3.46, `himalaya` 2.2.1 (email CLI, **sin configurar**), `opencode` 1.18.34, `kilo` 7.8.15, `ocshepherd` 0.2.5, `docker`, `tailscale`.

## Proveedores LLM del agente
| Proveedor | Fuente |
|---|---|
| `openrouter` | OpenRouter (saldo libre ~$0,69; modelo por defecto `baidu/ernie-5.5-flash-preview:free`) |
| `opencode-free` | OpenCode Zen free vía HTTP (11 modelos) |
| `opencode-free-acp` | CLI real de OpenCode sobre ACP (7 modelos curated) |
| `llamacpp` | Router local del portátil (`deepseek-v4pro`) — fallback |

Cadena de fallback: primario → `llamacpp` → `openrouter free`. La compresión de contexto y la visión usan modelos free.

## Convenciones de este entorno
- `terminal.cwd` se ignora en backend local: el cwd lo fija el drop-in `WorkingDirectory=/home/gabo`.
- El nombre MagicDNS `asus-tuf.ts.gruposalas2025.net` **no resuelve** aquí. Usar la IP `100.115.62.97`.
- Los servidores 44001/44002 escuchan solo en localhost y sin contraseña.
- `/tmp/opencode` se vacía en cada reinicio: nada persistente ahí.
