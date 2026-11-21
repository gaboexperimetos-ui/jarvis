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

Los cuatro llevan `connect_timeout: 30`.

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
| `cloudflare` | pide clave / token |
| `vercel` | pide clave |
| `railway` | pide clave |
| `postman` | pide clave |
| `hugging_face` | responde **401** sin token |
| el resto del catálogo Nous | OAuth o claves |

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
   npx -y @modelcontextprotocol/server-<nombre>   # si es stdio
   curl -s <url> -X POST -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
   ```
2. Añadir a `opencode.json` con `"enabled": true`.
3. Reiniciar OpenCode.
4. Si pide clave, **no añadirlo**: dejar la entrada en el catálogo con el placeholder y
   anotarlo en `PENDIENTES.md`.

---

## Reglas

- **Sin credenciales del usuario no se añade nada.** Un MCP que responde 401 en el
  `tools/list` ensucia el arranque y no sirve.
- Los MCP de Hermes y los de OpenCode son **catálogos separados**. Añadir uno no añade el otro.
- Si un MCP empieza a fallar, quitarlo antes de depurar el agente: un MCP roto puede
  tumbar el arranque entero.