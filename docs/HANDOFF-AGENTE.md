# Encargo para el otro agente

Vas a revisar este repo y proponer cambios. Esto es lo que hay, lo que no se toca y cómo se
entrega una propuesta.

---

## Qué es esto

Un espejo **bidireccional** del home de `gabo` (portátil `asus-tuf`) hacia GitHub, con
sincronización cada 5 minutos. No es un proyecto de software: es la copia de seguridad viva
de una máquina con un agente 24/7 encima.

Leer antes de tocar nada:

1. [`README.md`](../README.md) — el índice
2. [`docs/ARQUITECTURA.md`](ARQUITECTURA.md) — las máquinas y por qué están así
3. [`docs/SINCRONIZACION.md`](SINCRONIZACION.md) — la mecánica del sync
4. [`docs/SEGURIDAD.md`](SEGURIDAD.md) — qué no se sube y por qué

---

## Lo que NO se toca

| Cosa | Motivo |
|---|---|
| `.gitignore` (sin leerlo entero) | tiene 200+ líneas de exclusiones, la mayoría por una fuga real o un problema real |
| `jarvis-sync.sh`, orden de fases | está verificado con pruebas de ciclo completo; cambiar el orden rompe la restauración |
| La exclusión de `system/` del home | es información de máquina, no configuración |
| Cualquier cosa que añada secretos al índice | el repo es público |
| Los proyectos con `.git` propio | no van aquí |

---

## Lo que sí se puede proponer

- Mejoras al script de sync que **no cambien el orden** de las fases.
- Más documentación: si algo no está claro, es un fallo de los docs, no del sistema.
- Detección de nuevos secretos o nuevos volátiles que se cuelen.
- Arreglar los huecos de `docs/PENDIENTES.md`, si el usuario da lo que hace falta.
- Afinar el `.gitignore`: hay exclusiones redundantes y alguna demasiado ancha.

---

## Cómo entregar un cambio

1. **Edita en el repo local** (`~/jarvis`) o en GitHub. Los dos valen: el sync los une.
2. Si es un cambio en el home (no en el repo), documéntalo, no lo hagas: el repo es el
   espejo, no el original.
3. **Un commit por cambio conceptual.** Nada de "varios arreglos" en un commit.
4. Mensaje en imperativo y en español: `añade`, `corrige`, `quita`, `documenta`.
5. **Empuja** (`git push`). El sync lo aplicará al portátil en ≤5 minutos.
6. Si el cambio toca `jarvis-sync.sh`, **pruébalo con el ciclo completo** antes de empujar:
   - cambio en GitHub → aparece en el home
   - cambio en el home → aparece en GitHub
   - cambio en los dos sitios → `CONFLICTO`, nada se pierde

---

## Si el sync te trae un CONFLICTO

El del home manda y el de GitHub queda en `~/.jarvis/pending/`. No lo fuerces: lee las dos
versiones, decide, y si hay que quedarse con la de GitHub, cópiala a mano y commitea.

---

## Contexto que no se ve en el repo

- El agente Hermes vive en el **inspiron**, no en este portátil. Este repo es del portátil.
- `~/.hermes/config.yaml` del inspiron tiene las contraseñas del dashboard y los MCPs reales.
  **No se versiona aquí.**
- El modelo principal es `baidu/ernie-5.5-flash-preview:free` (OpenRouter), con
  `deepseek-v4pro` local como fallback.
- Presupuesto: **0 €**. No proponer nada de pago sin decirlo explícitamente.

---

## Criterio de calidad

Un cambio está bien si:

- Se puede revertir con un `git revert`.
- No rompe el sync (probado).
- No añade secretos.
- Si cambia comportamiento, está documentado en `docs/`.

Si no cumple los cuatro, no está listo.