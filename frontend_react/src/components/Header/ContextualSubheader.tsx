/**
 * 📍 ContextualSubheader.tsx
 * Componente adhesivo (sticky) que muestra breadcrumbs, filtros y acción primaria
 * Posición: Bajo GlobalTopBar, sticky top-16, z-30
 */

import React from 'react';
import { Loader } from 'lucide-react';
import { ContextualSubheaderProps, FilterOption } from './types';
import BreadcrumbNav from './BreadcrumbNav';
import FilterPopover from './FilterPopover';
import { getTransitionClass } from './AnimationDefinitions';

const ContextualSubheader: React.FC<ContextualSubheaderProps> = ({
  breadcrumbs,
  filterActive = false,
  filterCount = 0,
  onFilterClick,
  primaryAction,
  filterOptions = [],
  onFiltersChange,
  visible = true,
  className = '',
}) => {
  // No renderizar si no hay contenido o está oculto
  const hasContent = breadcrumbs && breadcrumbs.length > 0;
  const shouldRender = visible && hasContent;

  if (!shouldRender) {
    return null;
  }

  return (
    <div
      className={`
        sticky top-16 z-30
        bg-white/[0.02] border-b border-white/5
        backdrop-blur-md
        transition-opacity duration-200
        ${visible ? 'opacity-100' : 'opacity-0 pointer-events-none'}
        ${className}
      `}
      role="region"
      aria-label="Subheader contextual"
    >
      <div className="flex items-center justify-between px-6 py-3 h-12 gap-4">
        {/* Left: Breadcrumbs */}
        <div className="flex-1 overflow-x-auto scrollbar-hide">
          <BreadcrumbNav crumbs={breadcrumbs} />
        </div>

        {/* Center: Filtros con condición */}
        {filterOptions && filterOptions.length > 0 && (
          <div className="flex-shrink-0">
            <FilterPopover
              filters={{}}
              onFiltersChange={onFiltersChange}
              filterOptions={filterOptions}
              activeFilterCount={filterCount}
              onClearFilters={() => onFiltersChange?.({})}
              triggerClassName="whitespace-nowrap"
            />
          </div>
        )}

        {/* Right: Primary Action Button */}
        {primaryAction && (
          <div className="flex-shrink-0">
            <button
              onClick={primaryAction.onClick}
              disabled={primaryAction.disabled || primaryAction.loading}
              className={`
                px-4 py-2 rounded-lg font-medium text-sm
                flex items-center gap-2
                transition-all duration-200
                ${
                  primaryAction.disabled
                    ? 'opacity-50 cursor-not-allowed'
                    : `
                        bg-gradient-to-br from-blue-600 to-blue-700
                        border border-blue-500/30
                        text-white hover:from-blue-500 hover:to-blue-600
                        hover:border-blue-400/50
                        active:scale-95
                        shadow-lg hover:shadow-xl hover:shadow-blue-500/20
                        hover:translate-y-[-2px]
                      `
                }
              `}
              aria-label={primaryAction.label}
              aria-busy={primaryAction.loading}
            >
              {primaryAction.loading && (
                <Loader size={16} className="animate-spin" aria-hidden="true" />
              )}
              {primaryAction.icon && !primaryAction.loading && (
                <span className="flex items-center">{primaryAction.icon}</span>
              )}
              <span>{primaryAction.label}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContextualSubheader;
