import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, History } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import type { Lead } from './LeadsView';
import { LeadStatusSelector } from '../../../components/leads/LeadStatusSelector';
import { LeadHistoryTimeline } from '../../../components/leads/LeadHistoryTimeline';

const CRM_LEADS_BASE = '/admin/core/crm/leads';

export default function LeadDetailView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [lead, setLead] = useState<Lead | null>(null);
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
      <div className="flex items-center gap-4 p-4 lg:p-6 border-b border-gray-200 bg-white shrink-0">
        <button
          type="button"
          onClick={() => navigate('/crm/leads')}
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-600"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-gray-900 truncate">
            {isNew ? 'New lead' : (lead ? [lead.first_name, lead.last_name].filter(Boolean).join(' ') || lead.phone_number : 'Lead')}
          </h1>
          {lead && <p className="text-sm text-gray-500">{lead.phone_number}</p>}
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {!isNew && (
            <button
              type="button"
              onClick={() => setShowHistory(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
              title="Ver historial de estados"
            >
              <History size={18} className="text-blue-600" />
              <span className="hidden sm:inline">Historial</span>
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}
        {loading && !isNew ? (
          <div className="flex items-center justify-center py-12 text-gray-500">{t('common.loading')}</div>
        ) : (
          <form onSubmit={handleSave} className="max-w-lg space-y-4">
            {isNew && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone number *</label>
                <input
                  type="tel"
                  value={formData.phone_number}
                  onChange={(e) => setFormData((f) => ({ ...f, phone_number: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 focus:border-medical-500"
                  required
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">First name</label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData((f) => ({ ...f, first_name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 focus:border-medical-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Last name</label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => setFormData((f) => ({ ...f, last_name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 focus:border-medical-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 focus:border-medical-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Status</label>
              {isNew ? (
                <select
                  value={formData.status}
                  onChange={(e) => setFormData((f) => ({ ...f, status: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 focus:border-medical-500 bg-white"
                >
                  <option value="new">New</option>
                  <option value="contacted">Contacted</option>
                  <option value="interested">Interested</option>
                  <option value="negotiation">Negotiation</option>
                  <option value="closed_won">Closed Won</option>
                  <option value="closed_lost">Closed Lost</option>
                </select>
              ) : (
                <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex items-center justify-between">
                  <div className="text-sm text-slate-500 font-medium">Estado actual:</div>
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
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 bg-medical-600 text-white rounded-lg hover:bg-medical-700 disabled:opacity-50 font-medium"
            >
              <Save size={18} />
              {saving ? t('common.saving') : isNew ? 'Create lead' : t('common.save_changes')}
            </button>
          </form>
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
    </div>
  );
}
