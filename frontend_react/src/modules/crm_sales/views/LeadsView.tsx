import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Plus, Search, MessageSquare } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';

const CRM_LEADS_BASE = '/niche/crm_sales/leads';

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
  created_at: string;
  updated_at: string;
}

export default function LeadsView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchLeads();
  }, [statusFilter]);

  const fetchLeads = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: Record<string, string | number> = { limit: 50, offset: 0 };
      if (statusFilter) params.status = statusFilter;
      const response = await api.get<Lead[]>(CRM_LEADS_BASE, { params });
      setLeads(Array.isArray(response.data) ? response.data : []);
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Failed to load leads';
      setError(String(message));
      setLeads([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredLeads = leads.filter((lead) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const name = [lead.first_name, lead.last_name].filter(Boolean).join(' ').toLowerCase();
    return (
      name.includes(term) ||
      (lead.phone_number || '').includes(term) ||
      (lead.email || '').toLowerCase().includes(term)
    );
  });

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 lg:p-6 border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-medical-100 flex items-center justify-center">
            <Users className="w-5 h-5 text-medical-700" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">{t('nav.leads')}</h1>
            <p className="text-sm text-gray-500">{filteredLeads.length} {filteredLeads.length === 1 ? 'lead' : 'leads'}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 sm:flex-initial min-w-[180px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder={t('common.search')}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-medical-500 focus:border-medical-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-medical-500"
          >
            <option value="">All statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="interested">Interested</option>
            <option value="negotiation">Negotiation</option>
            <option value="closed_won">Closed Won</option>
            <option value="closed_lost">Closed Lost</option>
          </select>
          <button
            type="button"
            onClick={() => navigate('/crm/leads/new')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-medical-600 text-white rounded-lg hover:bg-medical-700 text-sm font-medium"
          >
            <Plus size={18} />
            Add lead
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}
        {loading ? (
          <div className="flex items-center justify-center py-12 text-gray-500">{t('common.loading')}</div>
        ) : filteredLeads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Users className="w-12 h-12 text-gray-300 mb-3" />
            <p>No leads yet.</p>
            <button
              type="button"
              onClick={() => navigate('/crm/leads/new')}
              className="mt-3 text-medical-600 hover:underline font-medium"
            >
              Add your first lead
            </button>
          </div>
        ) : (
          <ul className="space-y-2">
            {filteredLeads.map((lead) => {
              const name = [lead.first_name, lead.last_name].filter(Boolean).join(' ') || lead.phone_number || '—';
              return (
                <li
                  key={lead.id}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:border-medical-300 hover:shadow-sm transition-all cursor-pointer flex items-center justify-between gap-4"
                  onClick={() => navigate(`/crm/leads/${lead.id}`)}
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-10 h-10 rounded-full bg-medical-100 flex items-center justify-center shrink-0">
                      <span className="text-medical-700 font-semibold text-sm">{name.charAt(0).toUpperCase()}</span>
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900 truncate">{name}</p>
                      <p className="text-sm text-gray-500 truncate">{lead.phone_number}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700 capitalize">
                      {lead.status.replace('_', ' ')}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate('/chats');
                      }}
                      className="p-2 text-gray-400 hover:text-medical-600 rounded-lg hover:bg-medical-50"
                      title="Open chat"
                    >
                      <MessageSquare size={18} />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
