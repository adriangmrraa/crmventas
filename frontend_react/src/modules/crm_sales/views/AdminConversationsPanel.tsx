/**
 * AdminConversationsPanel — DEV-66: Panel admin de todas las conversaciones del equipo.
 * Split-view: izquierda lista de conversaciones con filtros, derecha hilo de mensajes (read-only).
 * Solo accesible por rol CEO.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  MessageSquare, Search, Filter, Users, Clock, ChevronDown, X
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from '../../../api/axios';
import { useAuth } from '../../../context/AuthContext';
import { useSocket } from '../../../context/SocketContext';

const API_BASE = '/admin/core/internal-chat';

// ── Types ─────────────────────────────────────────────────────────────────────

interface LastMessage {
  autor_nombre: string;
  autor_rol: string;
  contenido: string;
  created_at: string;
}

interface Conversacion {
  canal_id: string;
  tipo: 'canal' | 'dm';
  participantes: string[];
  ultima_actividad: string | null;
  last_message: LastMessage | null;
}

interface ConversacionesResponse {
  conversaciones: Conversacion[];
  total: number;
}

interface ChatMsg {
  id: string;
  canal_id: string;
  autor_id: string;
  autor_nombre: string;
  autor_rol: string;
  contenido: string;
  tipo: string;
  created_at: string;
}

interface Filters {
  vendedor_id: string;
  fecha_desde: string;
  fecha_hasta: string;
  tipo: '' | 'canal' | 'dm';
  keyword: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTimeAgo(isoDate: string | null): string {
  if (!isoDate) return '';
  const diff = Date.now() - new Date(isoDate).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return 'hace un momento';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `hace ${minutes}min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days}d`;
}

function highlightKeyword(text: string, keyword: string): React.ReactNode {
  if (!keyword.trim()) return text;
  const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  const parts = text.split(regex);
  return parts.map((part, i) =>
    regex.test(part)
      ? <mark key={i} className="bg-yellow-400/30 text-yellow-300 rounded px-0.5">{part}</mark>
      : part
  );
}

function canalLabel(conv: Conversacion): string {
  if (conv.tipo === 'canal') return `#${conv.canal_id}`;
  // DM: show participant IDs stripped of dm_ prefix
  const parts = conv.canal_id.replace('dm_', '').split('_');
  return parts.slice(0, 2).join(' · ') || conv.canal_id;
}

// ── ROL BADGE ────────────────────────────────────────────────────────────────

const ROL_COLORS: Record<string, string> = {
  ceo:      'bg-violet-500/20 text-violet-300',
  setter:   'bg-cyan-500/20 text-cyan-300',
  closer:   'bg-emerald-500/20 text-emerald-300',
  secretary:'bg-amber-500/20 text-amber-300',
};

const RolBadge = ({ rol }: { rol: string }) => (
  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase ${ROL_COLORS[rol] ?? 'bg-white/10 text-white/40'}`}>
    {rol}
  </span>
);

// ── MAIN COMPONENT ────────────────────────────────────────────────────────────

export default function AdminConversationsPanel() {
  const { user } = useAuth();
  const { socket } = useSocket();

  // Filters state
  const [filters, setFilters] = useState<Filters>({
    vendedor_id: '',
    fecha_desde: '',
    fecha_hasta: '',
    tipo: '',
    keyword: '',
  });
  const [showFilters, setShowFilters] = useState(false);

  // Selected conversation and its thread
  const [selectedCanal, setSelectedCanal] = useState<string | null>(null);
  const [thread, setThread] = useState<ChatMsg[]>([]);
  const [threadLoading, setThreadLoading] = useState(false);
  const [threadBefore, setThreadBefore] = useState<string | null>(null);
  const [hasMoreThread, setHasMoreThread] = useState(false);

  // Vendor list for dropdown
  const [vendedores, setVendedores] = useState<{ id: string; nombre: string }[]>([]);

  // Fetch conversations (React Query)
  const queryParams = new URLSearchParams();
  if (filters.vendedor_id) queryParams.set('vendedor_id', filters.vendedor_id);
  if (filters.fecha_desde) queryParams.set('fecha_desde', filters.fecha_desde);
  if (filters.fecha_hasta) queryParams.set('fecha_hasta', filters.fecha_hasta);
  if (filters.tipo) queryParams.set('tipo', filters.tipo);
  if (filters.keyword) queryParams.set('keyword', filters.keyword);
  queryParams.set('limit', '50');

  const {
    data: convData,
    isLoading: convLoading,
    refetch: refetchConvs,
  } = useQuery<ConversacionesResponse>({
    queryKey: ['admin-conversaciones', filters],
    queryFn: async () => {
      const res = await api.get(`${API_BASE}/admin/conversaciones?${queryParams.toString()}`);
      return res.data;
    },
    staleTime: 30_000,
  });

  // Load vendor profiles for filter dropdown
  useEffect(() => {
    api.get(`${API_BASE}/perfiles`)
      .then(res => setVendedores(res.data.map((p: any) => ({ id: p.id, nombre: p.nombre }))))
      .catch(() => {});
  }, []);

  // Load thread for selected canal
  const loadThread = useCallback(async (canalId: string, before?: string) => {
    setThreadLoading(true);
    try {
      const params = new URLSearchParams({ limit: '30' });
      if (before) params.set('before', before);
      const res = await api.get(`${API_BASE}/mensajes/${canalId}?${params.toString()}`);
      const msgs: ChatMsg[] = res.data;
      if (before) {
        setThread(prev => [...msgs, ...prev]);
      } else {
        setThread(msgs);
      }
      setHasMoreThread(msgs.length === 30);
      if (msgs.length > 0 && !before) {
        setThreadBefore(msgs[0].created_at);
      } else if (msgs.length > 0 && before) {
        setThreadBefore(msgs[0].created_at);
      }
    } catch {}
    setThreadLoading(false);
  }, []);

  const handleSelectConv = (canalId: string) => {
    setSelectedCanal(canalId);
    setThread([]);
    setThreadBefore(null);
    setHasMoreThread(false);
    loadThread(canalId);
  };

  const handleLoadEarlier = () => {
    if (selectedCanal && threadBefore) {
      loadThread(selectedCanal, threadBefore);
    }
  };

  // Socket: subscribe to admin room for real-time updates
  useEffect(() => {
    if (!socket || !user) return;
    socket.emit('chat:admin_subscribe', {
      tenant_id: user.tenant_id,
      role: user.role,
    });

    const handleNuevaActividad = (msg: ChatMsg) => {
      // Refresh conversation list
      refetchConvs();
      // If viewing this canal, append new message
      if (msg.canal_id === selectedCanal) {
        setThread(prev => {
          if (prev.some(m => m.id === msg.id)) return prev;
          return [...prev, msg];
        });
      }
    };

    socket.on('chat:admin:nueva_actividad', handleNuevaActividad);

    return () => {
      socket.emit('chat:admin_unsubscribe', { tenant_id: user.tenant_id });
      socket.off('chat:admin:nueva_actividad', handleNuevaActividad);
    };
  }, [socket, user, selectedCanal, refetchConvs]);

  const convs = convData?.conversaciones ?? [];
  const total = convData?.total ?? 0;
  const hasActiveFilters = !!(filters.vendedor_id || filters.fecha_desde || filters.fecha_hasta || filters.tipo || filters.keyword);

  const clearFilters = () => setFilters({ vendedor_id: '', fecha_desde: '', fecha_hasta: '', tipo: '', keyword: '' });

  // Thread bottom ref for scroll
  const threadBottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!threadBefore) {
      // Only auto-scroll on initial load, not on "cargar anteriores"
      threadBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thread, threadBefore]);

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-4 sm:px-6 py-4 border-b border-white/[0.06]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-white/[0.06]">
              <MessageSquare size={20} className="text-violet-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">Conversaciones del Equipo</h1>
              <p className="text-xs text-white/40">
                {total} conversaciones
                {hasActiveFilters && <span className="text-violet-400 ml-1">(filtrado)</span>}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`p-2 rounded-lg transition-colors ${hasActiveFilters ? 'bg-violet-500/20 text-violet-400' : 'bg-white/[0.06] text-white/60 hover:text-white'}`}
            >
              <Filter size={16} />
            </button>
          </div>
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <div className="mt-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {/* Vendedor */}
              <div>
                <label className="text-xs text-white/40 mb-1 block">Vendedor</label>
                <select
                  value={filters.vendedor_id}
                  onChange={e => setFilters(f => ({ ...f, vendedor_id: e.target.value }))}
                  className="w-full px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-white/20"
                >
                  <option value="">Todos</option>
                  {vendedores.map(v => (
                    <option key={v.id} value={v.id}>{v.nombre}</option>
                  ))}
                </select>
              </div>
              {/* Fecha desde */}
              <div>
                <label className="text-xs text-white/40 mb-1 block">Desde</label>
                <input
                  type="date"
                  value={filters.fecha_desde}
                  onChange={e => setFilters(f => ({ ...f, fecha_desde: e.target.value }))}
                  className="w-full px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-white/20"
                />
              </div>
              {/* Fecha hasta */}
              <div>
                <label className="text-xs text-white/40 mb-1 block">Hasta</label>
                <input
                  type="date"
                  value={filters.fecha_hasta}
                  onChange={e => setFilters(f => ({ ...f, fecha_hasta: e.target.value }))}
                  className="w-full px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-white/20"
                />
              </div>
            </div>
            {/* Keyword + tipo row */}
            <div className="flex flex-col sm:flex-row items-start sm:items-end gap-3">
              {/* Keyword */}
              <div className="flex-1">
                <label className="text-xs text-white/40 mb-1 block">Buscar en mensajes</label>
                <div className="relative">
                  <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/30" />
                  <input
                    type="text"
                    value={filters.keyword}
                    onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))}
                    placeholder="Keyword..."
                    className="w-full pl-7 pr-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-white/20 placeholder:text-white/20"
                  />
                </div>
              </div>
              {/* Tipo buttons */}
              <div>
                <label className="text-xs text-white/40 mb-1 block">Tipo</label>
                <div className="flex gap-1">
                  {(['', 'canal', 'dm'] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => setFilters(f => ({ ...f, tipo: t }))}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        filters.tipo === t
                          ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                          : 'bg-white/[0.06] text-white/50 hover:text-white border border-transparent'
                      }`}
                    >
                      {t === '' ? 'Todos' : t === 'canal' ? 'Canales' : 'DMs'}
                    </button>
                  ))}
                </div>
              </div>
              {/* Actions */}
              <div className="flex items-center gap-2">
                <button onClick={clearFilters} className="px-3 py-1.5 text-xs text-white/50 hover:text-white transition-colors">
                  Limpiar
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main split-view */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row">
        {/* LEFT: Conversation list */}
        <div className="lg:w-80 xl:w-96 shrink-0 border-b lg:border-b-0 lg:border-r border-white/[0.06] overflow-y-auto">
          {convLoading ? (
            <div className="flex items-center justify-center py-12 text-white/30 text-sm">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white/30" />
            </div>
          ) : convs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-white/30">
              <MessageSquare size={32} className="mb-3 opacity-30" />
              <p className="text-sm">Sin conversaciones</p>
              {hasActiveFilters && (
                <button onClick={clearFilters} className="mt-2 text-xs text-violet-400 hover:underline">
                  Quitar filtros
                </button>
              )}
            </div>
          ) : (
            convs.map(conv => (
              <button
                key={conv.canal_id}
                onClick={() => handleSelectConv(conv.canal_id)}
                className={`w-full text-left px-4 py-3 border-b border-white/[0.04] hover:bg-white/[0.04] transition-colors ${
                  selectedCanal === conv.canal_id ? 'bg-violet-500/[0.08] border-l-2 border-l-violet-500' : ''
                }`}
              >
                <div className="flex items-start gap-2">
                  <div className="mt-0.5 p-1.5 rounded-lg bg-white/[0.06] shrink-0">
                    {conv.tipo === 'canal'
                      ? <Users size={13} className="text-violet-400" />
                      : <MessageSquare size={13} className="text-cyan-400" />
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <span className="text-sm font-medium text-white truncate">
                        {canalLabel(conv)}
                      </span>
                      <span className="text-[10px] text-white/30 shrink-0 flex items-center gap-1">
                        <Clock size={10} />
                        {formatTimeAgo(conv.ultima_actividad)}
                      </span>
                    </div>
                    {conv.last_message ? (
                      <p className="text-xs text-white/50 truncate">
                        <span className="text-white/70 font-medium">{conv.last_message.autor_nombre}:</span>{' '}
                        {filters.keyword
                          ? highlightKeyword(conv.last_message.contenido, filters.keyword)
                          : conv.last_message.contenido
                        }
                      </p>
                    ) : (
                      <p className="text-xs text-white/30 italic">Sin mensajes</p>
                    )}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        {/* RIGHT: Thread viewer */}
        <div className="flex-1 min-h-0 flex flex-col">
          {!selectedCanal ? (
            <div className="flex flex-col items-center justify-center h-full text-white/20">
              <MessageSquare size={40} className="mb-3 opacity-30" />
              <p className="text-sm">Selecciona una conversacion</p>
            </div>
          ) : (
            <>
              {/* Thread header */}
              <div className="shrink-0 px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare size={15} className="text-white/40" />
                  <span className="text-sm font-medium text-white">
                    {convs.find(c => c.canal_id === selectedCanal)
                      ? canalLabel(convs.find(c => c.canal_id === selectedCanal)!)
                      : selectedCanal
                    }
                  </span>
                  <span className="text-[10px] text-white/30 uppercase tracking-wider">read-only</span>
                </div>
                <button
                  onClick={() => setSelectedCanal(null)}
                  className="p-1 text-white/30 hover:text-white/60 transition-colors"
                >
                  <X size={14} />
                </button>
              </div>

              {/* Load earlier button */}
              {hasMoreThread && (
                <div className="shrink-0 p-2 text-center border-b border-white/[0.04]">
                  <button
                    onClick={handleLoadEarlier}
                    disabled={threadLoading}
                    className="inline-flex items-center gap-2 px-4 py-1.5 text-xs text-white/50 bg-white/[0.04] hover:bg-white/[0.08] rounded-lg transition-colors disabled:opacity-50"
                  >
                    <ChevronDown size={13} className="rotate-180" />
                    Cargar anteriores
                  </button>
                </div>
              )}

              {/* Messages */}
              <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-3">
                {threadLoading && thread.length === 0 ? (
                  <div className="flex items-center justify-center py-8 text-white/30 text-sm">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white/30" />
                  </div>
                ) : thread.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-white/30">
                    <MessageSquare size={28} className="mb-2 opacity-30" />
                    <p className="text-sm">Sin mensajes</p>
                  </div>
                ) : (
                  thread.map(msg => (
                    <div key={msg.id} className="flex gap-2">
                      <div className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className="text-xs font-medium text-white/80">{msg.autor_nombre}</span>
                          <RolBadge rol={msg.autor_rol} />
                          <span className="text-[10px] text-white/25 ml-auto">
                            {new Date(msg.created_at).toLocaleString([], {
                              month: 'short', day: 'numeric',
                              hour: '2-digit', minute: '2-digit',
                            })}
                          </span>
                        </div>
                        <p className="text-sm text-white/70 whitespace-pre-wrap break-words">
                          {filters.keyword
                            ? highlightKeyword(msg.contenido, filters.keyword)
                            : msg.contenido
                          }
                        </p>
                      </div>
                    </div>
                  ))
                )}
                <div ref={threadBottomRef} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
