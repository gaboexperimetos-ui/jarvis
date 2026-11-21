# Seguridad

Regla de partida: **este repo es público en GitHub.** Todo lo que se sube lo puede leer
cualquiera. Por eso se revisa antes de cada push.

---

## Lo que nunca se sube

| Categoría | Ejemplos |
|---|---|
| Claves SSH | `~/.ssh/` entero (privadas y públicas) |
| Variables de entorno | `.env`, `*.env`, `.env.*` (salvo `.env.example`) |
| Claves y certificados | `*.pem`, `*.key`, `*.keystore`, `id_rsa*`, `id_ed25519*` |
| Tokens | `*.token`, `*.secret`, `.netrc`, `.pgpass`, `*.kdbx` |
| Estado de Hermes | `auth.json`, `gateway-connections.json`, `runtime/`, `locks/` |
| Credenciales de apps | `.config/opencode/secrets/`, `service*.json`, `identity.json` |
| Contraseñas de apps | `.config/Hermes/`, `.config/systemd/` |

---

## El caso real: el token del gateway

La primera versión del sync copió `~/.hermes/` casi entero. Dentro iba
`gateway-connections.json`, y dentro de ese fichero **el token del gateway en claro**
(empieza por `KhG2`, 43 caracteres).

Se detectó **antes del primer push** buscando entre los ficheros del índice:

```bash
git ls-files -z | xargs -0 grep -l "KhG2…(43 caracteres, se trunca aquí)"
```

Se sacó del índice con `git rm --cached`, se añadió al `.gitignore`, y se repitió la búsqueda
hasta que dio **0 ficheros**. Verificación final:

```
0 ficheros con secretos
```

### Qué se busca en cada revisión

```bash
cd ~/jarvis
for pat in "KhG2…(43 caracteres, se trunca aquí)" "sk-or-v1-" "hcQz…(clave del dashboard)" "gsk_"; do
  hit=$(git ls-files -z | xargs -0 grep -l "$pat" 2>/dev/null | head -2)
  [ -z "$hit" ] && echo "OK  $pat" || echo "!!! $pat -> $hit"
done
```

El patrón `ghp_` apareció dos veces y **las dos eran inocentes**:

- `hermes/config.yaml` línea 1732: un comentario de ejemplo, `# GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_..."`
- `opencode/scripts/hooks/post-bash-command-log.js` línea 188: precisamente una línea que
  **borra** tokens con `.replace(/\bghp_[A-Za-z0-9_]+\b/g, '<REDACTED>')`

Leer el contexto antes de alarmarse. Un patrón encontrado no es una fuga.

---

## Cifrado y transporte

- GitHub se usa por **SSH** (`git@github.com:…`), nunca HTTPS con contraseña.
- La clave que GitHub acepta es `~/.ssh/id_ed25519_opencode`. Está declarada en
  `~/.ssh/config` con `IdentitiesOnly yes`.
- Verificado: `ssh -T git@github.com` responde
  `Hi gaboexperimetos-ui! You've successfully authenticated`.

---

## Secretos que están en el portátil pero NO en el repo

- La **contraseña del dashboard** del inspiron (`hcQz…` (la clave real está en el `.env` del inspiron)) vive en
  `~/.hermes/config.yaml` **del inspiron**, no en este repo. El `config.yaml` versionado
  aquí es el del portátil y no la contiene.
- El **token del dashboard** del inspiron está en `~/.hermes/.env`.
- La **clave de sudo** del inspiron solo la tiene el usuario.

Si algún día se versiona el `config.yaml` del inspiron, hay que quitar antes:

```yaml
dashboard:
  basic_auth:
    username: "gabo"
    password: "..."          # ← fuera
    secret: "..."            # ← fuera
```

---

## Los proyectos no se tocan

`proyectos/`, `dev/`, `ECC/`, `freellmapi/` y los 21 repos con `.git` propio **no se
incluyen**. Motivos, en orden:

1. Cada uno es un repo independiente. Meterlos aquí los rompería (submódulos mal puestos).
2. Muchos tienen sus propios remotos y su propio historial.
3. Algunos pueden contener secretos que no hemos auditado.

Si se quiere respaldar uno, se respalda **en su propio repo**.

---

## Antes de cada push: lista de la compra

1. `git status --short` — ¿hay algo que no esperaba?
2. `git ls-files | wc -l` y `du -ch` — ¿el tamaño se disparó?
3. La búsqueda de patrones de arriba.
4. ¿Algún fichero nuevo en `hermes/` o `opencode/` que sea claramente sensible?

El sync automático hace el paso 1-2 implícitamente (solo versiona lo que el `.gitignore`
deja pasar), pero la revisión manual es la red de seguridad.