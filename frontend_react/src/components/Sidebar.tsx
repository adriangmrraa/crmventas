import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  Calendar,
  ClipboardList,
  Users,
  MessageSquare,
  Settings,
  Link2,
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
  Layout,
  LayoutGrid,
  BarChart3,
  Clock,
  Eye
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';

/* ── Unsplash thumbnails per menu section ── */
const SIDEBAR_IMAGES: Record<string, string> = {
  dashboard:      'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&q=60',
  leads:          'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&q=60',
  pipeline:       'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&q=60',
  meta_leads:     'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=400&q=60',
  clients:        'https://images.unsplash.com/photo-1521791136064-7986c2920216?w=400&q=60',
  crm_agenda:     'https://images.unsplash.com/photo-1506784983877-45594efa4cbe?w=400&q=60',
  chats:          'https://images.unsplash.com/photo-1577563908411-5077b6dc7624?w=400&q=60',
  prospecting:    'https://images.unsplash.com/photo-1553877522-43269d4ea984?w=400&q=60',
  follow_ups:     'https://images.unsplash.com/photo-1434626881859-194d67b2b86f?w=400&q=60',
  team_activity:  'https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=400&q=60',
  audit_log:      'https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&q=60',
  analytics:      'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&q=60',
  marketing:      'https://images.unsplash.com/photo-1533750349088-cd871a92f312?w=400&q=60',
  hsm_automation: 'https://images.unsplash.com/photo-1586281380349-632531db7ed4?w=400&q=60',
  sellers:        'https://images.unsplash.com/photo-1556745757-8d76bdb6984b?w=400&q=60',
  tenants:        'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=400&q=60',
  profile:        'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&q=60',
  integrations:   'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400&q=60',
  settings:       'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=400&q=60',
  supervisor:     'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=400&q=60',
};

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

  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [touchedId, setTouchedId] = useState<string | null>(null);
  const [tooltipId, setTooltipId] = useState<string | null>(null);
  const tooltipTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ── Preload all sidebar images ── */
  useEffect(() => {
    Object.values(SIDEBAR_IMAGES).forEach(src => {
      const img = new Image();
      img.src = src;
    });
  }, []);

  const isHovered = (id: string) => hoveredId === id || touchedId === id;

  const handleMouseEnter = (id: string) => {
    setHoveredId(id);
    tooltipTimer.current = setTimeout(() => setTooltipId(id), 600);
  };

  const handleMouseLeave = () => {
    setHoveredId(null);
    setTooltipId(null);
    if (tooltipTimer.current) {
      clearTimeout(tooltipTimer.current);
      tooltipTimer.current = null;
    }
  };

  const handleTouchStart = (id: string) => {
    setTouchedId(id);
    tooltipTimer.current = setTimeout(() => setTooltipId(id), 500);
  };

  const handleTouchEnd = () => {
    setTimeout(() => setTouchedId(null), 300);
    setTooltipId(null);
    if (tooltipTimer.current) {
      clearTimeout(tooltipTimer.current);
      tooltipTimer.current = null;
    }
  };

  const menuItems = [
    { id: 'dashboard', labelKey: 'nav.dashboard' as const, icon: <Home size={17} />, path: '/', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'], hint: 'Metricas clave de ventas, leads y conversion en tiempo real' },
    { id: 'leads', labelKey: 'nav.leads' as const, icon: <Users size={17} />, path: '/crm/leads', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'], hint: 'Todos los leads con estado, origen y seguimiento' },
    { id: 'pipeline', labelKey: 'nav.pipeline' as const, icon: <LayoutGrid size={17} />, path: '/crm/pipeline', roles: ['ceo', 'setter', 'closer'], hint: 'Kanban visual de oportunidades por etapa de venta' },
    { id: 'meta_leads', labelKey: 'nav.meta_leads' as const, icon: <Megaphone size={17} />, path: '/crm/meta-leads', roles: ['ceo', 'setter', 'closer', 'secretary'], hint: 'Leads entrantes desde formularios de Meta Ads' },
    { id: 'clients', labelKey: 'nav.clients' as const, icon: <Users size={17} />, path: '/crm/clientes', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'], hint: 'Base de clientes convertidos con historial de compras' },
    { id: 'crm_agenda', labelKey: 'nav.agenda' as const, icon: <Calendar size={17} />, path: '/crm/agenda', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'], hint: 'Agenda de llamadas, demos y reuniones del equipo' },
    { id: 'prospecting', labelKey: 'nav.prospecting' as const, icon: <Search size={17} />, path: '/crm/prospeccion', roles: ['ceo', 'setter', 'closer'], hint: 'Busqueda activa de prospectos y enriquecimiento de datos' },
    { id: 'follow_ups', labelKey: 'nav.follow_ups' as const, icon: <Clock size={17} />, path: '/crm/seguimientos', roles: ['ceo', 'setter', 'closer'], hint: 'Cola de seguimientos pendientes ordenados por prioridad' },
    { id: 'chats', labelKey: 'nav.chats' as const, icon: <MessageSquare size={17} />, path: '/chats', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'], hint: 'Conversaciones de WhatsApp e Instagram en un solo lugar' },
    { id: 'team_activity', labelKey: 'nav.team_activity' as const, icon: <Activity size={17} />, path: '/crm/actividad-equipo', roles: ['ceo'], hint: 'Feed en vivo de lo que hace cada vendedor ahora mismo' },
    { id: 'audit_log', labelKey: 'nav.audit_log' as const, icon: <ClipboardList size={17} />, path: '/crm/auditoria', roles: ['ceo'], hint: 'Historial completo de acciones por lead y vendedor' },
    { id: 'analytics', labelKey: 'nav.analytics' as const, icon: <BarChart3 size={17} />, path: '/crm/analytics', roles: ['ceo'], hint: 'Rendimiento por vendedor, canal y campana' },
    { id: 'marketing', labelKey: 'nav.marketing' as const, icon: <Megaphone size={17} />, path: '/crm/marketing', roles: ['ceo', 'admin', 'marketing'], hint: 'ROI de campanas publicitarias con atribucion de leads' },
    { id: 'hsm_automation', labelKey: 'nav.hsm_automation' as const, icon: <Layout size={17} />, path: '/crm/hsm', roles: ['ceo', 'admin', 'setter', 'closer'], hint: 'Plantillas HSM y secuencias de automatizacion' },
    { id: 'forms', labelKey: 'nav.forms' as const, icon: <Layout size={17} />, path: '/crm/formularios', roles: ['ceo', 'secretary'], hint: 'Formularios publicos de captura de leads' },
    { id: 'internal_chat', labelKey: 'nav.internal_chat' as const, icon: <MessageSquare size={17} />, path: '/crm/chat-interno', roles: ['ceo', 'setter', 'closer', 'secretary', 'professional'], hint: 'Chat interno del equipo: canales y mensajes directos' },
    { id: 'checkin', labelKey: 'nav.checkin' as const, icon: <Clock size={17} />, path: '/crm/checkin', roles: ['ceo', 'setter', 'closer', 'professional'], hint: 'Check-in diario: registra tu jornada y objetivos' },
    { id: 'mis_notas', labelKey: 'nav.mis_notas' as const, icon: <ClipboardList size={17} />, path: '/mis-notas', roles: ['ceo', 'setter', 'closer', 'professional', 'secretary'], hint: 'Tareas asignadas, notas del admin y tareas personales' },
    { id: 'manuales', labelKey: 'nav.manuales' as const, icon: <Home size={17} />, path: '/crm/manuales', roles: ['ceo', 'setter', 'closer', 'professional', 'secretary'], hint: 'Base de conocimiento: guiones, objeciones y procesos' },
    { id: 'plantillas', labelKey: 'nav.plantillas' as const, icon: <Layout size={17} />, path: '/crm/plantillas', roles: ['ceo', 'setter', 'closer'], hint: 'Plantillas de mensajes reutilizables con variables' },
    { id: 'sellers', labelKey: 'nav.sellers' as const, icon: <ShieldCheck size={17} />, path: '/crm/vendedores', roles: ['ceo'], hint: 'Equipo de ventas: setters, closers y asignacion de leads' },
    { id: 'supervisor', labelKey: 'nav.supervisor' as const, icon: <Eye size={17} />, path: '/crm/supervisor', roles: ['ceo'], hint: 'Monitoreo en tiempo real de conversaciones y alertas de IA' },
    { id: 'tenants', labelKey: 'nav.companies' as const, icon: <ShieldCheck size={17} />, path: '/empresas', roles: ['ceo'], hint: 'Empresas y organizaciones registradas en la plataforma' },
    { id: 'profile', labelKey: 'nav.profile' as const, icon: <User size={17} />, path: '/perfil', roles: ['ceo', 'professional', 'secretary', 'setter', 'closer'], hint: 'Tu perfil, cuenta y preferencias personales' },
    { id: 'integrations', labelKey: 'nav.integrations' as const, icon: <Link2 size={17} />, path: '/crm/integraciones', roles: ['ceo'], hint: 'WhatsApp, Instagram y Facebook: canales de mensajeria' },
    { id: 'settings', labelKey: 'nav.settings' as const, icon: <Settings size={17} />, path: '/configuracion', roles: ['ceo'], hint: 'Configuracion general, integraciones y credenciales' },
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
    if (path === '/crm/seguimientos') return location.pathname === path;
    if (path === '/crm/marketing') return location.pathname === path;
    if (path === '/crm/hsm') return location.pathname === path;
    if (path === '/crm/chat-interno') return location.pathname === path;
    if (path === '/crm/plantillas') return location.pathname === path;
    if (path === '/crm/integraciones') return location.pathname === path;
    if (path === '/crm/actividad-equipo') return location.pathname === path;
    if (path === '/crm/auditoria') return location.pathname === path;
    if (path === '/crm/supervisor') return location.pathname === path;
    return location.pathname === path;
  };

  const isCollapsedDesktop = collapsed && !onCloseMobile;

  return (
    <aside className="h-full bg-[#0a0e1a] text-white flex flex-col relative shadow-2xl overflow-hidden">
      {/* Logo Area */}
      <div className={`h-16 flex items-center ${isCollapsedDesktop ? 'justify-center' : 'px-6'} border-b border-white/[0.06] shrink-0`}>
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

        {/* Mobile Close Button */}
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="lg:hidden p-2 ml-auto text-white/40 hover:text-white transition-colors"
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
          className="hidden lg:flex absolute -right-3 top-20 w-6 h-6 bg-white/90 text-[#0a0e1a] rounded-full shadow-lg items-center justify-center hover:bg-white transition-all z-20"
          aria-label={collapsed ? t('nav.expand') : t('nav.collapse')}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      )}

      {/* Navigation */}
      <nav className={`flex-1 py-4 overflow-y-auto overflow-x-hidden ${isCollapsedDesktop ? 'px-2' : 'px-3'}`}>
        {filteredItems.map((item) => {
          const active = isActive(item.path);
          const hovered = isHovered(item.id);
          const showImage = active || hovered;
          const showTooltip = tooltipId === item.id;

          return (
            <div key={item.id} className="relative mb-1">
              <button
                onClick={() => {
                  navigate(item.path);
                  onCloseMobile?.();
                }}
                onMouseEnter={() => handleMouseEnter(item.id)}
                onMouseLeave={handleMouseLeave}
                onTouchStart={() => handleTouchStart(item.id)}
                onTouchEnd={handleTouchEnd}
                className={`
                  w-full relative overflow-hidden rounded-xl
                  ${isCollapsedDesktop ? 'h-10 justify-center px-0' : 'h-11 px-3'}
                  flex items-center gap-3 transition-all duration-200
                  ${active
                    ? 'ring-1 ring-white/[0.12] shadow-lg shadow-white/[0.03]'
                    : hovered
                      ? 'ring-1 ring-white/[0.06]'
                      : ''
                  }
                `}
                style={{
                  transform: hovered ? 'scale(1.03)' : 'scale(1)',
                  transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
                }}
              >
                {/* Background image layer */}
                <div
                  className="absolute inset-0 bg-cover bg-center pointer-events-none"
                  style={{
                    backgroundImage: SIDEBAR_IMAGES[item.id] ? `url(${SIDEBAR_IMAGES[item.id]})` : undefined,
                    filter: 'blur(1px)',
                    opacity: showImage ? 0.12 : 0,
                    transition: 'opacity 500ms ease-out',
                  }}
                />

                {/* Dark overlay */}
                <div
                  className={`absolute inset-0 pointer-events-none transition-all duration-500 ${
                    active ? 'bg-white/[0.08]' : hovered ? 'bg-white/[0.04]' : 'bg-transparent'
                  }`}
                />

                {/* Gradient edge on hover/active */}
                {showImage && (
                  <div className="absolute inset-0 bg-gradient-to-r from-violet-500/[0.06] to-transparent pointer-events-none" />
                )}

                {/* Active indicator bar */}
                {active && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-[#8F3DFF] rounded-r-full glow-violet-sm" />
                )}

                {/* Content */}
                <span className={`flex-shrink-0 relative z-10 ${active ? 'text-white' : hovered ? 'text-white' : 'text-white/40'}`}>
                  {item.icon}
                </span>
                {(!collapsed || onCloseMobile) && (
                  <span className={`font-medium text-[13px] truncate relative z-10 ${active ? 'text-white' : hovered ? 'text-white' : 'text-white/40'}`}>
                    {t(item.labelKey)}
                  </span>
                )}
              </button>

              {/* Tooltip */}
              {showTooltip && item.hint && (
                <div
                  className="absolute left-full top-0 ml-3 z-50 w-56 bg-[#0d1117] border border-white/[0.08] shadow-2xl rounded-xl px-3.5 py-2.5 pointer-events-none"
                  style={{
                    animation: 'sidebar-tooltip-in 0.15s ease-out forwards',
                  }}
                >
                  {/* Arrow */}
                  <div
                    className="absolute top-3.5 -left-[5px] w-0 h-0"
                    style={{
                      borderTop: '5px solid transparent',
                      borderBottom: '5px solid transparent',
                      borderRight: '5px solid rgba(255,255,255,0.08)',
                    }}
                  />
                  <p className="text-[11px] font-semibold text-white/80">{t(item.labelKey)}</p>
                  <p className="text-[10px] text-white/40 leading-relaxed mt-0.5">{item.hint}</p>
                </div>
              )}
            </div>
          );
        })}

        {/* Logout button */}
        <div className="relative mt-4">
          <button
            onClick={logout}
            onMouseEnter={() => setHoveredId('logout')}
            onMouseLeave={() => setHoveredId(null)}
            className={`
              w-full relative overflow-hidden rounded-xl
              ${isCollapsedDesktop ? 'h-10 justify-center px-0' : 'h-11 px-3'}
              flex items-center gap-3 transition-all duration-200 group
            `}
            style={{
              transform: isHovered('logout') ? 'scale(1.03)' : 'scale(1)',
              transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
            }}
            title={isCollapsedDesktop ? t('nav.logout') : undefined}
          >
            {/* Logout hover overlay */}
            <div
              className={`absolute inset-0 pointer-events-none transition-all duration-300 rounded-xl ${
                isHovered('logout') ? 'bg-red-500/[0.08]' : 'bg-transparent'
              }`}
            />

            <LogOut
              size={17}
              className={`flex-shrink-0 relative z-10 group-hover:rotate-12 transition-transform ${
                isHovered('logout') ? 'text-red-400' : 'text-red-400/60'
              }`}
            />
            {(!collapsed || onCloseMobile) && (
              <span className={`font-medium text-[13px] relative z-10 ${
                isHovered('logout') ? 'text-red-400' : 'text-red-400/60'
              }`}>
                {t('nav.logout')}
              </span>
            )}
          </button>
        </div>
      </nav>

      {/* Footer Info */}
      {(!collapsed || onCloseMobile) && (
        <div className="p-4 border-t border-white/[0.06] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center text-xs font-medium uppercase shrink-0">
              {user?.email?.[0] || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate text-white/70">{user?.email}</p>
              <p className="text-[10px] text-white/40 truncate uppercase tracking-wider font-semibold">{user?.role}</p>
            </div>
          </div>
        </div>
      )}

      {/* Tooltip animation keyframe */}
      <style>{`
        @keyframes sidebar-tooltip-in {
          from {
            opacity: 0;
            transform: translateX(-4px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </aside>
  );
};

export default Sidebar;
