import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PhoneCall, Calendar, ChevronDown, ChevronUp, Loader2, AlertCircle,
  RefreshCw, Clock, CheckCircle2, User, Tag, MessageSquare, X, Save
} from 'lucide-react';
import api from '../../../api/axios';
import { TagBadge, type LeadTag } from '../../../components/leads/TagBadge';
import ScoreBadge from '../../../components/leads/ScoreBadge';

const SELLERS_BASE = '/admin/core/sellers';

interface CloserCall {
  id: string;
  lead_id: string;
  lead_name: string;
  phone_number: string;
  scheduled_at: string;
  setter_name?: string;
  handoff_note?: string;
  tags?: LeadTag[];
  score?: number;
  status?: string;
  chat_history_preview?: string[];
  notes_preview?: string;
}

interface GroupedCalls {
  hoy: CloserCall[];
  manana: CloserCall[];
  esta_semana: CloserCall[];
  mas_adelante: CloserCall[];
}

const CALL_RESULTS = [
  { value: 'connected', label: 'Conectada - Hablo con prospecto' },
  { value: 'no_answer', label: 'No contesto' },
  { value: 'voicemail', label: 'Buzon de voz' },
  { value: 'rescheduled', label: 'Reagendada' },
  { value: 'closed_won', label: 'Cerrada - Ganada' },
  { value: 'closed_lost', label: 'Cerrada - Perdida' },
  { value: 'follow_up', label: 'Requiere seguimiento' },
];

export default function CloserPanelView() {
  const navigate = useNavigate();
  const [calls, setCalls] = useState<GroupedCalls>({
    hoy: [], manana: [], esta_semana: [], mas_adelante: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [postCallId, setPostCallId] = useState<string | null>(null);
  const [markingId, setMarkingId] = useState<string | null>(null);

  // Post-call note form
  const [postCallForm, setPostCallForm] = useState({
    result: '',
    objections: '',
    next_steps: '',
    next_contact_date: '',
  });
  const [submittingNote, setSubmittingNote] = useState(false);

  const fetchPanel = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<GroupedCalls>(`${SELLERS_BASE}/closer-panel`);
      setCalls(res.data || { hoy: [], manana: [], esta_semana: [], mas_adelante: [] });
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Error al cargar el panel';
      setError(String(message));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPanel();
  }, [fetchPanel]);

  const handleMarkDone = async (callId: string) => {
    setPostCallId(callId);
    setPostCallForm({ result: '', objections: '', next_steps: '', next_contact_date: '' });
  };

  const handleSubmitPostCall = async () => {
    if (!postCallId || !postCallForm.result) return;
    try {
      setSubmittingNote(true);
      // Find the call to get lead_id
      const allCalls = [...calls.hoy, ...calls.manana, ...calls.esta_semana, ...calls.mas_adelante];
      const call = allCalls.find((c) => c.id === postCallId);
      if (!call) return;

      await api.post(`/admin/core/crm/leads/${call.lead_id}/notes`, {
        type: 'post_call',
        content: postCallForm.objections,
        result: postCallForm.result,
        objections: postCallForm.objections,
        next_steps: postCallForm.next_steps,
        next_contact_date: postCallForm.next_contact_date || undefined,
        call_id: postCallId,
      });

      // Remove call from lists
      setCalls((prev) => {
        const remove = (arr: CloserCall[]) => arr.filter((c) => c.id !== postCallId);
        return {
          hoy: remove(prev.hoy),
          manana: remove(prev.manana),
          esta_semana: remove(prev.esta_semana),
          mas_adelante: remove(prev.mas_adelante),
        };
      });

      setPostCallId(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar la nota');
    } finally {
      setSubmittingNote(false);
    }
  };

  const formatTime = (dateStr: string) => {
    try {
      return new Intl.DateTimeFormat('es', {
        hour: '2-digit', minute: '2-digit',
      }).format(new Date(dateStr));
    } catch { return dateStr; }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Intl.DateTimeFormat('es', {
        weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
      }).format(new Date(dateStr));
    } catch { return dateStr; }
  };

  const renderCallCard = (call: CloserCall) => {
    const isExpanded = expandedId === call.id;

    return (
      <div
        key={call.id}
        className="bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden hover:bg-white/[0.03] transition-colors"
      >
        {/* Card header */}
        <div
          className="p-4 cursor-pointer"
          onClick={() => setExpandedId(isExpanded ? null : call.id)}
        >
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <button
                  onClick={(e) => { e.stopPropagation(); navigate(`/crm/leads/${call.lead_id}`); }}
                  className="text-sm font-semibold text-white hover:text-blue-400 transition-colors"
                >
                  {call.lead_name || 'Sin nombre'}
                </button>
                <ScoreBadge score={call.score} size="sm" />
              </div>

              <div className="flex items-center gap-3 text-xs text-white/40 mb-2">
                <span className="flex items-center gap-1">
                  <Clock size={11} />
                  {formatTime(call.scheduled_at)}
                </span>
                {call.setter_name && (
                  <span className="flex items-center gap-1">
                    <User size={11} />
                    Setter: {call.setter_name}
                  </span>
                )}
              </div>

              {/* Handoff note preview */}
              {call.handoff_note && (
                <p className="text-xs text-white/40 line-clamp-1 italic">
                  "{call.handoff_note}"
                </p>
              )}

              {/* Tags */}
              {call.tags && call.tags.length > 0 && (
                <div className="flex items-center gap-1 flex-wrap mt-2">
                  {call.tags.map((tag, i) => (
                    <TagBadge key={`${tag.name}-${i}`} tag={tag} />
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={(e) => { e.stopPropagation(); handleMarkDone(call.id); }}
                className="flex items-center gap-1 px-2.5 py-1.5 bg-green-500/10 text-green-400 border border-green-500/20 rounded-lg text-xs font-medium hover:bg-green-500/20 transition-colors"
              >
                <CheckCircle2 size={12} />
                Marcar realizada
              </button>
              {isExpanded ? <ChevronUp size={16} className="text-white/30" /> : <ChevronDown size={16} className="text-white/30" />}
            </div>
          </div>
        </div>

        {/* Expanded section */}
        {isExpanded && (
          <div className="border-t border-white/[0.06] p-4 bg-white/[0.01] space-y-3">
            {/* Full handoff note */}
            {call.handoff_note && (
              <div className="p-3 bg-amber-500/5 border border-amber-500/10 rounded-lg">
                <p className="text-xs font-medium text-amber-400 mb-1 flex items-center gap-1">
                  <MessageSquare size={11} />
                  Nota de handoff del setter
                </p>
                <p className="text-sm text-white/60">{call.handoff_note}</p>
              </div>
            )}

            {/* Chat history preview */}
            {call.chat_history_preview && call.chat_history_preview.length > 0 && (
              <div>
                <p className="text-xs font-medium text-white/40 mb-2">Historial de chat reciente:</p>
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {call.chat_history_preview.map((msg, i) => (
                    <div key={i} className="text-xs text-white/40 p-2 bg-white/[0.02] rounded-lg">
                      {msg}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Notes preview */}
            {call.notes_preview && (
              <div>
                <p className="text-xs font-medium text-white/40 mb-1">Notas previas:</p>
                <p className="text-sm text-white/50">{call.notes_preview}</p>
              </div>
            )}

            <div className="flex gap-2 pt-1">
              <button
                onClick={() => navigate(`/crm/leads/${call.lead_id}`)}
                className="text-xs text-blue-400 hover:text-blue-300 font-medium"
              >
                Ver lead completo
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderGroup = (title: string, items: CloserCall[], color: string) => {
    if (items.length === 0) return null;
    return (
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          <div className={`w-2 h-2 rounded-full ${color}`} />
          <h3 className="text-sm font-semibold text-white/70">{title}</h3>
          <span className="text-xs text-white/30 bg-white/[0.04] px-2 py-0.5 rounded-full">{items.length}</span>
        </div>
        <div className="space-y-2">
          {items.map(renderCallCard)}
        </div>
      </div>
    );
  };

  const totalCalls = calls.hoy.length + calls.manana.length + calls.esta_semana.length + calls.mas_adelante.length;

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-4 p-4 lg:p-6 border-b border-white/[0.06] bg-white/[0.03] shrink-0">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="p-2 rounded-xl bg-green-500/10 border border-green-500/20">
            <PhoneCall size={22} className="text-green-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-white">Panel del Closer</h1>
            <p className="text-sm text-white/40">
              {totalCalls} llamada{totalCalls !== 1 ? 's' : ''} programada{totalCalls !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        <button
          onClick={fetchPanel}
          disabled={loading}
          className="p-2 rounded-lg hover:bg-white/[0.04] text-white/50 hover:text-white transition-colors"
          title="Refrescar"
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6">
        {error && (
          <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center gap-2">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12 text-white/40">
            <Loader2 size={24} className="animate-spin mr-2" />
            Cargando panel...
          </div>
        ) : totalCalls === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Calendar size={48} className="text-white/10 mb-4" />
            <h3 className="text-lg font-medium text-white/50 mb-1">Sin llamadas programadas</h3>
            <p className="text-sm text-white/30">No tienes llamadas pendientes en este momento.</p>
          </div>
        ) : (
          <>
            {renderGroup('Hoy', calls.hoy, 'bg-red-400')}
            {renderGroup('Manana', calls.manana, 'bg-orange-400')}
            {renderGroup('Esta semana', calls.esta_semana, 'bg-blue-400')}
            {renderGroup('Mas adelante', calls.mas_adelante, 'bg-white/30')}
          </>
        )}
      </div>

      {/* Post-call note modal */}
      {postCallId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#1a1a2e] border border-white/[0.08] rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between p-5 border-b border-white/[0.06]">
              <h2 className="text-lg font-semibold text-white">Registrar nota post-llamada</h2>
              <button
                onClick={() => setPostCallId(null)}
                className="p-1.5 rounded-lg hover:bg-white/[0.06] text-white/40 hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {/* Result */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Resultado de la llamada *</label>
                <select
                  value={postCallForm.result}
                  onChange={(e) => setPostCallForm((f) => ({ ...f, result: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white focus:ring-2 focus:ring-green-500/40 focus:border-green-500/40"
                >
                  <option value="" className="bg-[#1a1a2e] text-white">Seleccionar resultado...</option>
                  {CALL_RESULTS.map((r) => (
                    <option key={r.value} value={r.value} className="bg-[#1a1a2e] text-white">{r.label}</option>
                  ))}
                </select>
              </div>

              {/* Objections */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Objeciones</label>
                <textarea
                  value={postCallForm.objections}
                  onChange={(e) => setPostCallForm((f) => ({ ...f, objections: e.target.value }))}
                  rows={3}
                  placeholder="Que objeciones tuvo el prospecto..."
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-white/30 focus:ring-2 focus:ring-green-500/40 resize-none"
                />
              </div>

              {/* Next steps */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Proximos pasos</label>
                <textarea
                  value={postCallForm.next_steps}
                  onChange={(e) => setPostCallForm((f) => ({ ...f, next_steps: e.target.value }))}
                  rows={2}
                  placeholder="Que se acordo para seguir..."
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-white/30 focus:ring-2 focus:ring-green-500/40 resize-none"
                />
              </div>

              {/* Next contact date */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Fecha proximo contacto</label>
                <input
                  type="datetime-local"
                  value={postCallForm.next_contact_date}
                  onChange={(e) => setPostCallForm((f) => ({ ...f, next_contact_date: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white focus:ring-2 focus:ring-green-500/40"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 p-5 border-t border-white/[0.06]">
              <button
                onClick={() => setPostCallId(null)}
                className="px-4 py-2 text-sm font-medium text-white/50 hover:text-white bg-white/[0.03] hover:bg-white/[0.06] rounded-lg border border-white/[0.06] transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleSubmitPostCall}
                disabled={!postCallForm.result || submittingNote}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg disabled:opacity-50 transition-colors"
              >
                {submittingNote ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                Guardar nota
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
