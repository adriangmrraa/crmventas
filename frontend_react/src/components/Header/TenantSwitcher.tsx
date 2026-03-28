/**
 * ────────────────────────────────────────────────────────────────
 * TenantSwitcher.tsx - Clinic Selector Dropdown
 * ────────────────────────────────────────────────────────────────
 * 
 * SPECS: v1.0 (28/03/2026) - ClinicForge Header Refactor
 * 
 * **PURPOSE**
 * Dropdown selector for switching between available clinics/tenants.
 * Only shown if: user.role === 'ceo' OR tenants.length > 1
 * 
 * **LAYOUT**
 * Button: Avatar (rounded square, 32px) + Name (truncated) + Chevron
 * Dropdown Menu: Popover below button with animated entrance (200ms)
 * Items: Each clinic with avatar, name, checkmark indicator
 * 
 * **DESKTOP (lg+)**
 * - Button shows: Avatar | Name | Chevron
 * - Width: min-w-[250px] for dropdown
 * 
 * **MOBILE (sm)**
 * - Button shows: Avatar only (hidden: name + chevron)
 * - Width: Adjusted for smaller screen
 * 
 * **ANIMATIONS**
 * - Dropdown open: scale(0.95) → scale(1), opacity 0 → 1, 200ms
 * - Button active: scale(0.96) press effect
 * - Button hover: scale(1.02), background increase
 * - Chevron: Rotates 180° when dropdown open
 * 
 * @example
 * <TenantSwitcher
 *   currentTenant={{ id: 1, clinic_name: 'Clínica A' }}
 *   tenants={[...]}
 *   onTenantChange={(id) => handleSwitch(id)}
 *   disabled={false}
 * />
 */

import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from '../../context/LanguageContext';
import { ChevronDown, Building2 } from 'lucide-react';
import type { TenantSwitcherProps } from './types';

export const TenantSwitcher: React.FC<TenantSwitcherProps> = ({
  currentTenant,
  tenants = [],
  onTenantChange,
  disabled = false,
}) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  /**
   * CLICK OUTSIDE HANDLER
   * Close dropdown when user clicks anywhere outside the component
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
   * SMOOTH ANIMATION ON TOGGLE
   * - Opening: Set isOpen=true immediately, then animate in 10ms
   * - Closing: Animate out first (200ms), then set isOpen=false
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
   * TENANT SELECTION HANDLER
   * Called when user clicks a clinic in dropdown
   */
  const handleTenantSelect = (tenantId: number) => {
    onTenantChange?.(tenantId);
    setIsAnimating(false);
    setTimeout(() => setIsOpen(false), 200);
  };

  /**
   * UTILITY: Calculate clinic initials for avatar
   */
  const getInitials = (name: string): string => {
    return name
      .split(' ')
      .map((word) => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const displayName = currentTenant?.clinic_name || t('header.tenant_selector', 'Select Clinic');

  return (
    <div ref={dropdownRef} className="relative">
      {/* ─────────────────────────────────────────────────────── */}
      {/* DESKTOP: Button visible (avatar + name + chevron) */}
      {/* ─────────────────────────────────────────────────────── */}
      <button
        onClick={handleToggle}
        disabled={disabled}
        className="hidden sm:flex items-center gap-3 px-4 py-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        title={displayName}
        aria-label={`${t('header.change_clinic', 'Change clinic')}: ${displayName}`}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
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

      {/* ─────────────────────────────────────────────────────── */}
      {/* MOBILE: Avatar only (sm breakpoint) */}
      {/* ─────────────────────────────────────────────────────── */}
      <button
        onClick={handleToggle}
        disabled={disabled}
        className="flex sm:hidden items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        title={displayName}
        aria-label={`${t('header.change_clinic', 'Change clinic')}: ${displayName}`}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
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

      {/* ─────────────────────────────────────────────────────── */}
      {/* DROPDOWN MENU: Popover with clinic list */}
      {/* ─────────────────────────────────────────────────────── */}
      {isOpen && (
        <div
          className={`absolute top-full left-0 mt-2 min-w-[250px] bg-slate-950/95 backdrop-blur-md border border-white/10 rounded-lg shadow-xl overflow-hidden z-50 transition-all duration-200 ${
            isAnimating ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
          }`}
          style={{
            transformOrigin: 'top left',
          }}
          role="listbox"
        >
          {/* Header: "Available Clinics" label */}
          {tenants.length > 0 && (
            <div className="px-4 py-2 border-b border-white/5 bg-white/[0.02]">
              <p className="text-xs font-semibold text-white/60 uppercase tracking-wide">
                {t('header.tenant_selector')}
              </p>
            </div>
          )}

          {/* Clinic List: Scrollable container (max-h-64) */}
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
                role="option"
                aria-selected={currentTenant?.id === tenant.id}
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

          {/* Empty State: When no clinics available */}
          {tenants.length === 0 && (
            <div className="px-4 py-8 text-center">
              <Building2 size={32} className="mx-auto mb-2 text-white/20" />
              <p className="text-sm text-white/50">
                {t('header.no_clinics', 'No clinics available')}
              </p>
            </div>
          )}
        </div>
      )}

      {/* CSS Keyframe Animation */}
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
