/**
 * SellerPerformanceView — DEV-41: Reportes de performance individual por vendedor.
 * KPIs, gráfica diaria, breakdown por tipo, comparativa vs equipo, ranking, export CSV.
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, TrendingUp, Clock, Target, BarChart3, Activity, Download, Medal, ChevronUp, ChevronDown, Minus } from 'lucide-react';
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

type PeriodPreset = 'week' | 'month' | '3months' | 'custom';

const SellerPerformanceView: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [period, setPeriod] = useState<PeriodPreset>('month');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');

  // Initialise custom dates to current month on first render
  useEffect(() => {
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    setCustomFrom(firstDay.toISOString().slice(0, 10));
    setCustomTo(now.toISOString().slice(0, 10));
  }, []);

  useEffect(() => {
    if (!userId) return;
    // For custom, wait until both dates are filled
    if (period === 'custom' && (!customFrom || !customTo)) return;
    const load = async () => {
      setLoading(true);
      try {
        const now = new Date();
        let dateFrom = new Date();
        if (period === 'week') dateFrom.setDate(now.getDate() - 7);
        else if (period === 'month') dateFrom.setDate(now.getDate() - 30);
        else if (period === '3months') dateFrom.setDate(now.getDate() - 90);

        const fromParam = period === 'custom' ? new Date(customFrom).toISOString() : dateFrom.toISOString();
        const toParam = period === 'custom' ? new Date(customTo + 'T23:59:59').toISOString() : now.toISOString();

        const res = await api.get(`/admin/core/team-activity/seller/${userId}/performance`, {
          params: { date_from: fromParam, date_to: toParam },
        });
        setData(res.data);
      } catch { /* */ }
      setLoading(false);
    };
    load();
  }, [userId, period, customFrom, customTo]);

  const handleExportCSV = () => {
    if (!data) return;
    const kpis: KPIs = data.kpis;
    const teamAvg = data.team_avg || {};
    const breakdown = data.event_type_breakdown || {};
    const daily = data.daily_breakdown || [];
    const sellerName = data.seller?.name || userId;

    const rows: string[][] = [];
    rows.push(['Reporte de Performance', sellerName]);
    rows.push(['Período', period === 'custom' ? `${customFrom} — ${customTo}` : period]);
    rows.push([]);
    rows.push(['KPIs Clave', 'Vendedor', 'Equipo (promedio)']);
    rows.push(['Leads Asignados', String(kpis.leads_assigned), '']);
    rows.push(['Leads Convertidos', String(kpis.leads_converted), '']);
    rows.push(['Tasa de Conversión', `${kpis.conversion_rate}%`, teamAvg.conversion_rate ? `${teamAvg.conversion_rate}%` : '-']);
    rows.push(['Respuesta Promedio (s)', kpis.avg_first_response_seconds != null ? String(kpis.avg_first_response_seconds) : '-', teamAvg.avg_first_response_seconds ? String(teamAvg.avg_first_response_seconds) : '-']);
    rows.push(['Acciones Totales', String(kpis.total_actions), '']);
    rows.push(['Leads Activos', String(kpis.active_leads_now), '']);
    rows.push([]);
    rows.push(['Desglose por Tipo', 'Cantidad']);
    Object.entries(breakdown).sort(([, a]: any, [, b]: any) => b - a).forEach(([type, count]: any) => {
      rows.push([LABELS[type] || type, String(count)]);
    });
    rows.push([]);
    rows.push(['Actividad Diaria', 'Fecha', 'Acciones']);
    daily.forEach((d: any) => rows.push(['', d.date, String(d.actions)]));

    const csv = rows.map(r => r.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `performance_${sellerName.replace(/\s+/g, '_')}_${period}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

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
  const teamComparison = data.team_comparison || {};
  const breakdown = data.event_type_breakdown || {};
  const daily = data.daily_breakdown || [];

  const formatTime = (s: number | null) => {
    if (!s) return '-';
    if (s < 60) return `${s}s`;
    return `${Math.round(s / 60)}min`;
  };

  const maxDailyActions = Math.max(...daily.map((d: any) => d.actions), 1);

  // Derive ranking info from team_comparison if available
  const rankConversion = teamComparison.rank_conversion_rate;
  const rankResponse = teamComparison.rank_response_time;
  const rankActions = teamComparison.rank_actions;
  const totalSellers = teamComparison.total_sellers;

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-4 sm:px-6 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3 flex-wrap">
          <button onClick={() => navigate(-1)} className="p-2 rounded-lg bg-white/[0.06] text-white/60 hover:text-white">
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-white">{data.seller?.name}</h1>
            <p className="text-xs text-white/40">{data.seller?.role} — Performance</p>
          </div>
          <div className="ml-auto flex items-center gap-2 flex-wrap">
            {/* Period preset buttons */}
            <div className="flex gap-1">
              {(['week', 'month', '3months', 'custom'] as const).map(p => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                    period === p ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70'
                  }`}
                >
                  {p === 'week' ? '7d' : p === 'month' ? '30d' : p === '3months' ? '90d' : 'Custom'}
                </button>
              ))}
            </div>
            {/* Export button */}
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 px-3 py-1 text-xs rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
            >
              <Download size={12} />
              Exportar CSV
            </button>
          </div>
        </div>

        {/* Custom date range inputs */}
        {period === 'custom' && (
          <div className="flex items-center gap-3 mt-3 flex-wrap">
            <span className="text-xs text-white/40">Desde</span>
            <input
              type="date"
              value={customFrom}
              onChange={e => setCustomFrom(e.target.value)}
              className="bg-white/[0.05] border border-white/[0.10] rounded-lg px-3 py-1.5 text-xs text-white/80 focus:outline-none focus:border-violet-500/50"
            />
            <span className="text-xs text-white/40">Hasta</span>
            <input
              type="date"
              value={customTo}
              onChange={e => setCustomTo(e.target.value)}
              className="bg-white/[0.05] border border-white/[0.10] rounded-lg px-3 py-1.5 text-xs text-white/80 focus:outline-none focus:border-violet-500/50"
            />
          </div>
        )}
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
            comparison={teamAvg.conversion_rate != null ? `Equipo: ${teamAvg.conversion_rate}%` : undefined}
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

        {/* G1: Ranking / Team Comparison Card */}
        <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
          <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Medal size={14} />
            Ranking vs Equipo
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <CompareRow
              label="Conversión"
              sellerVal={`${kpis.conversion_rate}%`}
              teamVal={teamAvg.conversion_rate != null ? `${teamAvg.conversion_rate}%` : null}
              rank={rankConversion}
              total={totalSellers}
              higherIsBetter
              sellerRaw={kpis.conversion_rate}
              teamRaw={teamAvg.conversion_rate}
            />
            <CompareRow
              label="Resp. promedio"
              sellerVal={formatTime(kpis.avg_first_response_seconds)}
              teamVal={teamAvg.avg_first_response_seconds ? formatTime(teamAvg.avg_first_response_seconds) : null}
              rank={rankResponse}
              total={totalSellers}
              higherIsBetter={false}
              sellerRaw={kpis.avg_first_response_seconds || 0}
              teamRaw={teamAvg.avg_first_response_seconds || 0}
            />
            <CompareRow
              label="Acciones"
              sellerVal={String(kpis.total_actions)}
              teamVal={teamAvg.total_actions != null ? String(teamAvg.total_actions) : null}
              rank={rankActions}
              total={totalSellers}
              higherIsBetter
              sellerRaw={kpis.total_actions}
              teamRaw={teamAvg.total_actions}
            />
          </div>
        </div>

        {/* Daily Activity Chart (simple bars) */}
        <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
          <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">Actividad Diaria</h3>
          <div className="flex items-end gap-1 h-32">
            {daily.slice(0, 30).reverse().map((d: any, i: number) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-violet-500/40 rounded-t hover:bg-violet-500/60 transition-colors"
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
                      <div className="h-full bg-violet-500/50 rounded-full" style={{ width: `${pct}%` }} />
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

// G1: Team comparison row component
const CompareRow: React.FC<{
  label: string;
  sellerVal: string;
  teamVal: string | null;
  rank?: number;
  total?: number;
  higherIsBetter: boolean;
  sellerRaw: number;
  teamRaw?: number;
}> = ({ label, sellerVal, teamVal, rank, total, higherIsBetter, sellerRaw, teamRaw }) => {
  const hasComparison = teamVal != null && teamRaw != null;
  const isGood = hasComparison
    ? higherIsBetter ? sellerRaw >= teamRaw! : sellerRaw <= teamRaw!
    : null;

  const DeltaIcon = isGood === null ? null : isGood ? ChevronUp : ChevronDown;

  return (
    <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-3 space-y-2">
      <p className="text-[10px] font-semibold text-white/40 uppercase tracking-wider">{label}</p>
      <div className="flex items-end justify-between gap-2">
        <div>
          <p className="text-xl font-bold text-white leading-none">{sellerVal}</p>
          {hasComparison && (
            <p className="text-[10px] text-white/40 mt-1">Equipo: {teamVal}</p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          {rank != null && total != null && (
            <span className="text-[10px] font-bold text-white/60 bg-white/[0.06] px-2 py-0.5 rounded-full">
              #{rank} de {total}
            </span>
          )}
          {DeltaIcon && (
            <DeltaIcon
              size={16}
              className={isGood ? 'text-emerald-400' : 'text-red-400'}
            />
          )}
          {isGood === null && <Minus size={14} className="text-white/30" />}
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
