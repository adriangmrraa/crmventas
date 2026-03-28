/**
 * 🎬 AnimationDefinitions.ts
 * Centralización de curvas de animación, duraciones y keyframes
 * Basado en Material Design 3 & specs v1.0
 */

export const animationConfig = {
  // Curvas Bézier estándar (cubic-bezier)
  cubic: {
    standard: 'cubic-bezier(0.4, 0, 0.2, 1)', // Material Design standard
    enter: 'cubic-bezier(0, 0, 0.2, 1)', // Accelerating entrance
    exit: 'cubic-bezier(0.4, 0, 1, 1)', // Decelerating exit
  },

  // Duraciones en milisegundos
  duration: {
    immediate: 100, // Instant feedback
    fast: 150, // Micro interactions
    normal: 200, // Standard transition
    slow: 300, // Complex animations
  },

  // Keyframes predefinidos
  keyframes: {
    scaleIn:
      '@keyframes scaleIn { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }',
    fadeIn:
      '@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }',
    slideIn:
      '@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }',
    slideInLeft:
      '@keyframes slideInLeft { from { transform: translateX(-100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }',
    pulse: '@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }',
    ping: '@keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }',
    shimmer:
      '@keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }',
  },
};

/**
 * Helper: Genera clases de transición Tailwind
 * @param property - Propiedad CSS a transicionar (ej: 'all', 'transform', 'opacity')
 * @param duration - Duración predefinida ('immediate' | 'fast' | 'normal' | 'slow')
 * @returns Clase Tailwind de transición
 */
export const getTransitionClass = (
  property: string = 'all',
  duration: 'immediate' | 'fast' | 'normal' | 'slow' = 'normal'
): string => {
  const durationMap = {
    immediate: '100',
    fast: '150',
    normal: '200',
    slow: '300',
  };

  return `transition-${property} duration-${durationMap[duration]}`;
};

/**
 * Helper: Genera estilo de animación inline
 * @param keyframe - Nombre del keyframe
 * @param duration - Duración en ms
 * @param iterationCount - 'infinite' o número
 * @param direction - 'normal', 'reverse', 'alternate'
 * @param timingFunction - Curva Bézier
 */
export const getAnimationStyle = (
  keyframe: keyof typeof animationConfig.keyframes,
  duration: number = animationConfig.duration.normal,
  iterationCount: 'infinite' | number = 1,
  timingFunction: string = animationConfig.cubic.standard,
  direction: 'normal' | 'reverse' | 'alternate' = 'normal'
): React.CSSProperties => ({
  animation: `${keyframe} ${duration}ms ${timingFunction} ${iterationCount === 'infinite' ? 'infinite' : iterationCount} ${direction}`,
});

/**
 * Estilos CSS para inyectar en el documento
 * Use en <style> tag o CSS-in-JS
 */
export const animationStyleSheet = `
  ${animationConfig.keyframes.scaleIn}
  ${animationConfig.keyframes.fadeIn}
  ${animationConfig.keyframes.slideIn}
  ${animationConfig.keyframes.slideInLeft}
  ${animationConfig.keyframes.pulse}
  ${animationConfig.keyframes.ping}
  ${animationConfig.keyframes.shimmer}
`;
