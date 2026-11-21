---
name: skill-creator
description: Crea, valida, lista e instala skills de OpenCode con skill-helper.sh. Usalo cuando el usuario pida crear un skill nuevo, revisar la estructura de un skill, o instalar uno desde GitHub o una ruta local.
---

# Skill Creator

Todo el trabajo real lo hace `~/.config/opencode/skills/skill-helper.sh`.
Estas son las instrucciones que sigues cuando el usuario pide un skill: no
existe un binario `skill-creator`, lo ejecutas tu con la shell.

## Crear un skill

```bash
bash ~/.config/opencode/skills/skill-helper.sh create <nombre> [template]
```

Templates: `basic`, `code-review`, `testing`, `docs`. El nombre solo admite
minusculas, numeros y guiones. El comando valida el resultado antes de terminar,
asi que si sale "OK" el skill ya cumple la estructura minima.

Despues de crearlo, edita `~/.config/opencode/skills/<nombre>/SKILL.md` y
rellenalo con el contenido real. La plantilla es un esqueleto, no el skill final.

## Validar

```bash
bash ~/.config/opencode/skills/skill-helper.sh validate <nombre>
bash ~/.config/opencode/skills/skill-helper.sh validate all
```

Comprueba: frontmatter de apertura en la primera linea, `name`, `description`,
y que la descripcion no este vacia.

## Listar

```bash
bash ~/.config/opencode/skills/skill-helper.sh list
```

## Estructura de un skill

```
~/.config/opencode/skills/
└── nombre-skill/
    ├── SKILL.md        # Requerido
    ├── scripts/        # Opcional: ejecutables
    ├── references/     # Opcional: documentacion que carga el agente
    └── templates/      # Opcional: plantillas
```

Un directorio con `SKILL.md` es un skill. OpenCode no busca dentro de el.

## Reglas del SKILL.md

Frontmatter minimo:

```yaml
---
name: nombre-skill
description: Que hace y cuando usarlo
---
```

La `description` es lo unico que el modelo ve antes de cargar el skill: escribe
que hace **y cuando usarlo**. Una descripcion vaga hace que el skill no se
active nunca.

## Distribucion

Opciones, de menos a mas:

1. `tar -czf nombre.tar.gz -C ~/.config/opencode/skills nombre` y compartir el
   archivo.
2. Subirlo a un repo de GitHub con el skill en un directorio propio.
3. Instalarlo en otra maquina con `install <url>` (ver `skill-installer`).

Alcance de la instalacion:

- Global: `~/.config/opencode/skills/` — todos los proyectos del usuario.
- Proyecto: `.opencode/skills/` en la raiz del proyecto.

OpenCode tambien lee `~/.claude/skills` y `~/.agents/skills` por compatibilidad.
Su precedencia es mas baja que `~/.config/opencode/skills`, asi que dos skills
con el mismo id resuelven al del directorio de mayor prioridad.

## Errores comunes

- **El skill no aparece en OpenCode**: el archivo se llama `skill.md` en
  minusculas. Tiene que ser `SKILL.md`.
- **Aparece pero nunca se activa**: la `description` no dice cuando usarlo.
- **Un skill con scripts no los encuentra**: usa rutas absolutas o relativas al
  directorio del skill, no al directorio de trabajo.

Tras crear o borrar skills no hace falta reiniciar: OpenCode vigila los archivos
de configuracion y los recarga. Fuera de eso, `opencode service restart`.

Documentacion oficial: <https://opencode.ai/docs/skills/>