import { useState, useEffect } from 'react';
import { Shield, Trash2, Plus, AlertCircle, Phone, Mail, ChevronDown } from 'lucide-react';
import api from '../../api/axios';
import { useTranslation } from '../../context/LanguageContext';
import GlassCard from '../GlassCard';

// G6: Predefined reasons
const PREDEFINED_REASONS = [
  { value: 'lead_descartado', label: 'Lead descartado definitivo' },
  { value: 'ex_cliente', label: 'Ex cliente' },
  { value: 'spam', label: 'Spam' },
  { value: 'numero_invalido', label: 'Número inválido' },
  { value: 'no_contactar', label: 'Solicitud de no contacto' },
];

// G7: Auto-detect type from value
function detectType(value: string): 'phone' | 'email' | 'domain' {
  if (value.includes('@')) return 'email';
  if (value.startsWith('http') || (value.includes('.') && !value.match(/^\d/))) return 'domain';
  return 'phone';
}

// G7: Fixed interface matching backend
interface BlacklistItem {
  id: string;
  value: string;
  type: string;
  reason: string;
  created_at: string;
}

export default function BlacklistManager() {
  const { t } = useTranslation();
  const [blacklist, setBlacklist] = useState<BlacklistItem[]>([]);
  const [newValue, setNewValue] = useState('');
  const [newReason, setNewReason] = useState('lead_descartado');
  const [customReason, setCustomReason] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const fetchBlacklist = async () => {
    try {
      const { data } = await api.get('/admin/core/blacklist');
      setBlacklist(data);
    } catch (err) {
      console.error('Error fetching blacklist:', err);
    }
  };

  useEffect(() => {
    fetchBlacklist();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newValue) return;
    setIsLoading(true);
    const type = detectType(newValue.trim());
    const reason = newReason === '_custom' ? customReason : newReason;
    try {
      // G7: send correct fields (value + type) instead of identifier
      await api.post('/admin/core/blacklist', {
        value: newValue.trim(),
        type,
        reason: reason || undefined,
      });
      setNewValue('');
      setNewReason('lead_descartado');
      setCustomReason('');
      fetchBlacklist();
    } catch (err) {
      console.error('Error adding to blacklist:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemove = async (value: string) => {
    try {
      await api.delete(`/admin/core/blacklist/${encodeURIComponent(value)}`);
      fetchBlacklist();
    } catch (err) {
      console.error('Error removing from blacklist:', err);
    }
  };

  const typeIcon = (type: string) => {
    if (type === 'email') return <Mail size={13} className="text-blue-400" />;
    if (type === 'phone') return <Phone size={13} className="text-green-400" />;
    return <Shield size={13} className="text-white/40" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
          <Shield size={20} className="text-red-400" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">Seguridad: Blacklist</h2>
          <p className="text-sm text-white/40">Bloquea leads por teléfono, email o dominio.</p>
        </div>
      </div>

      <GlassCard className="p-6">
        <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="space-y-2">
            <label className="text-xs font-bold text-white/40 uppercase">Teléfono o Email</label>
            <div className="relative">
              <input
                type="text"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                placeholder="54911... o user@mail.com"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:border-red-500/50 outline-none"
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1 opacity-20">
                <Phone size={12} />
                <Mail size={12} />
              </div>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-white/40 uppercase">Motivo</label>
            <div className="relative">
              <select
                value={newReason}
                onChange={(e) => setNewReason(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:border-red-500/50 outline-none appearance-none"
              >
                {PREDEFINED_REASONS.map((r) => (
                  <option key={r.value} value={r.value} className="bg-[#0a0e1a]">{r.label}</option>
                ))}
                <option value="_custom" className="bg-[#0a0e1a]">Otro (personalizado)</option>
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
            </div>
          </div>
          {newReason === '_custom' && (
            <div className="space-y-2">
              <label className="text-xs font-bold text-white/40 uppercase">Motivo personalizado</label>
              <input
                type="text"
                value={customReason}
                onChange={(e) => setCustomReason(e.target.value)}
                placeholder="Describe el motivo..."
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:border-red-500/50 outline-none"
              />
            </div>
          )}
          <div className="flex items-end">
            <button
              type="submit"
              disabled={isLoading || !newValue}
              className="w-full h-[38px] bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-bold flex items-center justify-center gap-2 transition-all active:scale-95"
            >
              <Plus size={16} />
              Bloquear
            </button>
          </div>
        </form>
      </GlassCard>

      <div className="bg-white/[0.02] rounded-2xl border border-white/5 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.02]">
              <th className="px-6 py-4 text-[10px] font-bold text-white/40 uppercase tracking-wider">Tipo</th>
              <th className="px-6 py-4 text-[10px] font-bold text-white/40 uppercase tracking-wider">Valor</th>
              <th className="px-6 py-4 text-[10px] font-bold text-white/40 uppercase tracking-wider">Motivo</th>
              <th className="px-6 py-4 text-[10px] font-bold text-white/40 uppercase tracking-wider">Fecha</th>
              <th className="px-6 py-4 text-[10px] font-bold text-white/40 uppercase tracking-wider text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {blacklist.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center opacity-20">
                  <Shield size={32} className="mx-auto mb-2" />
                  <p className="text-sm">No hay registros en la blacklist</p>
                </td>
              </tr>
            ) : (
              blacklist.map((item) => (
                <tr key={item.value} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5">
                      {typeIcon(item.type)}
                      <span className="text-xs text-white/40 uppercase">{item.type}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm font-medium text-white font-mono">{item.value}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-white/60">
                      {PREDEFINED_REASONS.find(r => r.value === item.reason)?.label || item.reason || '-'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs text-white/30">
                    {new Date(item.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRemove(item.value)}
                      className="p-2 text-white/20 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                      title="Quitar de blacklist"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-start gap-3 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
        <AlertCircle size={18} className="text-yellow-500 shrink-0 mt-0.5" />
        <p className="text-xs text-yellow-500/80 leading-relaxed">
          <strong>Aviso de Seguridad:</strong> Los contactos bloqueados no podrán generar leads ni enviar mensajes. El motor de entrada verifica teléfono normalizado y email. Esta acción aplica a todo el tenant.
        </p>
      </div>
    </div>
  );
}
