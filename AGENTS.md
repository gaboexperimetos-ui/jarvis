# AGENTS.md — reglas de este repo

Este fichero lo lee cualquier agente que trabaje aquí. Si lo que vas a hacer contradice algo
de esta lista, no lo hagas: pregunta.

---

## Qué es este repo

Un espejo **bidireccional** del home del portátil `asus-tuf` hacia GitHub.
Cada 5 minutos, `jarvis-sync.sh` baja lo de GitHub, lo aplica al home, sube lo del home y
empuja. Es un respaldo vivo, no un proyecto.

Documentación completa en [`docs/`](docs/).

---

## Reglas duras

1. **El repo es público.** Nada de secretos: ni claves, ni tokens, ni `.env`, ni
   `auth.json`, ni `gateway-connections.json`, ni contraseñas. Si dudas, no lo subas y pregunta.
2. **No tocar `jarvis-sync.sh`** sin leer [`docs/SINCRONIZACION.md`](docs/SINCRONIZACION.md)
   y sin probar el ciclo completo. El orden de las fases es: pull → restaurar → mirror → push.
3. **No restaurar `system/` al home.** Es información de la máquina, no configuración.
4. **No versionar los proyectos** con `.git` propio (`proyectos/`, `dev/`, `ECC/`, …).
5. **Si el pull falla, no tocar el home.** El script ya lo hace; no lo cambies.
6. **No borrar ficheros del índice sin mirar el `.gitignore` primero.** Muchas exclusiones
   existen por un incidente real (la fuga del token del gateway está documentada).

---

## Cómo trabajar aquí

### Un cambio, un commit

Mensaje en imperativo, en español:

```
añade documentación de los MCPs
corrige el cálculo de conflictos en el sync
quita los cachés de Hermes del espejo
```

Nada de "varios arreglos y mejoras" en un solo commit.

### Probar antes de empujar

Si tocas el sync, ejecuta las tres pruebas del ciclo (están en
[`docs/SINCRONIZACION.md`](docs/SINCRONIZACION.md#pruebas-que-se-hicieron)):

```bash
~/jarvis/jarvis-sync.sh
grep -E "restaurado|CONFLICTO|push|ERROR" ~/jarvis/sync.log
```

### Revisar antes de empujar

```bash
git status --short          # ¿algo inesperado?
git diff --cached           # ¿algún secreto?
git ls-files | wc -l        # ¿el tamaño se disparó?
```

---

## Contexto que no está en el repo

- El agente Hermes vive en el **inspiron** (`~/.hermes`), no en este portátil.
- El `hermes/config.yaml` de este repo es el del portátil, casi todo plantilla. El bueno está
  en el inspiron y **tiene contraseñas**: no se versiona.
- Presupuesto: **0 €**. Todo lo que hay es gratis (OpenRouter free, llama.cpp local, Edge TTS,
  faster-whisper, Pollinations). No proponer nada de pago sin avisar.
- El sync es bidireccional de verdad: un cambio en GitHub se aplica al home en ≤5 minutos.
- Si un fichero cambió en los dos sitios, el del home manda y el de GitHub queda en
  `~/.jarvis/pending/`. No se pierde nada.

---

## Criterio de "terminado"

Un cambio está terminado cuando:

- [ ] Se puede revertir con `git revert`.
- [ ] Si toca el sync, pasó las tres pruebas del ciclo.
- [ ] No añade secretos al índice.
- [ ] Si cambia comportamiento, está documentado en `docs/`.
- [ ] `git status` sale limpio y `git log` cuenta la historia.

---

## Si algo está mal

Dilo en el commit y en `docs/PENDIENTES.md`. No lo arregles en silencio si el arreglo cambia
el alcance: este repo es un respaldo, y un respaldo que cambia solo es un problema.