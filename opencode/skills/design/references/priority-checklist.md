---
name: priority-checklist
source: ui-ux-pro-max + impeccable
description: Priority-based rule index for UI/UX decisions by category and severity.
---

# Checklist de Prioridad — Reglas por Categoria

Prioridad 1→10. Seguir orden segun impacto. Para guia completa por categoria, leer `references/pro-rules.md`.

## Prioridad 1 — Accesibilidad (CRITICO)

**Dominio:** ux | **Impacto:** CRITICO | **Verificacion:** WCAG AA minimo

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Contrast ratio ≥ 4.5:1 para texto normal | Verificar con auditoria herramienta o calculadora color | Gray-on-gray (< 3:1), text sobre fondos con pattern complejo |
| Alt text descriptivo en imagenes informativas | Cada imagen tiene alt apropiado (empty si decorative=true) | Alt vacío en fotos producto, alt "image" genérico |
| Keyboard navigation completa | Tab order logico, skip links, focus visible en todo element | Focus rings eliminados, elementos sin tabindex tabeable |
| ARIA labels en icon-only buttons/link | Botones icon tienen aria-label especifico | Icono sin label = screen reader no entiende accion |
| Form states con aria-live/polite | Mensajes error/success announced por screen reader | Errores solo visuales, no announced |
| Heading hierarchy semantic H1→H6 | Solo un H1 por pagina, jerarquia logica sin saltos | H2 seguido de H4, multiples H1s |
| Focus states always visible | Outline/focus-ring siempre presente, contraste suficiente | Focus ring removed por "clean look" |
| Touch targets ≥ 44x44px | Botones e links cumplen size minimo | Link icons pequeños, controles apretados |

## Prioridad 2 — Touch e Interacción (CRITICO)

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Element touch target ≥ 44x44px min | Medir espacio clickeable real (no solo area visible) | Texto como link pequeño, icono como botn |
| Espaciado vertical ≥ 8px entre targets touch | Padding suficiente entre elementos consecutivos | Items lista separados por 2px solo |
| Loading feedback evidente | Skeleton screens, spinners, disabled state al enviar | Submit button clickable durante carga |
| Hover states NO sole interaction model | En mobile, touch debe activar misma funcionalidad | Menu que solo abre con hover desktop |
| Animacion instantanea (0ms) para estados → evitado | Transiciones naturales ≥ 100ms | Estado cambia instantaneamente sin transition |

## Prioridad 3 — Performance (ALTO)

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Imagenes WebP/AVIF con fallback JPG/PNG | <picture> con srcset multiple formatos | PNG/JPG pesado donde WebP es 30% menor |
| Lazy loading imágenes below-fold | loading="lazy" en img elements fuera viewport | Todas imagenes cargan simultaneously |
| CLS < 0.1 | Reservar space para imagenes/videos (aspect-ratio o height explicit) | Imagen carga y empuja contenido abajo |
| Layout thrashing evitado | Read layout properties separately de writes; batch DOM reads | Read offsetHeight inmediatamente despues de cambiar style |
| Debounce/throttle eventos intensivos | Scroll/resize/touchmove con debounce 50-100ms | Event listener sin throttle ejecuta cada pixel scroll |

## Prioridad 4 — Estilo Visual (ALTO)

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Estilo visual match tipo producto | Enterprise=profesional minimal; Entertainment=bold/expresivo | Estética SaaS genérica para toda aplicacion |
| Consistencia paleta a lo largo de app | Design tokens centralizados, max 2-3 colores accent | Colores random entre secciones |
| Iconos SVG preferidos sobre emojis | Vectorial, escalable, consistentes stroke-width | Emoji como iconos primarios (inconsistent cross-platform) |
| Elevation/depth systematizada | Layering predictable, box-shadow/spacer rules definidas | Sombras aleatorias diferentes en cada card |
| Border-radius intencional y jerarquizado | Un border-radius principal con variaciones logicas | Todos radius diferente, sin patrón |

## Prioridad 5 — Layout Responsive (ALTO)

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Mobile-first breakpoints | @media min-width aumenta, no disminuye styles | Desktop-first con media queries max-width |
| Viewport meta tag configurado | width=device-width, initial-scale=1, user-scalable=yes | User-scalable=no bloquea zoom accesibilidad |
| Sin horizontal scroll en mobile | Contenedor no excede viewport width en ningun breakpoint | Grid/table que fuerza overflow-x |
| Contenido adaptable a viewport | Tipografia fluida (clamp()), padding responsive, flex/grid adaptables | Fixed px widths en containers principales |
| Breakpoints logicos | Basados en content breakpoints, no device names específicos | Solo breakpoints iPhone/Mac/Desktop fijos |

## Prioridad 6 — Tipografía y Color (MEDIO)

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Body text ≥ 16px base | Font-size minimo 1rem/16px en body content | Body font 14px o menos sin buena razon |
| Line-height ≥ 1.5 para cuerpo | readability optimizada, especialmente en desktop | Line-height 1.0 o 1.1 compactado |
| Tokenización semantica de colores | --color-primary, --color-bg-surface, etc. en CSS vars | Hex #F4F1EA hardcodeado directamente en componentes |
| Semantic color tokens en design system | Colores nombrados por uso: primary, success, warning, error | Mismos hex en toda app sin distincion de rol |
| Maximo dos familias tipograficas distintas | Una para display/headings (si diferenciada), otra para body | Tres+ families en misma pagina |
| Type scale proporcional | Intervalos consistentes (1.25 major third recommended) | Tamaños arbitrarios sin sistema |

## Prioridad 7 — Animación y Motion (MEDIO)

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Context-aware timing | Animaciones relacionadas tienen timing coherente pero distinto | Diferentes velocidades para mismo tipo elemento |
| Motion conveye significado | Animación explica cambio de estado/espace/relacion | Animación decorativa sin purpose claro |
| Spatial continuity | Element mantiene path logico al moverse | Element teletransporta position nueva |
| Respects prefers-reduced-motion | Media query reduce/remove motion para sensibles | Motion obligatorio ignore preferencia usuario |
| Solo transform y opacity animan | GPU-accelerated, skip layout/paint | Animar width, height, padding, margin |
| Exit faster than enter | Release snappy (≤200ms), deliberate press lenta | Same duration enter y exit |
| Stagger items en grupos | Cascada natural 30-80ms spacing | Todos aparecen same time exacto |

## Prioridad 8 — Formularios y Feedback (MEDIO)

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Labels visibles permanentemente (no placeholder-only) | Placeholder complementa label, nunca reemplaza | Input sin label visible, solo placeholder |
| Error message near affected field | Validation inline/cerca campo invalido | Solo top-banner errors, field sin indication |
| Helper text para campos complejos | Instrucciones utiles antes/durante input | Campo password sin requirements visible |
| Progressive disclosure | Info progresiva mostrada segun necesidad | Todo formulario visible upfront overwhelm |
| Confirmation tras submit | CTA action reflected in interface immediately | Button dice "Submit", toast dice "Form submitted" |
| Vocabulary cohesion | Same button name throughout flow | "Publish", luego "Post", luego "Create"? Incoherent |

## Prioridad 9 — Patrones Navegación (ALTO)

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Back behavior predictable | Browser back closes modal, dismisses drawer | Modal open → back navigates away page |
| Bottom nav ≤5 items | Cognitive load limit respeccionado | 7+ tabs en bottom navigation |
| Deep linking soporta share | URL refleja vista actual, copy-paste work | Estado internal only, no URL reflect |
| Breadcrumbs/logical hierarchy | Ruta visible hacia arriba en navega profunda | Usuario perdido, no sabe donde esta |
| Active state clearly indicated | Item activo visible, no ambiguo cual section active | Sin indicador de pagina activa |

## Prioridad 10 — Graficos y Datos (BAJO)

| Regla | Check | Anti-pattern |
|-------|-------|-------------|
| Leyendas siempre presentes | Chart legend identifi every data series | Chart sin leyenda, colors without context |
| Tooltips en datos interactive | Hover/touch revela valor exacto serie | Valores abstractos sin numbers |
| Colores accesibles para graphs | Patterns/textures adicionales color distinction | Gráfico usa solo color para diferenciar series |
| Data labels directos cuando posible | Inline labels > legend when many series | Legend requerida para chart con 8+ lines |
| Axis labels with units | X/Y axis labeled with meaningful units | Numeric axis con sin context o units |
