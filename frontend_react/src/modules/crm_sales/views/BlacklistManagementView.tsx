/**
 * BlacklistManagementView — DEV-55: Gestión de blacklist de contactos.
 * Tabs: Blacklist CRUD | Intentos bloqueados | Estadísticas
 * Solo accesible por rol CEO.
 */
import { useState } from 'react';
import {
  Shield, Plus, Trash2, AlertCircle, Phone, Mail, RefreshCw,
  Clock, BarChart3, ChevronDown, X, Ban
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../../api/axios';

// ── Constants ─────────────────────────────────────────────────────────────────

const API_BASE = '/admin/core/blacklist';

const PREDEFINED_REASONS = [
  { value: 'lead_descartado', label: 'Lead descartado definitivo' },
  { value: 'ex_cliente', label: 'Ex cliente' },
  { value: 'spam', label: 'Spam' },
  { value: 'numero_invalido', label: 'Número inválido' },
  { value: 'no_contactar', label: 'Solicitud de no contacto' },
];

// ── Types ──────────────────────────────────────────────────────────────────────

interface BlacklistItem {
  id: string;
  value: string;
  type: string;
  reason: string | null;
  created_at: string;
}

interface BlacklistAttempt {
  id: string;
  value: string;
  type: string;
  source: string;
  payload: Record<string, unknown>;
  created_at: string;
}

interface AttemptsResponse {
  items: BlacklistAttempt[];
  total: number;
  limit: number;
  offset: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function detectType(value: string): 'phone' | 'email' | 'domain' {
  if (value.includes('@')) return 'email';
  if (value.startsWith('http') || (value.includes('.') && !value.match(/^\d/))) return 'domain';
  return 'phone';
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('es-AR', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function formatDatetime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('es-AR', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function reasonLabel(reason: string | null): string {
  if (!reason) return '-';
  return PREDEFINED_REASONS.find(r => r.value === reason)?.label || reason;
}

function typeIcon(type: string) {
  if (type === 'email') return <Mail size={13} className="text-blue-400" />;
  if (type === 'phone') return <Phone size={13} className="text-green-400" />;
  return <Shield size={13} className="text-white/40" />;
}

function typeBadge(type: string) {
  const base = 'px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border';
  if (type === 'phone') return `${base} bg-green-500/10 text-green-400 border-green-500/20`;
  if (type === 'email') return `${base} bg-blue-500/10 text-blue-400 border-blue-500/20`;
  return `${base} bg-white/[0.06] text-white/40 border-white/[0.08]`;
}

// ── Add Form ──────────────────────────────────────────────────────────────────

interface AddFormProps {
  onAdded: () => void;
}

function AddForm({ onAdded }: AddFormProps) {
  const [value, setValue] = useState('');
  const [reason, setReason] = useState('lead_descartado');
  const [customReason, setCustomReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    setLoading(true);
    setError(null);
    const type = detectType(value.trim());
    const finalReason = reason === '_custom' ? customReason : reason;
    try {
      await api.post(API_BASE, {
        value: value.trim(),
        type,
        reason: finalReason || undefined,
      });
      setValue('');
      setReason('lead_descartado');
      setCustomReason('');
      onAdded();
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Error al agregar';
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-5 bg-white/[0.02] border border-white/[0.06] rounded-2xl space-y-4">
      <p className="text-xs font-bold text-white/40 uppercase tracking-wider">Agregar a blacklist</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="space-y-1.5">
          <label className="text-xs text-white/40">Teléfono o Email *</label>
          <div className="relative">
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="54911... o user@mail.com"
              required
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:border-red-500/50 outline-none"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1 opacity-20">
              <Phone size={11} /><Mail size={11} />
            </div>
          </div>
        </div>
        <div className="space-y-1.5">
          <label className="text-xs text-white/40">Motivo</label>
          <div className="relative">
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:border-red-500/50 outline-none appearance-none"
            >
              {PREDEFINED_REASONS.map((r) => (
                <option key={r.value} value={r.value} className="bg-[#0a0e1a]">{r.label}</option>
              ))}
              <option value="_custom" className="bg-[#0a0e1a]">Otro (personalizado)</option>
            </select>
            <ChevronDown size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
          </div>
        </div>
        {reason === '_custom' ? (
          <div className="space-y-1.5">
            <label className="text-xs text-white/40">Motivo personalizado</label>
            <input
              type="text"
              value={customReason}
              onChange={(e) => setCustomReason(e.target.value)}
              placeholder="Describe el motivo..."
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:border-red-500/50 outline-none"
            />
          </div>
        ) : (
          <div className="flex items-end">
            <button
              type="submit"
              disabled={loading || !value.trim()}
              className="w-full h-[38px] bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-bold flex items-center justify-center gap-2 transition-all active:scale-95"
            >
              <Plus size={15} />
              {loading ? 'Agregando...' : 'Bloquear'}
            </button>
          </div>
        )}
      </div>
      {reason === '_custom' && (
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="h-[38px] px-6 bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-bold flex items-center gap-2 transition-all active:scale-95"
        >
          <Plus size={15} />
          {loading ? 'Agregando...' : 'Bloquear'}
        </button>
      )}
      {error && (
        <p className="text-xs text-red-400 flex items-center gap-1.5">
          <AlertCircle size={13} />{error}
        </p>
      )}
    </form>
  );
}

// ── Blacklist Tab ─────────────────────────────────────────────────────────────

function BlacklistTab() {
  const queryClient = useQueryClient();

  const { data: items = [], isLoading, refetch } = useQuery<BlacklistItem[]>({
    queryKey: ['blacklist'],
    queryFn: async () => {
      const { data } = await api.get(API_BASE);
      return data;
    },
  });

  const removeMutation = useMutation({
    mutationFn: (value: string) => api.delete(`${API_BASE}/${encodeURIComponent(value)}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['blacklist'] }),
  });

  const phoneCount = items.filter(i => i.type === 'phone').length;
  const emailCount = items.filter(i => i.type === 'email').length;

  return (
    <div className="space-y-5">
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl text-center">
          <p className="text-2xl font-bold text-white">{items.length}</p>
          <p className="text-xs text-white/40 mt-0.5">Total bloqueados</p>
        </div>
        <div className="p-4 bg-green-500/5 border border-green-500/10 rounded-xl text-center">
          <p className="text-2xl font-bold text-green-400">{phoneCount}</p>
          <p className="text-xs text-white/40 mt-0.5">Teléfonos</p>
        </div>
        <div className="p-4 bg-blue-500/5 border border-blue-500/10 rounded-xl text-center">
          <p className="text-2xl font-bold text-blue-400">{emailCount}</p>
          <p className="text-xs text-white/40 mt-0.5">Emails</p>
        </div>
      </div>

      <AddForm onAdded={() => refetch()} />

      {/* List */}
      <div className="bg-white/[0.02] rounded-2xl border border-white/5 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04]">
          <span className="text-xs font-bold text-white/40 uppercase tracking-wider">
            {items.length} registros
          </span>
          <button
            onClick={() => refetch()}
            className="p-1.5 text-white/30 hover:text-white/70 hover:bg-white/[0.04] rounded-lg transition-all"
            title="Actualizar"
          >
            <RefreshCw size={13} />
          </button>
        </div>
        {isLoading ? (
          <div className="py-12 text-center text-white/30 text-sm">Cargando...</div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center opacity-30">
            <Shield size={32} className="mx-auto mb-2" />
            <p className="text-sm">Blacklist vacía</p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.01]">
                <th className="px-5 py-3 text-[10px] font-bold text-white/30 uppercase tracking-wider">Tipo</th>
                <th className="px-5 py-3 text-[10px] font-bold text-white/30 uppercase tracking-wider">Valor</th>
                <th className="px-5 py-3 text-[10px] font-bold text-white/30 uppercase tracking-wider">Motivo</th>
                <th className="px-5 py-3 text-[10px] font-bold text-white/30 uppercase tracking-wider">Fecha</th>
                <th className="px-5 py-3 text-[10px] font-bold text-white/30 uppercase tracking-wider text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03]">
              {items.map((item) => (
                <tr key={item.id || item.value} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-1.5">
                      {typeIcon(item.type)}
                      <span className={typeBadge(item.type)}>{item.type}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <span className="text-sm font-mono text-white">{item.value}</span>
                  </td>
                  <td className="px-5 py-3">
                    <span className="text-sm text-white/50">{reasonLabel(item.reason)}</span>
                  </td>
                  <td className="px-5 py-3 text-xs text-white/30">
                    {formatDate(item.created_at)}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => removeMutation.mutate(item.value)}
                      disabled={removeMutation.isPending}
                      className="p-1.5 text-white/20 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                      title="Quitar de blacklist"
                    >
                      <X size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Warning */}
      <div className="flex items-start gap-3 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
        <AlertCircle size={16} className="text-yellow-500 shrink-0 mt-0.5" />
        <p className="text-xs text-yellow-500/80 leading-relaxed">
          <strong>Importante:</strong> Los contactos bloqueados no pueden generar leads ni pasar por el webhook de entrada. El sistema verifica teléfono raw y normalizado (E.164).
        </p>
      </div>
    </div>
  );
}

// ── Attempts Tab ─────────────────────────────────────────────────────────────

function AttemptsTab() {
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data, isLoading, refetch } = useQuery<AttemptsResponse>({
    queryKey: ['blacklist-attempts', page],
    queryFn: async () => {
      const { data } = await api.get(`${API_BASE}/attempts`, {
        params: { limit, offset: page * limit },
      });
      return data;
    },
  });

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-white/70">
            <span className="font-bold text-white">{total}</span> intentos bloqueados registrados
          </p>
          <p className="text-xs text-white/30 mt-0.5">Cada vez que un contacto bloqueado intenta generar un lead</p>
        </div>
        <button
          onClick={() => refetch()}
          className="p-2 text-white/30 hover:text-white/70 hover:bg-white/[0.04] rounded-lg transition-all"
          title="Actualizar"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      <div className="bg-white/[0.02] rounded-2xl border border-white/5 overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-white/30 text-sm">Cargando intentos...</div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center opacity-30">
            <Clock size={32} className="mx-auto mb-2" />
            <p className="text-sm">Sin intentos registrados</p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.01]">
                <th className="px-5 py-3 text-[10px] font-bold text-white/30 uppercase tracking-wider">Tipo</th>
                <th className="px-5 py-3 text-[10px] font-bold text-white/30 uppercase tracking-wider">Valor</th>
                <th className="px-5 py-3 text-[10px] font-bold text-white/30 uppercase tracking-wider">Fuente</th>
                <th className="px-5 py-3 text-[10px] font-bold text-white/30 uppercase tracking-wider">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03]">
              {items.map((attempt) => (
                <tr key={attempt.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-1.5">
                      {typeIcon(attempt.type)}
                      <span className={typeBadge(attempt.type)}>{attempt.type}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <span className="text-sm font-mono text-white">{attempt.value}</span>
                  </td>
                  <td className="px-5 py-3">
                    <span className="px-2 py-0.5 rounded text-xs bg-white/[0.05] text-white/50 border border-white/[0.06]">
                      {attempt.source}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-xs text-white/30">
                    {formatDatetime(attempt.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1.5 text-xs bg-white/5 border border-white/10 rounded-lg text-white/60 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Anterior
          </button>
          <span className="text-xs text-white/40">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1.5 text-xs bg-white/5 border border-white/10 rounded-lg text-white/60 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  );
}

// ── Stats Tab ────────────────────────────────────────────────────────────────

function StatsTab() {
  const { data: blacklist = [] } = useQuery<BlacklistItem[]>({
    queryKey: ['blacklist'],
    queryFn: async () => {
      const { data } = await api.get(API_BASE);
      return data;
    },
  });
  const { data: attemptsData } = useQuery<AttemptsResponse>({
    queryKey: ['blacklist-attempts', 0],
    queryFn: async () => {
      const { data } = await api.get(`${API_BASE}/attempts`, { params: { limit: 1, offset: 0 } });
      return data;
    },
  });

  // Reason breakdown
  const reasonCounts: Record<string, number> = {};
  blacklist.forEach(item => {
    const key = item.reason || 'sin_motivo';
    reasonCounts[key] = (reasonCounts[key] || 0) + 1;
  });
  const reasonEntries = Object.entries(reasonCounts).sort((a, b) => b[1] - a[1]);

  // Source breakdown from attempts would need more data — show simple view
  const phoneCount = blacklist.filter(i => i.type === 'phone').length;
  const emailCount = blacklist.filter(i => i.type === 'email').length;
  const domainCount = blacklist.filter(i => i.type === 'domain').length;

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-4 bg-red-500/5 border border-red-500/10 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <Ban size={16} className="text-red-400" />
            <span className="text-xs text-white/40 uppercase font-bold">Total</span>
          </div>
          <p className="text-2xl font-bold text-white">{blacklist.length}</p>
          <p className="text-xs text-white/30 mt-0.5">entradas bloqueadas</p>
        </div>
        <div className="p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={16} className="text-yellow-400" />
            <span className="text-xs text-white/40 uppercase font-bold">Intentos</span>
          </div>
          <p className="text-2xl font-bold text-white">{attemptsData?.total || 0}</p>
          <p className="text-xs text-white/30 mt-0.5">bloqueados histórico</p>
        </div>
        <div className="p-4 bg-green-500/5 border border-green-500/10 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <Phone size={16} className="text-green-400" />
            <span className="text-xs text-white/40 uppercase font-bold">Teléfonos</span>
          </div>
          <p className="text-2xl font-bold text-green-400">{phoneCount}</p>
        </div>
        <div className="p-4 bg-blue-500/5 border border-blue-500/10 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <Mail size={16} className="text-blue-400" />
            <span className="text-xs text-white/40 uppercase font-bold">Emails</span>
          </div>
          <p className="text-2xl font-bold text-blue-400">{emailCount}</p>
        </div>
      </div>

      {/* Reason breakdown */}
      <div className="p-5 bg-white/[0.02] border border-white/[0.06] rounded-2xl">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={16} className="text-violet-400" />
          <p className="text-sm font-bold text-white">Distribución por motivo</p>
        </div>
        {reasonEntries.length === 0 ? (
          <p className="text-sm text-white/30 text-center py-4">Sin datos</p>
        ) : (
          <div className="space-y-2">
            {reasonEntries.map(([reason, count]) => (
              <div key={reason} className="flex items-center gap-3">
                <div className="w-32 text-xs text-white/50 truncate shrink-0">
                  {PREDEFINED_REASONS.find(r => r.value === reason)?.label || reason}
                </div>
                <div className="flex-1 bg-white/[0.04] rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full bg-red-500/60 rounded-full"
                    style={{ width: `${(count / blacklist.length) * 100}%` }}
                  />
                </div>
                <div className="text-xs font-bold text-white/60 w-6 text-right">{count}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {domainCount > 0 && (
        <div className="p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl">
          <p className="text-xs text-white/40">Dominios bloqueados: <span className="text-white font-bold">{domainCount}</span></p>
        </div>
      )}
    </div>
  );
}

// ── Main View ─────────────────────────────────────────────────────────────────

type Tab = 'blacklist' | 'attempts' | 'stats';

export default function BlacklistManagementView() {
  const [activeTab, setActiveTab] = useState<Tab>('blacklist');

  const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'blacklist', label: 'Blacklist', icon: <Shield size={15} /> },
    { id: 'attempts', label: 'Intentos bloqueados', icon: <Clock size={15} /> },
    { id: 'stats', label: 'Estadísticas', icon: <BarChart3 size={15} /> },
  ];

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-4 p-4 lg:p-6 border-b border-white/[0.06] bg-white/[0.03] shrink-0">
        <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center shrink-0">
          <Shield size={20} className="text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-white">Blacklist</h1>
          <p className="text-sm text-white/40">Gestión de contactos bloqueados del tenant</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="shrink-0 flex border-b border-white/[0.06] bg-white/[0.02] px-4 lg:px-6">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? 'text-white border-red-500'
                : 'text-white/40 border-transparent hover:text-white/70'
            }`}
          >
            <span className={activeTab === tab.id ? 'text-red-400' : 'text-white/30'}>
              {tab.icon}
            </span>
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6">
        {activeTab === 'blacklist' && <BlacklistTab />}
        {activeTab === 'attempts' && <AttemptsTab />}
        {activeTab === 'stats' && <StatsTab />}
      </div>
    </div>
  );
}
