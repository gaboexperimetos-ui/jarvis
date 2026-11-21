---
description: Crea un skill nuevo (/skills/create <nombre> [template])
---

Crea un skill nuevo con el helper.

Argumentos del usuario: $ARGUMENTS

Si no indica template, usa `basic`. Templates validos: `basic`, `code-review`,
`testing`, `docs`.

```bash
bash /home/gabo/.config/opencode/skills/skill-helper.sh create $ARGUMENTS
```

Despues escribe el contenido real en `~/.config/opencode/skills/<nombre>/SKILL.md`
siguiendo la plantilla creada: `description` tiene que decir que hace **y cuando
usarlo**, si no el modelo nunca lo activa. No abras el archivo en ningun editor.

Termina validando con `bash /home/gabo/.config/opencode/skills/skill-helper.sh validate <nombre>`.