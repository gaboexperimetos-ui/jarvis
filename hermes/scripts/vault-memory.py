#!/usr/bin/env python3
"""vault-memory.py — índice FTS5 del Segundo Cerebro y fuentes de Hermes.

Inspirado en la memoria de OpenJarvis (SQLite/FTS5 con atribución), pero
reutilizando el recolector, el chunking y la tokenización de vault-rag.py para
no duplicar criterios.

Ventajas frente al JSON de vault-rag.py:
  - Índice SQLite pequeño y consultas en milisegundos.
  - Sincronización incremental: solo reextrae lo que cambió (mtime/tamaño).
  - Atribución por nota: fuente, ruta, título, área, etiquetas y encabezado.
  - Sin dependencias nuevas: sqlite3 y FTS5 vienen con Python.

Uso:
  vault-memory.py "consulta" [-k 5] [--json|--context]
  vault-memory.py --sync            actualiza el índice ahora
  vault-memory.py --stats           estado del índice
  vault-memory.py --rebuild         reindexa desde cero
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
import sys
import time
from pathlib import Path

HERMES_HOME = Path(__file__).resolve().parent.parent
DB_PATH = HERMES_HOME / "cache" / "vault-memory.sqlite"
VR_PATH = Path(__file__).resolve().parent / "vault-rag.py"
CHECK_INTERVAL = 30.0

_spec = importlib.util.spec_from_file_location("vault_rag", VR_PATH)
vr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vr)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            stem TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            areas TEXT NOT NULL DEFAULT '',
            mtime REAL NOT NULL DEFAULT 0,
            size INTEGER NOT NULL DEFAULT 0,
            hash TEXT NOT NULL DEFAULT ''
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
            tokens,
            text UNINDEXED,
            note_id UNINDEXED,
            heading UNINDEXED,
            chunk_index UNINDEXED,
            tokenize = 'unicode61 remove_diacritics 2'
        );
        """
    )
    return con


def _meta(con: sqlite3.Connection, key: str, default: str = "") -> str:
    row = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def _set_meta(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        "INSERT INTO meta(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _heading(text: str) -> str:
    first = text.strip().splitlines()[0].strip() if text.strip() else ""
    return first.lstrip("#").strip() if first.startswith("#") else ""


def _note_tokens(title: str, tags: list[str], body: str) -> str:
    head = vr.tokenize(title) * 3 + vr.tokenize(" ".join(tags)) * 2
    return " ".join(head + vr.tokenize(body))


def _upsert_note(con: sqlite3.Connection, src: str, path: str, title: str,
                 stem: str, tags: list[str], mtime: float, size: int,
                 digest: str, body: str) -> int:
    con.execute(
        """
        INSERT INTO notes(source,path,title,stem,tags,areas,mtime,size,hash)
        VALUES(?,?,?,?,?,'',?,?,?)
        ON CONFLICT(path) DO UPDATE SET
            source=excluded.source, title=excluded.title, stem=excluded.stem,
            tags=excluded.tags, mtime=excluded.mtime, size=excluded.size,
            hash=excluded.hash
        """,
        (src, path, title, stem, ", ".join(tags), mtime, size, digest),
    )
    note_id = con.execute("SELECT id FROM notes WHERE path=?", (path,)).fetchone()[0]
    con.execute("DELETE FROM chunks WHERE note_id=?", (note_id,))
    for idx, chunk in enumerate(vr.chunk_body(body)):
        text = chunk.strip()
        if not text:
            continue
        con.execute(
            "INSERT INTO chunks(tokens,text,note_id,heading,chunk_index) VALUES(?,?,?,?,?)",
            (_note_tokens(title, tags, text), text[:1200], note_id,
             _heading(text), idx),
        )
    return note_id


def _sync(con: sqlite3.Connection, rebuild: bool = False) -> dict:
    t0 = time.monotonic()
    cfg = vr.load_config()
    entries = vr.collect(cfg, [])
    snap = vr.latest_snapshot() if cfg.get("mikareno") else None
    sig = json.dumps(vr.signature(entries, snap, cfg), ensure_ascii=False)

    if rebuild:
        con.execute("DELETE FROM chunks")
        con.execute("DELETE FROM notes")

    existing = {
        row[0]: (row[1], row[2], row[3])
        for row in con.execute("SELECT path,mtime,size,hash FROM notes")
    }
    live_paths = {str(p) for p, _ in entries}
    hashes = {h for _, _, h in existing.values() if h}

    added = updated = removed = skipped = 0
    for path, src in entries:
        key = str(path)
        try:
            st = path.stat()
        except OSError:
            continue
        old = existing.get(key)
        if not rebuild and old and old[0] == st.st_mtime and old[1] == st.st_size:
            skipped += 1
            continue
        text = vr.extract_text(path)
        if not text.strip():
            continue
        digest = hashlib.sha1(vr.norm(text).encode("utf-8", "ignore")).hexdigest()
        if digest in hashes and (old is None or old[2] != digest):
            if old is not None:
                con.execute("DELETE FROM chunks WHERE note_id=(SELECT id FROM notes WHERE path=?)", (key,))
                con.execute("DELETE FROM notes WHERE path=?", (key,))
                removed += 1
            skipped += 1
            continue
        note = vr.parse_text(path, text[: cfg["max_kb"] * 1024])
        _upsert_note(con, src.get("name", ""), key, note["title"], note["stem"],
                     note["tags"], st.st_mtime, st.st_size, digest, note["body"])
        hashes.add(digest)
        if old is None:
            added += 1
        else:
            updated += 1

    for key in set(existing) - live_paths:
        if key.startswith(str(Path.home() / ".cache" / "mikareno-mcp")):
            continue
        con.execute("DELETE FROM chunks WHERE note_id=(SELECT id FROM notes WHERE path=?)", (key,))
        con.execute("DELETE FROM notes WHERE path=?", (key,))
        removed += 1

    mk = vr.mikareno_note() if cfg.get("mikareno") else None
    if mk:
        try:
            st = Path(mk["path"]).stat()
            mtime, size = st.st_mtime, st.st_size
        except OSError:
            mtime, size = time.time(), 0
        _upsert_note(con, "mikareno", mk["path"], mk["title"], mk["stem"],
                     mk["tags"], mtime, size, "mikareno", mk["body"])

    notes = [{"stem": row[0], "area_hint": row[1]}
             for row in con.execute("SELECT stem, '' FROM notes")]
    areas = vr.area_map(notes)
    con.executemany(
        "UPDATE notes SET areas=? WHERE stem=?",
        [(", ".join(v), k) for k, v in areas.items()],
    )

    _set_meta(con, "signature", sig)
    _set_meta(con, "checked_at", str(time.time()))
    _set_meta(con, "last_sync", time.strftime("%Y-%m-%d %H:%M:%S"))
    con.commit()
    return {
        "ok": True, "added": added, "updated": updated, "removed": removed,
        "skipped": skipped, "seconds": round(time.monotonic() - t0, 2),
    }


def ensure_index(con: sqlite3.Connection, force: bool = False) -> dict | None:
    if force:
        return _sync(con, rebuild=False)
    try:
        checked = float(_meta(con, "checked_at", "0") or 0)
    except ValueError:
        checked = 0.0
    if time.time() - checked < CHECK_INTERVAL:
        return None
    cfg = vr.load_config()
    entries = vr.collect(cfg, [])
    snap = vr.latest_snapshot() if cfg.get("mikareno") else None
    sig = json.dumps(vr.signature(entries, snap, cfg), ensure_ascii=False)
    if sig == _meta(con, "signature"):
        _set_meta(con, "checked_at", str(time.time()))
        con.commit()
        return None
    return _sync(con)


def _where(args: argparse.Namespace) -> tuple[str, list]:
    clauses, params = [], []
    if args.source:
        clauses.append("n.source = ?")
        params.append(args.source)
    if args.area:
        clauses.append("n.areas LIKE ?")
        params.append(f"%{args.area}%")
    if args.path:
        clauses.append("n.path LIKE ?")
        params.append(f"%{args.path}%")
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def _snippet(text: str, limit: int = 420) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def search(con: sqlite3.Connection, query: str, k: int = 5,
           source: str = "", area: str = "", path: str = "",
           per_note: int = 1) -> list[dict]:
    tokens = vr.tokenize(query)
    if not tokens:
        return []
    match = " OR ".join(tokens)
    where, params = _where(argparse.Namespace(source=source, area=area, path=path))
    sql = f"""
        SELECT c.note_id, c.text, c.heading, c.chunk_index,
               n.title, n.stem, n.path, n.source, n.tags, n.areas,
               bm25(chunks) AS rank
        FROM chunks c
        JOIN notes n ON n.id = c.note_id
        WHERE chunks MATCH ?{where}
        ORDER BY rank
        LIMIT ?
    """
    rows = con.execute(sql, [match, *params, max(k * 8, 20)]).fetchall()
    by_note: dict[int, list] = {}
    order: list[int] = []
    for row in rows:
        note_id = row[0]
        if note_id not in by_note:
            by_note[note_id] = []
            order.append(note_id)
        if len(by_note[note_id]) < max(1, per_note):
            by_note[note_id].append(row)
    results = []
    for note_id in order[:k]:
        chunks = by_note[note_id]
        head = chunks[0]
        snippets = [_snippet(c[1]) for c in chunks]
        results.append({
            "title": head[4],
            "stem": head[5],
            "link": f"[[{head[5]}|{head[4]}]]" if head[7] == "vault" else None,
            "areas": [a for a in head[9].split(", ") if a],
            "tags": [t for t in head[8].split(", ") if t],
            "source": head[7],
            "score": round(float(-head[10]), 4),
            "snippet": snippets[0],
            "snippets": snippets,
            "path": head[6],
            "heading": head[2],
        })
    return results


def _print_context(query: str, results: list[dict]) -> None:
    print(f"[vault-memory] Consulta: {query}\n")
    if not results:
        print("(sin coincidencias)")
        return
    for r in results:
        ref = r["link"] or f"{r['title']} ({r['path']})"
        a = ", ".join(r["areas"]) or "—"
        print(f"- {ref} (área: {a}; fuente: {r['source']})")
        for s in r["snippets"]:
            if s:
                print(f"  {s}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Memoria FTS5 del Segundo Cerebro")
    ap.add_argument("query", nargs="*", help="consulta")
    ap.add_argument("-k", "--top", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--context", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--source", default="")
    ap.add_argument("--area", default="")
    ap.add_argument("--path", default="")
    ap.add_argument("--chunks", type=int, default=1, help="fragmentos por nota")
    args = ap.parse_args()

    con = _connect()
    if args.rebuild:
        info = _sync(con, rebuild=True)
        print(json.dumps(info, ensure_ascii=False))
        return 0
    if args.sync:
        print(json.dumps(ensure_index(con, force=True), ensure_ascii=False))
        return 0
    if args.stats:
        notes = con.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        chunks = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        print(json.dumps({
            "notes": notes, "chunks": chunks, "db_bytes": size,
            "last_sync": _meta(con, "last_sync"), "db": str(DB_PATH),
        }, ensure_ascii=False))
        return 0

    query = " ".join(args.query).strip()
    if not query:
        ap.print_help()
        return 2
    ensure_index(con)
    results = search(con, query, args.top, args.source, args.area,
                     args.path, args.chunks)
    if args.json:
        print(json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=2))
    elif args.context:
        _print_context(query, results)
    else:
        if not results:
            print("Sin coincidencias.")
            return 0
        for n, r in enumerate(results, 1):
            ref = r["link"] or r["title"]
            a = ", ".join(r["areas"]) or "—"
            print(f"{n}) {ref}  ({r['score']})")
            print(f"   área: {a} · fuente: {r['source']}")
            for s in r["snippets"]:
                if s:
                    print(f"   {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
