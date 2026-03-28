import React, { type ReactNode, useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { io, Socket } from 'socket.io-client';
import { BACKEND_URL } from '../api/axios';
import { AlertCircle, X, HelpCircle } from 'lucide-react';
import NotificationBell from './NotificationBell';
import OnboardingGuide from './OnboardingGuide';
import { NovaWidget } from './NovaWidget';
import axios from 'axios';
import { GlobalTopBar, ContextualSubheader, StatusAlertsCluster } from './Header';
import type { BreadcrumbItem } from './Header/types';

interface Tenant {
  id: number;
  clinic_name: string;
  logo_url?: string;
}

interface LayoutProps {
  children: ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const socketRef = useRef<Socket | null>(null);
  const [showGuide, setShowGuide] = useState(false);
  const [guideTooltip, setGuideTooltip] = useState(false);
  const tooltipShownRef = useRef(false);

  // Tenant Management
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [currentTenant, setCurrentTenant] = useState<Tenant | undefined>();
  const [tenantsLoading, setTenantsLoading] = useState(false);

  // Tooltip on first visit
  useEffect(() => {
    if (tooltipShownRef.current) return;
    const alreadyShown = sessionStorage.getItem('tooltips_shown');
    if (alreadyShown) return;
    tooltipShownRef.current = true;
    const t1 = setTimeout(() => setGuideTooltip(true), 3000);
    const t2 = setTimeout(() => { setGuideTooltip(false); sessionStorage.setItem('tooltips_shown', '1'); }, 8000);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  // Notification State
  const [notification, setNotification] = useState<{
    show: boolean;
    phone: string;
    reason: string;
  } | null>(null);

  // Contextual subheader state
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([
    { label: t('breadcrumb.home') || 'Home', path: '/' }
  ]);
  const [filterActive, setFilterActive] = useState(false);
  const [filterCount, setFilterCount] = useState(0);

  // Global Socket Listener for Handoffs
  useEffect(() => {
    if (!user) return;

    // Conectar socket si no existe
    if (!socketRef.current) {
      // Connect to root namespace (matching ChatsView.tsx logic)
      socketRef.current = io(BACKEND_URL);
    }

    // Listener
    const handleHandoff = (data: { phone_number: string; reason: string }) => {

      // Mostrar notificación
      setNotification({
        show: true,
        phone: data.phone_number,
        reason: data.reason
      });

      // Auto-ocultar a los 5 segundos
      setTimeout(() => {
        setNotification(null);
      }, 5000);

      // Reproducir sonido (opcional, si el navegador lo permite)
      try {
        const audio = new Audio('/assets/notification.mp3');
        // Fallback or generic sound logic here if asset missing
        audio.play().catch(_e => { });
      } catch (e) { }
    };

    socketRef.current.on('HUMAN_HANDOFF', handleHandoff);

    return () => {
      socketRef.current?.off('HUMAN_HANDOFF', handleHandoff);
    };
  }, [user]);

  // Load tenants for current user
  useEffect(() => {
    if (!user) return;

    const loadTenants = async () => {
      try {
        setTenantsLoading(true);
        const response = await axios.get('/admin/tenants', {
          headers: {
            'X-Admin-Token': localStorage.getItem('admin_token') || '',
          }
        });
        
        if (Array.isArray(response.data)) {
          setTenants(response.data);
          // Set first tenant as default if not already set
          if (!currentTenant && response.data.length > 0) {
            setCurrentTenant(response.data[0]);
          }
        }
      } catch (error) {
        console.error('Failed to load tenants:', error);
      } finally {
        setTenantsLoading(false);
      }
    };

    loadTenants();
  }, [user, currentTenant]);

  const handleNotificationClick = () => {
    if (notification) {
      // Navegar al chat seleccionando el teléfono
      navigate('/chats', { state: { selectPhone: notification.phone } });
      setNotification(null);
    }
  };

  return (
    <div className="flex h-screen bg-[#06060e] relative overflow-hidden">
      {/* Mobile Backdrop */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar - Desktop and Mobile Drawer */}
      <div className={`
        fixed lg:relative inset-y-0 left-0 z-50 transition-all duration-300 transform
        w-72 lg:w-auto
        ${isMobileMenuOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full lg:translate-x-0 shadow-none'}
        ${sidebarCollapsed ? 'lg:w-16' : 'lg:w-64'}
      `}>
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          onCloseMobile={() => setIsMobileMenuOpen(false)}
        />
      </div>

      {/* Main Content - includes header and scrollable area */}
      <main
        className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 w-full min-w-0`}
      >
        {/* Global Top Bar (fixed at top) */}
        <GlobalTopBar
          currentTenant={currentTenant}
          tenants={tenants}
          onTenantChange={(tenantId) => {
            const tenant = tenants.find(t => t.id === tenantId);
            if (tenant) setCurrentTenant(tenant);
          }}
          isLoading={tenantsLoading}
          onMenuClick={() => setIsMobileMenuOpen(true)}
        />

        {/* Contextual Subheader (sticky below top bar) */}
        <ContextualSubheader
          breadcrumbs={breadcrumbs}
          filterActive={filterActive}
          filterCount={filterCount}
          onFilterClick={() => setFilterActive(!filterActive)}
          visible={true}
        />

        {/* Page Content Area - scrollable */}
        <div className="flex-1 min-h-0 bg-transparent overflow-y-auto overflow-x-hidden">
          {children}
        </div>
      </main>

      {/* Onboarding Guide */}
      {/* Nova AI Voice Widget */}
      <NovaWidget />

      {/* Onboarding Guide */}
      <OnboardingGuide isOpen={showGuide} onClose={() => setShowGuide(false)} />

      {/* GLOBAL NOTIFICATION TOAST */}
      {notification && (
        <div
          className="fixed bottom-6 right-6 z-50 max-w-sm w-full bg-[#0d1117] rounded-xl shadow-xl border border-white/[0.08] border-l-4 border-l-orange-500 p-4 transform transition-all duration-300 ease-in-out cursor-pointer hover:bg-white/[0.04]"
          onClick={handleNotificationClick}
        >
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <AlertCircle className="h-6 w-6 text-orange-500" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-white">🔔 {t('layout.notification_handoff')}</h3>
              <p className="mt-1 text-sm text-white/50 line-clamp-2">
                {notification.phone}. {t('layout.notification_reason')}: {notification.reason}
              </p>
              <div className="mt-2 text-xs text-orange-400 font-medium">
                {t('layout.click_to_open_chat')}
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setNotification(null); }}
              className="text-white/30 hover:text-white/60"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Layout;
