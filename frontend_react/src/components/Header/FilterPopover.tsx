/**
 * 🎛️ FilterPopover.tsx
 * Componente de filtros consolidados con popover
 * Proporciona UI para checkboxes, selects y multi-selects
 */

import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, X } from 'lucide-react';
import type { FilterPopoverProps } from './types';

const FilterPopover: React.FC<FilterPopoverProps> = ({
  filters = {},
  onFiltersChange,
  filterOptions = [],
  activeFilterCount = 0,
  triggerClassName = '',
  popoverClassName = '',
  onClearFilters,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const [popoverPosition, setPopoverPosition] = useState({ top: 0, left: 0 });

  // Calcular posición del popover
  useEffect(() => {
    if (isOpen && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPopoverPosition({
        top: rect.bottom + 8,
        left: rect.left,
      });
    }
  }, [isOpen]);

  // Cerrar popover al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (!popoverRef.current?.contains(e.target as Node) &&
          !triggerRef.current?.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Manejar cambio en checkbox
  const handleCheckboxChange = (optionId: string, valueId: string) => {
    const newFilters = { ...filters };

    if (!newFilters[optionId]) {
      newFilters[optionId] = { values: [] };
    }

    const idx = newFilters[optionId].values.indexOf(valueId);
    if (idx > -1) {
      newFilters[optionId].values.splice(idx, 1);
    } else {
      newFilters[optionId].values.push(valueId);
    }

    onFiltersChange?.(newFilters);
  };

  // Manejar cambio en select
  const handleSelectChange = (optionId: string, valueId: string) => {
    const newFilters = {
      ...filters,
      [optionId]: { value: valueId },
    };
    onFiltersChange?.(newFilters);
  };

  // Limpiar filtros
  const handleClearFilters = () => {
    onClearFilters?.();
    onFiltersChange?.({});
    setIsOpen(false);
  };

  // Verificar si checkbox está seleccionado
  const isCheckboxChecked = (optionId: string, valueId: string): boolean => {
    return filters[optionId]?.values?.includes(valueId) ?? false;
  };

  // Verificar si select tiene valor
  const getSelectValue = (optionId: string): string | undefined => {
    return filters[optionId]?.value;
  };

  return (
    <>
      {/* Trigger Button */}
      <button
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        className={`
          relative flex items-center gap-2 px-3 py-2 rounded-lg 
          transition-all duration-200 
          ${activeFilterCount > 0
            ? 'bg-blue-500/20 border border-blue-500/50 text-blue-300 hover:bg-blue-500/30'
            : 'bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 hover:text-white'
          }
          active:scale-95 whitespace-nowrap
          ${triggerClassName}
        `}
        aria-label={`Filtros${activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}`}
        aria-expanded={isOpen}
      >
        <span className="text-sm font-medium">Filtros</span>
        
        {/* Counter badge */}
        {activeFilterCount > 0 && (
          <span className="px-2 py-0.5 text-xs font-bold bg-blue-500 text-white rounded-full">
            {activeFilterCount}
          </span>
        )}

        {/* Chevron indicator */}
        <ChevronDown
          size={16}
          className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Popover */}
      {isOpen && (
        <div
          ref={popoverRef}
          style={{
            position: 'fixed',
            top: `${popoverPosition.top}px`,
            left: `${popoverPosition.left}px`,
            zIndex: 1000,
          }}
          className={`
            animate-in fade-in zoom-in-95
            bg-slate-900 border border-white/10 rounded-lg shadow-xl
            w-64 max-h-96 overflow-y-auto
            ${popoverClassName}
          `}
          role="dialog"
          aria-modal="true"
          aria-label="Filtros avanzados"
        >
          {/* Header */}
          <div className="sticky top-0 bg-slate-900/95 border-b border-white/5 px-4 py-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Opciones de Filtro</h3>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-md hover:bg-white/10 transition-colors"
              aria-label="Cerrar"
            >
              <X size={16} className="text-white/60" />
            </button>
          </div>

          {/* Filter Options */}
          <div className="p-4 space-y-4">
            {filterOptions.length === 0 ? (
              <p className="text-sm text-white/50 text-center py-6">
                No hay filtros disponibles
              </p>
            ) : (
              filterOptions.map((option) => (
                <div key={option.id} className="space-y-2">
                  {/* Option Label */}
                  <label className="text-xs font-semibold text-white/80 block">
                    {option.label}
                  </label>

                  {/* Render based on type */}
                  {option.type === 'checkbox' || option.type === 'multi-select' ? (
                    <div className="space-y-2">
                      {option.values?.map((value) => (
                        <label
                          key={value.id}
                          className="flex items-center gap-2 cursor-pointer group"
                        >
                          <input
                            type="checkbox"
                            checked={isCheckboxChecked(option.id, value.id)}
                            onChange={() => handleCheckboxChange(option.id, value.id)}
                            className="w-4 h-4 rounded border border-white/20 bg-white/5 text-blue-500 transition-all"
                          />
                          <span className="text-sm text-white/70 group-hover:text-white transition-colors">
                            {value.label}
                          </span>
                        </label>
                      ))}
                    </div>
                  ) : option.type === 'select' ? (
                    <select
                      value={getSelectValue(option.id) || ''}
                      onChange={(e) => handleSelectChange(option.id, e.target.value)}
                      className="w-full px-3 py-2 rounded border border-white/10 bg-white/5 text-white text-sm focus:outline-none focus:border-blue-500/50 focus:bg-white/10 transition-all"
                    >
                      <option value="">Seleccionar...</option>
                      {option.values?.map((value) => (
                        <option key={value.id} value={value.id}>
                          {value.label}
                        </option>
                      ))}
                    </select>
                  ) : null}
                </div>
              ))
            )}
          </div>

          {/* Footer with Clear button */}
          {activeFilterCount > 0 && (
            <div className="sticky bottom-0 bg-slate-900/95 border-t border-white/5 p-3 flex gap-2">
              <button
                onClick={handleClearFilters}
                className="flex-1 px-3 py-2 rounded-md border border-white/10 text-white/60 hover:text-white hover:bg-white/5 text-sm font-medium transition-all active:scale-95"
              >
                Limpiar Filtros
              </button>
            </div>
          )}
        </div>
      )}

      {/* Overlay backdrop (optional pero recomendado) */}
      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          className="fixed inset-0 z-40"
          aria-hidden="true"
        />
      )}
    </>
  );
};

export default FilterPopover;
