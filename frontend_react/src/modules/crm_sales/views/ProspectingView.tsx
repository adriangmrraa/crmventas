import { useEffect, useMemo, useState } from 'react';
import { Loader2, Search, SendHorizontal, Building2 } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';

type TenantOption = {
  id: number;
  clinic_name: string;
};

type ProspectLead = {
  id: string;
  tenant_id: number;
  phone_number: string;
  first_name?: string;
  apify_title?: string;
  apify_category_name?: string;
  apify_city?: string;
  apify_state?: string;
  apify_website?: string;
  outreach_message_sent: boolean;
  outreach_send_requested: boolean;
  updated_at: string;
};

export default function ProspectingView() {
  const { t } = useTranslation();
  const [tenants, setTenants] = useState<TenantOption[]>([]);
  const [tenantId, setTenantId] = useState<number | null>(null);
  const [niche, setNiche] = useState('');
  const [location, setLocation] = useState('');
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [loadingLeads, setLoadingLeads] = useState(false);
  const [requestingSend, setRequestingSend] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [leads, setLeads] = useState<ProspectLead[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  const selectedIds = useMemo(
    () => Object.entries(selected).filter(([, value]) => value).map(([id]) => id),
    [selected],
  );

  const loadTenants = async () => {
    try {
      setLoadingTenants(true);
      const res = await api.get<TenantOption[]>('/admin/core/chat/tenants');
      const rows = Array.isArray(res.data) ? res.data : [];
      setTenants(rows);
      if (rows.length > 0) {
        setTenantId((prev) => prev ?? rows[0].id);
      }
    } catch {
      setError(t('prospecting.errorLoadingEntities'));
    } finally {
      setLoadingTenants(false);
    }
  };

  const loadLeads = async (targetTenantId?: number) => {
    const resolvedTenantId = targetTenantId ?? tenantId;
    if (!resolvedTenantId) return;
    try {
      setLoadingLeads(true);
      const res = await api.get<ProspectLead[]>('/admin/core/crm/prospecting/leads', {
        params: {
          tenant_id_override: resolvedTenantId,
          only_pending: false,
          limit: 300,
          offset: 0,
        },
      });
      const rows = Array.isArray(res.data) ? res.data : [];
      setLeads(rows);
      setSelected({});
    } catch {
      setError(t('prospecting.errorLoadingLeads'));
    } finally {
      setLoadingLeads(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  useEffect(() => {
    if (tenantId) {
      loadLeads(tenantId);
    }
  }, [tenantId]);

  const handleScrape = async () => {
    if (!tenantId || !niche.trim() || !location.trim()) {
      setError(t('prospecting.errorMissingFields'));
      return;
    }
    try {
      setError(null);
      setSuccess(null);
      setScraping(true);
      const res = await api.post('/admin/core/crm/prospecting/scrape', {
        tenant_id: tenantId,
        niche: niche.trim(),
        location: location.trim(),
      });
      await loadLeads(tenantId);
      const total = res.data?.total_results ?? 0;
      const imported = res.data?.imported ?? res.data?.imported_or_updated ?? 0;
      const skipped = res.data?.skipped_already_exists ?? 0;
      const fromWeb = res.data?.fetched_from_web ?? 0;
      setSuccess(
        t('prospecting.scrapeSuccess', { total, imported, skipped, fromWeb }),
      );
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || t('prospecting.errorScraping'));
    } finally {
      setScraping(false);
    }
  };

  const handleRequestSend = async (mode: 'selected' | 'pending_all') => {
    if (!tenantId) return;
    try {
      setError(null);
      setSuccess(null);
      setRequestingSend(true);
      const payload =
        mode === 'selected'
          ? { tenant_id: tenantId, lead_ids: selectedIds, only_pending: true }
          : { tenant_id: tenantId, only_pending: true };
      const res = await api.post('/admin/core/crm/prospecting/request-send', payload);
      await loadLeads(tenantId);
      setSuccess(t('prospecting.sendQueued', { count: res.data?.updated ?? 0 }));
    } catch {
      setError(t('prospecting.errorSendRequest'));
    } finally {
      setRequestingSend(false);
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      <div className="p-4 lg:p-6 border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-medical-100 flex items-center justify-center">
            <Search className="w-5 h-5 text-medical-700" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">{t('nav.prospecting')}</h1>
            <p className="text-sm text-gray-500">{t('prospecting.subtitle')}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="text-xs font-medium text-gray-600">{t('prospecting.entity')}</label>
            <select
              className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
              value={tenantId ?? ''}
              disabled={loadingTenants}
              onChange={(e) => setTenantId(Number(e.target.value))}
            >
              {tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.clinic_name} (ID: {tenant.id})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">{t('prospecting.niche')}</label>
            <input
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
              className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder={t('prospecting.nichePlaceholder')}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">{t('prospecting.location')}</label>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder={t('prospecting.locationPlaceholder')}
            />
          </div>
          <div className="flex items-end">
            <button
              type="button"
              onClick={handleScrape}
              disabled={scraping || loadingTenants}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-medical-600 text-white rounded-lg hover:bg-medical-700 disabled:opacity-50"
            >
              {scraping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {t('prospecting.runScrape')}
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mt-3">
          <button
            type="button"
            onClick={() => handleRequestSend('pending_all')}
            disabled={requestingSend || !tenantId}
            className="inline-flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            <SendHorizontal className="w-4 h-4" />
            {t('prospecting.sendAllPending')}
          </button>
          <button
            type="button"
            onClick={() => handleRequestSend('selected')}
            disabled={requestingSend || selectedIds.length === 0 || !tenantId}
            className="inline-flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            <SendHorizontal className="w-4 h-4" />
            {t('prospecting.sendSelected', { count: selectedIds.length })}
          </button>
        </div>

        {error && <div className="mt-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">{error}</div>}
        {success && <div className="mt-3 p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">{success}</div>}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6">
        {loadingLeads ? (
          <div className="py-8 text-center text-gray-500 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            {t('prospecting.loadingLeads')}
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-3 py-2 w-10"></th>
                  <th className="text-left px-3 py-2">{t('prospecting.colBusiness')}</th>
                  <th className="text-left px-3 py-2">{t('prospecting.colPhone')}</th>
                  <th className="text-left px-3 py-2">Website</th>
                  <th className="text-left px-3 py-2">Social</th>
                  <th className="text-left px-3 py-2">{t('prospecting.colLocation')}</th>
                  <th className="text-left px-3 py-2">{t('prospecting.colStatus')}</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id} className="border-t border-gray-100">
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={Boolean(selected[lead.id])}
                        onChange={(e) => setSelected((prev) => ({ ...prev, [lead.id]: e.target.checked }))}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <div className="font-medium text-gray-800">{lead.apify_title || lead.first_name || '—'}</div>
                      <div className="text-xs text-gray-500">{lead.apify_category_name || '—'}</div>
                    </td>
                    <td className="px-3 py-2">{lead.phone_number}</td>
                    <td className="px-3 py-2 text-xs truncate max-w-[150px]">
                      {lead.apify_website ? (
                        <a href={lead.apify_website} target="_blank" rel="noopener noreferrer" className="text-medical-600 hover:underline">
                          {lead.apify_website.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
                        </a>
                      ) : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        {/* Placeholder for social links icons if extracted in future */}
                        <span className="text-gray-400">—</span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1 text-gray-700">
                        <Building2 className="w-3 h-3" />
                        {lead.apify_city || '—'} {lead.apify_state ? `(${lead.apify_state})` : ''}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      {lead.outreach_message_sent ? (
                        <span className="px-2 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs">{t('prospecting.statusSent')}</span>
                      ) : lead.outreach_send_requested ? (
                        <span className="px-2 py-1 rounded-full bg-amber-50 text-amber-700 text-xs">{t('prospecting.statusRequested')}</span>
                      ) : (
                        <span className="px-2 py-1 rounded-full bg-gray-100 text-gray-700 text-xs">{t('prospecting.statusPending')}</span>
                      )}
                    </td>
                  </tr>
                ))}
                {leads.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-gray-500">
                      {t('prospecting.noLeads')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
