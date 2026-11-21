#!/bin/bash
# Script auxiliar de skills de OpenCode: crear, validar, listar e instalar.
# Documentacion: ~/.config/opencode/skills/README.txt

set -euo pipefail

SKILLS_DIR="${HOME}/.config/opencode/skills"

die() { echo "Error: $*" >&2; exit 1; }

# Plantillas disponibles para `create`.
template_basic() {
    cat << 'EOF'
---
name: SKILL_NAME
description: Descripcion breve del skill
---

# SKILL_NAME

## Proposito

Que hace este skill y cuando usarlo.

## Uso

```bash
# Ejemplos
```
EOF
}

template_code_review() {
    mkdir -p "$1/checklists"
    cat << 'EOF' > "$1/checklists/review.md"
# Checklist de revision

- [ ] Legibilidad
- [ ] Complejidad
- [ ] Testing
- [ ] Documentacion
EOF
    cat << 'EOF'
---
name: SKILL_NAME
description: Revision de codigo con checklist y criterios verificables
---

# SKILL_NAME - Code Review

## Checklist

Lee `checklists/review.md` y verifica cada punto antes de aprobar.

## Uso

1. Lee el diff.
2. Recorre el checklist.
3. Reporta hallazgos con `ruta/archivo:línea`.
EOF
}

template_testing() {
    mkdir -p "$1/strategies"
    cat << 'EOF'
---
name: SKILL_NAME
description: Estrategias de testing con ejemplos por nivel
---

# SKILL_NAME - Testing

## Estrategias

- Unit tests: aislar la unidad, sin red ni disco.
- Integration tests: la unidad con sus dependencias reales.
- E2E tests: el flujo completo desde la interfaz.

## Uso

Escribe primero el test que falla, luego el codigo que lo pasa.
EOF
}

template_docs() {
    mkdir -p "$1/templates"
    cat << 'EOF' > "$1/templates/readme.md"
# Proyecto

## Instalacion

## Uso

## Configuracion
EOF
    cat << 'EOF'
---
name: SKILL_NAME
description: Genera y revisa documentacion a partir del codigo real
---

# SKILL_NAME - Documentacion

## Proposito

Documentar lo que el codigo hace hoy, no lo que se planeo.

## Uso

1. Lee el codigo fuente.
2. Usa `templates/readme.md` como base.
3. No documentes funciones que no existen.
EOF
}

create_skill() {
    local name="${1:-}"
    local template="${2:-basic}"

    [ -n "$name" ] || die "falta el nombre: $0 create <nombre> [template]"
    [[ "$name" =~ ^[a-z0-9][a-z0-9-]*$ ]] \
        || die "nombre invalido '$name' (usa minusculas, numeros y guiones)"

    local skill_dir="$SKILLS_DIR/$name"
    [ -d "$skill_dir" ] && die "el skill '$name' ya existe en $skill_dir"

    local body
    case "$template" in
        basic)       body="$(template_basic)" ;;
        code-review) body="$(template_code_review "$skill_dir")" ;;
        testing)     body="$(template_testing "$skill_dir")" ;;
        docs)        body="$(template_docs "$skill_dir")" ;;
        *) die "template desconocido '$template' (basic, code-review, testing, docs)" ;;
    esac

    mkdir -p "$skill_dir"
    printf '%s\n' "$body" | sed "s/SKILL_NAME/$name/g" > "$skill_dir/SKILL.md"

    validate_skill "$name" || die "el skill recien creado no valida"
    echo "Creado: $skill_dir/SKILL.md"
}

validate_skill() {
    local name="${1:-}"
    local skill_dir="$SKILLS_DIR/$name"
    local skill_file="$skill_dir/SKILL.md"

    [ -f "$skill_file" ] || { echo "FAIL $name: no existe $skill_file"; return 1; }

    local errors=0

    # El frontmatter abre en la primera linea y cierra en la quinta como maximo.
    if [ "$(head -1 "$skill_file")" != "---" ]; then
        echo "FAIL $name: falta el frontmatter de apertura '---'"
        errors=$((errors + 1))
    fi

    if ! grep -q '^name:' "$skill_file"; then
        echo "FAIL $name: falta el campo 'name'"
        errors=$((errors + 1))
    fi

    if ! grep -q '^description:' "$skill_file"; then
        echo "FAIL $name: falta el campo 'description'"
        errors=$((errors + 1))
    fi

    # Una descripcion vacia no se anuncia al modelo.
    if grep -q '^description:[[:space:]]*$' "$skill_file"; then
        echo "FAIL $name: la descripcion esta vacia"
        errors=$((errors + 1))
    fi

    [ "$errors" -eq 0 ] || return 1
    echo "OK   $name"
}

# Lee la descripcion del frontmatter y la pliega en una sola linea.
# Maneja el bloque plegado de YAML (description: >-) que usan skills como egm.
read_description() {
    awk '
        NR == 1 && $0 == "---" { fm = 1; next }
        fm && $0 == "---" { exit }
        fm && /^description:/ {
            v = $0
            sub(/^description:[[:space:]]*/, "", v)
            if (v ~ /^[>|][+-]?[[:space:]]*$/) { grab = 1; next }
            print v; exit
        }
        fm && grab && /^[[:space:]]+[^[:space:]]/ {
            l = $0
            sub(/^[[:space:]]+/, "", l); sub(/[[:space:]]+$/, "", l)
            buf = (buf == "" ? l : buf " " l); next
        }
        fm && grab { exit }
        END { if (buf != "") print buf }
    ' "$1" | head -1
}

# Lista skills sin pasar las descripciones por xargs (rompe con apostrofes).
list_skills() {
    echo "Skills en $SKILLS_DIR:"
    echo ""

    local found=0
    local skill_dir name desc
    for skill_dir in "$SKILLS_DIR"/*/; do
        [ -f "$skill_dir/SKILL.md" ] || continue
        name="$(basename "$skill_dir")"
        desc="$(read_description "$skill_dir/SKILL.md")"
        [ -n "$desc" ] || desc="(sin descripcion)"
        printf '  - %s\n    %s\n\n' "$name" "$desc"
        found=1
    done

    [ "$found" -eq 1 ] || echo "  (ninguno todavia)"
}

# Instala un skill desde un repo git o un directorio local.
# Uso: install <url-o-ruta> [nombre]
install_skill() {
    local src="${1:-}"
    local want="${2:-}"

    [ -n "$src" ] || die "falta la fuente: $0 install <url-o-ruta> [nombre]"

    # Bash 5.3: `local tmp` sin inicializar cuenta como sin asignar bajo set -u.
    local tmp="" srcdir=""
    if [[ "$src" == git@* || "$src" == https://* || "$src" == http://* ]]; then
        command -v git >/dev/null || die "git no esta instalado"
        tmp="$(mktemp -d)"
        git clone --depth 1 -q "$src" "$tmp/repo" || die "no se pudo clonar $src"
        srcdir="$tmp/repo"
    elif [ -d "$src" ]; then
        srcdir="$(cd "$src" && pwd)"
    else
        die "no es una URL valida ni un directorio: $src"
    fi

    # Un skill es un directorio con SKILL.md. Busca el mas superficial.
    local found
    found="$(find "$srcdir" -name SKILL.md -type f -printf '%h\n' 2>/dev/null \
        | awk -v s="$srcdir" 'length($0)<best || best==0 {best=length($0); line=$0} END {print line}')"

    [ -n "$found" ] || die "no se encontro ningun SKILL.md en $src"

    local name
    if [ -n "$want" ]; then
        name="$want"
    else
        name="$(basename "$found")"
        # Un SKILL.md suelto en la raiz del repo no da un buen nombre.
        if [ "$found" = "$srcdir" ] || [ "$name" = "skills" ]; then
            name="$(sed -n 's/^name:[[:space:]]*//p' "$found/SKILL.md" | head -1)"
            [ -n "$name" ] || name="$(basename "$srcdir")"
        fi
    fi

    [[ "$name" =~ ^[a-z0-9][a-z0-9-]*$ ]] \
        || die "el nombre '$name' no sirve (minusculas, numeros y guiones)"

    local dest="$SKILLS_DIR/$name"
    [ -d "$dest" ] && die "el skill '$name' ya existe; borralo o usa otro nombre"

    cp -r "$found" "$dest"
    [ -n "$tmp" ] && rm -rf "$tmp"

    validate_skill "$name" || die "el skill instalado no valida"
    echo "Instalado: $dest"
}

case "${1:-}" in
    create)
        create_skill "${2:-}" "${3:-basic}"
        ;;
    validate)
        if [ "${2:-}" = "all" ] || [ -z "${2:-}" ]; then
            failed=0
            for d in "$SKILLS_DIR"/*/; do
                [ -f "$d/SKILL.md" ] || continue
                validate_skill "$(basename "$d")" || failed=1
            done
            exit "$failed"
        fi
        validate_skill "${2:-}"
        ;;
    list)
        list_skills
        ;;
    install)
        install_skill "${2:-}" "${3:-}"
        ;;
    *)
        cat << EOF
Uso: $0 <comando> [args]

  create <nombre> [template]   Crea un skill. Templates: basic, code-review,
                               testing, docs
  validate [nombre|all]        Valida frontmatter y campos requeridos
  list                         Lista los skills instalados
  install <url-o-ruta> [nombre]
                               Instala desde un repo git o un directorio local
EOF
        exit 1
        ;;
esac