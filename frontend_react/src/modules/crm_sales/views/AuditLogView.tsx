/**
 * AuditLogView — DEV-40: Log de auditoría completo por lead y por vendedor.
 * Tabs: General | Por Lead | Por Vendedor. Export CSV.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ClipboardList, Download, Search, Filter, Users, FileText,
  ArrowRightLeft, UserPlus, MessageSquare, Phone, CheckCircle2,
  Zap, Activity, X
} from 'lucide-react';
import api from '../../../api/axios';

type Tab = 'general' | 'by_lead' | 'by_seller' | 'sistema';

const EVENT_LABELS: Record<string, string> = {
  lead_created: 'Creó lead',
  lead_status_changed: 'Cambió estado',
  lead_assigned: 'Asignó lead',
  note_added: 'Dejó nota',
  call_logged: 'Registró llamada',
  chat_message_sent: 'Envió mensaje',
  task_completed: 'Completó tarea',
  lead_qualified: 'Calificó lead',
  lead_handoff: 'Derivó a closer',
  user_login: 'Inició sesión',
};

const AuditLogView: React.FC = () => {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('general');
  const [loading, setLoading] = useState(false);

  // General tab
  const [feedItems, setFeedItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [filterSeller, setFilterSeller] = useState('');
  const [filterType, setFilterType] = useState('');
  const [sellers, setSellers] = useState<any[]>([]);

  // By Lead tab
  const [leadSearch, setLeadSearch] = useState('');
  const [leadResults, setLeadResults] = useState<any[]>([]);
  const [selectedLead, setSelectedLead] = useState<any>(null);
  const [leadTimeline, setLeadTimeline] = useState<any[]>([]);

  // Sistema tab
  const [systemLogs, setSystemLogs] = useState<any[]>([]);
  const [systemTotal, setSystemTotal] = useState(0);
  const [systemFilterType, setSystemFilterType] = useState('');
  const [systemFilterSeverity, setSystemFilterSeverity] = useState('');

  // By Seller tab
  const [selectedSeller, setSelectedSeller] = useState('');
  const [sellerTimeline, setSellerTimeline] = useState<any[]>([]);
  const [sellerInfo, setSellerInfo] = useState<any>(null);

  // Load sellers list
  useEffect(() => {
    api.get('/admin/core/team-activity/seller-status').then(r => setSellers(r.data.sellers || [])).catch(() => {});
  }, []);

  // General feed
  const loadFeed = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { limit: 100 };
      if (filterSeller) params.seller_id = filterSeller;
      if (filterType) params.event_type = filterType;
      const res = await api.get('/admin/core/team-activity/feed', { params });
      setFeedItems(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch { /* */ }
    setLoading(false);
  }, [filterSeller, filterType]);

  useEffect(() => {
    if (tab === 'general') loadFeed();
  }, [tab, loadFeed]);

  // Search leads
  const searchLeads = async () => {
    if (!leadSearch.trim()) return;
    try {
      const res = await api.get('/admin/core/crm/leads', { params: { search: leadSearch, limit: 10 } });
      setLeadResults(res.data.leads || res.data || []);
    } catch { /* */ }
  };

  // Load lead timeline
  const loadLeadTimeline = async (leadId: string) => {
    setLoading(true);
    try {
      const res = await api.get(`/admin/core/team-activity/audit/by-lead/${leadId}`);
      setLeadTimeline(res.data.items || []);
      setSelectedLead(res.data.lead);
    } catch { /* */ }
    setLoading(false);
  };

  // Load seller timeline
  const loadSellerTimeline = async (userId: string) => {
    setLoading(true);
    try {
      const res = await api.get(`/admin/core/team-activity/audit/by-seller/${userId}`);
      setSellerTimeline(res.data.items || []);
      setSellerInfo(res.data.seller);
    } catch { /* */ }
    setLoading(false);
  };

  // System logs
  const loadSystemLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { limit: 100 };
      if (systemFilterType) params.event_type = systemFilterType;
      if (systemFilterSeverity) params.severity = systemFilterSeverity;
      const res = await api.get('/admin/core/audit/logs', { params });
      setSystemLogs(res.data.items || res.data.logs || []);
      setSystemTotal(res.data.total || 0);
    } catch { /* */ }
    setLoading(false);
  }, [systemFilterType, systemFilterSeverity]);

  useEffect(() => {
    if (tab === 'sistema') loadSystemLogs();
  }, [tab, loadSystemLogs]);

  // Export CSV
  const handleExport = async () => {
    try {
      const params: any = {};
      if (filterSeller) params.seller_id = filterSeller;
      if (filterType) params.event_type = filterType;
      const res = await api.get('/admin/core/team-activity/audit/export', { params, responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'audit_log.csv';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch { /* */ }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'general', label: 'General' },
    { key: 'by_lead', label: 'Por Lead' },
    { key: 'by_seller', label: 'Por Vendedor' },
    { key: 'sistema', label: 'Sistema' },
  ];

  const SEVERITY_BADGE: Record<string, string> = {
    info: 'bg-blue-500/20 text-blue-300',
    warning: 'bg-yellow-500/20 text-yellow-300',
    error: 'bg-red-500/20 text-red-300',
    critical: 'bg-red-700/30 text-red-200',
  };

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-4 sm:px-6 py-4 border-b border-white/[0.06]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-white/[0.06]">
              <ClipboardList size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">Log de Auditoría</h1>
              <p className="text-xs text-white/40">{total} registros</p>
            </div>
          </div>
          {tab === 'general' && (
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-3 py-1.5 text-xs bg-white/[0.06] hover:bg-white/[0.1] text-white/70 hover:text-white rounded-lg transition-colors"
            >
              <Download size={14} /> Exportar CSV
            </button>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-1.5 text-xs rounded-lg transition-colors ${
                tab === t.key
                  ? 'bg-white/10 text-white font-medium'
                  : 'text-white/40 hover:text-white/70 hover:bg-white/[0.04]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* General Tab */}
        {tab === 'general' && (
          <div>
            {/* Filters */}
            <div className="px-4 py-3 border-b border-white/[0.04] flex flex-wrap gap-3">
              <select
                value={filterSeller}
                onChange={e => setFilterSeller(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-xs"
              >
                <option value="">Todos los vendedores</option>
                {sellers.map((s: any) => (
                  <option key={s.user_id} value={s.user_id}>{s.name}</option>
                ))}
              </select>
              <select
                value={filterType}
                onChange={e => setFilterType(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-xs"
              >
                <option value="">Todos los tipos</option>
                {Object.entries(EVENT_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>

            {/* Feed */}
            {feedItems.map((item: any) => (
              <button
                key={item.id}
                onClick={() => item.entity_type === 'lead' && navigate(`/crm/leads/${item.entity_id}`)}
                className="w-full text-left px-4 py-3 hover:bg-white/[0.04] border-b border-white/[0.04] flex items-center gap-3"
              >
                <div className="flex-1">
                  <p className="text-sm text-white/90">
                    <span className="font-medium text-white">{item.actor?.name}</span>{' '}
                    <span className="text-white/50">{EVENT_LABELS[item.event_type] || item.event_type}</span>{' '}
                    {item.entity_name && <span className="text-white/70">{item.entity_name}</span>}
                  </p>
                </div>
                <span className="text-xs text-white/30">{item.time_ago}</span>
              </button>
            ))}
            {loading && <p className="p-4 text-center text-white/30 text-xs">Cargando...</p>}
          </div>
        )}

        {/* By Lead Tab */}
        {tab === 'by_lead' && (
          <div className="p-4">
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={leadSearch}
                onChange={e => setLeadSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && searchLeads()}
                placeholder="Buscar lead por nombre o teléfono..."
                className="flex-1 px-3 py-2 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm placeholder-white/30"
              />
              <button onClick={searchLeads} className="p-2 rounded-lg bg-white/[0.06] text-white/60 hover:text-white">
                <Search size={16} />
              </button>
            </div>

            {leadResults.length > 0 && !selectedLead && (
              <div className="space-y-1 mb-4">
                {leadResults.map((l: any) => (
                  <button
                    key={l.id}
                    onClick={() => loadLeadTimeline(l.id)}
                    className="w-full text-left px-3 py-2 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] text-sm text-white/80"
                  >
                    {l.first_name} {l.last_name} — {l.phone_number}
                  </button>
                ))}
              </div>
            )}

            {selectedLead && (
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <h3 className="text-sm font-medium text-white">{selectedLead.name}</h3>
                  <span className="text-xs text-white/40">({selectedLead.status})</span>
                  <button onClick={() => { setSelectedLead(null); setLeadTimeline([]); }} className="ml-auto text-white/40 hover:text-white">
                    <X size={14} />
                  </button>
                </div>
                {/* Timeline */}
                <div className="border-l-2 border-white/[0.08] ml-2 space-y-0">
                  {leadTimeline.map((item: any) => (
                    <div key={item.id} className="pl-4 py-2 relative">
                      <div className="absolute -left-[5px] top-3 w-2 h-2 rounded-full bg-white/20" />
                      <p className="text-sm text-white/80">
                        <span className="font-medium">{item.actor?.name}</span>{' '}
                        <span className="text-white/50">{EVENT_LABELS[item.event_type] || item.event_type}</span>
                      </p>
                      <p className="text-xs text-white/30">{item.time_ago}</p>
                    </div>
                  ))}
                  {leadTimeline.length === 0 && <p className="pl-4 text-xs text-white/30">Sin actividad registrada</p>}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Sistema Tab */}
        {tab === 'sistema' && (
          <div>
            {/* Filters */}
            <div className="px-4 py-3 border-b border-white/[0.04] flex flex-wrap gap-3">
              <input
                type="text"
                value={systemFilterType}
                onChange={e => setSystemFilterType(e.target.value)}
                placeholder="Filtrar por tipo de evento..."
                className="px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-xs placeholder-white/30 w-52"
              />
              <select
                value={systemFilterSeverity}
                onChange={e => setSystemFilterSeverity(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-xs"
              >
                <option value="">Toda severidad</option>
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
                <option value="critical">Critical</option>
              </select>
              <span className="ml-auto text-xs text-white/30 self-center">{systemTotal} eventos</span>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-white/[0.06] text-white/40 text-left">
                    <th className="px-4 py-2 font-medium">Tipo</th>
                    <th className="px-4 py-2 font-medium">Severidad</th>
                    <th className="px-4 py-2 font-medium">Mensaje</th>
                    <th className="px-4 py-2 font-medium whitespace-nowrap">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {systemLogs.map((log: any) => (
                    <tr key={log.id} className="border-b border-white/[0.04] hover:bg-white/[0.03]">
                      <td className="px-4 py-2.5 text-white/70 font-mono">{log.event_type}</td>
                      <td className="px-4 py-2.5">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${SEVERITY_BADGE[log.severity] || 'bg-white/10 text-white/50'}`}>
                          {log.severity || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-white/80 max-w-xs truncate">{log.message || log.description || '—'}</td>
                      <td className="px-4 py-2.5 text-white/30 whitespace-nowrap">{log.time_ago || log.created_at || '—'}</td>
                    </tr>
                  ))}
                  {!loading && systemLogs.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-6 text-center text-white/30">Sin eventos de sistema</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {loading && <p className="p-4 text-center text-white/30 text-xs">Cargando...</p>}
          </div>
        )}

        {/* By Seller Tab */}
        {tab === 'by_seller' && (
          <div className="p-4">
            <select
              value={selectedSeller}
              onChange={e => {
                setSelectedSeller(e.target.value);
                if (e.target.value) loadSellerTimeline(e.target.value);
              }}
              className="w-full px-3 py-2 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm mb-4"
            >
              <option value="">Seleccionar vendedor...</option>
              {sellers.map((s: any) => (
                <option key={s.user_id} value={s.user_id}>{s.name} ({s.role})</option>
              ))}
            </select>

            {sellerInfo && (
              <div>
                <h3 className="text-sm font-medium text-white mb-3">{sellerInfo.name} <span className="text-white/40">({sellerInfo.role})</span></h3>
                <div className="border-l-2 border-white/[0.08] ml-2 space-y-0">
                  {sellerTimeline.map((item: any) => (
                    <button
                      key={item.id}
                      onClick={() => item.entity_type === 'lead' && navigate(`/crm/leads/${item.entity_id}`)}
                      className="w-full text-left pl-4 py-2 relative hover:bg-white/[0.02]"
                    >
                      <div className="absolute -left-[5px] top-3 w-2 h-2 rounded-full bg-white/20" />
                      <p className="text-sm text-white/80">
                        {EVENT_LABELS[item.event_type] || item.event_type}{' '}
                        {item.entity_name && <span className="text-white/60">— {item.entity_name}</span>}
                      </p>
                      <p className="text-xs text-white/30">{item.time_ago}</p>
                    </button>
                  ))}
                  {sellerTimeline.length === 0 && <p className="pl-4 text-xs text-white/30">Sin actividad registrada</p>}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditLogView;
