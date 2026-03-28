/**
 * StatusAlertsCluster.tsx
 * Help icon (?) + Notification bell (🔔) + Status indicators
 * 
 * Animaciones:
 * - Help: Pulse suave 2s
 * - Bell badge: Ping scale 1.5s
 * - Status dot: Verde=online, Rojo=offline
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from '../../context/LanguageContext';
import {
  HelpCircle,
  Bell,
  Wifi,
  WifiOff,
  AlertCircle,
  MoreVertical,
} from 'lucide-react';
import type { StatusAlertsClusterProps } from './types';

export const StatusAlertsCluster: React.FC<StatusAlertsClusterProps> = ({
  hasNewGuide = false,
  notificationCount = 0,
  onHelpClick,
  onNotificationClick,
  isOnline = true,
  connectionStatus = 'online',
}) => {
  const { t } = useTranslation();
  const [showTooltip, setShowTooltip] = useState<string | null>(null);
  const [displayNotificationCount, setDisplayNotificationCount] =
    useState(notificationCount);

  // Actualizar contador de notificaciones con animación suave
  useEffect(() => {
    if (notificationCount !== displayNotificationCount) {
      // Pequeña animación al cambiar
      setDisplayNotificationCount(notificationCount);
    }
  }, [notificationCount, displayNotificationCount]);

  // Estilos para estado de conexión
  const getStatusColor = () => {
    if (connectionStatus === 'online' || isOnline) {
      return '#28a745'; // Verde
    }
    if (connectionStatus === 'unstable') {
      return '#ffc107'; // Amarillo/Warning
    }
    return '#dc3545'; // Rojo
  };

  const getStatusIcon = () => {
    if (connectionStatus === 'unstable') {
      return <AlertCircle size={16} />;
    }
    if (connectionStatus === 'online' || isOnline) {
      return <Wifi size={16} />;
    }
    return <WifiOff size={16} />;
  };

  const getStatusLabel = () => {
    if (connectionStatus === 'online' || isOnline) {
      return t('header.status_online') || 'Online';
    }
    if (connectionStatus === 'unstable') {
      return t('header.status_unstable') || 'Unstable';
    }
    return t('header.offline') || 'Offline';
  };

  return (
    <div className="flex items-center gap-4">
      {/* Help Icon with tooltip */}
      <div className="relative group">
        <button
          onClick={onHelpClick}
          onMouseEnter={() => setShowTooltip('help')}
          onMouseLeave={() => setShowTooltip(null)}
          className={`flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200 ${
            hasNewGuide ? 'animate-pulse' : ''
          }`}
          title={t('header.help_tooltip')}
          aria-label="Help"
        >
          <HelpCircle
            size={18}
            className={`text-white/70 ${
              hasNewGuide ? 'text-medical-400' : ''
            }`}
            style={
              hasNewGuide
                ? {
                    animation: 'pulseSoft 2s ease-in-out infinite',
                  }
                : undefined
            }
          />
        </button>

        {/* Tooltip */}
        {showTooltip === 'help' && (
          <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-slate-900 text-white text-xs rounded-lg border border-white/10 whitespace-nowrap shadow-lg">
            {t('header.help_tooltip') || 'Press ? for help'}
            <div className="absolute top-full right-2 w-2 h-2 bg-slate-900 border-r border-b border-white/10 transform rotate-45" />
          </div>
        )}
      </div>

      {/* Notification Bell */}
      <div className="relative group">
        <button
          onClick={onNotificationClick}
          onMouseEnter={() => setShowTooltip('notifications')}
          onMouseLeave={() => setShowTooltip(null)}
          className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200 relative"
          title={
            displayNotificationCount > 0
              ? `${displayNotificationCount} notifications`
              : 'Notifications'
          }
          aria-label="Notifications"
        >
          <Bell
            size={18}
            className="text-white/70"
            strokeWidth={displayNotificationCount > 0 ? 2.5 : 2}
          />

          {/* Badge rojo con ping animation */}
          {displayNotificationCount > 0 && (
            <>
              <div
                className="absolute top-1 right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold border-2 border-slate-900"
                style={{
                  animation: 'ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite',
                }}
              >
                {displayNotificationCount > 9 ? '9+' : displayNotificationCount}
              </div>
              {/* Círculo de fondo del badge */}
              <div className="absolute top-1 right-1 w-5 h-5 bg-red-500/30 rounded-full pointer-events-none" />
            </>
          )}
        </button>

        {/* Tooltip */}
        {showTooltip === 'notifications' && (
          <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-slate-900 text-white text-xs rounded-lg border border-white/10 whitespace-nowrap shadow-lg">
            {displayNotificationCount > 0
              ? `${displayNotificationCount} new notifications`
              : 'No new notifications'}
            <div className="absolute top-full right-2 w-2 h-2 bg-slate-900 border-r border-b border-white/10 transform rotate-45" />
          </div>
        )}
      </div>

      {/* Status Dot with Connection Info */}
      <div className="relative group">
        <button
          onMouseEnter={() => setShowTooltip('status')}
          onMouseLeave={() => setShowTooltip(null)}
          className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-200"
          title={getStatusLabel()}
          aria-label={`Status: ${getStatusLabel()}`}
        >
          <div className="text-white/70">{getStatusIcon()}</div>
        </button>

        {/* Status Dot Indicator */}
        <div
          className={`absolute top-1 right-1 w-3 h-3 rounded-full border-2 border-slate-900 ${
            connectionStatus === 'unstable' ? 'animate-pulse' : ''
          }`}
          style={{
            backgroundColor: getStatusColor(),
          }}
        />

        {/* Tooltip */}
        {showTooltip === 'status' && (
          <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-slate-900 text-white text-xs rounded-lg border border-white/10 whitespace-nowrap shadow-lg">
            {getStatusLabel()}
            <div className="absolute top-full right-2 w-2 h-2 bg-slate-900 border-r border-b border-white/10 transform rotate-45" />
          </div>
        )}
      </div>

      {/* More Options (opcional) */}
      <button
        className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200"
        title="More options"
        aria-label="More options"
      >
        <MoreVertical size={18} className="text-white/70" />
      </button>

      {/* Estilos de animación */}
      <style>{`
        @keyframes pulseSoft {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        @keyframes ping {
          75%, 100% {
            transform: scale(2);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
};

export default StatusAlertsCluster;
