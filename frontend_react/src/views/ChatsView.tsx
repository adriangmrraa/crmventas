import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  MessageCircle, Send, Calendar, User, Activity,
  Pause, Play, AlertCircle, Clock, ChevronLeft,
  Search, XCircle, Bell, Volume2, VolumeX,
  UserPlus, Users, Target, Zap, Crown, Bot, RefreshCw, X,
  Tag, Star, HandMetal, Shield, FileText, Instagram, Facebook
} from 'lucide-react';
import api, { BACKEND_URL } from '../api/axios';
import { parseTags } from '../utils/parseTags';
import { useTranslation } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { io, Socket } from 'socket.io-client';
import SellerBadge from '../components/SellerBadge';
import SellerSelector from '../components/SellerSelector';
import AssignmentHistory from '../components/AssignmentHistory';
import { TagBadge, type LeadTag } from '../components/leads/TagBadge';
import HsmTemplatePanel from '../components/chat/HsmTemplatePanel';

// ============================================
// INTERFACES
// ============================================

interface TenantOption {
  id: number;
  clinic_name: string; // kept as clinic_name for API compatibility
}

interface ChatSession {
  phone_number: string;
  tenant_id: number;
  lead_id?: number;
  lead_name?: string;
  last_message: string;
  last_message_time: string;
  unread_count: number;
  status: 'active' | 'human_handling' | 'paused' | 'silenced';
  human_override_until?: string;
  urgency_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  last_derivhumano_at?: string;
  is_window_open?: boolean;
  last_user_message_time?: string;
  // Channel: whatsapp | instagram | facebook
  channel?: 'whatsapp' | 'instagram' | 'facebook';
  // AI agent activity fields
  tags?: string[];
  handoff_requested?: boolean;
  assigned_human_id?: string | null;
}

interface ChatMessage {
  id: number;
  from_number: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  is_derivhumano?: boolean;
}

/** Contexto del lead para panel CRM (GET /admin/core/crm/leads/phone/{phone}/context) */
interface LeadContext {
  lead: {
    id: string;
    first_name?: string;
    last_name?: string;
    phone_number?: string;
    status?: string;
    email?: string;
    assigned_seller_id?: string;
    assignment_history?: any[];
    tags?: string[];
    score?: number;
  } | null;
  upcoming_event: {
    id: string;
    title: string;
    date: string;
    end_datetime?: string;
    status?: string;
  } | null;
  last_event: {
    id: string;
    title: string;
    date: string;
    status?: string;
  } | null;
  upcoming_meetings?: {
    id: string;
    title: string;
    date: string;
    status?: string;
  }[];
  handoff_requested?: boolean;
  handoff_reason?: string;
  is_guest: boolean;
}

/** AI activity system messages shown inline in the chat */
interface AIActivityEvent {
  id: string;
  type: 'tag_assigned' | 'meeting_scheduled' | 'lead_qualified' | 'handoff_requested';
  message: string;
  timestamp: string;
}

// Tag color mapping for common CRM tags
const TAG_COLORS: Record<string, string> = {
  caliente: '#ef4444',
  tibio: '#f59e0b',
  frio: '#3b82f6',
  interesado: '#10b981',
  no_interesado: '#6b7280',
  seguimiento: '#8b5cf6',
  urgente: '#dc2626',
  vip: '#d97706',
  nuevo: '#06b6d4',
  contactado: '#14b8a6',
  cerrado: '#22c55e',
  perdido: '#ef4444',
};

const getTagColor = (tagName: string): string => {
  const normalized = tagName.toLowerCase().replace(/\s+/g, '_');
  return TAG_COLORS[normalized] || '#6b7280';
};

/** Score display helper */
const getScoreConfig = (score: number) => {
  if (score >= 80) return { label: 'Muy calificado', color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20' };
  if (score >= 60) return { label: 'Calificado', color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20' };
  if (score >= 40) return { label: 'Tibio', color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' };
  if (score >= 20) return { label: 'Bajo interes', color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/20' };
  return { label: 'Sin calificar', color: 'text-white/40', bg: 'bg-white/[0.02]', border: 'border-white/[0.06]' };
};

interface SellerAssignment {
  assigned_seller_id?: string;
  assigned_at?: string;
  assigned_by?: string;
  assignment_source?: string;
  seller_first_name?: string;
  seller_last_name?: string;
  seller_role?: string;
  assigned_by_first_name?: string;
  assigned_by_last_name?: string;
}

interface Toast {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
}

// ============================================

export default function ChatsView() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  // Empresas / Sedes (CEO puede tener varias; vendedor una)
  const [clinics, setClinics] = useState<TenantOption[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<number | null>(null);
  // Estados principales
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [leadContext, setLeadContext] = useState<LeadContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [messageOffset, setMessageOffset] = useState(0);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // Seller assignment states
  const [sellerAssignment, setSellerAssignment] = useState<SellerAssignment | null>(null);
  const [showSellerSelector, setShowSellerSelector] = useState(false);
  const [assigningSeller, setAssigningSeller] = useState(false);
  const { user } = useAuth();

  // AI activity events (inline system messages in chat)
  const [aiActivityEvents, setAiActivityEvents] = useState<AIActivityEvent[]>([]);

  // Estados de UI
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [showToast, setShowToast] = useState<Toast | null>(null);
  const [highlightedSession, setHighlightedSession] = useState<string | null>(null);
  const [showMobileContext, setShowMobileContext] = useState(false);
  const [showHsmPanel, setShowHsmPanel] = useState(false);
  const [channelFilter, setChannelFilter] = useState<'all' | 'whatsapp' | 'instagram' | 'facebook'>('all');

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const socketRef = useRef<Socket | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // ============================================
  // WEBSOCKET - CONEXIÓN EN TIEMPO REAL
  // ============================================

  useEffect(() => {
    // Conectar al WebSocket
    socketRef.current = io(BACKEND_URL);

    // Evento: Nueva derivación humana (derivhumano) — solo para la empresa seleccionada
    socketRef.current.on('HUMAN_HANDOFF', (data: { phone_number: string; reason: string; tenant_id?: number }) => {
      if (data.tenant_id != null && selectedTenantId != null && data.tenant_id !== selectedTenantId) return;
      setSessions(prev => prev.map(s =>
        s.phone_number === data.phone_number
          ? {
            ...s,
            status: 'human_handling' as const,
            human_override_until: new Date(Date.now() + 86400000).toISOString(),
            last_derivhumano_at: new Date().toISOString()
          }
          : s
      ));

      // Resaltar el chat en la lista

      // Evento: Asignación de vendedor actualizada
      socketRef.current.on('SELLER_ASSIGNMENT_UPDATED', (data: {
        phone_number: string;
        seller_id: string;
        seller_name: string;
        seller_role: string;
        assigned_by: string;
        source: string;
        tenant_id?: number
      }) => {
        if (data.tenant_id != null && selectedTenantId != null && data.tenant_id !== selectedTenantId) return;

        // Si es la conversación actual, actualizar la asignación
        if (selectedSession?.phone_number === data.phone_number) {
          setSellerAssignment({
            assigned_seller_id: data.seller_id,
            seller_first_name: data.seller_name.split(' ')[0],
            seller_last_name: data.seller_name.split(' ').slice(1).join(' '),
            seller_role: data.seller_role,
            assigned_by: data.assigned_by,
            assignment_source: data.source,
            assigned_at: new Date().toISOString()
          });
        }

        // Mostrar notificación
        setShowToast({
          id: Date.now().toString(),
          type: 'info',
          title: 'Asignación actualizada',
          message: `${data.phone_number} asignado a ${data.seller_name}`
        });
      });
      setHighlightedSession(data.phone_number);
      setTimeout(() => setHighlightedSession(null), 5000);

      // Mostrar toast (idioma según selector)
      setShowToast({
        id: Date.now().toString(),
        type: 'warning',
        title: '🔔 ' + t('chats.toast_handoff_title'),
        message: `${t('chats.toast_handoff_message_prefix')} ${data.phone_number}: ${data.reason}`,
      });

      // Reproducir sonido
      if (soundEnabled) {
        playNotificationSound();
      }
    });

    // Evento: Nuevo mensaje en chat (tenant_id opcional; si viene, solo actualizar si es la empresa seleccionada)
    socketRef.current.on('NEW_MESSAGE', (data: { phone_number: string; message: string; role: string; tenant_id?: number }) => {
      if (data.tenant_id != null && selectedTenantId != null && data.tenant_id !== selectedTenantId) return;
      setSessions(prev => {
        const updatedSessions = prev.map(s =>
          s.phone_number === data.phone_number
            ? {
              ...s,
              last_message: data.message,
              last_message_time: new Date().toISOString(),
              unread_count: s.phone_number === selectedSession?.phone_number ? 0 : s.unread_count + 1,
              is_window_open: data.role === 'user' ? true : s.is_window_open
            }
            : s
        );

        // Re-ordenar: último mensaje arriba
        const sortedSessions = [...updatedSessions].sort((a, b) => {
          const timeA = new Date(a.last_message_time || 0).getTime();
          const timeB = new Date(b.last_message_time || 0).getTime();
          return timeB - timeA;
        });

        // Si la sesión seleccionada recibió un mensaje, actualizarla para refrescar la UI (banner/input)
        if (data.phone_number === selectedSession?.phone_number) {
          const current = sortedSessions.find(s => s.phone_number === data.phone_number);
          if (current) {
            setSelectedSession(current);
          }
        }

        return sortedSessions;
      });

      // Si es del chat seleccionado, agregar mensaje si no existe
      if (data.phone_number === selectedSession?.phone_number) {
        setMessages(prev => {
          // Evitar duplicados (chequeo simple por contenido y timestamp reciente o id si viniera)
          const isDuplicate = prev.some(m =>
            m.role === data.role &&
            m.content === data.message &&
            new Date(m.created_at).getTime() > Date.now() - 5000
          );

          if (isDuplicate) return prev;

          return [...prev, {
            id: Date.now(), // ID temporal
            role: data.role as 'user' | 'assistant' | 'system',
            content: data.message,
            created_at: new Date().toISOString(),
            from_number: data.phone_number
          }];
        });
      }
    });

    // Evento: Estado de override cambiado (por empresa: solo actualizar si es la empresa seleccionada)
    socketRef.current.on('HUMAN_OVERRIDE_CHANGED', (data: { phone_number: string; enabled: boolean; until?: string; tenant_id?: number }) => {
      if (data.tenant_id != null && selectedTenantId != null && data.tenant_id !== selectedTenantId) return;
      setSessions(prev => {
        const updated = prev.map(s =>
          s.phone_number === data.phone_number
            ? {
              ...s,
              status: data.enabled ? 'silenced' as const : 'active' as const,
              human_override_until: data.until
            }
            : s
        );

        // Sincronizar selectedSession si es el actual
        if (selectedSession?.phone_number === data.phone_number) {
          const current = updated.find(s => s.phone_number === data.phone_number);
          if (current) setSelectedSession(current);
        }

        return updated;
      });
    });

    // Evento: Chat seleccionado actualizado (para sincronización)
    socketRef.current.on('CHAT_UPDATED', (data: Partial<ChatSession> & { phone_number: string }) => {
      setSessions(prev => {
        const updated = prev.map(s =>
          s.phone_number === data.phone_number ? { ...s, ...data } : s
        );

        // Sincronizar selectedSession si es el actual
        if (selectedSession?.phone_number === data.phone_number) {
          const current = updated.find(s => s.phone_number === data.phone_number);
          if (current) setSelectedSession(current);
        }

        return updated;
      });
    });

    // Evento: Lead actualizado (urgencia, etc)
    socketRef.current.on('PATIENT_UPDATED', (data: { phone_number: string; urgency_level: string }) => {
      if (selectedSession?.phone_number === data.phone_number) {
        fetchLeadContext(data.phone_number);
      }

      setSessions(prev => prev.map(s =>
        s.phone_number === data.phone_number
          ? { ...s, urgency_level: data.urgency_level as any }
          : s
      ));
    });

    // Evento: Nuevo turno agendado (refrescar contexto)
    socketRef.current.on('NEW_APPOINTMENT', (data: { phone_number: string }) => {
      if (selectedSession?.phone_number === data.phone_number) {
        fetchLeadContext(data.phone_number);
      }

      // Mostrar toast si el turno es nuevo (idioma según selector)
      setShowToast({
        id: Date.now().toString(),
        type: 'success',
        title: '📅 ' + t('chats.toast_new_appointment_title'),
        message: `${t('chats.toast_new_appointment_message_prefix')} ${data.phone_number}`,
      });
    });

    // Evento: Etiqueta asignada por IA
    socketRef.current.on('AI_TAG_ASSIGNED', (data: { phone_number: string; tag: string; tenant_id?: number }) => {
      if (data.tenant_id != null && selectedTenantId != null && data.tenant_id !== selectedTenantId) return;

      // Update session tags
      setSessions(prev => prev.map(s =>
        s.phone_number === data.phone_number
          ? { ...s, tags: [...(s.tags || []).filter(t => t !== data.tag), data.tag] }
          : s
      ));

      // Add inline AI activity event if viewing this conversation
      if (selectedSession?.phone_number === data.phone_number) {
        setAiActivityEvents(prev => [...prev, {
          id: `tag-${Date.now()}`,
          type: 'tag_assigned',
          message: `Etiqueta '${data.tag}' asignada automaticamente`,
          timestamp: new Date().toISOString(),
        }]);
        fetchLeadContext(data.phone_number);
      }
    });

    // Evento: Lead calificado por IA (score update)
    socketRef.current.on('LEAD_QUALIFIED', (data: { phone_number: string; score: number; tenant_id?: number }) => {
      if (data.tenant_id != null && selectedTenantId != null && data.tenant_id !== selectedTenantId) return;

      if (selectedSession?.phone_number === data.phone_number) {
        setAiActivityEvents(prev => [...prev, {
          id: `qual-${Date.now()}`,
          type: 'lead_qualified',
          message: `Lead calificado con score ${data.score}/100`,
          timestamp: new Date().toISOString(),
        }]);
        fetchLeadContext(data.phone_number);
      }
    });

    // Evento: Handoff solicitado por IA
    socketRef.current.on('HANDOFF_REQUESTED', (data: { phone_number: string; reason: string; tenant_id?: number }) => {
      if (data.tenant_id != null && selectedTenantId != null && data.tenant_id !== selectedTenantId) return;

      setSessions(prev => prev.map(s =>
        s.phone_number === data.phone_number
          ? { ...s, handoff_requested: true }
          : s
      ));

      if (selectedSession?.phone_number === data.phone_number) {
        setAiActivityEvents(prev => [...prev, {
          id: `handoff-${Date.now()}`,
          type: 'handoff_requested',
          message: `IA solicita handoff: ${data.reason}`,
          timestamp: new Date().toISOString(),
        }]);
        fetchLeadContext(data.phone_number);
      }

      setShowToast({
        id: Date.now().toString(),
        type: 'warning',
        title: 'Handoff solicitado',
        message: `IA solicita atencion humana para ${data.phone_number}: ${data.reason}`,
      });

      if (soundEnabled) playNotificationSound();
    });

    // Evento: Reunion agendada por IA
    socketRef.current.on('AI_MEETING_SCHEDULED', (data: { phone_number: string; title: string; date: string; tenant_id?: number }) => {
      if (data.tenant_id != null && selectedTenantId != null && data.tenant_id !== selectedTenantId) return;

      if (selectedSession?.phone_number === data.phone_number) {
        setAiActivityEvents(prev => [...prev, {
          id: `meeting-${Date.now()}`,
          type: 'meeting_scheduled',
          message: `Reunion '${data.title}' agendada para ${new Date(data.date).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}`,
          timestamp: new Date().toISOString(),
        }]);
        fetchLeadContext(data.phone_number);
      }
    });

    // Cleanup
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [selectedSession, soundEnabled, selectedTenantId, t]);

  // ============================================
  // DATOS - CARGAR EMPRESAS, SESIONES Y MENSAJES
  // ============================================

  useEffect(() => {
    api.get<TenantOption[]>('/admin/core/chat/tenants').then((res) => {
      setClinics(res.data);
      if (res.data.length >= 1) setSelectedTenantId(res.data[0].id);
    }).catch(() => setClinics([]));
  }, []);

  useEffect(() => {
    if (selectedTenantId != null) fetchSessions(selectedTenantId, location.state?.selectPhone, navigate);
    else setSessions([]);
  }, [selectedTenantId, location.state?.selectPhone, navigate]);

  useEffect(() => {
    if (selectedSession) {
      setLeadContext(null);
      fetchMessages(selectedSession.phone_number, selectedSession.tenant_id);
      fetchLeadContext(selectedSession.phone_number, selectedSession.tenant_id);
      markAsRead(selectedSession.phone_number, selectedSession.tenant_id);
      // Cargar asignación de vendedor
      loadSellerAssignment(selectedSession.phone_number);
    } else {
      setLeadContext(null);
      setSellerAssignment(null);
    }
  }, [selectedSession]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ============================================
  // FUNCIONES DE DATOS - ASIGNACIÓN DE VENDEDORES
  // ============================================

  /** Carga la asignación de vendedor para una conversación */
  const loadSellerAssignment = async (phone: string) => {
    if (!selectedTenantId) return;

    try {
      const response = await api.get(`/admin/core/sellers/conversations/${phone}/assignment`);

      if (response.data.success && response.data.assignment) {
        setSellerAssignment(response.data.assignment);
      } else {
        setSellerAssignment(null);
      }
    } catch (err: any) {
      console.error('Error loading seller assignment:', err);
      setSellerAssignment(null);
    }
  };

  /** Asigna un vendedor a la conversación actual */
  const handleAssignSeller = async (sellerId: string, sellerName: string) => {
    if (!selectedSession || !selectedTenantId || !user?.id) return;

    try {
      setAssigningSeller(true);

      const response = await api.post('/admin/core/sellers/conversations/assign', {
        phone: selectedSession.phone_number,
        seller_id: sellerId,
        source: 'manual'
      });

      if (response.data.success) {
        // Actualizar la asignación localmente
        await loadSellerAssignment(selectedSession.phone_number);

        // Actualizar lead context si existe
        if (leadContext?.lead) {
          const updatedLead = { ...leadContext.lead, assigned_seller_id: sellerId };
          setLeadContext({ ...leadContext, lead: updatedLead });
        }

        // Cerrar el selector
        setShowSellerSelector(false);

        // Mostrar notificación
        setShowToast({
          id: Date.now().toString(),
          type: 'success',
          title: 'Asignación exitosa',
          message: `Conversación asignada a: ${sellerName}`
        });
      } else {
        throw new Error(response.data.message);
      }
    } catch (err: any) {
      console.error('Error assigning seller:', err);
      setShowToast({
        id: Date.now().toString(),
        type: 'error',
        title: 'Error de asignación',
        message: err.response?.data?.detail || err.message
      });
    } finally {
      setAssigningSeller(false);
    }
  };

  /** Asignación automática */
  const handleAutoAssign = async () => {
    if (!selectedSession || !selectedTenantId) return;

    try {
      setAssigningSeller(true);

      const response = await api.post(`/admin/core/sellers/conversations/${selectedSession.phone_number}/auto-assign`);

      if (response.data.success) {
        await loadSellerAssignment(selectedSession.phone_number);

        setShowToast({
          id: Date.now().toString(),
          type: 'success',
          title: 'Asignación automática',
          message: 'Conversación asignada automáticamente'
        });
      } else {
        throw new Error(response.data.message);
      }
    } catch (err: any) {
      console.error('Error auto assigning:', err);
      setShowToast({
        id: Date.now().toString(),
        type: 'error',
        title: 'Error de asignación',
        message: err.response?.data?.detail || err.message
      });
    } finally {
      setAssigningSeller(false);
    }
  };

  // ============================================
  // FUNCIONES DE DATOS
  // ============================================

  const fetchSessions = async (tenantId: number, selectPhone?: string, nav?: ReturnType<typeof useNavigate>) => {
    try {
      setLoading(true);
      const response = await api.get<ChatSession[]>('/admin/core/chat/sessions', { params: { tenant_id: tenantId } });
      setSessions(response.data);
      // Al abrir desde notificación de derivación, seleccionar ese chat (state viene de Layout al hacer clic en el toast)
      if (selectPhone) {
        const targetSession = response.data.find((s: ChatSession) => s.phone_number === selectPhone);
        if (targetSession) {
          setSelectedSession(targetSession);
          nav?.('/chats', { replace: true, state: {} });
        }
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
      setSessions([]);
      setShowToast({
        id: Date.now().toString(),
        type: 'error',
        title: t('chats.error_connection_title'),
        message: t('chats.error_connection_message'),
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (phone: string, tenantId: number, append: boolean = false) => {
    if (!selectedSession) return;
    try {
      const currentOffset = append ? messageOffset + 50 : 0;
      const response = await api.get(`/admin/core/chat/messages/${phone}`, {
        params: { tenant_id: tenantId, limit: 50, offset: currentOffset }
      });

      const newBatch = response.data;

      if (append) {
        setMessages(prev => [...newBatch, ...prev]);
        setMessageOffset(currentOffset);
      } else {
        setMessages(newBatch);
        setMessageOffset(0);
        scrollToBottom();
      }

      setHasMoreMessages(newBatch.length === 50);
    } catch (error) {
      console.error('Error fetching messages:', error);
      if (!append) setMessages([]);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleLoadMore = () => {
    if (!selectedSession || loadingMore || !hasMoreMessages) return;
    setLoadingMore(true);
    fetchMessages(selectedSession.phone_number, selectedSession.tenant_id, true);
  };

  const fetchLeadContext = async (phone: string, tenantId?: number) => {
    try {
      const params = tenantId != null ? { tenant_id_override: tenantId } : {};
      const response = await api.get(`/admin/core/crm/leads/phone/${encodeURIComponent(phone)}/context`, { params });
      setLeadContext(response.data);
    } catch (error) {
      console.error('Error fetching lead context:', error);
      setLeadContext(null);
    }
  };

  const markAsRead = async (phone: string, tenantId: number) => {
    try {
      await api.put(`/admin/core/chat/sessions/${phone}/read`, null, { params: { tenant_id: tenantId } });
      setSessions(prev => prev.map(s =>
        s.phone_number === phone && s.tenant_id === tenantId ? { ...s, unread_count: 0 } : s
      ));
    } catch (error) {
      console.error('Error marking as read:', error);
    }
  };

  // ============================================
  // ACCIONES
  // ============================================

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedSession) return;

    const messageText = newMessage;
    const channel = selectedSession.channel || 'whatsapp';

    // Optimistic update: add message to local state immediately
    const optimisticMsg: ChatMessage = {
      id: Date.now(),
      from_number: 'me',
      role: 'assistant',
      content: messageText,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, optimisticMsg]);
    setNewMessage('');

    setSending(true);
    try {
      await api.post('/admin/core/chat/send', {
        phone: selectedSession.phone_number,
        tenant_id: selectedSession.tenant_id,
        message: messageText,
        channel,
      });

      setShowToast({
        id: Date.now().toString(),
        type: 'success',
        title: 'Mensaje enviado',
        message: `Enviado por ${getChannelLabel(channel)}`,
      });

      socketRef.current?.emit('MANUAL_MESSAGE', {
        phone: selectedSession.phone_number,
        tenant_id: selectedSession.tenant_id,
        message: messageText,
        channel,
      });
    } catch (error: any) {
      console.error('Error sending message:', error);
      // Remove optimistic message on failure
      setMessages(prev => prev.filter(m => m.id !== optimisticMsg.id));
      setNewMessage(messageText); // Restore the message text
      setShowToast({
        id: Date.now().toString(),
        type: 'error',
        title: 'Error al enviar',
        message: error.response?.data?.detail || 'No se pudo enviar el mensaje',
      });
    } finally {
      setSending(false);
    }
  };

  const handleToggleHumanMode = async () => {
    if (!selectedSession) return;

    const isCurrentlyHandled = selectedSession.status === 'human_handling' || selectedSession.status === 'silenced';
    const activate = !isCurrentlyHandled;

    try {
      await api.post('/admin/core/chat/human-intervention', {
        phone: selectedSession.phone_number,
        tenant_id: selectedSession.tenant_id,
        activate,
        duration: 24 * 60 * 60 * 1000, // 24 horas
      });

      // Actualización local inmediata para respuesta instantánea
      const until = activate ? new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() : undefined;
      const updatedStatus = activate ? 'silenced' as const : 'active' as const;

      const updateFn = (s: ChatSession) => s.phone_number === selectedSession.phone_number
        ? { ...s, status: updatedStatus, human_override_until: until }
        : s;

      setSessions(prev => prev.map(updateFn));
      setSelectedSession(prev => prev ? updateFn(prev) : null);

      // El evento socket redundante HUMAN_OVERRIDE_TOGGLE ya es manejado por el backend emitiendo HUMAN_OVERRIDE_CHANGED
    } catch (error) {
      console.error('Error toggling human mode:', error);
    }
  };

  const handleRemoveSilence = async () => {
    if (!selectedSession || !selectedSession.human_override_until) return;

    try {
      await api.post('/admin/core/chat/remove-silence', {
        phone: selectedSession.phone_number,
        tenant_id: selectedSession.tenant_id,
      });

      // Actualización local inmediata
      const updateFn = (s: ChatSession) => s.phone_number === selectedSession.phone_number
        ? { ...s, status: 'active' as const, human_override_until: undefined, last_derivhumano_at: undefined }
        : s;

      setSessions(prev => prev.map(updateFn));
      setSelectedSession(prev => prev ? updateFn(prev) : null);
    } catch (error) {
      console.error('Error removing silence:', error);
    }
  };

  const playNotificationSound = () => {
    if (audioRef.current) {
      audioRef.current.play().catch(() => { });
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // ============================================
  // UTILIDADES
  // ============================================

  const filteredSessions = sessions.filter(session => {
    const matchesSearch = session.lead_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      session.phone_number.includes(searchTerm);
    const matchesChannel = channelFilter === 'all' || (session.channel || 'whatsapp') === channelFilter;
    return matchesSearch && matchesChannel;
  });

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) return 'Ahora';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
    return date.toLocaleDateString();
  };

  /** Channel icon helper */
  const ChannelIcon = ({ channel, size = 14 }: { channel?: string; size?: number }) => {
    switch (channel) {
      case 'instagram':
        return <Instagram size={size} className="text-purple-400" />;
      case 'facebook':
        return <Facebook size={size} className="text-blue-400" />;
      case 'whatsapp':
      default:
        return <MessageCircle size={size} className="text-green-400" />;
    }
  };

  const getChannelLabel = (channel?: string) => {
    switch (channel) {
      case 'instagram': return 'Instagram';
      case 'facebook': return 'Facebook';
      case 'whatsapp':
      default: return 'WhatsApp';
    }
  };

  const getStatusConfig = (session: ChatSession) => {
    if (session.status === 'human_handling' || session.status === 'silenced') {
      return {
        badge: (
          <span className="flex items-center gap-1 text-xs font-medium">
            {session.status === 'silenced' ? (
              <VolumeX size={12} className="text-red-500" />
            ) : (
              <User size={12} className="text-orange-500" />
            )}
            {session.status === 'silenced' ? t('chats.silenced') : t('chats.manual')}
          </span>
        ),
        avatarBg: session.urgency_level === 'HIGH' || session.urgency_level === 'CRITICAL'
          ? 'bg-red-500 animate-pulse'
          : 'bg-orange-500',
        cardBorder: session.last_derivhumano_at ? 'border-l-4 border-orange-500' : '',
      };
    }
    return {
      badge: (
        <span className="flex items-center gap-1 text-xs text-green-400">
          <Activity size={12} /> IA Activa
        </span>
      ),
      avatarBg: 'bg-primary',
      cardBorder: '',
    };
  };


  // ============================================
  // RENDER
  // ============================================

  return (
    <div className="flex h-full min-h-0 bg-blue-500/10 overflow-hidden font-sans">
      {/* Audio para notificaciones */}
      <audio ref={audioRef} src="/notification.mp3" preload="auto" />

      {/* ======================================== */}
      {/* TOAST DE DERIVACIÓN HUMANA */}
      {/* ======================================== */}
      {showToast && (
        <div className="fixed top-4 right-4 z-50 animate-slide-in">
          <div className="bg-orange-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3">
            <Bell className="w-5 h-5" />
            <div>
              <p className="font-semibold">{showToast.title}</p>
              <p className="text-sm opacity-90">{showToast.message}</p>
            </div>
            <button
              onClick={() => setShowToast(null)}
              className="ml-4 hover:opacity-80"
            >
              <XCircle size={18} />
            </button>
          </div>
        </div>
      )}

      {/* Chat List */}
      <div className={`
        ${selectedSession ? 'hidden lg:flex' : 'flex'} 
        w-full lg:w-80 border-r bg-white/[0.03] flex-col
      `}>
        <div className="p-4 border-b">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-bold">{t('chats.title')}</h2>
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              className="p-2 rounded-lg hover:bg-white/[0.04]"
              title={soundEnabled ? t('chats.mute_sound') : t('chats.enable_sound')}
            >
              {soundEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
            </button>
          </div>
          {clinics.length > 1 && (
            <div className="mb-3">
              <label className="block text-xs font-medium text-white/40 mb-1">{t('chats.tenant_label')}</label>
              <select
                value={selectedTenantId ?? ''}
                onChange={(e) => setSelectedTenantId(Number(e.target.value))}
                className="w-full px-3 py-2 border border-white/[0.06] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-white/[0.03]"
              >
                {clinics.map((c) => (
                  <option key={c.id} value={c.id}>{c.clinic_name}</option>
                ))}
              </select>
            </div>
          )}
          {clinics.length === 1 && clinics[0] && (
            <p className="text-xs text-white/40 mb-2">{clinics[0].clinic_name}</p>
          )}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" size={16} />
            <input
              type="text"
              placeholder={t('chats.search_placeholder')}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Channel Filter Tabs */}
          <div className="flex gap-1 px-1 py-2 border-t border-white/[0.04]">
            {([
              { id: 'all' as const, label: 'Todos', icon: null },
              { id: 'whatsapp' as const, label: 'WA', icon: <MessageCircle size={12} className="text-green-400" /> },
              { id: 'instagram' as const, label: 'IG', icon: <Instagram size={12} className="text-purple-400" /> },
              { id: 'facebook' as const, label: 'FB', icon: <Facebook size={12} className="text-blue-400" /> },
            ]).map(tab => (
              <button
                key={tab.id}
                onClick={() => setChannelFilter(tab.id)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all flex-1 justify-center
                  ${channelFilter === tab.id
                    ? 'bg-white/[0.08] text-white'
                    : 'text-white/30 hover:text-white/60 hover:bg-white/[0.03]'
                  }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-center text-white/40">{t('common.loading')}</div>
          ) : filteredSessions.length === 0 ? (
            <div className="p-4 text-center text-white/40">{t('chats.no_sessions')}</div>
          ) : (
            filteredSessions.map(session => {
              const { avatarBg } = getStatusConfig(session);
              const isHighlighted = highlightedSession === session.phone_number;
              const isSelected = selectedSession?.phone_number === session.phone_number;

              return (
                <div
                  key={session.phone_number}
                  onClick={() => setSelectedSession(session)}
                  className={`px-4 py-3 border-b cursor-pointer transition-all relative
                    ${isSelected ? 'bg-blue-500/10' : 'hover:bg-white/[0.02] active:bg-white/[0.04]'}
                    ${isHighlighted ? 'bg-orange-500/10 animate-pulse' : ''}
                  `}
                >
                  <div className="flex items-center gap-3">
                    {/* Avatar with Status Ring */}
                    <div className="relative shrink-0">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg ${avatarBg}`}>
                        {(session.lead_name || session.phone_number).charAt(0)}
                      </div>
                      {session.status === 'human_handling' && (
                        <div className="absolute -bottom-1 -right-1 bg-white/[0.03] p-0.5 rounded-full">
                          <User size={12} className="text-orange-500 fill-orange-500" />
                        </div>
                      )}
                      {/* Robot icon if AI-handled (no human assigned) */}
                      {session.status === 'active' && !session.assigned_human_id && (
                        <div className="absolute -bottom-1 -right-1 bg-white/[0.03] p-0.5 rounded-full">
                          <Bot size={12} className="text-cyan-400" />
                        </div>
                      )}
                      {/* Alert icon if handoff requested */}
                      {session.handoff_requested && (
                        <div className="absolute -top-1 -right-1 bg-white/[0.03] p-0.5 rounded-full">
                          <AlertCircle size={12} className="text-orange-400 fill-orange-400/20" />
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-baseline mb-0.5">
                        <span className={`font-semibold truncate flex items-center gap-1.5 ${isSelected ? 'text-white' : 'text-white'}`}>
                          <ChannelIcon channel={session.channel} size={13} />
                          {session.lead_name || session.phone_number}
                        </span>
                        <span className={`text-[11px] shrink-0 ml-2 ${session.unread_count > 0 ? 'text-blue-400 font-bold' : 'text-white/30'}`}>
                          {formatTime(session.last_message_time)}
                        </span>
                      </div>

                      <div className="flex justify-between items-center">
                        <p className={`text-sm truncate pr-4 ${session.unread_count > 0 ? 'text-white font-medium' : 'text-white/40'}`}>
                          {session.last_message || t('chats.no_messages')}
                        </p>
                        {session.unread_count > 0 && (
                          <span className="bg-medical-600 text-white text-[10px] font-bold min-w-[20px] h-5 px-1.5 rounded-full flex items-center justify-center">
                            {session.unread_count}
                          </span>
                        )}
                      </div>
                      {/* Tag colored dots row */}
                      {parseTags(session.tags).length > 0 && (
                        <div className="flex items-center gap-1 mt-1">
                          {parseTags(session.tags).slice(0, 5).map(tag => (
                            <span
                              key={tag}
                              className="w-2 h-2 rounded-full shrink-0"
                              style={{ backgroundColor: getTagColor(tag) }}
                              title={tag}
                            />
                          ))}
                          {session.tags.length > 5 && (
                            <span className="text-[10px] text-white/30">+{session.tags.length - 5}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  {/* Floating Urgency Indicator for Mobile */}
                  <div className="absolute top-3 right-4 lg:hidden">
                    {session.urgency_level === 'CRITICAL' && (
                      <div className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Chat Detail */}
      {selectedSession ? (
        <>
          <div className="flex-1 flex flex-col min-w-0 bg-white/[0.02] h-full min-h-0">
            {/* Header + Messages + Input Container */}
            <div className="flex-1 flex flex-col min-h-0 relative">
              {/* Header */}
              <div className="p-4 border-b bg-white/[0.03] flex justify-between items-center">
                <div className="flex items-center gap-3 min-w-0">
                  <button
                    onClick={() => {
                      setSelectedSession(null);
                      setShowMobileContext(false);
                    }}
                    className="lg:hidden p-2 -ml-2 hover:bg-white/[0.04] rounded-full text-white/50 active:bg-white/[0.06] transition-colors"
                  >
                    <ChevronLeft size={24} />
                  </button>
                  <div
                    onClick={() => window.innerWidth < 1280 && setShowMobileContext(!showMobileContext)}
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold shrink-0 cursor-pointer ${selectedSession.status === 'human_handling' || selectedSession.status === 'silenced'
                      ? 'bg-orange-500'
                      : 'bg-medical-600'
                      }`}
                  >
                    {(selectedSession.lead_name || selectedSession.phone_number).charAt(0)}
                  </div>
                  <div className="min-w-0 flex-1 cursor-pointer" onClick={() => window.innerWidth < 1280 && setShowMobileContext(!showMobileContext)}>
                    <div className="flex items-center gap-2">
                      <ChannelIcon channel={selectedSession.channel} size={16} />
                      <h3 className="font-bold text-white truncate leading-tight">
                        {selectedSession.lead_name || t('chats.no_name')}
                      </h3>
                      {/* Seller Badge */}
                      {sellerAssignment && (
                        <SellerBadge
                          sellerId={sellerAssignment.assigned_seller_id}
                          sellerName={sellerAssignment.seller_first_name ?
                            `${sellerAssignment.seller_first_name} ${sellerAssignment.seller_last_name}` : undefined}
                          sellerRole={sellerAssignment.seller_role}
                          assignedAt={sellerAssignment.assigned_at}
                          source={sellerAssignment.assignment_source}
                          size="sm"
                          showLabel={true}
                          onClick={() => setShowSellerSelector(true)}
                        />
                      )}
                      {!sellerAssignment?.assigned_seller_id && (
                        <div
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/[0.04] text-white/70 border border-white/[0.06] text-xs cursor-pointer hover:bg-white/[0.06]"
                          onClick={() => setShowSellerSelector(true)}
                        >
                          <Bot size={12} />
                          <span>AGENTE IA</span>
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-white/40 truncate">{selectedSession.phone_number}</p>
                  </div>
                </div>

                {/* Header Actions - Seller Assignment */}
                <div className="flex items-center gap-1 sm:gap-2">
                  {/* Assign Seller Button */}
                  <button
                    onClick={() => setShowSellerSelector(!showSellerSelector)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all
                      ${sellerAssignment?.assigned_seller_id
                        ? 'bg-blue-500/10 text-blue-400 hover:bg-blue-200 border border-blue-500/20'
                        : 'bg-white/[0.04] text-white/70 hover:bg-white/[0.06] border border-white/[0.06]'
                      }`}
                    title={sellerAssignment?.assigned_seller_id ? "Reasignar vendedor" : "Asignar vendedor"}
                  >
                    {sellerAssignment?.assigned_seller_id ? (
                      <><User size={14} /> <span className="hidden sm:inline">Reasignar</span></>
                    ) : (
                      <><UserPlus size={14} /> <span className="hidden sm:inline">Asignar</span></>
                    )}
                  </button>

                  {/* Auto Assign Button */}
                  <button
                    onClick={handleAutoAssign}
                    disabled={assigningSeller}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 hover:bg-green-200 border border-green-500/20 transition-all disabled:opacity-50"
                    title="Asignación automática"
                  >
                    {assigningSeller ? (
                      <RefreshCw size={14} className="animate-spin" />
                    ) : (
                      <><span>🤖</span> <span className="hidden sm:inline">Auto</span></>
                    )}
                  </button>
                </div>

                {/* Header Actions */}
                <div className="flex items-center gap-1 sm:gap-2">
                  <button
                    onClick={() => setShowMobileContext(!showMobileContext)}
                    className="p-2 text-blue-400 hover:bg-blue-500/10 rounded-full lg:hidden transition-colors"
                    title={t('chats.view_lead_info')}
                  >
                    <Activity size={20} />
                  </button>

                  <button
                    onClick={handleToggleHumanMode}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold transition-all
                      ${selectedSession.status === 'human_handling' || selectedSession.status === 'silenced'
                        ? 'bg-green-500/10 text-green-400 hover:bg-green-200 border border-green-500/20'
                        : 'bg-orange-500/10 text-orange-700 hover:bg-orange-200 border border-orange-500/20'
                      }`}
                  >
                    {selectedSession.status === 'human_handling' || selectedSession.status === 'silenced' ? (
                      <><Play size={14} className="fill-current" /> <span className="hidden sm:inline">{t('chats.activate_ai')}</span></>
                    ) : (
                      <><Pause size={14} className="fill-current" /> <span className="hidden sm:inline">{t('chats.manual')}</span></>
                    )}
                  </button>
                </div>
              </div>

              {/* Alert Banner para derivhumano */}
              {selectedSession.last_derivhumano_at ? (
                <div className="bg-orange-500/10 border-b border-orange-500/20 px-4 py-2 flex items-center gap-2">
                  <AlertCircle size={16} className="text-orange-500" />
                  <span className="text-sm text-orange-700">
                    ⚠️ {t('chats.handoff_banner').replace('{{time}}', new Date(selectedSession.last_derivhumano_at).toLocaleTimeString())}
                  </span>
                  <button
                    onClick={handleRemoveSilence}
                    className="ml-auto text-xs text-orange-600 hover:underline"
                  >
                    {t('chats.remove_silence')}
                  </button>
                </div>
              ) : (selectedSession.status === 'silenced' || selectedSession.status === 'human_handling') && (
                <div className="bg-blue-500/10 border-b border-blue-500/20 px-4 py-2 flex items-center gap-2">
                  <Pause size={16} className="text-blue-500" />
                  <span className="text-sm text-blue-400">
                    ✋ {t('chats.manual_mode_active')}
                  </span>
                  <button
                    onClick={handleToggleHumanMode}
                    className="ml-auto text-xs text-blue-400 hover:underline"
                  >
                    {t('chats.activate_ai')}
                  </button>
                </div>
              )}

              {/* Banner de Ventana de 24hs Cerrada */}
              {selectedSession.is_window_open === false && (
                <div className="bg-yellow-500/10 border-b border-yellow-500/20 px-4 py-2 flex items-center gap-2">
                  <Clock size={16} className="text-yellow-600" />
                  <span className="text-sm text-yellow-700">
                    ⏳ {t('chats.window_24h_closed')}
                  </span>
                </div>
              )}

              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-white/[0.02] flex flex-col min-h-0">
                {hasMoreMessages && (
                  <button
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="mx-auto py-2 px-4 text-xs text-blue-400 hover:text-medical-700 font-medium bg-white/[0.03] rounded-full border border-white/[0.06] mb-4 transition-all disabled:opacity-50 shrink-0"
                  >
                    {loadingMore ? t('common.loading') : t('chats.load_older_messages')}
                  </button>
                )}

                <div className="flex-1" /> {/* Spacer to push messages down if few */}

                {/* Merge messages + AI activity events, sorted by time */}
                {(() => {
                  // Build combined timeline of messages + AI activity events
                  const aiItems = aiActivityEvents.map(ev => ({
                    kind: 'ai_event' as const,
                    sortTime: new Date(ev.timestamp).getTime(),
                    event: ev,
                  }));
                  const msgItems = messages.map(m => ({
                    kind: 'message' as const,
                    sortTime: new Date(m.created_at).getTime(),
                    message: m,
                  }));
                  const combined = [...msgItems, ...aiItems].sort((a, b) => a.sortTime - b.sortTime);

                  return combined.map((item, idx) => {
                    if (item.kind === 'ai_event') {
                      const ev = item.event;
                      return (
                        <div key={ev.id} className="flex justify-center my-1">
                          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-xs text-purple-300">
                            <Bot size={12} className="text-purple-400" />
                            <span>{ev.message}</span>
                            <span className="text-white/30 ml-1">
                              {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        </div>
                      );
                    }

                    const message = item.message;
                    return (
                      <div
                        key={message.id}
                        className={`flex ${message.role === 'user' ? 'justify-start' : message.role === 'system' ? 'justify-center' : 'justify-end'}`}
                      >
                        {/* System messages (tag assignments, etc) */}
                        {message.role === 'system' ? (
                          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.06] text-xs text-white/50">
                            <Zap size={12} className="text-yellow-400" />
                            <span>{message.content}</span>
                            <span className="text-white/30 ml-1">
                              {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        ) : (
                          <div
                            className={`max-w-[70%] rounded-lg px-4 py-3 ${message.role === 'user'
                              ? 'bg-white/[0.03]'
                              : message.is_derivhumano
                                ? 'bg-orange-500/10 border border-orange-300 text-white'
                                : 'bg-blue-600 text-white'
                              }`}
                          >
                            {/* IA badge for assistant messages */}
                            {message.role === 'assistant' && !message.is_derivhumano && (
                              <div className="flex items-center gap-1 text-[10px] text-blue-200/60 mb-1">
                                <Bot size={10} />
                                <span className="font-medium uppercase tracking-wider">IA</span>
                              </div>
                            )}
                            {message.is_derivhumano && (
                              <div className="flex items-center gap-1 text-xs text-orange-600 mb-1">
                                <User size={12} />
                                <span className="font-medium">{t('chats.auto_handoff')}</span>
                              </div>
                            )}
                            <p className="text-sm">{message.content}</p>
                            <p className={`text-xs mt-1 ${message.role === 'user' ? 'text-white/30' : 'text-blue-200'
                              }`}>
                              {new Date(message.created_at).toLocaleTimeString()}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  });
                })()}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <form onSubmit={handleSendMessage} className="p-4 border-t bg-white/[0.03]">
                {/* Channel indicator bar */}
                <div className="flex items-center gap-2 mb-2 px-1">
                  <ChannelIcon channel={selectedSession.channel} size={12} />
                  <span className="text-[11px] text-white/30 font-medium">
                    Enviando por {getChannelLabel(selectedSession.channel)}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowHsmPanel(prev => !prev)}
                    className={`p-2 rounded-lg flex items-center justify-center transition-colors min-w-[44px] ${
                      showHsmPanel
                        ? 'bg-medical-600 text-white'
                        : 'bg-white/[0.04] text-white/50 hover:text-white hover:bg-white/[0.08]'
                    }`}
                    title="Plantillas HSM"
                  >
                    <FileText size={20} />
                  </button>
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder={selectedSession.is_window_open === false ? "Ventana cerrada - Esperando respuesta del prospecto..." : "Escribe un mensaje..."}
                    disabled={selectedSession.is_window_open === false}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage(e as any);
                      }
                    }}
                    className={`flex-1 px-4 py-2 border border-white/[0.06] rounded-lg focus:outline-none focus:ring-2 focus:ring-medical-500 bg-white/[0.03] text-white ${selectedSession.is_window_open === false ? 'bg-white/[0.04] cursor-not-allowed opacity-75' : ''}`}
                  />
                  <button
                    type="submit"
                    disabled={sending || !newMessage.trim() || selectedSession.is_window_open === false}
                    className="p-2 bg-medical-600 text-white rounded-lg hover:bg-medical-700 disabled:opacity-50 flex items-center justify-center transition-colors min-w-[44px]"
                    title={selectedSession.is_window_open === false ? "Ventana de 24hs cerrada" : "Enviar mensaje"}
                  >
                    <Send size={20} />
                  </button>
                </div>
              </form>

              {/* HSM Template Panel */}
              <HsmTemplatePanel
                isOpen={showHsmPanel}
                onClose={() => setShowHsmPanel(false)}
                phoneNumber={selectedSession.phone_number}
                leadContext={{
                  leadName: leadContext?.lead?.first_name
                    ? `${leadContext.lead.first_name}${leadContext.lead.last_name ? ' ' + leadContext.lead.last_name : ''}`
                    : undefined,
                  phone: selectedSession.phone_number,
                }}
                vendorName={user?.email?.split('@')[0]}
                tenantName={clinics.find(c => c.id === selectedSession.tenant_id)?.clinic_name}
                onSendSuccess={() => {
                  fetchMessages(selectedSession.phone_number, selectedSession.tenant_id);
                  setShowHsmPanel(false);
                }}
              />
            </div>
          </div>

          {/* Lead Context Panel - WhatsApp Style Overlay on Mobile / Sidebar on Desktop */}
          <div className={`
            ${showMobileContext ? 'flex' : 'hidden'}
            xl:flex flex-col
            fixed inset-0 z-40 bg-white/[0.03]
            xl:relative xl:z-0 xl:w-80 xl:border-l xl:inset-auto
            animate-slide-in xl:animate-none
          `}>
            {/* Context Header (Mobile only) */}
            <div className="p-4 border-b flex justify-between items-center xl:hidden">
              <div className="flex items-center gap-2">
                <User className="text-blue-400" size={20} />
                <h3 className="font-bold">{t('chats.lead_profile_title')}</h3>
              </div>
              <button
                onClick={() => setShowMobileContext(false)}
                className="p-2 hover:bg-white/[0.04] rounded-full"
              >
                <ChevronLeft size={24} className="rotate-180" />
              </button>
            </div>

            {/* Desktop Context Header */}
            <div className="hidden xl:flex p-4 border-b items-center gap-2">
              <Activity size={18} className="text-primary" />
              <h3 className="font-medium">{t('chats.lead_context')}</h3>
            </div>

            <div className="flex-1 overflow-y-auto">
              {/* Handoff Alert Banner */}
              {(leadContext?.handoff_requested || selectedSession.handoff_requested) && (
                <div className="mx-3 mt-3 p-3 bg-orange-500/15 border border-orange-500/30 rounded-lg">
                  <div className="flex items-center gap-2 mb-1.5">
                    <AlertCircle size={16} className="text-orange-400 shrink-0" />
                    <span className="font-semibold text-sm text-orange-300">Handoff solicitado</span>
                  </div>
                  {leadContext?.handoff_reason && (
                    <p className="text-xs text-orange-300/70 mb-2 ml-6">{leadContext.handoff_reason}</p>
                  )}
                  <button
                    onClick={async () => {
                      // Take over: activate human mode
                      await handleToggleHumanMode();
                      // Clear handoff flag locally
                      setSessions(prev => prev.map(s =>
                        s.phone_number === selectedSession.phone_number
                          ? { ...s, handoff_requested: false }
                          : s
                      ));
                      setSelectedSession(prev => prev ? { ...prev, handoff_requested: false } : null);
                      if (leadContext) {
                        setLeadContext({ ...leadContext, handoff_requested: false });
                      }
                    }}
                    className="ml-6 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-500 text-white text-xs font-semibold hover:bg-orange-600 transition-colors"
                  >
                    <HandMetal size={14} />
                    Tomar conversacion
                  </button>
                </div>
              )}

              {/* Lead Score */}
              {leadContext?.lead?.score != null && leadContext.lead.score > 0 && (() => {
                const sc = getScoreConfig(leadContext.lead.score!);
                return (
                  <div className={`mx-3 mt-3 p-3 rounded-lg border ${sc.bg} ${sc.border}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Star size={14} className={sc.color} />
                        <span className="text-xs font-medium text-white/50">Lead Score</span>
                      </div>
                      <span className={`text-lg font-bold ${sc.color}`}>{leadContext.lead.score}</span>
                    </div>
                    <div className="mt-1.5 w-full bg-white/[0.06] rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full transition-all"
                        style={{ width: `${leadContext.lead.score}%`, backgroundColor: sc.color.includes('green') ? '#22c55e' : sc.color.includes('blue') ? '#3b82f6' : sc.color.includes('yellow') ? '#eab308' : sc.color.includes('orange') ? '#f97316' : '#6b7280' }}
                      />
                    </div>
                    <p className={`text-[11px] mt-1 ${sc.color}`}>{sc.label}</p>
                  </div>
                );
              })()}

              {/* Tags */}
              {leadContext?.lead?.tags && leadContext.lead.tags.length > 0 && (
                <div className="mx-3 mt-3 p-3 bg-white/[0.02] border border-white/[0.06] rounded-lg">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Tag size={12} className="text-white/40" />
                    <span className="text-xs font-medium text-white/50">Etiquetas</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {leadContext.lead.tags.map(tag => (
                      <TagBadge
                        key={tag}
                        tag={{ name: tag, color: getTagColor(tag) }}
                        className="text-[11px]"
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Upcoming Meetings (AI-scheduled) */}
              {leadContext?.upcoming_meetings && leadContext.upcoming_meetings.length > 0 && (
                <div className="mx-3 mt-3 p-3 bg-white/[0.02] border border-white/[0.06] rounded-lg">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Calendar size={12} className="text-white/40" />
                    <span className="text-xs font-medium text-white/50">Reuniones programadas</span>
                  </div>
                  <div className="space-y-2">
                    {leadContext.upcoming_meetings.map(mtg => (
                      <div key={mtg.id} className="flex items-start gap-2 p-2 rounded bg-white/[0.02]">
                        <Calendar size={14} className="text-primary shrink-0 mt-0.5" />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-white/80 truncate">{mtg.title}</p>
                          <p className="text-[11px] text-primary">
                            {new Date(mtg.date).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                          </p>
                          {mtg.status && (
                            <span className="text-[10px] text-white/30">{mtg.status}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Status */}
              <div className={`mx-3 mt-3 p-3 rounded-lg ${selectedSession.status === 'human_handling' || selectedSession.status === 'silenced'
                ? 'bg-orange-500/10 border border-orange-500/20'
                : 'bg-green-500/10 border border-green-500/20'
                }`}>
                <div className="flex items-center gap-2 mb-1">
                  {selectedSession.status === 'human_handling' || selectedSession.status === 'silenced' ? (
                    <User size={16} className="text-orange-600" />
                  ) : (
                    <Activity size={16} className="text-green-400" />
                  )}
                  <span className="font-medium text-sm">
                    {t('chats.bot_status')}
                  </span>
                </div>
                <p className="text-sm text-white/50">
                  {selectedSession.status === 'human_handling'
                    ? 'Atendido por persona'
                    : selectedSession.status === 'silenced'
                      ? t('chats.silenced_24h')
                      : t('chats.ia_active')}
                </p>
                {selectedSession.human_override_until && (
                  <p className="text-xs text-white/40 mt-1">
                    Hasta: {new Date(selectedSession.human_override_until).toLocaleString()}
                  </p>
                )}
              </div>

              {/* Lead / Contact Info — con o sin reuniones previas */}
              {(() => {
                const hasEvents = !!(leadContext?.last_event || leadContext?.upcoming_event);
                const displayName = leadContext?.lead
                  ? [leadContext.lead.first_name, leadContext.lead.last_name].filter(Boolean).join(' ').trim() || selectedSession.lead_name || selectedSession.phone_number
                  : selectedSession.lead_name || selectedSession.phone_number;
                return (
                  <>
                    <div className={`p-3 rounded-lg ${hasEvents ? 'bg-white/[0.02]' : 'bg-amber-50 border border-amber-200'}`}>
                      {hasEvents ? (
                        <>
                          <h4 className="text-xs font-medium text-white/40 mb-2">{t('chats.lead_label')}</h4>
                          <p className="font-medium">{displayName}</p>
                          <p className="text-sm text-white/40">{selectedSession.phone_number}</p>
                        </>
                      ) : (
                        <>
                          <h4 className="text-xs font-medium text-amber-700 mb-2">{t('chats.contact_no_meetings')}</h4>
                          <p className="font-medium">{displayName}</p>
                          <p className="text-sm text-white/40">{selectedSession.phone_number}</p>
                          <p className="text-xs text-amber-700 mt-2">{t('chats.no_meetings_yet')}</p>
                        </>
                      )}
                    </div>

                    {hasEvents ? (
                      <>
                        {/* Last Meeting */}
                        <div className="p-3 bg-white/[0.02] rounded-lg">
                          <h4 className="text-xs font-medium text-white/40 mb-2 flex items-center gap-1">
                            <Calendar size={12} /> {t('chats.last_meeting')}
                          </h4>
                          {leadContext?.last_event ? (
                            <div className="space-y-1">
                              <p className="text-sm font-medium">{leadContext.last_event.title}</p>
                              <div className="flex items-center gap-2 text-xs text-white/40">
                                <span>{new Date(leadContext.last_event.date).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-white/30">{t('chats.no_previous_meetings')}</p>
                          )}
                        </div>

                        {/* Upcoming Meeting */}
                        <div className="p-3 bg-white/[0.02] rounded-lg">
                          <h4 className="text-xs font-medium text-white/40 mb-2 flex items-center gap-1">
                            <Clock size={12} /> {t('chats.upcoming_meeting')}
                          </h4>
                          {leadContext?.upcoming_event ? (
                            <div className="space-y-1">
                              <p className="text-sm font-medium">{leadContext.upcoming_event.title}</p>
                              <div className="flex items-center gap-2 text-xs text-primary font-medium">
                                <span>{new Date(leadContext.upcoming_event.date).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-white/30">{t('chats.no_scheduled_meetings')}</p>
                          )}
                        </div>

                        {/* Historial de interacciones placeholder */}
                      </>
                    ) : (
                      <div className="p-3 bg-white/[0.02] rounded-lg">
                        <p className="text-sm text-white/40 italic">{t('chats.no_interaction_history')}</p>
                      </div>
                    )}

                    {/* Assignment History */}
                    {selectedSession && (
                      <div className="p-3">
                        <AssignmentHistory
                          phone={selectedSession.phone_number}
                          leadId={leadContext?.lead?.id}
                          maxItems={3}
                          showTitle={true}
                        />
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          </div>
        </>
      ) : (
        <div className="hidden lg:flex flex-1 items-center justify-center bg-white/[0.02] flex-col gap-4">
          <MessageCircle size={64} className="opacity-20" />
          <p className="text-lg font-medium text-white/30">{t('chats.select_conversation')}</p>
          <p className="text-sm text-white/30">{t('chats.to_start_chatting')}</p>
        </div>
      )}

      {/* ======================================== */}
      {/* Seller Selector Modal */}
      {/* ======================================== */}
      {showSellerSelector && selectedSession && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="relative max-w-md w-full">
            <SellerSelector
              phone={selectedSession.phone_number}
              currentSellerId={sellerAssignment?.assigned_seller_id}
              currentSellerName={sellerAssignment?.seller_first_name ?
                `${sellerAssignment.seller_first_name} ${sellerAssignment.seller_last_name}` : undefined}
              currentSellerRole={sellerAssignment?.seller_role}
              onSellerSelected={handleAssignSeller}
              onCancel={() => setShowSellerSelector(false)}
              showAssignToMe={true}
              showAutoAssign={true}
            />
          </div>
        </div>
      )}

      {/* ======================================== */}
      {/* CSS for animations - Removed to fix build error */}
      {/* ======================================== */}
    </div>
  );
}
