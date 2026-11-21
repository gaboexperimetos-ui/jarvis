# jarvis — copia de seguridad de `asus-tuf`

Espejo en los dos sentidos de la configuración y el estado del home de `gabo`.
Se sincroniza con GitHub cada 5 minutos.

## Qué contiene

| Ruta | Qué es |
|---|---|
| `hermes/` | Config del agente Hermes: `SOUL.md`, `config.yaml`, preferencias de UI (sin `.env`, sin tokens, sin estado volátil) |
| `opencode/` | Config de OpenCode: agentes, skills, comandos, plugins, MCP (sin credenciales) |
| `system/` | `hyprland.conf`, `kitty.conf`, servicios systemd, lspci/lsusb, red, discos |
| `skills/` | Lista de skills de Hermes y ECC |
| `scripts/` | Utilidades del repo (`seed-opencode-secrets.sh`) |
| `MEJORAS-AGENTE.md` | Auditoría del agente: qué se cambió y qué queda por decidir |
| `jarvis-sync.sh` | Script de sincronización |
| `sync.log` | Últimas 200 líneas del sync |

## Qué NO se sube (a propósito)

- **Secretos**: `.ssh/`, `.env`, tokens, `auth.json`, `gateway-connections.json`,
  `~/.config/opencode/secrets/`. Las claves de los proveedores locales se
  referencian como `{file:...}`, nunca en claro.
- **Pesado**: `Descargas/`, `Vídeos/`, `.local/`, `.cache/`, `.npm/`, `android-sdk/`,
  `node_modules/`, `*.db` (`state.db` incluido)
- **Proyectos**: cada uno es su propio repo (`proyectos/`, `dev/`, `ECC/`)
- **Estado volátil**: bases de datos de sesión, locks, cachés, logs

## Sincronización

```bash
./jarvis-sync.sh          # manual
systemctl --user status jarvis-sync.timer   # temporizador
```

Cada pasada hace, en este orden:

1. `git pull --rebase` — GitHub → repo local.
2. Repo → home, **solo** los ficheros que cambiaron en ese pull.
3. `rsync` del home → repo, con `--delete` y lista de exclusiones.
4. `git commit` + `git push` si hay cambios.

Reglas que aplica el script:

- **Un fichero tocado solo en GitHub** se copia al home. Si el home ya lo había
  cambiado por su cuenta, **no se pisa**: la versión nueva queda en
  `~/.jarvis/pending/` y se avisa en `sync.log`.
- **Cerrojo (`flock`)**: si el timer y una ejecución manual coinciden, la segunda
  sale sin tocar nada.
- **Guardia de secretos**: si lo que se va a commitear contiene algo con pinta de
  clave (`sk-`, `ghp_`, `AKIA`, `xox`, `PRIVATE KEY`), no commitea y lo apunta en
  `sync.log`.

## Restaurar en una máquina nueva

```bash
git clone git@github.com:gaboexperimetos-ui/jarvis.git
cp -r jarvis/hermes/* ~/.hermes/
cp -r jarvis/opencode/* ~/.config/opencode/
cp jarvis/system/hyprland.conf ~/.config/hypr/
./jarvis/scripts/seed-opencode-secrets.sh   # claves de los proveedores locales
```

Después: `hermes doctor` y abrir sesión nueva.
