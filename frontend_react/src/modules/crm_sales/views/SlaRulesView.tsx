import { useState } from 'react';
import { Plus, Edit2, Trash2, AlertTriangle, RefreshCw, CheckCircle, X } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../../api/axios';
import PageHeader from '../../../components/PageHeader';
import { useTranslation } from '../../../context/LanguageContext';

const API_BASE = '/admin/core/sla-rules';

interface SlaRule {
  id: string;
  name: string;
  description: string | null;
  trigger_type: string;
  threshold_minutes: number;
  applies_to_statuses: string[] | null;
  applies_to_roles: string[] | null;
  escalate_to_ceo: boolean;
  escalate_after_minutes: number;
  is_active: boolean;
  created_at: string;
}

interface RuleForm {
  name: string;
  description: string;
  trigger_type: string;
  threshold_minutes: number;
  escalate_to_ceo: boolean;
  escalate_after_minutes: number;
  is_active: boolean;
}

const emptyForm: RuleForm = {
  name: '', description: '', trigger_type: 'first_response',
  threshold_minutes: 60, escalate_to_ceo: true,
  escalate_after_minutes: 30, is_active: true,
};

export default function SlaRulesView() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<RuleForm>(emptyForm);

  const { data, isLoading, error } = useQuery({
    queryKey: ['sla-rules'],
    queryFn: () => api.get(API_BASE).then(r => r.data.rules as SlaRule[]),
  });

  const saveMutation = useMutation({
    mutationFn: (payload: { id?: string; data: RuleForm }) =>
      payload.id
        ? api.put(`${API_BASE}/${payload.id}`, payload.data)
        : api.post(API_BASE, payload.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sla-rules'] });
      setShowForm(false);
      setEditingId(null);
      setForm(emptyForm);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`${API_BASE}/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sla-rules'] }),
  });

  const triggerLabel = (t: string) =>
    t === 'first_response' ? 'Primera respuesta' : t === 'follow_up' ? 'Seguimiento' : t;

  return (
    <div className="h-full flex flex-col bg-[#0a0e1a]">
      <PageHeader
        title="Reglas SLA"
        subtitle="Configura las reglas de SLA para monitorear tiempos de respuesta y seguimiento de leads"
      >
        <button onClick={() => { setShowForm(true); setEditingId(null); setForm(emptyForm); }}
          className="flex items-center gap-2 px-4 py-2 bg-[#8F3DFF] hover:bg-[#7c2ee6] rounded-lg text-sm font-medium transition-colors">
          <Plus size={16} /> Nueva regla
        </button>
      </PageHeader>

      <div className="flex-1 p-6 overflow-y-auto">
        {isLoading && <div className="text-white/40 text-center py-10">Cargando...</div>}
        {error && <div className="text-red-400 text-center py-10">Error al cargar reglas</div>}

        {!isLoading && data && (
          <div className="space-y-4">
            {data.length === 0 && (
              <div className="text-white/30 text-center py-16">
                <AlertTriangle size={40} className="mx-auto mb-3 opacity-30" />
                <p>No hay reglas SLA configuradas</p>
                <p className="text-sm mt-1">Creá la primera regla para empezar a monitorear</p>
              </div>
            )}

            {data.map(rule => (
              <div key={rule.id}
                className="bg-white/[0.04] rounded-xl p-5 border border-white/[0.06] flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-white font-semibold">{rule.name}</h3>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${rule.is_active ? 'bg-green-500/20 text-green-400' : 'bg-white/[0.06] text-white/40'}`}>
                      {rule.is_active ? 'Activa' : 'Inactiva'}
                    </span>
                  </div>
                  {rule.description && <p className="text-white/40 text-sm mt-1">{rule.description}</p>}
                  <div className="flex gap-4 mt-3 text-sm text-white/50">
                    <span>Disparador: <strong className="text-white/70">{triggerLabel(rule.trigger_type)}</strong></span>
                    <span>Límite: <strong className="text-white/70">{rule.threshold_minutes} min</strong></span>
                    <span>Escalar a CEO: <strong className="text-white/70">{rule.escalate_to_ceo ? `sí (${rule.escalate_after_minutes} min)` : 'no'}</strong></span>
                  </div>
                </div>
                <div className="flex gap-2 ml-4">
                  <button onClick={() => { setEditingId(rule.id); setForm({ name: rule.name, description: rule.description || '', trigger_type: rule.trigger_type, threshold_minutes: rule.threshold_minutes, escalate_to_ceo: rule.escalate_to_ceo, escalate_after_minutes: rule.escalate_after_minutes, is_active: rule.is_active }); setShowForm(true); }}
                    className="p-2 rounded-lg hover:bg-white/[0.08] text-white/40 hover:text-white transition-colors">
                    <Edit2 size={16} />
                  </button>
                  <button onClick={() => deleteMutation.mutate(rule.id)}
                    className="p-2 rounded-lg hover:bg-red-500/20 text-white/40 hover:text-red-400 transition-colors">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          onClick={() => setShowForm(false)}>
          <div className="bg-[#0d1117] rounded-2xl border border-white/[0.08] p-6 w-full max-w-lg"
            onClick={e => e.stopPropagation()}>
            <h2 className="text-white text-lg font-semibold mb-4">
              {editingId ? 'Editar regla' : 'Nueva regla SLA'}
            </h2>
            <div className="space-y-3">
              <input placeholder="Nombre" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 bg-white/[0.06] border border-white/[0.08] rounded-lg text-white text-sm placeholder-white/30" />
              <input placeholder="Descripción (opcional)" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 bg-white/[0.06] border border-white/[0.08] rounded-lg text-white text-sm placeholder-white/30" />
              <div className="flex gap-3">
                <select value={form.trigger_type} onChange={e => setForm({ ...form, trigger_type: e.target.value })}
                  className="flex-1 px-3 py-2 bg-white/[0.06] border border-white/[0.08] rounded-lg text-white text-sm">
                  <option value="first_response">Primera respuesta</option>
                  <option value="follow_up">Seguimiento</option>
                </select>
                <input type="number" placeholder="Límite (min)" value={form.threshold_minutes} onChange={e => setForm({ ...form, threshold_minutes: +e.target.value })}
                  className="w-28 px-3 py-2 bg-white/[0.06] border border-white/[0.08] rounded-lg text-white text-sm" />
              </div>
              <label className="flex items-center gap-2 text-sm text-white/60">
                <input type="checkbox" checked={form.escalate_to_ceo} onChange={e => setForm({ ...form, escalate_to_ceo: e.target.checked })}
                  className="accent-[#8F3DFF]" />
                Escalar a CEO {form.escalate_to_ceo && (
                  <span className="text-white/40">después de
                    <input type="number" value={form.escalate_after_minutes} onChange={e => setForm({ ...form, escalate_after_minutes: +e.target.value })}
                      className="w-16 mx-1 px-2 py-0.5 bg-white/[0.06] rounded text-white text-center text-sm" /> min
                  </span>
                )}
              </label>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <button onClick={() => setShowForm(false)}
                className="px-4 py-2 rounded-lg text-sm text-white/50 hover:text-white transition-colors">Cancelar</button>
              <button onClick={() => saveMutation.mutate({ id: editingId || undefined, data: form })}
                className="px-4 py-2 bg-[#8F3DFF] hover:bg-[#7c2ee6] rounded-lg text-sm font-medium transition-colors">
                {editingId ? 'Guardar' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
