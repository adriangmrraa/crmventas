import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, History, Tag, ArrowRight } from 'lucide-react';
import api from '../../../api/axios';
import { parseTags } from '../../../utils/parseTags';
import { useTranslation } from '../../../context/LanguageContext';
import { useAuth } from '../../../context/AuthContext';
import type { Lead } from './LeadsView';
import { LeadStatusSelector } from '../../../components/leads/LeadStatusSelector';
import { LeadHistoryTimeline } from '../../../components/leads/LeadHistoryTimeline';
import TaskSection from '../../../components/leads/TaskSection';
import { TagSelector } from '../../../components/leads/TagSelector';
import LeadNotesThread from '../../../components/leads/LeadNotesThread';
import DeriveToCloserModal from '../../../components/leads/DeriveToCloserModal';

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
  const [showHistory, setShowHistory] = useState(false);
  const [formData, setFormData] = useState({
    phone_number: '',
    first_name: '',
    last_name: '',
    email: '',
    status: 'new',
  });

  const isNew = id === 'new';

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
          {!isNew && (
            <button
              type="button"
              onClick={() => setShowHistory(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white/50 hover:text-white bg-white/[0.02] hover:bg-white/[0.04] rounded-lg transition-colors border border-white/[0.06]"
              title="Ver historial de estados"
            >
              <History size={18} className="text-violet-400" />
              <span className="hidden sm:inline">Historial</span>
            </button>
          )}
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
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6">
        {error && (
          <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
        {loading && !isNew ? (
          <div className="flex items-center justify-center py-12 text-white/40">{t('common.loading')}</div>
        ) : (
          <form onSubmit={handleSave} className="max-w-lg space-y-4">
            {isNew && (
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
            )}
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
              {isNew ? (
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
              ) : (
                <div className="p-3 bg-white/[0.02] border border-white/[0.04] rounded-xl flex items-center justify-between">
                  <div className="text-sm text-white/40 font-medium">Estado actual:</div>
                  <LeadStatusSelector
                    leadId={id!}
                    currentStatusCode={formData.status}
                    onChangeSuccess={() => {
                      // Actualizar el lead localmente tras el cambio exitoso
                      fetchLead();
                    }}
                  />
                </div>
              )}
            </div>
            {/* Tags section — only for existing leads */}
            {!isNew && id && (
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

            <div className="flex items-center gap-3 pt-2">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 font-medium transition-colors"
              >
                <Save size={18} />
                {saving ? 'Guardando...' : isNew ? 'Crear lead' : 'Guardar cambios'}
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
        )}

        {/* Tareas section — only for existing leads */}
        {!isNew && id && !loading && (
          <div className="max-w-lg mt-8 pt-6 border-t border-white/[0.06]">
            <TaskSection leadId={id} />
          </div>
        )}

        {/* Notes thread — only for existing leads */}
        {!isNew && id && !loading && (
          <div className="max-w-lg mt-8 pt-6 border-t border-white/[0.06]">
            <LeadNotesThread leadId={id} />
          </div>
        )}
      </div>

      {/* Modals */}
      {showHistory && id && (
        <LeadHistoryTimeline
          leadId={id}
          leadName={lead ? `${lead.first_name || ''} ${lead.last_name || ''}`.trim() || lead.phone_number : 'Lead'}
          onClose={() => setShowHistory(false)}
        />
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
