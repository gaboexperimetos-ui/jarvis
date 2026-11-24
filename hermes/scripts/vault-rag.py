#!/usr/bin/env python3
"""vault-rag.py — recuperación (RAG) sobre el Segundo Cerebro y más fuentes.

Devuelve las notas/documentos más relevantes para una consulta, con cita y
fragmento, para que cualquier agente (OpenCode, NOVA, Hermes) responda
apoyándose en el material. La "generación" la hace el agente; esto recupera.

Diseño:
  - BM25 léxico (k1=1.5, b=0.75) sobre título (x3), etiquetas (x2) y cuerpo.
  - Español: minúsculas, sin acentos, sin palabras vacías.
  - Sin modelos, sin red, sin VRAM. Índice en caché para consultas rápidas.
  - Fuentes múltiples con peso, recursión, exclusiones y deduplicación.

Uso:
  vault-rag.py "consulta"                 top 5 en texto
  vault-rag.py -k 8 "consulta"            top 8
  vault-rag.py --json "consulta"          salida JSON (para agentes)
  vault-rag.py --context "consulta"       bloque listo para pegar a un LLM
  vault-rag.py --list                     fuentes y notas indexadas
  vault-rag.py --source DIR "consulta"    añade una fuente extra (recursiva)
  vault-rag.py --rebuild "consulta"       ignora la caché y reindexa

Config: ~/.hermes/vault-rag.json
  {
    "max_kb": 512,
    "mikareno": true,
    "exclude_dirs": ["node_modules", ".git", "..."],
    "sources": [
      {"name": "vault", "path": "~/SegundoCerebro", "recursive": false, "weight": 2.0},
      {"name": "Documentos", "path": "~/Documentos", "recursive": true, "weight": 1.5}
    ]
  }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

HOME = Path.home()
DEFAULT_VAULT = HOME / "SegundoCerebro"
CONFIG = HOME / ".hermes" / "vault-rag.json"
CACHE = HOME / ".hermes" / "cache" / "vault-rag-index.json"
SNAP_DIR = HOME / ".cache" / "mikareno-mcp" / "snapshots"
AREAS = ["Estudio", "Proyectos", "IA local", "WhatsApp", "Personal", "Bandeja de entrada"]

DEFAULT_EXCLUDES = [
    "node_modules", ".git", ".zig-cache", "zig-out", "target", "dist", "build",
    ".venv", "venv", "__pycache__", ".next", "site-packages", ".cache", ".npm",
]

STOP = set(
    """de la que el en y a los se del las un por con no una su para es al lo como
    mas pero sus le ya o este si porque esta entre cuando muy sin sobre tambien me
    hasta hay donde quien desde todo nos durante todos uno les ni contra otros ese
    eso ante ellos e esto mi antes algunos que unos yo otro otras otra el tanto esa
    estos mucho quienes nada muchos cual poco ella estar estas algunas algo nosotros
    mis tu te ti tus ellas nosotras vosotros vosotras os mio mia mios mias tuyo tuya
    tuyos tuyas suyo suya suyos suyas nuestro nuestra nuestros nuestras vuestro
    vuestra vuestros vuestras esos esas estoy estas esta estamos estais estan este
    estes estemos esteis esten estare estaras estara estaremos estareis estaran
    estaria estarias estariamos estariais estarian estaba estabas estabamos estabais
    estaban estuve estuviste estuvo estuvimos estuvisteis estuvieron estuviera
    estuvieras estuvieramos estuvierais estuvieran estuviese estuvieses estuviesemos
    estuvieseis estuviesen estando estado estada estados estadas estad he has ha
    hemos habeis han haya hayas hayamos hayais hayan habre habras habra habremos
    habreis habran habria habrias habriamos habriais habrian habia habias habiamos
    habiais habian hube hubiste hubo hubimos hubisteis hubieron hubiera hubieras
    hubieramos hubierais hubieran hubiese hubieses hubiesemos hubieseis hubiesen
    habiendo habido habida habidos habidas soy eres es somos sois son sea seas
    seamos seais sean sere seras sera seremos sereis seran seria serias seriamos
    seriais serian era eras eramos erais eran fui fuiste fue fuimos fuisteis fueron
    fuera fueras fueramos fuerais fueran fuese fueses fuesemos fueseis fuesen siendo
    sido tengo tienes tiene tenemos teneis tienen tenga tengas tengamos tengais
    tengan tendre tendras tendra tendremos tendreis tendran tendria tendrias
    tendriamos tendriais tendrian tenia tenias teniamos teniais tenian tuve tuviste
    tuvo tuvimos tuvisteis tuvieron tuviera tuvieras tuvieramos tuvierais tuvieran
    tuviese tuvieses tuviesemos tuvieseis tuviesen teniendo tenido tenida tenidos
    tenidas tened""".split()
)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", norm(text)) if len(w) > 1 and w not in STOP]


def parse_text(path: Path, text: str) -> dict:
    title, tags, body = path.stem, [], text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            header = text[4:end]
            body = text[end + 5:]
            for line in header.splitlines():
                s = line.strip()
                if s.startswith("title:"):
                    title = s[6:].strip().strip('"').strip("'") or title
                elif s.startswith("tags:"):
                    raw = s[5:].strip()
                    if raw.startswith("[") and raw.endswith("]"):
                        raw = raw[1:-1]
                    tags = [x.strip().strip('"').strip("'").lstrip("#") for x in raw.split(",") if x.strip()]
    return {"stem": path.stem, "title": title, "tags": tags, "body": body, "path": str(path)}


def norm_source(s) -> dict:
    if isinstance(s, str):
        return {"name": Path(s).name, "path": s, "recursive": True, "weight": 1.0, "exclude": []}
    d = dict(s)
    d.setdefault("name", Path(d.get("path", "")).name)
    d.setdefault("recursive", True)
    d.setdefault("weight", 1.0)
    d.setdefault("exclude", [])
    return d


def load_config() -> dict:
    cfg = {"max_kb": 512, "mikareno": False, "exclude_dirs": DEFAULT_EXCLUDES, "sources": []}
    if CONFIG.exists():
        try:
            raw = json.loads(CONFIG.read_text(encoding="utf-8"))
            for k in ("max_kb", "mikareno"):
                if k in raw:
                    cfg[k] = raw[k]
            if raw.get("exclude_dirs"):
                cfg["exclude_dirs"] = list(raw["exclude_dirs"])
            cfg["sources"] = [norm_source(s) for s in raw.get("sources", [])]
        except (OSError, ValueError) as e:
            print(f"vault-rag: config inválida ({e})", file=sys.stderr)
    if not cfg["sources"]:
        cfg["sources"] = [norm_source(DEFAULT_VAULT)]
    return cfg


def collect(cfg: dict, extra: list[str]) -> list[tuple[Path, dict]]:
    sources = list(cfg["sources"])
    sources += [norm_source({"name": "extra", "path": p, "recursive": True, "weight": 1.0}) for p in extra]
    sources.sort(key=lambda s: -s["weight"])
    entries: list[tuple[Path, dict]] = []
    seen: set[str] = set()
    for src in sources:
        root = Path(src["path"]).expanduser()
        if not root.is_dir():
            continue
        excludes = set(cfg["exclude_dirs"]) | set(src.get("exclude", []))
        it = root.rglob("*.md") if src["recursive"] else root.glob("*.md")
        for p in it:
            try:
                if not p.is_file() or p.name.startswith("."):
                    continue
                if set(p.parts) & excludes:
                    continue
                if p.stat().st_size > cfg["max_kb"] * 1024:
                    continue
            except OSError:
                continue
            rp = str(p.resolve())
            if rp in seen:
                continue
            seen.add(rp)
            entries.append((p, src))
    return entries


def latest_snapshot() -> Path | None:
    if not SNAP_DIR.is_dir():
        return None
    snaps = sorted(SNAP_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return snaps[0] if snaps else None


def mikareno_note() -> dict | None:
    f = latest_snapshot()
    if not f:
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8", errors="replace")).get("data", {})
    except (OSError, ValueError):
        return None
    ts = data.get("tarea_stats", {}) or {}
    lines = [
        f"Estado de tareas mikareno (snapshot {data.get('capturado', f.stem)}).",
        f"Esta semana: {ts.get('tasksCurrentWeek', 0)}. Hoy: {ts.get('todaysTasks', 0)}. Mañana: {ts.get('tomorrowsTask', 0)}.",
    ]
    tp = data.get("tareas_paginadas", {}) or {}
    items = tp.get("pageContent", []) if isinstance(tp, dict) else []
    for t in items[:20]:
        if not isinstance(t, dict):
            continue
        name = t.get("title") or t.get("name") or t.get("description") or "Tarea"
        due = t.get("dueDate") or t.get("date") or t.get("fecha") or ""
        lines.append(f"Tarea: {str(name)[:120]}" + (f" — {str(due)[:32]}" if due else ""))
    mat = data.get("matricula", {}).get("enrollment", {}) if isinstance(data.get("matricula"), dict) else {}
    if isinstance(mat, dict):
        for k in ("grade", "section", "level", "studentName"):
            if mat.get(k):
                lines.append(f"Matrícula {k}: {mat[k]}")
    body = "\n".join(lines)
    return {
        "stem": "mikareno-estado",
        "title": "Estado mikareno (tareas)",
        "tags": ["estudio", "mikareno", "tareas"],
        "body": body,
        "path": str(f),
        "source_name": "mikareno",
        "source_weight": 1.6,
        "area_hint": "Estudio",
        "_tokens": tokenize("Estado mikareno tareas " * 2 + body),
    }


def signature(entries: list[tuple[Path, dict]], snap: Path | None, cfg: dict) -> list:
    sig = []
    for p, src in entries:
        st = p.stat()
        sig.append([str(p), st.st_mtime_ns, st.st_size, src["weight"], src.get("name", "")])
    if snap:
        st = snap.stat()
        sig.append(["__mikareno__", str(snap), st.st_mtime_ns, st.st_size])
    sig.append(["__cfg__", cfg["max_kb"], sorted(cfg["exclude_dirs"])])
    return sig


def build(entries: list[tuple[Path, dict]], mk: dict | None) -> list[dict]:
    notes: list[dict] = []
    seen: set[str] = set()
    for p, src in entries:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        h = hashlib.sha1(norm(text).encode("utf-8", "ignore")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        n = parse_text(p, text)
        n["source_name"] = src.get("name", "")
        n["source_weight"] = src["weight"]
        n["_tokens"] = tokenize(n["title"]) * 3 + tokenize(" ".join(n["tags"])) * 2 + tokenize(n["body"])
        notes.append(n)
    if mk:
        notes.append(mk)
    return notes


def area_map(notes: list[dict]) -> dict[str, list[str]]:
    skip = set(AREAS) | {"Inicio", "README"}
    names = {n["stem"] for n in notes}
    area_of: dict[str, list[str]] = {}
    for area in AREAS:
        p = DEFAULT_VAULT / f"{area}.md"
        if not p.exists():
            continue
        for t in re.findall(r"\[\[([^\]|#]+)", p.read_text(encoding="utf-8", errors="replace")):
            t = t.strip().split("/")[-1]
            if t.endswith(".md"):
                t = t[:-3]
            if t in names and t not in skip:
                area_of.setdefault(t, []).append(area)
    return area_of


def load_index(cfg: dict, extra: list[str], rebuild: bool) -> tuple[list[dict], list[tuple[Path, dict]]]:
    entries = collect(cfg, extra)
    snap = latest_snapshot() if cfg.get("mikareno") else None
    sig = signature(entries, snap, cfg)
    if not rebuild and CACHE.exists():
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            if cached.get("signature") == sig:
                return cached["notes"], entries
        except (OSError, ValueError, KeyError):
            pass
    notes = build(entries, mikareno_note() if cfg.get("mikareno") else None)
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps({"signature": sig, "notes": notes}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return notes, entries


def bm25(docs: list[list[str]], avg: float, query: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    n = len(docs)
    df = Counter()
    for d in docs:
        df.update(set(d))
    scores = []
    for d in docs:
        tf = Counter(d)
        s = 0.0
        for w in query:
            if w not in tf:
                continue
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * (tf[w] * (k1 + 1)) / (tf[w] + k1 * (1 - b + b * len(d) / (avg or 1)))
        scores.append(s)
    return scores


def snippet(body: str, query: list[str], width: int = 240) -> str:
    parts = [p.strip() for p in re.split(r"\n\s*\n|\n", body) if p.strip()]
    if not parts:
        return ""
    qs = set(query)

    def hits(p: str) -> int:
        return sum(1 for w in tokenize(p) if w in qs)

    best = max(parts, key=lambda p: (hits(p), len(p)))
    clean = re.sub(r"\s+", " ", best).strip()
    if len(clean) > width:
        clean = clean[:width].rsplit(" ", 1)[0] + "…"
    return clean


def main() -> int:
    ap = argparse.ArgumentParser(description="Recuperación BM25 sobre el Segundo Cerebro y más fuentes")
    ap.add_argument("query", nargs="*", help="consulta")
    ap.add_argument("-k", "--top", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--context", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--source", action="append", default=[], help="fuente extra recursiva (repetible)")
    ap.add_argument("--max-kb", type=int, default=None)
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    if args.max_kb is not None:
        cfg["max_kb"] = args.max_kb

    notes, entries = load_index(cfg, args.source, args.rebuild)
    if not notes:
        print("vault-rag: no hay notas que indexar", file=sys.stderr)
        return 1
    area_of = area_map(notes)

    if args.list:
        by_src: dict[str, int] = Counter(n.get("source_name", "") for n in notes)
        for src, count in sorted(by_src.items()):
            print(f"{src:14} {count:5} notas")
        print(f"{'TOTAL':14} {len(notes):5} notas")
        for n in sorted(notes, key=lambda x: norm(x["title"])):
            a = ", ".join(area_of.get(n["stem"], [])) or n.get("area_hint") or "—"
            print(f"  [{n.get('source_name','')}] {a:18} {n['title']}")
        return 0

    query = tokenize(" ".join(args.query))
    if not query:
        print("vault-rag: consulta vacía", file=sys.stderr)
        return 2

    docs = [n["_tokens"] for n in notes]
    avg = sum(len(d) for d in docs) / len(docs) if docs else 0.0
    scores = bm25(docs, avg, query)
    for i, n in enumerate(notes):
        scores[i] *= float(n.get("source_weight", 1.0))
    order = sorted(range(len(notes)), key=lambda i: scores[i], reverse=True)
    picked = [i for i in order if scores[i] > 0][: args.top]

    results = []
    for i in picked:
        n = notes[i]
        is_vault = n.get("source_name") == "vault"
        results.append(
            {
                "title": n["title"],
                "stem": n["stem"],
                "link": f"[[{n['stem']}|{n['title']}]]" if is_vault else None,
                "areas": area_of.get(n["stem"], []) or ([n["area_hint"]] if n.get("area_hint") else []),
                "tags": n["tags"],
                "source": n.get("source_name", ""),
                "score": round(scores[i], 3),
                "snippet": snippet(n["body"], query),
                "path": n["path"],
            }
        )

    if args.json:
        print(json.dumps({"query": " ".join(args.query), "results": results}, ensure_ascii=False, indent=2))
        return 0

    if args.context:
        print(f"[vault-rag] Consulta: {' '.join(args.query)}\n")
        for r in results:
            ref = r["link"] or f"{r['title']} ({r['path']})"
            a = ", ".join(r["areas"]) or "—"
            print(f"- {ref} (área: {a}; fuente: {r['source']})")
            if r["snippet"]:
                print(f"  {r['snippet']}")
        if not results:
            print("(sin coincidencias)")
        return 0

    if not results:
        print("Sin coincidencias.")
        return 0
    for n, r in enumerate(results, 1):
        ref = r["link"] or r["title"]
        a = ", ".join(r["areas"]) or "—"
        print(f"{n}) {ref}  ({r['score']})")
        print(f"   área: {a} · fuente: {r['source']}")
        if r["snippet"]:
            print(f"   {r['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
