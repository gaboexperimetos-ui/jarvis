#!/usr/bin/env python3
"""Resumen diario para Gabo (Telegram).

Junta, con fuentes deterministas y sin depender del criterio del modelo local:
  * mikareno: deberes de la semana / hoy / manana (snapshot mas reciente).
  * Classroom: entregas con fecha en los proximos 10 dias.
  * Gmail: correo no leido e importante de las ultimas 48 h (sin rebotes ni marketing).
  * IA: titulares relevantes de las ultimas 36 h (deduplicados entre dias).

No ejecuta instrucciones del contenido: solo lee, filtra y compone texto.
Si una fuente falla, se omite su seccion y el resto se envia igual.
"""

from __future__ import annotations

import importlib.util
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
HERMES = HOME / ".hermes"
STATE = HERMES / "state"
STATE.mkdir(parents=True, exist_ok=True)
SEEN_NEWS = STATE / "ai-news-seen.json"
SNAP_DIR = HOME / ".cache" / "mikareno-mcp" / "snapshots"
CLASSROOM = HERMES / "scripts" / "classroom.py"
GMAIL_CRED = HOME / ".config" / "mcp-google-gmail" / "credentials.json"

LOCAL_TZ = datetime.now().astimezone().tzinfo
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


# ── utilidades ─────────────────────────────────────────────────────────────
def env(key: str, default: str = "") -> str:
    try:
        for line in (HERMES / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return os.environ.get(key, default)


def http_json(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 30):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def telegram(text: str) -> bool:
    token, chat = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_HOME_CHANNEL")
    if not token or not chat:
        print("Telegram: falta token o chat", file=sys.stderr)
        return False
    payload = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text[:4000],
        "disable_web_page_preview": "true",
    }).encode()
    try:
        d = http_json(f"https://api.telegram.org/bot{token}/sendMessage", payload)
        ok = bool(d.get("ok"))
        if not ok:
            print("Telegram rechazó:", str(d)[:200], file=sys.stderr)
        return ok
    except Exception as e:
        print("Telegram error:", type(e).__name__, str(e)[:150], file=sys.stderr)
        return False


# ── mikareno (snapshot en disco) ───────────────────────────────────────────
def mikareno() -> list[str]:
    snaps = sorted(SNAP_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not snaps:
        return []
    f = snaps[0]
    try:
        data = json.loads(f.read_text(encoding="utf-8", errors="replace")).get("data", {})
    except Exception as e:
        print("mikareno snapshot:", e, file=sys.stderr)
        return []
    ts = data.get("tarea_stats", {}) or {}
    out = [f"• Esta semana: {ts.get('tasksCurrentWeek', 0)} · Hoy: {ts.get('todaysTasks', 0)} · Mañana: {ts.get('tomorrowsTask', 0)}"]
    tp = data.get("tareas_paginadas", {}) or {}
    items = tp.get("pageContent", []) if isinstance(tp, dict) else []
    for t in items[:6]:
        if not isinstance(t, dict):
            continue
        name = t.get("title") or t.get("name") or t.get("description") or "Tarea"
        due = t.get("dueDate") or t.get("date") or t.get("fecha") or ""
        out.append(f"• {str(name)[:70]}" + (f" — {str(due)[:16]}" if due else ""))
    age_h = (datetime.now().timestamp() - f.stat().st_mtime) / 3600
    if age_h > 12:
        out.append(f"  (datos de hace {int(age_h)} h)")
    return out


# ── Classroom ──────────────────────────────────────────────────────────────
def _classroom_module():
    spec = importlib.util.spec_from_file_location("classroom", CLASSROOM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classroom() -> list[str]:
    try:
        mod = _classroom_module()
        token = mod.access_token()
    except Exception as e:
        print("Classroom auth:", e, file=sys.stderr)
        return []

    def gget(path, params):
        url = "https://classroom.googleapis.com/v1" + path + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    now = datetime.now(timezone.utc)
    lim = now + timedelta(days=10)
    rows = []
    try:
        courses = gget("/courses", {"pageSize": 100}).get("courses", [])
    except Exception as e:
        print("Classroom courses:", e, file=sys.stderr)
        return []
    for c in courses:
        cid, cname = c.get("id"), c.get("name", "Curso")
        try:
            work = gget(f"/courses/{cid}/courseWork", {"pageSize": 50}).get("courseWork", [])
        except Exception:
            continue
        for w in work:
            dd = w.get("dueDate") or {}
            if not dd.get("year"):
                continue
            dt_ = w.get("dueTime") or {}
            try:
                due = datetime(dd["year"], dd["month"], dd["day"],
                               dt_.get("hours", 23), dt_.get("minutes", 59), tzinfo=timezone.utc)
            except Exception:
                continue
            if not (now - timedelta(days=14) <= due <= lim):
                continue
            if w.get("state") == "DRAFT":
                continue
            local = due.astimezone(LOCAL_TZ)
            venc = " · VENCIDA" if due < now else ""
            rows.append((due, f"• {cname} — {str(w.get('title', 'Tarea'))[:60]} (vence {DIAS[local.weekday()]} {local.day} {MESES[local.month-1]}, {local:%H:%M}{venc})"))
    rows.sort(key=lambda x: x[0])
    return [r[1] for r in rows[:8]]


# ── Gmail ──────────────────────────────────────────────────────────────────
def gmail() -> list[str]:
    try:
        c = json.loads(GMAIL_CRED.read_text(encoding="utf-8"))
        data = urllib.parse.urlencode({
            "client_id": c["client_id"], "client_secret": c["client_secret"],
            "refresh_token": c["refresh_token"], "grant_type": "refresh_token",
        }).encode()
        tok = http_json("https://oauth2.googleapis.com/token", data)["access_token"]
    except Exception as e:
        print("Gmail auth:", e, file=sys.stderr)
        return []

    def api(path, params):
        url = "https://gmail.googleapis.com/gmail/v1/users/me/" + path + "?" + urllib.parse.urlencode(params, doseq=True)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    noise_from = ("mailer-daemon", "no-reply", "noreply", "notifications@", "newsletter", "marketing@", "info@")
    noise_subj = ("delivery status notification", "undelivered mail", "out of office", "factura", "recibo")
    queries = [
        "is:unread is:important newer_than:2d -category:promotions -category:social -category:forums",
        "is:unread newer_than:1d category:primary",
    ]
    for q in queries:
        try:
            res = api("messages", {"q": q, "maxResults": 12}).get("messages", [])
        except Exception as e:
            print("Gmail query:", e, file=sys.stderr)
            continue
        out = []
        for m in res:
            try:
                d = api(f"messages/{m['id']}", {"format": "metadata", "metadataHeaders": ["From", "Subject"]})
            except Exception:
                continue
            hs = {h["name"]: h["value"] for h in d.get("payload", {}).get("headers", [])}
            frm, subj = hs.get("From", "?"), hs.get("Subject", "(sin asunto)")
            low = (frm + " " + subj).lower()
            if any(n in low for n in noise_from) or any(n in low for n in noise_subj):
                continue
            frm = re.sub(r"<[^>]+>", "", frm).strip().strip('"')[:45]
            out.append(f"• {frm} — {subj[:70]}")
            if len(out) >= 5:
                break
        if out:
            return out
    return []


# ── Noticias de IA ─────────────────────────────────────────────────────────
FEEDS = [
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("Ars Technica", "https://arstechnica.com/ai/feed/"),
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Decoder", "https://the-decoder.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("MIT Tech Review", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
]
AI_KW = ("llm", "model", "open-source", "open source", "release", "launch", "gpt", "claude",
         "gemini", "llama", "qwen", "deepseek", "mistral", "benchmark", "agent", "reasoning",
         "multimodal", "openai", "anthropic", "nvidia", "gpu", "robot", "artificial intelligence")
NOISE = ("launch hn", "ask hn", "show hn", "who is hiring", "is hiring", "hiring ",
         "yc ", "coupon", "discount", "black friday")


def _seen() -> set[str]:
    try:
        return set(json.loads(SEEN_NEWS.read_text()))
    except Exception:
        return set()


def _entries(root):
    """Devuelve (titulo, link, fecha) tanto para RSS 2.0 como para Atom."""
    ns = "{http://www.w3.org/2005/Atom}"
    out = []
    for it in root.findall(".//item"):
        out.append((it.findtext("title") or "", it.findtext("link") or "", it.findtext("pubDate") or ""))
    for it in root.findall(f".//{ns}entry"):
        link = ""
        for l in it.findall(f"{ns}link"):
            if l.get("rel", "alternate") == "alternate":
                link = l.get("href", "")
                break
        out.append((it.findtext(f"{ns}title") or "", link, it.findtext(f"{ns}updated") or it.findtext(f"{ns}published") or ""))
    return out


def _when(value: str):
    from email.utils import parsedate_to_datetime
    try:
        d = parsedate_to_datetime(value)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def ai_news(commit: bool = True) -> list[str]:
    seen = _seen()
    now = datetime.now(timezone.utc)
    cands = []
    for name, url in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 hermes"})
            root = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
        except Exception:
            continue
        for title, link, pub in _entries(root)[:60]:
            title, link = title.strip(), link.strip()
            if not title or not link:
                continue
            low = title.lower()
            if any(n in low for n in NOISE):
                continue
            when = _when(pub)
            if not when or now - when > timedelta(hours=36):
                continue
            score = sum(1 for k in AI_KW if k in low)
            if score == 0:
                continue
            if link in seen:
                continue
            cands.append((when, score, name, title, link))
    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out = []
    chosen_words = []
    per_source = {}
    for when, score, name, title, link in cands:
        if per_source.get(name, 0) >= 1:
            continue
        words = {w for w in re.findall(r"[a-záéíóúñ]{4,}", html.unescape(title).lower())}
        if any(len(words & prev) / max(1, len(words | prev)) >= 0.5 for prev in chosen_words):
            continue
        chosen_words.append(words)
        per_source[name] = per_source.get(name, 0) + 1
        out.append(f"• {html.unescape(title)[:95]} ({name})")
        seen.add(link)
        if len(out) >= 5:
            break
    try:
        if commit:
            SEEN_NEWS.write_text(json.dumps(sorted(seen)[-2000:], ensure_ascii=False))
    except OSError:
        pass
    return out


# ── composición ────────────────────────────────────────────────────────────
def main() -> int:
    dry = "--dry-run" in sys.argv
    now = datetime.now(LOCAL_TZ)
    parts = [f"Buenos días, señor. Resumen del {DIAS[now.weekday()]} {now.day} {MESES[now.month-1]}."]

    sections = [
        ("COLEGIO · mikareno", mikareno()),
        ("CLASSROOM · entregas", classroom()),
        ("CORREO IMPORTANTE", gmail()),
        ("IA · últimas 36 h", ai_news(commit=not dry)),
    ]
    for title, rows in sections:
        if rows:
            parts.append("\n" + title + "\n" + "\n".join(rows))

    text = "\n".join(parts)
    print(text)
    if dry:
        return 0
    ok = telegram(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
