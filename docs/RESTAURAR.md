# Restaurar

Cómo reconstruir el portátil desde cero usando este repo. Probado paso a paso en la cabeza;
si algo falla, el orden importa.

---

## 0. Requisitos

```bash
git clone git@github.com:gaboexperimetos-ui/jarvis.git ~/jarvis
cd ~/jarvis
```

Funciona con SSH si la clave está en `~/.ssh/`; si no, con HTTPS y un token.

---

## 1. Configuración de Hermes

```bash
mkdir -p ~/.hermes
cp -r ~/jarvis/hermes/. ~/.hermes/
chmod 600 ~/.hermes/config.yaml 2>/dev/null || true
```

Lo que se restaura: `config.yaml` (plantilla), `SOUL.md` (personalidad), `ui-preferences.json`.

Lo que **no** se restaura y hay que rehacer:

- `~/.hermes/.env` — tokens y claves. Pedirlos al usuario.
- `~/.hermes/memories/` — memoria del agente. Si no se restaura, el agente arranca sin contexto.
- `~/.hermes/skills/` — las skills instaladas. Se reinstalan con `hermes pm install`.
- `~/.hermes/hermes-agent/` — el código de Hermes. Se reinstala con `install.sh`.
- `~/.hermes/cron/` — los crons. Se recrean (`resumen-diario`, `seguimiento-mikareno`).

> Este es el punto débil del respaldo: la memoria y las skills no están. Si se quiere
> blindar, hay que añadirlas al repo **sin los secretos** y revisadas a mano.

---

## 2. Configuración de OpenCode

```bash
mkdir -p ~/.config/opencode
cp -r ~/jarvis/opencode/. ~/.config/opencode/
```

Eso trae `opencode.json` (con los 9 MCP habilitados), agentes, skills, comandos, plugins y
hooks. Las credenciales **no** están: cada MCP que las necesite hay que configurarlo aparte.

---

## 3. Hyprland y kitty

```bash
mkdir -p ~/.config/hypr ~/.config/kitty
cp ~/jarvis/system/hyprland.conf ~/.config/hypr/hyprland.conf
cp ~/jarvis/system/kitty.conf   ~/.config/kitty/kitty.conf
hyprctl reload
```

---

## 4. Servicios systemd

`system/enabled-services.txt` es el inventario. Los unitarios en sí **no están** en el repo
(se excluyó `.config/systemd/`). Hay que recrearlos o copiarlos del inspiron:

```bash
scp homelab:~/.config/systemd/user/{hermes-gateway,kilo-serve,ocshepherd,ocshepherd-kilo}.service ~/.config/systemd/user/
systemctl --user daemon-reload
```

### El dashboard Bisa y su reenvío por Tailscale

El dashboard es un servicio **del portátil** (`study-platform`, `127.0.0.1:3100`). El agente
del inspiron lo usa por MCP. Al reinstalar o reiniciar Tailscale hay que republicar el
reenvío TCP (el HTTPS del 443 para el navegador es aparte):

```bash
tailscale serve --bg --tcp=3101 tcp://127.0.0.1:3100   # MCP del agente
tailscale serve --bg 3100                              # navegador por nombre
tailscale serve status
```

Y en el inspiron, la entrada `study-platform` de `~/.hermes/config.yaml` apunta a
`http://100.115.62.97:3101/mcp` con `X-API-Key: "${STUDY_PLATFORM_MCP_KEY}"`; la clave va en
`~/.hermes/.env`. Ver [MCP.md](MCP.md#study-platform--el-dashboard-bisa).

---

## 5. El agente

```bash
# en el inspiron, que es donde vive de verdad
ssh homelab 'systemctl --user status hermes-gateway'
```

Si el inspiron está vivo, **el portátil no necesita nada más**: la app de escritorio apunta
allí por Tailscale.

---

## 6. La app de escritorio

```bash
# binario oficial (compilado)
~/.hermes/hermes-agent/apps/desktop/release/linux-unpacked/Hermes

# lanzador
~/.local/bin/hermes-desktop-remote
```

Si falta el lanzador, está documentado entero en [`HERMES.md`](HERMES.md#la-app-de-escritorio).
Si falta el binario, hay que compilar la app oficial desde el repo de Nous.

---

## 7. Verificar

```bash
systemctl --user is-active jarvis-sync.timer
systemctl --user is-enabled hermes-gateway 2>/dev/null || ssh homelab 'systemctl --user is-enabled hermes-gateway'
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8004/v1/models
```

Y la prueba de fuego del sync:

```bash
~/jarvis/jarvis-sync.sh
grep -E "restaurado|CONFLICTO|push" ~/jarvis/sync.log
```

---

## Lo que este respaldo NO cubre

Conviene decirlo claro:

| Cosa | Por qué no está |
|---|---|
| `.env` y tokens | secretos, no se versionan |
| Memoria del agente (`memories/`) | no se añadió al repo |
| Skills instaladas | se reinstalan, no se copian |
| Código de Hermes | se reinstala con `install.sh` |
| Proyectos (`proyectos/`, `dev/`, `ECC/`) | cada uno es su repo |
| Descargas, vídeos, cachés | regenerable o irrelevante |
| `~/.ssh/` | secretos |

Es un respaldo de **configuración y de decisiones**, no de datos personales.