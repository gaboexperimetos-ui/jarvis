#!/usr/bin/env bash
# healthcheck.sh — revisión rápida del sistema, solo lectura.
# No cambia nada: solo dice qué está mal.
set -uo pipefail

OK=0; WARN=0; FAIL=0
ok()   { printf '  \033[32mOK\033[0m    %s\n' "$*"; OK=$((OK+1)); }
warn() { printf '  \033[33mAVISO\033[0m %s\n' "$*"; WARN=$((WARN+1)); }
bad()  { printf '  \033[31mFALLO\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }

echo "═══ Salud de jarvis ($(date '+%F %T')) ═══"

# ── 1. Sincronización ─────────────────────────────────────────────────────
echo
echo "Sync"
if [ ! -d /home/gabo/jarvis ]; then
    bad "no existe /home/gabo/jarvis"
else
    cd /home/gabo/jarvis || exit 1
    local_head="$(git rev-parse HEAD 2>/dev/null)"
    remote_head="$(git ls-remote origin main 2>/dev/null | cut -f1)"
    dirty="$(git status --porcelain 2>/dev/null | wc -l)"
    [ -n "$local_head" ] && ok "repo local $local_head" || bad "repo local ilegible"
    [ "$local_head" = "$remote_head" ] && ok "local = remoto" || warn "local != remoto (el sync lo arregla en 5 min)"
    [ "$dirty" -eq 0 ] && ok "árbol limpio" || warn "$dirty ficheros sin commitear"
    if [ -f sync.log ]; then
        if grep -q "ERROR" sync.log 2>/dev/null; then
            bad "hay ERROR en sync.log: $(grep -m1 ERROR sync.log | cut -c1-70)"
        else
            ok "sin errores en sync.log"
        fi
    fi
    pend="$(ls -1 "$HOME/.jarvis/pending" 2>/dev/null | wc -l)"
    [ "$pend" -eq 0 ] && ok "sin conflictos pendientes" || warn "$pend conflicto(s) en ~/.jarvis/pending/"
fi

# ── 2. Temporizador ───────────────────────────────────────────────────────
echo
echo "Temporizador"
state="$(systemctl --user is-active jarvis-sync.timer 2>/dev/null)"
[ "$state" = "active" ] && ok "jarvis-sync.timer activo" || bad "jarvis-sync.timer: $state"

# ── 3. Secretos ───────────────────────────────────────────────────────────
echo
echo "Secretos"
if [ -d /home/gabo/jarvis/.git ]; then
    hits=0
    for pat in "sk-or-v1-" "ghp_" "gsk_" "xoxb-"; do
        n="$(git ls-files -z | xargs -0 grep -l "$pat" 2>/dev/null | wc -l)"
        hits=$((hits+n))
    done
    [ "$hits" -eq 0 ] && ok "ningún patrón de secreto" || bad "$hits fichero(s) con patrón de secreto"
fi

# ── 4. Disco y /tmp ───────────────────────────────────────────────────────
echo
echo "Disco"
tmp_pct="$(df --output=pcent /tmp 2>/dev/null | tail -1 | tr -dc '0-9')"
[ -n "$tmp_pct" ] && { [ "$tmp_pct" -lt 85 ] && ok "/tmp al ${tmp_pct} %" || warn "/tmp al ${tmp_pct} % (limpiar)"; }
home_pct="$(df --output=pcent /home 2>/dev/null | tail -1 | tr -dc '0-9')"
[ -n "$home_pct" ] && { [ "$home_pct" -lt 90 ] && ok "/home al ${home_pct} %" || warn "/home al ${home_pct} %"; }

# ── 5. Unidades fallidas ──────────────────────────────────────────────────
echo
echo "Servicios locales"
nfail="$(systemctl --user list-units --state=failed --no-pager --plain 2>/dev/null | grep -cE '^●' || true)"
[ "${nfail:-0}" -eq 0 ] && ok "sin unidades fallidas" || bad "$nfail unidad(es) fallida(s)"

# ── 6. El agente (inspiron) ───────────────────────────────────────────────
echo
echo "Agente (inspiron)"
if ssh -o ConnectTimeout=5 -o BatchMode=yes homelab 'true' 2>/dev/null; then
    ok "SSH a homelab"
    gw="$(ssh homelab 'systemctl --user is-active hermes-gateway 2>/dev/null')"
    [ "$gw" = "active" ] && ok "hermes-gateway activo" || bad "hermes-gateway: $gw"

    # memoria: ¿los ficheros caben en su límite?
    read -r mlim ulim mus uls < <(ssh homelab '
        c=~/.hermes/config.yaml
        ml=$(grep -oP "memory_char_limit:\s*\K\d+" "$c" | head -1)
        ul=$(grep -oP "user_char_limit:\s*\K\d+" "$c" | head -1)
        ms=$(wc -c < ~/.hermes/memories/MEMORY.md 2>/dev/null || echo 0)
        us=$(wc -c < ~/.hermes/memories/USER.md 2>/dev/null || echo 0)
        echo "${ml:-0} ${ul:-0} ${ms:-0} ${us:-0}"
    ' 2>/dev/null)
    if [ "${mlim:-0}" -gt 0 ]; then
        [ "${mus:-0}" -le "${mlim:-1}" ] && ok "MEMORY.md ${mus}/${mlim} caracteres" || bad "MEMORY.md ${mus}/${mlim}: desbordado, no guardará memoria"
        [ "${uls:-0}" -le "${ulim:-1}" ] && ok "USER.md ${uls}/${ulim} caracteres"  || bad "USER.md ${uls}/${ulim}: desbordado"
    else
        warn "no pude leer los límites de memoria"
    fi

    # MCPs
    nmcp="$(ssh homelab 'T=$(grep HERMES_DASHBOARD_SESSION_TOKEN ~/.hermes/.env 2>/dev/null | cut -d= -f2-); curl -s -m 10 -H "Authorization: Bearer $T" http://localhost:9120/api/mcp/servers 2>/dev/null' | grep -o '"name"' | wc -l)"
    [ "${nmcp:-0}" -ge 1 ] && ok "$nmcp servidores MCP activos" || warn "no pude contar los MCP"

    # avisos de memoria en el log reciente
    nwarn="$(ssh homelab 'journalctl --user -u hermes-gateway --since "24 hours ago" --no-pager 2>/dev/null | grep -c "exceeds its char limit" || true')"
    [ "${nwarn:-0}" -eq 0 ] && ok "sin avisos de memoria desbordada" || warn "$nwarn aviso(s) de memoria en las últimas 24 h"
else
    bad "no hay SSH a homelab"
fi

# ── Resumen ───────────────────────────────────────────────────────────────
echo
printf '═══ %d OK · %d avisos · %d fallos ═══\n' "$OK" "$WARN" "$FAIL"
[ "$FAIL" -eq 0 ]