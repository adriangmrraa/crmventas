/**
 * useTeamActivity — DEV-39: Hook para el panel de actividad del equipo en tiempo real.
 * Se suscribe al canal WebSocket team_activity:{tenant_id} y mantiene el feed en memoria.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useSocket } from '../../../context/SocketContext';
import { useAuth } from '../../../context/AuthContext';
import api from '../../../api/axios';

export interface ActivityActor {
  id: string;
  name: string;
  role: string;
}

export interface ActivityEvent {
  id: string;
  actor: ActivityActor;
  event_type: string;
  entity_type: string;
  entity_id: string;
  entity_name?: string;
  metadata: Record<string, any>;
  created_at: string;
  time_ago?: string;
}

export interface SellerStatus {
  id: string;
  user_id: string;
  name: string;
  role: string;
  status: 'active' | 'idle' | 'inactive';
  active_leads_count: number;
  last_activity_at: string | null;
  last_activity_type: string | null;
  avg_first_response_today_seconds: number | null;
  avg_first_response_week_seconds: number | null;
  leads_without_activity_2h: number;
}

export interface InactiveLeadAlert {
  type: string;
  severity: 'warning' | 'critical';
  lead_id: string;
  lead_name: string;
  assigned_seller: string;
  hours_inactive: number;
  last_activity_at: string | null;
}

interface Filters {
  seller_id?: string;
  event_type?: string;
  date_from?: string;
  date_to?: string;
}

export function useTeamActivity() {
  const { socket, isConnected } = useSocket();
  const { user } = useAuth();

  const [feedItems, setFeedItems] = useState<ActivityEvent[]>([]);
  const [sellers, setSellers] = useState<SellerStatus[]>([]);
  const [alerts, setAlerts] = useState<InactiveLeadAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [filters, setFilters] = useState<Filters>({});
  const offsetRef = useRef(0);

  const tenantId = user?.tenant_id;

  // Fetch feed from API
  const fetchFeed = useCallback(async (reset = false) => {
    try {
      const offset = reset ? 0 : offsetRef.current;
      const params: Record<string, any> = { limit: 50, offset };
      if (filters.seller_id) params.seller_id = filters.seller_id;
      if (filters.event_type) params.event_type = filters.event_type;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;

      const res = await api.get('/admin/core/team-activity/feed', { params });
      const data = res.data;

      if (reset) {
        setFeedItems(data.items || []);
        offsetRef.current = (data.items || []).length;
      } else {
        setFeedItems(prev => [...prev, ...(data.items || [])]);
        offsetRef.current += (data.items || []).length;
      }
      setTotal(data.total || 0);
      setHasMore(data.has_more || false);
    } catch (err: any) {
      setError(err.message || 'Error cargando actividad');
    }
  }, [filters]);

  // Fetch seller statuses
  const fetchSellers = useCallback(async () => {
    try {
      const res = await api.get('/admin/core/team-activity/seller-status');
      setSellers(res.data.sellers || []);
    } catch {
      // Non-critical
    }
  }, []);

  // Fetch alerts
  const fetchAlerts = useCallback(async () => {
    try {
      const res = await api.get('/admin/core/team-activity/alerts');
      setAlerts(res.data.alerts || []);
    } catch {
      // Non-critical
    }
  }, []);

  // Initial load
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await Promise.all([fetchFeed(true), fetchSellers(), fetchAlerts()]);
      setLoading(false);
    };
    load();
  }, [fetchFeed, fetchSellers, fetchAlerts]);

  // WebSocket subscription
  useEffect(() => {
    if (!socket || !isConnected || !tenantId || user?.role !== 'ceo') return;

    socket.emit('subscribe_team_activity', { tenant_id: tenantId, role: user.role });

    const handleNewEvent = (event: ActivityEvent) => {
      setFeedItems(prev => [event, ...prev]);
      setTotal(prev => prev + 1);
      // Refresh seller statuses when new activity arrives
      fetchSellers();
    };

    const handleSellerStatusChanged = (data: any) => {
      setSellers(prev =>
        prev.map(s => s.user_id === data.seller_id ? { ...s, status: data.status, last_activity_at: data.last_activity_at } : s)
      );
    };

    const handleNewAlert = (alert: InactiveLeadAlert) => {
      setAlerts(prev => [alert, ...prev]);
    };

    socket.on('team_activity:new_event', handleNewEvent);
    socket.on('team_activity:seller_status_changed', handleSellerStatusChanged);
    socket.on('team_activity:new_alert', handleNewAlert);

    return () => {
      socket.emit('unsubscribe_team_activity', { tenant_id: tenantId });
      socket.off('team_activity:new_event', handleNewEvent);
      socket.off('team_activity:seller_status_changed', handleSellerStatusChanged);
      socket.off('team_activity:new_alert', handleNewAlert);
    };
  }, [socket, isConnected, tenantId, user?.role, fetchSellers]);

  // Refresh alerts every 2 minutes
  useEffect(() => {
    const interval = setInterval(fetchAlerts, 120_000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const loadMore = () => {
    if (hasMore) fetchFeed(false);
  };

  const applyFilters = (newFilters: Filters) => {
    setFilters(newFilters);
    offsetRef.current = 0;
  };

  return {
    feedItems,
    sellers,
    alerts,
    loading,
    error,
    total,
    hasMore,
    loadMore,
    filters,
    applyFilters,
    refresh: () => {
      fetchFeed(true);
      fetchSellers();
      fetchAlerts();
    },
  };
}
