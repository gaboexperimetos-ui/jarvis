#!/usr/bin/env python3
"""Autoenlaza el vault del Segundo Cerebro.

Hace dos cosas, sin borrar ni mover nada:

  1. Copia al vault las notas nuevas que NOVA dejó solo en su espejo
     (`~/proyectos/styp/notes`). La ruta MCP `create_note` escribe ahí pero
     se salta la exportación al vault; las demás rutas sí exportan.
  2. Cuelga cada nota huérfana de su área con un bloque gestionado
     (`<!-- autolink:inicio --> ... <!-- autolink:fin -->`). No toca el
     cuerpo de las notas ni los enlaces manuales.

Uso:
  vault-autolink.py            copia y enlaza
  vault-autolink.py --dry-run  muestra lo que haría, sin escribir
"""

from __future__ import annotations

import re
import shutil
import sys
import unicodedata
from pathlib import Path

HOME = Path.home()
VAULT = HOME / "SegundoCerebro"
MIRROR = HOME / "proyectos" / "styp" / "notes"

MARK_START = "<!-- autolink:inicio -->"
MARK_END = "<!-- autolink:fin -->"
SECTION = "## Notas vinculadas automáticamente"

# Notas de prueba que no deben entrar al vault.
JUNK = {
    "",
    "readme",
    "filtro-prueba-alfa",
    "filtro-prueba-beta",
    "mcp-verify-nota",
    "prueba-api",
    "sprint-test",
    "verificacion-tag-unico",
}

AREAS = [
    {
        "name": "WhatsApp",
        "file": "WhatsApp.md",
        "prefix": ("whatsapp-",),
        "tags": {"whatsapp"},
        "keywords": {"whatsapp", "mensaje", "chat", "grupo", "dm"},
    },
    {
        "name": "Estudio",
        "file": "Estudio.md",
        "tags": {
            "estudio", "tareas", "tarea", "examenes", "examen", "apuntes",
            "apunte", "colegio", "materia", "deberes", "matematicas", "fisica",
            "quimica", "lengua", "ingles", "historia", "biologia", "classroom",
        },
        "keywords": {
            "tarea", "examen", "deber", "clase", "materia", "colegio",
            "profesor", "profe", "leccion", "apunte", "matricula", "semestre",
            "bimestre", "cuaderno", "classroom", "entrega", "practico",
            "parcial", "quiz",
        },
    },
    {
        "name": "Proyectos",
        "file": "Proyectos.md",
        "tags": {"proyectos", "proyecto", "styp", "hermes", "mikareno", "zig", "codigo"},
        "keywords": {
            "proyecto", "styp", "hermes", "mikareno", "plataforma", "zig",
            "opencode", "mcp", "script", "api", "systemd", "timer",
            "repositorio", "git", "servicio", "vault", "obsidian", "grafo",
            "nodo", "automatizacion",
        },
    },
    {
        "name": "IA local",
        "file": "IA local.md",
        "tags": {"ia", "llm", "modelo", "modelos", "local"},
        "keywords": {
            "llm", "modelo", "deepseek", "qwen", "llama", "gpt", "openai",
            "anthropic", "hugging", "gpu", "cuda", "tok/s", "router",
            "inference", "benchmark", "cuantizacion", "open source",
            "open-source", "entrenamiento", "pesos",
        },
    },
    {
        "name": "Personal",
        "file": "Personal.md",
        "tags": {"personal", "ideas", "idea", "salud", "diario", "familia"},
        "keywords": {
            "personal", "idea", "salud", "familia", "casa", "compra",
            "viaje", "cumpleanos", "diario", "emocion",
        },
    },
]

FALLBACK = {"name": "Bandeja de entrada", "file": "Bandeja de entrada.md"}
FILES = {a["name"]: a["file"] for a in AREAS}
FILES[FALLBACK["name"]] = FALLBACK["file"]


def norm(value: str) -> str:
    """Minúsculas y sin acentos, para comparar."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return value.casefold()


def parse_frontmatter(text: str) -> tuple[str, list[str], str]:
    title = ""
    tags: list[str] = []
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            header = text[4:end]
            body = text[end + 5:]
            for line in header.splitlines():
                s = line.strip()
                if s.startswith("title:"):
                    title = s[6:].strip().strip('"').strip("'")
                elif s.startswith("tags:"):
                    raw = s[5:].strip()
                    if raw.startswith("[") and raw.endswith("]"):
                        raw = raw[1:-1]
                    for part in raw.split(","):
                        tag = part.strip().strip('"').strip("'").strip("#")
                        if tag:
                            tags.append(tag)
    return title.strip(), tags, body


def strip_blocks(text: str) -> str:
    return re.sub(
        re.escape(MARK_START) + r".*?" + re.escape(MARK_END),
        "",
        text,
        flags=re.S,
    )


def load_notes() -> dict[str, dict]:
    notes: dict[str, dict] = {}
    for path in sorted(VAULT.glob("*.md")):
        if path.name.startswith("."):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        title, tags, body = parse_frontmatter(text)
        notes[path.stem] = {
            "path": path,
            "title": title or path.stem,
            "tags": tags,
            "body": body,
            "text": text,
        }
    return notes


def manual_inbound(notes: dict[str, dict]) -> set[str]:
    """Notas que ya están enlazadas a mano (fuera de los bloques)."""
    inbound: set[str] = set()
    for note in notes.values():
        clean = strip_blocks(note["text"])
        for target in re.findall(r"\[\[([^\]|#]+)", clean):
            target = target.strip()
            if target.endswith(".md"):
                target = target[:-3]
            target = target.split("/")[-1]
            if target:
                inbound.add(target)
    return inbound


def sync_mirror(dry: bool) -> list[str]:
    copied: list[str] = []
    if not MIRROR.is_dir():
        return copied
    for src in sorted(MIRROR.glob("*.md")):
        if src.name.startswith(".") or src.stem in JUNK:
            continue
        dst = VAULT / src.name
        if dst.exists():
            continue
        copied.append(src.name)
        if not dry:
            shutil.copy2(src, dst)
    return copied


def classify(stem: str, title: str, tags: list[str], body: str) -> str:
    title_n = norm(title)
    body_n = norm(body)
    tagset = {norm(tag) for tag in tags}

    if stem.startswith("whatsapp-") or "whatsapp" in tagset:
        return "WhatsApp"

    best_name, best_score = FALLBACK["name"], 0
    for area in AREAS:
        score = 0
        for prefix in area.get("prefix", ()):
            if stem.startswith(prefix):
                score += 8
        for tag in tagset:
            if tag in area["tags"]:
                score += 5
        body_hits = 0
        for keyword in area["keywords"]:
            key = norm(keyword)
            if key in title_n:
                score += 3
            if key in body_n and body_hits < 6:
                score += 1
                body_hits += 1
        if norm(area["name"]) in title_n:
            score += 2
        if score > best_score:
            best_name, best_score = area["name"], score
    return best_name


def format_item(title: str, stem: str) -> str:
    clean = title.replace("|", "¦").replace("\n", " ").strip() or stem
    if clean == stem:
        return f"- [[{stem}]]\n"
    return f"- [[{stem}|{clean}]]\n"


def rebuild(content: str, items: list[tuple[str, str]]) -> str:
    block = "".join(format_item(title, stem) for title, stem in sorted(items, key=lambda x: norm(x[0])))
    has_block = MARK_START in content and MARK_END in content

    if items:
        if has_block:
            return re.sub(
                re.escape(MARK_START) + r".*?" + re.escape(MARK_END),
                MARK_START + "\n" + block + MARK_END,
                content,
                count=1,
                flags=re.S,
            )
        return content.rstrip() + "\n\n" + SECTION + "\n\n" + MARK_START + "\n" + block + MARK_END + "\n"

    if has_block:
        pattern = (
            r"\n*" + re.escape(SECTION) + r"\s*"
            + re.escape(MARK_START) + r".*?" + re.escape(MARK_END) + r"\s*"
        )
        out = re.sub(pattern, "\n", content, count=1, flags=re.S)
        if out == content:
            out = re.sub(
                re.escape(MARK_START) + r".*?" + re.escape(MARK_END),
                MARK_START + "\n" + MARK_END,
                content,
                count=1,
                flags=re.S,
            )
        return out

    return content


def main() -> int:
    dry = "--dry-run" in sys.argv
    copied = sync_mirror(dry)

    notes = load_notes()
    inbound = manual_inbound(notes)
    excluded = {"Inicio", "README"} | {Path(f).stem for f in FILES.values()}

    assignments: dict[str, list[tuple[str, str]]] = {name: [] for name in FILES}
    linked: list[tuple[str, str]] = []
    for stem, note in notes.items():
        if stem in excluded or stem in inbound:
            continue
        area = classify(stem, note["title"], note["tags"], note["body"])
        assignments[area].append((note["title"], stem))
        linked.append((stem, area))

    changed: list[str] = []
    for area, items in assignments.items():
        path = VAULT / FILES[area]
        content = path.read_text(encoding="utf-8", errors="replace")
        new = rebuild(content, items)
        if new != content:
            changed.append(FILES[area])
            if not dry:
                path.write_text(new, encoding="utf-8")

    print(f"copiadas del espejo: {len(copied)}")
    for name in copied:
        print(f"  + {name}")
    print(f"enlazadas: {len(linked)}")
    for stem, area in linked:
        print(f"  {stem} -> {area}")
    print(f"archivos actualizados: {len(changed)}")
    for name in changed:
        print(f"  ~ {name}")
    if dry:
        print("(dry-run: no se escribió nada)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
