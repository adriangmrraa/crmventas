import { useState, useEffect, Component, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, Plus, Search, MessageSquare, Edit, Loader2, AlertCircle, UserPlus,
  Star, Mail, MapPin, Building2, Globe, Instagram, Facebook, Linkedin, ExternalLink,
  History, MessageCircle, CheckCircle2, Layers, Check, Tag, X, Upload
} from 'lucide-react';
import api, { apiGet } from '../../../api/axios';
import { parseTags } from '../../../utils/parseTags';
import { useTranslation } from '../../../context/LanguageContext';
import { LeadStatusSelector } from '../../../components/leads/LeadStatusSelector';
import { LeadStatusBadge } from '../../../components/leads/LeadStatusBadge';
import { BulkStatusUpdate } from '../../../components/leads/BulkStatusUpdate';
import ScoreBadge from '../../../components/leads/ScoreBadge';
import { TagBadge, type LeadTag } from '../../../components/leads/TagBadge';
import LeadImportModal from '../../../components/leads/LeadImportModal';

const CRM_LEADS_BASE = '/admin/core/crm/leads';

interface LeadStatusOption {
  code: string;
  name: string;
  color: string;
  sort_order: number;
}

export interface Lead {
  id: string;
  tenant_id: number;
  phone_number: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  status: string;
  source?: string;
  assigned_seller_id?: string;
  tags?: string[];
  // Prospecting fields
  apify_title?: string;
  apify_category_name?: string;
  apify_address?: string;
  apify_city?: string;
  apify_state?: string;
  apify_website?: string;
  apify_rating?: number;
  apify_reviews?: number;
  social_links?: Record<string, string>;
  outreach_message_content?: string;
  outreach_last_sent_at?: string;
  outreach_message_sent?: boolean;
  score?: number;
  created_at: string;
  updated_at: string;
}

const defaultForm = {
  phone_number: '',
  first_name: '',
  last_name: '',
  email: '',
  status: 'nuevo',
};

// ─── Error Boundary ───────────────────────────────────────────────
class LeadsErrorBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { error: error.message };
  }
  render() {
    if (this.state.error) {
      return (
        <div className="h-full flex flex-col items-center justify-center p-8 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
          <h2 className="text-lg font-bold text-white mb-2">Error al cargar Leads</h2>
          <p className="text-sm text-white/40 max-w-md font-mono bg-red-500/10 p-3 rounded-lg border border-red-500/20">{this.state.error}</p>
          <button
            className="mt-4 px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-bold hover:bg-violet-700"
            onClick={() => window.location.reload()}
          >Recargar página</button>
        </div>
      );
    }
    return this.props.children;
  }
}
// ──────────────────────────────────────────────────────────────────

export default function LeadsView() {
  return <LeadsErrorBoundary><LeadsViewInner /></LeadsErrorBoundary>;
}

function LeadsViewInner() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [formData, setFormData] = useState(defaultForm);
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [convertingId, setConvertingId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'messages' | 'prospecting'>('all');
  const [selectedLeads, setSelectedLeads] = useState<string[]>([]);
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [availableTags, setAvailableTags] = useState<LeadTag[]>([]);
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [isTagFilterOpen, setIsTagFilterOpen] = useState(false);
  const [statusOptions, setStatusOptions] = useState<LeadStatusOption[]>([]);

  useEffect(() => {
    fetchLeads();
    fetchAvailableTags();
    fetchStatusOptions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const fetchStatusOptions = async () => {
    try {
      const res = await api.get('/admin/core/crm/lead-statuses');
      const data: LeadStatusOption[] = Array.isArray(res.data) ? res.data : [];
      setStatusOptions(data.sort((a, b) => a.sort_order - b.sort_order));
    } catch (err) {
      console.error('[LeadsView] Failed to fetch status options:', err);
    }
  };

  const fetchAvailableTags = async () => {
    try {
      const data = await apiGet<LeadTag[]>('/admin/core/crm/lead-tags');
      setAvailableTags(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('[LeadsView] Failed to fetch tags:', err);
    }
  };

  const handleConvertToClient = async (e: React.MouseEvent, lead: Lead) => {
    e.stopPropagation();
    if (!window.confirm(t('leads.confirm_convert_to_client'))) return;
    setConvertingId(lead.id);
    try {
      await api.post(`${CRM_LEADS_BASE}/${lead.id}/convert-to-client`);
      await fetchLeads();
      navigate('/crm/clientes');
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('leads.error_convert_to_client');
      alert(msg);
    } finally {
      setConvertingId(null);
    }
  };

  const fetchLeads = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: Record<string, string | number> = { limit: 500, offset: 0 };
      if (statusFilter) params.status = statusFilter;
      const response = await api.get<Lead[]>(CRM_LEADS_BASE, { params });
      setLeads(Array.isArray(response.data) ? response.data : []);
    } catch (err: unknown) {
      const ax = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      let message = 'Failed to load leads.';
      if (ax.response) {
        const rawDetail = ax.response.data?.detail;
        const detail = Array.isArray(rawDetail)
          ? rawDetail.map((d: { msg?: string; loc?: string[] }) => `${d.loc?.join('.') ?? ''}: ${d.msg ?? JSON.stringify(d)}`).join(' | ')
          : (typeof rawDetail === 'string' ? rawDetail : rawDetail ? JSON.stringify(rawDetail) : '');
        message = detail || (ax.response.status === 401 ? 'Session expired. Please log in again.' : ax.response.status === 403 ? 'You do not have access.' : `Error ${ax.response.status}.`);

      } else if (ax.message) {
        message = ax.message.includes('Network') || ax.message.includes('CORS') || ax.message.includes('Failed to fetch')
          ? 'Cannot reach the server. Ensure the backend is running and CORS allows this origin (redeploy if needed).'
          : String(ax.message);
      }
      setError(message);
      setLeads([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredLeads = leads.filter((lead) => {
    // Filter by Tab
    if (activeTab === 'messages' && lead.source !== 'whatsapp_inbound' && lead.source !== 'whatsapp') return false;
    if (activeTab === 'prospecting' && lead.source !== 'apify_scrape') return false;

    // Filter by tags (must have ALL selected tags)
    if (tagFilter.length > 0) {
      const leadTags = lead.tags || [];
      if (!tagFilter.every((t) => leadTags.includes(t))) return false;
    }

    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const name = [lead.first_name, lead.last_name].filter(Boolean).join(' ').toLowerCase();
    return (
      name.includes(term) ||
      (lead.phone_number || '').includes(term) ||
      (lead.email || '').toLowerCase().includes(term)
    );
  });

  const handleOpenModal = (lead: Lead | null = null) => {
    if (lead) {
      setEditingLead(lead);
      setFormData({
        phone_number: lead.phone_number,
        first_name: lead.first_name || '',
        last_name: lead.last_name || '',
        email: lead.email || '',
        status: lead.status || 'nuevo',
      });
    } else {
      setEditingLead(null);
      setFormData(defaultForm);
    }
    setModalError(null);
    setIsModalOpen(true);
  };

  const handleModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    try {
      if (editingLead) {
        await api.put(`${CRM_LEADS_BASE}/${editingLead.id}`, {
          first_name: formData.first_name || null,
          last_name: formData.last_name || null,
          email: formData.email || null,
          status: formData.status,
        });
      } else {
        if (!formData.phone_number.trim()) {
          setModalError('Phone number is required.');
          return;
        }
        await api.post(CRM_LEADS_BASE, {
          phone_number: formData.phone_number.trim(),
          first_name: formData.first_name || undefined,
          last_name: formData.last_name || undefined,
          email: formData.email || undefined,
          status: formData.status,
        });
      }
      await fetchLeads();
      setIsModalOpen(false);
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : editingLead ? 'Failed to update lead' : 'Failed to create lead';
      setModalError(String(msg));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* FIXED TITLE BAR */}
      <div className="flex items-center justify-between p-4 lg:p-6 border-b border-white/[0.06] bg-white/[0.03] shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-violet-500/15 flex items-center justify-center shrink-0">
            <Users className="w-5 h-5 text-medical-700" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-white">{t('nav.leads')}</h1>
            <p className="text-sm text-white/40">{leads.length} {leads.length === 1 ? 'lead' : 'leads'}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => handleOpenModal(null)}
          className="lg:hidden inline-flex items-center p-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 active:scale-95 transition-transform"
        >
          <Plus size={20} />
        </button>
      </div>

      {/* SCROLLABLE CONTENT AREA */}
      <div className="flex-1 overflow-y-auto min-h-0 bg-white/[0.02]/30">
        <div className="p-4 lg:p-6 space-y-6">
          {/* SEARCH & FILTERS BAR (Scrolls with content) */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 flex-1">
              <div className="relative flex-1 lg:max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input
                  type="text"
                  placeholder={t('common.search')}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-white/[0.06] rounded-xl text-sm outline-none focus:ring-2 focus:ring-violet-500 transition-all"
                />
              </div>
            </div>
            <div className="flex gap-2">
              {selectedLeads.length > 0 && (
                <button
                  type="button"
                  onClick={() => setIsBulkModalOpen(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-xl hover:bg-violet-700 text-sm font-bold transition-all shadow-md shadow-blue-100 animate-in fade-in slide-in-from-left-2"
                >
                  <Layers size={18} />
                  <span className="hidden sm:inline">Actualización Masiva</span>
                  <span className="bg-violet-500 text-[10px] px-1.5 py-0.5 rounded-full ml-1">
                    {selectedLeads.length}
                  </span>
                </button>
              )}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="flex-1 px-3 py-2 border border-white/[0.06] rounded-xl text-sm bg-white/[0.03] outline-none focus:ring-2 focus:ring-violet-500 transition-all font-medium text-white/70"
              >
                <option value="">Todos los estados</option>
                {statusOptions.map(s => (
                  <option key={s.code} value={s.code}>{s.name}</option>
                ))}
              </select>

              {/* Tag multi-select filter */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setIsTagFilterOpen(!isTagFilterOpen)}
                  className={`flex items-center gap-2 px-3 py-2 border rounded-xl text-sm font-medium transition-all ${
                    tagFilter.length > 0
                      ? 'border-violet-500/30 bg-violet-500/10 text-violet-400'
                      : 'border-white/[0.06] bg-white/[0.03] text-white/70'
                  }`}
                >
                  <Tag size={14} />
                  <span className="hidden sm:inline">Etiquetas</span>
                  {tagFilter.length > 0 && (
                    <span className="bg-violet-500/20 text-violet-400 text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                      {tagFilter.length}
                    </span>
                  )}
                </button>
                {isTagFilterOpen && (
                  <div className="absolute right-0 z-50 mt-2 w-56 bg-[#1a1a2e] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/40 overflow-hidden">
                    <div className="p-2 border-b border-white/[0.06] flex items-center justify-between">
                      <span className="text-xs font-bold text-white/40 uppercase tracking-wider">Filtrar por etiquetas</span>
                      {tagFilter.length > 0 && (
                        <button
                          type="button"
                          onClick={() => setTagFilter([])}
                          className="text-[10px] text-white/30 hover:text-white/50 font-medium"
                        >
                          Limpiar
                        </button>
                      )}
                    </div>
                    <div className="max-h-48 overflow-y-auto p-1">
                      {availableTags.length === 0 ? (
                        <div className="px-3 py-3 text-xs text-white/30 text-center">Sin etiquetas</div>
                      ) : (
                        availableTags.map((tag) => {
                          const isSelected = tagFilter.includes(tag.name);
                          return (
                            <button
                              key={tag.name}
                              type="button"
                              onClick={() =>
                                setTagFilter((prev) =>
                                  isSelected ? prev.filter((t) => t !== tag.name) : [...prev, tag.name]
                                )
                              }
                              className={`w-full flex items-center gap-2 px-3 py-2 text-xs rounded-lg transition-colors ${
                                isSelected
                                  ? 'bg-white/[0.06] text-white'
                                  : 'text-white/60 hover:bg-white/[0.04] hover:text-white'
                              }`}
                            >
                              <span
                                className="w-2.5 h-2.5 rounded-full shrink-0"
                                style={{ backgroundColor: tag.color }}
                              />
                              <span className="flex-1 text-left truncate">{tag.name}</span>
                              {isSelected && <Check className="w-3.5 h-3.5 text-violet-500 shrink-0" />}
                            </button>
                          );
                        })
                      )}
                    </div>
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => setIsImportModalOpen(true)}
                className="hidden lg:inline-flex items-center gap-2 px-4 py-2 bg-white/[0.06] text-white/70 hover:text-white rounded-xl hover:bg-white/[0.1] text-sm font-medium border border-white/[0.08] transition-all active:scale-[0.98]"
              >
                <Upload size={16} />
                Importar CSV
              </button>
              <button
                type="button"
                onClick={() => handleOpenModal(null)}
                className="hidden lg:inline-flex items-center gap-2 px-6 py-2 bg-violet-600 text-white rounded-xl hover:bg-violet-700 text-sm font-bold transition-all shadow-md shadow-blue-900 active:scale-[0.98]"
              >
                <Plus size={18} />
                Añadir Lead
              </button>
            </div>
          </div>
        </div>

        {/* TABS (integrated into scroll) */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden">
          <div className="flex overflow-x-auto no-scrollbar">
            <button
              onClick={() => setActiveTab('all')}
              className={`flex-1 py-3 px-4 text-sm font-bold border-b-2 transition-colors ${activeTab === 'all' ? 'border-medical-600 text-medical-700 bg-violet-500/10/30' : 'border-transparent text-white/30 hover:text-white/50'
                }`}
            >
              Todos
            </button>
            <button
              onClick={() => setActiveTab('messages')}
              className={`flex-1 py-3 px-4 text-sm font-bold border-b-2 transition-colors ${activeTab === 'messages' ? 'border-medical-600 text-medical-700 bg-violet-500/10/30' : 'border-transparent text-white/30 hover:text-white/50'
                }`}
            >
              Mensajes
            </button>
            <button
              onClick={() => setActiveTab('prospecting')}
              className={`flex-1 py-3 px-4 text-sm font-bold border-b-2 transition-colors ${activeTab === 'prospecting' ? 'border-medical-600 text-medical-700 bg-violet-500/10/30' : 'border-transparent text-white/30 hover:text-white/50'
                }`}
            >
              Prospección
            </button>
          </div>

          {activeTab === 'prospecting' && (
            <div className="p-3 bg-violet-500/10/50 border-t border-white/[0.04] flex items-center justify-between">
              <span className="text-xs font-bold text-medical-700 uppercase tracking-tight">Opciones de prospección</span>
              <button
                onClick={() => navigate('/crm/prospeccion')}
                className="text-[10px] font-bold uppercase tracking-wider text-white bg-violet-600 hover:bg-violet-700 px-4 py-2 rounded-lg transition-all"
              >
                Ir a Prospección →
              </button>
            </div>
          )}
        </div>

        {/* LEAD LIST SECTION */}
        <div>
          {error && (
            <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}
          {loading ? (
            <div className="flex items-center justify-center py-12 text-white/40">{t('common.loading')}</div>
          ) : filteredLeads.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-white/40 bg-white/[0.03] border border-white/[0.06] rounded-xl">
              <Users className="w-12 h-12 text-gray-200 mb-3" />
              <p>No leads yet.</p>
              <button
                type="button"
                onClick={() => handleOpenModal(null)}
                className="mt-3 text-violet-400 hover:underline font-medium"
              >
                Add your first lead
              </button>
            </div>
          ) : (
            <ul className="space-y-3">
              {filteredLeads.map((lead) => {
                if (!lead || !lead.id) return null;
                const safeName = [lead.first_name, lead.last_name].filter(Boolean).join(' ') || String(lead.phone_number || '—');
                const businessName = lead.apify_title || (lead.source === 'apify_scrape' ? 'Negocio Desconocido' : null);
                const displayName = businessName || safeName;
                const firstChar = String(displayName).charAt(0).toUpperCase() || '?';

                return (
                  <li
                    key={lead.id}
                    className={`group bg-white/[0.03] border ${selectedLeads.includes(lead.id) ? 'border-violet-300 ring-2 ring-blue-50 shadow-md' : 'border-white/[0.06]'} rounded-xl p-4 lg:p-5 hover:border-medical-300 hover:shadow-md transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 active:bg-white/[0.02] relative overflow-visible`}
                    onClick={() => handleOpenModal(lead)}
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      {/* Selection Checkbox */}
                      <div
                        className={`shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${selectedLeads.includes(lead.id) ? 'bg-violet-600 border-violet-600 opacity-100' : 'bg-white/[0.03] border-white/[0.06] opacity-0 group-hover:opacity-100'}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedLeads(prev =>
                            prev.includes(lead.id)
                              ? prev.filter(id => id !== lead.id)
                              : [...prev, lead.id]
                          );
                        }}
                      >
                        {selectedLeads.includes(lead.id) && <Check className="w-3 h-3 text-white" />}
                      </div>

                      <div className="w-12 h-12 rounded-full bg-violet-500/10 flex items-center justify-center shrink-0 border border-white/[0.06]">
                        <span className="text-medical-700 font-bold text-base">
                          {firstChar}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-bold text-white truncate text-base">
                            {displayName}
                          </p>
                          <ScoreBadge score={lead.score} />
                        </div>
                        {businessName && (
                          <p className="text-xs text-violet-400 font-medium truncate mb-0.5">
                            {safeName !== businessName ? safeName : String(lead.phone_number || '')}
                          </p>
                        )}
                        <p className="text-sm text-white/40 truncate">{String(lead.phone_number || '')}</p>
                        {parseTags(lead.tags).length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {parseTags(lead.tags).slice(0, 3).map((tagName) => {
                              const tagDef = availableTags.find((t) => t.name === tagName) || { name: tagName, color: '#6B7280' };
                              return <TagBadge key={tagName} tag={tagDef} />;
                            })}
                            {lead.tags.length > 3 && (
                              <span className="text-[10px] text-white/30 font-medium self-center">+{lead.tags.length - 3}</span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-3 pt-3 sm:pt-0 border-t sm:border-t-0 border-white/[0.04]">
                      <div className="flex flex-col items-start sm:items-end mr-2" onClick={(e) => e.stopPropagation()}>
                        <span className="text-[10px] font-bold text-white/30 uppercase tracking-widest leading-none mb-1">Status</span>
                        <LeadStatusSelector
                          leadId={lead.id}
                          currentStatusCode={lead.status}
                          onChangeSuccess={fetchLeads}
                        />
                      </div>

                      <div className="flex gap-1">
                        <button
                          type="button"
                          onClick={(e) => handleConvertToClient(e, lead)}
                          disabled={convertingId === lead.id}
                          className="p-3 bg-emerald-50 text-emerald-600 rounded-xl hover:bg-emerald-100 transition-colors"
                          title={t('leads.convert_to_client')}
                        >
                          {convertingId === lead.id ? <Loader2 size={20} className="animate-spin" /> : <UserPlus size={20} />}
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate('/chats');
                          }}
                          className="p-3 bg-violet-500/10 text-violet-400 rounded-xl hover:bg-violet-500/15 transition-colors"
                          title="Open chat"
                        >
                          <MessageSquare size={20} />
                        </button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {isModalOpen && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
            <div className={`bg-white/[0.03] rounded-xl shadow-2xl w-full ${editingLead?.source === 'apify_scrape' ? 'max-w-4xl' : 'max-w-md'} max-h-[90vh] flex flex-col`}>
              <div className="p-6 border-b border-white/[0.06] shrink-0 flex items-center justify-between">
                <h2 className="text-xl font-bold flex items-center gap-2 text-white">
                  {editingLead ? <Edit className="text-violet-400" size={22} /> : <Plus className="text-violet-400" size={22} />}
                  {editingLead ? (editingLead.source === 'apify_scrape' ? 'Business Detail' : 'Edit lead') : 'New lead'}
                </h2>
                <button onClick={() => setIsModalOpen(false)} className="text-white/30 hover:text-white/50">
                  <span className="sr-only">Close</span>
                  <History size={20} className="rotate-90" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto min-h-0">
                <div className={`p-6 ${editingLead?.source === 'apify_scrape' ? 'grid grid-cols-1 lg:grid-cols-2 gap-8' : 'space-y-4'}`}>
                  {/* LEFT COLUMN: Basic Form */}
                  <div className="space-y-4">
                    {modalError && (
                      <div className="bg-red-500/10 text-red-400 p-3 rounded-lg flex items-center gap-2 text-sm border border-red-500/20">
                        <AlertCircle size={16} /> {modalError}
                      </div>
                    )}

                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-full bg-violet-500/10 flex items-center justify-center text-medical-700 font-bold text-lg">
                        {(formData.first_name || editingLead?.apify_title || '?').charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <h3 className="font-bold text-white">
                          {editingLead?.apify_title || (formData.first_name ? `${formData.first_name} ${formData.last_name}` : editingLead?.phone_number)}
                        </h3>
                        {editingLead?.source === 'apify_scrape' && (
                          <span className="text-xs bg-violet-500/10 text-medical-700 px-2 py-0.5 rounded-full font-medium">Prospección</span>
                        )}
                      </div>
                    </div>

                    <form id="lead-form" onSubmit={handleModalSubmit} className="space-y-4">
                      {!editingLead && (
                        <div className="space-y-1">
                          <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Phone number *</label>
                          <input
                            required
                            type="tel"
                            className="w-full px-4 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30 outline-none transition-all"
                            value={formData.phone_number}
                            onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                          />
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <label className="text-xs font-bold text-white/40 uppercase tracking-wider">First name</label>
                          <input
                            type="text"
                            className="w-full px-4 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30 outline-none"
                            value={formData.first_name}
                            onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Last name</label>
                          <input
                            type="text"
                            className="w-full px-4 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30 outline-none"
                            value={formData.last_name}
                            onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                          />
                        </div>
                      </div>

                      <div className="space-y-1">
                        <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Email</label>
                        <div className="relative">
                          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                          <input
                            type="email"
                            className="w-full pl-10 pr-4 py-2 border border-white/[0.06] rounded-lg focus:ring-2 focus:ring-violet-500 outline-none"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          />
                        </div>
                      </div>

                      <div className="space-y-1">
                        <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Status</label>
                        <select
                          className="w-full px-4 py-2 border border-white/[0.06] rounded-lg focus:ring-2 focus:ring-violet-500 outline-none bg-white/[0.03] font-medium"
                          value={formData.status}
                          onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                        >
                          {statusOptions.map((s) => (
                            <option key={s.code} value={s.code}>{s.name}</option>
                          ))}
                        </select>
                      </div>
                    </form>
                  </div>

                  {/* RIGHT COLUMN: Business Intelligence (Only for apify_scrape) */}
                  {editingLead?.source === 'apify_scrape' && (
                    <div className="space-y-6">
                      <div className="bg-white/[0.02] rounded-xl p-5 border border-white/[0.04] space-y-4">
                        <h4 className="text-sm font-bold text-white border-b border-white/[0.06] pb-2 flex items-center gap-2">
                          <Building2 size={18} className="text-violet-400" />
                          Business Insights
                        </h4>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <p className="text-[10px] text-white/30 uppercase font-bold tracking-tight">Rating</p>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <Star size={16} className="text-amber-500 fill-current" />
                              <span className="text-lg font-bold text-white">{editingLead.apify_rating?.toFixed(1) || '—'}</span>
                              <span className="text-xs text-white/30">({editingLead.apify_reviews || 0} reviews)</span>
                            </div>
                          </div>
                          <div>
                            <p className="text-[10px] text-white/30 uppercase font-bold tracking-tight">Categoría</p>
                            <p className="text-sm font-medium text-white/70 mt-1">{editingLead.apify_category_name || '—'}</p>
                          </div>
                        </div>

                        <div className="space-y-3">
                          <div>
                            <p className="text-[10px] text-white/30 uppercase font-bold tracking-tight mb-1">Dirección</p>
                            <div className="flex items-start gap-2">
                              <MapPin size={16} className="text-white/30 mt-0.5 shrink-0" />
                              <p className="text-sm text-white/50 leading-tight">
                                {editingLead.apify_address || `${editingLead.apify_city || '—'}, ${editingLead.apify_state || ''}`}
                              </p>
                            </div>
                          </div>

                          {editingLead.apify_website && (
                            <div>
                              <p className="text-[10px] text-white/30 uppercase font-bold tracking-tight mb-1">Sitio Web</p>
                              <a
                                href={editingLead.apify_website}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-violet-400 font-medium flex items-center gap-1.5 hover:underline"
                              >
                                <Globe size={16} />
                                {editingLead.apify_website.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
                                <ExternalLink size={12} />
                              </a>
                            </div>
                          )}

                          <div>
                            <p className="text-[10px] text-white/30 uppercase font-bold tracking-tight mb-1">Redes Sociales</p>
                            <div className="flex gap-3 text-white/30">
                              {editingLead.social_links?.instagram ? (
                                <a href={editingLead.social_links.instagram} target="_blank" rel="noopener noreferrer" className="hover:text-pink-600">
                                  <Instagram size={20} />
                                </a>
                              ) : <Instagram size={20} className="opacity-25" />}
                              {editingLead.social_links?.facebook ? (
                                <a href={editingLead.social_links.facebook} target="_blank" rel="noopener noreferrer" className="hover:text-violet-400">
                                  <Facebook size={20} />
                                </a>
                              ) : <Facebook size={20} className="opacity-25" />}
                              {editingLead.social_links?.linkedin ? (
                                <a href={editingLead.social_links.linkedin} target="_blank" rel="noopener noreferrer" className="hover:text-violet-400">
                                  <Linkedin size={20} />
                                </a>
                              ) : <Linkedin size={20} className="opacity-25" />}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Outreach History Section */}
                      <div className="bg-emerald-50 rounded-xl p-5 border border-emerald-100 space-y-3">
                        <h4 className="text-sm font-bold text-emerald-900 border-b border-emerald-200 pb-2 flex items-center gap-2">
                          <History size={18} className="text-emerald-600" />
                          Auditoría de Outreach
                        </h4>

                        {editingLead.outreach_message_sent ? (
                          <div className="space-y-3">
                            <div className="flex items-center gap-2 text-emerald-700 font-bold text-xs uppercase tracking-wider">
                              <CheckCircle2 size={16} />
                              Mensaje Enviado
                            </div>
                            <div className="bg-white/60 p-3 rounded-lg border border-emerald-200">
                              <p className="text-[10px] text-emerald-600 font-bold uppercase mb-1">Contenido / Plantilla</p>
                              <p className="text-sm text-emerald-900 italic">
                                "{editingLead.outreach_message_content || 'First Contact Template'}"
                              </p>
                            </div>
                            <div className="flex justify-between items-center text-xs text-emerald-700">
                              <span>Fecha de envío:</span>
                              <span className="font-bold">
                                {editingLead.outreach_last_sent_at ? new Date(editingLead.outreach_last_sent_at).toLocaleString() : 'N/A'}
                              </span>
                            </div>
                          </div>
                        ) : (
                          <div className="py-4 text-center">
                            <MessageCircle size={32} className="mx-auto text-emerald-200 mb-2" />
                            <p className="text-sm text-emerald-700 italic">No se ha enviado ningún mensaje aún.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="p-6 border-t border-white/[0.06] bg-white/[0.02] shrink-0 flex flex-col sm:flex-row gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="w-full sm:flex-1 py-3 text-white/70 font-bold hover:bg-white/[0.04] rounded-xl transition-all border border-white/[0.06]"
                >
                  {t('common.cancel')}
                </button>
                <button
                  // Link with form tag via id
                  form="lead-form"
                  type="submit"
                  disabled={saving}
                  className="w-full sm:flex-[2] py-3 bg-violet-600 text-white font-bold rounded-xl hover:bg-violet-700 shadow-md shadow-medical-200 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {saving ? <Loader2 className="animate-spin" size={20} /> : (editingLead ? 'Update Lead' : t('common.save'))}
                </button>
              </div>
            </div>
          </div>
        )}

        {isBulkModalOpen && (
          <BulkStatusUpdate
            selectedLeadIds={selectedLeads}
            onSuccess={() => {
              setIsBulkModalOpen(false);
              setSelectedLeads([]);
              fetchLeads();
            }}
            onCancel={() => setIsBulkModalOpen(false)}
          />
        )}

        <LeadImportModal
          isOpen={isImportModalOpen}
          onClose={() => setIsImportModalOpen(false)}
          onComplete={() => fetchLeads()}
        />
      </div>
    </div>
  );
}
