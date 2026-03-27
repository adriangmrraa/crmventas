import React, { type ReactNode, useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { io, Socket } from 'socket.io-client';
import { BACKEND_URL } from '../api/axios';
import { AlertCircle, X } from 'lucide-react';
import NotificationBell from './NotificationBell';

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

  // Notification State
  const [notification, setNotification] = useState<{
    show: boolean;
    phone: string;
    reason: string;
  } | null>(null);

  // Global Socket Listener for Handoffs
  useEffect(() => {
    if (!user) return;

    // Conectar socket si no existe
    if (!socketRef.current) {
      // Connect to root namespace (matching ChatsView.tsx logic)
      socketRef.current = io(BACKEND_URL);
    }

    // Listener
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
      // No desconectamos el socket aquí porque Layout se monta/desmonta poco, 
      // pero si navegamos fuera de app (logout), el socket debería morir.
      // Ojo: ChatsView también crea socket. Idealmente debería ser un Context.
      // Por ahora para cumplir el requerimiento rápido, duplicamos la conexión (low cost).
    };
  }, [user]);

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

      {/* Main Content */}
      <main
        className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 w-full min-w-0`}
      >
        {/* Top Header */}
        <header className="h-14 bg-[#0a0e1a]/80 backdrop-blur-xl border-b border-white/[0.06] flex items-center justify-between px-4 lg:px-6 sticky top-0 z-30">
          <div className="flex items-center gap-3 lg:gap-4">
            {/* Hamburger Button for Mobile */}
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="lg:hidden p-2 hover:bg-white/[0.06] rounded-lg text-white/50"
            >
              <div className="w-6 h-5 flex flex-col justify-between">
                <span className="w-full h-0.5 bg-current rounded-full"></span>
                <span className="w-full h-0.5 bg-current rounded-full"></span>
                <span className="w-full h-0.5 bg-current rounded-full"></span>
              </div>
            </button>
            <h1 className="text-lg lg:text-xl font-semibold text-white truncate max-w-[150px] md:max-w-none">
              {t('layout.app_title_crm')}
            </h1>
          </div>

          <div className="flex items-center gap-2 lg:gap-4">
            {/* Tenant/Entity Selector - Hidden on small mobile */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-white/[0.04] rounded-lg text-sm border border-white/[0.06]">
              <span className="text-white/40">{t('layout.entity')}:</span>
              <span className="font-medium text-white/80">{t('layout.entity_principal')}</span>
            </div>

            {/* User Menu */}
            <div className="flex items-center gap-2 lg:gap-3">
              {/* Notification Bell */}
              <NotificationBell className="block" />

              <div className="hidden xs:flex flex-col items-end">
                <span className="text-xs lg:text-sm font-medium text-white/80">{user?.email?.split('@')[0]}</span>
                <span className="text-[10px] lg:text-xs text-white/40 uppercase leading-none">{user?.role}</span>
              </div>
              <div className="w-8 h-8 lg:w-9 lg:h-9 rounded-lg bg-white/[0.08] flex items-center justify-center text-white/70 font-semibold text-sm lg:text-base">
                {user?.email?.[0].toUpperCase() || 'U'}
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 min-h-0 bg-transparent overflow-hidden">
          {children}
        </div>
      </main>

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
