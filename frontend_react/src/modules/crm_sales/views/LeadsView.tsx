import { useState, useEffect, Component, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, Plus, Search, MessageSquare, Edit, Loader2, AlertCircle, UserPlus,
  Star, Mail, MapPin, Building2, Globe, Instagram, Facebook, Linkedin, ExternalLink,
  History, MessageCircle, CheckCircle2, Layers, Check
} from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import { LeadStatusSelector } from '../../../components/leads/LeadStatusSelector';
import { LeadStatusBadge } from '../../../components/leads/LeadStatusBadge';
import { BulkStatusUpdate } from '../../../components/leads/BulkStatusUpdate';

const CRM_LEADS_BASE = '/admin/core/crm/leads';
const STATUS_OPTIONS = ['new', 'contacted', 'interested', 'negotiation', 'closed_won', 'closed_lost'] as const;

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
  created_at: string;
  updated_at: string;
}

const defaultForm = {
  phone_number: '',
  first_name: '',
  last_name: '',
  email: '',
  status: 'new' as const,
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
          <h2 className="text-lg font-bold text-gray-800 mb-2">Error al cargar Leads</h2>
          <p className="text-sm text-gray-500 max-w-md font-mono bg-red-50 p-3 rounded-lg border border-red-100">{this.state.error}</p>
          <button
            className="mt-4 px-4 py-2 bg-medical-600 text-white rounded-lg text-sm font-bold hover:bg-medical-700"
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

  useEffect(() => {
    fetchLeads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

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
    if (activeTab === 'all') return true;
    if (activeTab === 'messages' && lead.source !== 'whatsapp_inbound' && lead.source !== 'whatsapp') return false;
    if (activeTab === 'prospecting' && lead.source !== 'apify_scrape') return false;

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
        status: (lead.status as typeof defaultForm.status) || 'new',
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
      <div className="flex items-center justify-between p-4 lg:p-6 border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-medical-100 flex items-center justify-center shrink-0">
            <Users className="w-5 h-5 text-medical-700" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">{t('nav.leads')}</h1>
            <p className="text-sm text-gray-500">{leads.length} {leads.length === 1 ? 'lead' : 'leads'}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => handleOpenModal(null)}
          className="lg:hidden inline-flex items-center p-2 bg-medical-600 text-white rounded-lg hover:bg-medical-700 active:scale-95 transition-transform"
        >
          <Plus size={20} />
        </button>
      </div>

      {/* SCROLLABLE CONTENT AREA */}
      <div className="flex-1 overflow-y-auto min-h-0 bg-gray-50/30">
        <div className="p-4 lg:p-6 space-y-6">
          {/* SEARCH & FILTERS BAR (Scrolls with content) */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 flex-1">
              <div className="relative flex-1 lg:max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder={t('common.search')}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-medical-500 transition-all shadow-sm"
                />
              </div>
            </div>
            <div className="flex gap-2">
              {selectedLeads.length > 0 && (
                <button
                  type="button"
                  onClick={() => setIsBulkModalOpen(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 text-sm font-bold transition-all shadow-md shadow-blue-100 animate-in fade-in slide-in-from-left-2"
                >
                  <Layers size={18} />
                  <span className="hidden sm:inline">Actualización Masiva</span>
                  <span className="bg-blue-500 text-[10px] px-1.5 py-0.5 rounded-full ml-1">
                    {selectedLeads.length}
                  </span>
                </button>
              )}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-xl text-sm bg-white outline-none focus:ring-2 focus:ring-medical-500 transition-all font-medium text-gray-700 shadow-sm"
              >
                <option value="">Todos los estados</option>
                {STATUS_OPTIONS.map(s => (
                  <option key={s} value={s}>{s.replace('_', ' ')}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => handleOpenModal(null)}
                className="hidden lg:inline-flex items-center gap-2 px-6 py-2 bg-medical-600 text-white rounded-xl hover:bg-medical-700 text-sm font-bold transition-all shadow-md shadow-medical-100 active:scale-[0.98]"
              >
                <Plus size={18} />
                Añadir Lead
              </button>
            </div>
          </div>
        </div>

        {/* TABS (integrated into scroll) */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
          <div className="flex overflow-x-auto no-scrollbar">
            <button
              onClick={() => setActiveTab('all')}
              className={`flex-1 py-3 px-4 text-sm font-bold border-b-2 transition-colors ${activeTab === 'all' ? 'border-medical-600 text-medical-700 bg-medical-50/30' : 'border-transparent text-gray-400 hover:text-gray-600'
                }`}
            >
              Todos
            </button>
            <button
              onClick={() => setActiveTab('messages')}
              className={`flex-1 py-3 px-4 text-sm font-bold border-b-2 transition-colors ${activeTab === 'messages' ? 'border-medical-600 text-medical-700 bg-medical-50/30' : 'border-transparent text-gray-400 hover:text-gray-600'
                }`}
            >
              Mensajes
            </button>
            <button
              onClick={() => setActiveTab('prospecting')}
              className={`flex-1 py-3 px-4 text-sm font-bold border-b-2 transition-colors ${activeTab === 'prospecting' ? 'border-medical-600 text-medical-700 bg-medical-50/30' : 'border-transparent text-gray-400 hover:text-gray-600'
                }`}
            >
              Prospección
            </button>
          </div>

          {activeTab === 'prospecting' && (
            <div className="p-3 bg-medical-50/50 border-t border-gray-100 flex items-center justify-between">
              <span className="text-xs font-bold text-medical-700 uppercase tracking-tight">Opciones de prospección</span>
              <button
                onClick={() => navigate('/crm/prospeccion')}
                className="text-[10px] font-bold uppercase tracking-wider text-white bg-medical-600 hover:bg-medical-700 px-4 py-2 rounded-lg transition-all shadow-sm"
              >
                Ir a Prospección →
              </button>
            </div>
          )}
        </div>

        {/* LEAD LIST SECTION */}
        <div>
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}
          {loading ? (
            <div className="flex items-center justify-center py-12 text-gray-500">{t('common.loading')}</div>
          ) : filteredLeads.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500 bg-white border border-gray-200 rounded-xl">
              <Users className="w-12 h-12 text-gray-200 mb-3" />
              <p>No leads yet.</p>
              <button
                type="button"
                onClick={() => handleOpenModal(null)}
                className="mt-3 text-medical-600 hover:underline font-medium"
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
                    className={`group bg-white border ${selectedLeads.includes(lead.id) ? 'border-blue-300 ring-2 ring-blue-50 shadow-md' : 'border-gray-200'} rounded-xl p-4 lg:p-5 hover:border-medical-300 hover:shadow-md transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 active:bg-gray-50 relative overflow-visible`}
                    onClick={() => handleOpenModal(lead)}
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      {/* Selection Checkbox */}
                      <div
                        className={`shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${selectedLeads.includes(lead.id) ? 'bg-blue-600 border-blue-600 opacity-100' : 'bg-white border-gray-300 opacity-0 group-hover:opacity-100'}`}
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

                      <div className="w-12 h-12 rounded-full bg-medical-50 flex items-center justify-center shrink-0 border border-medical-100">
                        <span className="text-medical-700 font-bold text-base">
                          {firstChar}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-gray-900 truncate text-base">
                          {displayName}
                        </p>
                        {businessName && (
                          <p className="text-xs text-medical-600 font-medium truncate mb-0.5">
                            {safeName !== businessName ? safeName : String(lead.phone_number || '')}
                          </p>
                        )}
                        <p className="text-sm text-gray-500 truncate">{String(lead.phone_number || '')}</p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-3 pt-3 sm:pt-0 border-t sm:border-t-0 border-gray-100">
                      <div className="flex flex-col items-start sm:items-end mr-2" onClick={(e) => e.stopPropagation()}>
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none mb-1">Status</span>
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
                          className="p-3 bg-medical-50 text-medical-600 rounded-xl hover:bg-medical-100 transition-colors"
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
            <div className={`bg-white rounded-xl shadow-2xl w-full ${editingLead?.source === 'apify_scrape' ? 'max-w-4xl' : 'max-w-md'} max-h-[90vh] flex flex-col`}>
              <div className="p-6 border-b border-gray-200 shrink-0 flex items-center justify-between">
                <h2 className="text-xl font-bold flex items-center gap-2 text-gray-900">
                  {editingLead ? <Edit className="text-medical-600" size={22} /> : <Plus className="text-medical-600" size={22} />}
                  {editingLead ? (editingLead.source === 'apify_scrape' ? 'Business Detail' : 'Edit lead') : 'New lead'}
                </h2>
                <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                  <span className="sr-only">Close</span>
                  <History size={20} className="rotate-90" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto min-h-0">
                <div className={`p-6 ${editingLead?.source === 'apify_scrape' ? 'grid grid-cols-1 lg:grid-cols-2 gap-8' : 'space-y-4'}`}>
                  {/* LEFT COLUMN: Basic Form */}
                  <div className="space-y-4">
                    {modalError && (
                      <div className="bg-red-50 text-red-600 p-3 rounded-lg flex items-center gap-2 text-sm border border-red-100">
                        <AlertCircle size={16} /> {modalError}
                      </div>
                    )}

                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-full bg-medical-50 flex items-center justify-center text-medical-700 font-bold text-lg">
                        {(formData.first_name || editingLead?.apify_title || '?').charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <h3 className="font-bold text-gray-900">
                          {editingLead?.apify_title || (formData.first_name ? `${formData.first_name} ${formData.last_name}` : editingLead?.phone_number)}
                        </h3>
                        {editingLead?.source === 'apify_scrape' && (
                          <span className="text-xs bg-medical-50 text-medical-700 px-2 py-0.5 rounded-full font-medium">Prospección</span>
                        )}
                      </div>
                    </div>

                    <form id="lead-form" onSubmit={handleModalSubmit} className="space-y-4">
                      {!editingLead && (
                        <div className="space-y-1">
                          <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Phone number *</label>
                          <input
                            required
                            type="tel"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 outline-none transition-all"
                            value={formData.phone_number}
                            onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                          />
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">First name</label>
                          <input
                            type="text"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 outline-none"
                            value={formData.first_name}
                            onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Last name</label>
                          <input
                            type="text"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 outline-none"
                            value={formData.last_name}
                            onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                          />
                        </div>
                      </div>

                      <div className="space-y-1">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Email</label>
                        <div className="relative">
                          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                          <input
                            type="email"
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 outline-none"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          />
                        </div>
                      </div>

                      <div className="space-y-1">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Status</label>
                        <select
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 outline-none bg-white font-medium"
                          value={formData.status}
                          onChange={(e) => setFormData({ ...formData, status: e.target.value as typeof defaultForm.status })}
                        >
                          {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>{s.replace('_', ' ')}</option>
                          ))}
                        </select>
                      </div>
                    </form>
                  </div>

                  {/* RIGHT COLUMN: Business Intelligence (Only for apify_scrape) */}
                  {editingLead?.source === 'apify_scrape' && (
                    <div className="space-y-6">
                      <div className="bg-gray-50 rounded-xl p-5 border border-gray-100 space-y-4">
                        <h4 className="text-sm font-bold text-gray-900 border-b border-gray-200 pb-2 flex items-center gap-2">
                          <Building2 size={18} className="text-medical-600" />
                          Business Insights
                        </h4>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <p className="text-[10px] text-gray-400 uppercase font-bold tracking-tight">Rating</p>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <Star size={16} className="text-amber-500 fill-current" />
                              <span className="text-lg font-bold text-gray-800">{editingLead.apify_rating?.toFixed(1) || '—'}</span>
                              <span className="text-xs text-gray-400">({editingLead.apify_reviews || 0} reviews)</span>
                            </div>
                          </div>
                          <div>
                            <p className="text-[10px] text-gray-400 uppercase font-bold tracking-tight">Categoría</p>
                            <p className="text-sm font-medium text-gray-700 mt-1">{editingLead.apify_category_name || '—'}</p>
                          </div>
                        </div>

                        <div className="space-y-3">
                          <div>
                            <p className="text-[10px] text-gray-400 uppercase font-bold tracking-tight mb-1">Dirección</p>
                            <div className="flex items-start gap-2">
                              <MapPin size={16} className="text-gray-400 mt-0.5 shrink-0" />
                              <p className="text-sm text-gray-600 leading-tight">
                                {editingLead.apify_address || `${editingLead.apify_city || '—'}, ${editingLead.apify_state || ''}`}
                              </p>
                            </div>
                          </div>

                          {editingLead.apify_website && (
                            <div>
                              <p className="text-[10px] text-gray-400 uppercase font-bold tracking-tight mb-1">Sitio Web</p>
                              <a
                                href={editingLead.apify_website}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-medical-600 font-medium flex items-center gap-1.5 hover:underline"
                              >
                                <Globe size={16} />
                                {editingLead.apify_website.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
                                <ExternalLink size={12} />
                              </a>
                            </div>
                          )}

                          <div>
                            <p className="text-[10px] text-gray-400 uppercase font-bold tracking-tight mb-1">Redes Sociales</p>
                            <div className="flex gap-3 text-gray-400">
                              {editingLead.social_links?.instagram ? (
                                <a href={editingLead.social_links.instagram} target="_blank" rel="noopener noreferrer" className="hover:text-pink-600">
                                  <Instagram size={20} />
                                </a>
                              ) : <Instagram size={20} className="opacity-25" />}
                              {editingLead.social_links?.facebook ? (
                                <a href={editingLead.social_links.facebook} target="_blank" rel="noopener noreferrer" className="hover:text-blue-600">
                                  <Facebook size={20} />
                                </a>
                              ) : <Facebook size={20} className="opacity-25" />}
                              {editingLead.social_links?.linkedin ? (
                                <a href={editingLead.social_links.linkedin} target="_blank" rel="noopener noreferrer" className="hover:text-blue-700">
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

              <div className="p-6 border-t border-gray-200 bg-gray-50 shrink-0 flex flex-col sm:flex-row gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="w-full sm:flex-1 py-3 text-gray-700 font-bold hover:bg-gray-100 rounded-xl transition-all border border-gray-200"
                >
                  {t('common.cancel')}
                </button>
                <button
                  // Link with form tag via id
                  form="lead-form"
                  type="submit"
                  disabled={saving}
                  className="w-full sm:flex-[2] py-3 bg-medical-600 text-white font-bold rounded-xl hover:bg-medical-700 shadow-md shadow-medical-200 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
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
      </div>
    </div>
  );
}
