import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Tag, ArrowRight, AlertTriangle, Ban, ChevronDown } from 'lucide-react';
import api from '../../../api/axios';
import { parseTags } from '../../../utils/parseTags';
import { useTranslation } from '../../../context/LanguageContext';
import { useAuth } from '../../../context/AuthContext';
import type { Lead } from './LeadsView';
import { LeadStatusSelector } from '../../../components/leads/LeadStatusSelector';
import TaskSection from '../../../components/leads/TaskSection';
import { TagSelector } from '../../../components/leads/TagSelector';
import DeriveToCloserModal from '../../../components/leads/DeriveToCloserModal';
import UnifiedTimeline from '../../../components/leads/UnifiedTimeline';

const CRM_LEADS_BASE = '/admin/core/crm/leads';

export default function LeadDetailView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user } = useAuth();
  const [lead, setLead] = useState<Lead | null>(null);
  const [showDeriveModal, setShowDeriveModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showBlockMenu, setShowBlockMenu] = useState(false);
  const [blocking, setBlocking] = useState(false);
  const [formData, setFormData] = useState({
    phone_number: '',
    first_name: '',
    last_name: '',
    email: '',
    status: 'new',
    estimated_value: 0,
    close_probability: 0,
  });

  const isNew = id === 'new';
  const [activeTab, setActiveTab] = useState<'timeline' | 'datos' | 'tareas'>('timeline');

  useEffect(() => {
    if (!isNew && id) fetchLead();
    else setLoading(false);
  }, [id, isNew]);

  useEffect(() => {
    if (lead) {
      setFormData({
        phone_number: lead.phone_number || '',
        first_name: lead.first_name || '',
        last_name: lead.last_name || '',
        email: lead.email || '',
        status: lead.status || 'new',
        estimated_value: lead.estimated_value ?? 0,
        close_probability: lead.close_probability ?? 0,
      });
    }
  }, [lead]);

  const fetchLead = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const response = await api.get<Lead>(`${CRM_LEADS_BASE}/${id}`);
      if (!response.data) {
        setError('Lead not found');
        return;
      }
      setLead(response.data);
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError('Lead not found');
      } else {
        const message = err.response?.data?.detail || 'Failed to load lead';
        setError(String(message));
      }
      setLead(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isNew) {
      if (!formData.phone_number.trim()) {
        setError('Phone number is required.');
        return;
      }
      try {
        setSaving(true);
        setError(null);
        const created = await api.post<Lead>(CRM_LEADS_BASE, {
          phone_number: formData.phone_number.trim(),
          first_name: formData.first_name || undefined,
          last_name: formData.last_name || undefined,
          email: formData.email || undefined,
          status: formData.status,
        });
        navigate(`/crm/leads/${created.data.id}`, { replace: true });
      } catch (err: unknown) {
        const message = err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : 'Failed to create lead';
        setError(String(message));
      } finally {
        setSaving(false);
      }
      return;
    }
    if (!id || !lead) return;
    try {
      setSaving(true);
      setError(null);
      await api.put(`${CRM_LEADS_BASE}/${id}`, {
        first_name: formData.first_name || null,
        last_name: formData.last_name || null,
        email: formData.email || null,
        status: formData.status,
        estimated_value: formData.estimated_value,
        close_probability: formData.close_probability,
      });
      setLead((prev) => prev ? { ...prev, ...formData } : null);
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Failed to save';
      setError(String(message));
    } finally {
      setSaving(false);
    }
  };

  const BLOCK_REASONS = [
    { value: 'lead_descartado', label: 'Lead descartado definitivo' },
    { value: 'ex_cliente', label: 'Ex cliente' },
    { value: 'spam', label: 'Spam' },
    { value: 'numero_invalido', label: 'Número inválido' },
    { value: 'no_contactar', label: 'Solicitud de no contacto' },
  ];

  const handleBlockLead = async (reason: string) => {
    if (!id || !lead) return;
    if (!window.confirm(`¿Bloquear este contacto con motivo "${reason}"? Se agregará a la blacklist y el lead quedará como bloqueado.`)) return;
    setBlocking(true);
    setShowBlockMenu(false);
    try {
      await api.post(`${CRM_LEADS_BASE}/${id}/block`, { reason });
      fetchLead();
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Error al bloquear';
      setError(String(msg));
    } finally {
      setBlocking(false);
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      <div className="flex items-center gap-4 p-4 lg:p-6 border-b border-white/[0.06] bg-white/[0.03] shrink-0">
        <button
          type="button"
          onClick={() => navigate('/crm/leads')}
          className="p-2 rounded-lg hover:bg-white/[0.04] text-white/50"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-white truncate">
            {isNew ? 'New lead' : (lead ? [lead.first_name, lead.last_name].filter(Boolean).join(' ') || lead.phone_number : 'Lead')}
          </h1>
          {lead && <p className="text-sm text-white/40">{lead.phone_number}</p>}
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {!isNew && user && (user.role === 'setter' || user.role === 'ceo') && (
            <button
              type="button"
              onClick={() => setShowDeriveModal(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white/50 hover:text-white bg-violet-500/5 hover:bg-violet-500/10 rounded-lg transition-colors border border-violet-500/20"
              title="Derivar a closer"
            >
              <ArrowRight size={18} className="text-violet-400" />
              <span className="hidden sm:inline">Derivar a closer</span>
            </button>
          )}
          {!isNew && user && user.role === 'ceo' && lead && lead.status !== 'blocked' && (
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowBlockMenu(v => !v)}
                disabled={blocking}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-red-400/70 hover:text-red-400 bg-red-500/5 hover:bg-red-500/10 rounded-lg transition-colors border border-red-500/20 disabled:opacity-50"
                title="Bloquear contacto"
              >
                <Ban size={16} className="text-red-400" />
                <span className="hidden sm:inline">{blocking ? 'Bloqueando...' : 'Bloquear'}</span>
                <ChevronDown size={13} className="text-red-400/50" />
              </button>
              {showBlockMenu && (
                <div className="absolute right-0 top-full mt-1 w-56 bg-[#0d1120] border border-white/[0.08] rounded-xl shadow-xl z-50 overflow-hidden">
                  <p className="px-4 py-2 text-[10px] font-bold text-white/30 uppercase tracking-wider border-b border-white/[0.06]">
                    Motivo del bloqueo
                  </p>
                  {BLOCK_REASONS.map(r => (
                    <button
                      key={r.value}
                      type="button"
                      onClick={() => handleBlockLead(r.value)}
                      className="w-full text-left px-4 py-2.5 text-sm text-white/70 hover:text-white hover:bg-red-500/10 transition-colors"
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              )}
              {showBlockMenu && (
                <div className="fixed inset-0 z-40" onClick={() => setShowBlockMenu(false)} />
              )}
            </div>
          )}
        </div>
      </div>

      {/* DEV-50: banner de duplicados pendientes */}
      {!isNew && lead && (lead as Lead & { has_pending_duplicates?: boolean }).has_pending_duplicates && (
        <div className="flex items-center gap-3 px-4 lg:px-6 py-2.5 bg-yellow-500/10 border-b border-yellow-500/20 shrink-0">
          <AlertTriangle size={15} className="text-yellow-400 shrink-0" />
          <span className="text-sm text-yellow-300/90 flex-1">
            Este lead tiene posibles duplicados.
          </span>
          <button
            type="button"
            onClick={() => navigate('/crm/duplicados')}
            className="text-xs text-yellow-400 hover:text-yellow-300 font-medium transition-colors shrink-0"
          >
            Ver duplicados →
          </button>
        </div>
      )}

      {/* ── NEW LEAD FORM (isNew = true) ── */}
      {isNew && (
        <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6">
          {error && (
            <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}
          <form onSubmit={handleSave} className="max-w-lg space-y-4">
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1">Teléfono *</label>
              <input
                type="tel"
                value={formData.phone_number}
                onChange={(e) => setFormData((f) => ({ ...f, phone_number: e.target.value }))}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1">Nombre</label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData((f) => ({ ...f, first_name: e.target.value }))}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1">Apellido</label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => setFormData((f) => ({ ...f, last_name: e.target.value }))}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData((f) => ({ ...f, status: e.target.value }))}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50"
              >
                <option value="nuevo" className="bg-[#1a1a2e] text-white">Nuevo</option>
                <option value="contactado" className="bg-[#1a1a2e] text-white">Contactado</option>
                <option value="calificado" className="bg-[#1a1a2e] text-white">Calificado</option>
                <option value="llamada_agendada" className="bg-[#1a1a2e] text-white">Llamada Agendada</option>
                <option value="negociacion" className="bg-[#1a1a2e] text-white">En Negociación</option>
                <option value="cerrado_ganado" className="bg-[#1a1a2e] text-white">Cerrado Ganado</option>
                <option value="cerrado_perdido" className="bg-[#1a1a2e] text-white">Cerrado Perdido</option>
              </select>
            </div>
            <div className="flex items-center gap-3 pt-2">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 font-medium transition-colors"
              >
                <Save size={18} />
                {saving ? 'Guardando...' : 'Crear lead'}
              </button>
              <button
                type="button"
                onClick={() => navigate('/crm/leads')}
                className="px-4 py-2.5 text-white/50 hover:text-white border border-white/[0.08] rounded-lg hover:bg-white/[0.04] transition-colors"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── EXISTING LEAD: 2-col desktop, tabs mobile ── */}
      {!isNew && (
        <>
          {/* Mobile tab bar */}
          <div className="lg:hidden shrink-0 flex border-b border-white/[0.06] bg-white/[0.02]">
            {(['timeline', 'datos', 'tareas'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                  activeTab === tab
                    ? 'text-white border-b-2 border-violet-500'
                    : 'text-white/40 hover:text-white/70'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Error bar */}
          {error && (
            <div className="mx-4 mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm shrink-0">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12 text-white/40 flex-1">
              {t('common.loading')}
            </div>
          ) : (
            <div className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden">
              {/* ── LEFT: Timeline (60%) ── */}
              <div
                className={`lg:flex-[3] min-h-0 overflow-y-auto p-4 lg:p-6 lg:border-r border-white/[0.06] ${
                  activeTab !== 'timeline' ? 'hidden lg:flex lg:flex-col' : 'flex flex-col'
                }`}
              >
                {id && <UnifiedTimeline leadId={id} />}
              </div>

              {/* ── RIGHT: Datos + Tags + Tasks (40%) ── */}
              <div
                className={`lg:flex-[2] min-h-0 overflow-y-auto p-4 lg:p-6 space-y-6 ${
                  activeTab === 'datos' ? 'block' : 'hidden lg:block'
                }`}
              >
                {/* Datos form */}
                <form onSubmit={handleSave} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1">Nombre</label>
                    <input
                      type="text"
                      value={formData.first_name}
                      onChange={(e) => setFormData((f) => ({ ...f, first_name: e.target.value }))}
                      className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1">Apellido</label>
                    <input
                      type="text"
                      value={formData.last_name}
                      onChange={(e) => setFormData((f) => ({ ...f, last_name: e.target.value }))}
                      className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1">Email</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                      className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
                    />
                  </div>

                  {/* Status selector */}
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1.5">Status</label>
                    <div className="p-3 bg-white/[0.02] border border-white/[0.04] rounded-xl flex items-center justify-between">
                      <div className="text-sm text-white/40 font-medium">Estado actual:</div>
                      <LeadStatusSelector
                        leadId={id!}
                        currentStatusCode={formData.status}
                        onChangeSuccess={() => fetchLead()}
                      />
                    </div>
                  </div>

                  {/* Tags */}
                  {id && (
                    <div>
                      <label className="block text-sm font-medium text-white/70 mb-1.5">
                        <span className="flex items-center gap-1.5">
                          <Tag size={14} className="text-white/40" />
                          Etiquetas
                        </span>
                      </label>
                      <div className="p-3 bg-white/[0.02] border border-white/[0.04] rounded-xl">
                        <TagSelector
                          leadId={id}
                          currentTags={parseTags(lead?.tags)}
                          onTagsChange={(newTags) => {
                            setLead((prev) => prev ? { ...prev, tags: newTags } : null);
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Forecasting fields */}
                  <div className="pt-2 border-t border-white/[0.04] space-y-3">
                    <p className="text-xs font-bold text-white/30 uppercase tracking-wider">Forecast</p>

                    {/* Ticket estimado */}
                    <div>
                      <label className="block text-sm font-medium text-white/70 mb-1">Ticket estimado</label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 text-sm">$</span>
                        <input
                          type="number"
                          min={0}
                          step={1}
                          value={formData.estimated_value}
                          onChange={(e) => setFormData((f) => ({ ...f, estimated_value: parseFloat(e.target.value) || 0 }))}
                          className="w-full pl-7 pr-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
                        />
                      </div>
                    </div>

                    {/* Probabilidad de cierre */}
                    <div>
                      <label className="block text-sm font-medium text-white/70 mb-1">Probabilidad de cierre</label>
                      <div className="relative">
                        <input
                          type="number"
                          min={0}
                          max={100}
                          step={5}
                          value={formData.close_probability}
                          onChange={(e) => setFormData((f) => ({ ...f, close_probability: parseFloat(e.target.value) || 0 }))}
                          className="w-full pl-3 pr-8 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
                        />
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 text-sm">%</span>
                      </div>
                    </div>

                    {/* Revenue ponderado — read only, live calculation */}
                    <div>
                      <label className="block text-sm font-medium text-white/70 mb-1">Revenue ponderado</label>
                      <div className="px-3 py-2 bg-white/[0.02] border border-white/[0.04] rounded-lg text-sm text-emerald-400 font-semibold">
                        ${(formData.estimated_value * (formData.close_probability / 100)).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 pt-1">
                    <button
                      type="submit"
                      disabled={saving}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 text-sm font-medium transition-colors"
                    >
                      <Save size={16} />
                      {saving ? 'Guardando...' : 'Guardar cambios'}
                    </button>
                  </div>
                </form>

                {/* Tareas — always visible in desktop right column */}
                {id && (
                  <div className="pt-4 border-t border-white/[0.06]">
                    <TaskSection leadId={id} />
                  </div>
                )}
              </div>

              {/* ── TAREAS: visible on mobile tab + inside right col on desktop ── */}
              <div
                className={`p-4 lg:hidden ${activeTab === 'tareas' ? 'block' : 'hidden'}`}
              >
                {id && <TaskSection leadId={id} />}
              </div>
            </div>
          )}
        </>
      )}

      {showDeriveModal && id && (
        <DeriveToCloserModal
          leadId={id}
          onClose={() => setShowDeriveModal(false)}
          onSuccess={() => {
            setShowDeriveModal(false);
            fetchLead();
          }}
        />
      )}
    </div>
  );
}
