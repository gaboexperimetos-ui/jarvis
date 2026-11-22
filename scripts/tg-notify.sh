#!/usr/bin/env python3
"""Envía texto a Telegram sin hacer polling (Bot API sendMessage).

El gateway del inspiron no hace getUpdates cuando el PC es el dueño del bot, así
que la entrega integrada de los crons no puede usarlo. Este script lee el token
de un fichero aparte y envía por HTTPS. Telegram permite varios remitentes a la
vez con el mismo token; el conflicto es solo entre getUpdates.

Uso:  printf '%s' "texto" | tg-notify.sh
      tg-notify.sh "texto"
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

home = pathlib.Path.home()
token_file = pathlib.Path(os.environ.get("TG_SEND_TOKEN_FILE", home / ".hermes/telegram-send.token"))
chat_file = pathlib.Path(os.environ.get("TG_SEND_CHAT_FILE", home / ".hermes/telegram-send.chat"))

try:
    token = token_file.read_text().strip()
    chat = chat_file.read_text().strip()
except OSError as exc:
    sys.exit(f"tg-notify: no puedo leer {exc.filename}")

text = (sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()).strip()
if not text:
    sys.exit("tg-notify: nada que enviar")
if not token or not chat:
    sys.exit("tg-notify: token o chat vacíos")


def chunks(value, size=3800):
    while value:
        cut = value.rfind("\n", 0, size)
        if cut < size // 2:
            cut = size
        yield value[:cut]
        value = value[cut:].lstrip("\n")


for part in chunks(text):
    payload = urllib.parse.urlencode(
        {"chat_id": chat, "text": part, "disable_web_page_preview": "true"}
    ).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=payload
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        sys.exit(f"tg-notify: HTTP {exc.code}")
    except Exception as exc:
        sys.exit(f"tg-notify: {type(exc).__name__}")
    if not body.get("ok"):
        sys.exit(f"tg-notify: {body.get('description', 'error desconocido')}")

print(f"enviado a {chat}")
