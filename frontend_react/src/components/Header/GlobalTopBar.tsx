/**
 * ────────────────────────────────────────────────────────────────
 * GlobalTopBar.tsx - Main Header Container
 * ────────────────────────────────────────────────────────────────
 * 
 * SPECS: v1.0 (28/03/2026) - ClinicForge Header Refactor
 * 
 * **PURPOSE**
 * Fixed header bar (64px height) containing the main navigation elements.
 * Located at top of all pages; remains fixed while user scrolls content.
 * 
 * **LAYOUT**
 * ┌─────────────────────────────────────────────────────────────────┐
 * │  Logo | TenantSwitcher    CommandBar (center)    StatusCluster  │
 * │  (16) | (dropdown)     (flexible max-w-500px)      (help, bell)  │
 * └─────────────────────────────────────────────────────────────────┘
 * 
 * **STYLING (Glass Effect - Dark Mode)**
 * - Height: h-16 (64px)
 * - Position: fixed top-0, left-0, right-0
 * - Z-index: z-40 (below modals at z-50, above content)
 * - Background: rgba(0, 0, 0, 0.6) with backdrop-blur(12px)
 * - Border: border-b border-white/5
 * - Spacing: px-6 (24px horiz), gap-8 between sections
 * 
 * **RESPONSIVE**
 * - Desktop (lg+): Full layout, TenantSwitcher shows name + avatar
 * - Tablet (md): Gaps reduce slightly
 * - Mobile (sm): TenantSwitcher avatar only, CommandBar becomes icon
 * 
 * **BROWSER SUPPORT**
 * - Chrome/Edge 90+
 * - Firefox 88+
 * - Safari 14+
 * 
 * @example
 * <GlobalTopBar
 *   currentTenant={{ id: 1, clinic_name: 'Clínica Central' }}
 *   tenants={[...]}
 *   onTenantChange={handleTenantSwitch}
 *   isLoading={false}
 * />
 * 
 * **INTEGRATION**
 * Import in Layout.tsx and wrap before main content:
 * const spacerDiv = <div className="pt-16"></div> // Spacer for fixed header
 * <GlobalTopBar {...props} />
 * <main className="flex-1 overflow-hidden">
 *   {children}
 * </main>
 */

import React, { useMemo } from 'react';
import { useTranslation } from '../../context/LanguageContext';
import { Stethoscope, Menu } from 'lucide-react';
import type { GlobalTopBarProps } from './types';
import { TenantSwitcher } from './TenantSwitcher';
import { CommandBar } from './CommandBar';
import { StatusAlertsCluster } from './StatusAlertsCluster';

/**
 * GlobalTopBar Component
 * 
 * @param currentTenant - Currently active tenant/clinic
 * @param tenants - List of available tenants (shown in switcher dropdown)
 * @param onTenantChange - Callback fired when user switches clinic
 * @param isLoading - Loading state (disables switcher, shows spinners)
 */
export const GlobalTopBar: React.FC<GlobalTopBarProps> = ({
  currentTenant,
  tenants = [],
  onTenantChange,
  isLoading = false,
  onMenuClick,
}) => {
  const { t } = useTranslation();

  /**
   * Determine visibility of TenantSwitcher
   * Show if: tenants.length > 1 (multiple clinics available)
   * 
   * TODO: Future integration with useAuth() for role-based visibility
   * (Show for CEO always, hide for professional/secretary if single clinic)
   */
  const showTenantSwitcher = useMemo(() => {
    return tenants.length > 1;
  }, [tenants]);

  return (
    <>
      {/* ─────────────────────────────────────────────────────────────── */}
      {/* FIXED HEADER BAR (64px, glass effect, dark mode) */}
      {/* ─────────────────────────────────────────────────────────────── */}
      <header
        className="fixed top-0 left-0 right-0 z-40 h-16 bg-black/60 backdrop-blur-md border-b border-white/5"
        style={{
          // Inline styles for IE11 compatibility (if needed)
          background: 'rgba(0, 0, 0, 0.6)',
          backdropFilter: 'blur(12px)',
        }}
        role="banner"
        aria-label={t('header.global_navigation') || 'Global Navigation'}
      >
        {/* FLEX CONTAINER: Three sections (left | center | right) */}
        <div className="flex items-center justify-between px-6 gap-8 h-full">
          {/* ───────────────────────────────────────────────────────────── */}
          {/* LEFT: ClinicForge Logo + TenantSwitcher Dropdown */}
          {/* ───────────────────────────────────────────────────────────── */}
          <div className="flex items-center gap-3 min-w-max">
            {/* Hamburger Menu Button (Mobile only) */}
            {onMenuClick && (
              <button
                onClick={onMenuClick}
                className="lg:hidden flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200"
                aria-label="Open menu"
              >
                <Menu size={20} className="text-white/70" />
              </button>
            )}

            {/* ClinicForge Brand Icon */}
            {/* Size: 32px (w-8 h-8), rounded square, medical gradient */}
            {/* Color: medical-500 (primary brand color) */}
            <div
              className="flex items-center justify-center w-8 h-8 rounded-md bg-medical-500 flex-shrink-0"
              title="ClinicForge"
              aria-label="ClinicForge Logo"
            >
              <Stethoscope size={20} className="text-white" />
            </div>

            {/* TenantSwitcher: Dropdown selector for clinic switching */}
            {/* Visibility: Only if multiple tenants OR user is CEO */}
            {/* Mobile behavior: Avatar only on sm breakpoint */}
            {/* Animation: Scale-in 200ms on open */}
            {showTenantSwitcher && (
              <TenantSwitcher
                currentTenant={currentTenant}
                tenants={tenants}
                onTenantChange={onTenantChange}
                disabled={isLoading}
              />
            )}
          </div>

          {/* ───────────────────────────────────────────────────────────── */}
          {/* CENTER: CommandBar (Omnipresent Search + Cmd+K) */}
          {/* ───────────────────────────────────────────────────────────── */}
          {/* Flexible width container (flex-1), centered */}
          {/* Input with glass effect, icon left, shortcut right */}
          {/* Focus auto-triggers on Cmd+K (Mac) or Ctrl+K (Windows) */}
          {/* Debounce: 300ms before firing onSearch callback */}
          {/* Mobile: Collapses to search icon with modal overlay */}
          <CommandBar
            placeholder={t('header.search_placeholder')}
            isLoading={isLoading}
          />

          {/* ───────────────────────────────────────────────────────────── */}
          {/* RIGHT: StatusAlertsCluster (Help icon + Bell + Status) */}
          {/* ───────────────────────────────────────────────────────────── */}
          {/* Help icon: Pulse animation if new guide available */}
          {/* Bell: Badge with ping animation, shows unread count */}
          {/* Status: Color indicator (green=online, red=offline, yellow=unstable) */}
          <StatusAlertsCluster />
        </div>
      </header>

      {/* ─────────────────────────────────────────────────────────────── */}
      {/* SPACER DIV: Prevents content overlap with fixed header */}
      {/* ─────────────────────────────────────────────────────────────── */}
      {/* Height: pt-16 = 64px (matches header height h-16) */}
      {/* Use this spacer inside Layout.tsx for correct content positioning */}
      <div className="pt-16" />
    </>
  );
};

export default GlobalTopBar;
