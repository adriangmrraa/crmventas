/**
 * PulsingBell Component
 * Bell icon con animación de ping en badge rojo
 * GPU Accelerated animations usando transform + opacity
 */

import React, { useMemo } from 'react';
import { Bell } from 'lucide-react';
import type { PulsingBellProps } from '../Header/types';
import { animationConfig } from '../Header/AnimationDefinitions';
import { createAnimationStyle } from '../../utils/animationHelpers';
import '../../../styles/animations.css'; // Asegura que los keyframes estén disponibles

const PulsingBell: React.FC<PulsingBellProps> = ({
  count = 0,
  onClick,
  onClickLabel = 'Notifications',
  animated = true,
}) => {
  // Determinar si mostrar badge
  const showBadge = useMemo(() => count > 0, [count]);

  // Limitar el número mostrado a 99+
  const displayCount = useMemo(() => {
    if (count <= 0) return null;
    if (count > 99) return '99+';
    return count.toString();
  }, [count]);

  // Animación del badge
  const badgeAnimationStyle = useMemo<React.CSSProperties>(() => {
    if (!animated || !showBadge) {
      return { display: 'none' };
    }

    return {
      ...createAnimationStyle(
        'ping',
        animationConfig.duration.slow + 500, // 1500ms = 1.5s
        animationConfig.cubic.standard,
        'infinite'
      ),
      position: 'absolute',
      top: '-4px',
      right: '-4px',
      width: '20px',
      height: '20px',
      backgroundColor: '#dc3545', // Red for notifications
      border: '2px solid #0a0a12',
      borderRadius: '50%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '0.625rem', // 10px
      fontWeight: '700',
      color: 'white',
      whiteSpace: 'nowrap',
      zIndex: 1,
    };
  }, [animated, showBadge]);

  // Estilo contenedor del bell
  const bellContainerStyle: React.CSSProperties = {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '2.5rem',
    height: '2.5rem',
    borderRadius: '0.75rem',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    cursor: onClick ? 'pointer' : 'default',
    transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
    ...getTransitionStyle(),
  };

  // Estilo del icono
  const bellIconStyle: React.CSSProperties = {
    width: '1.25rem',
    height: '1.25rem',
    color: 'rgba(255, 255, 255, 0.7)',
    transition: 'color 200ms cubic-bezier(0.4, 0, 0.2, 1)',
  };

  const getTransitionStyle = (): React.CSSProperties => ({
    transitionProperty: 'background-color, border-color, transform, box-shadow',
    transitionDuration: '200ms',
    transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)',
  });

  return (
    <button
      onClick={onClick}
      aria-label={onClickLabel}
      title={showBadge ? `${count} new notifications` : 'Notifications'}
      className="hover:bg-white/[0.08] hover:border-white/20 active:scale-95"
      style={bellContainerStyle}
      disabled={!onClick}
    >
      {/* Bell Icon */}
      <Bell style={bellIconStyle} strokeWidth={1.5} />

      {/* Notification Badge con Ping Animation */}
      {showBadge && (
        <span style={badgeAnimationStyle} className="notification-badge">
          {displayCount}
        </span>
      )}
    </button>
  );
};

export default PulsingBell;

/**
 * Estilos CSS necesarios que se inyectan en animations.css
 * 
 * @keyframes ping {
 *   75%, 100% {
 *     transform: scale(2);
 *     opacity: 0;
 *   }
 * }
 * 
 * .notification-badge {
 *   animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
 * }
 */
