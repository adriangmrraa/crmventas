import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  MessageCircle, Send, Calendar, User, Activity,
  Pause, Play, AlertCircle, Clock, ChevronLeft,
  Search, XCircle, Bell, Volume2, VolumeX,
  UserPlus, Users, Target, Zap, Crown, Bot, RefreshCw, X
} from 'lucide-react';
import api, { BACKEND_URL } from '../api/axios';
import { useTranslation } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { io, Socket } from 'socket.io-client';
import SellerBadge from '../components/SellerBadge';
import SellerSelector from '../components/SellerSelector';
import AssignmentHistory from '../components/AssignmentHistory';

// ============================================
// INTERFACES
// ============================================

interface ClinicOption {
  id: number;
  clinic_name: string;
}

interface ChatSession {
  phone_number: string;
  tenant_id: number;
  patient_id?: number;
  patient_name?: string;
  last_message: string;
  last_message_time: string;
  unread_count: number;
  status: 'active' | 'human_handling' | 'paused' | 'silenced';
  human_override_until?: string;
  urgency_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  last_derivhumano_at?: string;
  is_window_open?: boolean;
  last_user_message_time?: string;
}

interface ChatMessage {
  id: number;
  from_number: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  is_derivhumano?: boolean;
}

/** Contexto de lead para panel CRM (GET /admin/core/crm/leads/phone/{phone}/context) */
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
  is_guest: boolean;
}

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
  // Clínicas (CEO puede tener varias; secretary/professional una)
  const [clinics, setClinics] = useState<ClinicOption[]>([]);
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

  // Estados de UI
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [showToast, setShowToast] = useState<Toast | null>(null);
  const [highlightedSession, setHighlightedSession] = useState<string | null>(null);
  const [showMobileContext, setShowMobileContext] = useState(false);

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

    // Evento: Nueva derivación humana (derivhumano) — solo para la clínica seleccionada
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

    // Evento: Nuevo mensaje en chat (tenant_id opcional; si viene, solo actualizar si es la clínica seleccionada)
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

    // Evento: Estado de override cambiado (por clínica: solo actualizar si es la clínica seleccionada)
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

    // Evento: Paciente actualizado (urgencia, etc)
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

    // Cleanup
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [selectedSession, soundEnabled, selectedTenantId, t]);

  // ============================================
  // DATOS - CARGAR CLÍNICAS, SESIONES Y MENSAJES
  // ============================================

  useEffect(() => {
    api.get<ClinicOption[]>('/admin/core/chat/tenants').then((res) => {
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

    setSending(true);
    try {
      await api.post('/admin/core/chat/send', {
        phone: selectedSession.phone_number,
        tenant_id: selectedSession.tenant_id,
        message: newMessage,
      });
      setNewMessage('');
      fetchMessages(selectedSession.phone_number, selectedSession.tenant_id);

      socketRef.current?.emit('MANUAL_MESSAGE', {
        phone: selectedSession.phone_number,
        tenant_id: selectedSession.tenant_id,
        message: newMessage,
      });
    } catch (error) {
      console.error('Error sending message:', error);
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

  const filteredSessions = sessions.filter(session =>
    session.patient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    session.phone_number.includes(searchTerm)
  );

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) return 'Ahora';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
    return date.toLocaleDateString();
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
        <span className="flex items-center gap-1 text-xs text-green-600">
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
    <div className="flex h-full min-h-0 bg-medical-50 overflow-hidden font-sans">
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
        w-full lg:w-80 border-r bg-white flex-col
      `}>
        <div className="p-4 border-b">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-bold">{t('chats.title')}</h2>
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              className="p-2 rounded-lg hover:bg-gray-100"
              title={soundEnabled ? t('chats.mute_sound') : t('chats.enable_sound')}
            >
              {soundEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
            </button>
          </div>
          {clinics.length > 1 && (
            <div className="mb-3">
              <label className="block text-xs font-medium text-gray-500 mb-1">{t('chats.clinic_label')}</label>
              <select
                value={selectedTenantId ?? ''}
                onChange={(e) => setSelectedTenantId(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-white"
              >
                {clinics.map((c) => (
                  <option key={c.id} value={c.id}>{c.clinic_name}</option>
                ))}
              </select>
            </div>
          )}
          {clinics.length === 1 && clinics[0] && (
            <p className="text-xs text-gray-500 mb-2">{clinics[0].clinic_name}</p>
          )}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              placeholder={t('chats.search_placeholder')}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-500">{t('common.loading')}</div>
          ) : filteredSessions.length === 0 ? (
            <div className="p-4 text-center text-gray-500">{t('chats.no_sessions')}</div>
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
                    ${isSelected ? 'bg-medical-50' : 'hover:bg-gray-50 active:bg-gray-100'}
                    ${isHighlighted ? 'bg-orange-50 animate-pulse' : ''}
                  `}
                >
                  <div className="flex items-center gap-3">
                    {/* Avatar with Status Ring */}
                    <div className="relative shrink-0">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-sm ${avatarBg}`}>
                        {(session.patient_name || session.phone_number).charAt(0)}
                      </div>
                      {session.status === 'human_handling' && (
                        <div className="absolute -bottom-1 -right-1 bg-white p-0.5 rounded-full shadow-sm">
                          <User size={12} className="text-orange-500 fill-orange-500" />
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-baseline mb-0.5">
                        <span className={`font-semibold truncate ${isSelected ? 'text-medical-900' : 'text-gray-900'}`}>
                          {session.patient_name || session.phone_number}
                        </span>
                        <span className={`text-[11px] shrink-0 ml-2 ${session.unread_count > 0 ? 'text-medical-600 font-bold' : 'text-gray-400'}`}>
                          {formatTime(session.last_message_time)}
                        </span>
                      </div>

                      <div className="flex justify-between items-center">
                        <p className={`text-sm truncate pr-4 ${session.unread_count > 0 ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                          {session.last_message || t('chats.no_messages')}
                        </p>
                        {session.unread_count > 0 && (
                          <span className="bg-medical-600 text-white text-[10px] font-bold min-w-[20px] h-5 px-1.5 rounded-full flex items-center justify-center">
                            {session.unread_count}
                          </span>
                        )}
                      </div>
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
          <div className="flex-1 flex flex-col min-w-0 bg-gray-50 h-full min-h-0">
            {/* Header + Messages + Input Container */}
            <div className="flex-1 flex flex-col min-h-0 relative">
              {/* Header */}
              <div className="p-4 border-b bg-white flex justify-between items-center">
                <div className="flex items-center gap-3 min-w-0">
                  <button
                    onClick={() => {
                      setSelectedSession(null);
                      setShowMobileContext(false);
                    }}
                    className="lg:hidden p-2 -ml-2 hover:bg-gray-100 rounded-full text-gray-600 active:bg-gray-200 transition-colors"
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
                    {(selectedSession.patient_name || selectedSession.phone_number).charAt(0)}
                  </div>
                  <div className="min-w-0 flex-1 cursor-pointer" onClick={() => window.innerWidth < 1280 && setShowMobileContext(!showMobileContext)}>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-gray-900 truncate leading-tight">
                        {selectedSession.patient_name || t('chats.no_name')}
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
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 border border-gray-200 text-xs cursor-pointer hover:bg-gray-200"
                          onClick={() => setShowSellerSelector(true)}
                        >
                          <Bot size={12} />
                          <span>AGENTE IA</span>
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 truncate">{selectedSession.phone_number}</p>
                  </div>
                </div>

                {/* Header Actions - Seller Assignment */}
                <div className="flex items-center gap-1 sm:gap-2">
                  {/* Assign Seller Button */}
                  <button
                    onClick={() => setShowSellerSelector(!showSellerSelector)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm
                      ${sellerAssignment?.assigned_seller_id
                        ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 border border-blue-200'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200'
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
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-green-100 text-green-700 hover:bg-green-200 border border-green-200 transition-all shadow-sm disabled:opacity-50"
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
                    className="p-2 text-medical-600 hover:bg-medical-50 rounded-full lg:hidden transition-colors"
                    title={t('chats.view_clinical_chart')}
                  >
                    <Activity size={20} />
                  </button>

                  <button
                    onClick={handleToggleHumanMode}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold transition-all shadow-sm
                      ${selectedSession.status === 'human_handling' || selectedSession.status === 'silenced'
                        ? 'bg-green-100 text-green-700 hover:bg-green-200 border border-green-200'
                        : 'bg-orange-100 text-orange-700 hover:bg-orange-200 border border-orange-200'
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
                <div className="bg-orange-50 border-b border-orange-200 px-4 py-2 flex items-center gap-2">
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
                <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 flex items-center gap-2">
                  <Pause size={16} className="text-blue-500" />
                  <span className="text-sm text-blue-700">
                    ✋ {t('chats.manual_mode_active')}
                  </span>
                  <button
                    onClick={handleToggleHumanMode}
                    className="ml-auto text-xs text-blue-600 hover:underline"
                  >
                    {t('chats.activate_ai')}
                  </button>
                </div>
              )}

              {/* Banner de Ventana de 24hs Cerrada */}
              {selectedSession.is_window_open === false && (
                <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2 flex items-center gap-2">
                  <Clock size={16} className="text-yellow-600" />
                  <span className="text-sm text-yellow-700">
                    ⏳ {t('chats.window_24h_closed')}
                  </span>
                </div>
              )}

              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 flex flex-col min-h-0">
                {hasMoreMessages && (
                  <button
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="mx-auto py-2 px-4 text-xs text-medical-600 hover:text-medical-700 font-medium bg-white rounded-full shadow-sm border border-medical-100 mb-4 transition-all disabled:opacity-50 shrink-0"
                  >
                    {loadingMore ? t('common.loading') : t('chats.load_older_messages')}
                  </button>
                )}

                <div className="flex-1" /> {/* Spacer to push messages down if few */}

                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === 'user' ? 'justify-start' : 'justify-end'}`}
                  >
                    <div
                      className={`max-w-[70%] rounded-lg px-4 py-3 ${message.role === 'user'
                        ? 'bg-white shadow-sm'
                        : message.is_derivhumano
                          ? 'bg-orange-100 border border-orange-300 shadow-sm text-gray-800'
                          : 'bg-blue-600 text-white shadow-sm'
                        }`}
                    >
                      {message.is_derivhumano && (
                        <div className="flex items-center gap-1 text-xs text-orange-600 mb-1">
                          <User size={12} />
                          <span className="font-medium">{t('chats.auto_handoff')}</span>
                        </div>
                      )}
                      <p className="text-sm">{message.content}</p>
                      <p className={`text-xs mt-1 ${message.role === 'user' ? 'text-gray-400' : 'text-blue-200'
                        }`}>
                        {new Date(message.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <form onSubmit={handleSendMessage} className="p-4 border-t bg-white">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder={selectedSession.is_window_open === false ? "Ventana cerrada - Esperando paciente..." : "Escribe un mensaje..."}
                    disabled={selectedSession.is_window_open === false}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage(e as any);
                      }
                    }}
                    className={`flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-medical-500 bg-white text-gray-900 ${selectedSession.is_window_open === false ? 'bg-gray-100 cursor-not-allowed opacity-75' : ''}`}
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
            </div>
          </div>

          {/* Clinical Context Panel - WhatsApp Style Overlay on Mobile / Sidebar on Desktop */}
          <div className={`
            ${showMobileContext ? 'flex' : 'hidden'}
            xl:flex flex-col
            fixed inset-0 z-40 bg-white
            xl:relative xl:z-0 xl:w-80 xl:border-l xl:inset-auto
            animate-slide-in xl:animate-none
          `}>
            {/* Context Header (Mobile only) */}
            <div className="p-4 border-b flex justify-between items-center xl:hidden">
              <div className="flex items-center gap-2">
                <User className="text-medical-600" size={20} />
                <h3 className="font-bold">{t('chats.patient_profile_title')}</h3>
              </div>
              <button
                onClick={() => setShowMobileContext(false)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <ChevronLeft size={24} className="rotate-180" />
              </button>
            </div>

            {/* Desktop Context Header */}
            <div className="hidden xl:flex p-4 border-b items-center gap-2">
              <Activity size={18} className="text-primary" />
              <h3 className="font-medium">{t('chats.clinical_context')}</h3>
            </div>

            <div className="flex-1 overflow-y-auto">
              {/* AI Status */}
              <div className={`p-3 rounded-lg ${selectedSession.status === 'human_handling' || selectedSession.status === 'silenced'
                ? 'bg-orange-50 border border-orange-200'
                : 'bg-green-50 border border-green-200'
                }`}>
                <div className="flex items-center gap-2 mb-1">
                  {selectedSession.status === 'human_handling' || selectedSession.status === 'silenced' ? (
                    <User size={16} className="text-orange-600" />
                  ) : (
                    <Activity size={16} className="text-green-600" />
                  )}
                  <span className="font-medium text-sm">
                    {t('chats.bot_status')}
                  </span>
                </div>
                <p className="text-sm text-gray-600">
                  {selectedSession.status === 'human_handling'
                    ? 'Atendido por persona'
                    : selectedSession.status === 'silenced'
                      ? t('chats.silenced_24h')
                      : t('chats.ia_active')}
                </p>
                {selectedSession.human_override_until && (
                  <p className="text-xs text-gray-500 mt-1">
                    Hasta: {new Date(selectedSession.human_override_until).toLocaleString()}
                  </p>
                )}
              </div>

              {/* Patient / Contact Info — Lead vs Paciente (solo con turno = ficha con historial) */}
              {(() => {
                const hasEvents = !!(leadContext?.last_event || leadContext?.upcoming_event);
                const displayName = leadContext?.lead
                  ? [leadContext.lead.first_name, leadContext.lead.last_name].filter(Boolean).join(' ').trim() || selectedSession.patient_name || selectedSession.phone_number
                  : selectedSession.patient_name || selectedSession.phone_number;
                return (
                  <>
                    <div className={`p-3 rounded-lg ${hasEvents ? 'bg-gray-50' : 'bg-amber-50 border border-amber-200'}`}>
                      {hasEvents ? (
                        <>
                          <h4 className="text-xs font-medium text-gray-500 mb-2">{t('chats.patient_label')}</h4>
                          <p className="font-medium">{displayName}</p>
                          <p className="text-sm text-gray-500">{selectedSession.phone_number}</p>
                        </>
                      ) : (
                        <>
                          <h4 className="text-xs font-medium text-amber-700 mb-2">{t('chats.contact_no_appointments')}</h4>
                          <p className="font-medium">{displayName}</p>
                          <p className="text-sm text-gray-500">{selectedSession.phone_number}</p>
                          <p className="text-xs text-amber-700 mt-2">{t('chats.no_appointments_yet')}</p>
                        </>
                      )}
                    </div>

                    {hasEvents ? (
                      <>
                        {/* Last Appointment */}
                        <div className="p-3 bg-gray-50 rounded-lg">
                          <h4 className="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
                            <Calendar size={12} /> {t('chats.last_appointment')}
                          </h4>
                          {leadContext?.last_event ? (
                            <div className="space-y-1">
                              <p className="text-sm font-medium">{leadContext.last_event.title}</p>
                              <div className="flex items-center gap-2 text-xs text-gray-500">
                                <span>{new Date(leadContext.last_event.date).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-gray-400">{t('chats.no_previous_appointments')}</p>
                          )}
                        </div>

                        {/* Upcoming Appointment */}
                        <div className="p-3 bg-gray-50 rounded-lg">
                          <h4 className="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
                            <Clock size={12} /> {t('chats.upcoming_appointment')}
                          </h4>
                          {leadContext?.upcoming_event ? (
                            <div className="space-y-1">
                              <p className="text-sm font-medium">{leadContext.upcoming_event.title}</p>
                              <div className="flex items-center gap-2 text-xs text-primary font-medium">
                                <span>{new Date(leadContext.upcoming_event.date).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-gray-400">{t('chats.no_scheduled_appointments')}</p>
                          )}
                        </div>

                        {/* Tratamiento (CRM: no aplica) */}
                        <div className="p-3 bg-gray-50 rounded-lg">
                          <h4 className="text-xs font-medium text-gray-500 mb-2">{t('chats.current_treatment')}</h4>
                          <p className="text-sm text-gray-400 italic">{t('chats.no_treatment_plan')}</p>
                        </div>
                      </>
                    ) : (
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-500 italic">{t('chats.no_clinical_history')}</p>
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
        <div className="hidden lg:flex flex-1 items-center justify-center bg-gray-50 flex-col gap-4">
          <MessageCircle size={64} className="opacity-20" />
          <p className="text-lg font-medium text-gray-400">{t('chats.select_conversation')}</p>
          <p className="text-sm text-gray-400">{t('chats.to_start_chatting')}</p>
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
