/**
 * 🏢 TenantSwitcher.tsx
 * Dropdown selector de clínicas disponibles
 *
 * CARACTERÍSTICAS:
 * - Avatar con logo de clínica o iniciales
 * - Nombre de clínica truncado con ellipsis
 * - Chevron rotatable que indica estado abierto/cerrado
 * - Dropdown con animación scale-in (200ms, cubic-bezier(0.4, 0, 0.2, 1))
 * - Active item: highlighted con left border 3px #0066cc
 * - Mobile (sm): Solo muestra avatar sin nombre
 * - Click outside: cierra automáticamente
 *
 * ROLES:
 * - Solo visible si CEO o múltiples tenants disponibles
 */

import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Building2 } from 'lucide-react';
import type { TenantSwitcherProps } from './types';

export const TenantSwitcher: React.FC<TenantSwitcherProps> = ({
  currentTenant,
  tenants = [],
  onTenantChange,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  /**
   * Cerrar dropdown cuando se hace clic fuera del componente
   */
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  /**
   * Manejar apertura/cierre del dropdown con animación suave
   * Animación: 200ms con easing cubic-bezier
   */
  const handleToggle = () => {
    if (isOpen) {
      setIsAnimating(false);
      setTimeout(() => setIsOpen(false), 200);
    } else {
      setIsOpen(true);
      setTimeout(() => setIsAnimating(true), 10);
    }
  };

  /**
   * Manejar cambio de clínica
   */
  const handleTenantSelect = (tenantId: number) => {
    onTenantChange?.(tenantId);
    setIsAnimating(false);
    setTimeout(() => setIsOpen(false), 200);
  };

  /**
   * Obtener iniciales del nombre de la clínica para avatar
   * Ej: "Centro Dental" → "CD"
   */
  const getInitials = (name: string): string => {
    return name
      .split(' ')
      .map((word) => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const displayName = currentTenant?.clinic_name || 'Select Clinic';

  // ============================================
  // RENDER
  // ============================================

  return (
    <div ref={dropdownRef} className="relative">
      {/* ===== DESKTOP: Button visible (con nombre) ===== */}
      <button
        onClick={handleToggle}
        disabled={disabled}
        className="hidden sm:flex items-center gap-3 px-4 py-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        title={displayName}
        aria-label={`Change clinic: ${displayName}`}
        aria-expanded={isOpen}
      >
        {/* Avatar Logo/Initials */}
        <div className="flex items-center justify-center w-8 h-8 rounded-md bg-gradient-to-br from-medical-500 to-medical-700 text-white font-semibold text-sm flex-shrink-0 overflow-hidden">
          {currentTenant?.logo_url ? (
            <img
              src={currentTenant.logo_url}
              alt={currentTenant.clinic_name}
              className="w-full h-full object-cover"
            />
          ) : (
            <span>{getInitials(displayName)}</span>
          )}
        </div>

        {/* Clinic Name (truncated) */}
        <span className="max-w-[150px] truncate text-sm font-medium text-white/90">
          {displayName}
        </span>

        {/* Chevron indicator (rotates when open) */}
        <ChevronDown
          size={16}
          className={`text-white/60 transition-transform duration-200 flex-shrink-0 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* ===== MOBILE: Avatar only ===== */}
      <button
        onClick={handleToggle}
        disabled={disabled}
        className="flex sm:hidden items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        title={displayName}
        aria-label={`Change clinic: ${displayName}`}
        aria-expanded={isOpen}
      >
        <div className="flex items-center justify-center w-6 h-6 rounded-md bg-gradient-to-br from-medical-500 to-medical-700 text-white font-semibold text-xs flex-shrink-0 overflow-hidden">
          {currentTenant?.logo_url ? (
            <img
              src={currentTenant.logo_url}
              alt={currentTenant.clinic_name}
              className="w-full h-full object-cover"
            />
          ) : (
            <span>{getInitials(displayName)}</span>
          )}
        </div>
      </button>

      {/* ===== DROPDOWN MENU ===== */}
      {isOpen && (
        <div
          className={`absolute top-full left-0 mt-2 min-w-[250px] bg-slate-950/95 backdrop-blur-md border border-white/10 rounded-lg shadow-xl overflow-hidden z-50 transition-all duration-200 ${
            isAnimating ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
          }`}
          style={{
            transformOrigin: 'top left',
          }}
          role="menu"
        >
          {/* Header */}
          {tenants.length > 0 && (
            <div className="px-4 py-2 border-b border-white/5 bg-white/[0.02]">
              <p className="text-xs font-semibold text-white/60 uppercase tracking-wide">
                Available Clinics
              </p>
            </div>
          )}

          {/* Clinic List */}
          <div className="max-h-64 overflow-y-auto">
            {tenants.map((tenant) => (
              <button
                key={tenant.id}
                onClick={() => handleTenantSelect(tenant.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors duration-150 border-l-3 ${
                  currentTenant?.id === tenant.id
                    ? 'bg-white/10 border-l-medical-500 text-white'
                    : 'border-l-transparent hover:bg-white/5 text-white/80 hover:text-white'
                }`}
                role="menuitem"
                aria-current={currentTenant?.id === tenant.id ? 'true' : 'false'}
              >
                {/* Mini Avatar */}
                <div className="flex items-center justify-center w-7 h-7 rounded-md bg-gradient-to-br from-medical-500 to-medical-700 text-white font-semibold text-xs flex-shrink-0 overflow-hidden">
                  {tenant.logo_url ? (
                    <img
                      src={tenant.logo_url}
                      alt={tenant.clinic_name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span>{getInitials(tenant.clinic_name)}</span>
                  )}
                </div>

                {/* Clinic Name */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{tenant.clinic_name}</p>
                </div>

                {/* Active indicator dot */}
                {currentTenant?.id === tenant.id && (
                  <div className="w-2 h-2 rounded-full bg-medical-500 flex-shrink-0" />
                )}
              </button>
            ))}
          </div>

          {/* Empty State */}
          {tenants.length === 0 && (
            <div className="px-4 py-8 text-center">
              <Building2 size={32} className="mx-auto mb-2 text-white/20" />
              <p className="text-sm text-white/50">
                No clinics available
              </p>
            </div>
          )}
        </div>
      )}

      {/* ===== KEYFRAME ANIMATION (injected in <style>) ===== */}
      <style>{`
        @keyframes scaleIn {
          from {
            transform: scale(0.95);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

export default TenantSwitcher;
