import { useEffect, useMemo, useState } from 'react';
import {
  Search, Send, Play, CheckCircle2, AlertCircle, Loader2,
  Globe, Instagram, Facebook, Filter, X,
  Mail, Star, MapPin, ChevronUp, ChevronDown
} from 'lucide-react';
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
  email?: string;
  apify_total_score?: number;
  apify_reviews_count?: number;
  apify_rating?: number;
  apify_reviews?: number;
  apify_address?: string;
  social_links?: Record<string, string>;
  outreach_message_sent: boolean;
  outreach_send_requested: boolean;
  updated_at: string;
};

type WhatsAppTemplate = {
  name: string;
  status: string;
  language: string;
  category: string;
};

export default function ProspectingView() {
  const { t } = useTranslation();
  const [tenants, setTenants] = useState<TenantOption[]>([]);
  const [tenantId, setTenantId] = useState<number | null>(null);
  const [niche, setNiche] = useState('');
  const [location, setLocation] = useState('');
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [maxPlaces, setMaxPlaces] = useState(30);
  const [loadingLeads, setLoadingLeads] = useState(false);
  const [requestingSend, setRequestingSend] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [leads, setLeads] = useState<ProspectLead[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [templates, setTemplates] = useState<WhatsAppTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [isHeaderExpanded, setIsHeaderExpanded] = useState(true);

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

  const loadTemplates = async () => {
    if (!tenantId) return;
    try {
      setLoadingTemplates(true);
      const res = await api.get<{ items: WhatsAppTemplate[] }>('/admin/core/crm/prospecting/templates');
      setTemplates(res.data.items || []);
      if (res.data.items?.length > 0) {
        setSelectedTemplate(res.data.items[0].name);
      } else {
        setSelectedTemplate('');
      }
    } catch {
      console.error('Error loading templates');
    } finally {
      setLoadingTemplates(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  useEffect(() => {
    if (tenantId) {
      loadLeads(tenantId);
      loadTemplates();
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
        max_places: maxPlaces,
      }, { timeout: 300000 }); // 5 minutes timeout for scraping
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
          ? {
            tenant_id: tenantId,
            lead_ids: selectedIds,
            only_pending: true,
            template_name: selectedTemplate || undefined
          }
          : {
            tenant_id: tenantId,
            only_pending: true,
            template_name: selectedTemplate || undefined
          };
      const res = await api.post('/admin/core/crm/prospecting/request-send', payload);
      await loadLeads(tenantId);
      const count = res.data?.updated ?? 0;
      if (selectedTemplate) {
        setSuccess(t('prospecting.statusSending') + ` (${count} leads)`);
      } else {
        setSuccess(t('prospecting.sendQueued', { count }));
      }
    } catch {
      setError(t('prospecting.errorSendRequest'));
    } finally {
      setRequestingSend(false);
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* FIXED TITLE BAR */}
      <div
        onClick={() => {
          if (window.innerWidth < 1024) setIsHeaderExpanded(!isHeaderExpanded);
        }}
        className="flex items-center justify-between p-4 lg:p-6 border-b border-gray-200 bg-white shrink-0 cursor-pointer lg:cursor-default"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
            <Search className="w-5 h-5 text-emerald-700" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">{t('nav.prospecting')}</h1>
            <p className="text-sm text-gray-500">
              {leads.length} {t('prospecting.subtitle')}
            </p>
          </div>
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsHeaderExpanded(!isHeaderExpanded);
          }}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-500"
          title={isHeaderExpanded ? "Colapsar filtros" : "Expandir filtros"}
        >
          {isHeaderExpanded ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
        </button>
      </div>

      {/* SCROLLABLE CONTENT AREA */}
      <div className="flex-1 overflow-y-auto min-h-0 bg-gray-50/30">
        {/* COLLAPSIBLE FILTERS & ACTIONS BAR */}
        <div
          className={`transition-all duration-300 ease-in-out overflow-hidden border-b border-gray-200 bg-white/50
          ${isHeaderExpanded ? 'max-h-[500px] opacity-100 p-4 lg:p-6' : 'max-h-0 opacity-0 p-0 overflow-hidden'}`}
        >
          <div className="space-y-6">
            {/* FILTERS & ACTIONS BAR */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div>
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none mb-1.5 block">Entidad</label>
                <select
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl text-sm bg-white focus:ring-2 focus:ring-emerald-500 outline-none"
                  value={tenantId ?? ''}
                  disabled={loadingTenants}
                  onChange={(e) => setTenantId(Number(e.target.value))}
                >
                  {tenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.clinic_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none mb-1.5 block">{t('prospecting.niche')}</label>
                <input
                  type="text"
                  value={niche}
                  onChange={(e) => setNiche(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-emerald-500 transition-all outline-none"
                  placeholder={t('prospecting.nichePlaceholder')}
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none mb-1.5 block">{t('prospecting.location')}</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-emerald-500 transition-all outline-none"
                  placeholder={t('prospecting.locationPlaceholder')}
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none mb-1.5 block">Cant. Resultados</label>
                <select
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl text-sm bg-white focus:ring-2 focus:ring-emerald-500 outline-none"
                  value={maxPlaces}
                  onChange={(e) => setMaxPlaces(Number(e.target.value))}
                >
                  <option value={10}>10 resultados</option>
                  <option value={30}>30 resultados</option>
                  <option value={60}>60 resultados</option>
                  <option value={100}>100 resultados</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={handleScrape}
                  disabled={scraping || !niche || !location}
                  className="w-full flex items-center justify-center gap-2 px-6 py-2 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 disabled:opacity-50 transition-all font-bold shadow-md shadow-emerald-100 active:scale-[0.98]"
                >
                  {scraping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  {scraping ? 'Buscando...' : t('prospecting.runScrape')}
                </button>
              </div>
            </div>

            {/* Template & Send Mass Support */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-4 bg-emerald-50/50 border border-emerald-100 rounded-xl">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <span className="text-sm font-bold text-emerald-800 whitespace-nowrap">Plan de Mensajes:</span>
                <div className="relative">
                  <select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    className="w-full sm:w-auto pl-4 pr-10 py-2 border border-emerald-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-emerald-500 outline-none appearance-none font-medium text-emerald-900"
                  >
                    {templates.length === 0 ? (
                      <option value="">{loadingTemplates ? t('common.loading') : t('prospecting.noTemplates')}</option>
                    ) : (
                      <>
                        <option value="">{t('prospecting.selectTemplate')}</option>
                        {templates.map((tpl) => (
                          <option key={tpl.name} value={tpl.name}>
                            {tpl.name}
                          </option>
                        ))}
                      </>
                    )}
                  </select>
                  <Filter className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-400 pointer-events-none" />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleRequestSend('selected')}
                  disabled={requestingSend || selectedIds.length === 0 || !selectedTemplate}
                  className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-all font-bold text-sm shadow-sm"
                >
                  {requestingSend ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  {t('prospecting.sendSelected', { count: selectedIds.length })}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const toSelect: Record<string, boolean> = {};
                    leads.filter(l => !l.outreach_message_sent).forEach(l => toSelect[l.id] = true);
                    setSelected(toSelect);
                  }}
                  className="flex-1 sm:flex-none px-4 py-2.5 bg-white border border-emerald-200 text-emerald-700 rounded-lg hover:bg-emerald-50 transition-all text-sm font-bold shadow-sm"
                >
                  Auto-selección
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="p-4 lg:p-6 space-y-6">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-center gap-3">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <p className="text-sm font-medium">{error}</p>
            </div>
          )}
          {success && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <p className="text-sm font-medium">{success}</p>
            </div>
          )}

          {loadingLeads ? (
            <div className="py-12 text-center text-gray-500 flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
              <p className="font-medium">{t('prospecting.loadingLeads')}</p>
            </div>
          ) : (
            <>
              {/* Desktop Table View */}
              <div className="hidden lg:block bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-3 w-10">
                        <input
                          type="checkbox"
                          checked={leads.length > 0 && selectedIds.length === leads.length}
                          onChange={(e) => {
                            const next: Record<string, boolean> = {};
                            if (e.target.checked) {
                              leads.forEach(l => next[l.id] = true);
                            }
                            setSelected(next);
                          }}
                          className="rounded text-emerald-600 focus:ring-emerald-500"
                        />
                      </th>
                      <th className="text-left px-4 py-3 font-bold text-gray-900">{t('prospecting.colBusiness')}</th>
                      <th className="text-left px-4 py-3 font-bold text-gray-900">{t('prospecting.colPhone')}</th>
                      <th className="text-left px-4 py-3 font-bold text-gray-900">Email</th>
                      <th className="text-left px-4 py-3 font-bold text-gray-900">Rating</th>
                      <th className="text-left px-4 py-3 font-bold text-gray-900">Website</th>
                      <th className="text-left px-4 py-3 font-bold text-gray-900">Social</th>
                      <th className="text-left px-4 py-3 font-bold text-gray-900">{t('prospecting.colStatus')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {leads.map((lead) => (
                      <tr key={lead.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={Boolean(selected[lead.id])}
                            onChange={(e) => setSelected(prev => ({ ...prev, [lead.id]: e.target.checked }))}
                            className="rounded text-emerald-600 focus:ring-emerald-500"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-bold text-gray-900">{lead.apify_title || '—'}</div>
                          <div className="text-xs text-emerald-600 font-medium">{lead.apify_category_name || '—'}</div>
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-600">{lead.phone_number}</td>
                        <td className="px-4 py-3">
                          {lead.email ? (
                            <div className="flex items-center gap-1.5 text-gray-600">
                              <Mail className="w-3.5 h-3.5 text-gray-400" />
                              <span className="truncate max-w-[120px]" title={lead.email}>{lead.email}</span>
                            </div>
                          ) : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="px-4 py-3">
                          {lead.apify_rating ? (
                            <div className="flex items-center gap-1 text-amber-500">
                              <Star className="w-3.5 h-3.5 fill-current" />
                              <span className="font-bold">{lead.apify_rating.toFixed(1)}</span>
                            </div>
                          ) : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="px-4 py-3">
                          {lead.apify_website ? (
                            <a href={lead.apify_website} target="_blank" rel="noopener noreferrer" className="p-2 bg-gray-50 text-gray-500 rounded-lg hover:bg-emerald-50 hover:text-emerald-600 transition-colors inline-block">
                              <Globe className="w-4 h-4" />
                            </a>
                          ) : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            {lead.social_links?.instagram && (
                              <a href={lead.social_links.instagram} target="_blank" rel="noopener noreferrer" className="p-1.5 text-pink-500 hover:bg-pink-50 rounded-lg transition-colors">
                                <Instagram className="w-4 h-4" />
                              </a>
                            )}
                            {lead.social_links?.facebook && (
                              <a href={lead.social_links.facebook} target="_blank" rel="noopener noreferrer" className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                                <Facebook className="w-4 h-4" />
                              </a>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {lead.outreach_message_sent ? (
                            <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 text-[10px] font-bold uppercase tracking-wider">{t('prospecting.statusSent')}</span>
                          ) : lead.outreach_send_requested ? (
                            <span className="px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 text-[10px] font-bold uppercase tracking-wider">{t('prospecting.statusRequested')}</span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-md bg-gray-100 text-gray-700 text-[10px] font-bold uppercase tracking-wider">{t('prospecting.statusPending')}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile Card Layout */}
              <div className="lg:hidden space-y-4">
                {leads.map((lead) => (
                  <div
                    key={lead.id}
                    className={`bg-white border border-gray-200 rounded-2xl p-4 shadow-sm active:bg-gray-50 transition-colors ${selected[lead.id] ? 'ring-2 ring-emerald-500' : ''}`}
                    onClick={() => setSelected((prev) => ({ ...prev, [lead.id]: !prev[lead.id] }))}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center shrink-0 border border-emerald-100 mt-0.5">
                          <span className="text-emerald-700 font-bold">{(lead.apify_title || '—').charAt(0)}</span>
                        </div>
                        <div>
                          <div className="font-bold text-gray-900 leading-tight mb-0.5">
                            {lead.apify_title || '—'}
                          </div>
                          <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">
                            {lead.apify_category_name || '—'}
                          </div>
                        </div>
                      </div>
                      {lead.apify_rating && (
                        <div className="flex items-center gap-1 text-amber-500 bg-amber-50 px-2 py-0.5 rounded-lg border border-amber-100">
                          <Star className="w-3 h-3 fill-current" />
                          <span className="text-xs font-bold">{lead.apify_rating.toFixed(1)}</span>
                        </div>
                      )}
                    </div>

                    <div className="space-y-2 mb-4">
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <MapPin className="w-4 h-4 text-gray-400" />
                        {lead.apify_city || lead.apify_address || '—'}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-600 font-medium">
                        <span className="w-4 h-4 flex items-center justify-center text-[10px] font-bold bg-emerald-100 text-emerald-700 rounded-full">P</span>
                        {lead.phone_number}
                      </div>
                    </div>

                    <div className="flex justify-between items-center pt-3 border-t border-gray-100">
                      <div className="flex gap-2">
                        {lead.apify_website && (
                          <a
                            href={lead.apify_website}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="p-2.5 bg-gray-50 text-gray-500 rounded-xl hover:bg-emerald-50 hover:text-emerald-600 transition-colors"
                          >
                            <Globe className="w-5 h-5" />
                          </a>
                        )}
                        {lead.social_links?.instagram && (
                          <a
                            href={lead.social_links.instagram}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="p-2.5 bg-gray-50 text-pink-500 rounded-xl hover:bg-pink-50 transition-colors"
                          >
                            <Instagram className="w-5 h-5" />
                          </a>
                        )}
                      </div>
                      <div>
                        {lead.outreach_message_sent ? (
                          <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-bold uppercase tracking-wider">{t('prospecting.statusSent')}</span>
                        ) : lead.outreach_send_requested ? (
                          <span className="px-3 py-1 rounded-full bg-amber-50 text-amber-700 text-[10px] font-bold uppercase tracking-wider">{t('prospecting.statusRequested')}</span>
                        ) : (
                          <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-[10px] font-bold uppercase tracking-wider">{t('prospecting.statusPending')}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {leads.length === 0 && (
                <div className="py-20 text-center text-gray-500">
                  <Search className="w-16 h-16 mx-auto text-gray-200 mb-4" />
                  <p className="text-lg font-medium text-gray-400">{t('prospecting.noLeads')}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
