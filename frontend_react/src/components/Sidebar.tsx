import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Calendar,
  Users,
  MessageSquare,
  Settings,
  ChevronLeft,
  ChevronRight,
  Stethoscope,
  Home,
  ShieldCheck,
  LogOut,
  User,
  X,
  Search,
  Megaphone,
  Layout
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle, onCloseMobile }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { t } = useTranslation();

  // Single-niche: solo CRM Ventas (no sales)
  const menuItems = [
    { id: 'dashboard', labelKey: 'nav.dashboard' as const, icon: <Home size={20} />, path: '/', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'] },
    { id: 'leads', labelKey: 'nav.leads' as const, icon: <Users size={20} />, path: '/crm/leads', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'] },
    { id: 'meta_leads', labelKey: 'nav.meta_leads' as const, icon: <Megaphone size={20} />, path: '/crm/meta-leads', roles: ['ceo', 'setter', 'closer', 'secretary'] },
    { id: 'clients', labelKey: 'nav.clients' as const, icon: <Users size={20} />, path: '/crm/clientes', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'] },
    { id: 'crm_agenda', labelKey: 'nav.agenda' as const, icon: <Calendar size={20} />, path: '/crm/agenda', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'] },
    { id: 'prospecting', labelKey: 'nav.prospecting' as const, icon: <Search size={20} />, path: '/crm/prospeccion', roles: ['ceo', 'setter', 'closer'] },
    { id: 'chats', labelKey: 'nav.chats' as const, icon: <MessageSquare size={20} />, path: '/chats', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'] },
    // Marketing Items
    { id: 'marketing', labelKey: 'nav.marketing' as const, icon: <Megaphone size={20} />, path: '/crm/marketing', roles: ['ceo', 'admin', 'marketing'] },
    { id: 'hsm_automation', labelKey: 'nav.hsm_automation' as const, icon: <Layout size={20} />, path: '/crm/hsm', roles: ['ceo', 'admin', 'setter', 'closer'] },
    // Admin Items
    { id: 'sellers', labelKey: 'nav.sellers' as const, icon: <ShieldCheck size={20} />, path: '/crm/vendedores', roles: ['ceo'] },
    { id: 'tenants', labelKey: 'nav.companies' as const, icon: <ShieldCheck size={20} />, path: '/empresas', roles: ['ceo'] },
    { id: 'profile', labelKey: 'nav.profile' as const, icon: <User size={20} />, path: '/perfil', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'] },
    { id: 'settings', labelKey: 'nav.settings' as const, icon: <Settings size={20} />, path: '/configuracion', roles: ['ceo'] },
  ];

  const filteredItems = menuItems.filter(item =>
    user && item.roles.includes(user.role)
  );

  const isActive = (path: string) => {
    if (path === '/' && location.pathname !== '/') return false;
    if (path === '/crm/leads') return location.pathname === path || location.pathname.startsWith('/crm/leads/');
    if (path === '/crm/vendedores') return location.pathname === path;
    if (path === '/crm/clientes') return location.pathname === path || location.pathname.startsWith('/crm/clientes/');
    if (path === '/crm/agenda') return location.pathname === path;
    if (path === '/crm/prospeccion') return location.pathname === path;
    if (path === '/crm/marketing') return location.pathname === path;
    if (path === '/crm/hsm') return location.pathname === path;
    return location.pathname === path;
  };

  return (
    <aside className="h-full bg-medical-900 text-white flex flex-col relative shadow-xl overflow-hidden">
      {/* Logo Area */}
      <div className={`h-16 flex items-center ${collapsed && !onCloseMobile ? 'justify-center' : 'px-6'} border-b border-medical-800 shrink-0`}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0">
            <Stethoscope size={18} className="text-white" />
          </div>
          {(!collapsed || onCloseMobile) && (
            <span className="font-semibold text-lg truncate whitespace-nowrap">
              {t('nav.app_name_crm')}
            </span>
          )}
        </div>

        {/* Mobile Close Button - Visible only in drawer mode */}
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="lg:hidden p-2 ml-auto text-gray-400 hover:text-white transition-colors"
            aria-label={t('nav.close_menu')}
          >
            <X size={24} />
          </button>
        )}
      </div>

      {/* Toggle Button (Desktop only) */}
      {!onCloseMobile && (
        <button
          onClick={onToggle}
          className="hidden lg:flex absolute -right-3 top-20 w-6 h-6 bg-white rounded-full shadow-lg items-center justify-center text-medical-900 hover:bg-gray-100 transition-all z-20"
          aria-label={collapsed ? t('nav.expand') : t('nav.collapse')}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      )}

      {/* Navigation */}
      <nav className={`flex-1 py-4 overflow-y-auto overflow-x-hidden ${collapsed && !onCloseMobile ? 'px-2' : 'px-3'}`}>
        {filteredItems.map((item) => {
          const labelKey = item.labelKey;
          return (
            <button
              key={item.id}
              onClick={() => {
                navigate(item.path);
                onCloseMobile?.();
              }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 mb-1 group ${isActive(item.path)
                ? 'bg-white/10 text-white'
                : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`}
              title={collapsed && !onCloseMobile ? t(labelKey) : undefined}
            >
              <span className="flex-shrink-0 group-hover:scale-110 transition-transform">{item.icon}</span>
              {(!collapsed || onCloseMobile) && <span className="font-medium text-sm truncate">{t(labelKey)}</span>}
            </button>
          );
        })}

        <button
          onClick={logout}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 mt-4 text-red-400 hover:bg-red-500/10 group`}
          title={collapsed && !onCloseMobile ? t('nav.logout') : undefined}
        >
          <LogOut size={20} className="group-hover:rotate-12 transition-transform" />
          {(!collapsed || onCloseMobile) && <span className="font-medium text-sm">{t('nav.logout')}</span>}
        </button>
      </nav>

      {/* Footer Info */}
      {(!collapsed || onCloseMobile) && (
        <div className="p-4 border-t border-medical-800 bg-medical-900/50 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-medical-600 flex items-center justify-center text-xs font-medium uppercase shrink-0">
              {user?.email?.[0] || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate text-white">{user?.email}</p>
              <p className="text-[10px] text-gray-400 truncate uppercase tracking-wider font-semibold">{user?.role}</p>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};

export default Sidebar;
