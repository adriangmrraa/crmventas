/**
 * Header Components - Public API
 * Exportar todos los componentes del Header
 */

export { GlobalTopBar } from './GlobalTopBar';
export { TenantSwitcher } from './TenantSwitcher';
export { CommandBar } from './CommandBar';
export { StatusAlertsCluster } from './StatusAlertsCluster';
export { default as ContextualSubheader } from './ContextualSubheader';
export { default as BreadcrumbNav } from './BreadcrumbNav';
export { default as FilterPopover } from './FilterPopover';

// Animation utilities
export {
  animationConfig,
  getTransitionClass,
  getAnimationStyle,
  animationStyleSheet,
} from './AnimationDefinitions';

export * from './types';
