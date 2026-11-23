#!/usr/bin/env bash
# orquestar-engine.sh - despacha un brief a un motor de codigo instalado.
# Motores: kilo, opencode, freebuff, cline (llama.cpp), zcode (llama.cpp), qwen (GUI), qoder, copilot.
# Lo llama el agente `orquestador` de OpenCode.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${ORQ_LOG_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/opencode/orquestar}"
TIMEOUT="${ORQ_TIMEOUT:-1800}"

# cline: proveedor/modelo por defecto = tu llama.cpp local ("mi qwen")
CLINE_PROVIDER="${ORQ_CLINE_PROVIDER:-llamacpp}"
CLINE_MODEL="${ORQ_CLINE_MODEL:-deepseek-v4pro}"

# zcode: CLI de Z.ai en modo standalone con un proveedor personal -> llama.cpp local.
# El plan gratis de Z.ai solo funciona en su GUI; el CLI standalone rechaza
# proveedores de cuenta ("Standalone Account Provider"). Por eso va contra tu qwen.
ZCODE_CJS="${ORQ_ZCODE_CJS:-$HOME/.local/opt/ZCode/resources/glm/zcode.cjs}"
ZCODE_CFG_DIR="${ORQ_ZCODE_CFG_DIR:-$LOG_DIR/zcode}"
ZCODE_MODEL="${ORQ_ZCODE_MODEL:-deepseek-v4pro}"

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
  zcode     zcode -p                   plan/build   GRATIS via tu qwen (router 8004)
  qwen      GUI de Qwen Studio         plan         GRATIS (plan Free, solo lectura)
  qoder     qoder -p                   plan/build   sesion ok, sin modelos en tu plan
  copilot   copilot -p                 plan/build   requiere login GitHub (free)

No scriptables (GUI, a mano): Antigravity, Kilo Desktop, Qwen Studio (via motor qwen).

Seguridad:
  - build exige ORQ_ALLOW_WRITE=1; sin eso aborta con codigo 3.
  - Un solo escritor por arbol a la vez.
  - Log en $ORQ_LOG_DIR (por defecto ~/.local/state/opencode/orquestar).
  - Timeout por defecto 1800 s; ajustalo con ORQ_TIMEOUT.

Variables utiles:
  ORQ_CLINE_PROVIDER (default llamacpp)   ORQ_CLINE_MODEL (default deepseek-v4pro)
  ORQ_ZCODE_MODEL   (default deepseek-v4pro)
  ORQ_QWEN_COMPOSER_Y (default 94)       47 chat nuevo, 94 en conversacion
  ORQ_QWEN_WAIT     (default 30)         segundos de espera de la respuesta
  ORQ_FREEBUFF_SETTLE (default 15)        segundos de silencio para cerrar la TUI

Ejemplos:
  orquestar-engine.sh doctor
  orquestar-engine.sh kilo plan  ~/proyectos/styp "arregla el test que falla"
  ORQ_ALLOW_WRITE=1 orquestar-engine.sh cline build ~/proyectos/styp brief.md
  orquestar-engine.sh qwen plan ~/ Cual es el bug en este stacktrace
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
zcode      zcode -p --mode plan (local)              zcode -p --mode build (local)            si (router 8004)
qwen       GUI de Qwen Studio (captura la respuesta)  no (GUI no edita archivos)               si (plan Free)
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

  if have node && [ -f "$ZCODE_CJS" ]; then
    if [ ! -f "$ZCODE_CFG_DIR/builtin.json" ] || [ ! -f "$ZCODE_CFG_DIR/personal.json" ]; then st="instalado; falta config local ($ZCODE_CFG_DIR)"
    elif ! http_ok "http://127.0.0.1:8004/v1/models"; then st="config ok; router 8004 caido"
    else st="GRATIS via local (zcode -> $ZCODE_MODEL)"; fi
  else st="no instalado"; fi
  printf '%-10s %-8s %s\n' zcode "$(have node && [ -f "$ZCODE_CJS" ] && echo si || echo no)" "$st"

  if have hyprctl && have ydotool && have grim && have jq; then
    if [ -n "$(hyprctl clients -j 2>/dev/null | jq -r '.[]|select(.class=="Qwen-studio").address' | head -1)" ]; then st="GRATIS ok (GUI abierta, solo plan)"
    elif [ -x "$HOME/.local/opt/QwenStudio/qwen-studio-run" ]; then st="app instalada (se lanza al usar; solo plan)"
    else st="falta la app Qwen Studio"; fi
  else st="faltan hyprctl/ydotool/grim/jq"; fi
  printf '%-10s %-8s %s\n' qwen "$(have hyprctl && have ydotool && have grim && have jq && echo si || echo no)" "$st"

  if have qoder; then
    if [ -d "$HOME/.qoder" ]; then st="sesion ok; sin modelos en tu plan"; else st="sin login (qoder login)"; fi
  else st="no instalado"; fi
  printf '%-10s %-8s %s\n' qoder "$(have qoder && echo si || echo no)" "$st"

  if have copilot; then
    [ -f "$HOME/.copilot/config.json" ] && st="sesion ok (free, modelos limitados)" || st="sin auth (corre: copilot login)"
  else st="no instalado"; fi
  printf '%-10s %-8s %s\n' copilot "$(have copilot && echo si || echo no)" "$st"

  printf '\nGUI (a mano): Antigravity, Kilo Desktop. Qwen Studio se conduce con el motor qwen (solo plan).\n'
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
  kilo|opencode|freebuff|cline|zcode|qwen|qoder|copilot) ;;
  *) die "motor desconocido: $engine (usa: kilo|opencode|freebuff|cline|zcode|qwen|qoder|copilot)" ;;
esac
case "$mode" in plan|build) ;; *) die "modo invalido: $mode (usa: plan|build)" ;; esac
if [ "$engine" = qwen ] && [ "$mode" = build ]; then
  die "qwen es solo lectura (GUI, no edita archivos): usa modo plan o el build con otro motor" 4
fi
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
  zcode)
    [ -f "$ZCODE_CJS" ] || die "no encuentro $ZCODE_CJS (ZCode no instalado)"
    builtin_cfg="$ZCODE_CFG_DIR/builtin.json"
    personal_cfg="$ZCODE_CFG_DIR/personal.json"
    [ -f "$builtin_cfg" ] || die "falta $builtin_cfg"
    [ -f "$personal_cfg" ] || die "falta $personal_cfg"
    personal_use="$personal_cfg"
    if [ -n "$model" ] && [ "$model" != "$ZCODE_MODEL" ]; then
      personal_use="$(mktemp "${TMPDIR:-/tmp}/orq-zcode-XXXXXX.json")"
      jq --arg m "$model" '.config.providerConfigRules.providerRules[0].config.personalModelIds=[$m] | .config.defaultModelSelection.modelId=$m' "$personal_cfg" > "$personal_use" || die "no pude preparar config zcode para $model"
    fi
    args=(-p "$prompt" --mode "$mode" --cwd "$dir")
    run env ZCODE_BUILTIN_PROVIDER_CONFIG_FILE="$builtin_cfg" ZCODE_PERSONAL_PROVIDER_CONFIG_FILE="$personal_use" node "$ZCODE_CJS" "${args[@]}"
    rc=$?
    [ "$personal_use" != "$personal_cfg" ] && rm -f "$personal_use"
    exit "$rc"
    ;;
  qwen)
    [ -x "$SCRIPT_DIR/qwen-gui.sh" ] || die "falta $SCRIPT_DIR/qwen-gui.sh"
    qwen_state="${XDG_STATE_HOME:-$HOME/.local/state}/opencode/orquestar/qwen"
    snap="$LOG_DIR/${stamp}-qwen-${mode}.png"
    run env \
      QWEN_COMPOSER_Y="${ORQ_QWEN_COMPOSER_Y:-94}" \
      QWEN_WAIT="${ORQ_QWEN_WAIT:-30}" \
      "$SCRIPT_DIR/qwen-gui.sh" send "$prompt"
    rc=$?
    if [ -f "$qwen_state/last_reply.png" ]; then
      cp -f "$qwen_state/last_reply.png" "$snap" 2>/dev/null && printf '[orquestar] captura=%s\n' "$snap" >&2
    fi
    exit "$rc"
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
