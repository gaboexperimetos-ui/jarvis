# Auditoría del agente — 2026-11-21

Revisión de los dos agentes que viven en este repo:

- **Hermes** → `hermes/` (`SOUL.md` + `config.yaml`, 2.521 líneas)
- **OpenCode** → `opencode/` (`AGENTS.md`, `opencode.json`, 339 skills, 9 MCP, 12 subagentes)

Sin acceso a la máquina desde aquí: no he podido medir servicios ni ejecutar `hermes`. Todo lo que sigue son cambios de fichero y comprobaciones de sintaxis, no de comportamiento en vivo.

---

## 1. Cambios aplicados

| Fichero | Qué | Por qué |
|---|---|---|
| `hermes/SOUL.md` | Reescrito (58 líneas) | Decía **cómo escribir** pero casi nada de **cómo trabajar**. Los huecos los rellenaba el modelo a su criterio. |
| `hermes/config.yaml` | 6 ajustes puntuales | Bucles, verificación, failover y protección de la propia config. |
| `opencode/AGENTS.md` | 4 datos corregidos + 2 reglas | Tres afirmaciones se contradecían entre sí; el agente razonaba con datos falsos. |

### `SOUL.md` — qué se añadió

Se mantiene tu estilo (directo, sin relleno, español, tuteo, hechos vs estimaciones). Lo nuevo:

- **Ambigüedad:** una pregunta corta solo si dos lecturas cambian el trabajo; si no, decide, declara el supuesto y entrega.
- **Alcance:** no ampliar ni recortar en silencio; los extras van como sugerencia al final.
- **Seguridad:** secretos, acciones destructivas, `push --force`, y no editar `config.yaml` / `SOUL.md` / `AGENTS.md` / `opencode.json` sin copia y aviso.
- **Verificación:** enseñar la salida real cuando algo falla; no repetir el mismo comando fallido más de dos veces.
- **Memoria y skills:** guardar lo duradero, nunca credenciales; mirar la skill antes de decidir que no hace falta.
- **Contexto del setup:** OpenCode, Docker, llama.cpp, router 8004, GPU de 6 GB y 14 GB de RAM (no caben dos modelos).
- **Cierre:** qué cambió / qué está verificado / qué queda; nada de terminar con una promesa que podías ejecutar.

### `config.yaml` — los 6 ajustes

| Clave | Antes | Ahora | Motivo |
|---|---|---|---|
| `agent.max_turns` | 500 | **200** | 500 solo se alcanza en bucles; 200 deja aire sin permitir una sesión desbocada. |
| `agent.api_max_retries` | 3 (implícito) | **2** | Ya hay fallback al router local; reintentar 3 veces contra OpenRouter solo hace esperar. |
| `agent.verify_on_stop` | `false` | **`"auto"`** | Si edito código sin verificarlo, empuja a comprobarlo antes de cerrar (solo en superficies de código, no en Telegram). |
| `agent.coding_instructions` | vacío | **7 reglas** | Español, diff limpio, sin force-push, no tocar config propia, verificar, no instalar globales, diff pequeño. Se aplican solas en cualquier workspace de código. |
| `tool_loop_guardrails.hard_stop_enabled` | `false` | **`true`** | Corta a las 5/8 repeticiones del mismo fallo en vez de esperar a que lo notes. |
| `security` | comentado | **activo** | `SOUL.md`, `AGENTS.md`, `config.yaml`, `opencode.json`, `cli.json` protegidos: escribirlos pide aprobación humana incluso con `--yolo`. |

`allow_private_urls` se dejó sin tocar a propósito: el router de 8004 y los MCP locales siguen igual.

### `opencode/AGENTS.md` — contradicciones corregidas

1. **Ancho de banda:** decía `~289 GB/s` arriba y `314 GB/s medidos / 336 teóricos` abajo → unificado en **314 medidos**.
2. **Carga del modelo:** decía que se descarga a los **120 s** de inactividad, y dos párrafos después que `--sleep-idle-seconds 3600` lo mantiene cargado → queda **hasta una hora**, con 3-8 s de carga en frío.
3. **Tamaño del modelo:** hablaba de un **1,7B**, pero el único modelo es `deepseek-v4pro` de **4B** → corregido.
4. Añadidas dos reglas: copia antes de editar tu propia config, y no repetir un comando fallido más de dos veces.

---

## 2. Bug de configuración encontrado

`docker_run_as_host_user: true` estaba **suelto con indentación de dos espacios** entre los comentarios de "Browser Tool Configuration" y `browser:`, sin pertenecer a ninguna sección. Al activar `security:` se colgaba de `security` en vez de `terminal`. Recogido bajo `terminal:` (su sitio) y validado el YAML completo: 32 claves de nivel raíz, parsea sin errores.

---

## 3. Lo que NO toqué (y merece una decisión tuya)

1. **Modelo primario `:free` de OpenRouter.** Es gratis, pero tiene rate limit y calidad variable, y el fallback es un 4B local. Para trabajo serio, un modelo de pago de reserva en la cadena cambiaría más que cualquier prompt.
2. **`display.personality: concise` + `SOUL.md`.** Son dos capas de estilo a la vez. Prueba una sesión con `/personality` cambiado; si `SOUL.md` ya manda, quita la personalidad para no duplicar reglas.
3. **339 skills de OpenCode frente a las 11 de Hermes.** Un `skills.external_dirs` apuntando a todas inundaría el catálogo y gastaría contexto en descubrimiento. Mejor copiar 10-15 útiles.
4. **Delegación:** los subagentes heredan el modelo caro. Fijar `delegation.model` a uno barato es donde se ahorra de verdad.
5. **9 MCP en OpenCode:** si alguno está lento o caído, alarga el arranque. Empezaría por medir cuáles tardan con `opencode` en modo debug.
6. **Rotar las dos claves** que estuvieron publicadas (ver sección 6).
7. **`opencode.jsonc`**: define el pool "Unlimited" en el 8090, pero `opencode.json` (el activo según `AGENTS.md`) no lo incluye. Decidir cuál manda y borrar el otro, o quedan dos configs divergentes.

---

## 4. Cómo se aplica en tu máquina

El repo se sincroniza en dos sentidos cada 5 minutos:

- Lo que cambia aquí y **no** cambia en el home → se copia al home (`hermes/*` → `~/.hermes/`, `opencode/*` → `~/.config/opencode/`).
- Si el home también cambió en ese fichero → **no se pisa**: la versión nueva queda en `~/.jarvis/pending/` y se avisa en `sync.log`.

`config.yaml` se lee al arrancar: hace falta reiniciar el gateway o abrir sesión nueva. `coding_instructions` y `SOUL.md` aplican en la siguiente sesión.

Verificación mínima después del sync:

```bash
hermes doctor
hermes config get agent.max_turns      # 200
hermes config get security.protected_instruction_files   # true
grep -c "coding_instructions" ~/.hermes/config.yaml
```

---

## 5. Siguiente paso que yo elegiría

1. Reiniciar y **probar SOUL.md** con tres preguntas típicas (una de una línea, una de estado de la máquina, una de código) para ver si el tono y el cierre son los que quieres.
2. Añadir un **modelo de pago de reserva** a `fallback_providers` antes del router local.
3. Decidir lo de `personality` y el `auto_prune`. Son los dos que más ensucian el día a día sin que se note.

---

## 6. Segunda pasada (mismo día, después)

### 6.1 Dos claves estaban en claro en el repo

| Fichero | Qué era | Ahora |
|---|---|---|
| `opencode/opencode.json` | clave de `freellmapi` (`localhost:3001`) | `{file:/home/gabo/.config/opencode/secrets/freellmapi-api-key}` |
| `opencode/opencode.jsonc` | clave de "Unlimited" (`127.0.0.1:8090`) | `{file:/home/gabo/.config/opencode/secrets/unlimited-api-key}` |

Las dos apuntan a servicios locales, así que el riesgo real es bajo, pero el repo es público y el historial ya las tiene. **Antes de mergear el PR**, o justo después del sync, ejecuta:

```bash
cd ~/jarvis && ./scripts/seed-opencode-secrets.sh
```

Recupera los valores del commit `59100aa`, los deja en `~/.config/opencode/secrets/` con permisos `600` y no los imprime. Es idempotente: si los ficheros ya existen, no hace nada. Probado en un `HOME` temporal: crea los dos ficheros (59 y 35 bytes) y la segunda pasada los respeta.

Si no lo ejecutas, esos dos proveedores fallarán al arrancar hasta que las claves estén en su sitio. El modelo principal (`local/deepseek-v4pro`) no depende de ellas.

### 6.2 `jarvis-sync.sh` endurecido

- **`flock`**: el timer de 5 min y una ejecución manual ya no se pisan.
- **Guardia de secretos** antes de commitear: si una línea **añadida** contiene `sk-…32`, `ghp_…`, `github_pat_…`, `AKIA…`, `xox…` o `BEGIN … PRIVATE KEY`, no commitea y lo apunta en `sync.log`. Mira solo líneas añadidas, así que borrar una clave vieja no bloquea el sync.
- **Exclusiones nuevas** en el `rsync`: `*.db`, `*.db-wal`, `*.db-shm`, `*.sqlite*`, `attachments/`, `node_modules/`, `.git/`, `*.log`, `*.tmp`, `__pycache__/`, `.venv/`. Antes solo las ignoraba git; ahora ni se copian.
- Sintaxis comprobada con `bash -n`, y la regex probada contra la clave real (dispara) y contra un ejemplo `sk-proj-xxxx` (no dispara).

### 6.3 OpenCode

- **`small_model` corregido**: apuntaba a `opencode/minimax-m3.1-flash-free`, un proveedor que no existe en tu config; ahora `kiosapi/minimax-m3.1-flash-free`, que sí está definido. Era el modelo de títulos y tareas ligeras.
- **12 reglas `ask` nuevas** en `permissions`: `git reset --hard`, `git clean`, `git push --force`, `pacman -R`, `pacman -S`, `docker system prune`, `docker volume rm`, `chown -R`, `truncate -s`, `npm publish`, `gh pr merge`, `> /dev/sd*`.
- Comprobado que `provider` y `providers` **no** son un error: el propio OpenCode migra el formato viejo (`provider`) al nuevo (`providers`) y fusiona ambos. Ahí no había nada que arreglar.

### 6.4 Hermes, tres ajustes más

- **`sessions.auto_prune: true`**, retención 180 días, `VACUUM` tras podar. `state.db` deja de crecer sin límite; las sesiones abiertas o fijadas no se tocan.
- **Memoria 2.200/1.375 → 3.000/1.800** caracteres (~1.100 y ~650 tokens). Cabe de sobra en 200k de contexto.
- **`provider_routing.sort: "throughput"`**: con un modelo `:free`, ordenar por precio no aporta; que elija el proveedor más rápido de ese modelo.

### 6.5 Verificación

```bash
bash -n ~/jarvis/jarvis-sync.sh
python3 -c "import yaml;yaml.safe_load(open('$HOME/.hermes/config.yaml'));print('yaml ok')"
python3 -c "import json;json.load(open('$HOME/.config/opencode/opencode.json'));print('json ok')"
grep -c '"effect": "ask"' ~/.config/opencode/opencode.json   # 22
```
