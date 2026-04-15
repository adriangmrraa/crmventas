import React, { useState, useEffect } from 'react';
import {
  Bell, BellRing, Check, X, Settings, Filter, Clock,
  AlertCircle, TrendingUp, MessageSquare, User, Zap,
  ChevronRight, ExternalLink, MoreVertical, RefreshCw,
  Wifi, WifiOff, Radio
} from 'lucide-react';
import { useTranslation } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useSocket, useSocketNotifications } from '../context/SocketContext';
import api from '../api/axios';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  priority: string;
  recipient_id: string;
  sender_id?: string;
  related_entity_type?: string;
  related_entity_id?: string;
  metadata: Record<string, any>;
  read: boolean;
  created_at: string;
  expires_at?: string;
  sender_name?: string;
  sender_email?: string;
}

interface NotificationCount {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface NotificationCenterProps {
  onClose: () => void;
  onNotificationRead: (notificationId: string) => void;
  onMarkAllRead: () => void;
  initialCount: NotificationCount;
}

const NotificationCenter: React.FC<NotificationCenterProps> = ({
  onClose,
  onNotificationRead,
  onMarkAllRead,
  initialCount
}) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { socket, isConnected: socketConnected } = useSocket();
  const { newNotifications: socketNotifications } = useSocketNotifications();

  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'unread'>('unread');
  const [refreshing, setRefreshing] = useState(false);
  const [notificationCount, setNotificationCount] = useState<NotificationCount>(initialCount);
  const [usingSocket, setUsingSocket] = useState(false);

  // Determinar si usar Socket.IO o API
  useEffect(() => {
    setUsingSocket(!!(socket && socketConnected));
    // Siempre obtener las notificaciones iniciales independientemente de Socket.IO,
    // ya que Socket.IO solo envía las nuevas (historico / persistencia es por API)
    fetchNotifications();
  }, [socketConnected, filter]);

  // Sincronizar notificaciones de Socket.IO
  useEffect(() => {
    if (usingSocket && socketNotifications.length > 0) {
      // Combinar notificaciones existentes con nuevas de Socket.IO
      // (en un sistema real, esto sería más sofisticado)
      setNotifications(prev => {
        const socketIds = new Set(socketNotifications.map(n => n.id));
        const filteredPrev = prev.filter(n => !socketIds.has(n.id));
        return [...socketNotifications, ...filteredPrev].slice(0, 50);
      });
    }
  }, [socketNotifications, usingSocket]);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/admin/core/notifications', {
        params: {
          limit: 50,
          unread_only: filter === 'unread'
        }
      });

      setNotifications(response.data);

      // Also update count
      const countResponse = await api.get('/admin/core/notifications/count');
      setNotificationCount(countResponse.data);

    } catch (err: any) {
      console.error('Error fetching notifications:', err);
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const refreshNotifications = () => {
    setRefreshing(true);
    if (usingSocket && socket) {
      // Solicitar actualización via Socket.IO
      socket.emit('get_notification_count', { user_id: 'current' });
      setRefreshing(false);
    } else {
      fetchNotifications();
    }
  };

  const markAsRead = async (notificationId: string) => {
    try {
      if (usingSocket && socket) {
        // Usar Socket.IO
        socket.emit('mark_notification_read', {
          notification_id: notificationId,
          user_id: user?.id || 'current'
        });
      } else {
        // Usar API tradicional
        await api.post('/admin/core/notifications/read', {
          notification_id: notificationId
        });
      }

      // Update local state
      setNotifications(prev => prev.map(n =>
        n.id === notificationId ? { ...n, read: true } : n
      ));

      // Update count
      setNotificationCount(prev => ({
        ...prev,
        total: Math.max(0, prev.total - 1),
        [notificationPriorityCountKey(notificationId)]: Math.max(0,
          notificationCount[notificationPriorityCountKey(notificationId)] - 1
        )
      }));

      // Notify parent
      onNotificationRead(notificationId);

    } catch (err: any) {
      console.error('Error marking notification as read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await onMarkAllRead();
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setNotificationCount({
        total: 0,
        critical: 0,
        high: 0,
        medium: 0,
        low: 0
      });
    } catch (err: any) {
      console.error('Error marking all as read:', err);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'unanswered':
        return <MessageSquare size={16} className="text-red-500" />;
      case 'hot_lead':
        return <Zap size={16} className="text-orange-500" />;
      case 'followup':
        return <Clock size={16} className="text-violet-500" />;
      case 'performance_alert':
        return <TrendingUp size={16} className="text-yellow-500" />;
      case 'assignment':
        return <User size={16} className="text-green-500" />;
      default:
        return <Bell size={16} className="text-white/40" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'border-red-500 bg-red-500/10';
      case 'high':
        return 'border-orange-500 bg-orange-500/10';
      case 'medium':
        return 'border-yellow-500 bg-yellow-500/10';
      case 'low':
        return 'border-violet-500 bg-violet-500/10';
      default:
        return 'border-white/[0.10] bg-white/[0.02]';
    }
  };

  const getPriorityText = (priority: string) => {
    switch (priority) {
      case 'critical':
        return t('notifications.priority_critical');
      case 'high':
        return t('notifications.priority_high');
      case 'medium':
        return t('notifications.priority_medium');
      case 'low':
        return t('notifications.priority_low');
      default:
        return priority;
    }
  };

  const formatTime = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), {
        addSuffix: true,
        locale: es
      });
    } catch (err) {
      return dateString;
    }
  };

  const handleNotificationClick = (notification: Notification) => {
    // Mark as read when clicked
    if (!notification.read) {
      markAsRead(notification.id);
    }

    // Navigate to related entity if applicable
    if (notification.related_entity_type && notification.related_entity_id) {
      switch (notification.related_entity_type) {
        case 'conversation':
          // Navigate to chat
          window.location.href = `/chats?conversation=${notification.related_entity_id}`;
          break;
        case 'lead':
          // Navigate to lead
          window.location.href = `/crm/leads/${notification.related_entity_id}`;
          break;
        case 'client':
          // Navigate to client
          window.location.href = `/crm/clientes/${notification.related_entity_id}`;
          break;
      }
    }

    // Close notification center
    onClose();
  };

  const notificationPriorityCountKey = (notificationId: string) => {
    const notification = notifications.find(n => n.id === notificationId);
    if (!notification) return 'total';

    switch (notification.priority) {
      case 'critical': return 'critical';
      case 'high': return 'high';
      case 'medium': return 'medium';
      case 'low': return 'low';
      default: return 'total';
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, [filter]);

  const filteredNotifications = notifications.filter(n =>
    filter === 'all' || !n.read
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <BellRing size={20} className="text-white/70" />
            {usingSocket && (
              <div className={`absolute -bottom-1 -right-1 w-2 h-2 rounded-full ${socketConnected ? 'bg-green-500' : 'bg-red-500'
                }`} />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-white">
              {t('notifications.center_title')}
            </h3>
            <div className="flex items-center gap-2">
              <p className="text-sm text-white/40">
                {notificationCount.total} {t('notifications.notifications')}
                {notificationCount.critical > 0 && ` • ${notificationCount.critical} ${t('notifications.critical')}`}
              </p>
              {usingSocket && (
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${socketConnected
                  ? 'bg-green-500/10 text-green-400'
                  : 'bg-red-500/10 text-red-400'
                  }`}>
                  {socketConnected ? <Wifi size={10} /> : <WifiOff size={10} />}
                  {socketConnected ? t('notifications.real_time_updates') : t('notifications.socket_disconnected')}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {usingSocket && (
            <div className="text-xs text-white/40 px-2 py-1 rounded bg-white/[0.04]">
              {socketConnected ? 'Socket.IO' : 'API'}
            </div>
          )}

          <button
            onClick={refreshNotifications}
            disabled={refreshing}
            className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors disabled:opacity-50"
            title={t('notifications.refresh')}
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
          </button>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors"
            title={t('common.close')}
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="p-3 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex gap-1">
          <button
            onClick={() => setFilter('unread')}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${filter === 'unread'
              ? 'bg-violet-500/10 text-violet-400'
              : 'text-white/50 hover:bg-white/[0.06]'
              }`}
          >
            {t('notifications.unread')} ({notificationCount.total})
          </button>
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${filter === 'all'
              ? 'bg-violet-500/10 text-violet-400'
              : 'text-white/50 hover:bg-white/[0.06]'
              }`}
          >
            {t('notifications.all')}
          </button>
        </div>

        {notificationCount.total > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="text-sm text-violet-400 hover:text-violet-300 flex items-center gap-1"
          >
            <Check size={14} />
            {t('notifications.mark_all_read')}
          </button>
        )}
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-violet-600"></div>
            <p className="mt-2 text-white/40">
              {t('notifications.loading')}
            </p>
          </div>
        ) : error ? (
          <div className="p-4 text-center">
            <AlertCircle className="inline-block text-red-500 mb-2" size={24} />
            <p className="text-red-400">{error}</p>
            <button
              onClick={refreshNotifications}
              className="mt-2 text-sm text-violet-400 hover:underline"
            >
              {t('notifications.retry')}
            </button>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="p-8 text-center">
            <Bell className="inline-block text-white/30 mb-2" size={32} />
            <p className="text-white/40">
              {filter === 'unread'
                ? t('notifications.no_unread_notifications')
                : t('notifications.no_notifications')
              }
            </p>
          </div>
        ) : (
          <div className="divide-y divide-white/[0.04]">
            {filteredNotifications.map((notification) => (
              <div
                key={notification.id}
                className={`p-4 hover:bg-white/[0.04] transition-colors cursor-pointer ${!notification.read ? 'bg-violet-500/5' : ''
                  }`}
                onClick={() => handleNotificationClick(notification)}
              >
                <div className="flex gap-3">
                  {/* Icon */}
                  <div className="flex-shrink-0 mt-0.5">
                    {getTypeIcon(notification.type)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium text-white">
                          {notification.title}
                        </h4>
                        <p className="text-sm text-white/50 mt-1">
                          {notification.message}
                        </p>
                      </div>

                      {!notification.read && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            markAsRead(notification.id);
                          }}
                          className="flex-shrink-0 p-1 rounded-full hover:bg-white/[0.08] transition-colors"
                          title={t('notifications.mark_as_read')}
                        >
                          <Check size={14} className="text-white/40" />
                        </button>
                      )}
                    </div>

                    {/* Metadata */}
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${getPriorityColor(notification.priority)}`}>
                        {getPriorityText(notification.priority)}
                      </span>

                      <span className="text-xs text-white/40">
                        {formatTime(notification.created_at)}
                      </span>

                      {notification.sender_name && (
                        <span className="text-xs text-white/40">
                          • {notification.sender_name}
                        </span>
                      )}

                      {notification.related_entity_type && (
                        <span className="text-xs text-violet-400 flex items-center gap-1">
                          <ChevronRight size={10} />
                          {t(`notifications.entity_${notification.related_entity_type}`)}
                        </span>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="mt-3 flex gap-2">
                      {notification.related_entity_id && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleNotificationClick(notification);
                          }}
                          className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1"
                        >
                          <ExternalLink size={12} />
                          {t('notifications.view_entity')}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-white/[0.06] flex items-center justify-between">
        <button
          onClick={() => window.location.href = '/notificaciones'}
          className="text-sm text-white/50 hover:text-white/70 flex items-center gap-1"
        >
          {t('notifications.view_all')}
          <ChevronRight size={14} />
        </button>

        <button
          onClick={() => window.location.href = '/configuracion?tab=notifications'}
          className="text-sm text-white/50 hover:text-white/70 flex items-center gap-1"
        >
          <Settings size={14} />
          {t('notifications.settings')}
        </button>
      </div>
    </div>
  );
};

export default NotificationCenter;