/**
 * SellerPerformanceView — DEV-41: Reportes de performance individual por vendedor.
 * KPIs, gráfica diaria, breakdown por tipo, comparativa vs equipo.
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, TrendingUp, Users, Clock, Target, BarChart3, Activity } from 'lucide-react';
import api from '../../../api/axios';

interface KPIs {
  leads_assigned: number;
  leads_converted: number;
  conversion_rate: number;
  avg_first_response_seconds: number | null;
  total_actions: number;
  total_notes: number;
  total_calls: number;
  total_messages: number;
  active_leads_now: number;
}

const SellerPerformanceView: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [period, setPeriod] = useState<'week' | 'month' | '3months'>('month');

  useEffect(() => {
    if (!userId) return;
    const load = async () => {
      setLoading(true);
      try {
        const now = new Date();
        let dateFrom = new Date();
        if (period === 'week') dateFrom.setDate(now.getDate() - 7);
        else if (period === 'month') dateFrom.setDate(now.getDate() - 30);
        else dateFrom.setDate(now.getDate() - 90);

        const res = await api.get(`/admin/core/team-activity/seller/${userId}/performance`, {
          params: { date_from: dateFrom.toISOString(), date_to: now.toISOString() },
        });
        setData(res.data);
      } catch { /* */ }
      setLoading(false);
    };
    load();
  }, [userId, period]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/40" />
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div className="flex items-center justify-center h-full text-white/40">
        Vendedor no encontrado
      </div>
    );
  }

  const kpis: KPIs = data.kpis;
  const teamAvg = data.team_avg || {};
  const breakdown = data.event_type_breakdown || {};
  const daily = data.daily_breakdown || [];

  const formatTime = (s: number | null) => {
    if (!s) return '-';
    if (s < 60) return `${s}s`;
    return `${Math.round(s / 60)}min`;
  };

  const maxDailyActions = Math.max(...daily.map((d: any) => d.actions), 1);

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-4 sm:px-6 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="p-2 rounded-lg bg-white/[0.06] text-white/60 hover:text-white">
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-white">{data.seller?.name}</h1>
            <p className="text-xs text-white/40">{data.seller?.role} — Performance</p>
          </div>
          <div className="ml-auto flex gap-1">
            {(['week', 'month', '3months'] as const).map(p => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                  period === p ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70'
                }`}
              >
                {p === 'week' ? '7d' : p === 'month' ? '30d' : '90d'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 space-y-6">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <KpiCard icon={<Target size={16} />} label="Leads asignados" value={kpis.leads_assigned} />
          <KpiCard icon={<TrendingUp size={16} />} label="Convertidos" value={kpis.leads_converted} />
          <KpiCard
            icon={<BarChart3 size={16} />} label="Conversión"
            value={`${kpis.conversion_rate}%`}
            comparison={teamAvg.conversion_rate ? `Equipo: ${teamAvg.conversion_rate}%` : undefined}
            isGood={kpis.conversion_rate >= (teamAvg.conversion_rate || 0)}
          />
          <KpiCard
            icon={<Clock size={16} />} label="Resp. promedio"
            value={formatTime(kpis.avg_first_response_seconds)}
            comparison={teamAvg.avg_first_response_seconds ? `Equipo: ${formatTime(teamAvg.avg_first_response_seconds)}` : undefined}
            isGood={(kpis.avg_first_response_seconds || 999) <= (teamAvg.avg_first_response_seconds || 999)}
          />
          <KpiCard icon={<Activity size={16} />} label="Acciones totales" value={kpis.total_actions} />
        </div>

        {/* Daily Activity Chart (simple bars) */}
        <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
          <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">Actividad Diaria</h3>
          <div className="flex items-end gap-1 h-32">
            {daily.slice(0, 30).reverse().map((d: any, i: number) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-blue-500/40 rounded-t hover:bg-blue-500/60 transition-colors"
                  style={{ height: `${(d.actions / maxDailyActions) * 100}%`, minHeight: d.actions > 0 ? '4px' : '0' }}
                  title={`${d.date}: ${d.actions} acciones`}
                />
              </div>
            ))}
          </div>
          {daily.length === 0 && <p className="text-xs text-white/30 text-center">Sin datos en este período</p>}
        </div>

        {/* Event Type Breakdown */}
        <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
          <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">Desglose por Tipo</h3>
          <div className="space-y-2">
            {Object.entries(breakdown)
              .sort(([, a]: any, [, b]: any) => b - a)
              .map(([type, count]: any) => {
                const totalActions = kpis.total_actions || 1;
                const pct = Math.round((count / totalActions) * 100);
                return (
                  <div key={type} className="flex items-center gap-3">
                    <span className="text-xs text-white/60 w-40 truncate">{LABELS[type] || type}</span>
                    <div className="flex-1 h-2 bg-white/[0.06] rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500/50 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs text-white/40 w-12 text-right">{count}</span>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Active Leads */}
        <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
          <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-1">Leads Activos Ahora</h3>
          <p className="text-2xl font-bold text-white">{kpis.active_leads_now}</p>
        </div>
      </div>
    </div>
  );
};

const LABELS: Record<string, string> = {
  note_added: 'Notas',
  lead_status_changed: 'Cambios de estado',
  chat_message_sent: 'Mensajes',
  call_logged: 'Llamadas',
  lead_assigned: 'Asignaciones',
  lead_handoff: 'Derivaciones',
  task_completed: 'Tareas completadas',
  lead_created: 'Leads creados',
  lead_qualified: 'Leads calificados',
};

const KpiCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | number;
  comparison?: string;
  isGood?: boolean;
}> = ({ icon, label, value, comparison, isGood }) => (
  <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
    <div className="flex items-center gap-2 mb-1 text-white/40">{icon}<span className="text-xs">{label}</span></div>
    <p className="text-xl font-bold text-white">{value}</p>
    {comparison && (
      <p className={`text-[10px] mt-0.5 ${isGood ? 'text-emerald-400' : 'text-red-400'}`}>{comparison}</p>
    )}
  </div>
);

export default SellerPerformanceView;
