#!/usr/bin/env bash
# jarvis-sync.sh — sincroniza /home/gabo con GitHub en los DOS sentidos.
#
# Orden de cada pasada (cada 5 min, timer de systemd):
#   1. pull --rebase            GitHub -> repo local
#   2. merge-tree               repo  -> home  (solo lo que cambio en GitHub)
#   3. mirror                   home  -> repo  (lo que cambio aqui)
#   4. commit + push            repo  -> GitHub
#
# Regla de oro: un fichero que solo se toco en GitHub se aplica al home;
# uno que se toco en los dos sitios NO se pisa: se guarda copia del que
# llega de GitHub en ~/.jarvis/pending/ y se avisa en el log.
set -uo pipefail

REPO="/home/gabo/jarvis"
LOG="$REPO/sync.log"
MAX_LOG=200
PENDING="$HOME/.jarvis/pending"

log() {
    printf '[%s] %s\n' "$(date '+%F %T')" "$*" >> "$LOG"
    if [ "$(wc -l < "$LOG" 2>/dev/null || echo 0)" -gt "$MAX_LOG" ]; then
        tail -n "$MAX_LOG" "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
    fi
}

# ── Mapa repo -> home. Formato: <ruta-en-repo>:<destino> ──────────────────
MAP=(
    "hermes:$HOME/.hermes"
    "opencode:$HOME/.config/opencode"
    "skills/ecc-skills:$HOME/ECC/skills"
)

# ── Ficheros de sistema que se restauran a su sitio ──────────────────────
SYS_MAP=(
    "system/hyprland.conf:$HOME/.config/hypr/hyprland.conf"
    "system/kitty.conf:$HOME/.config/kitty/kitty.conf"
)

cd "$REPO" || { log "ERROR: no puedo entrar a $REPO"; exit 1; }

# ── 1. GitHub -> repo local ───────────────────────────────────────────────
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
if ! git pull --rebase --autostash origin "$BRANCH" >>"$LOG" 2>&1; then
    log "ERROR: pull --rebase fallo; no toco el home"
    git rebase --abort 2>/dev/null || true
    git stash pop 2>/dev/null || true
    exit 1
fi

# ── 2. repo -> home: solo lo que cambio en ESTE pull ─────────────────────
# Comparo el HEAD de antes del pull (ORIG_HEAD) con el de ahora: eso es
# exactamente lo que trajo GitHub, sin depender de la version de git.
CHANGED="$(git diff --name-only ORIG_HEAD HEAD 2>/dev/null || true)"

restore_one() {
    local src="$REPO/$1" dst="$2"
    [ -f "$src" ] || return 0
    if [ -f "$dst" ] && ! cmp -s "$src" "$dst"; then
        # Solo es conflicto de verdad si el home NO coincide con lo que habia
        # antes del pull: si coincide, es un cambio limpio de GitHub.
        if git cat-file -e "ORIG_HEAD:$1" 2>/dev/null; then
            git show "ORIG_HEAD:$1" > /tmp/jarvis-prev 2>/dev/null || true
            if [ -s /tmp/jarvis-prev ] && cmp -s /tmp/jarvis-prev "$dst"; then
                mkdir -p "$(dirname "$dst")"
                cp -p "$src" "$dst"
                log "restaurado de GitHub: $1 -> $dst"
                rm -f /tmp/jarvis-prev
                return 0
            fi
            rm -f /tmp/jarvis-prev
        fi
        # El home tiene cambios propios: no los piso.
        mkdir -p "$PENDING"
        cp -p "$src" "$PENDING/$(echo "$1" | tr / _).github-$(date +%s)"
        log "CONFLICTO $1: el home cambio por su cuenta; la version de GitHub queda en $PENDING"
        return 0
    fi
    mkdir -p "$(dirname "$dst")"
    cp -p "$src" "$dst"
    log "restaurado de GitHub: $1 -> $dst"
}

while IFS= read -r f; do
    [ -n "$f" ] || continue
    for entry in "${MAP[@]}"; do
        prefix="${entry%%:*}"; base="${entry#*:}"
        case "$f" in
            "$prefix"/*) restore_one "$f" "$base/${f#"$prefix"/}" ;;
        esac
    done
    for entry in "${SYS_MAP[@]}"; do
        rel="${entry%%:*}"; dst="${entry#*:}"
        [ "$f" = "$rel" ] && restore_one "$f" "$dst"
    done
done <<< "$CHANGED"

# ── 3. home -> repo (lo que yo cambie aqui) ──────────────────────────────
for entry in "${MAP[@]}"; do
    src="${entry%%:*}"; dst="${entry#*:}"
    [ -d "$dst" ] || continue
    rsync -a --delete \
        --exclude='.env' --exclude='*.key' --exclude='*.token' \
        --exclude='hermes-agent/' --exclude='tools/' --exclude='installs/' \
        --exclude='cache/' --exclude='sessions/' --exclude='logs/' \
        --exclude='state/' --exclude='telemetry/' --exclude='locks/' \
        --exclude='runtime/' --exclude='terminal-sessions/' \
        --exclude='backups/' --exclude='cron/' --exclude='gateway/' \
        --exclude='kanban/' --exclude='secrets/' --exclude='*.bak*' \
        --exclude='whatsapp/' --exclude='shared/' --exclude='platforms/' \
        --exclude='gateway.pid' \
        --exclude='identity.json' --exclude='service*.json' \
        --exclude='unlimited*.json' \
        "$dst/" "$src/" 2>/dev/null || log "AVISO: rsync fallo en $src"
done

# system/ no se espeja de vuelta al home: es solo lectura (info de la maquina)

# ── 4. commit + push ─────────────────────────────────────────────────────
if ! git diff --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    git add -A
    MSG="sync $(date '+%F %T')"
    git commit -q -m "$MSG" && log "commit: $MSG"
fi

if [ "$(git rev-parse HEAD)" != "$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo '')" ]; then
    if git push -q origin "$BRANCH" >>"$LOG" 2>&1; then
        log "push OK"
    else
        log "ERROR: push fallo (¿cambio Github a la vez?); la proxima pasada lo reintenta"
    fi
fi