"""vault-memory: expone el índice FTS5 del Segundo Cerebro como herramienta.

La herramienta ``vault_search`` busca en ~/SegundoCerebro, ~/Documentos y los
proyectos, y devuelve fragmentos con su nota y ruta de origen para que el
agente cite. El índice lo mantiene ``scripts/vault-memory.py`` de forma
incremental; aquí solo se lanza el script y se devuelve su salida.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
SCRIPT = HERMES_HOME / "scripts" / "vault-memory.py"

SCHEMA = {
    "name": "vault_search",
    "description": (
        "Busca en la memoria local del usuario (Segundo Cerebro, Documentos y "
        "proyectos) y devuelve fragmentos con su nota y ruta de origen. Úsela "
        "para horario, clases, exámenes, tareas, notas, proyectos o cualquier "
        "dato guardado. Cita siempre la nota o ruta que devuelva. Prefiérela "
        "antes de decir que no tiene acceso a esos datos."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Qué buscar, en español natural.",
            },
            "k": {
                "type": "integer",
                "description": "Número de notas a devolver (1-20). Por defecto 5.",
                "minimum": 1,
                "maximum": 20,
            },
            "area": {
                "type": "string",
                "description": (
                    "Filtra por área del vault: Estudio, Proyectos, IA local, "
                    "WhatsApp, Personal o Bandeja de entrada."
                ),
            },
            "source": {
                "type": "string",
                "description": "Filtra por fuente: vault, Documentos, styp, proyectos o mikareno.",
            },
            "path": {
                "type": "string",
                "description": "Subcadena de la ruta del archivo.",
            },
            "chunks": {
                "type": "integer",
                "description": "Fragmentos por nota (1-3). Por defecto 1.",
                "minimum": 1,
                "maximum": 3,
            },
            "format": {
                "type": "string",
                "enum": ["json", "context"],
                "description": "json (estructurado) o context (texto compacto). Por defecto json.",
            },
        },
        "required": ["query"],
    },
}


def _python() -> str:
    for candidate in (sys.executable, "python3"):
        if candidate and (candidate == "python3" or Path(candidate).exists()):
            return candidate
    return "python3"


def _clamp(value, low: int, high: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def handle_vault_search(args: dict, **_kw) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        return json.dumps({"error": "falta el parámetro 'query'"}, ensure_ascii=False)
    if not SCRIPT.is_file():
        return json.dumps(
            {"error": f"no existe el índice: {SCRIPT}"}, ensure_ascii=False
        )

    cmd = [
        _python(), str(SCRIPT), query,
        "-k", str(_clamp(args.get("k"), 1, 20, 5)),
        "--chunks", str(_clamp(args.get("chunks"), 1, 3, 1)),
    ]
    area = str(args.get("area") or "").strip()
    source = str(args.get("source") or "").strip()
    path = str(args.get("path") or "").strip()
    if area:
        cmd += ["--area", area]
    if source:
        cmd += ["--source", source]
    if path:
        cmd += ["--path", path]
    cmd.append("--context" if args.get("format") == "context" else "--json")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=90,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "vault_search agotó el tiempo (90 s)"}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"vault_search falló: {exc}"}, ensure_ascii=False)

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[-600:]
        return json.dumps(
            {"error": "el índice de memoria devolvió un error", "detail": detail},
            ensure_ascii=False,
        )
    return result.stdout.strip() or json.dumps({"results": []}, ensure_ascii=False)


def register(ctx) -> None:
    ctx.register_tool(
        name="vault_search",
        toolset="vault_memory",
        schema=SCHEMA,
        handler=handle_vault_search,
        description="Memoria local del Segundo Cerebro (FTS5) con citas de nota y ruta.",
        emoji="🧠",
    )
