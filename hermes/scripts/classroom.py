#!/usr/bin/env python3
"""Google Classroom para Hermes (usa Classroom API v3).

Uso:
  classroom.py courses                 -> lista tus cursos
  classroom.py coursework <courseId>   -> tareas del curso
  classroom.py announcements <courseId>-> anuncios del curso
  classroom.py students <courseId>     -> lista de alumnos

Requiere el token OAuth en ~/.config/mcp-google-gmail/credentials.json
con scope de Classroom y la Classroom API habilitada.
"""
import sys
import os
import json
import time
import urllib.request
import urllib.parse

API = "https://classroom.googleapis.com/v1"
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


def get(path, params=None):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            print("ERROR:", json.loads(body)["error"]["message"][:150])
        except Exception:
            print("ERROR:", body[:150])
        return None


def list_courses():
    d = get("/courses", {"pageSize": 30})
    if not d:
        return
    courses = d.get("courses", [])
    if not courses:
        print("No tienes cursos en Classroom.")
        return
    print(f"{len(courses)} curso(s):\n")
    for c in courses:
        print(f"  • [{c.get('id')}] {c.get('name')}  ({c.get('section','')}) - {c.get('enrollmentCode','')}")


def coursework(cid):
    d = get(f"/courses/{cid}/courseWork", {"pageSize": 30})
    if not d:
        return
    items = d.get("courseWork", [])
    if not items:
        print("Sin tareas en este curso.")
        return
    print(f"{len(items)} tarea(s):\n")
    for w in items:
        due = w.get("dueDate", {})
        due_s = f"{due.get('day','?')}/{due.get('month','?')}/{due.get('year','')}" if due else "sin fecha"
        state = w.get("state", "?")
        print(f"  • {w.get('title')}  [{state}] entrega: {due_s}")
        print(f"    {w.get('alternateLink','')}")


def announcements(cid):
    d = get(f"/courses/{cid}/announcements", {"pageSize": 20})
    if not d:
        return
    items = d.get("announcements", [])
    if not items:
        print("Sin anuncios.")
        return
    print(f"{len(items)} anuncio(s):\n")
    for a in items:
        print(f"  • {a.get('text','')[:120]}")


def students(cid):
    d = get(f"/courses/{cid}/students", {"pageSize": 50})
    if not d:
        return
    items = d.get("users", [])
    print(f"{len(items)} alumno(s):\n")
    for s in items:
        name = s.get("name", {}).get("fullName", "?")
        print(f"  • {name} ({s.get('primaryEmail','')})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "courses":
        list_courses()
    elif cmd == "coursework" and len(sys.argv) > 2:
        coursework(sys.argv[2])
    elif cmd == "announcements" and len(sys.argv) > 2:
        announcements(sys.argv[2])
    elif cmd == "students" and len(sys.argv) > 2:
        students(sys.argv[2])
    else:
        print("Comando o argumentos inválidos. Ver docstring.")