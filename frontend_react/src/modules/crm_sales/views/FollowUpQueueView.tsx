import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Clock, AlertTriangle, Phone, Calendar, ChevronDown, ChevronUp,
  Loader2, AlertCircle, RefreshCw, Filter, CheckCircle2, FileText,
  X, Search, ExternalLink
} from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import { TagBadge, type LeadTag } from '../../../components/leads/TagBadge';

const SELLERS_BASE = '/admin/core/sellers';

interface FollowUpLead {
  id: string;
  phone_number: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  company?: string;
  status: string;
  source?: string;
  lead_source?: string;
  score?: number;
  tags?: LeadTag[];
  estimated_value?: number;
  next_contact_date?: string;
  last_note_content?: string;
  last_note_at?: string;
  days_since_last_contact?: number;
  is_overdue?: boolean;
  created_at: string;
  updated_at: string;
}

type TimeFilter = 'all' | 'overdue' | 'today' | 'this_week';

interface CompleteFollowUpForm {
  result: string;
  notes: string;
  reschedule_date: string;
}

export default function FollowUpQueueView() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [leads, setLeads] = useState<FollowUpLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [completingId, setCompletingId] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [selectedLead, setSelectedLead] = useState<FollowUpLead | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<CompleteFollowUpForm>({
    result: 'contacted',
    notes: '',
    reschedule_date: '',
  });

  const fetchQueue = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = timeFilter !== 'all' ? `?filter=${timeFilter}` : '';
      const res = await api.get(`${SELLERS_BASE}/follow-up-queue${params}`);
      const data = res.data as { success: boolean; leads: FollowUpLead[]; count: number };
      setLeads(data.leads || []);
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Error al cargar la cola de seguimientos';
      setError(String(message));
    } finally {
      setLoading(false);
    }
  }, [timeFilter]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const filteredLeads = leads.filter((lead) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const name = `${lead.first_name || ''} ${lead.last_name || ''}`.toLowerCase();
    return (
      name.includes(q) ||
      lead.phone_number.includes(q) ||
      (lead.company || '').toLowerCase().includes(q) ||
      (lead.email || '').toLowerCase().includes(q)
    );
  });

  const openCompleteModal = (lead: FollowUpLead) => {
    setSelectedLead(lead);
    setForm({ result: 'contacted', notes: '', reschedule_date: '' });
    setShowModal(true);
  };

  const handleCompleteFollowUp = async () => {
    if (!selectedLead) return;
    try {
      setSubmitting(true);
      const payload: any = {
        result: form.result,
        notes: form.notes,
      };
      if (form.reschedule_date) {
        payload.reschedule_date = new Date(form.reschedule_date).toISOString();
      }
      await api.post(`${SELLERS_BASE}/follow-up-queue/${selectedLead.id}/complete-followup`, payload);
      setShowModal(false);
      setSelectedLead(null);
      fetchQueue();
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Error al completar seguimiento';
      alert(message);
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '--';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  const getLeadName = (lead: FollowUpLead) => {
    const name = `${lead.first_name || ''} ${lead.last_name || ''}`.trim();
    return name || lead.phone_number;
  };

  const overdueCount = leads.filter(l => l.is_overdue).length;
  const todayCount = leads.filter(l => {
    if (!l.next_contact_date) return false;
    const d = new Date(l.next_contact_date);
    const now = new Date();
    return d.toDateString() === now.toDateString();
  }).length;

  // ========= RENDER =========

  if (loading && leads.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
        <span className="ml-3 text-white/60">Cargando seguimientos...</span>
      </div>
    );
  }

  if (error && leads.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
        <h2 className="text-lg font-bold text-white mb-2">Error al cargar seguimientos</h2>
        <p className="text-sm text-white/40 max-w-md font-mono bg-red-500/10 p-3 rounded-lg border border-red-500/20">{error}</p>
        <button
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700"
          onClick={fetchQueue}
        >Reintentar</button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col p-4 lg:p-6 space-y-4">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-white flex items-center gap-2">
            <Clock className="w-6 h-6 text-blue-400" />
            Cola de Seguimientos
          </h1>
          <p className="text-sm text-white/50 mt-1">
            {leads.length} leads pendientes de seguimiento
            {overdueCount > 0 && (
              <span className="ml-2 text-red-400 font-semibold">
                ({overdueCount} vencidos)
              </span>
            )}
          </p>
        </div>
        <button
          onClick={fetchQueue}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-white/70 hover:text-white hover:border-blue-500/50 transition-all text-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Actualizar
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3">
          <p className="text-xs text-white/40 uppercase">Total</p>
          <p className="text-2xl font-bold text-white">{leads.length}</p>
        </div>
        <div className="bg-white/[0.02] border border-red-500/20 rounded-xl p-3">
          <p className="text-xs text-red-400 uppercase">Vencidos</p>
          <p className="text-2xl font-bold text-red-400">{overdueCount}</p>
        </div>
        <div className="bg-white/[0.02] border border-yellow-500/20 rounded-xl p-3">
          <p className="text-xs text-yellow-400 uppercase">Hoy</p>
          <p className="text-2xl font-bold text-yellow-400">{todayCount}</p>
        </div>
        <div className="bg-white/[0.02] border border-green-500/20 rounded-xl p-3">
          <p className="text-xs text-green-400 uppercase">Esta Semana</p>
          <p className="text-2xl font-bold text-green-400">{leads.length - overdueCount}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <input
            type="text"
            placeholder="Buscar por nombre, telefono, empresa..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-white placeholder-white/30 text-sm focus:outline-none focus:border-blue-500/50"
          />
        </div>
        <div className="flex gap-2">
          {(['all', 'overdue', 'today', 'this_week'] as TimeFilter[]).map((f) => (
            <button
              key={f}
              onClick={() => setTimeFilter(f)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                timeFilter === f
                  ? 'bg-blue-600 text-white'
                  : 'bg-white/[0.03] text-white/50 hover:text-white border border-white/[0.06]'
              }`}
            >
              {f === 'all' && 'Todos'}
              {f === 'overdue' && 'Vencidos'}
              {f === 'today' && 'Hoy'}
              {f === 'this_week' && 'Semana'}
            </button>
          ))}
        </div>
      </div>

      {/* Lead List */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {filteredLeads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <CheckCircle2 className="w-12 h-12 text-green-400/50 mb-3" />
            <p className="text-white/50 text-sm">
              {search ? 'No hay resultados para la busqueda.' : 'No hay seguimientos pendientes. Todo al dia!'}
            </p>
          </div>
        ) : (
          filteredLeads.map((lead) => {
            const isExpanded = expandedId === lead.id;
            return (
              <div
                key={lead.id}
                className={`bg-white/[0.02] border rounded-xl transition-all ${
                  lead.is_overdue
                    ? 'border-red-500/30 bg-red-500/5'
                    : 'border-white/5 hover:border-white/[0.06]'
                }`}
              >
                {/* Main Row */}
                <div
                  className="flex items-center gap-3 p-4 cursor-pointer"
                  onClick={() => setExpandedId(isExpanded ? null : lead.id)}
                >
                  {/* Overdue Badge */}
                  <div className="flex-shrink-0">
                    {lead.is_overdue ? (
                      <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                        <AlertTriangle className="w-5 h-5 text-red-400" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <Clock className="w-5 h-5 text-blue-400" />
                      </div>
                    )}
                  </div>

                  {/* Lead Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-semibold text-sm truncate">
                        {getLeadName(lead)}
                      </span>
                      {lead.is_overdue && (
                        <span className="flex-shrink-0 px-2 py-0.5 bg-red-500/20 text-red-400 text-xs font-bold rounded-full">
                          VENCIDO
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Phone className="w-3 h-3 text-white/30" />
                      <span className="text-xs text-white/40">{lead.phone_number}</span>
                      {lead.company && (
                        <>
                          <span className="text-white/20">|</span>
                          <span className="text-xs text-white/40">{lead.company}</span>
                        </>
                      )}
                    </div>
                    {/* Tags */}
                    {lead.tags && lead.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {(lead.tags as any[]).map((tag: any, idx: number) => {
                          const tagName = typeof tag === 'string' ? tag : tag.name;
                          return (
                            <span
                              key={idx}
                              className="px-1.5 py-0.5 bg-white/5 text-white/50 text-[10px] rounded-md"
                            >
                              {tagName}
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Right Info */}
                  <div className="flex-shrink-0 text-right">
                    <div className="flex items-center gap-1 text-xs text-white/40">
                      <Calendar className="w-3 h-3" />
                      <span className={lead.is_overdue ? 'text-red-400 font-semibold' : ''}>
                        {formatDate(lead.next_contact_date)}
                      </span>
                    </div>
                    {lead.days_since_last_contact != null && (
                      <p className="text-[10px] text-white/30 mt-0.5">
                        {lead.days_since_last_contact} dias sin contacto
                      </p>
                    )}
                  </div>

                  {/* Expand Arrow */}
                  <div className="flex-shrink-0">
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-white/30" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-white/30" />
                    )}
                  </div>
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-white/5 pt-3 space-y-3">
                    {/* Last Note */}
                    {lead.last_note_content && (
                      <div className="bg-white/[0.03] rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="w-3.5 h-3.5 text-white/40" />
                          <span className="text-xs text-white/40 font-medium">Ultima nota</span>
                          <span className="text-[10px] text-white/30 ml-auto">{formatDate(lead.last_note_at)}</span>
                        </div>
                        <p className="text-sm text-white/70 line-clamp-3">{lead.last_note_content}</p>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); openCompleteModal(lead); }}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-all"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        Completar Seguimiento
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); navigate(`/crm/leads/${lead.id}`); }}
                        className="flex items-center gap-2 px-3 py-2 bg-white/[0.03] border border-white/[0.06] text-white/70 hover:text-white text-sm rounded-lg transition-all"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Ver Ficha
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Complete Follow-Up Modal */}
      {showModal && selectedLead && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#1a1a2e] border border-white/[0.08] rounded-2xl w-full max-w-lg shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-white/[0.06]">
              <div>
                <h3 className="text-lg font-bold text-white">Completar Seguimiento</h3>
                <p className="text-sm text-white/40 mt-0.5">{getLeadName(selectedLead)} - {selectedLead.phone_number}</p>
              </div>
              <button onClick={() => setShowModal(false)} className="text-white/30 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4">
              {/* Result */}
              <div>
                <label className="block text-sm text-white/60 mb-1.5 font-medium">Resultado</label>
                <select
                  value={form.result}
                  onChange={(e) => setForm({ ...form, result: e.target.value })}
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/50"
                >
                  <option value="contacted" className="bg-[#1a1a2e] text-white">Contactado</option>
                  <option value="no_answer" className="bg-[#1a1a2e] text-white">No contesto</option>
                  <option value="rescheduled" className="bg-[#1a1a2e] text-white">Reagendado</option>
                  <option value="completed" className="bg-[#1a1a2e] text-white">Completado (cerrado ganado)</option>
                  <option value="lost" className="bg-[#1a1a2e] text-white">Perdido</option>
                </select>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm text-white/60 mb-1.5 font-medium">Notas</label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  rows={3}
                  placeholder="Describe el resultado del seguimiento..."
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-white placeholder-white/30 text-sm focus:outline-none focus:border-blue-500/50 resize-none"
                />
              </div>

              {/* Reschedule Date */}
              <div>
                <label className="block text-sm text-white/60 mb-1.5 font-medium">
                  Reagendar para (opcional)
                </label>
                <input
                  type="datetime-local"
                  value={form.reschedule_date}
                  onChange={(e) => setForm({ ...form, reschedule_date: e.target.value })}
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/50"
                />
                <p className="text-[10px] text-white/30 mt-1">
                  Si se completa, se creara un nuevo evento en agenda y se re-agrega la etiqueta "requiere_seguimiento".
                </p>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 p-5 border-t border-white/[0.06]">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-white/50 hover:text-white transition-all"
              >
                Cancelar
              </button>
              <button
                onClick={handleCompleteFollowUp}
                disabled={submitting || !form.notes.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-all"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                Completar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
