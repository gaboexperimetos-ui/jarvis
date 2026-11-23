#!/usr/bin/env bash
# orquestar-engine.sh - despacha un brief a un motor de codigo instalado.
# Motores: kilo, opencode, freebuff, cline (llama.cpp), qoder, copilot.
# Lo llama el agente `orquestador` de OpenCode.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${ORQ_LOG_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/opencode/orquestar}"
TIMEOUT="${ORQ_TIMEOUT:-1800}"

# cline: proveedor/modelo por defecto = tu llama.cpp local ("mi qwen")
CLINE_PROVIDER="${ORQ_CLINE_PROVIDER:-llamacpp}"
CLINE_MODEL="${ORQ_CLINE_MODEL:-deepseek-v4pro}"

usage() {
  cat <<'EOF'
Uso:
  orquestar-engine.sh <motor> <plan|build> <dir> <brief|archivo|-> [modelo]
  orquestar-engine.sh doctor
  orquestar-engine.sh list
  orquestar-engine.sh --help

Motores:
  kilo      kilo run                   plan/build   GRATIS (kilo-auto/free)
  opencode  opencode run               plan/build   GRATIS (freellmapi/auto)
  freebuff  driver TUI (scraping)      plan/build   GRATIS (experimental)
  cline     cline -P llamacpp          plan/build   tu qwen local (router 8004)
  qoder     qoder -p                   plan/build   sesion ok, sin modelos en tu plan
  copilot   copilot -p                 plan/build   requiere login GitHub (free)

No scriptables (GUI, a mano): Antigravity, Qwen Studio, Kilo Desktop.

Seguridad:
  - build exige ORQ_ALLOW_WRITE=1; sin eso aborta con codigo 3.
  - Un solo escritor por arbol a la vez.
  - Log en $ORQ_LOG_DIR (por defecto ~/.local/state/opencode/orquestar).
  - Timeout por defecto 1800 s; ajustalo con ORQ_TIMEOUT.

Variables utiles:
  ORQ_CLINE_PROVIDER (default llamacpp)   ORQ_CLINE_MODEL (default deepseek-v4pro)
  ORQ_FREEBUFF_SETTLE (default 15)        segundos de silencio para cerrar la TUI

Ejemplos:
  orquestar-engine.sh doctor
  orquestar-engine.sh kilo plan  ~/proyectos/styp "arregla el test que falla"
  ORQ_ALLOW_WRITE=1 orquestar-engine.sh cline build ~/proyectos/styp brief.md
  git diff --stat | orquestar-engine.sh opencode plan ~/proyectos/styp -
EOF
}

list_engines() {
  cat <<'EOF'
motor      plan                                     build                                    gratis
kilo       kilo run                                 kilo run --auto                          si
opencode   opencode run -m freellmapi/auto           opencode run --auto                      si
freebuff   driver TUI (scraping)                     driver TUI (scraping)                    si
cline      cline -p -P llamacpp -m deepseek-v4pro    cline -y -P llamacpp ...                 si (router 8004)
qoder      qoder -p --tools ""                       qoder -p --dangerously-skip-permissions  sesion, sin modelos
copilot    copilot -p --plan                         copilot -p --allow-all-tools --allow-all-paths  requiere login
EOF
}

have() { command -v "$1" >/dev/null 2>&1; }
http_ok() { curl -s -m "${2:-2}" -o /dev/null "$1" 2>/dev/null; }
router_chat() {
  # Prueba real: intenta cargar el modelo y responder 1 token. Imprime el HTTP code.
  curl -s -m "${1:-25}" -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:8004/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"deepseek-v4pro","messages":[{"role":"user","content":"OK"}],"max_tokens":1}' 2>/dev/null
}
freellm_chat() {
  local key; key="$(cat "$HOME/.freellmapi-key" 2>/dev/null)"
  [ -n "$key" ] || { printf '000'; return; }
  curl -s -m "${1:-30}" -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:3001/v1/chat/completions \
    -H "Authorization: Bearer $key" -H 'Content-Type: application/json' \
    -d '{"model":"auto","messages":[{"role":"user","content":"OK"}],"max_tokens":1}' 2>/dev/null
}

doctor() {
  printf '%-10s %-8s %s\n' MOTOR BINARIO ESTADO

  if have kilo; then
    [ -f "$HOME/.local/share/kilo/auth.json" ] && st="GRATIS ok (kilo-auto/free)" || st="instalado, sin auth (kilo login)"
  else st="no instalado"; fi
  printf '%-10s %-8s %s\n' kilo "$(have kilo && echo si || echo no)" "$st"

  if have opencode; then
    if ! http_ok "http://127.0.0.1:3001/v1/models"; then st="router 3001 caido"
    else
      code="$(freellm_chat 30)"
      if [ "$code" = "200" ]; then st="GRATIS ok (freellmapi/auto)"
      else st="freellmapi inestable (HTTP $code): usa kilo"; fi
    fi
  else st="no instalado"; fi
  printf '%-10s %-8s %s\n' opencode "$(have opencode && echo si || echo no)" "$st"

  if have freebuff; then
    [ -f "$HOME/.config/manicode/credentials.json" ] && st="GRATIS, driver TUI (experimental)" || st="sin login (freebuff login)"
  else st="no instalado"; fi
  printf '%-10s %-8s %s\n' freebuff "$(have freebuff && echo si || echo no)" "$st"

  if have cline; then
    if ! http_ok "http://127.0.0.1:8004/v1/models"; then st="router 8004 caido"
    else
      code="$(router_chat 25)"
      if [ "$code" = "200" ]; then st="GRATIS ok (llamacpp/$CLINE_MODEL)"
      else st="router responde pero el modelo no carga (VRAM): HTTP $code"; fi
    fi
  else st="no instalado"; fi
  printf '%-10s %-8s %s\n' cline "$(have cline && echo si || echo no)" "$st"

  if have qoder; then
    if [ -d "$HOME/.qoder" ]; then st="sesion ok; sin modelos en tu plan"; else st="sin login (qoder login)"; fi
  else st="no instalado"; fi
  printf '%-10s %-8s %s\n' qoder "$(have qoder && echo si || echo no)" "$st"

  if have copilot; then st="sin auth (corre: copilot login)"; else st="no instalado"; fi
  printf '%-10s %-8s %s\n' copilot "$(have copilot && echo si || echo no)" "$st"

  printf '\nGUI (a mano): Antigravity, Qwen Studio, Kilo Desktop\n'
}

die() { printf 'orquestar-engine: %s\n' "$*" >&2; exit "${2:-2}"; }

case "${1:-}" in
  --help|-h|help) usage; exit 0 ;;
  list) list_engines; exit 0 ;;
  doctor) doctor; exit 0 ;;
esac

[ $# -ge 4 ] || { usage >&2; exit 2; }

engine="$1"; mode="$2"; dir="$3"; brief="$4"; model="${5:-}"

case "$engine" in
  kilo|opencode|freebuff|cline|qoder|copilot) ;;
  *) die "motor desconocido: $engine (usa: kilo|opencode|freebuff|cline|qoder|copilot)" ;;
esac
case "$mode" in plan|build) ;; *) die "modo invalido: $mode (usa: plan|build)" ;; esac
[ -d "$dir" ] || die "directorio inexistente: $dir"
dir="$(cd "$dir" && pwd)"

if [ "$mode" = build ] && [ "${ORQ_ALLOW_WRITE:-0}" != "1" ]; then
  die "build bloqueado: exporta ORQ_ALLOW_WRITE=1 para permitir que $engine modifique archivos" 3
fi

if [ "$brief" = "-" ]; then
  prompt="$(cat)"
elif [ -f "$brief" ]; then
  prompt="$(cat "$brief")"
else
  prompt="$brief"
fi
[ -n "${prompt//[[:space:]]/}" ] || die "brief vacio"

mkdir -p "$LOG_DIR" || die "no puedo crear $LOG_DIR"
stamp="$(date +%Y%m%d-%H%M%S)"
log="$LOG_DIR/${stamp}-${engine}-${mode}.log"

run() {
  local -a cmd=("$@")
  printf '[orquestar] motor=%s modo=%s dir=%s timeout=%ss\n' "$engine" "$mode" "$dir" "$TIMEOUT" >&2
  printf '[orquestar] log=%s\n' "$log" >&2
  ( cd "$dir" && timeout "$TIMEOUT" "${cmd[@]}" ) >"$log" 2>&1
  local status=$?
  cat "$log"
  printf '[orquestar] salida=%s log=%s\n' "$status" "$log" >&2
  return "$status"
}

case "$engine" in
  kilo)
    args=(run --dir "$dir")
    [ -n "$model" ] && args+=(--model "$model")
    [ "$mode" = build ] && args+=(--auto)
    args+=("$prompt")
    run kilo "${args[@]}"
    ;;
  opencode)
    args=(run -m "${model:-freellmapi/auto}")
    [ "$mode" = build ] && args+=(--auto)
    args+=("$prompt")
    run opencode "${args[@]}"
    ;;
  freebuff)
    printf '[orquestar] aviso: freebuff es TUI; se conduce por scraping de pantalla (experimental)\n' >&2
    tmpbrief="$(mktemp "${TMPDIR:-/tmp}/orq-freebuff-XXXXXX.md")"
    printf '%s' "$prompt" > "$tmpbrief"
    run python3 "$SCRIPT_DIR/orquestar-freebuff.py" "$dir" "$tmpbrief" "${ORQ_FREEBUFF_SETTLE:-15}"
    rc=$?
    rm -f "$tmpbrief"
    exit "$rc"
    ;;
  cline)
    args=(-P "$CLINE_PROVIDER" -m "${model:-$CLINE_MODEL}" -c "$dir")
    if [ "$mode" = build ]; then args+=(-y); else args+=(-p); fi
    args+=("$prompt")
    run cline "${args[@]}"
    ;;
  qoder)
    args=(-p --cwd "$dir")
    if [ "$mode" = build ]; then args+=(--dangerously-skip-permissions); else args+=(--tools ""); fi
    args+=("$prompt")
    run qoder "${args[@]}"
    ;;
  copilot)
    if [ "$mode" = build ]; then
      args=(-p "$prompt" --allow-all-tools --allow-all-paths)
    else
      args=(-p "$prompt" --plan)
    fi
    [ -n "$model" ] && args+=(--model "$model")
    run copilot "${args[@]}"
    ;;
esac
