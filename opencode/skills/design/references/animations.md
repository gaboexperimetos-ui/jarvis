---
name: animations
source: emil-design-eng + ui-ux-pro-max
description: Complete animation, motion design, springs, gestures, transform, clip-path, performance rules, and accessibility guidelines.
---

# Guia Completa de Animacion y Motion Design

## Decision Framework — Antes de Cualquier Animación

**PREGUNTAR ORDENADAMENTE:**

### 1. Frecuencia → Decision de animar
- **100+ veces/dia** (shortcuts, command palette toggle) → **NO ANIMAR JAMAIS**. Raycast sin open/close animation = optimal experience para algo usado cientos veces diario.
- **Decenas/dia** (hover effects, list navigation) → REMOVER o reducir drasticamente.
- **Ocasional** (modals, drawers, toasts) → Standard animation apropiada.
- **Raro/first-time** (onboarding, feedback forms, celebrations) → Pode adicionar delight.

**NUNCA animar acciones de teclado.** Delay hace interface sentir lenta, disconnecta usuario.

### 2. Proposito valido
- **Spatial consistency** → toast entra/sale same direction → swipe-dismiss intuitive.
- **State indication** → morphing button muestra state change.
- **Explanation** → marketing animation que explica feature funcion.
- **Feedback** → button escala down on press → interface escucha.
- **Prevenir cambios abruptos** → elements appear/disappear sin transition → feel broken.

Si purpose solo "se ve cool" y usuario vera seguido → NO ANIMAR.

### 3. Easing segun tipo
```
Entrando? → ease-out (starts fast, feels responsive)
Moviendo/morfo on screen? → ease-in-out (natural acceleration/deceleration)
Hover/color change? → ease
Constant motion (marquee, progress bar)? → linear
Default general → ease-out
```

**Curvas custom obligatorias** (never built-in CSS):
```css
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

**NUNCA use ease-in en UI animations.** Empieza lento → sluggish. Dropdown ease-in 300ms se siente MAS LENTO que ease-out 300ms.

Usar [easing.dev](https://easing.dev/) o [easings.co](https://easings.co/) para encontrar variants fuertes de easings standard.

### 4. Duracion por element
| Element | Duracion |
|---------|----------|
| Button press feedback | 100-160ms |
| Tooltips, small popovers | 125-200ms |
| Dropdowns, selects | 150-250ms |
| Modals, drawers | 200-500ms |
| Marketing/explanatory | Puede ser mas largo |

**Regla:** UI animations under 300ms. 180ms dropdown feels more responsive than 400ms. Spinner spin mas rapido = loading parezca faster (mismo load time real, diferente perception).

## Perceived Performance

Speed en animation afecta perception directamente:
- Fast spinner → loading parece mas rapido
- 180ms select animation → feels more responsive que 400ms
- Instant tooltips tras first tooltip open → toolbar completa se siente faster

Easing amplifica: ease-out 200ms se SIENTE mas rápido que ease-in 200ms porque user ve movimiento inmediato.

## Spring Animations

Springs simulan real fisica, no durations fijas → settle based parameters fisicos.

### Cuando usar springs
- Drag interactions con momentum
- Elements que deben sentir "alive" (Apple Dynamic Island)
- Gestos interruptibles mid-animation
- Mouse-tracking decorative interactions

### Configuracion Apple-recommended
```javascript
{ type: "spring", duration: 0.5, bounce: 0.2 }
```

### Traditional physics (mas control)
```javascript
{ type: "spring", mass: 1, stiffness: 100, damping: 10 }
```

Bounce subtle (0.1-0.3). Evitar en la mayoria contexts UI. Solo drag-to-dismiss y playful interactions ok.

**Ventaja interruptibilidad:** Springs mantienen velocity when interrupted — CSS/keyframes restart zero. Click expanded item + quick Escape → spring reverses smoothly desde position actual.

### Spring-based mouse interactions
Mouse tracking directo a visual changes artificial senza motion. Usar spring interpolation:
```javascript
const springRotation = useSpring(mouseX * 0.1, {
  stiffness: 100,
  damping: 10,
});
```

Decorativo = OK. Funcional banking chart = no animation mejor. Distinguir cuando decoration ayuda vs hindre.

## Component Building Principles

### Buttons must feel responsive
```css
.button {
  transition: transform 160ms ease-out;
}
.button:active {
  transform: scale(0.97);
}
```
Scale subtle (0.95-0.98). Aplica a todo pressable element. Instant feedback, UI se siente que escucha.

### Never animate from scale(0)
Nada en mundo real desaparece completamente. Desde `scale(0.9)+` combinado opacity. Even barely-visible shape hace entrance feel natural como balloon deflated tiene shape visible aunque deflated.

```css
/* Mal */ .entering { transform: scale(0); }
/* Bien */ .entering { transform: scale(0.95); opacity: 0; }
```

### Popovers origin-aware
Popovers escalan desde trigger, NO desde center. `transform-origin: var(--transform-origin)` base UI. **Excepcion: modals.** Modals quedan `center` porque no anchored a specific trigger — aparecen centred viewport.

### Tooltips: skip delay subsequentes
Tooltip delay inicial previene accidental activation. Pero tras uno abierto, hovers adyacentes instantaneamente sin animacion. Se siente mas rapido sin defeat purpose initial delay.

### CSS transitions > keyframes para dynamic UI
Transitions: interruptible y retarget mid-animation. Keyframes: restart zero desde inicio. Para interacciones rapidas (toasts multiples, toggles), transitions produce smoother results.

### Blur masks imperfect crossfades
Crossfade entre states feeling off despite different easings/durations? Anadir `filter: blur(2px)` durante transicion.
- Sin blur: ves dos objects distintos superposing → unnatural
- Con blur: bridge gap blending dos states juntos → single smooth transformation perceived

Combine con scale-on-press para button state polished. Keep blur < 20px expensive Safari.

### @starting-style enter states modernos CSS
Firefox 112+, reemplaza useEffect mounted pattern:
```css
.toast {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 400ms ease, transform 400ms ease;
  @starting-style {
    opacity: 0;
    transform: translateY(100%);
  }
}
```

Fallback legacy: `data-mounted={mounted}` attribute pattern (funciona todos browsers).

## Transform Mastery

### translateY con porcentajes
% relativo al size proprio del elemento. `translateY(100%)` mueve por height propio, independiente dimensiones reales. Sonner posicione toasts, Vaul hide drawer antes animate in.

**Prefer % sobre px hardcoded.** Menos error-prone, adapta a content.

### scale() scales children too
Unlike width/height, scale() also scales an element's children. Font-size, icons, content scale proporcionalmente. Feature not bug para button press.

### 3D transforms para depth
`rotateX()`, `rotateY()` + `transform-style: preserve-3d` crean efectos reales 3D en CSS. Orbiting, coin flips, depth effects sin JavaScript.

### transform-origin
Cada element tiene anchor point transforms ejecutan. Default center. Set para match trigger location para origin-aware interactions.

## clip-path para Animaciones

### The inset shape
`clip-path: inset(top right bottom left)` define rectangular clipping region. Cada value "eats" into element desde ese lado.

```css
.hidden { clip-path: inset(0 100% 0 0); }
.visible { clip-path: inset(0 0 0 0); }
```

**Casos uso:**
- **Hold-to-delete:** overlay `clip-path: inset(0 100% 0 0)` → active transition a `inset(0 0 0 0)` 2s linear → release snap back 200ms ease-out + `scale(0.97)` button
- **Image reveals on scroll:** `clip-path: inset(0 0 100% 0)` hidden bottom → animate `inset(0 0 0 0)` viewport entry. IntersectionObserver o Framer Motion `useInView({ once: true, margin: "-100px" })`.
- **Comparison sliders:** Overlay dos images. Clip top con `clip-path: inset(0 50% 0 0)`. Adjust right inset value based on drag position. Hardware-accelerated, no extra DOM.
- **Tabs perfect color transition:** Duplicate tab list. Style copy as active (bg/text diff). Clip copy visible solo active tab. Animate clip → seamless color transition timing individual colors nunca achieve.

## Gesture y Drag Interactions

### Momentum-based dismissal
No require drag past threshold. Calcular velocity: `Math.abs(dragDistance) / elapsedTime`. Si velocity > ~0.11 → dismiss regardless distance. Quick flick suficiente.

```javascript
const velocity = Math.abs(swipeAmount) / 
  (new Date().getTime() - dragStartTime.current.getTime());
if (Math.abs(swipeAmount) >= THRESHOLD || velocity > 0.11) dismiss();
```

### Damping at boundaries
Drag past natural boundary (drawer up ya en top) → aplicar damping. Mas drags, menos element moves. Real life doesn't suddenly stop → slows down primero.

### Pointer capture for drag
Tras iniciar drag → capturar ALL pointer events. Drag continua mesmo si pointer leaves element bounds.

### Multi-touch protection
Ignorar additional touch points tras initial drag begin. Switching fingers mid-drag causa element jump to new position.

```javascript
function onPress() { if (isDragging) return; /* start drag */ }
```

### Friction instead of hard stops
En lugar de prevenir upward drag completamente → permitir com increasing friction. Natural que invisible wall.

## Performance Rules Animación

### SOLO animar transform y opacity
GPU-accelerated, skip layout paint render steps. Animar padding, margin, height, width → triggers all three rendering steps.

### CSS variables inheritables
Cambiar CSS variable en padre recalcula styles TODOS hijos. Drawer con many items, actualizar `--swipe-amount` container → expensive recalculation. Actualizar `transform` directo element.

```javascript
// Mal: triggers recalc todos hijos
element.style.setProperty('--swipe-amount', `${distance}px`);

// Bien: solo afecta este element  
element.style.transform = `translateY(${distance}px)`;
```

### Framer Motion hardware acceleration caveat
Shorthand props (`x`, `y`, `scale`) NOT hardware accelerated. Usan `requestAnimationFrame` main thread. Full `transform` string → GPU accelerated.

```jsx
// NO hardware accelerated (drops frames bajo carga)
<motion.div animate={{ x: 100 }} />

// Hardware accelerated (smooth incluso main thread busy)
<motion.div animate={{ transform: "translateX(100px)" }} />
```

Vercel dashboard tab animation con Shared Layout Animations → dropped frames page loads. Cambiar a CSS animations (off-main-thread) fix.

### CSS animations beat JS under load
CSS animations off-main-thread. Browser busy loading page → Framer Motion `requestAnimationFrame` drops frames. CSS permanece smooth.

**Rule:** CSS para predetermined animations, JS para dynamic/interruptible ones.

### WAAPI para programmatic CSS
Web Animations API = JavaScript control + CSS performance. Hardware-accelerated, interruptible, no library needed.

```javascript
element.animate([
  { clipPath: 'inset(0 0 100% 0)' }, 
  { clipPath: 'inset(0 0 0 0)' }
], { duration: 1000, fill: 'forwards', easing: 'cubic-bezier(0.77, 0, 0.175, 1)' });
```

## Accessibility Animaciones

### prefers-reduced-motion
Animations pueden causar motion sickness. Reduced motion = fewer/gentler animations, ZERO. Keep opacity/color transitions comprehension aid. Remove movement/position animations.

```css
@media (prefers-reduced-motion: reduce) {
  .element { animation: fade 0.2s ease; /* No transform-based motion */ }
}
```

### Touch device hover states
Touch devices trigger hover on tap → false positives. Gate hover animations:
```css
@media (hover: hover) and (pointer: fine) {
  .element:hover { transform: scale(1.05); }
}
```

## Stagger Animaciones

Items entering together → stagger appearance. Cascading effect feel natural vs appearing simultaneously.

```css
.item { opacity: 0; transform: translateY(8px); animation: fadeIn 300ms ease-out forwards; }
.item:nth-child(1) { animation-delay: 0ms; }
.item:nth-child(2) { animation-delay: 50ms; }
.item:nth-child(3) { animation-delay: 100ms; }
.item:nth-child(4) { animation-delay: 150ms; }
```

Stagger delays cortos (30-80ms entre items). Long delays hace interface sentir slow. Decorative — nunca bloque interaction mientras playing.

## Sonner Principles — Building Loved Components

1. **Developer experience es clave.** No hooks, no context, no complex setup. Insert `<Toaster />` una vez, `toast()` desde anywhere. Menos friction adoptar = mas usan.

2. **Good defaults importan mas que opciones.** Ship beautiful out-of-box. Majority usuarios nunca customizen. Default easing, timing, visual design excelente.

3. **Naming crea identity.** "Sonner" (French=ringer) elegante > "react-toast". Sacrifice discoverability para memorability cuando appropriate.

4. **Handle edge cases invisibly.** Pause timers tab hidden. Pseudo-elements gaps stacked toasts mantener hover state. Capture pointer during drag. User never notices → exacto correcto.

5. **Transitions NO keyframes para dynamic UI.** Toasts adicion rapidos. Keyframes restart zero interrupcion. Transitions retarget smoothly.

6. **Great documentation site.** Interactive examples ready code snippets bajan barrier adoption.

### Cohesion
Sonner animation satisfaction parcialmente porque whole experience cohesive. Easing/duration viben library. Slower que typical UI animations, usa `ease` no `ease-out` feel elegant. Animation style matches toast design, page design, name — everything harmony.

Al elegir animation values, considerar personality componente. Playful = bouncier. Professional dashboard = crisp/fast. Match motion a mood.

### Asymmetric enter/exit timing
Pressing slow donde necesita deliberation (hold-to-delete 2s linear), release siempre snappy (200ms ease-out). Slow donde usuario decide, fast donde sistema responde.

### Opacidad + altura combination
Cuando items enter/exit list, opacity debe funcionar bien con height animation. Trial-error. No formula — adjust until feels right.

## Debugging Animaciones

### Slow motion testing
Aumentar duration temporal 2-5x normal. DevTools animation inspector slow playback.

Check en slow motion:
- Colors transition smoothly o ves dos states distinct overlapping?
- Easing feels right o starts/stops abruptly?
- transform-origin correcto o element scale wrong punto?
- Multiple animated properties (opacity, transform, color) sync?

### Frame-by-frame inspection
Chrome DevTools Animations panel step through frame by frame. Revela timing issues entre coordinated properties invisible full speed.

### Test on real devices
Phone USB IP local dev server → Safari remote devtools. Xcode Simulator alternative pero real hardware better para gesture testing.

## Review Checklist Animaciones

| Issue | Fix |
|-------|-----|
| `transition: all` | Especificar propiedades exactas: `transition: transform 200ms ease-out` |
| `scale(0)` entry animation | Empezar desde `scale(0.95)` con `opacity: 0` |
| `ease-in` en UI element | Switch a `ease-out` o custom curve |
| `transform-origin: center` popover | Set a trigger location o `var(--transform-origin)` (modals exempt → centered) |
| Animacion en accion de teclado | Remover animacion completamente |
| Duration > 300ms en UI element | Reducir a 150-250ms |
| Hover animation sin media query | Agregar `@media (hover: hover) and (pointer: fine)` |
| Keyframes en elemento rapido-trigger | Usar CSS transitions para interruptibility |
| Framer Motion `x`/`y` bajo carga | Usar `transform: "translateX()"` hardware acceleration |
| Mismo enter/exit transition speed | Hacer exit mas rapide que enter |
| Todos elementos aparecen mismo tiempo | Agregar stagger delay (30-80ms entre items) |
