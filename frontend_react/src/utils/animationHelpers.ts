/**
 * Animation Helper Utilities
 * Funciones auxiliares para animaciones complejas y cálculos de timing
 */

import { animationConfig } from '../Header/AnimationDefinitions';

/**
 * Genera clase de delay escalonado para animaciones en cascada
 * Útil para listas que cargan progresivamente
 *
 * @param index - Índice del elemento (0-based)
 * @param delayIncrement - Incremento de delay en ms (default: 50ms)
 * @returns String con clase de delay o objeto de estilo
 */
export const getAnimationDelayClass = (
  index: number,
  delayIncrement: number = 50
): string => {
  const delayMs = index * delayIncrement;
  // Retorna clase delay-X de Tailwind (necesita estar configurado en tailwind.config.js)
  // Alternativa: return `delay-${delayMs}`
  return `animation-delay-${delayMs}`;
};

/**
 * Retorna inline style con delay
 * Más confiable que clases Tailwind
 */
export const getAnimationDelayStyle = (
  index: number,
  delayIncrement: number = 50
): React.CSSProperties => {
  const delayMs = index * delayIncrement;
  return {
    animationDelay: `${delayMs}ms`,
  };
};

/**
 * Genera clase de transición con duración flexible
 *
 * @param property - Propiedad CSS (ej: 'transform', 'opacity', 'all')
 * @param duration - Duración en ms o preset ('immediate'|'fast'|'normal'|'slow')
 * @returns Clase Tailwind de transición
 */
export const getTransitionClass = (
  property: string = 'all',
  duration: 'immediate' | 'fast' | 'normal' | 'slow' | number = 'normal'
): string => {
  let durationClass: string;

  if (typeof duration === 'number') {
    // Mapear ms a clase Tailwind más cercana
    if (duration <= 100) durationClass = '100';
    else if (duration <= 150) durationClass = '150';
    else if (duration <= 200) durationClass = '200';
    else if (duration <= 300) durationClass = '300';
    else if (duration <= 500) durationClass = '500';
    else durationClass = '700';
  } else {
    const durationMap = {
      immediate: '100',
      fast: '150',
      normal: '200',
      slow: '300',
    };
    durationClass = durationMap[duration];
  }

  return `transition-${property} duration-${durationClass}`;
};

/**
 * Retorna inline style de transición
 */
export const getTransitionStyle = (
  property: string = 'all',
  duration: 'immediate' | 'fast' | 'normal' | 'slow' | number = 'normal',
  easing: string = animationConfig.cubic.standard
): React.CSSProperties => {
  let durationMs: number;

  if (typeof duration === 'number') {
    durationMs = duration;
  } else {
    durationMs = animationConfig.duration[duration];
  }

  return {
    transition: `${property} ${durationMs}ms ${easing}`,
  };
};

/**
 * Ease out bounce - curva personalizada para animaciones complejas
 * Devuelve valor interpolado (0-1) para usar en custom animations
 *
 * @param progress - Progreso de 0 a 1
 * @returns Valor easeOutBounce (0-1)
 */
export const easeOutBounce = (progress: number): number => {
  const n1 = 7.5625;
  const d1 = 2.75;

  if (progress < 1 / d1) {
    return n1 * progress * progress;
  } else if (progress < 2 / d1) {
    return n1 * (progress -= 1.5 / d1) * progress + 0.75;
  } else if (progress < 2.5 / d1) {
    return n1 * (progress -= 2.25 / d1) * progress + 0.9375;
  } else {
    return n1 * (progress -= 2.625 / d1) * progress + 0.984375;
  }
};

/**
 * Ease out cubic - animación suave de salida
 * Comúnmente usada para transiciones
 *
 * @param progress - Progreso de 0 a 1
 * @returns Valor easeOutCubic (0-1)
 */
export const easeOutCubic = (progress: number): number => {
  const p = progress - 1;
  return p * p * p + 1;
};

/**
 * Ease in out cubic - animación suave entrada y salida
 *
 * @param progress - Progreso de 0 a 1
 * @returns Valor easeInOutCubic (0-1)
 */
export const easeInOutCubic = (progress: number): number => {
  if (progress < 0.5) {
    return 4 * progress * progress * progress;
  } else {
    const p = 2 * progress - 2;
    return 0.5 * p * p * p + 1;
  }
};

/**
 * Genera un objeto de estilo para animaciones con easing personalizado
 *
 * @param keyframeName - Nombre del keyframe (@keyframes name)
 * @param duration - Duración en ms
 * @param easing - Curva de animación (default: standard)
 * @param iterationCount - Número de iteraciones ('infinite' o número)
 * @returns Objeto de estilo React
 */
export const createAnimationStyle = (
  keyframeName: string,
  duration: number = animationConfig.duration.normal,
  easing: string = animationConfig.cubic.standard,
  iterationCount: 'infinite' | number = 1
): React.CSSProperties => {
  return {
    animation: `${keyframeName} ${duration}ms ${easing} ${iterationCount}`,
  };
};

/**
 * Interpolación lineal - útil para animaciones
 *
 * @param start - Valor inicial
 * @param end - Valor final
 * @param progress - Progreso de 0 a 1
 * @returns Valor interpolado
 */
export const lerp = (start: number, end: number, progress: number): number => {
  return start + (end - start) * progress;
};

/**
 * Genera estilos para transformaciones suaves
 *
 * @param scale - Factor de escala (default: 1)
 * @param translateX - Desplazamiento X en px
 * @param translateY - Desplazamiento Y en px
 * @param rotate - Rotación en grados
 * @returns Objeto transform CSS
 */
export const createTransformStyle = (
  scale: number = 1,
  translateX: number = 0,
  translateY: number = 0,
  rotate: number = 0
): React.CSSProperties => {
  const transforms: string[] = [];

  if (scale !== 1) transforms.push(`scale(${scale})`);
  if (translateX !== 0) transforms.push(`translateX(${translateX}px)`);
  if (translateY !== 0) transforms.push(`translateY(${translateY}px)`);
  if (rotate !== 0) transforms.push(`rotate(${rotate}deg)`);

  return {
    transform: transforms.length > 0 ? transforms.join(' ') : undefined,
  };
};

/**
 * Clip path animation helper
 * Útil para reveal animations
 *
 * @param percentage - Porcentaje de revelación (0-100)
 * @returns clip-path value para CSS
 */
export const getClipPathReveal = (percentage: number): string => {
  // Revela de izq a derecha
  const normalized = Math.min(100, Math.max(0, percentage));
  return `polygon(0 0, ${normalized}% 0, ${normalized}% 100%, 0 100%)`;
};

/**
 * Calcula duración óptima para animaciones basada en distancia
 * Útil para smooth scroll animations
 *
 * @param distance - Distancia en px
 * @param baseSpeed - Velocidad base en px/ms (default: 0.5)
 * @returns Duración en ms (clamped entre 100-800ms)
 */
export const calculateAnimationDuration = (
  distance: number,
  baseSpeed: number = 0.5
): number => {
  const duration = Math.abs(distance) / baseSpeed;
  return Math.min(800, Math.max(100, Math.round(duration)));
};

/**
 * Presets de animación comunes para reutilizar
 */
export const animationPresets = {
  // Button ripple effect
  buttonRipple: {
    duration: animationConfig.duration.normal,
    easing: animationConfig.cubic.standard,
  },

  // Hover effects
  hoverScale: (scale: number = 1.02) => getTransitionStyle('transform', 'normal'),

  // Loading spinner
  spinner: {
    duration: 1000,
    easing: 'linear',
  },

  // Pulse (help icon)
  pulse: {
    duration: 2000,
    easing: 'ease-in-out',
    iterationCount: 'infinite',
  },

  // Ping (notification badge)
  ping: {
    duration: 1500,
    easing: animationConfig.cubic.standard,
    iterationCount: 'infinite',
  },

  // Shimmer loader
  shimmer: {
    duration: 1500,
    easing: 'linear',
    iterationCount: 'infinite',
  },
};

export type AnimationPresetKey = keyof typeof animationPresets;
