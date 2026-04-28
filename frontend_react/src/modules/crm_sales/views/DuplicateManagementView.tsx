/**
 * DuplicateManagementView — DEV-50: Gestión de leads duplicados.
 * Split-view: izquierda lista de candidatos pending, derecha comparación lado a lado con acciones.
 * Solo accesible por rol CEO.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Copy, CheckCircle2, X, AlertTriangle, ChevronRight, RefreshCw } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../../api/axios';

const API_BASE = '/admin/core/crm/duplicates';

// ── Types ─────────────────────────────────────────────────────────────────────

interface DuplicateStats {
  pending: number;
  merged: number;
  dismissed: number;
}

interface LeadSnapshot {
  id: string;
  first_name: string | null;
  last_name: string | null;
  phone_number: string | null;
  email: string | null;
  status: string | null;
  source: string | null;
  company: string | null;
  estimated_value: number | null;
  created_at: string;
}

interface DuplicateCandidate {
  id: string;
  confidence: number;
  match_reasons: string[];
  status: 'pending' | 'merged' | 'dismissed';
  created_at: string;
  lead_a: LeadSnapshot;
  lead_b: LeadSnapshot;
}

interface DuplicateCandidateList {
  id: string;
  confidence: number;
  match_reasons: string[];
  status: string;
  created_at: string;
  lead_a_id: string;
  lead_b_id: string;
  lead_a_name: string | null;
  lead_b_name: string | null;
  lead_a_phone: string | null;
  lead_b_phone: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function confidenceColor(confidence: number): string {
  if (confidence >= 90) return 'bg-red-500/20 text-red-400 border-red-500/30';
  if (confidence >= 70) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
  return 'bg-white/[0.06] text-white/50 border-white/[0.08]';
}

function reasonLabel(reason: string): string {
  if (reason.startsWith('phone')) return 'teléfono';
  if (reason.startsWith('email')) return 'email';
  if (reason.startsWith('name')) return 'nombre';
  return reason;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return iso;
  }
}

function leadDisplayName(lead: LeadSnapshot | { first_name: string | null; last_name: string | null; phone_number: string | null }): string {
  const name = [lead.first_name, lead.last_name].filter(Boolean).join(' ').trim();
  return name || lead.phone_number || 'Sin nombre';
}

// ── Comparison field rows ─────────────────────────────────────────────────────

const COMPARISON_FIELDS: { key: keyof LeadSnapshot; label: string }[] = [
  { key: 'first_name', label: 'Nombre' },
  { key: 'last_name', label: 'Apellido' },
  { key: 'phone_number', label: 'Teléfono' },
  { key: 'email', label: 'Email' },
  { key: 'status', label: 'Estado' },
  { key: 'source', label: 'Origen' },
  { key: 'company', label: 'Empresa' },
  { key: 'estimated_value', label: 'Valor estimado' },
  { key: 'created_at', label: 'Creado' },
];

// ── Candidate list item ───────────────────────────────────────────────────────

interface CandidateItemProps {
  candidate: DuplicateCandidateList;
  isSelected: boolean;
  onClick: () => void;
}

const CandidateItem: React.FC<CandidateItemProps> = ({ candidate, isSelected, onClick }) => (
  <button
    onClick={onClick}
    className={`
      w-full text-left px-4 py-3 transition-colors border-b border-white/[0.04]
      ${isSelected
        ? 'bg-violet-500/10 border-l-2 border-l-violet-500'
        : 'hover:bg-white/[0.03]'
      }
    `}
  >
    <div className="flex items-start justify-between gap-2">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate">
          {candidate.lead_a_name || candidate.lead_a_phone || candidate.lead_a_id.slice(0, 8)}
          <span className="text-white/30 mx-1">vs</span>
          {candidate.lead_b_name || candidate.lead_b_phone || candidate.lead_b_id.slice(0, 8)}
        </p>
        <p className="text-xs text-white/40 mt-0.5">{formatDate(candidate.created_at)}</p>
        <div className="flex flex-wrap gap-1 mt-1.5">
          {candidate.match_reasons.slice(0, 3).map((r) => (
            <span key={r} className="px-1.5 py-0.5 rounded text-xs bg-white/[0.06] text-white/50">
              {reasonLabel(r)}
            </span>
          ))}
        </div>
      </div>
      <div className="flex flex-col items-end gap-1 shrink-0">
        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${confidenceColor(candidate.confidence)}`}>
          {candidate.confidence}%
        </span>
        <ChevronRight size={14} className="text-white/20" />
      </div>
    </div>
  </button>
);

// ── Comparison panel ─────────────────────────────────────────────────────────

interface ComparisonPanelProps {
  candidateId: string;
  onDone: () => void;
}

const ComparisonPanel: React.FC<ComparisonPanelProps> = ({ candidateId, onDone }) => {
  const queryClient = useQueryClient();
  const [fieldOverrides, setFieldOverrides] = useState<Record<string, 'a' | 'b'>>({});

  const { data: candidate, isLoading } = useQuery<DuplicateCandidate>({
    queryKey: ['duplicate-detail', candidateId],
    queryFn: async () => {
      const res = await api.get<DuplicateCandidate>(`${API_BASE}/${candidateId}`);
      return res.data;
    },
  });

  const mergeMutation = useMutation({
    mutationFn: async () => {
      if (!candidate) return;
      // Build field_overrides: pick from B when user selects B, otherwise keep A (primary)
      const overrides: Record<string, string> = {};
      if (candidate) {
        COMPARISON_FIELDS.forEach(({ key }) => {
          if (fieldOverrides[key] === 'b' && candidate.lead_b[key] !== null && candidate.lead_b[key] !== undefined) {
            overrides[key] = String(candidate.lead_b[key]);
          }
        });
      }
      await api.post(`${API_BASE}/${candidateId}/merge`, {
        primary_id: candidate.lead_a.id,
        secondary_id: candidate.lead_b.id,
        field_overrides: overrides,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['duplicates'] });
      queryClient.invalidateQueries({ queryKey: ['duplicate-stats'] });
      onDone();
    },
  });

  const dismissMutation = useMutation({
    mutationFn: async () => {
      await api.post(`${API_BASE}/${candidateId}/dismiss`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['duplicates'] });
      queryClient.invalidateQueries({ queryKey: ['duplicate-stats'] });
      onDone();
    },
  });

  if (isLoading || !candidate) {
    return (
      <div className="flex items-center justify-center h-full text-white/30 text-sm">
        Cargando comparación...
      </div>
    );
  }

  const a = candidate.lead_a;
  const b = candidate.lead_b;

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/[0.06] shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Comparar leads</h3>
            <p className="text-xs text-white/40 mt-0.5">
              Confianza: <span className={`font-medium ${candidate.confidence >= 90 ? 'text-red-400' : candidate.confidence >= 70 ? 'text-yellow-400' : 'text-white/50'}`}>{candidate.confidence}%</span>
              {' · '}
              Motivos: {candidate.match_reasons.map(reasonLabel).join(', ')}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => dismissMutation.mutate()}
              disabled={dismissMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white/50 hover:text-white bg-white/[0.05] hover:bg-white/[0.08] rounded-lg transition-colors border border-white/[0.08] disabled:opacity-40"
            >
              <X size={13} />
              Descartar
            </button>
            <button
              onClick={() => mergeMutation.mutate()}
              disabled={mergeMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-violet-600 hover:bg-violet-500 rounded-lg transition-colors disabled:opacity-40"
            >
              <CheckCircle2 size={13} />
              Fusionar
            </button>
          </div>
        </div>
        {(mergeMutation.isError || dismissMutation.isError) && (
          <p className="mt-2 text-xs text-red-400">
            Error al procesar. Intentá de nuevo.
          </p>
        )}
      </div>

      {/* Comparison table */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* Column headers */}
        <div className="grid grid-cols-[1fr_1fr_1fr] gap-0 sticky top-0 bg-[#0a0e1a] border-b border-white/[0.06] z-10">
          <div className="px-4 py-2 text-xs font-medium text-white/40 uppercase tracking-wider">Campo</div>
          <div className="px-4 py-2 text-xs font-medium text-violet-400 uppercase tracking-wider border-l border-white/[0.04]">
            Lead A (primario)
          </div>
          <div className="px-4 py-2 text-xs font-medium text-cyan-400 uppercase tracking-wider border-l border-white/[0.04]">
            Lead B (secundario)
          </div>
        </div>

        {COMPARISON_FIELDS.map(({ key, label }) => {
          const valA = a[key] !== null && a[key] !== undefined ? String(a[key]) : '—';
          const valB = b[key] !== null && b[key] !== undefined ? String(b[key]) : '—';
          const isDifferent = valA !== valB;
          const selectedChoice = fieldOverrides[key];

          return (
            <div
              key={key}
              className={`grid grid-cols-[1fr_1fr_1fr] gap-0 border-b border-white/[0.04] ${isDifferent ? 'bg-yellow-500/[0.03]' : ''}`}
            >
              <div className="px-4 py-2.5 text-xs text-white/40 flex items-center">
                {label}
                {isDifferent && <AlertTriangle size={11} className="ml-1.5 text-yellow-500/60" />}
              </div>

              {/* Lead A */}
              <div className={`px-4 py-2.5 border-l border-white/[0.04] flex items-center gap-2 ${isDifferent && selectedChoice === 'a' ? 'bg-violet-500/10' : ''}`}>
                <span className="text-sm text-white/80 flex-1 truncate">{valA}</span>
                {isDifferent && (
                  <input
                    type="radio"
                    name={`field-${key}`}
                    checked={selectedChoice === 'a' || (!selectedChoice)}
                    onChange={() => setFieldOverrides(prev => ({ ...prev, [key]: 'a' }))}
                    className="accent-violet-500 shrink-0"
                    title={`Usar valor de Lead A para ${label}`}
                  />
                )}
              </div>

              {/* Lead B */}
              <div className={`px-4 py-2.5 border-l border-white/[0.04] flex items-center gap-2 ${isDifferent && selectedChoice === 'b' ? 'bg-cyan-500/10' : ''}`}>
                <span className="text-sm text-white/80 flex-1 truncate">{valB}</span>
                {isDifferent && (
                  <input
                    type="radio"
                    name={`field-${key}`}
                    checked={selectedChoice === 'b'}
                    onChange={() => setFieldOverrides(prev => ({ ...prev, [key]: 'b' }))}
                    className="accent-cyan-500 shrink-0"
                    title={`Usar valor de Lead B para ${label}`}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ── Main View ─────────────────────────────────────────────────────────────────

export default function DuplicateManagementView() {
  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: stats } = useQuery<DuplicateStats>({
    queryKey: ['duplicate-stats'],
    queryFn: async () => {
      const res = await api.get<DuplicateStats>(`${API_BASE}/stats`);
      return res.data;
    },
    refetchInterval: 30_000,
  });

  const { data: candidates, isLoading, refetch } = useQuery<DuplicateCandidateList[]>({
    queryKey: ['duplicates'],
    queryFn: async () => {
      const res = await api.get<DuplicateCandidateList[]>(API_BASE, { params: { status: 'pending' } });
      return res.data;
    },
    refetchInterval: 60_000,
  });

  const handleDone = () => {
    setSelectedId(null);
    refetch();
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-4 p-4 lg:p-6 border-b border-white/[0.06] bg-white/[0.03] shrink-0">
        <div className="p-2 rounded-lg bg-white/[0.06]">
          <Copy size={18} className="text-violet-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-white">Gestión de Duplicados</h1>
          <p className="text-sm text-white/40">Detectados automáticamente por teléfono, email y nombre</p>
        </div>
        <button
          onClick={() => refetch()}
          className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/[0.04] transition-colors"
          title="Actualizar"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Stats bar */}
      <div className="flex gap-4 px-4 lg:px-6 py-3 border-b border-white/[0.06] bg-white/[0.02] shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/40">Pendientes</span>
          <span className="text-sm font-semibold text-yellow-400">{stats?.pending ?? '—'}</span>
        </div>
        <div className="w-px bg-white/[0.06]" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/40">Fusionados</span>
          <span className="text-sm font-semibold text-emerald-400">{stats?.merged ?? '—'}</span>
        </div>
        <div className="w-px bg-white/[0.06]" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/40">Descartados</span>
          <span className="text-sm font-semibold text-white/50">{stats?.dismissed ?? '—'}</span>
        </div>
      </div>

      {/* Split view */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Left panel — candidate list */}
        <div className="w-80 shrink-0 border-r border-white/[0.06] flex flex-col min-h-0">
          <div className="px-4 py-2 border-b border-white/[0.04] shrink-0">
            <p className="text-xs text-white/30 uppercase tracking-wider font-medium">Candidatos pendientes</p>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto">
            {isLoading && (
              <div className="flex items-center justify-center h-32 text-white/30 text-sm">
                Cargando...
              </div>
            )}

            {!isLoading && (!candidates || candidates.length === 0) && (
              <div className="flex flex-col items-center justify-center h-48 gap-3 text-white/30">
                <CheckCircle2 size={32} className="text-emerald-500/40" />
                <p className="text-sm">No hay duplicados pendientes</p>
              </div>
            )}

            {!isLoading && candidates && candidates.map((c) => (
              <CandidateItem
                key={c.id}
                candidate={c}
                isSelected={selectedId === c.id}
                onClick={() => setSelectedId(c.id)}
              />
            ))}
          </div>
        </div>

        {/* Right panel — comparison or empty state */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {selectedId ? (
            <ComparisonPanel
              key={selectedId}
              candidateId={selectedId}
              onDone={handleDone}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-white/20">
              <Copy size={40} className="opacity-30" />
              <p className="text-sm">Seleccioná un candidato para comparar</p>
              <button
                onClick={() => navigate('/crm/leads')}
                className="mt-2 text-xs text-violet-400/60 hover:text-violet-400 transition-colors"
              >
                Ir a Leads →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
