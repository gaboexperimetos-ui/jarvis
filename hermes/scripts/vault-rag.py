#!/usr/bin/env python3
"""vault-rag.py — recuperación (RAG) sobre el Segundo Cerebro, sin dependencias.

Devuelve las notas más relevantes para una consulta, con su enlace [[nota]] y
un fragmento, para que cualquier agente (OpenCode, NOVA, Hermes) pueda responder
citando el vault. La "generación" la hace el agente; esto es el recuperador.

Diseño:
  - BM25 léxico (k1=1.5, b=0.75) sobre título (x3), etiquetas (x2) y cuerpo.
  - Español: minúsculas, sin acentos, sin palabras vacías.
  - Sin modelos, sin red, sin VRAM: funciona en esta máquina tal cual.

Uso:
  vault-rag.py "consulta"                 top 5 en texto
  vault-rag.py -k 8 "consulta"            top 8
  vault-rag.py --json "consulta"          salida JSON (para agentes)
  vault-rag.py --context "consulta"       bloque listo para pegar a un LLM
  vault-rag.py --list                     notas indexadas
  vault-rag.py --source DIR ... "consulta"  añade fuentes extra (repetible)

Fuentes por defecto: ~/SegundoCerebro/*.md
Config opcional: ~/.hermes/vault-rag.json
  { "sources": ["/ruta/extra", "/otra/ruta"], "max_kb": 256 }
"""

from __future__ import annotations

import argparse
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
AREAS = ["Estudio", "Proyectos", "IA local", "WhatsApp", "Personal", "Bandeja de entrada"]

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


def parse_note(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
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


def load_sources(extra: list[str], max_kb: int) -> tuple[list[dict], dict[str, list[str]]]:
    dirs = [DEFAULT_VAULT] + [Path(p).expanduser() for p in extra]
    notes: dict[str, dict] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            if p.name.startswith(".") or p.stem in notes:
                continue
            if p.stat().st_size > max_kb * 1024:
                continue
            note = parse_note(p)
            if note:
                notes[note["stem"]] = note
    # área = MOC que enlaza la nota (las propias áreas no pertenecen a un área)
    skip = set(AREAS) | {"Inicio", "README"}
    area_of: dict[str, list[str]] = {}
    for area in AREAS:
        p = DEFAULT_VAULT / f"{area}.md"
        if not p.exists():
            continue
        for t in re.findall(r"\[\[([^\]|#]+)", p.read_text(encoding="utf-8", errors="replace")):
            t = t.strip().split("/")[-1]
            if t.endswith(".md"):
                t = t[:-3]
            if t in notes and t not in skip:
                area_of.setdefault(t, []).append(area)
    return list(notes.values()), area_of


def build_index(notes: list[dict]) -> tuple[list[list[str]], float]:
    docs = []
    for n in notes:
        toks = tokenize(n["title"]) * 3 + tokenize(" ".join(n["tags"])) * 2 + tokenize(n["body"])
        docs.append(toks)
    avg = sum(len(d) for d in docs) / len(docs) if docs else 0.0
    return docs, avg


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
    ap = argparse.ArgumentParser(description="Recuperación BM25 sobre el Segundo Cerebro")
    ap.add_argument("query", nargs="*", help="consulta")
    ap.add_argument("-k", "--top", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--context", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--source", action="append", default=[], help="fuente extra (repetible)")
    ap.add_argument("--max-kb", type=int, default=None)
    args = ap.parse_args()

    extra = list(args.source)
    max_kb = args.max_kb or 256
    if CONFIG.exists():
        try:
            cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
            extra += cfg.get("sources", [])
            if args.max_kb is None:
                max_kb = int(cfg.get("max_kb", max_kb))
        except (OSError, ValueError):
            pass

    notes, area_of = load_sources(extra, max_kb)
    if not notes:
        print("vault-rag: no hay notas que indexar", file=sys.stderr)
        return 1

    if args.list:
        for n in sorted(notes, key=lambda x: norm(x["title"])):
            a = ", ".join(area_of.get(n["stem"], [])) or "—"
            print(f"{a:20} {n['title']}  [{n['stem']}]")
        print(f"\n{len(notes)} notas", file=sys.stderr)
        return 0

    query = tokenize(" ".join(args.query))
    if not query:
        print("vault-rag: consulta vacía", file=sys.stderr)
        return 2

    docs, avg = build_index(notes)
    scores = bm25(docs, avg, query)
    order = sorted(range(len(notes)), key=lambda i: scores[i], reverse=True)
    picked = [i for i in order if scores[i] > 0][: args.top]

    results = []
    for i in picked:
        n = notes[i]
        results.append(
            {
                "stem": n["stem"],
                "title": n["title"],
                "link": f"[[{n['stem']}|{n['title']}]]",
                "areas": area_of.get(n["stem"], []),
                "tags": n["tags"],
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
            a = ", ".join(r["areas"]) or "—"
            print(f"- {r['link']} (área: {a})")
            if r["snippet"]:
                print(f"  {r['snippet']}")
        if not results:
            print("(sin coincidencias)")
        return 0

    if not results:
        print("Sin coincidencias.")
        return 0
    for n, r in enumerate(results, 1):
        a = ", ".join(r["areas"]) or "—"
        print(f"{n}) {r['link']}  ({r['score']})")
        print(f"   área: {a}" + (f" · tags: {', '.join(r['tags'])}" if r["tags"] else ""))
        if r["snippet"]:
            print(f"   {r['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
