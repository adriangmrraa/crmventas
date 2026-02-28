import { useState, useEffect, useCallback } from 'react';
import {
    Bell, Filter, User, MessageSquare, Zap, Clock, TrendingUp, AlertCircle,
    ChevronDown, RefreshCw, Loader2, Calendar, CheckCircle, Info
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import PageHeader from '../components/PageHeader';
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
}

interface Seller {
    id: string;
    email: string;
    first_name?: string;
    last_name?: string;
    role: string;
}

export default function NotificationsView() {
    const { user } = useAuth();

    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [sellers, setSellers] = useState<Seller[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [offset, setOffset] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [selectedSellerId, setSelectedSellerId] = useState<string>('all');
    const [unreadOnly, setUnreadOnly] = useState(false);

    const LIMIT = 30;

    // Fetch sellers for CEO filter
    useEffect(() => {
        if (user?.role === 'ceo') {
            const fetchSellers = async () => {
                try {
                    const response = await api.get('/admin/core/users');
                    // Filter only staff roles
                    const staff = response.data.filter((u: any) =>
                        ['setter', 'closer', 'secretary', 'professional'].includes(u.role)
                    );
                    setSellers(staff);
                } catch (err) {
                    console.error('Error fetching sellers:', err);
                }
            };
            fetchSellers();
        }
    }, [user]);

    const fetchNotifications = useCallback(async (currentOffset: number, append = false) => {
        try {
            if (append) setLoadingMore(true);
            else setLoading(true);

            const response = await api.get('/admin/core/notifications', {
                params: {
                    limit: LIMIT,
                    offset: currentOffset,
                    unread_only: unreadOnly,
                    seller_id: selectedSellerId === 'all' ? undefined : selectedSellerId
                }
            });

            const newNotifications = response.data;

            if (append) {
                setNotifications(prev => [...prev, ...newNotifications]);
            } else {
                setNotifications(newNotifications);
            }

            setHasMore(newNotifications.length === LIMIT);
            setError(null);
        } catch (err: any) {
            console.error('Error fetching notifications:', err);
            setError('No se pudieron cargar las notificaciones. Intenta de nuevo.');
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    }, [selectedSellerId, unreadOnly]);

    useEffect(() => {
        setOffset(0);
        fetchNotifications(0, false);
    }, [selectedSellerId, unreadOnly, fetchNotifications]);

    const loadMore = () => {
        const nextOffset = offset + LIMIT;
        setOffset(nextOffset);
        fetchNotifications(nextOffset, true);
    };

    const markAsRead = async (id: string) => {
        try {
            await api.post('/admin/core/notifications/read', { notification_id: id });
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
        } catch (err) {
            console.error('Error marking as read:', err);
        }
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case 'unanswered': return <MessageSquare size={18} className="text-red-500" />;
            case 'hot_lead': return <Zap size={18} className="text-orange-500" />;
            case 'followup': return <Clock size={18} className="text-blue-500" />;
            case 'performance_alert': return <TrendingUp size={18} className="text-yellow-500" />;
            case 'assignment': return <User size={18} className="text-green-500" />;
            default: return <Bell size={18} className="text-gray-500" />;
        }
    };

    const getPriorityBadge = (priority: string) => {
        const styles: Record<string, string> = {
            critical: 'bg-red-100 text-red-700 border-red-200',
            high: 'bg-orange-100 text-orange-700 border-orange-200',
            medium: 'bg-blue-100 text-blue-700 border-blue-200',
            low: 'bg-gray-100 text-gray-700 border-gray-200',
        };
        return (
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${styles[priority] || styles.medium}`}>
                {priority.toUpperCase()}
            </span>
        );
    };

    return (
        <div className="min-h-screen bg-gray-50 pb-20">
            <div className="max-w-6xl mx-auto px-4 pt-8">
                <PageHeader
                    title={user?.role === 'ceo' ? "Centro de Control (CEO)" : "Mis Notificaciones"}
                    subtitle="Monitoreo en tiempo real de la actividad comercial"
                    icon={<Bell className="text-primary-600" />}
                />

                {/* Filters Bar */}
                <div className="mt-8 flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-2xl shadow-sm border border-gray-200">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 bg-gray-100 p-1 rounded-lg">
                            <button
                                onClick={() => setUnreadOnly(false)}
                                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${!unreadOnly ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                Todas
                            </button>
                            <button
                                onClick={() => setUnreadOnly(true)}
                                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${unreadOnly ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                No leídas
                            </button>
                        </div>

                        {user?.role === 'ceo' && (
                            <div className="flex items-center gap-2 ml-4">
                                <Filter size={16} className="text-gray-400" />
                                <select
                                    value={selectedSellerId}
                                    onChange={(e) => setSelectedSellerId(e.target.value)}
                                    className="bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block p-2 transition-all"
                                >
                                    <option value="all">Todos los vendedores</option>
                                    {sellers.map(s => (
                                        <option key={s.id} value={s.id}>
                                            {s.first_name ? `${s.first_name} ${s.last_name || ''}` : s.email} ({s.role})
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={() => fetchNotifications(0, false)}
                        className="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-full transition-all"
                        title="Refrescar"
                    >
                        <RefreshCw size={20} className={loading && !loadingMore ? 'animate-spin' : ''} />
                    </button>
                </div>

                {/* Notifications List */}
                <div className="mt-6 space-y-4">
                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl flex items-center gap-3">
                            <AlertCircle size={20} />
                            <p>{error}</p>
                        </div>
                    )}

                    {!loading && notifications.length === 0 ? (
                        <div className="bg-white rounded-3xl p-12 text-center border-2 border-dashed border-gray-200">
                            <div className="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Bell size={40} className="text-gray-300" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900">Sin notificaciones</h3>
                            <p className="text-gray-500 mt-2">No se encontraron alertas para el filtro seleccionado.</p>
                        </div>
                    ) : (
                        <>
                            {notifications.map((n) => (
                                <div
                                    key={n.id}
                                    className={`bg-white rounded-2xl p-5 border transition-all hover:shadow-md flex gap-4 ${!n.read ? 'border-primary-200 bg-primary-50/10' : 'border-gray-200'
                                        }`}
                                >
                                    <div className={`flex-none w-12 h-12 rounded-xl flex items-center justify-center ${!n.read ? 'bg-primary-100' : 'bg-gray-100'
                                        }`}>
                                        {getTypeIcon(n.type)}
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-2 mb-1">
                                            <div className="flex items-center gap-2">
                                                <h4 className={`font-bold text-gray-900 truncate ${!n.read ? '' : 'font-semibold'}`}>
                                                    {n.title}
                                                </h4>
                                                {getPriorityBadge(n.priority)}
                                            </div>
                                            <span className="text-xs text-gray-400 flex items-center gap-1 whitespace-nowrap">
                                                <Calendar size={12} />
                                                {formatDistanceToNow(new Date(n.created_at), { addSuffix: true, locale: es })}
                                            </span>
                                        </div>
                                        <p className="text-gray-600 text-sm leading-relaxed mb-3">
                                            {n.message}
                                        </p>

                                        <div className="flex items-center gap-3">
                                            {!n.read && (
                                                <button
                                                    onClick={() => markAsRead(n.id)}
                                                    className="text-xs font-bold text-primary-600 hover:text-primary-700 flex items-center gap-1 uppercase tracking-wider"
                                                >
                                                    <CheckCircle size={14} />
                                                    Marcar como leída
                                                </button>
                                            )}

                                            {n.related_entity_id && (
                                                <a
                                                    href={n.related_entity_type === 'conversation' ? `/chat?phone=${n.metadata?.phone}` : `/leads/${n.related_entity_id}`}
                                                    className="text-xs font-bold text-gray-600 hover:text-gray-900 flex items-center gap-1 uppercase tracking-wider bg-gray-100 px-3 py-1 rounded-md transition-all"
                                                >
                                                    <Info size={14} />
                                                    Ir al detalle
                                                </a>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}

                            {hasMore && (
                                <button
                                    onClick={loadMore}
                                    disabled={loadingMore}
                                    className="w-full py-4 bg-white border border-gray-200 rounded-2xl text-gray-600 font-bold hover:bg-gray-50 flex items-center justify-center gap-2 transition-all shadow-sm"
                                >
                                    {loadingMore ? (
                                        <>
                                            <Loader2 size={20} className="animate-spin" />
                                            Cargando más...
                                        </>
                                    ) : (
                                        <>
                                            Ver más notificaciones
                                            <ChevronDown size={20} />
                                        </>
                                    )}
                                </button>
                            )}
                        </>
                    )}

                    {loading && !loadingMore && (
                        <div className="flex flex-col items-center justify-center p-20">
                            <Loader2 size={48} className="text-primary-500 animate-spin mb-4" />
                            <p className="text-gray-500 font-medium">Sincronizando con el servidor...</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
