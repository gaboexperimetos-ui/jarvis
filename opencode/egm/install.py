#!/usr/bin/env python3
"""Instala EGM (Elephant-Goldfish Model) en OpenCode V2 como un solo skill.

- Copia el paquete canonico (skills, agents, resources, docs) a ~/.config/opencode/egm/bundle
- Registra las personas Goldfish como subagentes de solo lectura en opencode.json
- Genera un unico skill wrapper en ~/.config/opencode/skills/egm/SKILL.md

Idempotente: se puede reejecutar para actualizar.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC = Path("/home/gabo/proyectos/elephant-goldfish-model")
DEST = Path("/home/gabo/.config/opencode/egm")
BUNDLE = DEST / "bundle"
CONFIG = Path("/home/gabo/.config/opencode/opencode.json")
SKILL_DIR = Path("/home/gabo/.config/opencode/skills/egm")
COMMAND_DIR = Path("/home/gabo/.config/opencode/commands")

REVIEWERS = {
    "codebase_details": "egm-codebase-details",
    "comprehension": "egm-comprehension",
    "design_critic": "egm-design",
    "implementation_readiness": "egm-implementation-readiness",
    "inventive_catalyst": "egm-inventive-catalyst",
    "structural": "egm-structural",
    "style": "egm-style",
    "zoom_out": "egm-zoom-out",
}

EXTRA_AGENTS = {
    "synthesizer": "egm-synthesizer",
    "bootstrap_orchestrator": "egm-bootstrap-orchestrator",
}

REVIEWER_IDS = sorted(REVIEWERS.values())
SYNTHESIZER = EXTRA_AGENTS["synthesizer"]
BOOTSTRAP = EXTRA_AGENTS["bootstrap_orchestrator"]


def read_name(path: Path) -> str:
    header = path.read_text(encoding="utf-8").split("---", 2)[1]
    for line in header.splitlines():
        if line.startswith("name: "):
            return line[len("name: ") :].strip()
    raise ValueError(f"sin name en {path}")


def read_description(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    header = text.split("---", 2)[1]
    lines = header.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("description:"):
            value = line.split(":", 1)[1].strip()
            if value in (">", "|", ">-", "|-"):
                out = []
                for nxt in lines[i + 1 :]:
                    if nxt and not nxt.startswith((" ", "\t")):
                        break
                    out.append(nxt.strip())
                return " ".join(x for x in out if x)
            return value
    return ""


def reviewer_permissions() -> list[dict]:
    rules = [
        {"action": "*", "resource": "*", "effect": "deny"},
        {"action": "read", "resource": "*", "effect": "allow"},
        # El orden importa: gana la ultima regla que coincide.
        {"action": "read", "resource": "*.env", "effect": "deny"},
        {"action": "read", "resource": "*.env.*", "effect": "deny"},
        {"action": "read", "resource": "*.env.example", "effect": "allow"},
        {"action": "glob", "resource": "*", "effect": "allow"},
        # El bundle vive fuera del proyecto: hay que abrirle la puerta explicitamente.
        # /tmp/opencode es el area temporal aprobada del entorno.
        {"action": "external_directory", "resource": "*", "effect": "deny"},
        {"action": "external_directory", "resource": "/tmp/opencode/*", "effect": "allow"},
        {"action": "external_directory", "resource": f"{BUNDLE}/*", "effect": "allow"},
        {"action": "external_directory", "resource": f"{BUNDLE}", "effect": "allow"},
        {"action": "read", "resource": "/tmp/opencode/**", "effect": "allow"},
        {"action": "read", "resource": f"{BUNDLE}/**", "effect": "allow"},
    ]
    return rules


def dispatcher_permissions(allowed: list[str]) -> list[dict]:
    rules = [{"action": "subagent", "resource": "*", "effect": "deny"}]
    rules += [{"action": "subagent", "resource": name, "effect": "allow"} for name in allowed]
    return rules


def build_agents() -> dict:
    agents: dict = {}

    for filename, agent_id in REVIEWERS.items():
        persona = BUNDLE / "agents" / f"{filename}.md"
        agents[agent_id] = {
            "description": f"EGM Goldfish de solo lectura: {read_description(persona)}",
            "mode": "subagent",
            "system": (
                f"Lee {persona} primero y sigue ese prompt al pie de la letra. "
                "Eres un revisor de solo lectura: no puedes escribir, editar ni ejecutar comandos. "
                "No tienes historial de conversacion: no pidas ni recuperes contexto previo. "
                "Devuelve tus hallazgos al agente que te delego. "
                "Si un archivo requerido no es accesible, reporta la revision como incompleta."
            ),
            "permissions": reviewer_permissions(),
        }

    agents[SYNTHESIZER] = {
        "description": (
            "EGM: agrega y deduplica hallazgos de varios Goldfish y compila un informe. "
            "Solo se usa cuando la skill canonica lo pide explicitamente."
        ),
        "mode": "subagent",
        "system": (
            f"Lee {BUNDLE / 'agents' / 'synthesizer.md'} primero y sigue ese prompt. "
            "Compila, deduplica y normaliza los hallazgos de los revisores Goldfish. "
            "No escribas codigo ni edites archivos del proyecto."
        ),
        "permissions": reviewer_permissions() + dispatcher_permissions(REVIEWER_IDS),
    }

    agents[BOOTSTRAP] = {
        "description": (
            "EGM: orquesta el bootstrap de documentacion README en un subarbol. "
            "Puede delegar en Goldfish. La delegacion anidada en OpenCode V2 no esta verificada."
        ),
        "mode": "subagent",
        "system": (
            f"Lee {BUNDLE / 'agents' / 'bootstrap_orchestrator.md'} primero y sigue ese prompt. "
            "Puedes delegar lecturas en los revisores Goldfish registrados. "
            "Si la delegacion anidada no esta disponible, ejecuta los pasos de scouting en linea."
        ),
        "permissions": reviewer_permissions()
        + [{"action": "edit", "resource": "*", "effect": "allow"}]
        + dispatcher_permissions(REVIEWER_IDS),
    }

    return agents


def build_skill() -> str:
    reviewer_list = "\n".join(f"- `{name}`" for name in REVIEWER_IDS)
    return f"""---
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

- Raiz del paquete: `{BUNDLE}`
- Personas Goldfish: `{BUNDLE}/agents/*.md`
- Estandares de documento: `{BUNDLE}/resources/document_standards/`
- Skills canonicas (se leen por ruta, NO estan registradas como skills de OpenCode):
  `{BUNDLE}/skills/<id>/SKILL.md`
- Guia del adaptador: `{BUNDLE}/docs/opencode.md`

Nunca copies ni reescribas el texto de las skills canonicas. Leelo y siguelo.

## Como trabajar

1. Lee `{BUNDLE}/docs/opencode.md` una vez por sesion de trabajo EGM.
2. Elige la skill canonica segun lo que pidio el usuario y **leela completa** antes de actuar:

| Peticion del usuario | Archivo canonico |
| --- | --- |
| Probar una idea, lluvia de ideas, "que tal si..." | `{BUNDLE}/skills/egm-brainstorm/SKILL.md` |
| Convertir notas o un brief en documento de diseno | `{BUNDLE}/skills/egm-draft/SKILL.md` |
| Revisar un diseno, README, plan de PR o spec | `{BUNDLE}/skills/egm-review/SKILL.md` |
| Resolver hallazgos de una revision | `{BUNDLE}/skills/egm-resolve/SKILL.md` |
| Auditar un documento contra varios estandares a la vez | `{BUNDLE}/skills/egm-review-loop/SKILL.md` |
| Documentar un codigo existente (READMEs) | `{BUNDLE}/skills/egm-bootstrap/SKILL.md` |
| Comparar documentos con el codigo actual | `{BUNDLE}/skills/egm-drift-report/SKILL.md` |

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

{reviewer_list}

Extra: `{SYNTHESIZER}` (agregador) y `{BOOTSTRAP}` (solo para egm-bootstrap).

Por defecto despacha los revisores directamente. Usa `{SYNTHESIZER}` solo si la skill canonica lo pide de forma explicita.

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
"""


def build_command() -> str:
    return """---
description: EGM: disena, revisa o documenta con el modelo Elefante y Pez Dorado
---

Usa el skill `egm` (Modelo Elefante y Pez Dorado) para atender esta peticion. Lee el skill completo y siguelo paso a paso, incluyendo el despacho de los revisores Goldfish.

Peticion del usuario: $ARGUMENTS

Si la peticion esta vacia, pregunta al usuario en texto plano que quiere disenar, revisar o documentar, y espera su respuesta antes de continuar.
"""


def install() -> None:
    if not (SRC / "skills").is_dir():
        sys.exit(f"no encuentro el repo fuente en {SRC}")

    commit = subprocess.run(
        ["git", "-C", str(SRC), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    DEST.mkdir(parents=True, exist_ok=True)
    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    BUNDLE.mkdir(parents=True)

    for directory in ("skills", "agents", "resources", "docs"):
        shutil.copytree(SRC / directory, BUNDLE / directory)
    for filename in ("plugin.json", "LICENSE", "README.md", "TESTING.md"):
        shutil.copy2(SRC / filename, BUNDLE / filename)

    # El skill wrapper
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    (SKILL_DIR / "SKILL.md").write_text(build_skill(), encoding="utf-8")

    # Comando /egm
    COMMAND_DIR.mkdir(parents=True, exist_ok=True)
    (COMMAND_DIR / "egm.md").write_text(build_command(), encoding="utf-8")

    # Config global: backup y merge de solo las claves que gestiona EGM
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = CONFIG.with_name(f"opencode.json.bak-egm-{stamp}")
    if not backup.exists():
        shutil.copy2(CONFIG, backup)

    agents = config.setdefault("agents", {})
    agents.update(build_agents())
    config["skills"] = config.get("skills") or []

    CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    hashes = {
        p.relative_to(BUNDLE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(BUNDLE.rglob("*"))
        if p.is_file()
    }
    (DEST / "install.json").write_text(
        json.dumps(
            {
                "name": "egm",
                "source": str(SRC),
                "source_commit": commit,
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "host": "opencode",
                "skill": str(SKILL_DIR / "SKILL.md"),
                "config": str(CONFIG),
                "backup": str(backup),
                "agents": sorted(agents.keys()),
                "sha256": hashes,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"repo fuente     : {SRC} @ {commit[:12]}")
    print(f"paquete         : {BUNDLE}")
    print(f"skill unico     : {SKILL_DIR / 'SKILL.md'}")
    print(f"comando         : {COMMAND_DIR / 'egm.md'}  (/egm)")
    print(f"config          : {CONFIG}")
    print(f"backup          : {backup}")
    print(f"subagentes      : {', '.join(sorted(agents))}")


if __name__ == "__main__":
    install()