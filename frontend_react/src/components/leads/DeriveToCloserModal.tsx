import { useState, useEffect } from 'react';
import { X, ArrowRight, Loader2, Save, Users } from 'lucide-react';
import api from '../../api/axios';

interface Closer {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

interface DeriveToCloserModalProps {
  leadId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function DeriveToCloserModal({ leadId, onClose, onSuccess }: DeriveToCloserModalProps) {
  const [closers, setClosers] = useState<Closer[]>([]);
  const [loadingClosers, setLoadingClosers] = useState(true);
  const [selectedCloser, setSelectedCloser] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    handoff_note: '',
    prospect_wants: '',
    budget: '',
    objections: '',
    next_steps: '',
  });

  useEffect(() => {
    const fetchClosers = async () => {
      try {
        setLoadingClosers(true);
        const res = await api.get<Closer[]>('/admin/core/sellers', {
          params: { role: 'closer' },
        });
        setClosers(res.data || []);
      } catch (err: any) {
        setError('No se pudieron cargar los closers');
      } finally {
        setLoadingClosers(false);
      }
    };
    fetchClosers();
  }, []);

  const handleSubmit = async () => {
    if (!selectedCloser) {
      setError('Selecciona un closer');
      return;
    }
    try {
      setSubmitting(true);
      setError(null);
      await api.post(`/admin/core/crm/leads/${leadId}/derive`, {
        closer_id: selectedCloser,
        handoff_note: form.handoff_note,
        prospect_wants: form.prospect_wants || undefined,
        budget: form.budget || undefined,
        objections: form.objections || undefined,
        next_steps: form.next_steps || undefined,
      });
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al derivar el lead');
    } finally {
      setSubmitting(false);
    }
  };

  const getCloserLabel = (c: Closer) => {
    const name = [c.first_name, c.last_name].filter(Boolean).join(' ');
    return name || c.email;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-[#1a1a2e] border border-white/[0.08] rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-white/[0.06] shrink-0">
          <div className="flex items-center gap-2">
            <ArrowRight size={18} className="text-violet-400" />
            <h2 className="text-lg font-semibold text-white">Derivar a Closer</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/[0.06] text-white/40 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs">
              {error}
            </div>
          )}

          {/* Closer selector */}
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Users size={13} className="text-white/40" />
                Closer asignado *
              </span>
            </label>
            {loadingClosers ? (
              <div className="flex items-center gap-2 text-white/30 text-sm py-2">
                <Loader2 size={14} className="animate-spin" />
                Cargando closers...
              </div>
            ) : (
              <select
                value={selectedCloser}
                onChange={(e) => setSelectedCloser(e.target.value)}
                className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/40"
              >
                <option value="" className="bg-[#1a1a2e] text-white">Seleccionar closer...</option>
                {closers.map((c) => (
                  <option key={c.id} value={c.id} className="bg-[#1a1a2e] text-white">{getCloserLabel(c)}</option>
                ))}
              </select>
            )}
          </div>

          {/* Handoff note */}
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1.5">Nota de handoff</label>
            <textarea
              value={form.handoff_note}
              onChange={(e) => setForm((f) => ({ ...f, handoff_note: e.target.value }))}
              rows={3}
              placeholder="Contexto para el closer sobre esta conversacion..."
              className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-white/30 focus:ring-2 focus:ring-violet-500/40 resize-none"
            />
          </div>

          {/* Structured fields */}
          <div className="p-3 bg-white/[0.02] border border-white/[0.04] rounded-xl space-y-3">
            <p className="text-xs font-medium text-white/40 uppercase tracking-wider">Informacion estructurada</p>

            <div>
              <label className="block text-xs font-medium text-white/50 mb-1">Que busca el prospecto</label>
              <input
                type="text"
                value={form.prospect_wants}
                onChange={(e) => setForm((f) => ({ ...f, prospect_wants: e.target.value }))}
                placeholder="Servicio o producto que le interesa..."
                className="w-full px-3 py-1.5 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-white/25 focus:ring-2 focus:ring-violet-500/40"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-white/50 mb-1">Presupuesto</label>
              <input
                type="text"
                value={form.budget}
                onChange={(e) => setForm((f) => ({ ...f, budget: e.target.value }))}
                placeholder="Rango de presupuesto estimado..."
                className="w-full px-3 py-1.5 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-white/25 focus:ring-2 focus:ring-violet-500/40"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-white/50 mb-1">Objeciones detectadas</label>
              <textarea
                value={form.objections}
                onChange={(e) => setForm((f) => ({ ...f, objections: e.target.value }))}
                rows={2}
                placeholder="Dudas o resistencias que mostro..."
                className="w-full px-3 py-1.5 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-white/25 focus:ring-2 focus:ring-violet-500/40 resize-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-white/50 mb-1">Proximos pasos sugeridos</label>
              <input
                type="text"
                value={form.next_steps}
                onChange={(e) => setForm((f) => ({ ...f, next_steps: e.target.value }))}
                placeholder="Que deberia hacer el closer..."
                className="w-full px-3 py-1.5 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-white/25 focus:ring-2 focus:ring-violet-500/40"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-5 border-t border-white/[0.06] shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white/50 hover:text-white bg-white/[0.03] hover:bg-white/[0.06] rounded-lg border border-white/[0.06] transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!selectedCloser || submitting}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg disabled:opacity-50 transition-colors"
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
            Derivar a closer
          </button>
        </div>
      </div>
    </div>
  );
}
