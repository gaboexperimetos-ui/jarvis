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
  orquestar-engine.sh list
  orquestar-engine.sh --help

Motores scriptables:
  kilo    kilo run            (plan: sin --auto | build: --auto)
  cline   cline               (plan: -p        | build: -y)
  claude  claude -p           (plan: --permission-mode plan | build: acceptEdits)
  dsh     dsh --profile headless (asesor de solo lectura, no escribe)

No scriptables (GUI o solo interactivo): freebuff, antigravity, qwen-studio,
kilo desktop, cline desktop. Usalos a mano.

Seguridad:
  - build exige ORQ_ALLOW_WRITE=1 en el entorno; sin eso aborta con codigo 3.
  - El log completo queda en $ORQ_LOG_DIR
    (por defecto ~/.local/state/opencode/orquestar).
  - Timeout por defecto 1800 s; ajustalo con ORQ_TIMEOUT.

Ejemplos:
  orquestar-engine.sh kilo plan  ~/proyectos/styp "arregla el test que falla"
  ORQ_ALLOW_WRITE=1 orquestar-engine.sh cline build ~/proyectos/styp brief.md
  git diff --stat | orquestar-engine.sh dsh plan ~/proyectos/styp -
EOF
}

list_engines() {
  cat <<'EOF'
motor   plan                         build
kilo    kilo run                     kilo run --auto
cline   cline -p                     cline -y
claude  claude -p --permission-mode plan   claude -p --permission-mode acceptEdits
dsh     dsh --profile headless       (solo asesor)
EOF
}

die() { printf 'orquestar-engine: %s\n' "$*" >&2; exit "${2:-2}"; }

case "${1:-}" in
  --help|-h|help) usage; exit 0 ;;
  list) list_engines; exit 0 ;;
esac

[ $# -ge 4 ] || { usage >&2; exit 2; }

engine="$1"; mode="$2"; dir="$3"; brief="$4"; model="${5:-}"

case "$engine" in kilo|cline|claude|dsh) ;; *) die "motor desconocido: $engine (usa: kilo|cline|claude|dsh)" ;; esac
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
