import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, User, Phone, Mail, Trash2 } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import type { Client } from './ClientsView';

const CRM_CLIENTS_BASE = '/admin/core/crm/clients';

export default function ClientDetailView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [client, setClient] = useState<Client | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    status: 'active' as 'active' | 'inactive',
  });

  useEffect(() => {
    if (id) fetchClient();
  }, [id]);

  useEffect(() => {
    if (client) {
      setFormData({
        first_name: client.first_name || '',
        last_name: client.last_name || '',
        email: client.email || '',
        status: (client.status === 'active' || client.status === 'inactive' ? client.status : 'active'),
      });
    }
  }, [client]);

  const fetchClient = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const response = await api.get<Client>(`${CRM_CLIENTS_BASE}/${id}`);
      setClient(response.data);
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('clients.error_load');
      setError(String(message));
      setClient(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !client) return;
    try {
      setSaving(true);
      setError(null);
      await api.put(`${CRM_CLIENTS_BASE}/${id}`, {
        first_name: formData.first_name || null,
        last_name: formData.last_name || null,
        email: formData.email || null,
        status: formData.status,
      });
      setClient((prev) => prev ? { ...prev, ...formData } : null);
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('clients.error_save');
      setError(String(message));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !confirm(t('clients.confirm_delete'))) return;
    try {
      await api.delete(`${CRM_CLIENTS_BASE}/${id}`);
      navigate('/crm/clientes', { replace: true });
    } catch (err) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('clients.error_delete');
      setError(String(message));
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">{t('common.loading')}</div>
    );
  }

  if (!client && !loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-gray-500">
        <p className="mb-4">{t('clients.not_found')}</p>
        <button onClick={() => navigate('/crm/clientes')} className="text-primary hover:underline font-medium">
          {t('clients.back_to_list')}
        </button>
      </div>
    );
  }

  const displayName = client ? [client.first_name, client.last_name].filter(Boolean).join(' ') || client.phone_number || '—' : '—';

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      <div className="flex items-center justify-between gap-4 p-4 lg:p-6 border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-4 min-w-0">
          <button
            type="button"
            onClick={() => navigate('/crm/clientes')}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 shrink-0"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-gray-900 truncate">{displayName}</h1>
            {client && <p className="text-sm text-gray-500 truncate">{client.phone_number}</p>}
          </div>
        </div>
        <button
          type="button"
          onClick={handleDelete}
          className="p-2 rounded-lg hover:bg-red-50 text-red-600 shrink-0 flex items-center gap-2"
          title={t('common.delete')}
        >
          <Trash2 size={18} />
          <span className="hidden sm:inline text-sm font-medium">{t('common.delete')}</span>
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}
        <form onSubmit={handleSave} className="max-w-lg space-y-6">
          <div>
            <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2">
              <User size={18} />
              {t('clients.personal_data')}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('clients.first_name')}</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData((f) => ({ ...f, first_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('clients.last_name')}</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData((f) => ({ ...f, last_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
              <div className="sm:col-span-2 flex items-center gap-2 text-sm text-gray-500">
                <Phone size={16} />
                {client?.phone_number}
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  <Mail size={14} />
                  {t('clients.email')}
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('clients.status')}</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData((f) => ({ ...f, status: e.target.value as 'active' | 'inactive' }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              <option value="active">{t('clients.status_active')}</option>
              <option value="inactive">{t('clients.status_inactive')}</option>
            </select>
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 font-medium"
            >
              <Save size={18} />
              {saving ? t('common.saving') : t('common.save_changes')}
            </button>
            <button
              type="button"
              onClick={() => navigate('/crm/clientes')}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 font-medium"
            >
              {t('common.cancel')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
