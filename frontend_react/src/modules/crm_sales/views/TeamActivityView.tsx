/**
 * TeamActivityView — DEV-39: Panel de actividad del equipo en tiempo real.
 * Solo accesible por rol CEO.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, Users, AlertTriangle, RefreshCw, Filter, X,
  FileText, ArrowRightLeft, UserPlus, MessageSquare, Phone,
  CheckCircle2, Zap, ChevronDown
} from 'lucide-react';
import { useTeamActivity, ActivityEvent, SellerStatus, InactiveLeadAlert } from '../hooks/useTeamActivity';

// ──────────────────────────────────────────
// EVENT TYPE CONFIG
// ──────────────────────────────────────────
const EVENT_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  lead_created:        { label: 'Creo lead',           icon: <UserPlus size={14} />,       color: 'text-emerald-400' },
  lead_status_changed: { label: 'Cambio estado',       icon: <ArrowRightLeft size={14} />, color: 'text-violet-400' },
  lead_assigned:       { label: 'Asigno lead',         icon: <Users size={14} />,          color: 'text-violet-400' },
  note_added:          { label: 'Dejo nota',           icon: <FileText size={14} />,       color: 'text-amber-400' },
  call_logged:         { label: 'Registro llamada',    icon: <Phone size={14} />,          color: 'text-cyan-400' },
  chat_message_sent:   { label: 'Envio mensaje',       icon: <MessageSquare size={14} />,  color: 'text-green-400' },
  task_completed:      { label: 'Completo tarea',      icon: <CheckCircle2 size={14} />,   color: 'text-teal-400' },
  lead_qualified:      { label: 'Califico lead',       icon: <Zap size={14} />,            color: 'text-yellow-400' },
  lead_handoff:        { label: 'Derivo a closer',     icon: <ArrowRightLeft size={14} />, color: 'text-purple-400' },
};

const STATUS_COLORS: Record<string, string> = {
  active:   'bg-emerald-500',
  idle:     'bg-amber-500',
  inactive: 'bg-red-500',
};

const STATUS_LABELS: Record<string, string> = {
  active:   'Activo',
  idle:     'Inactivo',
  inactive: 'Desconectado',
};

const EVENT_TYPES_FILTER = [
  { value: '', label: 'Todos los tipos' },
  { value: 'note_added', label: 'Notas' },
  { value: 'lead_status_changed', label: 'Cambios de estado' },
  { value: 'lead_assigned', label: 'Asignaciones' },
  { value: 'lead_handoff', label: 'Derivaciones' },
  { value: 'chat_message_sent', label: 'Mensajes' },
  { value: 'call_logged', label: 'Llamadas' },
  { value: 'task_completed', label: 'Tareas completadas' },
];

// ──────────────────────────────────────────
// ACTIVITY FEED ITEM
// ──────────────────────────────────────────
const ActivityFeedItem: React.FC<{ event: ActivityEvent; onClick: () => void }> = ({ event, onClick }) => {
  const config = EVENT_CONFIG[event.event_type] || { label: event.event_type, icon: <Activity size={14} />, color: 'text-white/60' };
  const meta = event.metadata || {};

  let description = '';
  switch (event.event_type) {
    case 'lead_status_changed':
      description = `${meta.from_status || '?'} → ${meta.to_status || '?'}`;
      break;
    case 'lead_handoff':
      description = `de ${meta.from_seller || '?'} a ${meta.to_seller || '?'}`;
      break;
    case 'note_added':
      description = meta.note_type || '';
      break;
    default:
      description = '';
  }

  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-3 hover:bg-white/[0.04] transition-colors border-b border-white/[0.04] group"
    >
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 p-1.5 rounded-lg bg-white/[0.06] ${config.color}`}>
          {config.icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-white/90">
            <span className="font-medium text-white">{event.actor?.name || 'Sistema'}</span>
            {' '}<span className="text-white/50">{config.label.toLowerCase()}</span>
            {event.entity_name && (
              <>
                {' en '}
                <span className="text-white/80 font-medium">{event.entity_name}</span>
              </>
            )}
          </p>
          {description && (
            <p className="text-xs text-white/40 mt-0.5">{description}</p>
          )}
        </div>
        <span className="text-xs text-white/30 shrink-0 mt-0.5">
          {event.time_ago || formatTimeAgo(event.created_at)}
        </span>
      </div>
    </button>
  );
};

// ──────────────────────────────────────────
// SELLER STATUS CARD
// ──────────────────────────────────────────
const SellerStatusCard: React.FC<{ seller: SellerStatus }> = ({ seller }) => {
  const formatResponseTime = (seconds: number | null) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds}s`;
    return `${Math.round(seconds / 60)}min`;
  };

  return (
    <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-white/[0.1] transition-colors">
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[seller.status]}`} />
        <span className="text-sm font-medium text-white truncate">{seller.name}</span>
        <span className="text-[10px] text-white/30 ml-auto">{seller.role}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-white/40">Leads activos</span>
          <p className="text-white font-medium">{seller.active_leads_count}</p>
        </div>
        <div>
          <span className="text-white/40">Resp. hoy</span>
          <p className="text-white font-medium">{formatResponseTime(seller.avg_first_response_today_seconds)}</p>
        </div>
        <div>
          <span className="text-white/40">Estado</span>
          <p className={`font-medium ${seller.status === 'active' ? 'text-emerald-400' : seller.status === 'idle' ? 'text-amber-400' : 'text-red-400'}`}>
            {STATUS_LABELS[seller.status]}
          </p>
        </div>
        <div>
          <span className="text-white/40">Sin atender</span>
          <p className={`font-medium ${seller.leads_without_activity_2h > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
            {seller.leads_without_activity_2h}
          </p>
        </div>
      </div>
    </div>
  );
};

// ──────────────────────────────────────────
// INACTIVE LEAD ALERT
// ──────────────────────────────────────────
const InactiveLeadAlertItem: React.FC<{ alert: InactiveLeadAlert; onClick: () => void }> = ({ alert, onClick }) => (
  <button
    onClick={onClick}
    className="w-full text-left px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 hover:border-red-500/40 transition-colors"
  >
    <div className="flex items-center gap-2">
      <AlertTriangle size={14} className={alert.severity === 'critical' ? 'text-red-400' : 'text-amber-400'} />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-white/80 truncate">{alert.lead_name}</p>
        <p className="text-[10px] text-white/40">{alert.assigned_seller} — {alert.hours_inactive}h sin actividad</p>
      </div>
    </div>
  </button>
);

// ──────────────────────────────────────────
// MAIN VIEW
// ──────────────────────────────────────────
const TeamActivityView: React.FC = () => {
  const navigate = useNavigate();
  const {
    feedItems, sellers, alerts, loading, total,
    hasMore, loadMore, filters, applyFilters, refresh,
  } = useTeamActivity();

  const [showFilters, setShowFilters] = useState(false);
  const [filterSeller, setFilterSeller] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');

  const handleApplyFilters = () => {
    applyFilters({
      seller_id: filterSeller || undefined,
      event_type: filterType || undefined,
      date_from: filterDateFrom || undefined,
      date_to: filterDateTo || undefined,
    });
    setShowFilters(false);
  };

  const handleClearFilters = () => {
    setFilterSeller('');
    setFilterType('');
    setFilterDateFrom('');
    setFilterDateTo('');
    applyFilters({});
    setShowFilters(false);
  };

  const hasActiveFilters = !!(filters.seller_id || filters.event_type || filters.date_from || filters.date_to);

  const activeSellersCount = sellers.filter(s => s.status === 'active').length;
  const totalAlerts = alerts.length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/40" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-4 sm:px-6 py-4 border-b border-white/[0.06]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-white/[0.06]">
              <Activity size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">Actividad del Equipo</h1>
              <p className="text-xs text-white/40">
                {activeSellersCount} vendedores activos — {total} eventos — {totalAlerts} alertas
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`p-2 rounded-lg transition-colors ${hasActiveFilters ? 'bg-violet-500/20 text-violet-400' : 'bg-white/[0.06] text-white/60 hover:text-white'}`}
            >
              <Filter size={16} />
            </button>
            <button onClick={refresh} className="p-2 rounded-lg bg-white/[0.06] text-white/60 hover:text-white transition-colors">
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <div className="mt-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div>
                <label className="text-xs text-white/40 mb-1 block">Vendedor</label>
                <select
                  value={filterSeller}
                  onChange={(e) => setFilterSeller(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-white/20"
                >
                  <option value="">Todos</option>
                  {sellers.map(s => (
                    <option key={s.user_id} value={s.user_id}>{s.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">Tipo de accion</label>
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-white/20"
                >
                  {EVENT_TYPES_FILTER.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">Desde</label>
                <input
                  type="date"
                  value={filterDateFrom}
                  onChange={(e) => setFilterDateFrom(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-white/20"
                />
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">Hasta</label>
                <input
                  type="date"
                  value={filterDateTo}
                  onChange={(e) => setFilterDateTo(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-white/20"
                />
              </div>
            </div>
            <div className="flex items-center gap-2 justify-end">
              <button onClick={handleClearFilters} className="px-3 py-1.5 text-xs text-white/50 hover:text-white transition-colors">
                Limpiar
              </button>
              <button
                onClick={handleApplyFilters}
                className="px-4 py-1.5 text-xs bg-white/10 hover:bg-white/15 text-white rounded-lg transition-colors"
              >
                Aplicar filtros
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main Content: two-panel layout */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row">
        {/* Left Panel: Sellers + Alerts (desktop sidebar, mobile top) */}
        <div className="lg:w-72 xl:w-80 shrink-0 border-b lg:border-b-0 lg:border-r border-white/[0.06] overflow-y-auto">
          <div className="p-4 space-y-4">
            {/* Seller Status Section */}
            <div>
              <h2 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Users size={13} />
                Vendedores ({sellers.length})
              </h2>
              <div className="space-y-2">
                {sellers.map(seller => (
                  <SellerStatusCard key={seller.id} seller={seller} />
                ))}
                {sellers.length === 0 && (
                  <p className="text-xs text-white/30 text-center py-4">Sin vendedores activos</p>
                )}
              </div>
            </div>

            {/* Alerts Section */}
            {alerts.length > 0 && (
              <div>
                <h2 className="text-xs font-semibold text-red-400/80 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <AlertTriangle size={13} />
                  Alertas ({alerts.length})
                </h2>
                <div className="space-y-2">
                  {alerts.map(alert => (
                    <InactiveLeadAlertItem
                      key={alert.lead_id}
                      alert={alert}
                      onClick={() => navigate(`/crm/leads/${alert.lead_id}`)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel: Activity Feed */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between">
            <h2 className="text-xs font-semibold text-white/50 uppercase tracking-wider flex items-center gap-2">
              <Activity size={13} />
              Feed de actividad
              {hasActiveFilters && <span className="text-violet-400">(filtrado)</span>}
            </h2>
            <span className="text-xs text-white/30">{total} eventos</span>
          </div>

          {feedItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-white/30">
              <Activity size={32} className="mb-3 opacity-30" />
              <p className="text-sm">Sin actividad registrada</p>
              {hasActiveFilters && (
                <button onClick={handleClearFilters} className="mt-2 text-xs text-violet-400 hover:underline">
                  Quitar filtros
                </button>
              )}
            </div>
          ) : (
            <>
              {feedItems.map(event => (
                <ActivityFeedItem
                  key={event.id}
                  event={event}
                  onClick={() => {
                    if (event.entity_type === 'lead' && event.entity_id) {
                      navigate(`/crm/leads/${event.entity_id}`);
                    }
                  }}
                />
              ))}
              {hasMore && (
                <div className="p-4 text-center">
                  <button
                    onClick={loadMore}
                    className="inline-flex items-center gap-2 px-4 py-2 text-xs text-white/50 bg-white/[0.04] hover:bg-white/[0.08] rounded-lg transition-colors"
                  >
                    <ChevronDown size={14} />
                    Cargar mas
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

// ──────────────────────────────────────────
// UTILS
// ──────────────────────────────────────────
function formatTimeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return 'hace un momento';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days}d`;
}

export default TeamActivityView;
