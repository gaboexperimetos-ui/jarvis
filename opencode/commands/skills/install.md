---
description: Instala un skill desde GitHub o una ruta local (/skills/install <url-o-ruta>)
---

Instala el skill que pide el usuario.

Argumentos del usuario: $ARGUMENTS

Ejecuta:

```bash
bash /home/gabo/.config/opencode/skills/skill-helper.sh install $ARGUMENTS
```

Despues ejecuta `validate all` con el mismo script y ensena el resultado.

Si el comando falla, ensena el error tal cual. No reintentes con otros argumentos ni
inventes una fuente: pide la URL o la ruta correcta.

El script no sobrescribe: si el skill ya existe, informa y pregunta si quiere reemplazarlo.