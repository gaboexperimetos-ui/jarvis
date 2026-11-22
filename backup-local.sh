#!/usr/bin/env bash
# backup-local.sh — copia local en el PC y en el homelab.
#
# GitHub (jarvis-sync.sh) es la copia remota: la "2.0". Esto es el respaldo
# físico en las dos máquinas, por si GitHub o la red fallan.
#
# Guarda, con fecha y rotación de 7 días:
#   PC (asus-tuf)          -> ~/backups/{jarvis,styp,vault}/
#   inspiron (~/.hermes)   -> ~/backups/hermes/  (y una copia en el PC)
# Después espeja todo al homelab en ~/backups/laptop/.
#
# No versiona secretos fuera de casa: los .tar.gz se quedan en los dos equipos.
# El .env del agente va dentro del snapshot local porque es su única copia.
set -uo pipefail
umask 077

BASE="$HOME/backups"
AGENT="homelab"
KEEP=7
DATE="$(date +%Y%m%d-%H%M%S)"
LOG="$BASE/backup.log"

mkdir -p "$BASE"/{jarvis,styp,vault,hermes-inspiron}
chmod 700 "$BASE"

log() {
    printf '[%s] %s\n' "$(date '+%F %T')" "$*" >>"$LOG"
    if [ "$(wc -l <"$LOG" 2>/dev/null || echo 0)" -gt 200 ]; then
        tail -n 200 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"
    fi
}
say() { log "$*"; printf '  %s\n' "$*"; }

prune() {
    local d="$1"
    ls -1t "$d"/*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
}

# ── 1. PC: repo jarvis sin .git ni cacheados del navegador ────────────────
if tar czf "$BASE/jarvis/jarvis-$DATE.tar.gz" -C "$HOME" \
    --exclude='jarvis/.git' \
    --exclude='jarvis/opencode/skills/poki/blacktop/profile' \
    --exclude='jarvis/opencode/skills/poki/blacktop/offline' \
    jarvis 2>/dev/null; then
    say "PC jarvis: $(du -h "$BASE/jarvis/jarvis-$DATE.tar.gz" | cut -f1)"
else
    say "ERROR: no pude empaquetar el repo jarvis"
fi

# ── 2. PC: datos del dashboard (SQLite + notas) y bóveda ──────────────────
if tar czf "$BASE/styp/styp-$DATE.tar.gz" -C "$HOME/proyectos/styp" data notes 2>/dev/null; then
    say "PC dashboard: $(du -h "$BASE/styp/styp-$DATE.tar.gz" | cut -f1)"
else
    say "ERROR: no pude empaquetar los datos del dashboard"
fi

if [ -d "$HOME/SegundoCerebro" ]; then
    tar czf "$BASE/vault/vault-$DATE.tar.gz" -C "$HOME" SegundoCerebro 2>/dev/null &&
        say "PC bóveda: $(du -h "$BASE/vault/vault-$DATE.tar.gz" | cut -f1)"
fi

# ── 3. Homelab: ~/.hermes esencial (config, memoria, skills, sesiones) ────
# Se copia desde el inspiron, se empaqueta aquí y se devuelve al inspiron:
# así las dos máquinas tienen la misma copia.
if ssh -o BatchMode=yes -o ConnectTimeout=8 "$AGENT" 'true' 2>/dev/null; then
    STAGE="$(mktemp -d)"
    for item in config.yaml .env SOUL.md memories skills plugins sessions \
        cron kanban state.db state.db-wal state.db-shm; do
        rsync -a --exclude='*.bak*' "$AGENT:.hermes/$item" "$STAGE/hermes/" 2>/dev/null || true
    done
    if tar czf "$BASE/hermes-inspiron/hermes-$DATE.tar.gz" -C "$STAGE" --exclude='hermes/*.bak*' hermes 2>/dev/null; then
        say "inspiron ~/.hermes: $(du -h "$BASE/hermes-inspiron/hermes-$DATE.tar.gz" | cut -f1)"
    else
        say "ERROR: no pude empaquetar ~/.hermes del inspiron"
    fi
    rm -rf "$STAGE"
else
    say "AVISO: inspiron no alcanzable; salto la copia de ~/.hermes"
fi

# ── 4. Rotación local ─────────────────────────────────────────────────────
for d in "$BASE"/jarvis "$BASE"/styp "$BASE"/vault "$BASE"/hermes-inspiron; do
    prune "$d"
done

# ── 5. Espejo al homelab: que el PC también viva allí ─────────────────────
if ssh -o BatchMode=yes -o ConnectTimeout=8 "$AGENT" \
    'mkdir -p ~/backups/laptop/jarvis ~/backups/laptop/styp ~/backups/laptop/vault ~/backups/hermes' 2>/dev/null; then
    rsync -a --delete "$BASE/jarvis/" "$AGENT:backups/laptop/jarvis/" 2>/dev/null &&
        rsync -a --delete "$BASE/styp/" "$AGENT:backups/laptop/styp/" 2>/dev/null &&
        rsync -a --delete "$BASE/vault/" "$AGENT:backups/laptop/vault/" 2>/dev/null &&
        rsync -a --delete "$BASE/hermes-inspiron/" "$AGENT:backups/hermes/" 2>/dev/null &&
        say "espejado al homelab (~/backups/)" || say "ERROR: fallo el espejo al homelab"
else
    say "AVISO: no pude espejar al homelab"
fi

say "hecho: $DATE"
