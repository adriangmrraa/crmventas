import { useEffect, useState } from 'react';
import {
  Users,
  UserCheck,
  Target,
  DollarSign,
  TrendingUp,
  Clock,
  ArrowUpRight,
  Phone,
  Building,
  MapPin,
  Filter
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import api from '../api/axios';
import PageHeader from '../components/PageHeader';

// ============================================
// INTERFACES & TYPES
// ============================================

interface CrmDashboardStats {
  total_leads: number;
  total_clients: number;
  active_leads: number;
  converted_leads: number;
  total_revenue: number;
  conversion_rate: number;
  revenue_leads_trend: Array<{
    month: string;
    revenue: number;
    leads: number;
  }>;
  status_distribution: Array<{
    status: string;
    count: number;
    color: string;
  }>;
  recent_leads: Array<{
    id: string;
    name: string;
    phone: string;
    status: string;
    source: string;
    niche: string;
    created_at: string;
  }>;
}

// interfaces for dashboard data mapping are managed in CrmDashboardStats

// ============================================
// COMPONENTS
// ============================================

const KPICard = ({ title, value, icon: Icon, color, trend }: any) => (
  <div className="bg-white/[0.03] backdrop-blur-md border border-white/[0.06] rounded-2xl p-6 hover:shadow-lg hover:shadow-black/20 transition-all duration-300 group">
    <div className="flex justify-between items-start mb-4">
      <div className={`p-3 rounded-xl ${color} bg-opacity-10 group-hover:scale-110 transition-transform`}>
        <Icon className={`w-6 h-6 ${color.replace('bg-', 'text-')}`} />
      </div>
      {trend && (
        <span className="flex items-center gap-1 text-xs font-medium text-green-400 bg-green-500/10 px-2 py-1 rounded-full">
          <TrendingUp size={12} /> {trend}
        </span>
      )}
    </div>
    <p className="text-white/40 text-sm font-medium">{title}</p>
    <h3 className="text-2xl font-bold text-white mt-1">{value}</h3>
  </div>
);

import { LeadStatusBadge } from '../components/leads/LeadStatusBadge';
import { BulkStatusUpdate } from '../components/leads/BulkStatusUpdate';
import { LeadHistoryTimeline } from '../components/leads/LeadHistoryTimeline';

const StatusBadge = ({ status }: { status: string }) => {
  const styles: Record<string, string> = {
    'new': 'bg-violet-500/100/10 text-violet-400 border-violet-500/20',
    'contacted': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    'interested': 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    'negotiation': 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    'closed_won': 'bg-green-500/10 text-green-400 border-green-500/20',
    'closed_lost': 'bg-red-500/10 text-red-400 border-red-500/20',
    'default': 'bg-white/[0.04] text-white/70 border-white/[0.06]'
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-bold border ${styles[status] || styles.default}`}>
      {status.replace('_', ' ').toUpperCase()}
    </span>
  );
};

// ============================================
// MAIN VIEW
// ============================================

export default function CrmDashboardView() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<CrmDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'weekly' | 'monthly'>('weekly');
  const [selectedLeads, setSelectedLeads] = useState<string[]>([]);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [historyModalLead, setHistoryModalLead] = useState<{ id: string, name: string } | null>(null);

  const isAdvancedLeadStatusEnabled = import.meta.env.VITE_ENABLE_ADVANCED_LEAD_STATUS === 'true';

  const toggleLeadSelection = (id: string) => {
    setSelectedLeads(prev =>
      prev.includes(id) ? prev.filter(tId => tId !== id) : [...prev, id]
    );
  };

  const toggleAllSelection = () => {
    if (selectedLeads.length === stats?.recent_leads?.length) {
      setSelectedLeads([]);
    } else {
      setSelectedLeads(stats?.recent_leads?.map(l => l.id) || []);
    }
  };

  useEffect(() => {
    const loadDashboardData = async (range: string) => {
      try {
        setLoading(true);
        const statsRes = await api.get('/admin/core/crm/stats/summary', { params: { range } });
        setStats(statsRes.data);
      } catch (error) {
        console.error('Error loading CRM dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData(timeRange);
  }, [timeRange]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#06060e]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-500"></div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#06060e] overflow-hidden">
      {/* HEADER SECTION */}
      <header className="p-4 sm:p-6 shrink-0 bg-white/[0.03] backdrop-blur-sm border-b border-white/[0.04]">
        <PageHeader
          title="CRM Sales Dashboard"
          subtitle="Real-time sales pipeline monitoring and analytics"
          action={
            <div className="flex gap-2">
              <button
                onClick={() => setTimeRange('weekly')}
                className={`px-4 py-2 rounded-xl border text-sm font-medium transition-colors ${timeRange === 'weekly'
                  ? 'bg-white/[0.03] text-[#0a0e1a] border-white'
                  : 'bg-white/[0.03] text-white/50 border-white/[0.06] hover:bg-white/[0.04]'
                  }`}
              >
                Weekly
              </button>
              <button
                onClick={() => setTimeRange('monthly')}
                className={`px-4 py-2 rounded-xl border text-sm font-medium transition-colors ${timeRange === 'monthly'
                  ? 'bg-white/[0.03] text-[#0a0e1a] border-white'
                  : 'bg-white/[0.03] text-white/50 border-white/[0.06] hover:bg-white/[0.04]'
                  }`}
              >
                Monthly
              </button>
            </div>
          }
        />
      </header>

      {/* MAIN SCROLLABLE CONTENT */}
      <main className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6 scroll-smooth">

        {/* TOP ROW: KPI CARDS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Total Leads"
            value={stats?.total_leads || 0}
            icon={Users}
            color="bg-violet-500/100"
            trend="+12%"
          />
          <KPICard
            title="Active Leads"
            value={stats?.active_leads || 0}
            icon={UserCheck}
            color="bg-emerald-500"
            trend="+8%"
          />
          <KPICard
            title="Conversion Rate"
            value={`${stats?.conversion_rate || 0}%`}
            icon={Target}
            color="bg-amber-500"
            trend="+2.5%"
          />
          <KPICard
            title="Total Revenue"
            value={`$${(stats?.total_revenue || 0).toLocaleString()}`}
            icon={DollarSign}
            color="bg-purple-500"
            trend="+15%"
          />
        </div>

        {/* MIDDLE ROW: CHARTS */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Lead Status Distribution */}
          <div className="bg-white/[0.03] rounded-2xl border border-white/[0.06] p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-white">Lead Status Distribution</h2>
              <Filter size={18} className="text-white/30" />
            </div>
            <div className="h-[300px] min-h-[300px] w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                <PieChart>
                  <Pie
                    data={stats?.status_distribution || []}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ status, percent }: any) => `${status}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {(stats?.status_distribution || []).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: any, name) => [`${value} leads`, name]}
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Revenue Trend */}
          <div className="bg-white/[0.03] rounded-2xl border border-white/[0.06] p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-white">Revenue & Leads Trend</h2>
              <div className="hidden sm:flex gap-4 text-xs font-medium text-white/40">
                <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-violet-500/100"></div> Revenue</span>
                <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-emerald-500"></div> Leads</span>
              </div>
            </div>
            <div className="h-[300px] min-h-[300px] w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                <BarChart data={stats?.revenue_leads_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value: any, name) => {
                      if (name === 'revenue' && value != null) return [`$${value.toLocaleString()}`, 'Revenue'];
                      return [value, 'Leads'];
                    }}
                  />
                  <Bar dataKey="revenue" fill="#8F3DFF" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="leads" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* BOTTOM ROW: RECENT LEADS */}
        <div className="bg-white/[0.03] rounded-2xl border border-white/[0.06] overflow-hidden flex flex-col mb-4">
          <div className="p-6 border-b border-white/[0.04] flex justify-between items-center bg-white/[0.02]">
            <div className="flex items-center gap-4">
              <h2 className="text-lg font-semibold text-white">Recent Leads</h2>
              {isAdvancedLeadStatusEnabled && selectedLeads.length > 0 && (
                <div className="animate-in fade-in slide-in-from-left-4 flex items-center gap-3">
                  <span className="text-sm font-medium text-violet-400 bg-violet-500/10 px-3 py-1 rounded-full">
                    {selectedLeads.length} seleccionados
                  </span>
                  <button
                    onClick={() => setShowBulkModal(true)}
                    className="text-white text-sm font-semibold hover:bg-violet-700 bg-violet-600 px-4 py-1.5 rounded-xl transition-all flex items-center gap-2"
                  >
                    Actualizar Estado Múltiple
                  </button>
                </div>
              )}
            </div>

            <button
              onClick={() => navigate('/crm/leads')}
              className="text-violet-400 text-sm font-semibold hover:underline px-3 py-2"
            >
              See All Leads
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[600px]">
              <thead>
                <tr className="bg-white/[0.02]/50">
                  {isAdvancedLeadStatusEnabled && (
                    <th className="px-6 py-4 w-12 text-center text-xs font-bold text-white/40 uppercase tracking-wider">
                      <input
                        type="checkbox"
                        className="rounded border-white/[0.06] text-violet-400 focus:ring-violet-500 cursor-pointer"
                        checked={selectedLeads.length > 0 && selectedLeads.length === (stats?.recent_leads ? stats.recent_leads.length : 0)}
                        onChange={toggleAllSelection}
                      />
                    </th>
                  )}
                  <th className="px-6 py-4 text-xs font-bold text-white/40 uppercase tracking-wider">Lead</th>
                  <th className="px-6 py-4 text-xs font-bold text-white/40 uppercase tracking-wider">Contact</th>
                  <th className="px-6 py-4 text-xs font-bold text-white/40 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-xs font-bold text-white/40 uppercase tracking-wider">Source</th>
                  <th className="px-6 py-4 text-xs font-bold text-white/40 uppercase tracking-wider">Niche</th>
                  <th className="px-6 py-4 text-xs font-bold text-white/40 uppercase tracking-wider">Created</th>
                  <th className="px-6 py-4 text-xs font-bold text-white/40 uppercase tracking-wider"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {(stats?.recent_leads || []).map((lead) => (
                  <tr key={lead.id} className={`hover:bg-white/[0.04] transition-colors group ${selectedLeads.includes(lead.id) && isAdvancedLeadStatusEnabled ? 'bg-violet-500/100/10' : ''}`}>
                    {isAdvancedLeadStatusEnabled && (
                      <td className="px-6 py-4 text-center">
                        <input
                          type="checkbox"
                          className="rounded border-white/[0.06] text-violet-400 focus:ring-violet-500 cursor-pointer"
                          checked={selectedLeads.includes(lead.id)}
                          onChange={() => toggleLeadSelection(lead.id)}
                        />
                      </td>
                    )}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-white/[0.04] flex items-center justify-center text-white/40 group-hover:bg-violet-500/10 group-hover:text-violet-400 transition-colors">
                          <Users size={18} />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-white">{lead.name}</p>
                          <p className="text-[11px] text-white/40">ID: {lead.id.substring(0, 8)}...</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm text-white/50">
                          <Phone size={14} className="text-white/30" />
                          {lead.phone}
                        </div>
                        {lead.source === 'website' && (
                          <div className="flex items-center gap-2 text-xs text-white/40">
                            <Building size={12} className="text-white/30" />
                            Website Lead
                          </div>
                        )}
                        {lead.source === 'meta_ads' && (
                          <div className="flex items-center gap-2 text-xs text-white/40">
                            <TrendingUp size={12} className="text-white/30" />
                            Meta Ads
                          </div>
                        )}
                        {lead.source === 'referral' && (
                          <div className="flex items-center gap-2 text-xs text-white/40">
                            <UserCheck size={12} className="text-white/30" />
                            Referral
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {isAdvancedLeadStatusEnabled ? (
                        <LeadStatusBadge statusCode={lead.status} />
                      ) : (
                        <StatusBadge status={lead.status} />
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-white/50">
                      <span className="capitalize">{lead.source}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-white/50">
                      <div className="flex items-center gap-2">
                        <MapPin size={14} className="text-white/30" />
                        {lead.niche}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-white/40">
                      <div className="flex items-center gap-1.5">
                        <Clock size={14} className="text-white/30" />
                        {new Date(lead.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {isAdvancedLeadStatusEnabled && (
                          <button
                            title="Ver Historial de Estados"
                            onClick={() => setHistoryModalLead({ id: lead.id, name: lead.name })}
                            className="p-2 hover:bg-white/[0.06] rounded-lg border border-transparent hover:border-white/[0.06] text-white/30 hover:text-violet-400 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center"
                          >
                            <Clock size={18} />
                          </button>
                        )}
                        <button
                          title="Ver Detalles del Lead"
                          onClick={() => navigate(`/crm/leads/${lead.id}`)}
                          className="p-2 hover:bg-white/[0.06] rounded-lg border border-transparent hover:border-white/[0.06] text-white/30 hover:text-violet-400 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center"
                        >
                          <ArrowUpRight size={20} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {(stats?.recent_leads || []).length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-white/30">
                      <div className="flex flex-col items-center gap-2">
                        <Users size={48} className="text-white/30" />
                        <p className="text-lg font-medium">No recent leads found</p>
                        <p className="text-sm">Start prospecting to see leads here</p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Bulk Status Update Modal */}
      {isAdvancedLeadStatusEnabled && showBulkModal && (
        <BulkStatusUpdate
          selectedLeadIds={selectedLeads}
          onCancel={() => setShowBulkModal(false)}
          onSuccess={() => {
            setShowBulkModal(false);
            setSelectedLeads([]);
            // Force local manual reload since the hook query invalidation hits 'leads' rather than dashboard stats
            window.location.reload();
          }}
        />
      )}

      {/* Lead History Timeline Modal */}
      {isAdvancedLeadStatusEnabled && historyModalLead && (
        <LeadHistoryTimeline
          leadId={historyModalLead.id}
          leadName={historyModalLead.name}
          onClose={() => setHistoryModalLead(null)}
        />
      )}
    </div>
  );
}