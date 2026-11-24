#!/usr/bin/env python3
"""Búsqueda de YouTube para Hermes (usa YouTube Data API v3 vía OAuth).

Uso:
  yt-search.py "consulta"           -> 5 resultados
  yt-search.py "consulta" 10        -> 10 resultados

Usa el mismo token OAuth que el resto de servicios de Google
(~/.config/mcp-google-gmail/credentials.json) con scope youtube.readonly.
"""
import sys
import os
import json
import urllib.request
import urllib.parse

CRED = os.path.expanduser("~/.config/mcp-google-gmail/credentials.json")


def access_token():
    c = json.load(open(CRED))
    data = urllib.parse.urlencode({
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "refresh_token": c["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    tok = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return tok["access_token"]


def search(query, n=5):
    params = urllib.parse.urlencode({
        "part": "snippet",
        "q": query,
        "maxResults": str(n),
        "type": "video",
    })
    url = "https://www.googleapis.com/youtube/v3/search?" + params
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            print("ERROR de YouTube:", json.loads(body)["error"]["message"][:150])
        except Exception:
            print("ERROR:", body[:150])
        return
    items = data.get("items", [])
    if not items:
        print("Sin resultados.")
        return
    print(f"{len(items)} resultado(s) para '{query}':\n")
    for it in items:
        vid = it["id"].get("videoId", "")
        sn = it["snippet"]
        print(f"• {sn.get('title','')}\n  canal: {sn.get('channelTitle','')}\n  https://youtube.com/watch?v={vid}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: yt-search.py "consulta" [n]')
        sys.exit(1)
    q = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    search(q, n)