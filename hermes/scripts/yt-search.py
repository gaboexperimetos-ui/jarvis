#!/usr/bin/env python3
"""Búsqueda de YouTube para Hermes (usa YouTube Data API v3).

Uso:
  yt-search.py "consulta"           -> 5 resultados
  yt-search.py "consulta" 10        -> 10 resultados

No depende de MCP roto: el agente lo llama por terminal.
Requiere YOUTUBE_API_KEY en ~/.hermes/.env y la YouTube Data API v3 habilitada.
"""
import sys
import os
import json
import urllib.request
import urllib.parse

def api_key():
    env = os.path.expanduser("~/.hermes/.env")
    for line in open(env):
        if line.startswith("YOUTUBE_API_KEY="):
            return line.split("=", 1)[1].strip()
    return os.environ.get("YOUTUBE_API_KEY", "")

def search(query, n=5):
    key = api_key()
    if not key:
        print("ERROR: no hay YOUTUBE_API_KEY en ~/.hermes/.env")
        return
    params = urllib.parse.urlencode({
        "part": "snippet",
        "q": query,
        "maxResults": str(n),
        "type": "video",
        "key": key,
    })
    url = "https://www.googleapis.com/youtube/v3/search?" + params
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            msg = json.loads(body)["error"]["message"]
        except Exception:
            msg = body[:200]
        print(f"ERROR de YouTube: {msg}")
        print("(¿Está habilitada la YouTube Data API v3 en Google Cloud?)")
        return
    items = data.get("items", [])
    if not items:
        print("Sin resultados.")
        return
    print(f"{len(items)} resultado(s) para '{query}':\n")
    for it in items:
        vid = it["id"].get("videoId", "")
        sn = it["snippet"]
        title = sn.get("title", "")
        ch = sn.get("channelTitle", "")
        url = f"https://youtube.com/watch?v={vid}"
        print(f"• {title}\n  canal: {ch}\n  {url}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: yt-search.py "consulta" [n]')
        sys.exit(1)
    q = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    search(q, n)