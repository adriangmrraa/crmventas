import { useState, useEffect } from 'react';
import { Shield, Trash2, Plus, AlertCircle, Phone, Mail, User } from 'lucide-react';
import api from '../../api/axios';
import { useTranslation } from '../../context/LanguageContext';
import GlassCard from '../GlassCard';

interface BlacklistItem {
  identifier: string;
  reason: string;
  created_at: string;
}

export default function BlacklistManager() {
  const [blacklist, setBlacklist] = useState<BlacklistItem[]>([]);
  const [newIdentifier, setNewIdentifier] = useState('');
  const [newReason, setNewReason] = useState('');
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
    if (!newIdentifier) return;
    setIsLoading(true);
    try {
      await api.post('/admin/core/blacklist', { 
        identifier: newIdentifier, 
        reason: newReason 
      });
      setNewIdentifier('');
      setNewReason('');
      fetchBlacklist();
    } catch (err) {
      console.error('Error adding to blacklist:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemove = async (identifier: string) => {
    try {
      await api.delete(`/admin/core/blacklist/${identifier}`);
      fetchBlacklist();
    } catch (err) {
      console.error('Error removing from blacklist:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
          <Shield size={20} className="text-red-400" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">Seguridad: Blacklist</h2>
          <p className="text-sm text-white/40">Bloquea leads por teléfono, email o identificador único.</p>
        </div>
      </div>

      <GlassCard className="p-6">
        <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <label className="text-xs font-bold text-white/40 uppercase">Identificador (Tel/Email)</label>
            <div className="relative">
              <input
                type="text"
                value={newIdentifier}
                onChange={(e) => setNewIdentifier(e.target.value)}
                placeholder="54911..."
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:border-red-500/50 outline-none"
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1 opacity-20">
                <Phone size={12} />
                <Mail size={12} />
              </div>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-white/40 uppercase">Motivo del bloqueo</label>
            <input
              type="text"
              value={newReason}
              onChange={(e) => setNewReason(e.target.value)}
              placeholder="Spam, duplicado, etc."
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:border-red-500/50 outline-none"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={isLoading || !newIdentifier}
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
              <th className="px-6 py-4 text-[10px] font-bold text-white/40 uppercase tracking-wider">Identificador</th>
              <th className="px-6 py-4 text-[10px] font-bold text-white/40 uppercase tracking-wider">Motivo</th>
              <th className="px-6 py-4 text-[10px] font-bold text-white/40 uppercase tracking-wider">Fecha</th>
              <th className="px-6 py-4 text-[10px] font-bold text-white/40 uppercase tracking-wider text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {blacklist.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-12 text-center opacity-20">
                  <User size={32} className="mx-auto mb-2" />
                  <p className="text-sm">No hay registros en la blacklist</p>
                </td>
              </tr>
            ) : (
              blacklist.map((item) => (
                <tr key={item.identifier} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-6 py-4">
                    <span className="text-sm font-medium text-white">{item.identifier}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-white/60">{item.reason || '-'}</span>
                  </td>
                  <td className="px-6 py-4 text-xs text-white/30">
                    {new Date(item.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRemove(item.identifier)}
                      className="p-2 text-white/20 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                      title="Quitar"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              )
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="flex items-start gap-3 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
        <AlertCircle size={18} className="text-yellow-500 shrink-0 mt-0.5" />
        <p className="text-xs text-yellow-500/80 leading-relaxed">
          <strong>Aviso de Seguridad:</strong> Los identificadores bloqueados no podrán generar leads en ninguna clínica ni enviar mensajes nuevos si son detectados por el motor de entrada. Esta acción es global para tu tenant.
        </p>
      </div>
    </div>
  );
}
