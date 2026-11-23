# Pendientes

Lo que falta, en orden de importancia, y qué necesita cada cosa. Nada de esto es un misterio:
casi todo está parado esperando **credenciales del usuario**.

---

## 1. Gmail y Calendar

**Estado:** sin nada. `himalaya` no está instalado, no hay `~/.config/himalaya/`, no hay
`google_token.json`.

**Falta:**

1. Instalar `himalaya` (cliente de correo en línea de comandos).
2. Crear el proyecto en Google Cloud y activar Gmail API + Calendar API.
3. Descargar `client_secret.json` y hacer el flujo OAuth una vez.
4. Guardar el token en `~/.hermes/.env` (no en este repo).

**Alternativa sin fricción:** `google-workspace` MCP, que pide `google_token.json`.
Si el usuario prefiere no tocar Google Cloud, esta vía es más limpia.

---

## 2. Qué es «curia»

**Estado:** sin identificar. El usuario lo mencionó como algo pendiente y no hay nada en el
sistema que responda a ese nombre.

**Falta:** que el usuario diga qué es. Hasta entonces no se puede planificar.

---

## 3. TikTok

**Estado:** sin CLI, sin integración.

**Falta:** clave de API de TikTok para desarrolladores (o usar la vía manual). Publicar en
TikTok desde la terminal no es trivial y seguramente no valga la pena.

---

## 4. Vídeo generado

**Estado:** descartado por coste. No hay opción gratuita.

**Falta:** dinero o una clave de pago (fal.ai, DeepInfra, xAI). Los modelos `free` de
OpenRouter son solo texto.

Si el usuario acepta pagar, el camino más corto es fal.ai.

---

## 5. Audio del portátil

**Estado:** sink `C-Media 58` al **0 %**, micro `59` **MUTED**.

**Falta:** dos comandos.

```bash
pactl set-sink-volume 58 60%
pactl set-source-mute 59 0
```

Sin esto, el STT captura silencio y parece que el agente no oye.

---

## 6. MCPs con credenciales

Añadir cualquiera de estos necesita la clave del usuario. Están las plantillas en
`~/.config/opencode/mcp-configs/mcp-servers.json`.

| MCP | Qué falta |
|---|---|
| `github` | `GITHUB_PERSONAL_ACCESS_TOKEN` (placeholder `YOUR_GITHUB_PAT_HERE`) |
| `firecrawl` | `FIRECRAWL_API_KEY` (placeholder `YOUR_FIRECRAWL_KEY_HERE`) |
| `vercel` | token de Vercel |
| `railway` | token de Railway |
| `cloudflare` | token de Cloudflare |
| `hugging_face` | token de Hugging Face (responde 401 sin él) |
| `supabase` | URL + clave de proyecto |
| `jira` / `confluence` | usuario + token de Atlassian |
| `fal-ai` | clave de fal.ai (de pago) |

**No añadir nada de esto sin la clave.** Un MCP que responde 401 ensucia el arranque.

---

## 7. Hueco en el respaldo: memoria y skills

**Estado:** `~/.hermes/memories/` y `~/.hermes/skills/` no están en el repo.

Es el hueco más serio del respaldo: si el portátil muere, el agente pierde la memoria y las
skills. Se podrían añadir al repo revisándolas a mano (sin secretos), pero no se ha hecho
porque mezclan configuración con datos del usuario.

**Decisión pendiente del usuario:** ¿versionar la memoria del agente o no?

---

## 9. Tercer repo de la petición

El usuario pidió «añade estos 3» pero pasó dos URLs, una repetida:

- `https://github.com/gaboexperimetos-ui/automaticaion-bida-` (repetida dos veces)
- `https://github.com/gaboexperimetos-ui/mikareno-mcp-`

Los dos están integrados y en uso (dashboard y MCP de Mikareno). **Falta identificar el
tercero**: hace falta el nombre o la URL. No se inventa; cuando llegue, se clona, se comprueba
si expone MCP o servicio y se documenta igual que estos dos.

---

## Resuelto el 2026-11-22

| Cosa | Antes | Ahora |
|---|---|---|
| Clave de `freellmapi` | literal en `opencode.json`, en el historial público | `{file:~/.freellmapi-key}`; clave rotada (vieja 401, nueva 200) |
| `.env` de `mikareno-mcp` | versionado con usuario y contraseña reales | fuera del índice, solo en disco (600); `.env.example` en el repo |
| MCP del dashboard en OpenCode | no estaba | `study-platform` (`:3100/mcp`, 9 herramientas) |
| MCP de Mikareno en Hermes (PC) | no estaba | `mikareno` (`:8080/mcp`, 17 herramientas) |
| Repo `mikareno-mcp-` | clon viejo | actualizado con la migración Zig/CDP; servicio reiniciado y probado |
| Documentación de los repos | dispersa | `docs/MCP.md` dice de dónde sale cada servicio y qué clon corre |

---

## Resuelto el 2026-11-21

| Cosa | Antes | Ahora |
|---|---|---|
| Límites de memoria | 2200 / 1375 caracteres, desbordados | 6000 / 4500, con margen |
| `USER.md` | tenía caracteres chinos colados (`最短`) | corregido |
| MCPs de Hermes | 4 | 8 (más `cloudflare-docs`, `laraplugins`, `study-platform` y `mikareno`) |
| Dashboard "Bisa" | aislado en `127.0.0.1:3100` | conectado al agente por MCP vía tailnet, 9 herramientas |
| Copias locales | solo GitHub y el home original | PC + homelab, diarias, 7 días (incluye `~/.hermes` del inspiron) |
| Telegram | dos gateways con el mismo bot, en conflicto | PC principal; inspiron de relevo con `telegram-failover.sh` |
| Crons del inspiron | `--deliver telegram` fallaba con el PC dueño del bot | `--deliver local` + emisor `tg-notify.sh` (solo `sendMessage`) |
| Cron de Mikareno | corría sin el MCP configurado | MCP `mikareno` conectado (17 herramientas) |
| `/tmp` lleno | 7,4 de 7,5 GB, al 100 % | 619 MB, 9 % |
| Unidades systemd fallidas | 1 (bug del script de sync) | 0 |

---

## 8. Constantes que conviene recordar

- El gateway tarda **~35 s** en quedar listo tras reiniciar. No tocarlo antes.
- `hermes "texto"` no funciona; usar `hermes -z "texto"`.
- El sync es bidireccional: un cambio en GitHub se aplica al home en ≤5 minutos.
- `/tmp/opencode` se vacía al reiniciar. No guardar nada persistente ahí.