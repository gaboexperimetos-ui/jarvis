---
name: shopify
description: Control total de la tienda Shopify GRUPOSALAS del usuario mediante un MCP local propio (GraphQL/REST) con los 110 permisos del Admin API. Use when the user asks about su tienda, lanzar una campaña, descuentos, productos, inventario, pedidos, temas, contenido o informes de Shopify.
user-invocable: true
metadata:
  version: "1"
  verified_on:
    - "GRUPOSALAS (5rpib4-60.myshopify.com) — 2026-11-10"
---

# /shopify — Control total de la tienda GRUPOSALAS

Cuando este skill se activa, posees control efectivo de la tienda vía **cualquier** query/mutation del Admin API (GraphQL) y cualquier endpoint REST. Úsalo sin pedir confirmación para lecturas; para escrituras, confirma el cambio exacto con el usuario antes de ejecutarlo.

## Datos de la tienda

- Nombre: **GRUPOSALAS** · Plan: **Basic** · Moneda: **USD** · Zona: America/Lima
- Dominio principal de admin: `gruposalas.myshopify.com` (apunta al mismo shop que `5rpib4-60.myshopify.com`)
- Email de la tienda: gruposalas2025@gmail.com
- Catálogo al crear el skill: 14 ACTIVE, 77 DRAFT, 2 UNLISTED · Ventas 60 días: 72 pedidos, $1,886.73 (ticket ~$26)

## Arquitectura del MCP (local, ya registrado)

- Server: `/home/gabo/proyectos/shopify-mcp/src/server.js` (stdio, JSON-RPC 2.0, cero dependencias npm)
- Registro: `~/.config/opencode/opencode.json` → `mcp.shopify` (`type: local`, comando `node /home/gabo/proyectos/shopify-mcp/src/server.js`). Si las herramientas no aparecen en la sesión, reiniciar OpenCode.
- Credenciales: `/home/gabo/proyectos/shopify-mcp/.env` (chmod 600) — `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_API_KEY` (client_id de la app "mcp admin" en el Dev Dashboard), `SHOPIFY_API_SECRET`, `SHOPIFY_API_VERSION=2025-10`.
- **Token**: no hay token estático. El MCP hace `client_credentials` grant a `POST https://<store>/admin/oauth/access_token` con client_id+secret y cachea ~24h, re-mintiendo solo. Caducidad → no hacer nada, se renueva. Si falla 401, la app no está Released/Installed (ver abajo).
- Requests directos a la API desde shell (sin MCP) también son válidos usando el mismo mint (ver "Recetas").

### Herramientas MCP expuestas

- `shop_info` — nombre, dominio, plan, currencyCode (usa `{ shop { ... } }`)
- `list_products({limit})` — id/title/handle/status/inventario/tags
- `list_orders({limit, status})` — pedidos recientes (REST, cualquier estado)
- `shopify_graphql({query, variables})` — **cualquier** query/mutation GraphQL del Admin API. Es el camino para todo lo demás.
- `shopify_rest({method, path, body})` — **cualquier** endpoint REST (ej. `products.json?limit=10`)
- `create_discount({title, percentage|value})` — descuento básico automático (atajo; para códigos usar GraphQL `discountCodeBasicCreate`)

## Permisos concedidos (110/110 de la versión Released, Nov-10)

Instalación: 110 handles. App "mcp admin" (client_id `b63cf74f527996957d59ac9b15e3d959`), Dev Dashboard → Versions "Active" (mcp-admin-3). Verificar en cualquier momento:

```graphql
{ currentAppInstallation { accessScopes { handle } } }
```

Limitaciones reales (documentadas por Shopify, no errores):

- `write_companies` NO lo concede Shopify (requiere B2B/Plus; Plan Basic). Se ignora silenciosamente.
- `read_all_orders` y pagos (`read_shopify_payments*`) y Pixel: requieren aprobación manual de Shopify en el dashboard o plan superior. Descuentos/testeos: no usar.
- `fulfillmentOrders` root exige `read_assigned_fulfillment_orders` (no concedido) — ACCESS_DENIED **esperado**, no es fallo de la instalación.
- Pedidos por ventana: `read_orders`/`write_orders` cubren los **últimos 60 días**. Histórico mayor solo con `read_all_orders` (aprobación).
- `collections.json` REST da 403 ("Scope undefined: collections") — usar GraphQL para colecciones: `{ collections(first:5) { edges { node { id title } } } }`.
- Las escrituras implican lectura **excepto** en `orders` (por eso existe `read_orders` separado).
- 77 productos en DRAFT vs 14 ACTIVE: la tienda depende de publicar borradores para vender.

## Reglas de operación

1. **Lectura libre**; escritura solo tras confirmar con el usuario: nombre exacto y efecto del cambio (ej. "crear descuento automático 10% "Verano" desde hoy").
2. **Nunca** borrar productos/órdenes/colecciones sin aprobación explícita escrita; para borrar, preferir archivar/despublicar.
3. Nunca imprimir `SHOPIFY_API_SECRET` ni tokens en chat/logs; el .env es chmod 600.
4. Si el usuario pide "lanzar campaña" / "descuento", proponer rango 10–15% en tickets bajos; en tickets de ~$26 un 20% corta demasiado margen.
5. El usuario prefiere que abras todo y él solo haga clics mínimos; tomar la iniciativa con datos (`list_*`, GraphQL) y presentar opciones concretas con precios/margenes.

## Recetas

### Token al vuelo en shell (sin MCP)

```bash
TOKEN=$(python3 << 'EOF'
import json, urllib.request, re
env = {}
for l in open('/home/gabo/proyectos/shopify-mcp/.env'):
    m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$', l)
    if m and not l.strip().startswith('#'):
        env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
body = json.dumps({'grant_type':'client_credentials',
                   'client_id':env['SHOPIFY_API_KEY'],
                   'client_secret':env['SHOPIFY_API_SECRET']}).encode()
req = urllib.request.Request('https://gruposalas.myshopify.com/admin/oauth/access_token',
                             data=body, headers={'Content-Type':'application/json'}, method='POST')
print(json.load(urllib.request.urlopen(req))['access_token'])
EOF
)
curl -s -X POST "https://gruposalas.myshopify.com/admin/api/2025-10/graphql.json" \
  -H "Content-Type: application/json" -H "X-Shopify-Access-Token: $TOKEN" \
  -d '{"query":"{ shop { name plan { displayName } } }"}'
```

### Productos ACTIVE + count de borradores

```graphql
{ products(first:250) { edges { node { id title status } } } }
# filtrar por status: ACTIVE / DRAFT / UNLISTED
```

### Métricas 60 días (para campaña)

```graphql
{ orders(first:250, query:"created_at:>=<ISO-60d>") {
  edges { node { totalPriceSet { shopMoney { amount currencyCode } } } } } }
# sumar amount; ticket = ventas/pedidos
```

### Descuento automático general (previa confirmación del usuario)

```graphql
mutation {
  discountAutomaticBasicCreate(automaticBasicDiscount: {
    title: "Campaña <nombre>",
    startsAt: "<ISO>",
    customerGets: { value: { percentage: 0.10 }, items: { all: true } }
  }) { automaticDiscountNode { id } userErrors { field message } } }
```

### Descuento con código

```graphql
mutation { discountCodeBasicCreate(basicCodeDiscount: {
  title:"...", code:"LANZAMIENTO10", startsAt:"<ISO>",
  customerGets: { value: { percentage: 0.10 }, items: { all: true } } })
  { codeDiscountNode { id } userErrors { field message } } }
```

### Editar tema / crear artículo de blog (campaña)

```graphql
mutation { themeFilesUpsert(files:[{ filename:"...", body:{ variable:"..." } }], themeId:"gid://...") {
  upsertedThemeFiles { filename } userErrors { field message } } }
mutation { articleCreate(article:{ title:"...", blogId:"gid://shopify/Blog/..." }) {
  article { id } userErrors { field message } } }
```

## Flujo con el usuario para cualquier cambio

1. Obtener datos con lecturas (catálogo, pedidos, márgenes estimados).
2. Proponer 2-3 opciones concretas (ej.: 10% automático 14 días vs código, ticket estimado).
3. Esperar aprobación explícita ("haz el 10% con código X").
4. Ejecutar la mutación mínima.
5. Verificar con la consulta de lectura correspondiente y reportar resultado real (incluyendo si hubo userErrors).

## Sesión abierta del MCP en OpenCode

La sesión que cargó el MCP antes del último cambio de `.env`/`server.js` sigue usando el código antiguo en memoria: **reiniciar OpenCode antes de usar las tools `shopify_*` tras un cambio**. Mientras tanto, usar el mint directo en shell como en Recetas — siempre funciona.
