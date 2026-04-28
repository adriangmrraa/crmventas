/**
 * UnifiedTimeline — DEV-45: Unified timeline component for leads.
 * Renders all event types (messages, notes, status changes, tasks, calls, HSM, assignments)
 * in a single chronological thread with filter chips and infinite scroll.
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  MessageSquare,
  StickyNote,
  ArrowRightLeft,
  Phone,
  UserCheck,
  CheckSquare,
  Send,
  Eye,
  Lock,
  ChevronDown,
  RefreshCw,
  AlertCircle,
  Instagram,
  Loader2,
} from 'lucide-react';
import { useLeadTimeline, TimelineEvent } from '../../modules/crm_sales/hooks/useLeadTimeline';

// ──────────────────────────────────────────
// TYPES
// ──────────────────────────────────────────

interface FilterChip {
  value: string;
  label: string;
  icon: React.ReactNode;
  color: string;
}

interface UnifiedTimelineProps {
  leadId: string;
}

// ──────────────────────────────────────────
// CONSTANTS
// ──────────────────────────────────────────

const FILTER_CHIPS: FilterChip[] = [
  { value: '', label: 'Todos', icon: null, color: 'text-white/70' },
  {
    value: 'whatsapp_message',
    label: 'WhatsApp',
    icon: <MessageSquare size={12} />,
    color: 'text-green-400',
  },
  {
    value: 'instagram_message',
    label: 'Instagram',
    icon: <Instagram size={12} />,
    color: 'text-pink-400',
  },
  { value: 'note', label: 'Notas', icon: <StickyNote size={12} />, color: 'text-amber-400' },
  {
    value: 'status_change',
    label: 'Estados',
    icon: <ArrowRightLeft size={12} />,
    color: 'text-violet-400',
  },
  {
    value: 'task_created,task_completed',
    label: 'Tareas',
    icon: <CheckSquare size={12} />,
    color: 'text-teal-400',
  },
  { value: 'call_logged', label: 'Llamadas', icon: <Phone size={12} />, color: 'text-cyan-400' },
  {
    value: 'assignment_change',
    label: 'Asignaciones',
    icon: <UserCheck size={12} />,
    color: 'text-purple-400',
  },
  { value: 'hsm_sent', label: 'HSM', icon: <Send size={12} />, color: 'text-blue-400' },
];

const EVENT_ICON: Record<string, React.ReactNode> = {
  whatsapp_message: <MessageSquare size={14} />,
  instagram_message: <Instagram size={14} />,
  facebook_message: <MessageSquare size={14} />,
  note: <StickyNote size={14} />,
  status_change: <ArrowRightLeft size={14} />,
  task_created: <CheckSquare size={14} />,
  task_completed: <CheckSquare size={14} />,
  call_logged: <Phone size={14} />,
  hsm_sent: <Send size={14} />,
  assignment_change: <UserCheck size={14} />,
};

const EVENT_COLOR: Record<string, string> = {
  whatsapp_message: 'text-green-400 bg-green-500/10',
  instagram_message: 'text-pink-400 bg-pink-500/10',
  facebook_message: 'text-blue-400 bg-blue-500/10',
  note: 'text-amber-400 bg-amber-500/10',
  status_change: 'text-violet-400 bg-violet-500/10',
  task_created: 'text-teal-400 bg-teal-500/10',
  task_completed: 'text-teal-400 bg-teal-500/10',
  call_logged: 'text-cyan-400 bg-cyan-500/10',
  hsm_sent: 'text-blue-400 bg-blue-500/10',
  assignment_change: 'text-purple-400 bg-purple-500/10',
};

const EVENT_LABEL: Record<string, string> = {
  whatsapp_message: 'WhatsApp',
  instagram_message: 'Instagram',
  facebook_message: 'Facebook',
  note: 'Nota',
  status_change: 'Cambio de estado',
  task_created: 'Tarea creada',
  task_completed: 'Tarea completada',
  call_logged: 'Llamada',
  hsm_sent: 'HSM enviado',
  assignment_change: 'Asignación',
};

// ──────────────────────────────────────────
// HELPERS
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

function formatFullDate(isoDate: string): string {
  try {
    return new Intl.DateTimeFormat('es', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(isoDate));
  } catch {
    return isoDate;
  }
}

// ──────────────────────────────────────────
// TIMELINE EVENT CARD
// ──────────────────────────────────────────

const TimelineEventCard: React.FC<{ event: TimelineEvent }> = ({ event }) => {
  const [expanded, setExpanded] = useState(false);
  const colorClass = EVENT_COLOR[event.event_type] || 'text-white/50 bg-white/[0.06]';
  const icon = EVENT_ICON[event.event_type] || <MessageSquare size={14} />;
  const label = EVENT_LABEL[event.event_type] || event.event_type;
  const isPublic = event.visibility === 'public';
  const hasDetail = !!event.content?.detail && event.content.detail !== event.content.summary;

  return (
    <div className="flex gap-3 group">
      {/* Timeline line + icon */}
      <div className="flex flex-col items-center">
        <div className={`p-1.5 rounded-lg shrink-0 ${colorClass}`}>{icon}</div>
        <div className="w-px flex-1 bg-white/[0.04] mt-1" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pb-4">
        {/* Header row */}
        <div className="flex items-start gap-2 flex-wrap mb-1">
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium border ${colorClass} border-current/20`}
          >
            {label}
          </span>

          {event.actor?.name && event.actor.name !== 'Sistema' && (
            <span className="text-xs text-white/60 font-medium">{event.actor.name}</span>
          )}
          {event.actor?.role && event.actor.role !== 'system' && (
            <span className="text-[10px] text-white/30 px-1.5 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06]">
              {event.actor.role}
            </span>
          )}

          <div className="ml-auto flex items-center gap-1.5 shrink-0">
            {/* Visibility indicator */}
            <span title={isPublic ? 'Público' : 'Interno'}>
              {isPublic ? (
                <Eye size={11} className="text-white/20" />
              ) : (
                <Lock size={11} className="text-white/20" />
              )}
            </span>
            {/* Timestamp */}
            <span
              className="text-[10px] text-white/25 whitespace-nowrap"
              title={formatFullDate(event.timestamp)}
            >
              {formatTimeAgo(event.timestamp)}
            </span>
          </div>
        </div>

        {/* Summary */}
        <p className="text-sm text-white/70 leading-snug">{event.content?.summary}</p>

        {/* Expandable detail */}
        {hasDetail && (
          <>
            {expanded && (
              <p className="mt-2 text-xs text-white/50 whitespace-pre-wrap bg-white/[0.02] border border-white/[0.05] rounded-lg p-2.5">
                {event.content.detail}
              </p>
            )}
            <button
              onClick={() => setExpanded((v) => !v)}
              className="mt-1 text-[10px] text-white/30 hover:text-white/60 flex items-center gap-0.5 transition-colors"
            >
              <ChevronDown
                size={10}
                className={`transition-transform ${expanded ? 'rotate-180' : ''}`}
              />
              {expanded ? 'Ocultar' : 'Ver detalle'}
            </button>
          </>
        )}
      </div>
    </div>
  );
};

// ──────────────────────────────────────────
// SKELETON LOADING STATE
// ──────────────────────────────────────────

const SkeletonCard: React.FC = () => (
  <div className="flex gap-3 animate-pulse">
    <div className="flex flex-col items-center">
      <div className="w-7 h-7 rounded-lg bg-white/[0.04]" />
      <div className="w-px flex-1 bg-white/[0.04] mt-1" />
    </div>
    <div className="flex-1 pb-4 space-y-2">
      <div className="flex gap-2">
        <div className="h-4 w-16 rounded-full bg-white/[0.04]" />
        <div className="h-4 w-20 rounded-full bg-white/[0.04]" />
      </div>
      <div className="h-4 w-3/4 rounded bg-white/[0.04]" />
    </div>
  </div>
);

// ──────────────────────────────────────────
// FILTER BAR
// ──────────────────────────────────────────

interface FilterBarProps {
  activeFilter: string;
  onChange: (value: string) => void;
}

const FilterBar: React.FC<FilterBarProps> = ({ activeFilter, onChange }) => (
  <div className="flex items-center gap-1.5 flex-wrap">
    {FILTER_CHIPS.map((chip) => {
      const isActive = activeFilter === chip.value;
      return (
        <button
          key={chip.value}
          onClick={() => onChange(chip.value)}
          className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${
            isActive
              ? 'bg-white/10 border-white/20 text-white'
              : 'bg-white/[0.03] border-white/[0.06] text-white/40 hover:text-white/70 hover:bg-white/[0.06]'
          }`}
        >
          {chip.icon && <span className={chip.color}>{chip.icon}</span>}
          {chip.label}
        </button>
      );
    })}
  </div>
);

// ──────────────────────────────────────────
// MAIN COMPONENT
// ──────────────────────────────────────────

const UnifiedTimeline: React.FC<UnifiedTimelineProps> = ({ leadId }) => {
  const [activeFilter, setActiveFilter] = useState('');

  // Convert filter chip value to types array
  const activeTypes = activeFilter
    ? activeFilter.split(',').map((t) => t.trim()).filter(Boolean)
    : undefined;

  const { events, isLoading, isFetchingMore, hasMore, error, fetchNextPage, refetch } =
    useLeadTimeline({ leadId, types: activeTypes });

  // IntersectionObserver sentinel for infinite scroll
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  const handleFilterChange = useCallback((value: string) => {
    setActiveFilter(value);
  }, []);

  useEffect(() => {
    if (!sentinelRef.current) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMore && !isFetchingMore) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 },
    );

    observerRef.current.observe(sentinelRef.current);

    return () => {
      observerRef.current?.disconnect();
    };
  }, [hasMore, isFetchingMore, fetchNextPage]);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 shrink-0">
        <h3 className="text-sm font-semibold text-white/70 flex items-center gap-2">
          <ArrowRightLeft size={15} className="text-white/30" />
          Timeline
          {!isLoading && (
            <span className="text-xs text-white/30 bg-white/[0.04] px-2 py-0.5 rounded-full font-normal">
              {events.length}{hasMore ? '+' : ''}
            </span>
          )}
        </h3>
        <button
          onClick={refetch}
          className="p-1.5 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/[0.04] transition-colors"
          title="Actualizar"
        >
          <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Filter chips */}
      <div className="mb-4 shrink-0">
        <FilterBar activeFilter={activeFilter} onChange={handleFilterChange} />
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs flex items-center gap-2 shrink-0">
          <AlertCircle size={14} />
          {error}
          <button onClick={refetch} className="ml-auto underline hover:no-underline">
            Reintentar
          </button>
        </div>
      )}

      {/* Timeline list */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-0">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <ArrowRightLeft size={28} className="text-white/10 mb-2" />
            <p className="text-sm text-white/30">
              {activeFilter
                ? 'No hay eventos de este tipo para este lead'
                : 'No hay actividad registrada para este lead'}
            </p>
            {activeFilter && (
              <button
                onClick={() => setActiveFilter('')}
                className="mt-2 text-xs text-violet-400 hover:underline"
              >
                Quitar filtro
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-0">
            {events.map((event) => (
              <TimelineEventCard key={event.id} event={event} />
            ))}

            {/* Infinite scroll sentinel */}
            <div ref={sentinelRef} className="py-1" />

            {/* Load more indicator */}
            {isFetchingMore && (
              <div className="flex items-center justify-center py-3 text-white/30">
                <Loader2 size={16} className="animate-spin mr-2" />
                <span className="text-xs">Cargando más...</span>
              </div>
            )}

            {/* Manual load more fallback */}
            {hasMore && !isFetchingMore && (
              <div className="py-3 text-center">
                <button
                  onClick={fetchNextPage}
                  className="inline-flex items-center gap-2 px-4 py-2 text-xs text-white/40 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] rounded-lg transition-colors"
                >
                  <ChevronDown size={13} />
                  Cargar más eventos
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default UnifiedTimeline;
