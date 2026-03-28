/**
 * ✨ ShimmerLoader.tsx
 * Componente skeleton con shimmer effect (barrido de luz)
 * Animación 1.5s por ciclo
 */

import React from 'react';
import { ShimmerLoaderProps } from '../Header/types';

const ShimmerLoader: React.FC<ShimmerLoaderProps> = ({
  width = '100%',
  height = 20,
  borderRadius = '0.5rem',
  count = 1,
  className = '',
  animated = true,
  variant = 'text',
}) => {
  // Variantes de skeleton predefinidas
  const variantStyles = {
    text: {
      width: '100%',
      height: 16,
      borderRadius: '0.375rem',
    },
    card: {
      width: '100%',
      height: 200,
      borderRadius: '0.75rem',
    },
    avatar: {
      width: 40,
      height: 40,
      borderRadius: '9999px',
    },
  };

  const selectedVariant = variantStyles[variant];
  const finalWidth = width ?? selectedVariant.width;
  const finalHeight = height ?? selectedVariant.height;
  const finalRadius = borderRadius ?? selectedVariant.borderRadius;

  // Inyectar keyframes únicos
  const keyframeId = `shimmer-${Date.now()}`;

  return (
    <>
      {/* Inyectar estilos globales */}
      <style>{`
        @keyframes shimmerAnimation {
          0% {
            background-position: -1000px 0;
          }
          100% {
            background-position: 1000px 0;
          }
        }

        .${keyframeId} {
          background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0.02) 0%,
            rgba(255, 255, 255, 0.08) 50%,
            rgba(255, 255, 255, 0.02) 100%
          );
          background-size: 1000px 100%;
          ${animated ? `animation: shimmerAnimation 1.5s infinite;` : ''}
        }
      `}</style>

      {/* Renderizar skeleton loaders */}
      <div className={`space-y-3 ${className}`}>
        {Array.from({ length: count }).map((_, index) => (
          <div
            key={`shimmer-${index}`}
            className={keyframeId}
            style={{
              width: typeof finalWidth === 'number' ? `${finalWidth}px` : finalWidth,
              height: typeof finalHeight === 'number' ? `${finalHeight}px` : finalHeight,
              borderRadius:
                typeof finalRadius === 'number' ? `${finalRadius}px` : finalRadius,
              minWidth: 0,
            }}
            aria-hidden="true"
            role="status"
          >
            <span className="sr-only">Cargando...</span>
          </div>
        ))}
      </div>
    </>
  );
};

export default ShimmerLoader;
