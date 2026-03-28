import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Inbox, UserCheck, ArrowRight, Search, Filter, Flame, Thermometer, Snowflake,
  Calendar, Phone, Loader2, AlertCircle, RefreshCw, ChevronDown, X, Bot
} from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import { TagBadge, type LeadTag } from '../../../components/leads/TagBadge';
import ScoreBadge from '../../../components/leads/ScoreBadge';
import DeriveToCloserModal from '../../../components/leads/DeriveToCloserModal';

const SELLERS_BASE = '/admin/core/sellers';

interface QueueLead {
  id: string;
  phone_number: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  status: string;
  score?: number;
  tags?: LeadTag[];
  ai_summary?: string;
  source?: string;
  priority?: 'hot' | 'warm' | 'cold';
  upcoming_meeting?: {
    id: string;
    title: string;
    date: string;
  } | null;
  created_at: string;
}

type PriorityFilter = 'all' | 'hot' | 'warm' | 'cold';

export default function SetterQueueView() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [leads, setLeads] = useState<QueueLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>('all');
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [takingId, setTakingId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [deriveLeadId, setDeriveLeadId] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<QueueLead[]>(`${SELLERS_BASE}/my-queue`);
      setLeads(res.data || []);
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Error al cargar la cola';
      setError(String(message));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const handleTake = async (leadId: string) => {
    try {
      setTakingId(leadId);
      await api.post(`${SELLERS_BASE}/my-queue/${leadId}/take`);
      // Remove from queue after taking
      setLeads((prev) => prev.filter((l) => l.id !== leadId));
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Error al tomar el lead';
      setError(String(message));
    } finally {
      setTakingId(null);
    }
  };

  const getPriorityFromScore = (score?: number): 'hot' | 'warm' | 'cold' => {
    if (!score) return 'cold';
    if (score >= 80) return 'hot';
    if (score >= 50) return 'warm';
    return 'cold';
  };

  // Collect all unique tag names for filter dropdown
  const allTags = Array.from(
    new Set(leads.flatMap((l) => (l.tags || []).map((tag) => tag.name)))
  );

  const filteredLeads = leads.filter((lead) => {
    // Search filter
    if (search) {
      const q = search.toLowerCase();
      const name = `${lead.first_name || ''} ${lead.last_name || ''}`.toLowerCase();
      if (!name.includes(q) && !lead.phone_number.includes(q)) return false;
    }
    // Priority filter
    if (priorityFilter !== 'all') {
      const p = lead.priority || getPriorityFromScore(lead.score);
      if (p !== priorityFilter) return false;
    }
    // Tag filter
    if (tagFilter) {
      if (!(lead.tags || []).some((tag) => tag.name === tagFilter)) return false;
    }
    return true;
  });

  const formatDate = (dateStr: string) => {
    try {
      return new Intl.DateTimeFormat('es', {
        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
      }).format(new Date(dateStr));
    } catch { return dateStr; }
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-4 p-4 lg:p-6 border-b border-white/[0.06] bg-white/[0.03] shrink-0">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20">
            <Inbox size={22} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-white">Cola del Setter</h1>
            <p className="text-sm text-white/40">
              {filteredLeads.length} lead{filteredLeads.length !== 1 ? 's' : ''} en cola
            </p>
          </div>
        </div>

        <button
          onClick={fetchQueue}
          disabled={loading}
          className="p-2 rounded-lg hover:bg-white/[0.04] text-white/50 hover:text-white transition-colors"
          title="Refrescar"
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Search & Filters */}
      <div className="p-4 lg:px-6 border-b border-white/[0.06] space-y-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              placeholder="Buscar por nombre o telefono..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-white/30 focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/40"
            />
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60">
                <X size={14} />
              </button>
            )}
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
              showFilters || priorityFilter !== 'all' || tagFilter
                ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                : 'bg-white/[0.03] text-white/50 border-white/[0.06] hover:bg-white/[0.04]'
            }`}
          >
            <Filter size={16} />
            Filtros
          </button>
        </div>

        {showFilters && (
          <div className="flex items-center gap-3 flex-wrap">
            {/* Priority filter */}
            <div className="flex items-center gap-1.5 bg-white/[0.02] rounded-lg p-1 border border-white/[0.06]">
              {([
                { key: 'all', label: 'Todos', icon: null },
                { key: 'hot', label: 'Hot', icon: Flame },
                { key: 'warm', label: 'Warm', icon: Thermometer },
                { key: 'cold', label: 'Cold', icon: Snowflake },
              ] as const).map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setPriorityFilter(key)}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                    priorityFilter === key
                      ? 'bg-white/[0.08] text-white'
                      : 'text-white/40 hover:text-white/60'
                  }`}
                >
                  {Icon && <Icon size={12} />}
                  {label}
                </button>
              ))}
            </div>

            {/* Tag filter */}
            {allTags.length > 0 && (
              <div className="relative">
                <select
                  value={tagFilter || ''}
                  onChange={(e) => setTagFilter(e.target.value || null)}
                  className="appearance-none bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5 pr-7 text-xs text-white/70 focus:ring-2 focus:ring-blue-500/40"
                >
                  <option value="">Todas las etiquetas</option>
                  {allTags.map((tag) => (
                    <option key={tag} value={tag}>{tag}</option>
                  ))}
                </select>
                <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
              </div>
            )}

            {(priorityFilter !== 'all' || tagFilter) && (
              <button
                onClick={() => { setPriorityFilter('all'); setTagFilter(null); }}
                className="text-xs text-white/40 hover:text-white/60 underline"
              >
                Limpiar filtros
              </button>
            )}
          </div>
        )}
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
            Cargando cola...
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Inbox size={48} className="text-white/10 mb-4" />
            <h3 className="text-lg font-medium text-white/50 mb-1">Cola vacia</h3>
            <p className="text-sm text-white/30">
              {search || priorityFilter !== 'all' || tagFilter
                ? 'No hay leads que coincidan con los filtros.'
                : 'No hay leads derivados por la IA en este momento.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredLeads.map((lead) => (
              <div
                key={lead.id}
                className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4 hover:bg-white/[0.04] transition-colors group"
              >
                <div className="flex items-start gap-4">
                  {/* Left: Info */}
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={() => navigate(`/crm/leads/${lead.id}`)}
                        className="text-base font-semibold text-white hover:text-blue-400 transition-colors truncate"
                      >
                        {[lead.first_name, lead.last_name].filter(Boolean).join(' ') || 'Sin nombre'}
                      </button>
                      <ScoreBadge score={lead.score} size="sm" showLabel />
                    </div>

                    <div className="flex items-center gap-3 text-sm text-white/40">
                      <span className="flex items-center gap-1">
                        <Phone size={12} />
                        {lead.phone_number}
                      </span>
                      {lead.upcoming_meeting && (
                        <span className="flex items-center gap-1 text-green-400">
                          <Calendar size={12} />
                          {formatDate(lead.upcoming_meeting.date)}
                        </span>
                      )}
                    </div>

                    {/* Tags */}
                    {lead.tags && lead.tags.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {lead.tags.map((tag, i) => (
                          <TagBadge key={`${tag.name}-${i}`} tag={tag} />
                        ))}
                      </div>
                    )}

                    {/* AI Summary */}
                    {lead.ai_summary && (
                      <div className="flex items-start gap-2 p-2.5 bg-purple-500/5 border border-purple-500/10 rounded-lg">
                        <Bot size={14} className="text-purple-400 mt-0.5 shrink-0" />
                        <p className="text-xs text-white/50 line-clamp-2">{lead.ai_summary}</p>
                      </div>
                    )}
                  </div>

                  {/* Right: Actions */}
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => handleTake(lead.id)}
                      disabled={takingId === lead.id}
                      className="flex items-center gap-1.5 px-3 py-2 bg-medical-600 text-white rounded-lg text-sm font-medium hover:bg-medical-700 disabled:opacity-50 transition-colors"
                    >
                      {takingId === lead.id ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <UserCheck size={14} />
                      )}
                      Tomar lead
                    </button>
                    <button
                      onClick={() => setDeriveLeadId(lead.id)}
                      className="flex items-center gap-1.5 px-3 py-2 bg-white/[0.04] text-white/60 border border-white/[0.08] rounded-lg text-sm font-medium hover:bg-white/[0.06] hover:text-white transition-colors"
                    >
                      <ArrowRight size={14} />
                      Derivar a closer
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Derive Modal */}
      {deriveLeadId && (
        <DeriveToCloserModal
          leadId={deriveLeadId}
          onClose={() => setDeriveLeadId(null)}
          onSuccess={() => {
            setDeriveLeadId(null);
            fetchQueue();
          }}
        />
      )}
    </div>
  );
}
