---
name: components
source: impeccable + frontend-design
description: Component review patterns, polish guidelines, and before/after review format for UI code analysis.
---

# Patrones de Revision y Polish de Componentes

## Formato de Revision (Obligatorio)

Al revisar UI code, SIEMPRE usar tabla Markdown con columnas Before/After/Why. NO usar listas separadas.

```markdown
| Before | After | Why |
| --- | --- | --- |
| `transition: all 300ms` | `transition: transform 200ms ease-out` | Specificar propiedades exactas; evitar `all` |
| `transform: scale(0)` | `transform: scale(0.95); opacity: 0` | Nada en mundo real aparece desde nada |
| `ease-in` dropdown | `ease-out` custom curve | `ease-in` feels sluggish; `ease-out` instant feedback |
| Sin `:active` state button | `transform: scale(0.97)` on `:active` | Botones deben sentir responsive a press |
| `transform-origin: center` popover | `transform-origin: var(--transform-origin)` | Popovers escalan desde trigger (no modals — centrados) |
```

**Incorrecto (NUNCA):**
```
Before: transition: all 300ms
After: transition: transform 200ms ease-out
────────────────────────────
Before: scale(0)
After: scale(0.95)
```

Correcto = Una sola tabla markdown con columnas | Before | After | Why |, una fila por issue encontrado. Columna "Why" explica reasoning brevemente.

---

## Patrones Comunes y Mejoras

### Buttons

| Issue | Pattern Correcto | Razon |
|-------|-----------------|-------|
| Sin press feedback | `.button { transition: transform 160ms ease-out; } .button:active { transform: scale(0.97); }` | Instant feedback, interface se siente que escucha |
| Transicion too generic | Especificar properties exactos, no `transition: all` | Rendimiento predecible, solo animar lo necesario |
| Focus ring removed | Mantener focus-ring visible siempre | Accesibilidad critica, keyboard users necesitan indicador visual |
| Text alignment inconsistent | Text-center para icon+text, left-aligned para texto largo | UX patron standard buttons |

### Cards

| Issue | Pattern Correcto | Razon |
|-------|-----------------|-------|
| Border-radius same everywhere | Hierarchy-based radius (larger cards bigger radius) | Visual hierarchy via shape consistency |
| Shadow too uniform | Different shadow intensity by elevation level | Depth signals layer relationship |
| Card padding not consistent | Tokenized spacing system (8px grid) | Consistency across all card sizes |
| Overflow hidden missing | `overflow: hidden` en container con rounded corners | Children don't clip behind border-radius |

### Forms

| Issue | Pattern Correcto | Razon |
|-------|-----------------|-------|
| Placeholder as only label | Permanent visible `<label>` above/beside input | Placeholder desaparece al typing, label stays |
| Error at top of form only | Inline validation near field + error summary optional | User sees exactly which field has problem |
| No loading state on submit | Disabled button with spinner during processing | Prevent double-submit, show progress |
| Helper text missing complex fields | Instructions contextual antes/during input | Reduces errors, improves UX |

### Navigation

| Issue | Pattern Correcto | Razon |
|-------|-----------------|-------|
| Active state unclear | Bold + accent color indicator for current section | User always knows where they are |
| Navigation only horizontal | Responsive: horizontal → hamburger/menu vertical | Space constraints mobile vs desktop |
| Inconsistent navigation pattern | Same nav pattern throughout app | Predictability reduces cognitive load |
| Missing skip links | Skip to main content link first in DOM | Keyboard users bypass repetitive nav |

### Tables/Data Displays

| Issue | Pattern Correcto | Razon |
|-------|-----------------|-------|
| No empty state handling | Informative empty state with action CTA | Users know what to do when no data |
| Horizontal scroll on small screens | Responsive: stack rows, horizontal scroll container, or carousel | Mobile usability |
| No sort/filter indication | Clear sort indicator (↑↓), filter count badge | Users understand current sorting/filtering |
| Cell content truncated | Tooltips on hover/focus, expand option | Information accessible without clutter |

---

## Refinement Methods

### Critica Auto-Correctiva

Antes de entregar, aplicar metodo Chanel:
1. Mirar trabajo terminado como si fuera ajeno.
2. Identificar elementos decorativos redundantes.
3. Eliminar cada decoration que no sirva el brief especifico.
4. Verificar quality floor: mobile responsive, keyboard focus, reduced-motion respected, accessible, harmony colors.

### Pro-Rules Delivery Checklist

Ver `references/pro-rules.md` para checklist completo delivery mobile/native app. Incluye icon discipline, interaction feedback, light/dark contrast, safe-area layout, accessibility mobile-specific.

### Iteration Strategy

Para mejora iterativa de componentes existentes:
1. Identificar componente target.
2. Revisar contra todas las categorias de prioridad (#1→#10).
3. Documentar issues en tabla Before/After/Why.
4. Priorizar fixes segun impacto (CRITICO > ALTO > MEDIO > BAJO).
5. Implementar cambios uno-a-uno verificando cada fix.
6. Review final tras todos cambios aplicados.
