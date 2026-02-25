import { useEffect, useState, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import {
  MessageSquare,
  CalendarCheck,
  Activity,
  DollarSign,
  TrendingUp,
  Clock,
  ArrowUpRight,
  User,
  Users,
  Target,
  TrendingUp as TrendingUpIcon,
  Briefcase
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
  Bar
} from 'recharts';
import api, { BACKEND_URL } from '../api/axios';
import { useTranslation } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import PageHeader from '../components/PageHeader';

// ============================================
// INTERFACES & TYPES
// ============================================

// Interface para stats DENTAL (existente)
interface DentalAnalyticsStats {
  ia_conversations: number;
  ia_appointments: number;
  active_urgencies: number;
  total_revenue: number;
  growth_data: { date: string; ia_referrals: number; completed_appointments: number }[];
}

// Interface para stats CRM (nuevo)
interface CrmAnalyticsStats {
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

// Tipo unificado
type AnalyticsStats = DentalAnalyticsStats | CrmAnalyticsStats;

interface UrgencyRecord {
  id: string;
  patient_name: string;
  phone: string;
  urgency_level: 'CRITICAL' | 'HIGH' | 'NORMAL';
  reason: string;
  timestamp: string;
}

interface RecentLeadRecord {
  id: string;
  name: string;
  phone: string;
  status: string;
  source: string;
  niche: string;
  created_at: string;
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

const UrgencyBadge = ({ level }: { level: UrgencyRecord['urgency_level'] }) => {
  const styles = {
    CRITICAL: 'bg-red-100 text-red-700 border-red-200',
    HIGH: 'bg-orange-100 text-orange-700 border-orange-200',
    NORMAL: 'bg-green-100 text-green-700 border-green-200'
  };
  return (
    <span className={`px-2 py-1 rounded-full text-[10px] font-bold border ${styles[level]}`}>
      {level}
    </span>
  );
};

// ============================================
// MAIN VIEW
// ============================================

export default function DashboardView() {
  const { t } = useTranslation();
  const { user } = useAuth();
  
  // Determinar el nicho basado en el usuario
  const nicheType = user?.niche_type || 'dental';
  const isCrmSales = nicheType === 'crm_sales';
  
  const [stats, setStats] = useState<AnalyticsStats | null>(null);
  const [urgencies, setUrgencies] = useState<UrgencyRecord[]>([]);
  const [recentLeads, setRecentLeads] = useState<RecentLeadRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'weekly' | 'monthly'>('weekly');
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // 1. Conectar WebSocket
    socketRef.current = io(BACKEND_URL);

    // 2. Escuchar nuevos turnos/mensajes para actualización en vivo
    socketRef.current.on('NEW_APPOINTMENT', () => {
      setStats(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          ia_appointments: prev.ia_appointments + 1
        };
      });
    });

    const loadDashboardData = async (range: string) => {
      try {
        setLoading(true);
        
        if (isCrmSales) {
          // Cargar datos para CRM Sales
          const [statsRes, recentLeadsRes] = await Promise.all([
            api.get(`/admin/core/crm/stats/summary?range=${range}`),
            api.get('/admin/core/crm/leads?limit=5&offset=0')
          ]);

          setStats(statsRes.data);
          setRecentLeads(statsRes.data.recent_leads || []);
          setUrgencies([]); // No hay urgencias en CRM
          
        } else {
          // Cargar datos para Dental (existente)
          const [statsRes, urgenciesRes] = await Promise.all([
            api.get(`/admin/core/stats/summary?range=${range}`),
            api.get('/admin/core/chat/urgencies')
          ]);

          setStats(statsRes.data);
          setUrgencies(urgenciesRes.data);
          setRecentLeads([]);
        }

      } catch (error) {
        console.error('Error loading analytics:', error);
        
        if (isCrmSales) {
          setStats({
            total_leads: 0,
            total_clients: 0,
            active_leads: 0,
            converted_leads: 0,
            total_revenue: 0,
            conversion_rate: 0,
            recent_leads: []
          });
          setRecentLeads([]);
        } else {
          setStats({
            ia_conversations: 0,
            ia_appointments: 0,
            active_urgencies: 0,
            total_revenue: 0,
            growth_data: [],
          });
        }
        setUrgencies([]);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData(timeRange);

    return () => {
      if (socketRef.current) socketRef.current.disconnect();
    };
  }, [timeRange]); // Re-run effect when timeRange changes to fetch new data

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
          title={t('dashboard.analytics_title')}
          subtitle={t('dashboard.analytics_subtitle')}
          action={
            <div className="flex gap-2">
              <button
                onClick={() => setTimeRange('weekly')}
                className={`px-4 py-2 rounded-xl shadow-sm border text-sm font-medium transition-colors ${timeRange === 'weekly'
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
              >
                {t('dashboard.weekly')}
              </button>
              <button
                onClick={() => setTimeRange('monthly')}
                className={`px-4 py-2 rounded-xl shadow-sm border text-sm font-medium transition-colors ${timeRange === 'monthly'
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
              >
                {t('dashboard.monthly')}
              </button>
            </div>
          }
        />
      </header>

      {/* MAIN SCROLLABLE CONTENT WITH ISORATION */}
      <main className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6 scroll-smooth">

        {/* TOP ROW: KPI CARDS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {isCrmSales ? (
            // KPIs para CRM Sales
            <>
              <KPICard
                title="Total Leads"
                value={(stats as CrmAnalyticsStats)?.total_leads || 0}
                icon={Users}
                color="bg-blue-500"
                trend="+12%"
              />
              <KPICard
                title="Active Leads"
                value={(stats as CrmAnalyticsStats)?.active_leads || 0}
                icon={Activity}
                color="bg-emerald-500"
                trend="+5%"
              />
              <KPICard
                title="Conversion Rate"
                value={`${(stats as CrmAnalyticsStats)?.conversion_rate || 0}%`}
                icon={Target}
                color="bg-amber-500"
              />
              <KPICard
                title="Total Revenue"
                value={`$${((stats as CrmAnalyticsStats)?.total_revenue || 0).toLocaleString()}`}
                icon={DollarSign}
                color="bg-purple-500"
                trend="+8%"
              />
            </>
          ) : (
            // KPIs para Dental (existente)
            <>
              <KPICard
                title={t('dashboard.conversations')}
                value={(stats as DentalAnalyticsStats)?.ia_conversations || 0}
                icon={MessageSquare}
                color="bg-blue-500"
                trend="+12%"
              />
              <KPICard
                title={t('dashboard.ia_appointments')}
                value={(stats as DentalAnalyticsStats)?.ia_appointments || 0}
                icon={CalendarCheck}
                color="bg-emerald-500"
                trend="+5%"
              />
              <KPICard
                title={t('dashboard.urgencies')}
                value={(stats as DentalAnalyticsStats)?.active_urgencies || 0}
                icon={Activity}
                color="bg-rose-500"
              />
              <KPICard
                title={t('dashboard.revenue')}
                value={`$${(stats as DentalAnalyticsStats)?.total_revenue?.toLocaleString() || 0}`}
                icon={DollarSign}
                color="bg-amber-500"
                trend="+8%"
              />
            </>
          )}
        </div>

        {/* MIDDLE ROW: CHARTS */}
        <div className="grid grid-cols-1 gap-6">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-slate-800">
                {isCrmSales ? 'Leads Overview' : t('dashboard.chart_title')}
              </h2>
              {!isCrmSales && (
                <div className="hidden sm:flex gap-4 text-xs font-medium text-slate-500">
                  <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-blue-500"></div> {t('dashboard.referrals')}</span>
                  <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-emerald-500"></div> {t('dashboard.completed')}</span>
                </div>
              )}
            </div>
            <div className="h-[300px] min-h-[300px] w-full min-w-0">
              {isCrmSales ? (
                // Placeholder para gráfico de CRM (podemos implementar más tarde)
                <div className="h-full flex flex-col items-center justify-center text-slate-400">
                  <TrendingUpIcon className="w-16 h-16 mb-4 opacity-50" />
                  <p className="text-lg font-medium">Leads Analytics</p>
                  <p className="text-sm mt-2">Chart coming soon with lead conversion data</p>
                </div>
              ) : (
                // Gráfico existente para Dental
                <ResponsiveContainer width="100%" height="100%" minHeight={300}>
                  <AreaChart data={(stats as DentalAnalyticsStats)?.growth_data ?? []}>
                    <defs>
                      <linearGradient id="colorIA" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorDone" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.1} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Area type="monotone" dataKey="ia_referrals" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorIA)" />
                    <Area type="monotone" dataKey="completed_appointments" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#colorDone)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        {/* BOTTOM ROW: RECENT ITEMS TABLE */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col mb-4">
          <div className="p-6 border-b border-slate-50 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-slate-800">
              {isCrmSales ? 'Recent Leads' : t('dashboard.urgencies_recent')}
            </h2>
            <button className="text-blue-600 text-sm font-semibold hover:underline px-3 py-2">
              {isCrmSales ? 'See All Leads' : t('dashboard.see_all')}
            </button>
          </div>
          <div className="overflow-x-auto">
            {isCrmSales ? (
              // Tabla para Recent Leads (CRM)
              <table className="w-full text-left border-collapse min-w-[600px]">
                <thead>
                  <tr className="bg-slate-50/50">
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Lead</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Phone</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Source</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Created</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {recentLeads.map((lead) => (
                    <tr key={lead.id} className="hover:bg-slate-50/50 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors">
                            <User size={18} />
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-slate-800">{lead.name}</p>
                            <p className="text-[11px] text-slate-500">{lead.niche || 'General'}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600 font-mono">{lead.phone}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          lead.status === 'new' ? 'bg-blue-100 text-blue-700' :
                          lead.status === 'contacted' ? 'bg-yellow-100 text-yellow-700' :
                          lead.status === 'qualified' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {lead.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">{lead.source}</td>
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
                  {recentLeads.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-slate-400">
                        No recent leads found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            ) : (
              // Tabla existente para Urgencies (Dental)
              <table className="w-full text-left border-collapse min-w-[600px]">
                <thead>
                  <tr className="bg-slate-50/50">
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">{t('dashboard.patient')}</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">{t('dashboard.reason')}</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">{t('dashboard.severity')}</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">{t('dashboard.time')}</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {urgencies.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/50 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors">
                            <User size={18} />
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-slate-800">{u.patient_name}</p>
                            <p className="text-[11px] text-slate-500 font-mono tracking-tighter">{u.phone}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600 font-medium">{u.reason}</td>
                      <td className="px-6 py-4">
                        <UrgencyBadge level={u.urgency_level} />
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-500">
                        <div className="flex items-center gap-1.5">
                          <Clock size={14} className="text-slate-400" /> {u.timestamp}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button className="p-2 hover:bg-white rounded-lg border border-transparent hover:border-slate-200 text-slate-400 hover:text-blue-600 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center">
                          <ArrowUpRight size={20} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

      </main>
    </div>
  );
}
