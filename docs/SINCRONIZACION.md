# Sincronización

El repo es **bidireccional**. Esto es la mecánica exacta, para que nadie la "mejore" a ciegas.

---

## El temporizador

`~/.config/systemd/user/jarvis-sync.timer` → `jarvis-sync.service` → `jarvis-sync.sh`

```ini
[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=30s
Persistent=true
```

`Persistent=true` significa que si el portátil estaba apagado, al arrancar se hace la pasada
perdida. Comprobar:

```bash
systemctl --user list-timers jarvis-sync.timer
systemctl --user status jarvis-sync.service
```

---

## Las cuatro fases de cada pasada

### 1. GitHub → repo local

```bash
git pull --rebase --autostash origin "$BRANCH"
```

Si falla, **no toca el home** y sale. Es la regla de seguridad más importante: ante la duda,
no romper nada.

### 2. Repo → home

Solo se restaura **lo que cambió en el pull**, no todo. Se calcula con:

```bash
CHANGED="$(git diff --name-only ORIG_HEAD HEAD)"
```

> `ORIG_HEAD` es el HEAD de antes del pull. Ojo: se usó `HEAD@{1}` en la primera versión y
> fallaba, porque `git pull --rebase` no actualiza la reflog de esa forma y **todo parecía
> conflicto**. Verificado con pruebas reales.

Mapa repo → home:

| En el repo | En el home |
|---|---|
| `hermes/` | `~/.hermes/` |
| `opencode/` | `~/.config/opencode/` |
| `skills/ecc-skills/` | `~/ECC/skills/` |
| `system/hyprland.conf` | `~/.config/hypr/hyprland.conf` |
| `system/kitty.conf` | `~/.config/kitty/kitty.conf` |

`system/` es **solo lectura**: se sube como información de la máquina, pero no se restaura.
`uname.txt` o `lspci.txt` no van a ningún sitio.

### 3. Home → repo

`rsync -a --delete` con las exclusiones de secretos, cachés y estado volátil.

### 4. Commit + push

Solo si hay cambios. Mensaje: `sync YYYY-MM-DD HH:MM:SS`.

Si el push falla (alguien cambió GitHub a la vez), lo anota en el log y **la pasada
siguiente lo reintenta**.

---

## Conflictos: el PC manda

Si el mismo fichero cambió **en los dos sitios**, el script no pisa el del PC:

```bash
cp -p "$src" ~/.jarvis/pending/<ruta-con-guiones>.github-<timestamp>
log "CONFLICTO $1: el home cambio por su cuenta; la version de GitHub queda en $PENDING"
```

El del PC se queda. El de GitHub queda guardado con marca de tiempo en `~/.jarvis/pending/`.
Tú decides cuál vale. **No se pierde nada por los dos lados.**

El caso real, verificado: escribimos en `SOUL.md` aquí y en GitHub a la vez →
`CONFLICTO hermes/SOUL.md: el home cambio por su cuenta; la version de GitHub queda en /home/gabo/.jarvis/pending`.

### Cómo lo distingue de un cambio limpio

Antes de decidir que hay conflicto, compara el home con la versión que había **antes** del pull:

- Si el home coincide con `ORIG_HEAD:<fichero>` → el cambio es solo de GitHub → **restaura**.
- Si no coincide → el home tiene cambios propios → **conflicto**.

---

## Pruebas que se hicieron

No es teoría. Ciclos completos, con el resultado delante:

| Prueba | Resultado |
|---|---|
| Cambio en GitHub → aparece en el home | `restaurado de GitHub: hermes/ui-preferences.json`, `grep` = 1 |
| Cambio en el home → sube a GitHub | commit + `push OK`, visible en `origin/main` |
| Cambio en los dos sitios | `CONFLICTO`, copia guardada, nada perdido |
| Fichero de prueba creado a mano | subió solo, apareció en `origin/main`, se quitó |
| `system/uname.txt` desde GitHub | llegó al repo, **no** se restauró al home (correcto) |

---

## Ficheros que NO deben viajar

Se añadieron al `.gitignore` después de verlos aparecer:

- `hermes/runtime/`, `hermes/terminal-sessions/`, `hermes/locks/`, `hermes/state/`,
  `hermes/kanban/`, `hermes/cron/`, `hermes/logs/`, `hermes/backups/`, `hermes/gateway/`
- Locks de sesión de Chromium/Electron: `opencode/skills/**/profile/Singleton*`
- Volátiles: `system/memory.txt`, `system/disk.txt`, `system/network.txt`, `sync.log`
- Cachés: `models_dev_cache.*`, `provider_models_cache.json`, `skills_prompt_snapshot.json`

Motivo: cambiaban en cada arranque, ensuciaban el historial y no aportan nada al restaurar.

---

## El log

`jarvis/sync.log`, truncado a 200 líneas.

```bash
tail -f ~/jarvis/sync.log
grep -E "restaurado|CONFLICTO|ERROR|AVISO" ~/jarvis/sync.log
```

---

## Historia de dos bugs

**Bug 1 — `set -u` y la función `log`.** La primera versión tenía
`local msg="...$msg"`: la variable se auto-referenciaba antes de existir y el script moría
con `msg: variable sin asignar`. El temporizador marcó un fallo a las 10:19. Arreglado con
`local msg="...$*"`.

**Bug 2 — `HEAD@{1}`.** Hacía que todo pareciera conflicto. Arreglado con `ORIG_HEAD`
(ver arriba).

Los dos quedaron reverificados con `Result=success` y pruebas de ciclo completo.

---

## Reglas para quien lo toque

1. **No cambiar el orden de las fases.** Pull → restaurar → mirror → push.
2. **No quitar el `--autostash`** del pull: sin él, un cambio local a medio hacer rompe el rebase.
3. **No restaurar `system/`.** Es información, no configuración.
4. **Si falla el pull, salir sin tocar el home.**
5. Probar cualquier cambio con el ciclo completo antes de darlo por bueno.