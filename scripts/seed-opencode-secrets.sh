#!/usr/bin/env bash
# Rellena los secretos que se sacaron del repo el 2026-11-21.
#
# `opencode.jsonc` ya no lleva la clave en claro: apunta a
#   ~/.config/opencode/secrets/unlimited-api-key
# (el proveedor freellmapi se elimino, su clave ya no hace falta)
# Este script las recupera del historial de git y las deja en su sitio.
#
# Uso:
#   ./scripts/seed-opencode-secrets.sh            # usa el commit 59100aa
#   ./scripts/seed-opencode-secrets.sh <commit>   # otro commit
#   OPENCODE_SECRETS_DIR=/ruta ./scripts/seed-opencode-secrets.sh
#
# No imprime las claves, solo confirma que creo los ficheros.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REF="${1:-59100aa}"
DEST="${OPENCODE_SECRETS_DIR:-$HOME/.config/opencode/secrets}"

mkdir -p "$DEST"
chmod 700 "$DEST" 2>/dev/null || true

seed() {
    local repo_file="$1" json_path="$2" out="$3"

    if [ -s "$out" ]; then
        echo "ya existe: $out"
        return 0
    fi

    if ! git -C "$REPO" cat-file -e "$REF:$repo_file" 2>/dev/null; then
        echo "AVISO: $repo_file no existe en $REF; salto $out" >&2
        return 0
    fi

    git -C "$REPO" show "$REF:$repo_file" | python3 -c '
import json, sys
node = json.load(sys.stdin)
for key in sys.argv[1].split("."):
    node = node[key]
sys.stdout.write(node)
' "$json_path" > "$out"

    chmod 600 "$out"
    echo "creado: $out ($(wc -c < "$out") bytes)"
}

seed "opencode/opencode.jsonc" "provider.unlimited.options.apiKey"    "$DEST/unlimited-api-key"

echo "Listo. Reinicia opencode para que lea los ficheros."
echo "Recomendado: rota estas claves cuando puedas; estuvieron publicas en el historial."
