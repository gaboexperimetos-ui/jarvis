# jarvis — copia de seguridad de `asus-tuf`

Espejo automático de la configuración y el estado del home de `gabo`.
Se sincroniza con GitHub cada 5 minutos.

## Qué contiene

| Ruta | Qué es |
|---|---|
| `hermes/` | Config del agente Hermes (sin `.env`, sin tokens, sin estado volátil) |
| `opencode/` | Config de OpenCode: agentes, skills, comandos, plugins (sin credenciales) |
| `system/` | `hyprland.conf`, `kitty.conf`, servicios systemd, lspci/lsusb, red, discos |
| `skills/` | Lista de skills de Hermes y ECC |
| `jarvis-sync.sh` | Script de sincronización |
| `sync.log` | Últimas líneas del sync (se trunca a 200) |

## Qué NO se sube (a propósito)

- **Secretos**: `.ssh/`, `.env`, tokens, `auth.json`, `gateway-connections.json`
- **Pesado**: `Descargas/`, `Vídeos/`, `.local/`, `.cache/`, `.npm/`, `android-sdk/`
- **Proyectos**: cada uno es su propio repo (`proyectos/`, `dev/`, `ECC/`)
- **Estado volátil**: bases de datos de sesión, locks, cachés, logs

## Sincronización

```bash
./jarvis-sync.sh          # manual
systemctl --user status jarvis-sync.timer   # temporizador
```

El sync hace `rsync` del home → copia local, `git commit` si hay cambios, y
`git pull --rebase` + `git push` a GitHub.

## Restaurar

```bash
git clone git@github.com:gaboexperimetos-ui/jarvis.git
cp -r jarvis/hermes/* ~/.hermes/
cp -r jarvis/opencode/* ~/.config/opencode/
cp jarvis/system/hyprland.conf ~/.config/hypr/
```
