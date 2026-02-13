import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, Edit, Trash2, X, FileText, User } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import PageHeader from '../../../components/PageHeader';

const CRM_CLIENTS_BASE = '/admin/core/crm/clients';
const CRM_LEADS_BASE = '/admin/core/crm/leads';
const STATUS_OPTIONS = ['active', 'inactive'] as const;

export interface Client {
  id: number;
  phone_number: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export default function ClientsView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone_number: '',
    email: '',
    status: 'active' as typeof STATUS_OPTIONS[number],
  });
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [leads, setLeads] = useState<{ id: string; phone_number: string; first_name?: string; last_name?: string; email?: string }[]>([]);
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);

  useEffect(() => {
    fetchClients();
  }, [statusFilter, searchTerm]);

  const fetchClients = async () => {
    try {
      setLoading(true);
      const params: Record<string, string | number> = { limit: 100, offset: 0 };
      if (statusFilter) params.status = statusFilter;
      if (searchTerm.trim()) params.search = searchTerm.trim();
      const response = await api.get<Client[]>(CRM_CLIENTS_BASE, { params });
      setClients(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Error fetching clients:', err);
      setClients([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    try {
      if (editingClient) {
        await api.put(`${CRM_CLIENTS_BASE}/${editingClient.id}`, {
          first_name: formData.first_name || null,
          last_name: formData.last_name || null,
          email: formData.email || null,
          phone_number: formData.phone_number || null,
          status: formData.status,
        });
      } else {
        if (!formData.phone_number.trim()) {
          setModalError(t('clients.phone_required'));
          setSaving(false);
          return;
        }
        await api.post(CRM_CLIENTS_BASE, {
          phone_number: formData.phone_number.trim(),
          first_name: formData.first_name || undefined,
          last_name: formData.last_name || undefined,
          email: formData.email || undefined,
          status: formData.status,
          ...(selectedLeadId ? { lead_id: selectedLeadId } : {}),
        });
      }
      fetchClients();
      closeModal();
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('clients.error_save');
      setModalError(String(msg));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm(t('clients.confirm_delete'))) return;
    try {
      await api.delete(`${CRM_CLIENTS_BASE}/${id}`);
      fetchClients();
    } catch (err) {
      console.error('Error deleting client:', err);
      alert(t('clients.error_delete'));
    }
  };

  const openEditModal = (client: Client) => {
    setEditingClient(client);
    setFormData({
      first_name: client.first_name || '',
      last_name: client.last_name || '',
      phone_number: client.phone_number || '',
      email: client.email || '',
      status: (client.status as typeof formData.status) || 'active',
    });
    setShowModal(true);
  };

  const openCreateModal = async () => {
    setEditingClient(null);
    setSelectedLeadId(null);
    setFormData({
      first_name: '',
      last_name: '',
      phone_number: '',
      email: '',
      status: 'active',
    });
    setShowModal(true);
    try {
      const res = await api.get<typeof leads>(CRM_LEADS_BASE, { params: { limit: 200 } });
      setLeads(Array.isArray(res.data) ? res.data : []);
    } catch {
      setLeads([]);
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingClient(null);
    setSelectedLeadId(null);
    setModalError(null);
  };

  const handleSelectLead = (leadId: string) => {
    setSelectedLeadId(leadId || null);
    if (!leadId) return;
    const lead = leads.find((l) => l.id === leadId);
    if (lead) {
      setFormData({
        first_name: lead.first_name || '',
        last_name: lead.last_name || '',
        phone_number: lead.phone_number || '',
        email: lead.email || '',
        status: 'active',
      });
    }
  };

  return (
    <div className="p-4 lg:p-6 h-full flex flex-col min-h-0 overflow-hidden bg-gray-100">
      <PageHeader
        title={t('clients.title')}
        subtitle={t('clients.subtitle')}
        icon={<User size={22} />}
        action={
          <button
            onClick={openCreateModal}
            className="w-full sm:w-auto flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white px-4 py-2.5 rounded-xl transition-colors text-sm font-medium shadow-md active:scale-[0.98]"
          >
            <Plus size={20} />
            {t('clients.new_client')}
          </button>
        }
      />

      <div className="mb-6 grid grid-cols-1 sm:grid-cols-2 gap-4 shrink-0">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder={t('clients.search_placeholder')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-primary"
        >
          <option value="">{t('clients.all_statuses')}</option>
          <option value="active">{t('clients.status_active')}</option>
          <option value="inactive">{t('clients.status_inactive')}</option>
        </select>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto bg-white rounded-lg shadow">
        {loading ? (
          <div className="p-8 text-center text-gray-500">{t('common.loading')}</div>
        ) : clients.length === 0 ? (
          <div className="p-8 text-center text-gray-500">{t('clients.no_clients')}</div>
        ) : (
          <>
            <div className="overflow-x-auto hidden md:block">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('clients.client')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('clients.contact')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('clients.status')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('clients.date_added')}</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">{t('clients.actions')}</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {clients.map((client) => (
                    <tr key={client.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10 bg-primary-light rounded-full flex items-center justify-center text-white font-medium">
                            {(client.first_name || client.phone_number || '?').charAt(0).toUpperCase()}
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">
                              {[client.first_name, client.last_name].filter(Boolean).join(' ') || client.phone_number || '—'}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{client.phone_number}</div>
                        <div className="text-sm text-gray-500">{client.email || '—'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700 capitalize">
                          {t('clients.status_' + (client.status === 'active' ? 'active' : 'inactive'))}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(client.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => navigate(`/crm/clientes/${client.id}`)}
                            className="p-2 text-gray-600 hover:text-primary hover:bg-gray-100 rounded-lg transition-colors"
                            title={t('clients.view_detail')}
                          >
                            <FileText size={18} />
                          </button>
                          <button
                            onClick={() => openEditModal(client)}
                            className="p-2 text-gray-600 hover:text-primary hover:bg-gray-100 rounded-lg transition-colors"
                            title={t('common.edit')}
                          >
                            <Edit size={18} />
                          </button>
                          <button
                            onClick={() => handleDelete(client.id)}
                            className="p-2 text-gray-600 hover:text-red-600 hover:bg-gray-100 rounded-lg transition-colors"
                            title={t('common.delete')}
                          >
                            <Trash2 size={18} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="md:hidden divide-y">
              {clients.map((client) => (
                <div key={client.id} className="p-4 bg-white hover:bg-gray-50 transition-colors">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 bg-primary-light rounded-full flex items-center justify-center text-white font-medium shrink-0">
                        {(client.first_name || client.phone_number || '?').charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-sm font-semibold text-gray-900 truncate">
                          {[client.first_name, client.last_name].filter(Boolean).join(' ') || client.phone_number || '—'}
                        </h3>
                        <p className="text-xs text-gray-500 truncate">{client.phone_number}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => navigate(`/crm/clientes/${client.id}`)} className="p-2 text-gray-600 hover:text-primary active:bg-gray-200 rounded-lg">
                        <FileText size={18} />
                      </button>
                      <button onClick={() => openEditModal(client)} className="p-2 text-gray-600 hover:text-primary active:bg-gray-200 rounded-lg">
                        <Edit size={18} />
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-2">
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700 capitalize">{t('clients.status_' + (client.status === 'active' ? 'active' : 'inactive'))}</span>
                    <button onClick={() => handleDelete(client.id)} className="text-xs text-red-500 font-medium px-2 py-1 hover:bg-red-50 rounded">
                      {t('common.delete')}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto p-4">
          <div className="bg-white rounded-lg w-full max-w-2xl mx-4 my-8">
            <div className="flex justify-between items-center p-4 border-b sticky top-0 bg-white z-10">
              <h2 className="text-xl font-bold">
                {editingClient ? t('clients.edit_client') : t('clients.new_client')}
              </h2>
              <button onClick={closeModal} className="text-gray-500 hover:text-gray-700 p-1">
                <X size={24} />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6">
              {modalError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{modalError}</div>
              )}
              <div className="space-y-4">
                {!editingClient && leads.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('clients.load_from_lead')}</label>
                    <select
                      value={selectedLeadId || ''}
                      onChange={(e) => handleSelectLead(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                    >
                      <option value="">{t('clients.select_lead_placeholder')}</option>
                      {leads.map((lead) => (
                        <option key={lead.id} value={lead.id}>
                          {[lead.first_name, lead.last_name].filter(Boolean).join(' ') || lead.phone_number} — {lead.phone_number}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {!editingClient && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('clients.phone')} *</label>
                    <input
                      type="tel"
                      required
                      value={formData.phone_number}
                      onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('clients.first_name')}</label>
                    <input
                      type="text"
                      value={formData.first_name}
                      onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('clients.last_name')}</label>
                    <input
                      type="text"
                      value={formData.last_name}
                      onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('clients.email')}</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('clients.status')}</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as 'active' | 'inactive' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                  >
                    <option value="active">{t('clients.status_active')}</option>
                    <option value="inactive">{t('clients.status_inactive')}</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={closeModal} className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">
                  {t('common.cancel')}
                </button>
                <button type="submit" disabled={saving} className="px-4 py-2 text-white bg-primary rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50">
                  {editingClient ? t('common.save_changes') : t('clients.create_client')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
