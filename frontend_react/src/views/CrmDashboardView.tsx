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
  Mail,
  Building,
  MapPin,
  Filter
} from 'lucide-react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import api from '../api/axios';
import { useTranslation } from '../context/LanguageContext';
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

interface LeadStatusDistribution {
  status: string;
  count: number;
  color: string;
}

interface RevenueTrend {
  month: string;
  revenue: number;
  leads: number;
}

// ============================================
// COMPONENTS
// ============================================

const KPICard = ({ title, value, icon: Icon, color, trend }: any) => (
  <div className="bg-white/80 backdrop-blur-md border border-white/20 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 group">
    <div className="flex justify-between items-start mb-4">
      <div className={`p-3 rounded-xl ${color} bg-opacity-10 group-hover:scale-110 transition-transform`}>
        <Icon className={`w-6 h-6 ${color.replace('bg-', 'text-')}`} />
      </div>
      {trend && (
        <span className="flex items-center gap-1 text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded-full">
          <TrendingUp size={12} /> {trend}
        </span>
      )}
    </div>
    <p className="text-gray-500 text-sm font-medium">{title}</p>
    <h3 className="text-2xl font-bold text-gray-800 mt-1">{value}</h3>
  </div>
);

const StatusBadge = ({ status }: { status: string }) => {
  const styles: Record<string, string> = {
    'new': 'bg-blue-100 text-blue-700 border-blue-200',
    'contacted': 'bg-yellow-100 text-yellow-700 border-yellow-200',
    'interested': 'bg-purple-100 text-purple-700 border-purple-200',
    'negotiation': 'bg-orange-100 text-orange-700 border-orange-200',
    'closed_won': 'bg-green-100 text-green-700 border-green-200',
    'closed_lost': 'bg-red-100 text-red-700 border-red-200',
    'default': 'bg-gray-100 text-gray-700 border-gray-200'
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
  const { t } = useTranslation();
  const [stats, setStats] = useState<CrmDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'weekly' | 'monthly'>('weekly');
  
  // Datos de ejemplo para gráficos (en producción vendrían del backend)
  const [statusDistribution, setStatusDistribution] = useState<LeadStatusDistribution[]>([
    { status: 'new', count: 45, color: '#3b82f6' },
    { status: 'contacted', count: 28, color: '#f59e0b' },
    { status: 'interested', count: 18, color: '#8b5cf6' },
    { status: 'negotiation', count: 12, color: '#f97316' },
    { status: 'closed_won', count: 8, color: '#10b981' },
    { status: 'closed_lost', count: 4, color: '#ef4444' }
  ]);
  
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrend[]>([
    { month: 'Jan', revenue: 12500, leads: 45 },
    { month: 'Feb', revenue: 18900, leads: 52 },
    { month: 'Mar', revenue: 21500, leads: 61 },
    { month: 'Apr', revenue: 17800, leads: 48 },
    { month: 'May', revenue: 23400, leads: 67 },
    { month: 'Jun', revenue: 28700, leads: 72 }
  ]);

  useEffect(() => {
    const loadDashboardData = async (range: string) => {
      try {
        setLoading(true);
        
        // Cargar estadísticas del CRM
        const statsRes = await api.get(`/admin/core/crm/stats/summary?range=${range}`);
        
        setStats(statsRes.data);
        
        // En una implementación real, también cargaríamos:
        // - Distribución de status desde endpoint específico
        // - Tendencias de revenue desde endpoint específico
        
      } catch (error) {
        console.error('Error loading CRM dashboard data:', error);
        
        // Datos de ejemplo para desarrollo
        setStats({
          total_leads: 156,
          total_clients: 42,
          active_leads: 87,
          converted_leads: 24,
          total_revenue: 28700,
          conversion_rate: 15.4,
          recent_leads: [
            {
              id: '1',
              name: 'Juan Pérez',
              phone: '+5491134567890',
              status: 'new',
              source: 'website',
              niche: 'Consultoría',
              created_at: new Date().toISOString()
            },
            {
              id: '2',
              name: 'María González',
              phone: '+5491145678901',
              status: 'contacted',
              source: 'referral',
              niche: 'Software',
              created_at: new Date(Date.now() - 86400000).toISOString()
            },
            {
              id: '3',
              name: 'Carlos Rodríguez',
              phone: '+5491156789012',
              status: 'interested',
              source: 'meta_ads',
              niche: 'Consultoría',
              created_at: new Date(Date.now() - 172800000).toISOString()
            },
            {
              id: '4',
              name: 'Ana Martínez',
              phone: '+5491167890123',
              status: 'negotiation',
              source: 'website',
              niche: 'Servicios',
              created_at: new Date(Date.now() - 259200000).toISOString()
            },
            {
              id: '5',
              name: 'Luis Fernández',
              phone: '+5491178901234',
              status: 'closed_won',
              source: 'referral',
              niche: 'Software',
              created_at: new Date(Date.now() - 345600000).toISOString()
            }
          ]
        });
        
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData(timeRange);
  }, [timeRange]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">
      {/* HEADER SECTION */}
      <header className="p-4 sm:p-6 shrink-0 bg-white/50 backdrop-blur-sm border-b border-slate-100">
        <PageHeader
          title="CRM Sales Dashboard"
          subtitle="Real-time sales pipeline monitoring and analytics"
          action={
            <div className="flex gap-2">
              <button
                onClick={() => setTimeRange('weekly')}
                className={`px-4 py-2 rounded-xl shadow-sm border text-sm font-medium transition-colors ${timeRange === 'weekly'
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
              >
                Weekly
              </button>
              <button
                onClick={() => setTimeRange('monthly')}
                className={`px-4 py-2 rounded-xl shadow-sm border text-sm font-medium transition-colors ${timeRange === 'monthly'
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
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
            color="bg-blue-500"
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
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-slate-800">Lead Status Distribution</h2>
              <Filter size={18} className="text-slate-400" />
            </div>
            <div className="h-[300px] min-h-[300px] w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                <PieChart>
                  <Pie
                    data={statusDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ status, percent }) => `${status}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {statusDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value, name) => [`${value} leads`, name]}
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Revenue Trend */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-slate-800">Revenue & Leads Trend</h2>
              <div className="hidden sm:flex gap-4 text-xs font-medium text-slate-500">
                <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-blue-500"></div> Revenue</span>
                <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-emerald-500"></div> Leads</span>
              </div>
            </div>
            <div className="h-[300px] min-h-[300px] w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                <BarChart data={revenueTrend}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value, name) => {
                      if (name === 'revenue') return [`$${value.toLocaleString()}`, 'Revenue'];
                      return [value, 'Leads'];
                    }}
                  />
                  <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="leads" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* BOTTOM ROW: RECENT LEADS */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col mb-4">
          <div className="p-6 border-b border-slate-50 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-slate-800">Recent Leads</h2>
            <button className="text-blue-600 text-sm font-semibold hover:underline px-3 py-2">
              See All Leads
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[600px]">
              <thead>
                <tr className="bg-slate-50/50">
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Lead</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Contact</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Source</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Niche</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Created</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {(stats?.recent_leads || []).map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-50/50 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors">
                          <Users size={18} />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-800">{lead.name}</p>
                          <p className="text-[11px] text-slate-500">ID: {lead.id.substring(0, 8)}...</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm text-slate-600">
                          <Phone size={14} className="text-slate-400" />
                          {lead.phone}
                        </div>
                        {lead.source === 'website' && (
                          <div className="flex items-center gap-2 text-xs text-slate-500">
                            <Building size={12} className="text-slate-400" />
                            Website Lead
                          </div>
                        )}
                        {lead.source === 'meta_ads' && (
                          <div className="flex items-center gap-2 text-xs text-slate-500">
                            <TrendingUp size={12} className="text-slate-400" />
                            Meta Ads
                          </div>
                        )}
                        {lead.source === 'referral' && (
                          <div className="flex items-center gap-2 text-xs text-slate-500">
                            <UserCheck size={12} className="text-slate-400" />
                            Referral
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={lead.status} />
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      <span className="capitalize">{lead.source}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      <div className="flex items-center gap-2">
                        <MapPin size={14} className="text-slate-400" />
                        {lead.niche}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-500">
                      <div className="flex items-center gap-1.5">
                        <Clock size={14} className="text-slate-400" />
                        {new Date(lead.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-2 hover:bg-white rounded-lg border border-transparent hover:border-slate-200 text-slate-400 hover:text-blue-600 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center">
                        <ArrowUpRight size={20} />
                      </button>
                    </td>
                  </tr>
                ))}
                {(stats?.recent_leads || []).length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-slate-400">
                      <div className="flex flex-col items-center gap-2">
                        <Users size={48} className="text-slate-300" />
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
    </div>
  );
}