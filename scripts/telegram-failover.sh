#!/usr/bin/env bash
# telegram-failover.sh — un solo dueño del bot de Telegram, con relevo.
#
# Regla del usuario: el PC (asus-tuf) es el principal y atiende todo mientras
# esté encendido. El inspiron es el 24/7 (crons y automatizaciones) y toma el
# bot SOLO si el PC cae. En cuanto el PC vuelve, el inspiron lo suelta.
#
# Este script corre EN EL INSPIRON, por un timer de systemd cada 30 s.
# Telegram no permite dos getUpdates con el mismo token, por eso hay que turnarse.
set -uo pipefail

PC_HOST="${PC_HOST:-asus-tuf}"
ENVF="$HOME/.hermes/.env"
COUNT_FILE="$HOME/.hermes/.telegram-fail-count"
LOG="$HOME/.hermes/telegram-failover.log"
MAX_LOG=200

log() {
    printf '[%s] %s\n' "$(date '+%F %T')" "$*" >>"$LOG"
    if [ "$(wc -l <"$LOG" 2>/dev/null || echo 0)" -gt "$MAX_LOG" ]; then
        tail -n "$MAX_LOG" "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"
    fi
}

pc_gateway_active() {
    ssh -o BatchMode=yes -o ConnectTimeout=6 "$PC_HOST" \
        'systemctl --user is-active hermes-gateway' 2>/dev/null | grep -qx 'active'
}

tg_enabled() {
    grep -q '^TELEGRAM_BOT_TOKEN=' "$ENVF" 2>/dev/null
}

# 1 = activar (quitar el # del marcador), 0 = desactivar (poner #TELEGRAM_)
set_tg() {
    python3 - "$ENVF" "$1" <<'PY'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
want = sys.argv[2] == "1"
t = p.read_text()
if want:
    t = re.sub(r'(?m)^#\s?(TELEGRAM_[A-Z_]+=)', r'\1', t)
else:
    t = re.sub(r'(?m)^\s?(TELEGRAM_[A-Z_]+=)', r'#\1', t)
p.write_text(t)
PY
}

restart_gateway() { systemctl --user restart hermes-gateway; }

fails="$(cat "$COUNT_FILE" 2>/dev/null || echo 0)"
case "$fails" in ''|*[!0-9]*) fails=0 ;; esac

if pc_gateway_active; then
    echo 0 >"$COUNT_FILE"
    if tg_enabled; then
        set_tg 0
        restart_gateway
        log "PC activo -> el inspiron suelta Telegram"
    fi
else
    fails=$((fails + 1))
    echo "$fails" >"$COUNT_FILE"
    if [ "$fails" -ge 2 ] && ! tg_enabled; then
        set_tg 1
        restart_gateway
        log "PC caído ($fails comprobaciones) -> el inspiron toma Telegram"
    fi
fi
