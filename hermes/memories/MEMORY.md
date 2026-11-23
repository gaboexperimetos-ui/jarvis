# MEMORY.md — notas del agente sobre este entorno

## Máquina (verificada 2026-11-23)
- Host `asus-tuf`, usuario `gabo`, Linux. Workspace `/home/gabo`.
- GPU RTX 3060 Laptop 6 GB; RAM 14 GB (no cargar dos modelos grandes a la vez).
- Router llama.cpp local en `127.0.0.1:8004` (modelo `deepseek-v4pro`, alias `chat`).
- Zona horaria America/Lima (UTC-5). No suspende.

## Proyectos en disco (`/home/gabo`)
- `proyectos/styp` — NOVA: centro de control Zig, servicio `study-platform` en :3100. BD `data/app.db` (fuente de verdad). Espejo `.md` en `notes/`.
- `SegundoCerebro` — vault Obsidian (notas personales, no borrar sin permiso).
- Repos GitHub `gaboexperimetos-ui`: automaticaion-bida, CyberHex, mikareno-mcp.

## Servicios systemd (usuario)
- `hermes-gateway` (el agente), `study-platform` (NOVA :3100).
- `mikareno-mcp`, `genoffice-mcp`, `freellmapi`, etc. Todos `enabled` + `Linger=yes`.

## Herramientas del agente (MCP, verificadas)
- `mikareno` (37 tools): notas, tareas, calendario, mensajes, asistencia, perfil.
- `study-platform` (11 tools): `search_notes`, `get_note`, `create_note`, `get_academic_context`, `get_subject_notes`, `get_study_sheets`.
- Terminal local: acceso a disco, servicios, red, git.
- STT audio: Groq `whisper-large-v3-turbo` (0 €). TTS: `es-EC-LuisNeural`.

## Convenciones
- Responder en español, de usted, breve. No repetir el rollo.
- Verificar el estado real de la máquina antes de afirmar nada.
- No escribir a terceros sin pedido explícito.