---
description: WiFi skill — escanear redes, capturar handshake o extraer la PSK actual
---

Usa la skill wifi instalada en ~/.config/opencode/skills/wifi (lee su SKILL.md si hace falta).
El comando real es `wifi` en el PATH (/home/gabo/bin/wifi).

Argumentos del usuario: $ARGUMENTS

- Sin argumentos: ejecuta `wifi scan` y muestra la tabla de redes (no usa modo monitor).
- "captura N" o "capture": ejecuta `wifi capture N` (avisa que activa modo monitor y desconecta).
- "brute" o "router": ejecuta `wifi --brute` (solo contra routers del usuario).
- Cualquier otra cosa: muestra `wifi --help`.
