#!/usr/bin/env python3
"""Consulta de solo lectura del registro de WhatsApp de Hermes.

Lee ``~/.hermes/logs/whatsapp-inbox.jsonl`` (lo escribe el plugin
``whatsapp-triage`` con cada mensaje admitido: DMs y grupos) y lo presenta
legible. No envia nada, no responde y no toca WhatsApp.

Ejemplos:
  wa-recent.py                         # ultimos 30 mensajes
  wa-recent.py --chats                 # chats vistos (nombre, id, cantidad, ultimo)
  wa-recent.py --chat 10mo --limit 50  # solo chats cuyo nombre/id contenga "10mo"
  wa-recent.py --since 24h             # ultimas 24 horas
  wa-recent.py --since 2026-11-22 --json

Limites reales: el registro empieza cuando se instalo el plugin. No hay
historial anterior ni lista de chats del telefono (el puente Baileys no
persiste el historial).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOG_PATH = Path(os.environ.get("WA_INBOX_LOG", Path.home() / ".hermes" / "logs" / "whatsapp-inbox.jsonl"))


def _parse_ts(value: str) -> float:
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).timestamp()
        except Exception:
            pass
    return 0.0


def _cutoff(spec: str | None) -> float:
    if not spec:
        return 0.0
    m = re.fullmatch(r"(\d+)\s*([mhd])", spec.strip().lower())
    if m:
        n = int(m.group(1))
        unit = {"m": 60, "h": 3600, "d": 86400}[m.group(2)]
        return datetime.now().timestamp() - n * unit
    try:
        return datetime.strptime(spec, "%Y-%m-%d").timestamp()
    except Exception:
        sys.exit(f"--since invalido: {spec!r} (usa 30m, 24h, 7d o YYYY-MM-DD)")


def _load(cutoff: float) -> list[dict]:
    if not LOG_PATH.exists():
        sys.exit(f"No existe el registro: {LOG_PATH}")
    rows: list[dict] = []
    with open(LOG_PATH, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if _parse_ts(str(rec.get("ts") or "")) < cutoff:
                continue
            rows.append(rec)
    return rows


def _label(rec: dict) -> str:
    name = str(rec.get("chat_name") or "").strip()
    cid = str(rec.get("chat_id") or "").strip()
    return name or cid or "?"


def _when(rec: dict) -> str:
    ts = _parse_ts(str(rec.get("ts") or ""))
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "?"


def _one_line(text: str, width: int = 400) -> str:
    body = re.sub(r"\s+", " ", str(text or "")).strip()
    return body[:width] + ("…" if len(body) > width else "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Consulta el registro de WhatsApp de Hermes (solo lectura).")
    ap.add_argument("--chat", default="", help="filtra por nombre o id de chat (subcadena, sin distinguir mayusculas)")
    ap.add_argument("--since", default="", help="desde: 30m, 24h, 7d o YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=30, help="maximo de mensajes (default 30)")
    ap.add_argument("--chats", action="store_true", help="lista los chats vistos en vez de los mensajes")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    args = ap.parse_args()

    cutoff = _cutoff(args.since)
    rows = _load(cutoff)
    needle = args.chat.casefold().strip()
    if needle:
        rows = [r for r in rows
                if needle in str(r.get("chat_name") or "").casefold()
                or needle in str(r.get("chat_id") or "").casefold()]

    if args.chats:
        chats: dict[str, dict] = {}
        for rec in rows:
            key = str(rec.get("chat_id") or _label(rec))
            entry = chats.setdefault(key, {
                "chat_id": key,
                "chat_name": rec.get("chat_name") or "",
                "chat_type": rec.get("chat_type") or "",
                "count": 0,
                "last_ts": 0.0,
                "last_text": "",
            })
            entry["count"] += 1
            ts = _parse_ts(str(rec.get("ts") or ""))
            if ts >= entry["last_ts"]:
                entry["last_ts"] = ts
                entry["last_text"] = _one_line(rec.get("text") or "", 120)
        ordered = sorted(chats.values(), key=lambda e: e["last_ts"], reverse=True)
        if args.json:
            print(json.dumps(ordered, ensure_ascii=False, indent=2))
            return 0
        if not ordered:
            print("(sin chats en el registro para ese filtro)")
            return 0
        for e in ordered:
            stamp = datetime.fromtimestamp(e["last_ts"]).strftime("%Y-%m-%d %H:%M")
            kind = e["chat_type"] or "chat"
            print(f"{stamp}  [{kind}] {e['chat_name'] or e['chat_id']}  ({e['count']} msj)  · {e['last_text']}")
        return 0

    rows = rows[-max(0, args.limit):] if args.limit else rows
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("(sin mensajes para ese filtro)")
        return 0
    for rec in rows:
        who = str(rec.get("user") or "?")
        kind = str(rec.get("chat_type") or "chat")
        print(f"{_when(rec)}  [{kind}] {_label(rec)} · {who}: {_one_line(rec.get('text') or '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
