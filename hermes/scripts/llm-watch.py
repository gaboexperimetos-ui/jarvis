#!/usr/bin/env python3
"""Vigilante de nuevos LLM open-source (Hugging Face) -> Telegram.

Corre varias veces al dia (timer). Avisa el mismo dia de modelos nuevos que
sean notables: de organizaciones conocidas, o con traccion real (likes /
descargas). Ignora cuantizaciones, adaptadores y merges para no llenar de
ruido. Guarda los ids ya avisados para no repetir.

Uso:
  llm-watch.py            revisa y avisa por Telegram
  llm-watch.py --dry-run  imprime lo que avisaria, sin enviar
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERMES = Path.home() / ".hermes"
STATE = HERMES / "state"
STATE.mkdir(parents=True, exist_ok=True)
SEEN_FILE = STATE / "llm-watch.json"

NOTABLE = {
    "qwen", "deepseek-ai", "meta-llama", "mistralai", "google", "microsoft", "nvidia",
    "allenai", "ai21labs", "cohere", "tiiuae", "bigcode", "stabilityai", "openai",
    "moonshotai", "x-ai", "01-ai", "baichuan-inc", "internlm", "thudm", "zhipuai",
    "minimaxai", "inclusionai", "tencent", "bytedance", "ibm-granite", "huggingfacetb",
    "liquidai", "unsloth", "thinkingmachines", "apple", "amazon", "salesforce", "ai2",
}
# Variantes que no son "un modelo nuevo" sino derivados.
DERIVED = re.compile(
    r"(gguf|awq|gptq|exl2|onnx|mlx|lora|adapter|adapt|merge|quant|4bit|8bit|fp8|"
    r"w4a16|w8a8|bnb|int4|int8|test|demo|tmp|playground|mirror|copy)",
    re.IGNORECASE,
)


def env(key: str) -> str:
    try:
        for line in (HERMES / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return os.environ.get(key, "")


def telegram(text: str) -> bool:
    token, chat = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_HOME_CHANNEL")
    if not token or not chat:
        print("Telegram: falta token o chat", file=sys.stderr)
        return False
    payload = urllib.parse.urlencode({
        "chat_id": chat, "text": text[:4000], "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read())
        return bool(d.get("ok"))
    except Exception as e:
        print("Telegram error:", type(e).__name__, str(e)[:150], file=sys.stderr)
        return False


def hf(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-llm-watch"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def parse_dt(value: str):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def load_seen() -> set[str]:
    try:
        return set(json.loads(SEEN_FILE.read_text()).get("seen", []))
    except Exception:
        return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps({
        "seen": sorted(seen)[-4000:],
        "updated": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False))


def candidates():
    now = datetime.now(timezone.utc)
    out = {}
    # 1) recien creados (text-generation)
    try:
        for m in hf("https://huggingface.co/api/models?filter=text-generation&sort=createdAt&direction=-1&limit=100"):
            mid = m.get("id") or ""
            created = parse_dt(m.get("createdAt") or "")
            if not mid or not created or now - created > timedelta(days=3):
                continue
            org = mid.split("/", 1)[0].lower()
            likes, dl = int(m.get("likes") or 0), int(m.get("downloads") or 0)
            if org in NOTABLE or likes >= 25 or dl >= 1000:
                out[mid] = (m, created, likes, dl, org)
    except Exception as e:
        print("HF createdAt:", e, file=sys.stderr)
    # 2) en tendencia (capta los que despegaron sin estar en el top por fecha)
    try:
        for m in hf("https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=40"):
            mid = m.get("id") or ""
            created = parse_dt(m.get("createdAt") or "")
            likes = int(m.get("likes") or 0)
            if not mid or not created or now - created > timedelta(days=10):
                continue
            if likes >= 150:
                out.setdefault(mid, (m, created, likes, int(m.get("downloads") or 0), mid.split("/", 1)[0].lower()))
    except Exception as e:
        print("HF trending:", e, file=sys.stderr)
    # 3) descartar derivados
    return {k: v for k, v in out.items() if not DERIVED.search(k)}


def main() -> int:
    dry = "--dry-run" in sys.argv
    seen = load_seen()
    now = datetime.now(timezone.utc)
    found = candidates()
    fresh = []
    for mid, (m, created, likes, dl, org) in found.items():
        if mid in seen:
            continue
        # En la primera pasada no arrastrar un backlog viejo.
        if now - created > timedelta(days=4):
            seen.add(mid)
            continue
        fresh.append((created, mid, likes, dl, org))
    fresh.sort(reverse=True)

    if not fresh:
        print("sin LLM nuevos notables")
        save_seen(seen)
        return 0

    lines = ["Nuevo LLM open source en Hugging Face:"]
    for created, mid, likes, dl, org in fresh[:8]:
        lines.append(f"• {mid}\n  {likes} likes · {dl} descargas\n  https://huggingface.co/{mid}")
        seen.add(mid)
    text = "\n".join(lines)
    print(text)
    if dry:
        return 0
    ok = telegram(text)
    save_seen(seen)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
