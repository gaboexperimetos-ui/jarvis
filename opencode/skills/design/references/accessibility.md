---
name: accessibility
source: vercel web-design-guidelines + impeccable
description: WCAG audit rules summary for UI code review. Live fetches from Vercel source; local summary here for quick reference.
---

# Guia de Accesibilidad — WCAG Audit Rules Resumen Local

## Reglas Criticas (Prioridad 1)

### ARIA y Semantic HTML
- **Label inputs correctamente** → `<label>` asociado al input via `for/id` o wrapping. Labels must be visible siempre, no solo placeholder.
- **Icon-only buttons tienen aria-label** → Screen reader necesita contexto textual. No button con solo icon sin label = invisible para assistive tech.
- **Decorative images tienen alt=""** → Imagenes decorative NO necesitan descripcion. Alt vacio permite screen reader skip. Solo imagenes informativas necesitan alt descriptivo.
- **Use role apropiados** → Custom components necesitan roles explicitos (`role="dialog"`, `role="tablist"`) cuando elements semanticas no aplican.
- **ARIA live regions para updates** → Dynamic content changes anunciadas via `aria-live="polite"` o `"assertive"`. Status messages, form validation, notifications deben announce.

### Focus Management
- **Focus rings visibles siempre** → Outline/focus-ring NEVER REMOVED por "clean look". Visual indicator que element focusable tiene.
- **Tab order logical** → Keyboard navigation flow corresponde visual layout. Skip links para contenido principal bypassing repetitive nav.
- **Focus visible en interactive elements** → Links, buttons, inputs, custom widgets focusable via keyboard muestran indicator claro.
- **Modal dialog trapping** → Tab focus trapped inside modal mientras open. Escape closes modal. Focus return al trigger elemento tras cerrar.

### Color y Contrast
- **Text contrast ≥ 4.5:1 ratio** → Texto normal contra background. Large text (≥ 18px bold / ≥ 24px normal) puede usar ≥ 3:1.
- **NO convey informacion solo con color** → Links diferenciados por underline, no solo color. Chart series diferenciados por patterns + colors. Error states combinan icon + texto + color.
- **Error messages near field affected** → Validation inline/cerca campo invalido, no solo top-banner.

### Touch e Interaccion
- **Touch targets ≥ 44x44px min** → Espacio clickeable real minimo. Control app specificaciones Apple HIG / Material Design coinciden aqui.
- **No hover-only interaction** → En mobile, touch debe activar misma funcionalidad hover desktop ofrece. Menus dropdowns accessible via tap.

### Motion
- **Respet prefers-reduced-motion** → Usuarios motion-sensitive pueden experimentar nausea/disorientation. Provide reduced animation option.
- **Animaciones functional son ok en reduced mode** → Opacity transitions indicando state change OK mantener. Remove movement/position animations solo.

```css
@media (prefers-reduced-motion: reduce) {
  .element {
    /* No transform-based motion */
    animation: fade 0.2s ease; /* opacity/color solo */
  }
}
```

## Reglas Importantes (Prioridades 2-5)

### Headings y Structure
- **Jerarquia semantica heading H1→H6** → Solo un H1 por pagina (typicamente pag title). Hierarquia logica sin saltos H2→H4.
- **Skip navigation link** → Permiten keyboard users bypass repeat content nav → main content.
- **Landmark regions** → `<nav>`, `<main>`, `<header>`, `<footer>`, `<aside>` identifican areas pagina para screen reader navigation.

### Forms
- **Labels visibles permanentemente** → Placeholder complementa label nunca reemplaza. Placeholder disappears typing; label stays.
- **Helper text donde necesario** → Password requirements, phone format examples, contextual help disponible antes/during input.
- **Error messages claros y proximos al campo** → No errores solo arriba formulario. Cada invalid field tiene indication specific.
- **Progressive disclosure** → Mostrar info segun necesidad. overwhelming upfront complexity.

### Links y CTAs
- **Link text meaningful** → "Read more" ≠ good link text. "Read about our privacy policy" = bueno. Link text self-explanatory standalone.
- **Buttons especifican action** → "Save changes" mejor que "Submit". CTA dice exactamente que pasa usado.

### Performance (accesibilidad indirecta)
- **Images con WebP/AVIF** → Faster load = usable sooner. CLS < 0.1 pre-content shift disorientation.
- **Lazy loading below-fold** → Reduce initial payload, improve Time to Interactive.

## Auditoria Practica

Al revisar UI code para accesibilidad:

1. **Fetch reglas actualizadas:** `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`
2. **Apply rules** a cada componente/pagina revisando.
3. **Output findings formato `file:line`** posicion exacta problema.

### Checklist Rapido Entrega

| Check | Como verificar |
|-------|---------------|
| Focus rings visibles | Navegar tab keyboard, verificar outline presente |
| Alt text imagenes | Inspect srcset alt attributes imagenes |
| Labels inputs | Verificar label for/id association |
| Colors accesibles | Contrast checker herramienta color pairs |
| Heading hierarchy | Outline view DevTools jerarquia headings |
| Keyboard navigable | Tab through entire page interactividad completa |
| Reduced motion respected | @media query present animaciones reducen |
| ARIA labels icons | Icon-only elements tienen aria-label descriptive |
| Form error handling | Test form invalid submission, verificar feedback claro |
| Semantic structure | HTML semantic tags usan correctamente |
