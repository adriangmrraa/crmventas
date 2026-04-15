import { useState, useEffect, useRef, useMemo } from 'react';
import { Eye, MessageSquare, ShieldAlert, Zap, Clock, User, Bot, Monitor, Phone, Filter } from 'lucide-react';
import { io, Socket } from 'socket.io-client';
import api, { BACKEND_URL } from '../../../api/axios';
import { useAuth } from '../../../context/AuthContext';
import PageHeader from '../../../components/PageHeader';
import GlassCard, { CARD_IMAGES } from '../../../components/GlassCard';

interface LiveMessage {
  tenant_id: number;
  lead_id: string | null;
  phone_number: string;
  content: string;
  role: string;
  channel_source: string;
  is_silenced: boolean;
  timestamp: string;
}

const ROLE_CONFIG: Record<string, { icon: typeof User; color: string; label: string }> = {
  user: { icon: User, color: 'bg-violet-500/20 text-violet-400', label: 'Cliente' },
  assistant: { icon: Bot, color: 'bg-violet-500/20 text-violet-400', label: 'IA' },
  system: { icon: Monitor, color: 'bg-white/10 text-white/40', label: 'Sistema' },
};

const CHANNELS = ['all', 'whatsapp', 'instagram', 'facebook'] as const;

export default function SupervisorDashboard() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<LiveMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [channelFilter, setChannelFilter] = useState<string>('all');
  const [intervened, setIntervened] = useState<Set<string>>(new Set());
  const [activeSessions, setActiveSessions] = useState(0);
  const [urgencyCount, setUrgencyCount] = useState(0);
  const socketRef = useRef<Socket | null>(null);

  // Load real stats on mount
  useEffect(() => {
    const loadStats = async () => {
      try {
        const [sessionsRes, urgenciesRes] = await Promise.allSettled([
          api.get('/admin/core/chat/sessions'),
          api.get('/admin/core/chat/urgencies'),
        ]);
        if (sessionsRes.status === 'fulfilled') {
          setActiveSessions(Array.isArray(sessionsRes.value.data) ? sessionsRes.value.data.length : 0);
        }
        if (urgenciesRes.status === 'fulfilled') {
          const urgencies = Array.isArray(urgenciesRes.value.data) ? urgenciesRes.value.data : [];
          setUrgencyCount(urgencies.filter((u: any) => u.urgency_level === 'URGENT' || u.urgency_level === 'high').length);
        }
      } catch {}
    };
    loadStats();
    const interval = setInterval(loadStats, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!user || !user.tenant_id) return;
    const socket = io(BACKEND_URL);
    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      socket.emit('join', { room: `supervisors:${user.tenant_id}` });
    });
    socket.on('disconnect', () => setIsConnected(false));
    socket.on('SUPERVISOR_CHAT_EVENT', (msg: LiveMessage) => {
      setMessages(prev => [msg, ...prev].slice(0, 50));
    });

    return () => { socket.disconnect(); };
  }, [user]);

  // Calculated stats
  const iaRatio = useMemo(() => {
    if (messages.length === 0) return 0;
    const iaCount = messages.filter(m => m.role === 'assistant').length;
    return Math.round((iaCount / messages.length) * 100);
  }, [messages]);

  const waitingUsers = useMemo(() => {
    const byPhone: Record<string, LiveMessage> = {};
    messages.forEach(m => { byPhone[m.phone_number] = m; });
    const fiveMinAgo = Date.now() - 5 * 60 * 1000;
    return Object.values(byPhone).filter(m =>
      m.role === 'user' && new Date(m.timestamp).getTime() < fiveMinAgo
    ).length;
  }, [messages]);

  const filteredMessages = channelFilter === 'all'
    ? messages
    : messages.filter(m => m.channel_source === channelFilter);

  const handleIntervene = async (phone: string, activate: boolean) => {
    try {
      await api.post('/admin/core/chat/human-intervention', {
        phone, tenant_id: user?.tenant_id, activate,
      });
      setIntervened(prev => {
        const next = new Set(prev);
        activate ? next.add(phone) : next.delete(phone);
        return next;
      });
    } catch {}
  };

  return (
    <div className="h-full overflow-hidden flex flex-col p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Modo Supervisor"
        subtitle="Monitoreo en tiempo real de conversaciones de IA"
        icon={<Eye size={20} className="text-violet-400" />}
        action={
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-[10px] font-bold text-white/60 uppercase tracking-wider">
              {isConnected ? 'LIVE' : 'DISCONNECTED'}
            </span>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-0">
        {/* Stats Column */}
        <div className="lg:col-span-1 space-y-4">
          <GlassCard image={CARD_IMAGES.analytics} className="p-4">
            <h3 className="text-xs font-bold text-white/40 uppercase mb-3">Actividad</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-white/50">Msgs sesion</span>
                <span className="text-lg font-bold text-white">{messages.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-white/50">Convs activas</span>
                <span className="text-lg font-bold text-white">{activeSessions}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-white/50">Ratio IA</span>
                <span className="text-lg font-bold text-violet-400">{iaRatio}%</span>
              </div>
            </div>
          </GlassCard>

          <GlassCard image={CARD_IMAGES.team} className="p-4">
            <h3 className="text-xs font-bold text-white/40 uppercase mb-3">Alertas</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-yellow-500">
                <ShieldAlert size={14} />
                <span className="text-xs font-medium">{urgencyCount} Intervenciones req.</span>
              </div>
              <div className="flex items-center gap-2 text-amber-400">
                <Clock size={14} />
                <span className="text-xs font-medium">{waitingUsers} Esperando &gt;5min</span>
              </div>
              <div className="flex items-center gap-2 text-violet-400">
                <Zap size={14} />
                <span className="text-xs font-medium">{intervened.size} Intervenidos</span>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Live Feed Column */}
        <div className="lg:col-span-3 flex flex-col min-h-0 bg-white/[0.02] rounded-2xl border border-white/5 overflow-hidden">
          <div className="p-4 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <MessageSquare size={16} className="text-violet-400" />
              Live Feed
            </h3>
            <div className="flex items-center gap-2">
              {CHANNELS.map(ch => (
                <button
                  key={ch}
                  onClick={() => setChannelFilter(ch)}
                  className={`px-2 py-1 rounded text-[10px] font-medium uppercase ${
                    channelFilter === ch ? 'bg-violet-500/20 text-violet-400' : 'text-white/30 hover:text-white/50'
                  }`}
                >
                  {ch === 'all' ? 'Todos' : ch}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {filteredMessages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center opacity-20 py-20">
                <Clock size={48} className="mb-4" />
                <p className="text-sm font-medium">Esperando actividad...</p>
              </div>
            ) : (
              filteredMessages.map((msg, i) => {
                const roleConf = ROLE_CONFIG[msg.role] || ROLE_CONFIG.user;
                const RoleIcon = roleConf.icon;
                const isIntervened = intervened.has(msg.phone_number);

                return (
                  <div
                    key={i}
                    className={`flex gap-3 p-3 rounded-xl border transition-all animate-fadeIn ${
                      msg.is_silenced
                        ? 'bg-red-500/5 border-red-500/10'
                        : isIntervened
                        ? 'bg-yellow-500/5 border-yellow-500/10'
                        : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.05]'
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${roleConf.color}`}>
                      <RoleIcon size={18} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start mb-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-bold text-white">{msg.phone_number}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/40 uppercase">
                            {msg.channel_source}
                          </span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${roleConf.color} uppercase font-medium`}>
                            {roleConf.label}
                          </span>
                          {msg.is_silenced && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 uppercase font-black">
                              SILENCED
                            </span>
                          )}
                          {isIntervened && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-400 uppercase font-black">
                              INTERVENIDO
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {msg.role === 'user' && !isIntervened && (
                            <button
                              onClick={() => handleIntervene(msg.phone_number, true)}
                              className="text-[10px] px-2 py-1 bg-yellow-500/10 text-yellow-400 rounded hover:bg-yellow-500/20 font-medium"
                            >
                              Tomar control
                            </button>
                          )}
                          {isIntervened && (
                            <button
                              onClick={() => handleIntervene(msg.phone_number, false)}
                              className="text-[10px] px-2 py-1 bg-green-500/10 text-green-400 rounded hover:bg-green-500/20 font-medium"
                            >
                              Liberar
                            </button>
                          )}
                          <span className="text-[10px] text-white/20">
                            {new Date(msg.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-white/70 break-words">{msg.content}</p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
