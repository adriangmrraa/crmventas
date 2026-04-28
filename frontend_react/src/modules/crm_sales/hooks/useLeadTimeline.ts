/**
 * useLeadTimeline — DEV-45: Infinite-scroll hook for the unified lead timeline.
 * Fetches from GET /admin/core/crm/leads/{leadId}/timeline with cursor pagination.
 * Subscribes to Socket.IO room lead:{leadId} for real-time prepend.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useSocket } from '../../../context/SocketContext';
import api from '../../../api/axios';

export interface TimelineActor {
  id: string | null;
  name: string;
  role: string;
}

export interface TimelineContent {
  summary: string;
  detail: string | null;
  structured: Record<string, any> | null;
}

export interface TimelineEvent {
  id: string;
  event_type: string;
  timestamp: string;
  actor: TimelineActor;
  content: TimelineContent;
  visibility: 'public' | 'internal' | 'private';
  source_table: string;
  source_id: string;
  metadata: Record<string, any>;
}

interface TimelineResponse {
  lead: {
    id: string;
    name: string;
    phone_number: string;
    status: string;
  };
  items: TimelineEvent[];
  pagination: {
    next_cursor: string | null;
    has_more: boolean;
  };
}

interface UseLeadTimelineOptions {
  leadId: string;
  types?: string[];
}

const PAGE_SIZE = 20;

export function useLeadTimeline({ leadId, types }: UseLeadTimelineOptions) {
  const { socket, isConnected } = useSocket();

  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isFetchingMore, setIsFetchingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cursorRef = useRef<string | null>(null);
  const isMountedRef = useRef(true);

  const typesParam = types && types.length > 0 ? types.join(',') : undefined;

  const fetchPage = useCallback(
    async (reset = false) => {
      if (reset) {
        setIsLoading(true);
        cursorRef.current = null;
      } else {
        setIsFetchingMore(true);
      }

      try {
        setError(null);
        const params: Record<string, string | number> = { limit: PAGE_SIZE };
        if (typesParam) params.types = typesParam;
        if (!reset && cursorRef.current) params.cursor = cursorRef.current;

        const res = await api.get<TimelineResponse>(
          `/admin/core/crm/leads/${leadId}/timeline`,
          { params },
        );

        if (!isMountedRef.current) return;

        const data = res.data;
        const newItems = data.items || [];
        cursorRef.current = data.pagination.next_cursor ?? null;

        if (reset) {
          setEvents(newItems);
        } else {
          setEvents((prev) => [...prev, ...newItems]);
        }
        setHasMore(data.pagination.has_more);
      } catch (err: any) {
        if (!isMountedRef.current) return;
        setError(err.response?.data?.detail || 'Error al cargar el timeline');
      } finally {
        if (!isMountedRef.current) return;
        if (reset) setIsLoading(false);
        else setIsFetchingMore(false);
      }
    },
    [leadId, typesParam],
  );

  // Initial load + refetch when leadId or types change
  useEffect(() => {
    isMountedRef.current = true;
    fetchPage(true);
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchPage]);

  // Socket.IO real-time subscription
  useEffect(() => {
    if (!socket || !isConnected) return;

    // Join the lead room
    socket.emit('join_lead_room', { lead_id: leadId });

    const handleNewEvent = (data: { lead_id: string; event: TimelineEvent }) => {
      if (data.lead_id !== leadId) return;
      const incoming = data.event;
      setEvents((prev) => {
        // Deduplicate by id
        if (prev.some((e) => e.id === incoming.id)) return prev;
        // Prepend (most recent first)
        return [incoming, ...prev];
      });
    };

    socket.on('lead_timeline:new_event', handleNewEvent);

    return () => {
      socket.emit('leave_lead_room', { lead_id: leadId });
      socket.off('lead_timeline:new_event', handleNewEvent);
    };
  }, [socket, isConnected, leadId]);

  const fetchNextPage = useCallback(() => {
    if (!isFetchingMore && hasMore) {
      fetchPage(false);
    }
  }, [fetchPage, isFetchingMore, hasMore]);

  const refetch = useCallback(() => {
    fetchPage(true);
  }, [fetchPage]);

  return {
    events,
    isLoading,
    isFetchingMore,
    hasMore,
    error,
    fetchNextPage,
    refetch,
  };
}
