"""Triage de WhatsApp para Hermes.

Objetivo del dueno:
- Leer TODO el WhatsApp (DMs y grupos).
- NO responder nada salvo que el mensaje traiga el codigo ``!Hermes``.
- Analizar lo demas: si es importante (deberes, tareas, examenes, comunicados,
  o viene de un chat de 10mo), dejar una nota en NOVA y avisar por Telegram.
- Registrar cada mensaje en ``~/.hermes/logs/whatsapp-inbox.jsonl`` para que el
  agente pueda consultarlo despues.

Enganche: hook de plugin ``post_gateway_admission``. Devolver
``{"action": "handled"}`` consume el mensaje (no se responde); devolver ``None``
lo deja pasar al agente (solo para ``!Hermes``).

No ejecuta instrucciones que vengan en el texto de los mensajes: solo clasifica
y registra. Fallo seguro: si algo falla, consume el mensaje para no responder
por accidente (salvo que traiga el codigo).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

HERMES_HOME = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
ENV_PATH = HERMES_HOME / ".env"
LOG_DIR = HERMES_HOME / "logs"
LOG_PATH = LOG_DIR / "whatsapp-inbox.jsonl"

DEFAULT_TRIGGER = "!Hermes"
NOVA_DEFAULT_URL = "http://127.0.0.1:3100/mcp"
EXTRA_ENV_PATHS = (Path("/home/gabo/proyectos/styp/.env"),)

_log_lock = threading.Lock()

# Palabras que delatan deberes, examenes o comunicados escolares.
IMPORTANT_KEYWORDS = (
    "deber", "deberes", "tarea", "tareas", "trabajo", "trabajos", "taller",
    "leccion", "lección", "examen", "examenes", "exámenes", "prueba", "pruebas",
    "evaluacion", "evaluación", "calificacion", "calificación", "nota",
    "comunicado", "comunicados", "circular", "convocatoria", "reunion", "reunión",
    "matricula", "matrícula", "entrega", "entregar", "plazo", "fecha limite",
    "fecha límite", "urgente", "recordatorio", "aviso", "importante",
    "proyecto", "investigacion", "investigación", "lectura", "leer", "cuaderno",
    "actividad", "actividades", "recuperacion", "recuperación", "supletorio",
    "trimestre", "parcial", "deber de", "subir al", "plataforma",
)

TEN_RE = re.compile(
    r"(?:\b10\s*(?:mo|mo\.|º|°|a|b|c|-?1|-?2)\b|\bd[eé]cimo\b|\b10mo\b)",
    re.IGNORECASE,
)


def _read_setting(name: str, default: str = "") -> str:
    """Prioriza os.environ; si no, lee ~/.hermes/.env (sin exponer el valor)."""
    value = os.environ.get(name)
    if value:
        return value.strip()
    for path in (ENV_PATH, *EXTRA_ENV_PATHS):
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, raw = line.partition("=")
                if key.strip() == name:
                    return raw.strip().strip('"').strip("'")
        except Exception:
            continue
    return default


def _trigger() -> str:
    return _read_setting("WHATSAPP_TRIGGER", DEFAULT_TRIGGER) or DEFAULT_TRIGGER


def _ten_chat_ids() -> frozenset[str]:
    """Chats de 10mo por id (env WA_10MO_CHATS, separados por coma).

    El grupo real de padres suele tener JID numérico, no "10mo" en el nombre.
    Se acepta el id completo y su parte antes de ``@``.
    """
    raw = _read_setting("WA_10MO_CHATS", "")
    out: set[str] = set()
    for part in raw.split(","):
        p = part.strip().lower()
        if not p:
            continue
        out.add(p)
        out.add(p.split("@", 1)[0])
    return frozenset(out)


def _is_ten_chat(chat_id: str) -> bool:
    ids = _ten_chat_ids()
    if not ids:
        return False
    cid = str(chat_id or "").strip().lower()
    return cid in ids or cid.split("@", 1)[0] in ids


def _append_log(record: dict[str, Any]) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False)
        with _log_lock:
            with open(LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except Exception:
        logger.debug("whatsapp-triage: no pude escribir el log", exc_info=True)


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float = 8.0) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", **headers}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", "replace")
    try:
        return json.loads(body)
    except Exception:
        return {"raw": body}


def _telegram_send(text: str) -> bool:
    token = _read_setting("TELEGRAM_BOT_TOKEN")
    chat = _read_setting("TELEGRAM_HOME_CHANNEL") or _read_setting("TELEGRAM_ALLOWED_USERS")
    if not token or not chat:
        return False
    result = _post_json(
        f"https://api.telegram.org/bot{token}/sendMessage",
        {"chat_id": chat, "text": text[:3800], "disable_web_page_preview": True},
        {},
    )
    return bool(result.get("ok"))


def _nova_create_note(title: str, content: str, tags: str) -> Optional[dict[str, Any]]:
    key = (
        _read_setting("CUSTOM_MCP_API_KEY")
        or _read_setting("NOVA_MCP_KEY")
        or _read_setting("STUDY_PLATFORM_MCP_KEY")
    )
    if not key:
        return None
    url = _read_setting("NOVA_MCP_URL", NOVA_DEFAULT_URL) or NOVA_DEFAULT_URL
    tag_list = [t.strip() for t in str(tags or "").split(",") if t.strip()]
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "create_note", "arguments": {"title": title, "content": content, "tags": tag_list}},
    }
    result = _post_json(url, payload, {"x-api-key": key})
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(f"NOVA rechazó la nota: {result['error']}")
    return result


def _looks_important(text: str, chat_name: str, chat_id: str) -> tuple[bool, bool, list[str]]:
    low = (text or "").casefold()
    hits = [k for k in IMPORTANT_KEYWORDS if k in low]
    # "nota"/"notas" como calificacion escolar, pero "nota de voz" es un audio normal.
    if "voz" in low or "[audio]" in low or "audio" in low:
        hits = [k for k in hits if k not in ("nota", "notas")]
    ten = bool(TEN_RE.search(f"{chat_name or ''} {chat_id or ''} {text or ''}")) or _is_ten_chat(chat_id)
    return bool(hits) or ten, ten, hits


async def _handle(*, platform: str = "", source: Any = None, text: str = "", message_id: str = "", **_: Any) -> Any:
    if str(platform or "").lower() != "whatsapp":
        return None

    src = source if isinstance(source, dict) else {}
    chat_id = str(src.get("chat_id") or "")
    chat_name = str(src.get("chat_name") or "")
    user_name = str(src.get("user_name") or src.get("user_id") or "")
    chat_type = str(src.get("chat_type") or "")
    body = str(text or "")
    trigger = _trigger()
    is_trigger = bool(trigger) and trigger.casefold() in body.casefold()

    def _work() -> None:
        _append_log(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "chat_id": chat_id,
                "chat_name": chat_name,
                "chat_type": chat_type,
                "user": user_name,
                "message_id": message_id,
                "trigger": is_trigger,
                "text": body[:4000],
            }
        )
        if is_trigger or not body.strip():
            return
        important, ten, hits = _looks_important(body, chat_name, chat_id)
        if not important:
            return
        label = chat_name or chat_id or "WhatsApp"
        head = body.strip().replace("\n", " ")[:60]
        title = f"WhatsApp {label}: {head}"
        if len(title) > 120:
            title = title[:117] + "..."
        tags = "whatsapp,importante" + (",10mo" if ten else "")
        content = (
            f"De: {user_name}\n"
            f"Chat: {label} ({chat_type or 'chat'})\n"
            f"Fecha: {time.strftime('%Y-%m-%d %H:%M')}\n"
            f"Coincidencias: {', '.join(hits) if hits else '(chat 10mo)'}\n\n"
            f"{body}"
        )
        try:
            _nova_create_note(title, content, tags)
        except Exception:
            logger.warning("whatsapp-triage: fallo al crear nota en NOVA", exc_info=True)
        try:
            icon = "📚" if ten else "⚠️"
            _telegram_send(f"{icon} WhatsApp importante · {label} · {user_name}\n{body[:1500]}")
        except Exception:
            logger.warning("whatsapp-triage: fallo al avisar por Telegram", exc_info=True)

    try:
        await asyncio.to_thread(_work)
    except Exception:
        logger.warning("whatsapp-triage: error procesando mensaje", exc_info=True)

    # Solo el mensaje con el codigo llega al agente; todo lo demas se consume.
    return None if is_trigger else {"action": "handled"}


def register(ctx: Any) -> None:
    ctx.register_hook("post_gateway_admission", _handle)
    print("[whatsapp-triage] plugin registrado (post_gateway_admission)", flush=True)
