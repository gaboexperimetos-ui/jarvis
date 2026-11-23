#!/usr/bin/env bash
# qwen-gui.sh - automatiza la GUI de Qwen Studio (Tauri/WebKitGTK) via Hyprland + ydotool.
# No hay API usable (anti-bot de Alibaba) ni WebDriver compatible (webkit 4.1 vs 6.0),
# asi que se conduce la ventana real: foco -> New Chat -> composer -> escribir -> Enter -> captura.
#
# Uso:
#   qwen-gui.sh send "<prompt>"      envia el prompt y guarda last_reply.png
#   qwen-gui.sh newchat              clic en "New Chat" (reset a chat vacio)
#   qwen-gui.sh shot [archivo]       captura la ventana completa
#   qwen-gui.sh focus                solo enfoca la app (la lanza si hace falta)
#
# Env: QWEN_COMPOSER_Y=47|94  (posicion vertical del composer; 47 chat vacio, 94 en conversacion)
#      QWEN_WAIT=10           segundos de espera para la respuesta antes de capturar
#      QWEN_NEWCHAT_WAIT=4    segundos tras pulsar New Chat
#
# Requisitos: Hyprland (hyprctl), ydotool + ydotoold, grim. La lectura de la
# respuesta queda en la captura (la interpreta el agente con vision o el usuario).
set -uo pipefail

STATE="${XDG_STATE_HOME:-$HOME/.local/state}/opencode/orquestar/qwen"
APP="${QWEN_STUDIO_APP:-$HOME/.local/opt/QwenStudio/qwen-studio-run}"
CLASS="Qwen-studio"
mkdir -p "$STATE"

need() { command -v "$1" >/dev/null 2>&1 || { echo "falta $1" >&2; exit 2; }; }
need hyprctl; need ydotool; need grim; need jq

ensure_daemon() {
  if [ ! -S "/run/user/$(id -u)/.ydotool_socket" ]; then
    nohup ydotoold >"$STATE/ydotoold.log" 2>&1 &
    sleep 1
  fi
}

addr() {
  hyprctl clients -j 2>/dev/null | jq -r --arg c "$CLASS" '.[]|select(.class==$c)|.address' | head -1
}

ensure_app() {
  local a; a="$(addr)"
  if [ -z "$a" ]; then
    setsid "$APP" >"$STATE/app.log" 2>&1 </dev/null & disown
    for _ in $(seq 1 40); do sleep 1; a="$(addr)"; [ -n "$a" ] && break; done
  fi
  [ -n "$a" ] || { echo "no aparecio la ventana de Qwen Studio" >&2; exit 3; }
  printf '%s' "$a"
}

focus() { hyprctl dispatch "hl.dsp.focus({window=\"address:$1\"})" >/dev/null 2>&1; }
move()  { hyprctl dispatch "hl.dsp.cursor.move({x=$1,y=$2})" >/dev/null 2>&1; }
click() { ydotool click 0xC0; }
key()   { ydotool key "$@"; }

geom() {
  hyprctl clients -j 2>/dev/null | jq -r --arg c "$CLASS" \
    '.[]|select(.class==$c)|"\(.at[0]) \(.at[1]) \(.size[0]) \(.size[1])"' | head -1
}

focus_app() {
  ensure_daemon
  local a; a="$(ensure_app)"
  focus "$a"
  sleep 0.3
  printf '%s' "$a"
}

cmd_send() {
  local prompt="${1:?falta el prompt}"
  local a; a="$(focus_app)"
  read -r wx wy ww wh < <(geom)
  # Composer: por defecto estado "chat vacio" (centrado ~47% del alto).
  # En una conversacion el composer baja (~94%): exporta QWEN_COMPOSER_Y=94.
  local yfrac="${QWEN_COMPOSER_Y:-47}"
  local cx=$(( wx + ww*60/100 ))  cy=$(( wy + wh*yfrac/100 ))
  move "$cx" "$cy"; sleep 0.3; click; sleep 0.5
  # limpiar borrador previo (si lo hubiera) y escribir
  key 29:1 30:1 30:0 29:0; sleep 0.15   # Ctrl+A
  ydotool type "$prompt"; sleep 0.4
  key 28:1 28:0
  sleep "${QWEN_WAIT:-10}"
  grim "$STATE/last_reply.png" 2>/dev/null
  echo "enviado. captura: $STATE/last_reply.png"
}

cmd_newchat() {
  local a; a="$(focus_app)"
  read -r wx wy ww wh < <(geom)
  local nx=$(( wx + ww*12/100 ))  ny=$(( wy + wh*9/100 ))
  move "$nx" "$ny"; sleep 0.3; click
  sleep "${QWEN_NEWCHAT_WAIT:-4}"
  echo "new chat"
}

cmd_shot() {
  local out="${1:-$STATE/shot.png}"
  local a; a="$(ensure_app)"; focus "$a"; sleep 0.3
  grim "$out" 2>/dev/null && echo "$out"
}

cmd_focus() {
  local a; a="$(focus_app)"; echo "enfocado: $a"
}

case "${1:-}" in
  send)    shift; cmd_send "$@" ;;
  newchat) cmd_newchat ;;
  shot)    shift; cmd_shot "$@" ;;
  focus)   cmd_focus ;;
  *) sed -n '2,22p' "$0"; exit 1 ;;
esac
