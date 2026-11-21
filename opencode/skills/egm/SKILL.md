---
name: EGM - Modelo Elefante y Pez Dorado
description: >-
  Flujo de trabajo de Google para disenar y revisar software con agentes antes de escribir codigo.
  Usalo cuando el usuario pida disenar una funcionalidad, lluvia de ideas, una especificacion,
  un documento de diseno, revisar un diseno o un README contra el codigo, resolver hallazgos de
  una revision, documentar un codigo existente, o detectar desviacion (drift) entre la
  documentacion y el codigo. Tambien cuando el usuario mencione EGM, elefante, pez dorado,
  brainstorm de diseno, design review o spec.
---

# EGM - Modelo Elefante y Pez Dorado

**Elefante**: el agente con todo el contexto del proyecto. Explora el problema y escribe la especificacion.
**Pez dorado (Goldfish)**: revisores en contexto limpio, sin el historial de la conversacion. Encuentran supuestos implicitos y puntos ciegos.
**Tu usuario**: decide los compromisos de arquitectura y aprueba la especificacion antes de implementar.

EGM no implementa codigo: produce especificaciones y revisiones aprobadas. Cuando el usuario apruebe el diseno, implementar es una tarea aparte.

## Paquete instalado

- Raiz del paquete: `/home/gabo/.config/opencode/egm/bundle`
- Personas Goldfish: `/home/gabo/.config/opencode/egm/bundle/agents/*.md`
- Estandares de documento: `/home/gabo/.config/opencode/egm/bundle/resources/document_standards/`
- Skills canonicas (se leen por ruta, NO estan registradas como skills de OpenCode):
  `/home/gabo/.config/opencode/egm/bundle/skills/<id>/SKILL.md`
- Guia del adaptador: `/home/gabo/.config/opencode/egm/bundle/docs/opencode.md`

Nunca copies ni reescribas el texto de las skills canonicas. Leelo y siguelo.

## Como trabajar

1. Lee `/home/gabo/.config/opencode/egm/bundle/docs/opencode.md` una vez por sesion de trabajo EGM.
2. Elige la skill canonica segun lo que pidio el usuario y **leela completa** antes de actuar:

| Peticion del usuario | Archivo canonico |
| --- | --- |
| Probar una idea, lluvia de ideas, "que tal si..." | `/home/gabo/.config/opencode/egm/bundle/skills/egm-brainstorm/SKILL.md` |
| Convertir notas o un brief en documento de diseno | `/home/gabo/.config/opencode/egm/bundle/skills/egm-draft/SKILL.md` |
| Revisar un diseno, README, plan de PR o spec | `/home/gabo/.config/opencode/egm/bundle/skills/egm-review/SKILL.md` |
| Resolver hallazgos de una revision | `/home/gabo/.config/opencode/egm/bundle/skills/egm-resolve/SKILL.md` |
| Auditar un documento contra varios estandares a la vez | `/home/gabo/.config/opencode/egm/bundle/skills/egm-review-loop/SKILL.md` |
| Documentar un codigo existente (READMEs) | `/home/gabo/.config/opencode/egm/bundle/skills/egm-bootstrap/SKILL.md` |
| Comparar documentos con el codigo actual | `/home/gabo/.config/opencode/egm/bundle/skills/egm-drift-report/SKILL.md` |

3. Sigue esa skill paso a paso. Sus pasos, sus gates y sus nombres de archivo son obligatorios.

## Despacho de revisores Goldfish

Los revisores estan registrados como subagentes de OpenCode. Se despachan con la herramienta `subagent`:

- `agent`: el ID canonico del revisor.
- `description`: una linea corta.
- `prompt`: la tarea exacta que indica la skill canonica, mas las rutas absolutas del documento, del estandar y de las fuentes permitidas.
- **Omite `sessionID`**: cada revision necesita una sesion nueva. Nunca reutilices un revisor.

Reglas duras:

- Los Goldfish corren en segundo plano. **Espera el reporte de cada uno** antes de sintetizar o de pasar al siguiente paso. Si sigues sin el reporte, estas inventando la revision.
- Pasales solo la tarea y las rutas. **Nunca** el historial de la conversacion, tu razonamiento privado ni hallazgos de otros revisores, salvo cuando la etapa canonica lo exija explicitamente (por ejemplo `zoom_out_report.md` en el paso 8 de la revision).
- Si una herramienta de subagentes no esta disponible, **detente** y dile al usuario: una revision en el mismo contexto no es una revision Goldfish. No simules revisores.

Revisores disponibles:

- `egm-codebase-details`
- `egm-comprehension`
- `egm-design`
- `egm-implementation-readiness`
- `egm-inventive-catalyst`
- `egm-structural`
- `egm-style`
- `egm-zoom-out`

Extra: `egm-synthesizer` (agregador) y `egm-bootstrap-orchestrator` (solo para egm-bootstrap).

Por defecto despacha los revisores directamente. Usa `egm-synthesizer` solo si la skill canonica lo pide de forma explicita.

## Artefactos

- Directorio por defecto: el directorio de trabajo del proyecto.
- Si las instrucciones del usuario traen la linea `EGM artifact directory: <path>`, escribe ahi. Ruta relativa = relativa al directorio de trabajo. Crea la carpeta si no existe.
- Nombres canonicos: `concepts_brief.md`, `design_draft.md`, y los informes de etapa (`*_report.md`).
- Escribe tu mismo los informes. No delegues la escritura.

## Gates humanos

Conserva cada puerta de aprobacion de la skill: readiness, seccion por seccion, y aprobacion de cada etapa.
Cuando no exista la herramienta de pregunta nativa, haz **una** pregunta en texto plano y espera la respuesta.
El tiempo transcurrido y la ausencia de herramientas no son aprobacion.

## Limites conocidos

- OpenCode V2 ejecuta los subagentes en segundo plano: el reporte llega cuando el hijo queda inactivo.
- La delegacion anidada (un subagente que lanza otro) no esta verificada en V2. `egm-bootstrap` puede necesitar el modo en linea.
- Los revisores son de solo lectura por permiso, no por aislamiento de proceso o de sistema de archivos.
- Las instrucciones del proyecto (AGENTS.md) y los skills globales siguen visibles para el hijo: declara los supuestos como criterios de revision explicitos.
