#!/usr/bin/env bash
# telegram-failover.sh — un solo dueño del bot de Telegram, con relevo.
#
# Regla: el PC (asus-tuf) es el principal y atiende todo mientras esté
# encendido. El inspiron es el 24/7 (crons y automatizaciones) y toma el bot
# SOLO si el PC cae. En cuanto el PC vuelve, el inspiron lo suelta.
#
# Corre EN EL INSPIRON, por un timer de systemd cada 30 s.
# Telegram no permite dos getUpdates con el mismo token: hay que turnarse.
#
# Las líneas de Telegram se desactivan anteponiendo el marcador #FAILOVER#.
# Así se reactivan EXACTAMENTE las cuatro líneas reales y nunca las de
# plantilla (`# TELEGRAM_WEBHOOK_URL=...`), que romperían el polling.
set -uo pipefail

PC_HOST="${PC_HOST:-asus-tuf}"
ENVF="$HOME/.hermes/.env"
COUNT_FILE="$HOME/.hermes/.telegram-fail-count"
LOG="$HOME/.hermes/telegram-failover.log"
MAX_LOG=200
MARK="#FAILOVER#"

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

# 1 = activar (quitar el marcador), 0 = desactivar (poner el marcador).
set_tg() {
    python3 - "$ENVF" "$1" "$MARK" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
want = sys.argv[2] == "1"
mark = sys.argv[3]
out = []
for ln in p.read_text().splitlines(True):
    if want and ln.startswith(mark):
        out.append(ln[len(mark):])
    elif not want and ln.startswith("TELEGRAM_"):
        out.append(mark + ln)
    else:
        out.append(ln)
p.write_text("".join(out))
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
