/**
 * 🗺️ BreadcrumbNav.tsx
 * Componente de navegación de ruta (breadcrumbs)
 * Renderiza: 🏠 / Agenda / Editar Turno #123
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import type { BreadcrumbNavProps } from './types';

const BreadcrumbNav: React.FC<BreadcrumbNavProps> = ({
  crumbs = [],
  className = '',
  onNavigate,
}) => {
  const navigate = useNavigate();

  const handleNavigate = (path?: string) => {
    if (!path) return;
    onNavigate?.(path);
    navigate(path);
  };

  // No renderizar si no hay crumbs
  if (!crumbs || crumbs.length === 0) {
    return null;
  }

  return (
    <nav
      className={`flex items-center gap-1 text-sm ${className}`}
      aria-label="Breadcrumb"
    >
      {/* Home icon / link */}
      <button
        onClick={() => handleNavigate('/')}
        className="flex items-center justify-center w-8 h-8 rounded-md transition-all duration-200 hover:bg-white/10 active:scale-95 text-white/70 hover:text-white"
        title="Home"
        aria-label="Home"
      >
        <Home size={16} />
      </button>

      {/* Breadcrumb items */}
      {crumbs.map((crumb, index) => {
        const isLast = index === crumbs.length - 1;

        return (
          <React.Fragment key={`${crumb.label}-${index}`}>
            {/* Separator */}
            <div className="flex items-center justify-center text-white/30">
              <ChevronRight size={16} />
            </div>

            {/* Breadcrumb item */}
            {isLast ? (
              // Last item (current page) - not clickable
              <span className="px-2 py-1 text-white/90 font-medium flex items-center gap-1">
                {crumb.icon && <span className="flex items-center">{crumb.icon}</span>}
                {crumb.label}
              </span>
            ) : (
              // Clickable breadcrumb
              <button
                onClick={() => handleNavigate(crumb.path)}
                className="px-2 py-1 rounded-md transition-all duration-150 text-white/60 hover:text-white hover:bg-white/5 active:scale-95 flex items-center gap-1"
                title={crumb.label}
              >
                {crumb.icon && <span className="flex items-center">{crumb.icon}</span>}
                {crumb.label}
              </button>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};

export default BreadcrumbNav;
