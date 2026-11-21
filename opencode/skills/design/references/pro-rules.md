---
name: pro-rules
source: impeccable + ui-ux-pro-max
description: Pre-delivery checklist for native/mobile app UI polish. Covers icon discipline, interaction feedback, light/dark contrast, safe-area layout, accessibility — scoped to iOS/Android/React Native/Flutter.
---

# Pre-Delivery Checklist — App UI Nativa/Mobile

Antes de entregar cualquier UI mobile/native app, verificar cada item de esta lista canonica. No entregar sin completar todos los checks.

## Iconos y Elementos Visuales

| Check | Estado | Detalle |
|-------|--------|---------|
| SVG icons preferidos sobre emojis | [ ] | Vectoriales escalables consistentes stroke-width |
| Iconos semanticamente correctos | [ ] | Busca para intent, no por apariencia |
| Consistent sizing icon set | [ ] | Todos icons same pixel height/baseline |
| Decorative icons aria-hidden=true | [ ] | Screen reader no announces decorative elements |
| Icons have accessible labels | [ ] | Icon-only buttons tienen label descriptivo |
| Visual hierarchy icons meaningful | [ ] | Sizes/weights correspond important levels |
| Loading states visual claro | [ ] | Skeletons o spinners durante async operations |
| Empty states con action invited | [ ] | No pantallas vacias sin guidance |

## Feedback de Interaccion

| Check | Estado | Detalle |
|-------|--------|---------|
| Touch targets ≥ 44x44px | [ ] | Minimo tap area todo interactive element |
| Press feedback presente | [ ] | scale(0.97) u opaque-down en active state |
| Haptic feedback donde apropiado | [ ] | Confirm actions, errors, toggles clave |
| Loading/disabled estado clear | [ ] | Submit button disabled while processing |
| Success/error feedback visible | [ ] | Toast/snackbar/banner para confirmacion |
| Undo disponible tras destructive | [ ] | Delete actions ofrecen undo window |
| Long press secondary actions | [ ] | Context menus via long press en mobile |
| Pull-to-refresh standard | [ ] | User expect refresh pattern comun |

## Light/Dark Mode Contrast

| Check | Estado | Detalle |
|-------|--------|---------|
| Text legible ambos modes | [ ] | 4.5:1 min contrast normal text ambos themes |
| Icon colors adapt themes | [ ] | Icons no usan hardcoded color fijo |
| Background surfaces hierarchical | [ ] | Elevation via shades no shadows en mobile |
| Accent colors accessible dark | [ ] | Accent sobre dark bg mantiene ≥ 3:1 ratio |
| Safe areas respected dark/light | [ ] | Padding respects notches/pill/home indicator |
| Color tokens systematized | [ ] | Design tokens centralizados tema completo |
| System theme preference respeta | [ ] | Usa `UserInterfaceStyle` / `ThemeMode.system` |
| Dark mode tested real device | [ ] | Verificar en pantalla real, no solo simulador |

## Layout y Safe Areas

| Check | Estado | Detalle |
|-------|--------|---------|
| SafeArea padding aplicado | [ ] | Top/bottom safe areas respect notches/home bars |
| Content no oculta behind controls | [ ] | Keyboard no cubra inputs, bottom nav accesible |
| Bottom navigation ≤ 5 items | [ ] | Cognitive load limit respectado |
| Status bar contrast theme-matched | [ ] | Bar icon/color cambia segun background below |
| Orientation handles gracefully | [ ] | Portrait/landscape ambos functional usable |
| Modal/drawer dismissible | [ ] | Back gesture, back button, swipe down, escape key |
| Scroll content doesn't overflow | [ ] | Horizontal scroll NO acceptable en mobile apps |
| Viewport meta configured | [ ] | width=device-width, initial-scale=1, user-scalable=yes |

## Accesibilidad Mobile

| Check | Estado | Detalle |
|-------|--------|---------|
| VoiceOver/TalkBack compatible | [ ] | Elements announce correctamente screen readers |
| Dynamic Type supported | [ ] | Font size preferences respected, layouts adapten |
| Reduced motion respected | [ ] | Animaciones complejas opcionales/reducible |
| High contrast mode works | [ ] | Colores funcionan si usuario activ high contrast |
| Gestures have alternatives | [ ] | Pinch/tap/swipe también accessible via buttons |
| Error messages readable | [ ] | Errors annunced screen reader con contexto |

## Performance Mobile

| Check | Estado | Detalle |
|-------|--------|---------|
| Images optimized/loaded lazily | [ ] | WebP/AVIF lazy-load below-fold |
| Bundle size reasonable | [ ] | Tree-shaking, code-splitting implementado |
| Re-renders minimized | [ ] | React.memo, useMemo, useCallback where appropriate |
| Memory no leaks observed | [ ] | Components unmount properly, listeners removed |
| Jank-free animations | [ ] | Solo transform+opacity animated, GPU-accelerated |

## UX Polish Final

| Check | Estado | Detalle |
|-------|--------|---------|
| Spacing consistent (8px grid) | [ ] | Todo spacing multiples de 4/8px system |
| Typography system defined | [ ] | Hierarquia typografica clara, max 2 familias |
| Colors tokenized | [ ] | Hex raw NO hardcodeados en componentes |
| Border-radius intentional | [ ] | Un radius principal, variaciones logicas |
| Animation purposeful | [ ] | Cada animacion tiene purpose claro definido |
| Copy end-user perspective | [ ] | Language user understands, no system terminology |
| Form validation inline | [ ] | Error cerca campo, helper text contextual |
| Navigation predictable | [ ] | Back behavior logical, breadcrumbs deep pages |
| Offline states handled | [ ] | No connectivity → informative message, not crash |
| Share/back intents wired | [ ] | OS-level sharing y back working as expected |

## Post-Delivery Verification

Despues de completar checklist:
1. **Test real device** — Simulador diferente hardware real, especialmente gestures y performance.
2. **Test on multiple sizes** — iPhone SE/Mini/Pro, Android small/large screens.
3. **Test with VoiceOver/TalkBack** — Verify screen reader flow.
4. **Review animation timing** — Play in slow-motion. Adjust until feels right.
5. **Check dynamic type** — Increase font size, verify layout adapts.
6. **Verify dark mode thoroughly** — All screens, all components, all states.
7. **Have non-developer test** — Fresh eyes catch usability issues devs miss.
