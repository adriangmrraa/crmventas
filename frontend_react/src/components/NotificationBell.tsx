import React, { useState, useEffect, useRef } from 'react';
import { Bell, BellRing, Check, X, Settings, Filter, Wifi, WifiOff } from 'lucide-react';
import { useTranslation } from '../context/LanguageContext';
import { useSocketNotifications } from '../context/SocketContext';
import api from '../api/axios';
import NotificationCenter from './NotificationCenter';

interface NotificationCount {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface NotificationBellProps {
  className?: string;
  showLabel?: boolean;
  useSocket?: boolean; // Usar Socket.IO en tiempo real
  fallbackToApi?: boolean; // Fallback a API si Socket falla
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const NotificationBell: React.FC<NotificationBellProps> = ({
  className = '',
  showLabel = false,
  useSocket = true,
  fallbackToApi = true,
  autoRefresh = true,
  refreshInterval = 30000 // 30 segundos
}) => {
  const { t } = useTranslation();
  const {
    notificationCount: socketCount,
    refreshCount: socketRefresh,
    isConnected: socketConnected
  } = useSocketNotifications();

  const [showCenter, setShowCenter] = useState(false);
  const [notificationCount, setNotificationCount] = useState<NotificationCount>({
    total: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [usingSocket, setUsingSocket] = useState(useSocket);

  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Usar Socket.IO si está disponible y conectado
  useEffect(() => {
    if (useSocket && socketConnected) {
      setUsingSocket(true);
      // Socket.IO actualiza automáticamente via useSocketNotifications hook
    } else if (fallbackToApi) {
      setUsingSocket(false);
    }
  }, [useSocket, socketConnected, fallbackToApi]);

  // Sincronizar count de Socket.IO con estado local
  useEffect(() => {
    if (usingSocket && socketConnected) {
      setNotificationCount(socketCount);
      setLastUpdated(new Date());
    }
  }, [socketCount, usingSocket, socketConnected]);

  const fetchNotificationCount = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/admin/core/notifications/count');
      setNotificationCount(response.data);
      setLastUpdated(new Date());

    } catch (err: any) {
      console.error('Error fetching notification count:', err);
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.post('/admin/core/notifications/read-all');

      // Refresh count según el método que estemos usando
      if (usingSocket && socketConnected) {
        socketRefresh();
      } else {
        await fetchNotificationCount();
      }
    } catch (err: any) {
      console.error('Error marking all as read:', err);
    }
  };

  const refreshCount = () => {
    if (usingSocket && socketConnected) {
      socketRefresh();
    } else {
      fetchNotificationCount();
    }
  };

  useEffect(() => {
    // Fetch initial count
    if (!usingSocket || !socketConnected) {
      fetchNotificationCount();
    }

    // Set up auto-refresh if enabled y no estamos usando Socket.IO
    if (autoRefresh && (!usingSocket || !socketConnected)) {
      refreshIntervalRef.current = setInterval(fetchNotificationCount, refreshInterval);
    }

    // Cleanup
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, usingSocket, socketConnected]);

  const getPriorityColor = () => {
    if (notificationCount.critical > 0) return 'bg-red-500';
    if (notificationCount.high > 0) return 'bg-orange-500';
    if (notificationCount.medium > 0) return 'bg-yellow-500';
    if (notificationCount.low > 0) return 'bg-blue-500';
    return 'bg-gray-400';
  };

  const getPriorityIcon = () => {
    if (notificationCount.critical > 0) return <BellRing className="text-red-500" />;
    if (notificationCount.total > 0) return <BellRing className="text-orange-500" />;
    return <Bell className="text-gray-400" />;
  };

  const getTooltipText = () => {
    if (notificationCount.total === 0) return t('notifications.no_notifications');

    const parts = [];
    if (notificationCount.critical > 0) parts.push(`${notificationCount.critical} críticas`);
    if (notificationCount.high > 0) parts.push(`${notificationCount.high} altas`);
    if (notificationCount.medium > 0) parts.push(`${notificationCount.medium} medias`);
    if (notificationCount.low > 0) parts.push(`${notificationCount.low} bajas`);

    return `${notificationCount.total} notificaciones (${parts.join(', ')})`;
  };

  const handleBellClick = () => {
    setShowCenter(!showCenter);
  };

  const handleCloseCenter = () => {
    setShowCenter(false);
  };

  const handleNotificationRead = () => {
    // Refresh count when a notification is marked as read
    refreshCount();
  };

  const handleMarkAllRead = async () => {
    await markAllAsRead();
    if (showCenter) {
      // If notification center is open, we might want to refresh it too
      // This will be handled by the NotificationCenter component via props
    }
  };

  const getConnectionStatus = () => {
    if (usingSocket) {
      return socketConnected ? 'connected' : 'disconnected';
    }
    return 'api';
  };

  const getConnectionTooltip = () => {
    const status = getConnectionStatus();
    switch (status) {
      case 'connected':
        return t('notifications.socket_connected');
      case 'disconnected':
        return t('notifications.socket_disconnected');
      default:
        return t('notifications.using_api');
    }
  };

  return (
    <div className={`relative ${className}`}>
      {/* Notification Bell Button */}
      <button
        onClick={handleBellClick}
        className="relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group"
        aria-label={t('notifications.bell_aria_label')}
        title={`${getTooltipText()} (${getConnectionTooltip()})`}
      >
        <div className="relative">
          {getPriorityIcon()}

          {/* Connection status indicator */}
          {usingSocket && (
            <div className={`absolute -bottom-1 -right-1 w-2 h-2 rounded-full ${socketConnected ? 'bg-green-500' : 'bg-red-500'
              }`} />
          )}
        </div>

        {/* Badge with count */}
        {notificationCount.total > 0 && (
          <span className={`absolute -top-1 -right-1 min-w-5 h-5 px-1 rounded-full text-xs font-bold text-white flex items-center justify-center ${getPriorityColor()}`}>
            {notificationCount.total > 99 ? '99+' : notificationCount.total}
          </span>
        )}

        {/* Loading indicator */}
        {loading && (
          <span className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-2 h-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
          </span>
        )}
      </button>

      {/* Label if enabled */}
      {showLabel && (
        <div className="mt-1 text-xs text-gray-500 text-center">
          {notificationCount.total === 0
            ? t('notifications.no_notifications')
            : `${notificationCount.total} ${t('notifications.notifications')}`
          }
        </div>
      )}

      {/* Notification Center (Dropdown) */}
      {showCenter && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={handleCloseCenter}
          />

          {/* Center Container */}
          <div className="fixed sm:absolute top-16 sm:top-full right-2 sm:right-0 sm:mt-2 w-[calc(100vw-1rem)] sm:w-96 bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50 max-h-[calc(100vh-5rem)] sm:max-h-[80vh] flex flex-col overflow-hidden">
            <NotificationCenter
              onClose={handleCloseCenter}
              onNotificationRead={handleNotificationRead}
              onMarkAllRead={handleMarkAllRead}
              initialCount={notificationCount}
            />
          </div>
        </>
      )}

      {/* Error message (hidden by default, shows on hover if there's an error) */}
      {error && (
        <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50">
          <div className="flex items-center gap-2">
            <X size={14} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Last updated time (debug) */}
      {process.env.NODE_ENV === 'development' && lastUpdated && (
        <div className="absolute -bottom-6 right-0 text-[10px] text-gray-400">
          {t('notifications.last_updated')}: {lastUpdated.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

export default NotificationBell;