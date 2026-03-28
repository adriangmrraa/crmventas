/**
 * Header Components Type Definitions
 * ────────────────────────────────────────────────────────────────
 * Central type definitions for GlobalTopBar, TenantSwitcher,
 * CommandBar, StatusAlertsCluster, ContextualSubheader, and related
 * components per specs v1.0 (28/03/2026).
 * 
 * See docs/32_header_refactor_specs.md for full specifications.
 * 
 * @version 1.0
 * @author ClinicForge Team
 */

import type { ReactNode } from 'react';

// ════════════════════════════════════════════════════════════════
// TENANT & ORGANIZATION TYPES
// ════════════════════════════════════════════════════════════════

export interface Tenant {
  id: number;
  clinic_name: string;
  logo_url?: string;
}

export interface UserContext {
  id?: number;
  name?: string;
  email?: string;
  role?: 'ceo' | 'professional' | 'secretary' | 'admin';
  avatar_url?: string;
}

// ════════════════════════════════════════════════════════════════
// GLOBAL TOP BAR TYPES
// ════════════════════════════════════════════════════════════════

export interface GlobalTopBarProps {
  currentTenant?: Tenant;
  tenants?: Tenant[];
  onTenantChange?: (tenantId: number) => void;
  isLoading?: boolean;
  /** Callback to open the mobile sidebar drawer */
  onMenuClick?: () => void;
}

// ════════════════════════════════════════════════════════════════
// TENANT SWITCHER TYPES
// ════════════════════════════════════════════════════════════════

export interface TenantSwitcherProps {
  currentTenant?: Tenant;
  tenants?: Tenant[];
  onTenantChange?: (tenantId: number) => void;
  disabled?: boolean;
}

// ════════════════════════════════════════════════════════════════
// COMMAND BAR TYPES
// ════════════════════════════════════════════════════════════════

export interface SearchResultItem {
  id: string | number;
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  type?: 'patient' | 'appointment' | 'lead' | string;
}

export interface CommandBarProps {
  placeholder?: string;
  onSearch?: (query: string) => void;
  onCommandKey?: () => void;
  isLoading?: boolean;
  results?: SearchResultItem[];
}

export interface SearchResult {
  id: string;
  type: 'patient' | 'appointment' | 'lead';
  label: string;
  description?: string;
  path?: string;
}

// ════════════════════════════════════════════════════════════════
// STATUS ALERTS CLUSTER TYPES
// ════════════════════════════════════════════════════════════════

export type ConnectionStatus = 'online' | 'offline' | 'unstable';

export interface StatusAlertsClusterProps {
  hasNewGuide?: boolean;
  notificationCount?: number;
  onHelpClick?: () => void;
  onNotificationClick?: () => void;
  isOnline?: boolean;
  connectionStatus?: ConnectionStatus;
}

// ════════════════════════════════════════════════════════════════
// BREADCRUMB NAV TYPES
// ════════════════════════════════════════════════════════════════

export interface BreadcrumbItem {
  label: string;
  path?: string;
  icon?: ReactNode;
}

export interface BreadcrumbNavProps {
  crumbs?: BreadcrumbItem[];
  className?: string;
  onNavigate?: (path: string) => void;
}

// ════════════════════════════════════════════════════════════════
// FILTER POPOVER TYPES
// ════════════════════════════════════════════════════════════════

export interface FilterOption {
  id: string;
  label: string;
  type?: 'checkbox' | 'select' | 'date-range' | 'multi-select';
  values?: Array<{
    id: string;
    label: string;
    checked?: boolean;
  }>;
}

export interface FilterPopoverProps {
  filters?: Record<string, any>;
  onFiltersChange?: (filters: Record<string, any>) => void;
  filterOptions?: FilterOption[];
  activeFilterCount?: number;
  triggerClassName?: string;
  popoverClassName?: string;
  onClearFilters?: () => void;
}

// ════════════════════════════════════════════════════════════════
// CONTEXTUAL SUBHEADER TYPES
// ════════════════════════════════════════════════════════════════

export interface PrimaryAction {
  label: string;
  icon?: ReactNode;
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
}

export interface ContextualSubheaderProps {
  breadcrumbs?: BreadcrumbItem[];
  filterActive?: boolean;
  filterCount?: number;
  onFilterClick?: () => void;
  primaryAction?: PrimaryAction;
  filterOptions?: FilterOption[];
  onFiltersChange?: (filters: Record<string, any>) => void;
  visible?: boolean;
  className?: string;
}

// ════════════════════════════════════════════════════════════════
// ANIMATION CONFIGURATION TYPES
// ════════════════════════════════════════════════════════════════

export type CubicBezier = 'standard' | 'enter' | 'exit';
export type AnimationDuration = 'immediate' | 'fast' | 'normal' | 'slow';
export type KeyframeAnimation = 'scaleIn' | 'fadeIn' | 'slideIn' | 'pulse' | 'ping' | 'slideInLeft' | 'shimmer';

// ════════════════════════════════════════════════════════════════
// DESIGN TOKEN TYPES
// ════════════════════════════════════════════════════════════════

export interface HeaderColorPalette {
  background: string;
  backgroundGlass: string;
  borderPrimary: string;
  borderHover: string;
  textPrimary: string;
  textSecondary: string;
  textTertiary: string;
  accentPrimary: string;
  accentHover: string;
  success: string;
  warning: string;
  danger: string;
}

// ════════════════════════════════════════════════════════════════
// ADDITIONAL UI COMPONENT TYPES
// ════════════════════════════════════════════════════════════════

export interface ShimmerLoaderProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  count?: number;
  className?: string;
  animated?: boolean;
  variant?: 'text' | 'card' | 'avatar';
}

export interface PulsingBellProps {
  count?: number;
  onClick?: () => void;
  onClickLabel?: string;
  animated?: boolean;
}

// ════════════════════════════════════════════════════════════════
// RE-EXPORTS
// ════════════════════════════════════════════════════════════════

export type { ReactNode };
