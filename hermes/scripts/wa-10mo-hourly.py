#!/usr/bin/env python3
"""Resumen horario de los chats de 10mo.

Lee el log que escribe el plugin whatsapp-triage
(``~/.hermes/logs/whatsapp-inbox.jsonl``), filtra los mensajes de los chats de
10mo desde la ultima ejecucion, y deja una nota-resumen en NOVA + un aviso por
Telegram. Recordar la marca de tiempo en ``~/.hermes/state/wa-10mo-last.json``
evita repetir mensajes.

No ejecuta instrucciones del texto: solo agrupa y resume.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

PLUGIN = Path.home() / ".hermes" / "plugins" / "whatsapp-triage" / "__init__.py"
STATE = Path.home() / ".hermes" / "state" / "wa-10mo-last.json"


def _load_plugin():
    spec = importlib.util.spec_from_file_location("wa_triage", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_ts(value: str) -> float:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").timestamp()
    except Exception:
        return 0.0


def _load_last() -> float:
    try:
        return float(json.loads(STATE.read_text(encoding="utf-8")).get("ts", 0))
    except Exception:
        return time.time() - 3600


def _save_last(ts: float) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"ts": ts}), encoding="utf-8")


def main() -> int:
    wa = _load_plugin()
    pattern = re.compile(
        wa._read_setting("WA_10MO_PATTERN", r"(?:\b10\s*(?:mo|mo\.|º|°|a|b|c|-?1|-?2)\b|\bd[eé]cimo\b|\b10mo\b)"),
        re.IGNORECASE,
    )
    now = time.time()
    last = _load_last()
    seen: set[str] = set()
    items: list[dict] = []
    log = wa.LOG_PATH
    if log.exists():
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = _parse_ts(str(rec.get("ts") or ""))
                if ts <= last:
                    continue
                hay = f"{rec.get('chat_name', '')} {rec.get('chat_id', '')}"
                if not pattern.search(hay):
                    continue
                key = str(rec.get("message_id") or f"{ts}-{rec.get('text','')[:40]}")
                if key in seen:
                    continue
                seen.add(key)
                items.append(rec)
    _save_last(now)
    if not items:
        print(f"[wa-10mo] sin mensajes nuevos de 10mo (desde {datetime.fromtimestamp(last):%H:%M})")
        return 0

    important = 0
    lines: list[str] = []
    for rec in items[:40]:
        body = str(rec.get("text") or "").strip().replace("\n", " ")
        if not body:
            continue
        _, _, hits = wa._looks_important(body, str(rec.get("chat_name") or ""), str(rec.get("chat_id") or ""))
        mark = "⚠️" if hits else "•"
        if hits:
            important += 1
        lines.append(
            f"{mark} [{str(rec.get('ts') or '')[11:16]}] {rec.get('chat_name') or rec.get('chat_id')} · "
            f"{rec.get('user') or '?'}: {body[:400]}"
        )
    if not lines:
        print("[wa-10mo] mensajes sin texto; nada que resumir")
        return 0

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"10mo · resumen {stamp}"
    content = f"Resumen de {len(lines)} mensaje(s) de 10mo (última hora).\n\n" + "\n".join(lines)
    try:
        wa._nova_create_note(title, content, "whatsapp,10mo,resumen")
        print(f"[wa-10mo] nota creada: {title}")
    except Exception as exc:
        print(f"[wa-10mo] fallo nota NOVA: {exc}", file=sys.stderr)
    try:
        wa._telegram_send(f"📚 Resumen 10mo ({stamp})\n" + "\n".join(lines)[:3500])
        print(f"[wa-10mo] Telegram enviado ({len(lines)} mensajes, {important} marcados)")
    except Exception as exc:
        print(f"[wa-10mo] fallo Telegram: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
