# OpenJarvis y OpenClaw frente a nuestro stack (Hermes)

Fecha: 2026-11-23
Fuentes: documentación oficial de ambos proyectos y el inventario real de `~/.hermes`.
No se instaló nada. Este documento compara capacidades, no marketing.

## Qué es cada uno

### OpenJarvis
- Framework **local-first** de investigación de Stanford (Hazy Research / Scaling Intelligence Lab), licencia Apache 2.0.
- No es un asistente cerrado: es una **capa para construir agentes que corren en tu equipo**, con la nube solo cuando hace falta.
- Cinco primitivas: **Intelligence** (catálogo de modelos), **Engine** (Ollama, vLLM, SGLang, llama.cpp, nube), **Agentic Logic** (9 tipos de agente), **Memory** (5 backends) y **Learning** (trazas y enrutado aprendido).
- Trae agentes listos: chat simple, orquestador con herramientas, ReAct, CodeAct (`native_openhands`), RLM, OpenHands, Claude Code, operativo programado y **monitor de largo plazo con compresión de memoria**.
- Memoria con SQLite/FTS5, FAISS, ColBERTv2, BM25 e híbrido RRF; ingesta, chunking, embeddings e inyección de contexto con atribución de fuente.
- Aprendizaje basado en trazas: registra decisiones, latencia, coste y resultado; enruta al mejor modelo/agente/herramienta.
- Benchmarking que trata **energía, FLOPs, latencia y dólares** como restricciones de primer nivel.
- Seguridad: escáner de secretos y PII, guardrails, política de archivos sensibles, auditoría.
- Sandbox Docker/Podman, servidor compatible OpenAI, CLI + GUI, MCP, scheduler (cron/intervalo/una vez).
- Canal WhatsApp mediante **Baileys** (el mismo puente que ya usamos), skills importables de Hermes y OpenClaw.
- Presets: morning digest (Gmail/Calendar/Tasks + voz), deep research con citas, code assistant, monitor programado, chat simple.

### OpenClaw
- **Gateway autoalojado** (MIT) que conecta tus apps de chat con agentes. Un proceso sirve todos los canales.
- Canales: núcleo con A2A, Reef, Telegram y WebChat; plugins oficiales para Discord, Feishu, Google Chat, iMessage, IRC, LINE, Matrix, Mattermost, Teams, Nextcloud, Nostr, QQ, Raft, Signal, Slack, SMS, Synology, Tlon, Twitch, **Voice Call**, WhatsApp y Zalo.
- **Enrutado multiagente** real: cada agente tiene workspace, auth, store de sesiones y SQLite propios; los mensajes se enrutan con *bindings* por canal, cuenta y par (persona/grupo).
- Sesiones: los DMs se colapsan en `main`; los grupos se aíslan por defecto.
- Herramientas: exec, process, terminal, code execution, archivos, ask_user/secrets, web_search (Brave, DuckDuckGo, Exa, Firecrawl, Gemini, Grok, Kimi, MiniMax, Ollama, Perplexity, SearXNG, Tavily), x_search, browser, media, `view_image`, `image_generate`, `music_generate`, `video_generate`, tts.
- Colaboración: subagentes, ACP agents, **Swarm**, Code Mode, Tool Search, sesiones inspeccionables.
- Automatización: cron, heartbeat, hooks, webhooks y **Lobster** (pipelines tipados con aprobaciones reanudables).
- Apps: Control UI web, app de barra de menú en macOS, **nodos iOS/Android** con cámara, grabación de pantalla, ubicación y voz; **A2UI canvas**.
- **Llamadas de voz**: briefs por llamada, informes, conducción en vivo, callbacks, detección de buzón de voz, endpoint propio de voz realtime.
- Plugins y marketplace **ClawHub**; SDK para canales, proveedores, herramientas y hooks.

## Comparación honesta

| Capacidad | OpenJarvis | OpenClaw | Hermes (lo nuestro) | ¿Nos falta? |
|---|---|---|---|---|
| WhatsApp | Baileys | plugin | Baileys + plugin `whatsapp-triage` | No |
| Canales | pocos | ~20+ | **26** plataformas en `plugins/platforms/` | No |
| Telegram | sí | sí | sí | No |
| Enrutado multiagente por canal/par | no (tipos de agente, no routing) | **sí (bindings)** | solo delegación/subagentes | **Sí (OpenClaw)** |
| Workspace/sesión aislada por agente | no | **sí** | perfiles y sesiones, no por par | Parcial |
| Motores de inferencia | Ollama/vLLM/SGLang/llama.cpp/nube | muchos + OAuth | llama.cpp local + OpenRouter/nube | No |
| Memoria | **5 backends + atribución** | memoria + wiki | notas y perfil, sin vectorial | **Sí (OpenJarvis)** |
| Aprendizaje por trazas | **sí** | self-learning de skills | telemetría apagada, sin trazas | Sí, pero no lo necesitamos |
| Benchmark energía/coste | **sí** | no | no | No |
| Sandbox | Docker/Podman | Docker por agente | Docker/Daytona/Modal (soportado, apagado) | Capacidad ya existe |
| Navegador | no | sí | sí | No |
| Búsqueda web | herramientas | 12 proveedores | Firecrawl/SearXNG/Exa/Parallel | No |
| CodeAct / ejecución de código | sí | Code Mode / exec | `execute_code`, terminal | No |
| Skills | catálogo + import | skills + ClawHub | **131 skills** + hubs (ClawHub, GitHub, oficial, skills.sh) | No |
| Cron / programación | cron/intervalo/una vez | cron + heartbeat | cron + timers systemd | No |
| Voz (STT/TTS) | TTS en digest | STT, TTS, **llamadas** | STT CPU, TTS Edge, voice mode, wake word | Llamadas: no aplica |
| Apps / UI | GUI + API | **Control UI + nodos iOS/Android** | TUI/CLI + gateway + NOVA | Nodos: no aplica |
| Generación de imagen/vídeo | no | sí | sí | No |
| A2UI canvas | no | **sí** | no | No aplica |
| MCP | sí | sí | sí (9 servidores) | No |
| Marketplace | skills | **ClawHub** | hubs de skills + plugins | No |
| Deep research con citas | **sí** | parcial | herramientas web + skills | Parcial |
| Digest matutino | **sí** | cron | resumen horario de 10mo | No (ya cubierto) |
| Seguridad/guardrails | **secretos, PII, auditoría** | política de tools, sandbox, aprobaciones | aprobaciones, path security, plugin de seguridad | Parcial |
| Llamadas telefónicas | no | **sí** | no | No aplica |
| Nodos móviles | no | **sí** | no | No aplica |

## Lo que sí vale la pena adoptar

### 1. Memoria vectorial con atribución (de OpenJarvis) — recomendado
Hoy Hermes guarda notas y perfil, pero no indexa el Segundo Cerebro ni las notas de NOVA para recuperarlas por relevancia.
OpenJarvis lo resuelve con SQLite/FTS5 (sin dependencias) o BM25/híbrido.
Aplicado a nosotros: indexar `~/SegundoCerebro` y las notas de NOVA, y que el agente recupere fragmentos con la fuente.
- Coste: 0 €, sin GPU, sin nube.
- Riesgo: bajo (solo lectura del vault; no mueve ni borra notas).
- Utilidad: alta para un asistente personal con segundo cerebro.

### 2. Enrutado multiagente por chat (de OpenClaw) — opcional
Hoy todos los chats van al mismo agente. OpenClaw permite que el grupo de 10mo hable con un agente "colegio" (otra personalidad, otra memoria) y los DMs con el agente personal, con sesiones aisladas.
- Coste: 0 €, pero requiere tocar el gateway o un plugin de enrutado.
- Riesgo: medio (puede romper el flujo actual de WhatsApp).
- Utilidad: media; hoy el triage y el resumen horario ya cubren el caso de 10mo.

### 3. Sandbox de ejecución — ya existe, apagado
Hermes ya soporta Docker/Daytona/Modal. No hace falta copiarlo de ellos; solo decidir si se enciende. En esta máquina (14 GB RAM, 6 GB VRAM) un contenedor extra compite por recursos. No lo recomiendo ahora.

### 4. Trazas, benchmarks y aprendizaje — no para este caso
Es el corazón de OpenJarvis como plataforma de investigación, pero para un asistente personal de WhatsApp no aporta. Añade complejidad y almacenamiento sin mejorar las tareas actuales.

### 5. Llamadas, nodos móviles, A2UI, Lobster, Swarm — no aplica
Son capacidades de OpenClaw para otros productos (telefonía, apps nativas, canvas visual, orquestación masiva). No tenemos ese caso de uso y sumarlas solo engorda el stack.

## Conclusión

No conviene instalar OpenJarvis ni OpenClaw completos: duplicarían WhatsApp, el gateway y el modelo local, y en 14 GB de RAM competirían con lo que ya funciona.
Lo que realmente nos falta y encaja es **memoria vectorial sobre el Segundo Cerebro/NOVA** (OpenJarvis) y, si se quiere, **enrutado por chat** (OpenClaw).
El resto o ya lo tenemos, o no aplica.

## Fuentes
- OpenJarvis: `github.com/open-jarvis/OpenJarvis` (README, `docs/architecture/overview.md`), `openjarvis.stanford.edu`, arXiv 2605.17172.
- OpenClaw: `docs.openclaw.ai` (`concepts/features`, `concepts/multi-agent`, `tools`, `index`), `github.com/openclaw/openclaw`.
- Nuestro stack: `~/.hermes/config.yaml`, `~/.hermes/plugins/`, `~/.hermes/hermes-agent/plugins/platforms/`, `~/.hermes/hermes-agent/tools/`.
