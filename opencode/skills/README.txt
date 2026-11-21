# Skills de OpenCode

Directorio global de skills: aplica a todos los proyectos de este usuario.

## Que hay aqui

| Skill | Tipo | Que hace |
|---|---|---|
| `karpathy` | directorio | Guidelines de Andrej Karpathy para reducir los errores tipicos de un LLM al programar: pensar antes de codificar, simplicidad, cambios quirurgicos, criterios de exito verificables. |
| `skill-installer` | `.md` | Instrucciones para instalar skills desde GitHub o rutas locales. |
| `skill-creator` | `.md` | Instrucciones para crear, validar y listar skills. |

Los otros directorios (`design`, `egm`, `impeccable`, `poki`,
`reverse-engineer-anything`, `shopify`, `wifi`) son skills anteriores, no tocar.

## skill-helper.sh

El unico ejecutable. `skill-installer` y `skill-creator` no son comandos: son
instrucciones que lee el agente. Todo el trabajo real pasa por este script.

```bash
H=~/.config/opencode/skills/skill-helper.sh

bash $H list                      # lista los skills instalados
bash $H validate all              # valida el frontmatter de todos
bash $H create <nombre> [template]  # crea uno nuevo
bash $H install <url-o-ruta> [nombre]  # instala desde git o ruta local
```

Templates de `create`: `basic`, `code-review`, `testing`, `docs`.

## Flujo tipico

Crear un skill:

```bash
bash $H create mi-skill
$EDITOR ~/.config/opencode/skills/mi-skill/SKILL.md   # rellenar la plantilla
bash $H validate mi-skill
```

Instalar uno de GitHub:

```bash
bash $H install https://github.com/usuario/repo
bash $H validate all
```

Borrarlo (no hay comando, es un directorio):

```bash
mv ~/.config/opencode/skills/<nombre> ~/.config/opencode/skills/<nombre>.bak
```

Moverlo antes de borrar: si venia de un repo, el `.bak` es la unica copia de los
cambios locales que le hayas hecho.

## Reglas de un SKILL.md

```yaml
---
name: nombre-skill
description: Que hace y cuando usarlo
---
```

- El archivo se llama `SKILL.md`, en mayusculas.
- `description` es lo unico que el modelo ve antes de cargar el skill: si no dice
  **cuando** usarlo, el skill no se activa nunca.
- Un directorio con `SKILL.md` es un skill. OpenCode no busca dentro de el.

## Alcance

| Ruta | Alcance |
|---|---|
| `~/.config/opencode/skills/` | global, todos los proyectos |
| `<proyecto>/.opencode/skills/` | solo ese proyecto |

OpenCode tambien lee `~/.claude/skills` y `~/.agents/skills`, con precedencia
mas baja que `~/.config/opencode/skills`.

## Notas

- No hace falta reiniciar: OpenCode vigila los archivos y los recarga al vuelo.
- `bash $H install` no sobrescribe: si el skill existe, falla y no toca nada.
- Antes de instalar un repo que no conoces, lee su `SKILL.md` y sus `scripts/`:
  un skill es texto que el agente va a seguir, y puede traer ejecutables.

Documentacion oficial: <https://opencode.ai/docs/skills/>