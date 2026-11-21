#!/bin/bash
# Router Crack Skill - Master Wrapper
# Permite invocar la skill con comandos simples desde cualquier lugar

SKILL_DIR="/home/gabo/.config/opencode/skills/router-crack"
SCRIPTS_DIR="$SKILL_DIR/scripts"

# Función para ejecutar el script de búsqueda
search() {
    python3 "$SCRIPTS_DIR/search.py" "$@"
}

# Alias para invocar la skill fácilmente
alias router-crack='search'
