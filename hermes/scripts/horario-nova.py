#!/usr/bin/env python3
"""horario-nova.py — horario de clases y calendario escolar en el vault.

Lee el snapshot de mikareno (el mismo que usa el resumen diario) y escribe dos
notas del Segundo Cerebro, de forma idempotente:

  * `Horario.md`   — la semana, bloque por bloque, con hora y materia.
  * `Calendario.md`— el trimestre en curso, las vacaciones y los próximos
                     eventos, más las entregas de Classroom con fecha.

No borra ni mueve nada: solo reescribe esas dos notas.

Uso:
  horario-nova.py            escribe las dos notas
  horario-nova.py --dry-run  muestra lo que haría
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

HOME = Path.home()
VAULT = HOME / "SegundoCerebro"
SNAP_DIR = HOME / ".cache" / "mikareno-mcp" / "snapshots"
MCP_URL = "http://127.0.0.1:8080/mcp"

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def latest_snapshot() -> Path | None:
    if not SNAP_DIR.is_dir():
        return None
    snaps = sorted(SNAP_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return snaps[0] if snaps else None


def load() -> dict:
    f = latest_snapshot()
    if not f:
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8", errors="replace")).get("data", {})
    except (OSError, ValueError):
        return {}


def mcp_call(name: str, args: dict | None = None):
    """Llama una herramienta del MCP de mikareno. Devuelve dict o None."""
    def post(body, sid=None):
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if sid:
            h["mcp-session-id"] = sid
        req = urllib.request.Request(MCP_URL, data=json.dumps(body).encode(), headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace"), r.headers.get("mcp-session-id")

    def parse(raw):
        for line in raw.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return json.loads(raw) if raw.strip() else {}

    try:
        raw, sid = post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                    "clientInfo": {"name": "horario-nova", "version": "1"}}})
        post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
        raw, _ = post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                       "params": {"name": name, "arguments": args or {}}}, sid)
        result = parse(raw).get("result") or {}
        text = (result.get("content") or [{}])[0].get("text", "")
        return json.loads(text)
    except Exception:
        return None


def horario_note(data: dict, mcp: dict | None) -> str:
    days = {"MONDAY": "Lunes", "TUESDAY": "Martes", "WEDNESDAY": "Miércoles", "THURSDAY": "Jueves", "FRIDAY": "Viernes"}
    rows = (data.get("horario", {}) or {}).get("periodMap", {}) or {}
    lunes = rows.get("MONDAY") or []
    year = (lunes[0].get("year") if lunes else datetime.now().year) or datetime.now().year
    lines = [
        "---",
        'title: "Horario"',
        "tags: [estudio, horario, clases, colegio]",
        "---",
        "",
        "# Horario",
        "",
        f"Horario de clases {year}. Fuente: mikareno (snapshot del {datetime.now():%d/%m/%Y %H:%M}).",
        "",
    ]
    if mcp and mcp.get("horario"):
        by_day: dict[str, list] = {}
        for r in mcp["horario"]:
            by_day.setdefault(str(r.get("dia", "")).capitalize(), []).append(r)
        for day, items in by_day.items():
            lines += [f"## {day}", "", "| Hora | Materia |", "| --- | --- |"]
            for r in items:
                if not (r.get("clase") or "").strip():
                    continue  # recreo
                lines.append(f"| {r.get('hora', '—')} | {r.get('clase', '—')} |")
            lines.append("")
        lines += ["Relacionado: [[Estudio]] · [[Calendario]] · [[Tareas]] · [[mikareno]] · [[Inicio]]", ""]
        return "\n".join(lines)
    for key, day in days.items():
        items = sorted(
            (r for r in rows.get(key) or [] if r.get("subject")),
            key=lambda r: (r.get("slot") or {}).get("ordinal", 0),
        )
        if not items:
            continue
        lines.append(f"## {day}")
        lines.append("")
        lines.append("| Hora | Materia | Aula |")
        lines.append("| --- | --- | --- |")
        for r in items:
            slot = r.get("slot") or {}
            subj = (r.get("subject") or {}).get("name") or "—"
            hora = slot.get("prettyTime") or "—"
            aula = r.get("room") or r.get("parallel") or "—"
            lines.append(f"| {hora} | {subj} | {aula} |")
        lines.append("")
    lines += ["Relacionado: [[Estudio]] · [[Calendario]] · [[Tareas]] · [[mikareno]] · [[Inicio]]", ""]
    return "\n".join(lines)


def calendario_note(data: dict, mcp: dict | None) -> str:
    today = date.today()
    lines = [
        "---",
        'title: "Calendario"',
        "tags: [estudio, calendario, colegio, entregas]",
        "---",
        "",
        "# Calendario",
        "",
        "Trimestre en curso, vacaciones y entregas. Fuente: mikareno y Classroom.",
        "",
    ]

    term = (data.get("term", {}) or {}).get("currentPartial") or {}
    if term:
        lines += [
            "## Trimestre",
            "",
            f"- **{term.get('name', '—')}**: {term.get('start', '?')} → {term.get('end', '?')} "
            f"({term.get('days', '?')} días).",
            "",
        ]

    events = []
    if mcp:
        for e in mcp.get("dias_no_lectivos", []) or []:
            start = str(e.get("fecha", ""))[:10]
            try:
                d = datetime.strptime(start, "%Y-%m-%d").date()
            except ValueError:
                continue
            if d >= today:
                events.append((d, e.get("titulo") or "Sin clases"))
    if not events:
        for e in data.get("calendario", []) or []:
            start = str(e.get("start", ""))[:10]
            if not start:
                continue
            try:
                d = datetime.strptime(start, "%Y-%m-%d").date()
            except ValueError:
                continue
            if e.get("dayType") == "SCHOOL_DAY" or d < today:
                continue
            events.append((d, e.get("title") or "Evento"))
    if events:
        lines += ["## Próximos días sin clase", ""]
        for d, title in sorted(events)[:12]:
            lines.append(f"- {d:%d/%m}: {title}")
        lines.append("")

    ts = data.get("tarea_stats", {}) or {}
    if ts:
        lines += [
            "## Tareas",
            "",
            f"- Esta semana: {ts.get('tasksCurrentWeek', 0)} · "
            f"Hoy: {ts.get('todaysTasks', 0)} · Mañana: {ts.get('tomorrowsTask', 0)}.",
            "",
        ]

    tasks = (data.get("tareas_paginadas", {}) or {}).get("pageContent", []) or []
    pend = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        due = str(t.get("dueDate") or t.get("date") or "")[:10]
        if not due:
            continue
        try:
            d = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            continue
        name = t.get("title") or t.get("name") or t.get("description") or "Tarea"
        pend.append((d, str(name)[:90]))
    if pend:
        lines += ["## Tareas con fecha", ""]
        for d, name in sorted(pend)[:15]:
            mark = "⚠️ " if d < today else ""
            lines.append(f"- {mark}{d:%d/%m} — {name}")
        lines.append("")

    lines += ["Relacionado: [[Estudio]] · [[Horario]] · [[Tareas]] · [[mikareno]] · [[Inicio]]", ""]
    return "\n".join(lines)


def main() -> int:
    dry = "--dry-run" in sys.argv
    data = load()
    if not data:
        print("horario-nova: sin snapshot de mikareno", file=sys.stderr)
        return 1
    mcp_h = mcp_call("get_horario")
    mcp_c = mcp_call("get_calendario")
    notes = {
        "Horario.md": horario_note(data, mcp_h),
        "Calendario.md": calendario_note(data, mcp_c),
    }
    for name, text in notes.items():
        path = VAULT / name
        if dry:
            print(f"--- {name} ({len(text)} bytes) ---")
            print(text[:400])
            continue
        path.write_text(text, encoding="utf-8")
        print(f"escrito: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())