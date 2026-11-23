#!/usr/bin/env bash
# orquestar-engine.sh - despacha un brief a un motor de codigo instalado.
# Pensado para que lo llame el agente `orquestador` de OpenCode.
set -uo pipefail

LOG_DIR="${ORQ_LOG_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/opencode/orquestar}"
TIMEOUT="${ORQ_TIMEOUT:-1800}"

usage() {
  cat <<'EOF'
Uso:
  orquestar-engine.sh <motor> <plan|build> <dir> <brief|archivo|-> [modelo]
  orquestar-engine.sh doctor
  orquestar-engine.sh list
  orquestar-engine.sh --help

Motores scriptables:
  kilo      kilo run            (plan: sin --auto | build: --auto)     GRATIS
  opencode  opencode run        (modelo por defecto: freellmapi/auto)  GRATIS
  cline     cline               (plan: -p | build: -y)                 requiere Ollama
  claude    claude -p           (plan/build con permission-mode)       requiere login
  dsh       dsh --profile headless (asesor, no escribe)                requiere DEEPSEEK_API_KEY

No scriptables (TUI o GUI, a mano): freebuff (gratis), Antigravity, Qwen Studio,
Kilo Desktop, Copilot CLI.

Seguridad:
  - build exige ORQ_ALLOW_WRITE=1 en el entorno; sin eso aborta con codigo 3.
  - El log completo queda en $ORQ_LOG_DIR
    (por defecto ~/.local/state/opencode/orquestar).
  - Timeout por defecto 1800 s; ajustalo con ORQ_TIMEOUT.

Ejemplos:
  orquestar-engine.sh doctor
  orquestar-engine.sh kilo plan  ~/proyectos/styp "arregla el test que falla"
  ORQ_ALLOW_WRITE=1 orquestar-engine.sh opencode build ~/proyectos/styp brief.md
  git diff --stat | orquestar-engine.sh dsh plan ~/proyectos/styp -
EOF
}

list_engines() {
  cat <<'EOF'
motor      plan                                build                              free
kilo       kilo run                            kilo run --auto                    si
opencode   opencode run -m freellmapi/auto      opencode run -m freellmapi/auto    si
cline      cline -p                            cline -y                           si Ollama arriba
claude     claude -p --permission-mode plan    claude -p --permission-mode acceptEdits  no (login)
dsh        dsh --profile headless              (solo asesor)                      no (API key)
freebuff   (TUI interactiva, no scriptable)    (TUI interactiva)                  si
EOF
}

have() { command -v "$1" >/dev/null 2>&1; }
up() { curl -s -m 2 -o /dev/null "$1" 2>/dev/null; }

doctor() {
  printf '%-12s %-8s %s\n' MOTOR BINARIO ESTADO
  # kilo: binario + auth oauth
  if have kilo; then
    if [ -f "$HOME/.local/share/kilo/auth.json" ]; then st="GRATIS ok (kilo-auto/free)"; else st="instalado, sin auth"; fi
  else st="no instalado"; fi
  printf '%-12s %-8s %s\n' kilo "$(have kilo && echo si || echo no)" "$st"

  # opencode: binario + router free
  if have opencode; then
    if [ -f "$HOME/.freellmapi-key" ] && up "http://127.0.0.1:3001/v1/models"; then st="GRATIS ok (freellmapi/auto)";
    elif up "http://127.0.0.1:8004/v1/models"; then st="GRATIS ok (local/deepseek-v4pro)";
    else st="instalado, sin router free"; fi
  else st="no instalado"; fi
  printf '%-12s %-8s %s\n' opencode "$(have opencode && echo si || echo no)" "$st"

  # cline: binario + ollama
  if have cline; then
    if up "http://127.0.0.1:11434/api/tags"; then st="GRATIS ok (ollama)"; else st="Ollama caido: no usable"; fi
  else st="no instalado"; fi
  printf '%-12s %-8s %s\n' cline "$(have cline && echo si || echo no)" "$st"

  # claude
  if have claude; then
    if [ -f "$HOME/.claude/.credentials.json" ] || [ -f "$HOME/.local/share/claude/.credentials.json" ]; then st="con credenciales"; else st="sin login"; fi
  else st="no instalado"; fi
  printf '%-12s %-8s %s\n' claude "$(have claude && echo si || echo no)" "$st"

  # dsh
  if have dsh; then
    if [ -n "${DEEPSEEK_API_KEY:-}" ]; then st="con DEEPSEEK_API_KEY"; else st="falta DEEPSEEK_API_KEY (pago)"; fi
  else st="no instalado"; fi
  printf '%-12s %-8s %s\n' dsh "$(have dsh && echo si || echo no)" "$st"

  # freebuff
  if have freebuff; then
    if [ -f "$HOME/.config/manicode/credentials.json" ]; then st="GRATIS, solo TUI"; else st="sin login"; fi
  else st="no instalado"; fi
  printf '%-12s %-8s %s\n' freebuff "$(have freebuff && echo si || echo no)" "$st"

  # qoder
  if have qoder; then st="sin modelo (login/modelo no disponible)"; else st="no instalado"; fi
  printf '%-12s %-8s %s\n' qoder "$(have qoder && echo si || echo no)" "$st"

  # copilot
  if have copilot; then st="sin auth GitHub (y requiere suscripcion)"; else st="no instalado"; fi
  printf '%-12s %-8s %s\n' copilot "$(have copilot && echo si || echo no)" "$st"

  # gsk
  if have gsk; then
    if [ -f "$HOME/.genspark-tool-cli/config.json" ]; then st="con config"; else st="sin API key"; fi
  else st="no instalado"; fi
  printf '%-12s %-8s %s\n' gsk "$(have gsk && echo si || echo no)" "$st"

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

case "$engine" in kilo|opencode|cline|claude|dsh) ;; *) die "motor desconocido: $engine (usa: kilo|opencode|cline|claude|dsh)" ;; esac
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
    args=(run --archived -m "${model:-freellmapi/auto}")
    [ "$mode" = build ] && args+=(--auto)
    args+=("$prompt")
    run opencode "${args[@]}"
    ;;
  cline)
    args=(-c "$dir")
    if [ "$mode" = build ]; then args+=(-y); else args+=(-p); fi
    [ -n "$model" ] && args+=(-m "$model")
    args+=("$prompt")
    run cline "${args[@]}"
    ;;
  claude)
    args=(-p "$prompt")
    if [ "$mode" = build ]; then args+=(--permission-mode acceptEdits); else args+=(--permission-mode plan); fi
    [ -n "$model" ] && args+=(--model "$model")
    run claude "${args[@]}"
    ;;
  dsh)
    [ "$mode" = build ] && printf '[orquestar] aviso: dsh es asesor, no escribe archivos\n' >&2
    run dsh --profile headless "$prompt"
    ;;
esac
