import { useState, useEffect } from 'react';
import { AlertTriangle, RefreshCw, CheckCircle, Clock, User, Phone, ArrowUp } from 'lucide-react';
import api from '../../../api/axios';
import PageHeader from '../../../components/PageHeader';
import { useTranslation } from '../../../context/LanguageContext';

interface Violation {
  rule_id: string;
  rule_name: string;
  trigger_type: string;
  lead_id: string;
  lead_name: string;
  seller_id: string | null;
  seller_name: string;
  threshold_minutes: number;
  minutes_exceeded: number;
  escalate_to_ceo: boolean;
  should_escalate: boolean;
}

export default function SlaViolationsView() {
  const { t } = useTranslation();
  const [violations, setViolations] = useState<Violation[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchViolations = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/core/sla-rules/violations');
      setViolations(res.data.violations);
    } catch (e) {
      console.error('Error fetching violations', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchViolations(); }, []);

  const triggerLabel = (t: string) =>
    t === 'first_response' ? 'Primera respuesta' : t === 'follow_up' ? 'Seguimiento' : t;

  return (
    <div className="h-full flex flex-col bg-[#0a0e1a]">
      <PageHeader
        title="Violaciones SLA"
        subtitle="Monitoreá en tiempo real los leads que excedieron los tiempos límite configurados"
      >
        <button onClick={fetchViolations}
          className="flex items-center gap-2 px-4 py-2 bg-white/[0.06] hover:bg-white/[0.1] rounded-lg text-sm font-medium transition-colors">
          <RefreshCw size={16} /> Actualizar
        </button>
      </PageHeader>

      <div className="flex-1 p-6 overflow-y-auto">
        {/* Stats summary */}
        {!loading && violations.length > 0 && (
          <div className="flex gap-4 mb-6">
            <div className="flex-1 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
              <p className="text-2xl font-bold text-red-400">{violations.length}</p>
              <p className="text-xs text-white/40 mt-1">Violaciones activas</p>
            </div>
            <div className="flex-1 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4">
              <p className="text-2xl font-bold text-yellow-400">{violations.filter(v => v.should_escalate).length}</p>
              <p className="text-xs text-white/40 mt-1">Escaladas a CEO</p>
            </div>
            <div className="flex-1 bg-white/[0.04] border border-white/[0.06] rounded-xl p-4">
              <p className="text-2xl font-bold text-white">{new Set(violations.map(v => v.rule_name)).size}</p>
              <p className="text-xs text-white/40 mt-1">Reglas afectadas</p>
            </div>
          </div>
        )}

        {loading && <div className="text-white/40 text-center py-16">Cargando violaciones...</div>}

        {!loading && violations.length === 0 && (
          <div className="text-center py-20">
            <CheckCircle size={48} className="mx-auto mb-4 text-green-400/60" />
            <p className="text-white/60 text-lg">No hay violaciones activas</p>
            <p className="text-white/30 text-sm mt-1">Todos los leads están dentro de los tiempos SLA configurados</p>
          </div>
        )}

        {!loading && violations.length > 0 && (
          <div className="space-y-3">
            {violations.map((v, i) => (
              <div key={`${v.lead_id}-${v.rule_id}-${i}`}
                className="bg-white/[0.04] rounded-xl p-4 border border-white/[0.06] flex items-start gap-4">
                <div className={`p-2 rounded-lg shrink-0 ${v.should_escalate ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                  <AlertTriangle size={18} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-white font-semibold">{v.lead_name}</h3>
                    <span className="text-xs px-2 py-0.5 rounded bg-white/[0.06] text-white/50">
                      {triggerLabel(v.trigger_type)}
                    </span>
                    {v.should_escalate && (
                      <span className="text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400 flex items-center gap-1">
                        <ArrowUp size={12} /> Escalado
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-white/40">
                    <span className="flex items-center gap-1"><Clock size={13} /> {v.minutes_exceeded} min excedido (límite: {v.threshold_minutes} min)</span>
                    {v.seller_name && <span className="flex items-center gap-1"><User size={13} /> {v.seller_name}</span>}
                  </div>
                  <p className="text-xs text-white/30 mt-1">Regla: {v.rule_name}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
