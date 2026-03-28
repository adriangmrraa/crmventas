import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Clock, DollarSign, User, GripVertical, RefreshCw, Filter, LayoutGrid, List } from 'lucide-react';
import api from '../../../api/axios';
import { parseTags } from '../../../utils/parseTags';
import PageHeader from '../../../components/PageHeader';
import { useTranslation } from '../../../context/LanguageContext';
import ScoreBadge from '../../../components/leads/ScoreBadge';

interface LeadStatus {
  id: number;
  name: string;
  code: string;
  color: string;
  icon?: string;
  sort_order: number;
  is_initial: boolean;
  is_final: boolean;
}

interface Lead {
  id: number;
  first_name: string;
  last_name: string;
  phone_number: string;
  email?: string;
  company?: string;
  status: string;
  source?: string;
  seller_id?: number;
  seller_name?: string;
  created_at: string;
  updated_at?: string;
  last_activity_at?: string;
  tags?: string[];
  notes?: string;
  estimated_value?: number;
  score?: number;
}

export default function KanbanPipelineView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [statuses, setStatuses] = useState<LeadStatus[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, leadsRes] = await Promise.all([
        api.get('/admin/core/crm/lead-statuses'),
        api.get('/admin/core/crm/leads', { params: { limit: 500 } }),
      ]);
      setStatuses(statusRes.data.sort((a: LeadStatus, b: LeadStatus) => a.sort_order - b.sort_order));
      setLeads(Array.isArray(leadsRes.data) ? leadsRes.data : leadsRes.data.leads || []);
    } catch (err) {
      console.error('Error fetching pipeline data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const getLeadsByStatus = (statusCode: string) =>
    leads.filter(l => {
      const leadStatus = l.status || 'nuevo';
      return leadStatus === statusCode;
    });

  const getDaysInStage = (lead: Lead) => {
    const updated = lead.updated_at || lead.created_at;
    if (!updated) return 0;
    return Math.floor((Date.now() - new Date(updated).getTime()) / (1000 * 60 * 60 * 24));
  };

  // Drag handlers
  const handleDragStart = (e: React.DragEvent, leadId: number) => {
    e.dataTransfer.setData('leadId', String(leadId));
    e.dataTransfer.effectAllowed = 'move';
    setDraggingId(leadId);
  };

  const handleDragOver = (e: React.DragEvent, statusCode: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverColumn(statusCode);
  };

  const handleDragLeave = () => {
    setDragOverColumn(null);
  };

  const handleDrop = async (e: React.DragEvent, newStatus: string) => {
    e.preventDefault();
    setDragOverColumn(null);
    setDraggingId(null);

    const leadId = parseInt(e.dataTransfer.getData('leadId'));
    const lead = leads.find(l => l.id === leadId);
    if (!lead || lead.status === newStatus) return;

    // Optimistic update
    const oldStatus = lead.status;
    setLeads(prev => prev.map(l => l.id === leadId ? { ...l, status: newStatus } : l));
    setUpdatingId(leadId);

    try {
      await api.post(`/admin/core/crm/leads/${leadId}/status`, {
        new_status_id: newStatus,
        reason: 'Moved via Kanban pipeline',
      });
    } catch (err: any) {
      // Revert on failure
      console.error('Failed to move lead:', err);
      setLeads(prev => prev.map(l => l.id === leadId ? { ...l, status: oldStatus } : l));
    } finally {
      setUpdatingId(null);
    }
  };

  const handleDragEnd = () => {
    setDraggingId(null);
    setDragOverColumn(null);
  };

  // Touch drag for mobile
  const touchLeadRef = useRef<{ id: number; startX: number; startY: number } | null>(null);

  const getColumnValue = (statusCode: string) => {
    const columnLeads = getLeadsByStatus(statusCode);
    const total = columnLeads.reduce((sum, l) => sum + (l.estimated_value || 0), 0);
    return total;
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 sm:px-6 pt-4 sm:pt-6 shrink-0">
        <PageHeader
          title={t('pipeline.title') || 'Pipeline de Ventas'}
          subtitle={t('pipeline.subtitle') || 'Arrastra leads entre etapas para actualizar su estado'}
          icon={<LayoutGrid size={20} />}
          action={
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate('/crm/leads')}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-white/[0.06] text-white/60 border border-white/[0.08] hover:bg-white/[0.10] transition-all active:scale-95"
              >
                <List size={14} />
                Vista Lista
              </button>
              <button
                onClick={fetchData}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-all active:scale-95"
              >
                <RefreshCw size={14} />
                Actualizar
              </button>
            </div>
          }
        />
      </div>

      {/* Kanban Board */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-x-auto overflow-y-hidden px-4 sm:px-6 pb-4"
        style={{ scrollSnapType: 'x mandatory' }}
      >
        <div className="flex gap-3 h-full min-w-max">
          {statuses.map(status => {
            const columnLeads = getLeadsByStatus(status.code);
            const isOver = dragOverColumn === status.code;
            const totalValue = getColumnValue(status.code);

            return (
              <div
                key={status.code}
                className={`flex flex-col w-[280px] sm:w-[300px] shrink-0 rounded-2xl border transition-all duration-200
                  ${isOver
                    ? 'border-blue-500/40 bg-blue-500/[0.04] scale-[1.01]'
                    : 'border-white/[0.06] bg-white/[0.02]'
                  }
                `}
                style={{ scrollSnapAlign: 'start' }}
                onDragOver={(e) => handleDragOver(e, status.code)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, status.code)}
              >
                {/* Column Header */}
                <div className="px-3 py-3 border-b border-white/[0.04] shrink-0">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: status.color || '#6B7280' }}
                      />
                      <span className="text-sm font-semibold text-white">{status.name}</span>
                    </div>
                    <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-white/[0.06] text-white/50">
                      {columnLeads.length}
                    </span>
                  </div>
                  {totalValue > 0 && (
                    <div className="flex items-center gap-1 text-[10px] text-white/30">
                      <DollarSign size={10} />
                      <span>${totalValue.toLocaleString()}</span>
                    </div>
                  )}
                </div>

                {/* Column Cards */}
                <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-0">
                  {columnLeads.length === 0 ? (
                    <div className="flex items-center justify-center h-24 text-white/15 text-xs">
                      Sin leads
                    </div>
                  ) : (
                    columnLeads.map(lead => {
                      const days = getDaysInStage(lead);
                      const isDragging = draggingId === lead.id;
                      const isUpdating = updatingId === lead.id;

                      return (
                        <div
                          key={lead.id}
                          draggable
                          onDragStart={(e) => handleDragStart(e, lead.id)}
                          onDragEnd={handleDragEnd}
                          onClick={() => navigate(`/crm/leads/${lead.id}`)}
                          className={`group relative bg-white/[0.03] rounded-xl border border-white/[0.06] p-3 cursor-grab
                            hover:bg-white/[0.05] hover:border-white/[0.10]
                            active:cursor-grabbing active:scale-[0.97]
                            transition-all duration-200 touch-manipulation
                            ${isDragging ? 'opacity-40 scale-95' : ''}
                            ${isUpdating ? 'animate-pulse ring-2 ring-blue-500/30' : ''}
                          `}
                        >
                          {/* Drag handle */}
                          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-30 transition-opacity">
                            <GripVertical size={14} />
                          </div>

                          {/* Lead name */}
                          <div className="flex items-center gap-1.5 pr-6">
                            <h4 className="text-sm font-semibold text-white truncate">
                              {lead.first_name} {lead.last_name}
                            </h4>
                            <ScoreBadge score={lead.score} size="sm" />
                          </div>

                          {/* Phone */}
                          {lead.phone_number && (
                            <p className="text-[11px] text-white/40 truncate mt-0.5">
                              {lead.phone_number}
                            </p>
                          )}

                          {/* Meta row */}
                          <div className="flex items-center gap-3 mt-2 text-[10px] text-white/30">
                            {/* Seller */}
                            {lead.seller_name && (
                              <div className="flex items-center gap-1">
                                <User size={10} />
                                <span className="truncate max-w-[60px]">{lead.seller_name}</span>
                              </div>
                            )}

                            {/* Days in stage */}
                            <div className="flex items-center gap-1">
                              <Clock size={10} />
                              <span>{days}d</span>
                            </div>

                            {/* Value */}
                            {lead.estimated_value && lead.estimated_value > 0 && (
                              <div className="flex items-center gap-1 text-green-400/60">
                                <DollarSign size={10} />
                                <span>${lead.estimated_value.toLocaleString()}</span>
                              </div>
                            )}
                          </div>

                          {/* Source badge */}
                          {lead.source && (
                            <div className="mt-2">
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.04] text-white/25 uppercase font-bold">
                                {lead.source}
                              </span>
                            </div>
                          )}

                          {/* Tags */}
                          {parseTags(lead.tags).length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {parseTags(lead.tags).slice(0, 2).map(tag => (
                                <span key={tag} className="text-[9px] px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400/60">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
