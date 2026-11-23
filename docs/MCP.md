# Servidores MCP

MCP = servidores de herramientas que el agente puede llamar. Aquí están los dos catálogos
que conviven: el de **Hermes** y el de **OpenCode**.

Regla que aprendimos probando: **solo se añaden los que responden a `initialize` sin
credenciales.** Todo lo demás es ruido hasta que el usuario dé la clave.

---

## Hermes (el agente 24/7, en el inspiron)

`~/.hermes/config.yaml`, sección `mcp_servers`. Ocho activos, verificados respondiendo a
`initialize` y `tools/list`:

| Servidor | URL | Estado |
|---|---|---|
| `deepwiki` | `https://mcp.deepwiki.com/mcp` | activo |
| `context7` | `https://mcp.context7.com/mcp` | activo |
| `microsoft-learn` | `https://learn.microsoft.com/api/mcp` | activo |
| `twilio-docs` | `https://mcp.twilio.com/docs` | activo |
| `cloudflare-docs` | `https://docs.mcp.cloudflare.com/mcp` | activo (2 herramientas) |
| `laraplugins` | `https://laraplugins.io/mcp/plugins` | activo (12 herramientas) |
| `study-platform` | `http://100.115.62.97:3101/mcp` | activo (9 herramientas) |
| `mikareno` | `http://100.115.62.97:8080/mcp` | activo (17 herramientas) |

Los ocho llevan `connect_timeout: 30`.

El PC (Hermes principal) usa las mismas dos entradas locales: `study-platform` en
`http://127.0.0.1:3100/mcp` y `mikareno` en `http://127.0.0.1:8080/mcp`.

### `study-platform` — el dashboard "Bisa"

El dashboard académico (`~/proyectos/styp`, servicio `study-platform`) ya trae su propio
servidor MCP en `POST /mcp`, autenticado con la cabecera `X-API-Key`. No se construyó nada
nuevo: se conectó el que existe.

El proceso escucha en `127.0.0.1:3100` del portátil, así que el inspiron no lo alcanza
directo. Se publica **solo en la tailnet** con un reenvío TCP crudo de Tailscale, sin abrir
puertos a la LAN, sin firewall y sin depender de MagicDNS (el inspiron tiene
`/etc/resolv.conf` inmutable y no resuelve `*.ts.net`):

```bash
# en el portátil, una vez (persiste en el estado de tailscaled)
tailscale serve --bg --tcp=3101 tcp://127.0.0.1:3100
tailscale serve status
```

Queda accesible como `http://100.115.62.97:3101` y `http://asus-tuf.tail7deabb.ts.net:3101`.
Además sigue el `tailscale serve` HTTPS en el 443 para abrir el dashboard por nombre desde
un navegador con MagicDNS:

```bash
tailscale serve --bg 3100        # https://asus-tuf.tail7deabb.ts.net/
```

La clave **no se versiona**. Vive en `~/.hermes/.env` del inspiron (excluido del sync) y el
`config.yaml` la referencia con `${STUDY_PLATFORM_MCP_KEY}`, que Hermes expande al conectar:

```yaml
  study-platform:
    url: "http://100.115.62.97:3101/mcp"
    headers:
      X-API-Key: "${STUDY_PLATFORM_MCP_KEY}"
    connect_timeout: 30
```

Herramientas (9): `search_notes`, `get_note`, `create_note`, `get_academic_context`,
`get_subject_notes`, `get_study_sheets`, `app_list_backups`, `app_backup_now`, `app_ai_cost`.

Verificación real, con la clave puesta y sin ella:

```bash
curl -s -X POST http://100.115.62.97:3101/mcp \
  -H 'Content-Type: application/json' -H "X-API-Key: $STUDY_PLATFORM_MCP_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -c 200
# sin la cabecera: HTTP 401

hermes mcp test study-platform     # ✓ Connected, 9 tools discovered
```

Prueba de punta a punta desde el agente (2026-11-21): pidió `get_academic_context` y
devolvió el promedio real de Lengua y Literatura, `5,51`. La UI del dashboard usa
`AUTH_DISABLED=true`; el MCP **sí** exige la clave.

> El `~/.hermes` que se espeja a este repo es el del **portátil**, no el del inspiron donde
> corre el agente. Por eso esta entrada no aparece en `hermes/config.yaml` del repo: el
> bloque de arriba es la fuente para reproducirla.

```bash
# consultar el estado real
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:9120/api/mcp/servers
# el catálogo de Nous (66 entradas)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:9120/api/mcp/catalog
```

`_save_mcp_server` escribe en `config.yaml` + `mcp_servers`. **El gateway tarda ~35 s en
quedar listo** después de reiniciar: no lo toques antes.

### `mikareno` — seguimiento académico

El MCP de Mikareno corre en el **portátil** (`0.0.0.0:8080`) y el inspiron lo alcanza directo
por la tailnet en `http://100.115.62.97:8080/mcp`, sin cabecera ni clave. Es el que usa el cron
`seguimiento-mikareno`; antes no estaba en el inspiron y ese cron corría a ciegas.

```yaml
  mikareno:
    url: "http://100.115.62.97:8080/mcp"
    connect_timeout: 30
```

```bash
hermes mcp test mikareno     # ✓ Connected, 17 tools discovered
```

Limitación: si el PC está apagado, el inspiron no alcanza Mikareno (el MCP vive en el PC). El
cron falla entonces con un error claro, sin inventar datos.

**De dónde sale ese servicio.** El código es el repo privado
`github.com/gaboexperimetos-ui/mikareno-mcp-`, clonado en `~/mikareno-mcp` y arrancado por
`mikareno-mcp.service` (`venv/bin/python server.py`, `EnvironmentFile=.env`). El `.env` con el
usuario y la contraseña de Mikareno vive **solo en disco** (600) y no se versiona; la plantilla
pública es `.env.example`. El `server.py` sigue siendo el servidor real: la migración a Zig del
repo está iniciada pero no terminada, así que no se sustituye el servicio por el binario Zig.

**El dashboard.** El repo público `github.com/gaboexperimetos-ui/automaticaion-bida-` es la
plataforma NOVA. El clon que corre es `~/proyectos/styp` (servicio `study-platform`, binario Zig
`zig-out/bin/study-platform`); el directorio `~/proyectos/automaticaion-bida-` es un clon viejo
del mismo repo y no es el que sirve. Su MCP sale del propio binario en `/mcp` (9 herramientas).
Los dos repos se pueden usar desde OpenCode por los MCP `mikareno` y `study-platform`.

### Los que NO se añadieron, y por qué

| Servidor | Motivo |
|---|---|
| `memxus` | responde a `initialize` con 29 herramientas, pero al llamarlas da `Missing bearer token` |
| `arcmira` | `No credential was sent` |
| `huggingface` | sesión obligatoria; sin token no lista herramientas |
| `gitmcp` | exige cabecera `Mcp-Session-Id` |
| `sentry`, `docker`, `linear`, `confluent`, `qdrant`, `zep`, `groq`, `wolfram` | `initialize` OK pero `tools/list` vacío sin sesión |
| `npm` | `Unauthorized` |
| `smithery` | redirige (308), no es un servidor directo |
| `cloudflare` (workers) | pide clave / token |
| `vercel` | `NO` — pide autenticación |
| `railway` | pide clave |
| `postman` | `NO` |
| `hugging_face` | responde **401** sin token |
| el resto del catálogo Nous | OAuth o claves |

> Los que dan `initialize` OK pero `tools/list` vacío no sirven: Hermes los marca como
> activos y luego falla al usarlos. Solo se añaden los que **cuentan herramientas de verdad**.

---

## OpenCode (la interfaz del portátil)

`~/.config/opencode/opencode.json`, sección `mcp`. **10 habilitados**:

| Servidor | Tipo | Para qué |
|---|---|---|
| `genoffice` | local | documentos Office, PDF, presentaciones |
| `mikareno` | remoto | seguimiento académico (17 herramientas) |
| `study-platform` | remoto | dashboard NOVA: notas, promedios, respaldos (9 herramientas) |
| `rea` | local | ingeniería inversa de binarios y artefactos |
| `freecad` | local | CAD |
| `blender` | local | 3D |
| `shopify` | local | la tienda GRUPOSALAS |
| `facebook` | local | publicar en Facebook |
| `meta-ads` | local | anuncios de Meta |
| `servers` | stdio | utilidades varias |

Las claves se referencian con `{file:...}` (por ejemplo `study-platform` usa
`~/.config/opencode/secrets/study-platform-mcp-key`, ignorado por git), nunca en claro: el repo
es público y una clave que llegue al índice hay que rotarla aunque se borre después.

### Catálogo de plantillas: 37 servidores

`~/.config/opencode/mcp-configs/mcp-servers.json` tiene 37 entradas con placeholders,
listas para cuando haya credenciales:

```
nexus, ito-compute, jira, github, firecrawl, supabase, ecc-memory-vault, memory,
omega-memory, longhand, deja-vu, sequential-thinking, vercel, railway,
cloudflare-docs, cloudflare-workers-builds, cloudflare-workers-bindings,
cloudflare-observability, clickhouse, exa-web-search, parallel-search, arcmira,
context7, codescene, magic, memxus, filesystem, playwright, fal-ai, browserbase,
browser-use, devfleet, token-optimizer, laraplugins, confluence, evalview,
mnemosyne-os
```

### Cómo se añade uno nuevo

1. Comprobar que responde **sin** credenciales:

   ```bash
   curl -s -X POST <url> -H 'Content-Type: application/json' \
     -H 'Accept: application/json, text/event-stream' \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
   ```

2. **Y que `tools/list` devuelva nombres de verdad**, no vacío:

   ```bash
   curl -s -X POST <url> -H 'Content-Type: application/json' \
     -H 'Accept: application/json, text/event-stream' \
     -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | grep -o '"name"' | wc -l
   ```

   Muchos servidores dan `initialize` correcto y `tools/list` vacío si no hay sesión.
   Esos **no sirven**: Hermes los marca como activos y fallan al usarlos.

3. Añadir a `~/.hermes/config.yaml` en `mcp_servers:` con `url` y `connect_timeout: 30`.
4. `systemctl --user restart hermes-gateway` y esperar **~45 s**.
5. Verificar: `curl -H "Authorization: Bearer $TOKEN" http://localhost:9120/api/mcp/servers`.
6. Si pide clave, **no añadirlo**: dejar la entrada en el catálogo con el placeholder y
   anotarlo en `PENDIENTES.md`.

---

## Reglas

- **Sin credenciales del usuario no se añade nada.** Un MCP que responde 401 en el
  `tools/list` ensucia el arranque y no sirve.
- Los MCP de Hermes y los de OpenCode son **catálogos separados**. Añadir uno no añade el otro.
- Si un MCP empieza a fallar, quitarlo antes de depurar el agente: un MCP roto puede
  tumbar el arranque entero.