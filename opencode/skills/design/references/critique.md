---
name: critique
source: frontend-design + impeccable
description: Self-critique methods, refinement techniques, anti-patterns detection, and design polish strategies.
---

# Metodos de Critica y Refinamiento de Diseno

## Detection de Anti-Patrones IA

### Defaults Peligrosos que Aparecen en Generacion IA

Estos traits legitimos para algunos briefs son defaults, NO choices:

1. **Fondo crema cálido #F4F1EA** con serif display high-contrast y accent terracotta/warm-clay (#D97757). Común porque Anthropic's interaction accent usa tono similar → lee como tell genérico.

2. **Near-black background** con single bright acid-green o vermilion accent. Default oscuro dramatico sin personalidad especifica.

3. **Broadsheet layout** con hairline rules, zero border-radius, dense newspaper columns. Aprovecha cuando brief es editorial; generic si no.

4. **SaaS-card kit**: content chopped identical rounded cards, un border-radius todo, soft grey shadow rgba(0,0,0,.1), gradient washes decoration. El template mas comun generado por IA.

5. **Template chrome** aparece sin importar tema: eyebrow tracked-out ALL-CAPS sobre cada heading, meta strings middle dots ('A · B · C'), 'WORD — fragment' spaced em dash, tinted near-black (#0B0B0B #111) stand-in black, monospace small data labels, '→' appended link/button text.

**Regla:** Si el brief pinna direction visual especifica, seguirlo exactamente. Si deja axis libre, NO gastar esa libertad en uno de estos defaults. Donde la libertad queda disponible, usarla para algo unique del proyecto.

### Auto-Detektion Antes de Construir

Antes de escribir codigo:
1. Brainstorm short design plan basado en brief del cliente.
2. Revisar plan contra brief ANTES de construir.
3. Si cualquier parte lee como default generico que produciria para cualquier pagina similar → revisar esa parte.
4. Decir QUE cambiaste y PORQUE.
5. Solo despues confirmar relative uniqueness plan → empezar escribir codigo.

---

## Methods de Critica Auto-Correctiva

### Metodo Chanel

Antes de dejar casa (entregar diseno):
1. Mirar espejo (review completo del trabajo).
2. Remover UN accessory (un elemento decorativo que no esencial).
3. Repetir hasta decision final.

Aplica a UI: eliminar toda decoration que no sirva brief especifico. Spender boldness en UN lugar. Todo alrededor quieto y disciplined.

### Review con Ojos Frescos

- Revisar animaciones siguiente dia tras desarrollo. Perfecciones invisibles durante development se vuelven evidentes next day.
- Play animations slow-motion o frame-by-frame para spot timing issues invisible full speed.
- Test en dispositivo real para touch interactions (drawers, swipe gestures). Xcode Simulator alternative pero hardware real mejor gesture testing.

### Comparacion con Referencias Humanas

Human creatives tienen memory y siempre intentan algo nuevo. Si tienes space quick notes about tried approaches, ayuda future passes. Keep mental repository of what you've done vs what could be different.

---

## Estrategias de Refinamiento

### Typography Refinement

| Problema | Solucion | Impacto |
|----------|----------|---------|
| Typeface feels generic | Swap para font menos obvious, same category | Instant personality shift |
| Scale feels arbitrary | Define system: 1rem base, 1.25 major third steps | Coherent hierarchy emerges |
| Line length too long | Adjust max-width ~65ch for body text | readability improves dramatically |
| Heading-weight relationship unclear | Bold headline weight, lighter body within same family | Visual hierarchy via weight contrast |
| All caps labels | Use sentence case or proper capitalization | More approachable, less template-feel |

### Color Refinement

| Problema | Solucion | Impacto |
|----------|----------|---------|
| Palette looks SaaS-generic | Inject subject-matter-specific color | Unique identity emerges from content |
| Accent too aggressive or dull | Recalculate saturation/lightness for context | Accent pops without dominating |
| Dark mode breaks contrast | Verify all light/dark pairs meet 4.5:1 ratio | Accessibility maintained across themes |
| Color tokens hardcoded | Extract to CSS custom properties | Consistency + theme-swappable |

### Layout Refinement

| Problema | Solucion | Impacto |
|----------|----------|---------|
| Grid feels rigid | Introduce intentional asymmetry in one section | Breaks template feel, adds interest |
| Padding inconsistent | Systematize spacing scale (8px base multiplier) | Cohesive rhythm throughout |
| Content width too wide | Constrain main content to ~65ch-75ch | Better reading experience |
| Mobile only scaled-down desktop | True mobile-first breakpoint thinking | Layout makes sense at every size |
| Horizontal scroll appears | Remove fixed-width elements, use flex/grid | Responsive without scroll bar |

### Animation Refinement

| Problema | Solucion | Impacto |
|----------|----------|---------|
| One duration for everything | Vary by element type (see timing table) | Each animation fits its purpose |
| No reduced-motion support | @media query wraps motion code | Inclusive, no motion sickness |
| Animations restart on interrupt | Use transitions, not keyframes, for dynamic | Smooth regardless of trigger speed |
| Stagger feels robotic | Randomize delays ±10ms or natural variation | Organic feel vs machine-perfect |
| Enter equals exit duration | Exit faster than enter (asymmetric timing) | Polished, professional impression |

---

## Checklist Pre-Entrega Rapido

Antes de entregar cualquier UI:

- [ ] Anti-patterns IA presentes? Si, revisados y eliminados/justificados.
- [ ] Typographic scale systematized? Max 2 families tipograficas distintas.
- [ ] Colors tokenizados semanticamente? Sin hex raw en componentes.
- [ ] Contrast ≥ 4.5:1 texto normal? Verificado ambos modos light/dark.
- [ ] Focus states visibles keyboard nav? Tab order logical.
- [ ] Touch targets ≥ 44x44px? Espaciado ≥ 8px entre targets.
- [ ] Animaciones under 300ms UI? Easing custom aplicado.
- [ ] prefers-reduced-motion respected? Motion removido/gentle para sensibles.
- [ ] Hover gated `@media (hover: hover)`? Touch devices no false positives.
- [ ] Performance: solo transform+opacity animated? GPU accelerated.
- [ ] Copy end-user perspective? Active voice, specific action verbs.
- [ ] Empty/error states con guidance? No pantallas muertas sin direccion.
- [ ] Mobile responsive desde baseline? Viewport configured correctamente.
- [ ] Structural devices meaningful? Borders/dividers encode info, no decorate.
- [ ] Un elemento memorable, resto quieto disciplinado? Reduccion aplicada.
