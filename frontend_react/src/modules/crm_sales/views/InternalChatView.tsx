/**
 * InternalChatView — SPEC-04: Team chat with channels and DMs.
 * Layout: sidebar (channels + DMs) + message panel.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Hash, MessageSquare, Send, Plus, Users, Phone, Bell, ChevronDown
} from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import { useSocket } from '../../../context/SocketContext';
import { useAuth } from '../../../context/AuthContext';

const API_BASE = '/admin/core/internal-chat';

interface ChatMsg {
  id: string;
  canal_id: string;
  autor_id: string;
  autor_nombre: string;
  autor_rol: string;
  contenido: string;
  tipo: string;
  metadata?: { cliente_nombre?: string; descripcion?: string; url?: string };
  created_at: string;
}

interface Canal {
  canal_id: string;
  label: string;
  tipo: string;
}

interface DM {
  canal_id: string;
  tipo: string;
  otro_participante: { id: string; nombre: string; rol: string };
  ultima_actividad: string;
  no_leidos: number;
}

interface UserProfile {
  id: string;
  nombre: string;
  email: string;
  rol: string;
}

export default function InternalChatView() {
  const { t } = useTranslation();
  const { socket } = useSocket();
  const { user } = useAuth();
  const [canales, setCanales] = useState<Canal[]>([]);
  const [dms, setDms] = useState<DM[]>([]);
  const [activeCanal, setActiveCanal] = useState<string>('general');
  const [activeLabel, setActiveLabel] = useState<string>('#general');
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [showNewDM, setShowNewDM] = useState(false);
  const [profiles, setProfiles] = useState<UserProfile[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevCanalRef = useRef<string | null>(null);

  // Load channels + DMs
  const loadCanales = useCallback(async () => {
    try {
      const res = await api.get(`${API_BASE}/canales`);
      setCanales(res.data.canales);
      setDms(res.data.dms);
    } catch {}
  }, []);

  // Load messages for active channel
  const loadMessages = useCallback(async () => {
    if (!activeCanal) return;
    setLoading(true);
    try {
      const res = await api.get(`${API_BASE}/mensajes/${activeCanal}`);
      setMessages(res.data);
    } catch {}
    setLoading(false);
  }, [activeCanal]);

  useEffect(() => { loadCanales(); }, [loadCanales]);
  useEffect(() => { loadMessages(); }, [loadMessages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Socket.IO: join/leave rooms
  useEffect(() => {
    if (!socket || !user) return;

    // Leave previous room
    if (prevCanalRef.current) {
      socket.emit('chat:leave_canal', {
        tenant_id: user.tenant_id,
        canal_id: prevCanalRef.current,
      });
    }

    // Join new room
    socket.emit('chat:join_canal', {
      tenant_id: user.tenant_id,
      canal_id: activeCanal,
      user_id: user.id,
    });
    prevCanalRef.current = activeCanal;

    // Listen for new messages
    const handleNewMsg = (msg: ChatMsg) => {
      if (msg.canal_id === activeCanal) {
        setMessages(prev => {
          if (prev.some(m => m.id === msg.id)) return prev; // Dedup
          return [...prev, msg];
        });
      }
    };

    const handleBadgeUpdate = (data: { canal_id: string; no_leidos: number }) => {
      setDms(prev => prev.map(dm =>
        dm.canal_id === data.canal_id ? { ...dm, no_leidos: data.no_leidos } : dm
      ));
    };

    const handleBadgeClear = (data: { canal_id: string }) => {
      setDms(prev => prev.map(dm =>
        dm.canal_id === data.canal_id ? { ...dm, no_leidos: 0 } : dm
      ));
    };

    socket.on('chat:nuevo_mensaje', handleNewMsg);
    socket.on('chat:dm_badge_update', handleBadgeUpdate);
    socket.on('chat:badge_clear', handleBadgeClear);

    return () => {
      socket.off('chat:nuevo_mensaje', handleNewMsg);
      socket.off('chat:dm_badge_update', handleBadgeUpdate);
      socket.off('chat:badge_clear', handleBadgeClear);
    };
  }, [socket, activeCanal, user]);

  // Mark DM as read when opening
  useEffect(() => {
    if (activeCanal.startsWith('dm_')) {
      api.post(`${API_BASE}/dms/${activeCanal}/leer`).catch(() => {});
      if (socket && user) {
        socket.emit('chat:dm_leido', {
          tenant_id: user.tenant_id,
          canal_id: activeCanal,
          user_id: user.id,
        });
      }
    }
  }, [activeCanal, socket, user]);

  const handleSend = async () => {
    if (!inputText.trim() || !activeCanal) return;
    try {
      await api.post(`${API_BASE}/mensajes`, {
        canal_id: activeCanal,
        contenido: inputText.trim(),
        tipo: 'mensaje',
      });
      setInputText('');
    } catch {}
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const switchCanal = (canalId: string, label: string) => {
    setActiveCanal(canalId);
    setActiveLabel(label);
  };

  const handleNewDM = async (profile: UserProfile) => {
    try {
      const res = await api.post(`${API_BASE}/dms/iniciar`, { destinatario_id: profile.id });
      setShowNewDM(false);
      await loadCanales();
      switchCanal(res.data.canal_id, profile.nombre);
    } catch {}
  };

  const openNewDMDialog = async () => {
    try {
      const res = await api.get(`${API_BASE}/perfiles`);
      setProfiles(res.data.filter((p: UserProfile) => p.id !== user?.id));
      setShowNewDM(true);
    } catch {}
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 shrink-0 border-r border-white/[0.06] flex flex-col bg-white/[0.02]">
        <div className="p-3 border-b border-white/[0.06]">
          <h2 className="text-sm font-semibold text-white">{t('chat.title')}</h2>
        </div>

        {/* Channels */}
        <div className="px-2 py-2">
          <p className="px-2 text-[10px] uppercase text-white/30 font-semibold mb-1">{t('chat.channels')}</p>
          {canales.map(c => (
            <button
              key={c.canal_id}
              onClick={() => switchCanal(c.canal_id, `#${c.label}`)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm ${
                activeCanal === c.canal_id ? 'bg-white/[0.08] text-white' : 'text-white/50 hover:text-white/70 hover:bg-white/[0.04]'
              }`}
            >
              <Hash size={14} /> {c.label}
            </button>
          ))}
        </div>

        {/* DMs */}
        <div className="px-2 py-2 flex-1 min-h-0 overflow-y-auto">
          <div className="flex items-center justify-between px-2 mb-1">
            <p className="text-[10px] uppercase text-white/30 font-semibold">{t('chat.direct_messages')}</p>
            <button onClick={openNewDMDialog} className="p-1 hover:bg-white/[0.06] rounded">
              <Plus size={12} className="text-white/40" />
            </button>
          </div>
          {dms.map(dm => (
            <button
              key={dm.canal_id}
              onClick={() => switchCanal(dm.canal_id, dm.otro_participante.nombre)}
              className={`w-full flex items-center justify-between gap-2 px-2 py-1.5 rounded text-sm ${
                activeCanal === dm.canal_id ? 'bg-white/[0.08] text-white' : 'text-white/50 hover:text-white/70 hover:bg-white/[0.04]'
              }`}
            >
              <span className="truncate">{dm.otro_participante.nombre}</span>
              {dm.no_leidos > 0 && (
                <span className="px-1.5 py-0.5 bg-red-500 text-white text-[10px] rounded-full font-bold">
                  {dm.no_leidos}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Main panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="shrink-0 px-4 py-3 border-b border-white/[0.06] flex items-center gap-2">
          {activeCanal.startsWith('dm_')
            ? <MessageSquare size={16} className="text-white/50" />
            : <Hash size={16} className="text-white/50" />
          }
          <span className="text-sm font-medium text-white">{activeLabel}</span>
        </div>

        {/* Messages */}
        <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-3">
          {loading ? (
            <div className="flex items-center justify-center h-20 text-white/30 text-sm">{t('common.loading')}</div>
          ) : messages.length === 0 ? (
            <div className="flex items-center justify-center h-20 text-white/30 text-sm">{t('chat.no_messages')}</div>
          ) : (
            messages.map(msg => (
              <div key={msg.id}>
                {msg.tipo === 'notificacion_llamada' ? (
                  <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10">
                    <div className="flex items-center gap-2 mb-1">
                      <Phone size={14} className="text-amber-400" />
                      <span className="text-xs font-medium text-amber-400">{t('chat.call_notification')}</span>
                    </div>
                    <p className="text-sm text-white/80">{msg.contenido}</p>
                    {msg.metadata?.descripcion && (
                      <p className="text-xs text-white/50 mt-1">{msg.metadata.descripcion}</p>
                    )}
                  </div>
                ) : msg.tipo === 'notificacion_tarea' ? (
                  <div className="p-3 rounded-lg border border-violet-500/30 bg-violet-500/10">
                    <div className="flex items-center gap-2 mb-1">
                      <Bell size={14} className="text-violet-400" />
                      <span className="text-xs font-medium text-violet-400">{t('chat.task_notification')}</span>
                    </div>
                    <p className="text-sm text-white/80">{msg.contenido}</p>
                  </div>
                ) : (
                  <div className={`flex gap-2 ${msg.autor_id === user?.id ? 'justify-end' : ''}`}>
                    <div className={`max-w-[70%] ${msg.autor_id === user?.id ? 'bg-primary/20 border-primary/30' : 'bg-white/[0.04] border-white/[0.08]'} border rounded-lg px-3 py-2`}>
                      <div className="flex items-baseline gap-2 mb-0.5">
                        <span className="text-xs font-medium text-white/70">{msg.autor_nombre}</span>
                        <span className="text-[10px] text-white/30">
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-sm text-white/80 whitespace-pre-wrap">{msg.contenido}</p>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="shrink-0 px-4 py-3 border-t border-white/[0.06]">
          <div className="flex gap-2">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              maxLength={2000}
              rows={1}
              placeholder={t('chat.type_message')}
              className="flex-1 px-3 py-2 bg-white/[0.05] text-white text-sm border border-white/[0.08] rounded-lg resize-none focus:ring-2 focus:ring-blue-500/30 placeholder:text-white/30"
            />
            <button
              onClick={handleSend}
              disabled={!inputText.trim()}
              className="px-3 py-2 bg-primary text-white rounded-lg hover:bg-blue-700 disabled:opacity-30"
            >
              <Send size={16} />
            </button>
          </div>
          {inputText.length > 1800 && (
            <p className="text-[10px] text-amber-400 mt-1">{inputText.length}/2000</p>
          )}
        </div>
      </div>

      {/* New DM Dialog */}
      {showNewDM && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-[#1a1a2e] border border-white/[0.08] rounded-xl w-full max-w-sm">
            <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
              <h3 className="text-white font-semibold text-sm">{t('chat.new_dm')}</h3>
              <button onClick={() => setShowNewDM(false)} className="text-white/40 hover:text-white">&times;</button>
            </div>
            <div className="p-4 max-h-60 overflow-y-auto space-y-1">
              {profiles.map(p => (
                <button
                  key={p.id}
                  onClick={() => handleNewDM(p)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/[0.04] text-left"
                >
                  <Users size={14} className="text-white/40 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm text-white truncate">{p.nombre}</p>
                    <p className="text-[10px] text-white/30">{p.rol}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
