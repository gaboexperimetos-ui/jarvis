#!/bin/bash
# jarvis-sync.sh — sincroniza /home/gabo con el repo local y GitHub
# Se ejecuta automáticamente cada 5 minutos vía systemd timer
set -euo pipefail

REPO="/home/gabo/jarvis"
REMOTE="git@github.com:gaboexperimetos-ui/jarvis.git"
LOG="/home/gabo/jarvis/sync.log"
MAX_LOG_LINES=200

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" >> "$LOG"
    # Mantener el log bajo control
    if [ "$(wc -l < "$LOG")" -gt "$MAX_LOG_LINES" ]; then
        tail -n "$MAX_LOG_LINES" "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
    fi
}

cd "$REPO" || { log "ERROR: no se puede entrar a $REPO"; exit 1; }

# ── 1. Actualizar datos espejo ────────────────────────────────────────────
# Hermes (sin secretos)
rsync -a --delete \
  --exclude='.env' --exclude='*.key' --exclude='*.token' \
  --exclude='hermes-agent/' --exclude='tools/' --exclude='installs/' \
  --exclude='cache/' --exclude='sessions/' \
  ~/.hermes/ hermes/ 2>/dev/null || true

# OpenCode (sin tokens)
rsync -a --delete \
  --exclude='secrets/' --exclude='*.bak*' --exclude='identity.json' \
  --exclude='service*.json' --exclude='unlimited*.json' \
  ~/.config/opencode/ opencode/ 2>/dev/null || true

# Skills
rsync -a --delete ~/ECC/skills/ skills/ecc-skills/ 2>/dev/null || true
ls ~/.hermes/skills/ 2>/dev/null > skills/hermes-skills.txt || true

# Info del sistema (solo lo estable: no memory/disk/network, que son ruido en cada sync)
cp /etc/pacman.conf system/ 2>/dev/null || true
cp ~/.config/hypr/hyprland.conf system/ 2>/dev/null || true
cp ~/.config/kitty/kitty.conf system/ 2>/dev/null || true
systemctl list-unit-files --state=enabled --no-pager > system/enabled-services.txt 2>/dev/null || true
uname -a > system/uname.txt 2>/dev/null || true
lspci > system/lspci.txt 2>/dev/null || true
lsusb > system/lsusb.txt 2>/dev/null || true
pactl list short sinks > system/audio-sinks.txt 2>/dev/null || true
pactl list short sources > system/audio-sources.txt 2>/dev/null || true

# ── 2. Git add + commit si hay cambios ────────────────────────────────────
if ! git diff --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    git add -A
    MSG="sync $(date '+%Y-%m-%d %H:%M')"
    git commit -m "$MSG" --quiet || true
    log "commit: $MSG"
else
    log "sin cambios"
fi

# ── 3. Push a GitHub ──────────────────────────────────────────────────────
# Rebase antes de push (por si cambió desde otro lado)
git pull --rebase origin main --quiet 2>/dev/null || \
git pull --rebase origin master --quiet 2>/dev/null || true

git push origin main 2>>"$LOG" || \
git push origin master 2>>"$LOG" || true

log "push OK"