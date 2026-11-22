# Servidores MCP

MCP = servidores de herramientas que el agente puede llamar. Aquí están los dos catálogos
que conviven: el de **Hermes** y el de **OpenCode**.

Regla que aprendimos probando: **solo se añaden los que responden a `initialize` sin
credenciales.** Todo lo demás es ruido hasta que el usuario dé la clave.

---

## Hermes (el agente 24/7, en el inspiron)

`~/.hermes/config.yaml`, sección `mcp_servers`. Cuatro activos, los cuatro verificados
respondiendo a `initialize` y `tools/list`:

| Servidor | URL | Estado |
|---|---|---|
| `deepwiki` | `https://mcp.deepwiki.com/mcp` | activo |
| `context7` | `https://mcp.context7.com/mcp` | activo |
| `microsoft-learn` | `https://learn.microsoft.com/api/mcp` | activo |
| `twilio-docs` | `https://mcp.twilio.com/docs` | activo |
| `cloudflare-docs` | `https://docs.mcp.cloudflare.com/mcp` | activo (2 herramientas) |
| `laraplugins` | `https://laraplugins.io/mcp/plugins` | activo (12 herramientas) |

Los seis llevan `connect_timeout: 30`.

```bash
# consultar el estado real
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:9120/api/mcp/servers
# el catálogo de Nous (66 entradas)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:9120/api/mcp/catalog
```

`_save_mcp_server` escribe en `config.yaml` + `mcp_servers`. **El gateway tarda ~35 s en
quedar listo** después de reiniciar: no lo toques antes.

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

`~/.config/opencode/opencode.json`, sección `mcp`. **9 habilitados**:

| Servidor | Tipo | Para qué |
|---|---|---|
| `genoffice` | local | documentos Office, PDF, presentaciones |
| `mikareno` | remoto | seguimiento académico |
| `rea` | local | ingeniería inversa de binarios y artefactos |
| `freecad` | local | CAD |
| `blender` | local | 3D |
| `shopify` | local | la tienda GRUPOSALAS |
| `facebook` | local | publicar en Facebook |
| `meta-ads` | local | anuncios de Meta |
| `servers` | stdio | utilidades varias |

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