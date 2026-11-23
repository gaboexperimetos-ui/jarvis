---
description: Orquesta un objetivo con los motores instalados (plan, build, verificación)
agent: orquestador
---

# /orquestar

Objetivo: $ARGUMENTS

Ejecuta el ciclo completo del agente `orquestador`:

1. **Contrato**: objetivo, criterios de aceptación, repo y restricciones.
2. **Recon** de solo lectura del repo y de los comandos reales de verificación.
3. **Plan** numerado con archivos, orden, motor elegido y verificación por paso.
   Guárdalo en `~/.local/state/opencode/orquestar/plan-<slug>.md`.
4. **Gate**: presenta el plan. Si el objetivo vino con instrucción de ejecutar
   ("hazlo", "arréglalo", "implementa"), continúa; si no, espera aprobación.
5. **Build**: usa herramientas en sesión para cambios pequeños; delega en
   `~/.config/opencode/scripts/orquestar-engine.sh` para trabajo grande. Un solo
   escritor por árbol. `git status --short` antes y después.
6. **Verificar**: corre test/lint/build reales, revisa el diff y delega revisiones
   en los subagentes que apliquen. Máximo 3 ciclos de corrección.
7. **Reporte**: cambios, evidencia con exit codes, motor usado, pendientes.

Si `$ARGUMENTS` está vacío, pide el objetivo y no hagas nada más.
