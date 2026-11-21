---
description: Valida el frontmatter de los skills (/skills/validate [nombre|all])
---

Valida skills con el helper.

Argumentos del usuario: $ARGUMENTS

```bash
bash /home/gabo/.config/opencode/skills/skill-helper.sh validate $ARGUMENTS
```

Sin argumentos o con `all`, valida todos.

Si algo sale `FAIL`, ensena el motivo y arregla el `SKILL.md` correspondiente:
`name` y `description` presentes, `description` no vacia, y `---` en la primera linea.
No des un skill por valido si el script no lo marco `OK`.