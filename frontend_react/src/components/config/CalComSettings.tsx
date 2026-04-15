import { useState, useEffect } from 'react';
import { Calendar, Link2, ExternalLink, ShieldCheck, AlertCircle, Copy, CheckCircle2 } from 'lucide-react';
import api from '../../api/axios';
import GlassCard from '../GlassCard';

export default function CalComSettings() {
  const [webhookUrl, setWebhookUrl] = useState('');
  const [tenantId, setTenantId] = useState<number | null>(null);
  const [tenants, setTenants] = useState<any[]>([]);
  const [isCopied, setIsCopied] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const { data: tenantsData } = await api.get('/admin/core/chat/tenants');
        setTenants(tenantsData);
        if (tenantsData.length > 0) setTenantId(tenantsData[0].id);

        const { data: config } = await api.get('/admin/core/config/deployment');
        setWebhookUrl(config.webhook_calcom_url || '');
      } catch (err) {
        console.error('Error loading Cal.com config:', err);
      }
    };
    loadData();
  }, []);

  const fullWebhookUrl = tenantId ? `${webhookUrl}/${tenantId}` : webhookUrl;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(fullWebhookUrl);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-orange-500/20 flex items-center justify-center">
          <Calendar size={20} className="text-orange-400" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">Integración Cal.com</h2>
          <p className="text-sm text-white/40">Configura el agendamiento externo y sincronización de eventos.</p>
        </div>
      </div>

      <GlassCard className="p-6 border-orange-500/20">
        <div className="space-y-6">
          <div className="flex items-start gap-4 p-4 bg-orange-500/5 border border-orange-500/10 rounded-xl">
            <Link2 className="text-orange-400 mt-1" size={20} />
            <div>
              <h3 className="text-sm font-bold text-white mb-1">Paso 1: Configurar Webhook en Cal.com</h3>
              <p className="text-xs text-white/50 leading-relaxed">
                Copia la siguiente URL y búscala en tu panel de Cal.com (Settings &gt; Webhooks). 
                Asegúrate de seleccionar los eventos <strong>"BOOKING_CREATED"</strong> y <strong>"BOOKING_CANCELLED"</strong>.
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-[10px] font-bold text-white/40 uppercase tracking-widest mb-1.5 block">Seleccionar Entidad / Clínica</label>
              <select
                value={tenantId || ''}
                onChange={(e) => setTenantId(Number(e.target.value))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:border-orange-500/50 outline-none transition-all"
              >
                {tenants.map(t => (
                  <option key={t.id} value={t.id} className="bg-[#0f1115]">{t.clinic_name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[10px] font-bold text-white/40 uppercase tracking-widest mb-1.5 block">URL del Webhook</label>
              <div className="flex gap-2">
                <input
                  readOnly
                  value={fullWebhookUrl}
                  className="flex-1 bg-white/[0.03] border border-white/10 rounded-lg px-4 py-2.5 text-white/60 text-xs font-mono outline-none"
                />
                <button
                  onClick={copyToClipboard}
                  className={`px-4 py-2.5 rounded-lg font-bold text-xs flex items-center gap-2 transition-all active:scale-95 ${
                    isCopied ? 'bg-green-500 text-white' : 'bg-orange-500 hover:bg-orange-600 text-white'
                  }`}
                >
                  {isCopied ? <CheckCircle2 size={16} /> : <Copy size={16} />}
                  {isCopied ? 'Copiado' : 'Copiar'}
                </button>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-white/5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-white/60 text-xs">
                <ShieldCheck size={14} className="text-green-500" />
                Seguridad activa: Verificación de JWT requerida en el endpoint.
              </div>
              <a 
                href="https://cal.com/settings/developer/webhooks" 
                target="_blank" 
                rel="noreferrer"
                className="text-orange-400 hover:text-orange-300 text-xs font-semibold flex items-center gap-1 transition-colors"
              >
                Ir a Cal.com <ExternalLink size={12} />
              </a>
            </div>
          </div>
        </div>
      </GlassCard>

      <div className="flex items-start gap-3 p-4 bg-violet-500/10 border border-violet-500/20 rounded-xl">
        <AlertCircle size={18} className="text-violet-400 shrink-0 mt-0.5" />
        <p className="text-xs text-violet-400/80 leading-relaxed">
          <strong>Nota de Sincronización:</strong> El sistema sincronizará automáticamente los turnos agendados vía Cal.com con la agenda local del vendedor asignado al lead.
        </p>
      </div>
    </div>
  );
}
