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

export default {
  GlobalTopBar: require('./GlobalTopBar').GlobalTopBar,
  TenantSwitcher: require('./TenantSwitcher').TenantSwitcher,
  CommandBar: require('./CommandBar').CommandBar,
  StatusAlertsCluster: require('./StatusAlertsCluster').StatusAlertsCluster,
  ContextualSubheader: require('./ContextualSubheader').default,
  BreadcrumbNav: require('./BreadcrumbNav').default,
  FilterPopover: require('./FilterPopover').default,
};
