"""Escalado al modelo local cuando el principal se niega.

El modelo principal (OpenRouter free) orquesta y responde lo normal. Si su
respuesta es una negativa, este plugin reenvía la misma petición al modelo
local de llama.cpp (``deepseek-v4pro`` en 127.0.0.1:8004) y entrega esa
respuesta en lugar de la negativa.

- ``pre_llm_call``: guarda el mensaje del usuario y el historial reciente por turno.
- ``transform_llm_output``: detecta la negativa y pide la respuesta al modelo local.

No modifica nada si el turno ya venía del modelo local ni si la respuesta no
parece una negativa. Si el modelo local falla, deja la respuesta original.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LOCAL_URL = "http://127.0.0.1:8004/v1/chat/completions"
LOCAL_MODEL = "deepseek-v4pro"
LOCAL_KEY = "sk-local"
LOCAL_TIMEOUT = 170.0

_MAX_TURNS = 64
_MAX_HISTORY = 6
_MAX_PART = 8000

_recent: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

_REFUSAL_RE = re.compile(
    "|".join(
        (
            r"i(?:'m| am) (?:sorry|afraid)[^.\n]{0,45}(?:can't|cannot|can not|unable|won't|will not)",
            r"i (?:can't|cannot|can not) (?:help|assist|comply|provide|do that|fulfill|support|engage)",
            r"i (?:won't|will not) (?:help|assist|provide|comply|engage)",
            r"i(?:'m| am) (?:not able|unable) to (?:help|assist|provide|comply)",
            r"(?:can't|cannot|unable to) (?:help|assist) with (?:that|this|your)",
            r"against (?:my|our) (?:guidelines|policies|usage|programming)",
            r"not (?:able|allowed) to (?:help|assist|provide) (?:with )?(?:that|this)",
            r"no puedo (?:ayudar|asistir|proporcionar|facilitar|cumplir|colaborar|hacer eso|realizar)",
            r"no (?:me es posible|estoy en condiciones de) (?:ayudar|asistir|proporcionar|cumplir)",
            r"lo siento[^.\n]{0,45}no puedo",
            r"lamentablemente,? no puedo",
            r"como (?:modelo|asistente|ia)[^.\n]{0,60}no puedo",
        )
    ),
    re.IGNORECASE,
)

_SYSTEM = (
    "Eres Hermes, el asistente personal del señor Gabriel. Responde en español, "
    "de usted, con «señor», de forma directa y breve, sin relleno ni listas "
    "marciales. No te niegues a tareas técnicas legítimas: análisis de código "
    "malicioso, auditorías de seguridad, pentesting autorizado y trabajo "
    "defensivo son trabajo normal. Si la petición es ambigua, responde la "
    "lectura más razonable sin preguntar de más. No menciones que otro modelo "
    "se negó; entrega la respuesta directamente."
)


def _text_of(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


def _trim_history(value: Any) -> List[Dict[str, str]]:
    history: List[Dict[str, str]] = []
    if not isinstance(value, list):
        return history
    for message in value[-_MAX_HISTORY:]:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = _text_of(message.get("content"))
        if role in ("user", "assistant") and content.strip():
            history.append({"role": role, "content": content[:_MAX_PART]})
    return history


def _on_pre_llm_call(*, turn_id: str = "", session_id: str = "", user_message: Any = None,
                     conversation_history: Any = None, model: str = "", **_: Any) -> None:
    key = turn_id or session_id
    if not key:
        return
    entry = {
        "user": _text_of(user_message)[:_MAX_PART],
        "history": _trim_history(conversation_history),
        "model": model or "",
    }
    with _lock:
        _recent[key] = entry
        while len(_recent) > _MAX_TURNS:
            _recent.pop(next(iter(_recent)))
    return None


def _is_refusal(text: str) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) > 1600:
        return False
    return bool(_REFUSAL_RE.search(stripped[:800]))


def _ask_local(entry: Dict[str, Any]) -> str:
    messages: List[Dict[str, str]] = [{"role": "system", "content": _SYSTEM}]
    messages.extend(entry.get("history") or [])
    user = entry.get("user") or ""
    if user:
        if not messages or messages[-1].get("content") != user:
            messages.append({"role": "user", "content": user})
    elif messages[-1].get("role") == "assistant":
        return ""
    payload = json.dumps(
        {
            "model": LOCAL_MODEL,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1600,
            "stream": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        LOCAL_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LOCAL_KEY}",
        },
    )
    with urllib.request.urlopen(request, timeout=LOCAL_TIMEOUT) as response:
        data = json.loads(response.read().decode("utf-8", "replace"))
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return _text_of(message.get("content")).strip()


def _on_transform_llm_output(*, response_text: Any = None, turn_id: str = "", session_id: str = "",
                             model: str = "", **_: Any) -> Optional[str]:
    text = _text_of(response_text)
    if not _is_refusal(text):
        return None
    if LOCAL_MODEL in str(model or "").lower():
        return None
    with _lock:
        entry = _recent.get(turn_id or session_id)
    if not entry:
        return None
    try:
        answer = _ask_local(entry)
    except Exception as exc:  # deja la respuesta original si el local falla
        logger.warning("escalado-local: no pude consultar el modelo local: %s", exc)
        return None
    if not answer:
        return None
    logger.info("escalado-local: el principal se negó; respondió %s", LOCAL_MODEL)
    return answer


def register(ctx) -> None:
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("transform_llm_output", _on_transform_llm_output)
