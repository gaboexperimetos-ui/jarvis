---
description: Poki — saltar anuncios con recompensa y desbloquear progreso (Blacktop u otro juego)
---

Usa la skill poki instalada en ~/.config/opencode/skills/poki (lee su SKILL.md si hace falta).

Argumentos del usuario: $ARGUMENTS

- Sin argumentos: lanza Blacktop Police Chase con el launcher ya montado:
  `bash ~/.config/opencode/skills/poki/blacktop/launch.sh`
  (extensión MV3 + perfil propio; con WiFi cachea assets, sin WiFi arranca en offline).

- "unlock", "desbloquear" o "coches": parchea el guardado del juego que este corriendo.
  Sigue la seccion 3 del SKILL.md: identifica la clave y el esquema reales antes de tocar
  nada, haz copia del valor crudo y recarga para verificar. No apliques el snippet de
  Blacktop a otro juego sin comprobar la clave.

- "bypass", "rewards" o "anuncios": prepara el salto de recompensas generico
  (seccion 2 del SKILL.md) para cualquier juego de Poki.

- Cualquier otra cosa: trata el argumento como la URL o el nombre del juego, y sigue la
  skill desde el paso 1 (identificar el objetivo con evidencia real).

Reglas: trabaja con lo que veas en consola/almacenamiento, no supongas el esquema. Si el
juego verifica premios contra el servidor, dilo en vez de prometer que funciona. No cierres
el navegador del usuario sin confirmar.