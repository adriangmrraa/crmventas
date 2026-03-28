# SPEC: UI Premium Components — ClinicForge Design System for CRM

**Fecha:** 2026-03-28
**Prioridad:** Alta (Quick Win — UI inmediato)
**Esfuerzo:** Bajo (copiar y adaptar de ClinicForge)
**Confidence:** 95%

---

## 1. Contexto y Objetivos

El CRM VENTAS ya tiene dark theme (index.css, Layout, todos los componentes). Pero le faltan los componentes premium interactivos que hacen que ClinicForge se sienta "alive": GlassCard, OnboardingGuide, animated buttons, tooltips de primera visita.

**Objetivo:** Copiar los 4 componentes premium de ClinicForge y adaptarlos al contexto de ventas.

---

## 2. Componentes a Implementar

### 2.1 GlassCard (Ken Burns hover)
**Source:** `clinicforge/frontend_react/src/components/GlassCard.tsx`
**Target:** `crm/frontend_react/src/components/GlassCard.tsx`

**Adaptaciones:**
- CARD_IMAGES: cambiar de dental a ventas (pipeline, leads, revenue, calls, marketing)
- Mantener: blur(2px), opacity 0.03→0.08, scale 1.015, glow edge, touch 500ms

**Uso en CRM:**
- Dashboard KPI cards (conversaciones IA, turnos, urgencias, revenue)
- Seller performance cards
- Pipeline stage summary cards

### 2.2 OnboardingGuide (3D tilt + swipe)
**Source:** `clinicforge/frontend_react/src/components/OnboardingGuide.tsx`
**Target:** `crm/frontend_react/src/components/OnboardingGuide.tsx`

**Adaptaciones:**
- Reemplazar GUIDES por páginas del CRM: Dashboard, Leads, Clientes, Agenda, Chats, Vendedores, Marketing, Prospecting, Config
- Pasos orientados a ventas (no dental)
- Mantener: 3D tilt, swipe gestures, step dots, modalIn animation

### 2.3 Animated Buttons (wobble + ping)
**Source:** `clinicforge/frontend_react/src/index.css` (guideWobble, guidePing, novaWobble, novaPing)
**Target:** `crm/frontend_react/src/index.css`

**Agregar a index.css:**
- `@keyframes guidePing` + `@keyframes guideWobble` (para botón ?)
- `@keyframes tooltipIn` (para tooltips)
- `.guide-btn .guide-icon` animation rules

**Agregar a Layout.tsx:**
- Botón `?` con HelpCircle + wobble + ping ring
- Integración con OnboardingGuide

### 2.4 Tooltip Sequence (primera visita)
**Source:** `clinicforge/frontend_react/src/components/Layout.tsx` (tooltip logic)
**Target:** `crm/frontend_react/src/components/Layout.tsx`

**Secuencia:**
- 3s: tooltip sobre botón `?` → "Toca para ver la guía de esta página"
- 8s: tooltip desaparece, marcado en sessionStorage

---

## 3. Criterios de Aceptación

```gherkin
Scenario: GlassCard hover en dashboard
  Given estoy en el Dashboard
  When paso el mouse sobre una KPI card
  Then la card se escala 1.015x con spring easing
  And la imagen de fondo hace zoom (Ken Burns 8s)
  And aparece un glow azul en el borde inferior

Scenario: OnboardingGuide swipe
  Given el modal de guía está abierto en el paso 2 de 5
  When deslizo el contenido hacia la izquierda
  Then se muestra el paso 3 con animación cardSlideLeft
  When estoy en el paso 5 y deslizo izquierda
  Then el modal se cierra y se marca como completado

Scenario: Tooltip primera visita
  Given es la primera vez que visito la página
  When pasan 3 segundos
  Then aparece un tooltip sobre el botón ?
  And el tooltip desaparece a los 8 segundos
  And no se muestra de nuevo en la misma sesión
```

---

## 4. Archivos a Crear/Modificar

| Acción | Archivo |
|--------|---------|
| CREAR | `frontend_react/src/components/GlassCard.tsx` |
| CREAR | `frontend_react/src/components/OnboardingGuide.tsx` |
| MODIFICAR | `frontend_react/src/index.css` (agregar keyframes) |
| MODIFICAR | `frontend_react/src/components/Layout.tsx` (agregar botón ? + tooltips) |

---

## 5. Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| GlassCard necesita imágenes | Usar URLs de Unsplash o placeholders gradient |
| OnboardingGuide pasos incorrectos para CRM | Escribir pasos específicos de ventas |
| Conflicto con Layout existente | Non-destructive: solo agregar, no reemplazar |
