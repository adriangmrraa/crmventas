import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Zap, Target, RefreshCw } from 'lucide-react';
import api from '../../../api/axios';
import PageHeader from '../../../components/PageHeader';
import GlassCard, { CARD_IMAGES } from '../../../components/GlassCard';
import SalesFunnelChart from '../components/SalesFunnelChart';

type Tab = 'funnel' | 'forecast' | 'velocity';

interface FunnelStage {
  code: string;
  name: string;
  color: string;
  count: number;
  conversion_from_top: number;
  conversion_from_prev: number;
  is_final: boolean;
}

export default function SalesAnalyticsView() {
  const [activeTab, setActiveTab] = useState<Tab>('funnel');
  const [period, setPeriod] = useState(30);
  const [loading, setLoading] = useState(true);
  const [funnel, setFunnel] = useState<any>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [velocity, setVelocity] = useState<any>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [funnelRes, forecastRes, velocityRes] = await Promise.all([
        api.get('/admin/core/crm/analytics/funnel', { params: { days: period } }),
        api.get('/admin/core/crm/analytics/forecast'),
        api.get('/admin/core/crm/analytics/velocity', { params: { days: period } }),
      ]);
      setFunnel(funnelRes.data);
      setForecast(forecastRes.data);
      setVelocity(velocityRes.data);
    } catch (err) {
      console.error('Analytics error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [period]);

  const tabs: { id: Tab; label: string; icon: any }[] = [
    { id: 'funnel', label: 'Embudo', icon: BarChart3 },
    { id: 'forecast', label: 'Forecast', icon: TrendingUp },
    { id: 'velocity', label: 'Velocidad', icon: Zap },
  ];

  const periods = [
    { value: 7, label: '7d' },
    { value: 30, label: '30d' },
    { value: 90, label: '90d' },
    { value: 365, label: '1 año' },
  ];

  // const maxFunnelCount = funnel?.funnel?.reduce((max: number, s: FunnelStage) => Math.max(max, s.count), 1) || 1;

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-6">
      <PageHeader
        title="Analytics de Ventas"
        subtitle="Embudo, forecast y velocidad de cierre"
        icon={<Target size={20} />}
        action={
          <button onClick={fetchData} className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20 hover:bg-violet-500/20 transition-all active:scale-95">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Actualizar
          </button>
        }
      />

      {/* Period selector + Tabs */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex gap-1">
          {tabs.map(tab => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-95
                  ${active ? 'bg-white/[0.08] text-white border border-white/[0.12]' : 'text-white/40 hover:text-white/60 hover:bg-white/[0.04]'}
                `}
              >
                <Icon size={14} />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="flex gap-1 bg-white/[0.03] rounded-lg p-0.5 border border-white/[0.06]">
          {periods.map(p => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1.5 rounded-md text-[11px] font-semibold transition-all
                ${period === p.value ? 'bg-white/[0.08] text-white' : 'text-white/40 hover:text-white/60'}
              `}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <RefreshCw className="w-8 h-8 text-violet-400 animate-spin" />
        </div>
      ) : (
        <>
          {/* ===== FUNNEL TAB ===== */}
          {activeTab === 'funnel' && funnel && (
            <div className="space-y-4">
              {/* KPI row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <GlassCard image={CARD_IMAGES.leads} className="p-4">
                  <p className="text-white/40 text-xs">Total Leads</p>
                  <p className="text-2xl font-bold text-white mt-1">{funnel.total_leads}</p>
                </GlassCard>
                <GlassCard image={CARD_IMAGES.revenue} className="p-4">
                  <p className="text-white/40 text-xs">Ganados</p>
                  <p className="text-2xl font-bold text-green-400 mt-1">{funnel.won}</p>
                </GlassCard>
                <GlassCard image={CARD_IMAGES.pipeline} className="p-4">
                  <p className="text-white/40 text-xs">Perdidos</p>
                  <p className="text-2xl font-bold text-red-400 mt-1">{funnel.lost}</p>
                </GlassCard>
                <GlassCard image={CARD_IMAGES.analytics} className="p-4">
                  <p className="text-white/40 text-xs">Win Rate</p>
                  <p className="text-2xl font-bold text-violet-400 mt-1">{funnel.win_rate}%</p>
                </GlassCard>
              </div>

              {/* Funnel chart (Professional) */}
              <GlassCard className="p-4 sm:p-6 border-white/5">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <BarChart3 size={16} className="text-violet-400" />
                    Distribución de Leads por Etapa
                  </h3>
                  <p className="text-[10px] text-white/30 uppercase tracking-widest font-bold">Datos en tiempo real</p>
                </div>
                <SalesFunnelChart 
                  data={funnel.funnel.map((s: FunnelStage) => ({
                    stage: s.name,
                    count: s.count
                  }))} 
                />
              </GlassCard>
            </div>
          )}

          {/* ===== FORECAST TAB ===== */}
          {activeTab === 'forecast' && forecast && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <GlassCard image={CARD_IMAGES.revenue} className="p-4">
                  <p className="text-white/40 text-xs">Pipeline Total</p>
                  <p className="text-xl font-bold text-white mt-1">${forecast.total_pipeline_value?.toLocaleString()}</p>
                </GlassCard>
                <GlassCard image={CARD_IMAGES.analytics} className="p-4">
                  <p className="text-white/40 text-xs">Forecast Ponderado</p>
                  <p className="text-xl font-bold text-violet-400 mt-1">${forecast.weighted_forecast?.toLocaleString()}</p>
                </GlassCard>
                <GlassCard image={CARD_IMAGES.pipeline} className="p-4 col-span-2 sm:col-span-1">
                  <p className="text-white/40 text-xs">Revenue Ganado</p>
                  <p className="text-xl font-bold text-green-400 mt-1">${forecast.won_revenue?.toLocaleString()}</p>
                </GlassCard>
              </div>

              <div className="bg-white/[0.03] rounded-2xl border border-white/[0.06] p-4 sm:p-6">
                <h3 className="text-sm font-bold text-white mb-4">Pipeline por Etapa (Ponderado)</h3>
                <div className="space-y-3">
                  {forecast.pipeline?.map((stage: any) => (
                    <div key={stage.stage} className="flex items-center justify-between p-3 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                      <div>
                        <p className="text-sm font-semibold text-white">{stage.stage}</p>
                        <p className="text-[11px] text-white/30">{stage.count} leads | prob: {(stage.probability * 100).toFixed(0)}%</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-white">${stage.total_value?.toLocaleString()}</p>
                        <p className="text-[11px] text-violet-400">${stage.weighted_value?.toLocaleString()} pond.</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ===== VELOCITY TAB ===== */}
          {activeTab === 'velocity' && velocity && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <GlassCard image={CARD_IMAGES.analytics} className="p-4">
                  <p className="text-white/40 text-xs">Deals Cerrados</p>
                  <p className="text-2xl font-bold text-white mt-1">{velocity.deals_won}</p>
                  <p className="text-[10px] text-white/30">{velocity.deals_per_month}/mes</p>
                </GlassCard>
                <GlassCard image={CARD_IMAGES.revenue} className="p-4">
                  <p className="text-white/40 text-xs">Ticket Promedio</p>
                  <p className="text-2xl font-bold text-green-400 mt-1">${velocity.avg_deal_size?.toLocaleString()}</p>
                </GlassCard>
                <GlassCard image={CARD_IMAGES.calendar} className="p-4">
                  <p className="text-white/40 text-xs">Ciclo Promedio</p>
                  <p className="text-2xl font-bold text-violet-400 mt-1">{velocity.avg_cycle_days} dias</p>
                </GlassCard>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <GlassCard image={CARD_IMAGES.team} className="p-4">
                  <p className="text-white/40 text-xs">Win Rate</p>
                  <p className="text-3xl font-bold text-white mt-1">{velocity.win_rate}%</p>
                  <div className="mt-2 h-2 bg-white/[0.06] rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full transition-all duration-700" style={{ width: `${velocity.win_rate}%` }} />
                  </div>
                </GlassCard>
                <GlassCard image={CARD_IMAGES.pipeline} className="p-4">
                  <p className="text-white/40 text-xs">Sales Velocity</p>
                  <p className="text-3xl font-bold text-violet-400 mt-1">${velocity.velocity?.toLocaleString()}</p>
                  <p className="text-[10px] text-white/30 mt-1">$/dia (deals × size × rate / ciclo)</p>
                </GlassCard>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
