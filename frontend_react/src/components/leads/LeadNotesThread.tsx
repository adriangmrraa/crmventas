import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send, Loader2, AlertCircle, MessageSquare, ArrowRightLeft,
  PhoneCall, CheckCircle2, Clock, AlertTriangle, ArrowRight
} from 'lucide-react';
import api from '../../api/axios';
import { useAuth } from '../../context/AuthContext';
import { useSocket } from '../../context/SocketContext';

interface LeadNote {
  id: string;
  lead_id: string;
  author_id: string;
  author_name: string;
  author_role: string;
  type: 'general' | 'handoff' | 'post_call' | 'system';
  content: string;
  // Post-call structured data
  result?: string;
  objections?: string;
  next_steps?: string;
  next_contact_date?: string;
  created_at: string;
}

interface LeadNotesThreadProps {
  leadId: string;
}

const CRM_LEADS_BASE = '/admin/core/crm/leads';

const ROLE_COLORS: Record<string, string> = {
  ceo: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  setter: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  closer: 'bg-green-500/20 text-green-400 border-green-500/30',
  secretary: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  professional: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  system: 'bg-white/10 text-white/40 border-white/10',
};

const RESULT_LABELS: Record<string, { label: string; color: string }> = {
  connected: { label: 'Conectada', color: 'text-green-400 bg-green-500/10 border-green-500/20' },
  no_answer: { label: 'No contesto', color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' },
  voicemail: { label: 'Buzon de voz', color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' },
  rescheduled: { label: 'Reagendada', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  closed_won: { label: 'Cerrada - Ganada', color: 'text-green-400 bg-green-500/10 border-green-500/20' },
  closed_lost: { label: 'Cerrada - Perdida', color: 'text-red-400 bg-red-500/10 border-red-500/20' },
  follow_up: { label: 'Requiere seguimiento', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
};

export default function LeadNotesThread({ leadId }: LeadNotesThreadProps) {
  const { user } = useAuth();
  const { socket, isConnected } = useSocket();
  const [notes, setNotes] = useState<LeadNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newNote, setNewNote] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchNotes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<LeadNote[]>(`${CRM_LEADS_BASE}/${leadId}/notes`);
      setNotes(res.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar notas');
    } finally {
      setLoading(false);
    }
  }, [leadId]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  // Auto-scroll when new notes arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [notes]);

  // Real-time Socket.IO updates
  useEffect(() => {
    if (!socket || !isConnected) return;

    const handleNewNote = (data: LeadNote) => {
      if (data.lead_id === leadId) {
        setNotes((prev) => {
          // Avoid duplicates
          if (prev.some((n) => n.id === data.id)) return prev;
          return [...prev, data];
        });
      }
    };

    socket.on('LEAD_NOTE_CREATED', handleNewNote);
    return () => {
      socket.off('LEAD_NOTE_CREATED', handleNewNote);
    };
  }, [socket, isConnected, leadId]);

  const handleSend = async () => {
    if (!newNote.trim()) return;
    try {
      setSending(true);
      const res = await api.post<LeadNote>(`${CRM_LEADS_BASE}/${leadId}/notes`, {
        type: 'general',
        content: newNote.trim(),
      });
      // Optimistic add if not already received via socket
      setNotes((prev) => {
        if (prev.some((n) => n.id === res.data.id)) return prev;
        return [...prev, res.data];
      });
      setNewNote('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al enviar nota');
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase();
  };

  const formatTimestamp = (dateStr: string) => {
    try {
      return new Intl.DateTimeFormat('es', {
        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
      }).format(new Date(dateStr));
    } catch { return dateStr; }
  };

  const renderNote = (note: LeadNote) => {
    const isHandoff = note.type === 'handoff';
    const isPostCall = note.type === 'post_call';
    const isSystem = note.type === 'system';
    const roleClass = ROLE_COLORS[note.author_role] || ROLE_COLORS.system;

    return (
      <div
        key={note.id}
        className={`flex gap-3 ${isHandoff ? 'pl-2' : ''}`}
      >
        {/* Avatar */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
          isSystem ? 'bg-white/[0.06] text-white/30' : 'bg-white/[0.08] text-white/60'
        }`}>
          {isSystem ? <MessageSquare size={14} /> : getInitials(note.author_name)}
        </div>

        {/* Content */}
        <div className={`flex-1 min-w-0 ${
          isHandoff
            ? 'border-l-2 border-amber-500/40 pl-3'
            : isPostCall
              ? 'border-l-2 border-green-500/40 pl-3'
              : ''
        }`}>
          {/* Header */}
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-sm font-medium text-white/80">{note.author_name}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-medium ${roleClass}`}>
              {note.author_role}
            </span>
            {isHandoff && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium flex items-center gap-0.5">
                <ArrowRightLeft size={9} />
                Handoff
              </span>
            )}
            {isPostCall && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20 font-medium flex items-center gap-0.5">
                <PhoneCall size={9} />
                Post-llamada
              </span>
            )}
            <span className="text-[10px] text-white/25 flex items-center gap-0.5">
              <Clock size={9} />
              {formatTimestamp(note.created_at)}
            </span>
          </div>

          {/* Body */}
          {note.content && (
            <p className="text-sm text-white/60 whitespace-pre-wrap">{note.content}</p>
          )}

          {/* Post-call structured data */}
          {isPostCall && (
            <div className="mt-2 space-y-1.5">
              {note.result && (
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 size={11} className="text-white/30" />
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                    RESULT_LABELS[note.result]?.color || 'text-white/50 bg-white/[0.04] border-white/[0.08]'
                  }`}>
                    {RESULT_LABELS[note.result]?.label || note.result}
                  </span>
                </div>
              )}
              {note.objections && (
                <div className="flex items-start gap-1.5">
                  <AlertTriangle size={11} className="text-white/30 mt-0.5" />
                  <span className="text-xs text-white/40"><strong className="text-white/50">Objeciones:</strong> {note.objections}</span>
                </div>
              )}
              {note.next_steps && (
                <div className="flex items-start gap-1.5">
                  <ArrowRight size={11} className="text-white/30 mt-0.5" />
                  <span className="text-xs text-white/40"><strong className="text-white/50">Proximos pasos:</strong> {note.next_steps}</span>
                </div>
              )}
              {note.next_contact_date && (
                <div className="flex items-center gap-1.5">
                  <Clock size={11} className="text-white/30" />
                  <span className="text-xs text-white/40">
                    <strong className="text-white/50">Proximo contacto:</strong> {formatTimestamp(note.next_contact_date)}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare size={16} className="text-white/40" />
        <h3 className="text-sm font-semibold text-white/70">Notas del equipo</h3>
        <span className="text-xs text-white/30 bg-white/[0.04] px-2 py-0.5 rounded-full">
          {notes.length}
        </span>
      </div>

      {error && (
        <div className="mb-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs flex items-center gap-2">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {/* Notes list */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto space-y-4 mb-3 max-h-96"
      >
        {loading ? (
          <div className="flex items-center justify-center py-8 text-white/30">
            <Loader2 size={18} className="animate-spin mr-2" />
            <span className="text-sm">Cargando notas...</span>
          </div>
        ) : notes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <MessageSquare size={24} className="text-white/10 mb-2" />
            <p className="text-sm text-white/30">No hay notas aun. Se el primero en agregar una.</p>
          </div>
        ) : (
          notes.map(renderNote)
        )}
      </div>

      {/* Input */}
      <div className="flex items-end gap-2 pt-2 border-t border-white/[0.06]">
        <textarea
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Escribe una nota..."
          className="flex-1 px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-white/30 focus:ring-2 focus:ring-medical-500/40 resize-none"
        />
        <button
          onClick={handleSend}
          disabled={!newNote.trim() || sending}
          className="p-2 bg-medical-600 text-white rounded-lg hover:bg-medical-700 disabled:opacity-50 transition-colors shrink-0"
        >
          {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </div>
    </div>
  );
}
