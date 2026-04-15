import { useState, useEffect, useRef } from 'react';
import { Eye, MessageSquare, ShieldAlert, Zap, Clock, User } from 'lucide-react';
import { io, Socket } from 'socket.io-client';
import { BACKEND_URL } from '../../../api/axios';
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

export default function SupervisorDashboard() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<LiveMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    if (!user || !user.tenant_id) return;

    // Connect to Socket.IO
    const socket = io(BACKEND_URL);
    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      // Join the supervisor room for this tenant
      socket.emit('join', { room: `supervisors:${user.tenant_id}` });
      console.log(`Joined supervisor room: supervisors:${user.tenant_id}`);
    });

    socket.on('disconnect', () => setIsConnected(false));

    socket.on('SUPERVISOR_CHAT_EVENT', (msg: LiveMessage) => {
      setMessages(prev => [msg, ...prev].slice(0, 50)); // Keep last 50
    });

    return () => {
      socket.disconnect();
    };
  }, [user]);

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
            <h3 className="text-xs font-bold text-white/40 uppercase mb-3">Actividad Total</h3>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold text-white">{messages.length}</span>
              <span className="text-xs text-white/30 pb-1">msgs en sesión</span>
            </div>
          </GlassCard>

          <GlassCard image={CARD_IMAGES.team} className="p-4">
            <h3 className="text-xs font-bold text-white/40 uppercase mb-3">Alertas Críticas</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-yellow-500">
                <ShieldAlert size={14} />
                <span className="text-xs font-medium">0 Intervenciones req.</span>
              </div>
              <div className="flex items-center gap-2 text-violet-400">
                <Zap size={14} />
                <span className="text-xs font-medium">Buscando patrones...</span>
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
            <span className="text-[10px] text-white/30 uppercase font-medium">Últimos 50 mensajes</span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-hide">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center opacity-20 py-20">
                <Clock size={48} className="mb-4" />
                <p className="text-sm font-medium">Esperando actividad...</p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div 
                  key={i} 
                  className={`flex gap-3 p-3 rounded-xl border transition-all animate-fadeIn ${
                    msg.is_silenced 
                      ? 'bg-red-500/5 border-red-500/10' 
                      : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.05]'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                    msg.is_silenced ? 'bg-red-500/20 text-red-400' : 'bg-violet-500/20 text-violet-400'
                  }`}>
                    <User size={18} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start mb-1">
                      <div>
                        <span className="text-xs font-bold text-white">{msg.phone_number}</span>
                        <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/40 uppercase">
                          {msg.channel_source}
                        </span>
                        {msg.is_silenced && (
                          <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 uppercase font-black">
                            SILENCED
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-white/20">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-white/70 break-words">{msg.content}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
