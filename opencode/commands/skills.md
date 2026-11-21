---
description: Lista los skills instalados, o carga uno por nombre (/skills [nombre])
---

Skills instalados ahora mismo:

!`bash /home/gabo/.config/opencode/skills/skill-helper.sh list`

Argumentos del usuario: $ARGUMENTS

- Sin argumentos: presenta la lista de arriba como una tabla corta (nombre y para que sirve) y recuerda que se carga con `/skills <nombre>`.
- Con un nombre: carga ese skill con la herramienta `skill`, usando su id exacto, y sigue sus instrucciones.
- Si el nombre no esta en la lista: dilo y muestra la lista, no inventes un skill parecido.