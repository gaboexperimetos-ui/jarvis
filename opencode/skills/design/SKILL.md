---
name: design
description: Unified design skill merging Frontend Design (Anthropic), UI/UX Pro Max, Emil Kowalski Design Engineering, Web Design Guidelines (Vercel), and Impeccable. Covers distinctive visual identity, design system generation, animations, accessibility audits, typography, color palettes, interaction patterns, responsive layout, UX guidelines, performance, stack-specific implementation, and delivery-ready polish across web, mobile, and desktop.
user-invocable: true
---

# Design — Skill Unificado

Eres un equipo de diseño completo fusionado en una sola skill. Trabaja como **dirigente creativo**: decisiones intencionales, opinionadas, especificas del contexto. NUNCA predeterminadas IA.

## Ruta Base

Este skill vive en `~/.config/opencode/skills/design/`. Para invocar el motor de busqueda interno, usar siempre esta ruta absoluta:

```bash
python3 "${HOME}/.config/opencode/skills/design/scripts/search.py" "<query>" --domain <domain>
```

Si python3 falla, intentar `python` o `py -3`. Requiere Python 3.x (sin dependencias externas).

---

## Flujo General

### Paso 0: Identificar tema

Si brief no identifica producto, identificalo antes de disenyar: sujeto, audiencia, trabajo primario. Industria y lenguaje vernacular son donde nacen elecciones visuales distintas.

### Paso 1: Detectar pila y contexto

Extraer del request: tipo producto (SaaS, e-commerce, portfolio, dashboard, entretenimiento, tool), audiencia objetivo, keywords estilisticas. Detectar stack desde package.json o equivalentes. Si no detectable y stack importa para implementacion, preguntá. **Nunca asumir stack.**

### Paso 2: Si proyecto/pagina nuevo → Generar Sistema de Diseny

```bash
python3 "${HOME}/.config/opencode/skills/design/scripts/search.py" "<product_type> <industry> <keywords>" --design-system -p "Project Name"
```

Devuelve: patrones, estilo, colores, tipografia, efectos, anti-patterns a evitar.

**Persistir** para sesiones futuras (`--persist` + `--output-dir "<project-root>"`):
- `design-system/<slug>/MASTER.md` — Fuente unica verdad
- `design-system/<slug>/pages/<page>.md` — Overrides por pagina

**Dials opcionales:** `--variance <1-10>` (minimal→bold), `--motion <1-10>` (subtle→complex), `--density <1-10>` (spacious→dense).

Retirada construyendo pagina: leer MASTER primero, verificar override pagina.

### Paso 3: Consulta dirigida

```bash
python3 "${HOME}/.config/opencode/skills/design/scripts/search.py" "<query>" --domain <domain>
```

| Necesidad | Domain | Ejemplo |
|-----------|--------|---------|
| Patrones producto | `product` | `"dashboard analytics"` |
| Estilos visuales | `style` | `"glassmorphism dark"` |
| Paletas color | `color` | `"entertainment vibrant"` |
| Tipografia | `typography` | `"playful modern"` |
| Fuentes Google | `google-fonts` | `"sans serif variable"` |
| UX practicas | `ux` | `"error summary validation"` |
| Landing page | `landing` | `"hero social-proof"` |
| Iconos | `icons` | `"decorative icon aria hidden"` |
| GSAP animaciones | `gsap` | `"scroll reveal stagger"` |
| Graficos/charts | `chart` | `"real-time dashboard"` |
| Rendimiento React | `react` | `"rerender memo list"` |

### Paso 4: Guia por stack

```bash
python3 "${HOME}/.config/opencode/skills/design/scripts/search.py" "<query>" --stack <stack>
```

Stacks: `react`, `nextjs`, `vue`, `svelte`, `astro`, `nuxtjs`, `nuxt-ui`, `angular`, `laravel`, `swiftui`, `react-native`, `flutter`, `jetpack-compose`, `html-tailwind`, `shadcn`, `threejs`, `javafx`, `wpf`, `winui`, `avalonia`, `uno`, `uwp`.

---

## Prioridad de Reglas (de #1 a #10)

Segun impacto, priorizar asi:

| # | Categoria | Impacto | Dominio | Checks clave | Anti-patterns |
|---|-----------|---------|---------|-------------|---------------|
| 1 | Accesibilidad | CRITICO | `ux` | Contrast 4.5:1, Alt text, Nav teclado, Aria-labels | Remover focus rings, Botones solo icono sin label |
| 2 | Touch/Interaccion | CRITICO | `ux` | Min 44x44px, Espaciado 8px+, Feedback carga | Hover unico, Cambios instantaneos (0ms) |
| 3 | Performance | ALTO | `ux` | WebP/AVIF, Lazy loading, CLS < 0.1 | Layout thrashing, Cumulative Layout Shift |
| 4 | Estilo | ALTO | `style`,`product` | Match tipo prod, Consistencia, Iconos SVG | Mezclar flat/skeuomorphic random, Emoji icons |
| 5 | Layout Responsive | ALTO | `ux` | Mobile-first breakpoints, Viewport meta, Sin scroll horz | Scroll horizontal, Widths fijas px, Disable zoom |
| 6 | Tipografía/Color | MEDIO | `type`,`color` | Base 16px, Line-height 1.5, Tokens semanticos | Texto < 12px body, Gray-on-gray, Hex raw en comps |
| 7 | Animación | MEDIO | `ux`,`gsap` | Timing contextual, Motion da significado, Espacial continua | Una duracion todo, Animar width/height, Sin reduced-motion |
| 8 | Formularios | MEDIO | `ux` | Labels visibles, Error cerca campo, Helper text, Disclosure progre | Placeholder-only, Errores arriba solo, Overwhelm upfront |
| 9 | Navegacion | ALTO | `ux` | Back predecible, Bottom nav ≤5, Deep linking | Nav sobrecargada, Back roto, Sin deep links |
| 10 | Graficos/Data | BAJO | `chart` | Leyendas, Tooltips, Colores accesibles | Solo color conveyer meaning |

Ver `references/priority-checklist.md` para reglas completas por categoria.

---

## Directrices Integrales

### Direccion Visual y Estética

Ser dirigente creativo en estudio: dar identidad visual distinta que NO parezca nadie mas. Cliente rechazo propuestas cliché; merece vision propia.

- Fundamentar diseños en materia prima: toy ninas 8-11 esteticamente distinto dashboard financiero.
- Hero = lo primero que ven: titular, imagen, animacion, demo, momento interactivo. Elegir deliberadamente.
- Tipografia lleva personalidad. MAXIMO dos families claramente distintas. No necesitas diferente typeface para display y cuerpo.
- **Defaults peligrosos IA** (solo usar si justificado explicitamente): fondo crema cálido #F4F1EA con accent terracotta; near-black con green acid; SaaS-card kit border-radius uniforme soft grey shadow gradient washes; eyebrows ALL-CAPS, middle dots meta strings, '→' en botones link-text.

### Principios de Tipografía

- Defaults: lineas < 80 caracteres. Serif con line-height mayor que sans-serif.
- Evitar: acotar una sola palabra headline, labels ALL CAPS, etiquetas tipograficas innecesarias sobre contenido.
- Type como headline = tratamiento activo parte del diseno, no entrega vehiculo neutral contenido.
- Consultas rápidas: `search.py` con `--domain typography` o `--domain google-fonts`.

### Estructura Visual

Dispositivos estructurales codifican informacion util, no decoran: outlines, borders, numbering, dividers. Antes de anadir numbered markers (#01/#02/#03), verificar content realmente secuencia.

Motion non-triggered: sparsamente. Un momento orchestrado (fade-slide-up por seccion, hover cards) lee como default generado.

### Content y Copywriting

Palabras = hacen entender/usar. Intencionalidad minima como spacing/color.
- End-user perspective: users manage notifications, not webhook config.
- Active voice default: CTA dice exactamente que pasa ("Save changes", no "Submit").
- Failure/emptiness: explicar que paso y como reparar. Errors no apologizan, never vague. Empty screen = invitation to act.

### Reduccion y Auto-critica

Gastar osadia en UN lugar. Dejar elemento memorable, quieto disciplinado alrededor. Cortar toda decoracion que no sirva brief. Build quality floor sin anunciarlo: mobile-responsive, keyboard-focus visible, reduced-motion respected, accessible, harmony colors. Criticar propio trabajo constantemente. Remover un accessory antes de salir casa.

---

## Polish Componentes (Impeccable)

Antes de entregar UI nativa/mobile app: ver `references/pro-rules.md` completar Pre-Delivery Checklist (iconos/disiplina visual, feedback interaccion, light/dark contrast, safe-area layout, acessibilidade).

Cuando revisar UI code: tablas Markdown con Before/After columnas. Formato tabla, NO listas separadas.

Referencias: `references/components.md`, `references/critique.md`, `references/polish.md`.

---

## Animacion y Motion (Emil Kowalski)

### Decision Framework

**1. ¿Debe animarse?** Frecuencia dicta decision:
- 100+/dia (shortcuts, palette toggle) → NO ANIMAR JAMAIS. Raycast no tiene open/close animation. Optimal para algo usado cientos veces dia.
- Decenas/dia (hover, list nav) → REMOVER o reducir drasticamente.
- Ocasional (modals, drawers, toasts) → Standard animation.
- Raro/first-time (onboarding, feedback forms, celebrations) → Puede adicionar delight.

**NUNCA animar acciones de teclado.** Repetidas cientos veces diario. Animaçao faz lentido, delay, disconnect.

**2. Proposito:** spatial consistency, state indication, explanation, feedback, prevenir cambios abruptos. Si purpose = "cool visual" y usuario vera seguido → NO ANIMAR.

**3. Easing:**
- Entrando → ease-out (starts fast, feels responsive)
- Moviendo/morfo on-screen → ease-in-out
- Hover/color → ease
- Marquee/progress bar → linear
- Default → ease-out
- **NUNCA ease-in UI animations.** Starts slow → sluggish, unresponsive. Dropdown ease-in 300ms feels slower que ease-out 300ms.

**Curvas custom obligatorias** (never built-in CSS easings):
```css
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

**4. Duracion:**
- Button press → 100-160ms
- Tooltips/small popovers → 125-200ms
- Dropdowns/selects → 150-250ms
- Modals/drawers → 200-500ms
- Marketing/explanatory → longer ok

**Regla general:** UI animations under 300ms. 180ms dropdown feels more responsive than 400ms. Spinner mas rapido = load parece faster.

### Spring Animations

Springs simulan real fisica. Ideal para drag interactions, elementos alive (Apple Dynamic Island), gestos interruptibles, mouse-tracking decorative.

Config Apple-recommended: `{ type: "spring", duration: 0.5, bounce: 0.2 }`
Bounce subtle 0.1-0.3. Evitar la mayoria contexts UI. Solo drag-to-dismiss y playful interactions.

Interruptibilidad advantage: springs mantienen velocity when interrupted — CSS/keyframes restart zero. Para gestures que cambian mid-motion, springs son ideales.

### Component Building Principles

- **Buttons:** `transform: scale(0.97)` on `:active`. Subtle 0.95-0.98. Instant feedback.
- **Never scale(0):** nada real desaparece completamente. Empezar `scale(0.9)+` con opacity. Even barely-visible shape hace entrance feel natural como balloon deflated.
- **Popovers origin-aware:** `transform-origin: var(--transform-origin)` desde trigger. Excepcion: modals quedan `center`.
- **Tooltips subsequentes:** skip delay + skip animation tras uno abierto. Tooltip[data-instant] transition-duration: 0ms.
- **CSS transitions > keyframes** para dynamic/repeatedly triggered UI (interruptible). Keyframes restart zero; transitions retarget smoothly.
- **Blur masks imperfect crossfades:** `filter: blur(2px)` entre states. Keep under 20px expensive Safari. Combine scale-on-press para button state polished.
- **@starting-style** moderno CSS enter states (Firefox 112+). Fallback: `data-mounted` attribute pattern.

### Transform Mastery

- `translateY(%)` relativo size own element (Sonner/Vaul). Prefer over hardcoded px values. Adapta a content.
- `scale()` scales children too — feature for button press (font/icons scale proporcionalmente).
- `clip-path: inset()` powerful: hold-to-delete (2s linear + release 200ms ease-out), image reveals on-scroll, comparison sliders, tabs perfect color transition (duplicar tab list clip layer activa).
- **Gestures:** momentum-based dismissal (velocity > 0.11 dismiss regardless distance). Damping at boundaries. Pointer capture. Multi-touch protection. Friction vs hard stops.

### Performance Animación

- SOLO animar `transform` y `opacity` → GPU. Animar padding/margin/height/width triggers layout paint reflow.
- CSS vars inheritables: cambiar en padre recalcula styles TODOS hijos. Actualizar `transform` directo en element, no via CSS var (`--swipe-amount`).
- **Framer Motion caveat:** shorthand props (`x`, `y`, `scale`) NOT hardware accelerated. Usar `transform: "translateX()"` string.
- **CSS animations beat JS under load** (off-main-thread). CSS predetermined animations, JS dynamic/interruptible.
- **WAAPI** programmatic CSS: JavaScript control + CSS performance, hardware-accelerated, no library needed.

### Accessibility Animaciones

- `prefers-reduced-motion`: menos/no movement pero KEEP opacity/color transitions comprehension.
- **Touch hover gates:** `@media (hover: hover) and (pointer: fine)` gate hover animations. Touch devices trigger hover on tap → false positives.

### Stagger Animations

30-80ms entre items. Decorative — nunca bloquear interaction mientras playing.

### Sonner Principles (Componentes Amados)

1. Developer experience: menos friction adoptar = mas usan.
2. Good defaults > options. Ship beautiful out-of-box.
3. Naming crea identidad: "Sonner" French=ringer > "react-toast". Sacrifice discoverability para memorability.
4. Edge cases invisibles: pause timers tab hidden, pseudo-elements gaps stacked toasts, pointer capture during drag.
5. Transitions no keyframes para dynamic UI.
6. Great documentation site lowers adoption barrier.

**Cohesion:** Animation style match component mood, page design, name — everything harmony. Playful=bouncier, professional dashboard=cristal/rápido.

**Asymmetric enter/exit:** Slow donde usuario decide (hold-to-delete 2s linear), fast donde sistema responde (release 200ms ease-out).

Ver `references/animations.md` para guia completa.

---

## Accesibilidad (Vercel Web Design Guidelines)

Al pedir "review my UI", "check accessibility", "audit design", "WCAG compliance":

1. Fetch latest rules:
```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```
2. Read specified files.
3. Apply all rules.
4. Output findings formato `file:line`.

100+ regras: ARIA attributes, visible focus states, labeled inputs, touch target sizes, reduced-motion support, semantic HTML, keyboard navigation, heading hierarchy, mas. Ver `references/accessibility.md` resumen local.

---

## Si Busqueda Devuelve 0 Resultados

NO fabricar output. Orden:
1. Reintentar query mas narrow o domain/stack explicito.
2. Si aun vacio, fallback priority table y decir explicitamente que recommendation viene de built-in defaults, NO database match ("no palette match for X, using general SaaS defaults").
3. Nunca presentar 0-result como si devolviera data.

---

## Workflow Completo Ejemplo

Request: "Make an AI search homepage." (stack Next.js detectado)

```bash
# Step 2: design system
python3 "${HOME}/.config/opencode/skills/design/scripts/search.py" "AI search tool modern minimal" --design-system -p "AI Search"

# Step 3: supplement targeted concern
python3 "${HOME}/.config/opencode/skills/design/scripts/search.py" "keyboard focus modal" --domain ux

# Step 4: stack guidelines
python3 "${HOME}/.config/opencode/skills/design/scripts/search.py" "suspense streaming bundle" --stack nextjs
```

Synthesis final: design system + detailed searches + animation policy + accessibility audit + polished deliverable.

---

## Estructura Interna

Esta skill unifica cinco fuentes:
- **Frontend Design** (Anthropic) → estetica distinctiva, anti-template, writing principles
- **UI/UX Pro Max** → 79 styles, 192 palettes, 74 font pairings, 119 UX guidelines, 105 icons, 25 charts, 22 stacks, 17 GSAP presets + motor busqueda BM25 Python
- **Emil Kowalski Design Eng** → animations, springs, gestures, micro-interactions, transform mastery, clip-path, Sonner principles
- **Web Design Guidelines** (Vercel) → WCAG audit, 100+ rules correctness, live fetch remote source
- **Impeccable** → component polish, critique workflow, pro-rules delivery checklist

Archivos referencia internos:
- `references/animations.md` → Full animation & motion guide completa
- `references/accessibility.md` → WCAG audit rules resumen local
- `references/priority-checklist.md` → Priority-based rule index detallado
- `references/pro-rules.md` → Pre-delivery checklist native/app UI
- `references/components.md` → Impeccable component review patterns
- `references/critique.md` → Self-critique y refinement methods

Datos y scripts motores: `data/` y `scripts/` de UI/UX Pro Max preservados intactos, funcionales con Python 3.x standalone.
