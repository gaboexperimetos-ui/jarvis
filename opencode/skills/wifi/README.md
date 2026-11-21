# WiFi — skill y comando `wifi`

El manual completo para el LLM está en [`SKILL.md`](SKILL.md). El comando ya está
en el PATH (`/home/gabo/bin/wifi`).

```bash
wifi          # escanea redes y abre el menú para elegir una
wifi scan     # solo muestra las redes y cuáles se pueden crackear
wifi capture 3  # captura el handshake de la red 3 y la crackea
wifi --brute  # ataca el router de la red actual sin menú
wifi --help   # ayuda
```

Flujo: Hydra + RockYou contra el SSH del router → login con paramiko → extracción
de la PSK WiFi actual. Resultados en `results/<usuario>_final.txt`.

Referencia rápida de credenciales/puertos/diccionarios:
[`references/priority-checklist.md`](references/priority-checklist.md).
