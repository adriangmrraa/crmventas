/**
 * MisNotasView — SPEC-06: Vendor tasks/notes with 3 sections.
 */
import { useState, useEffect } from 'react';
import { CheckSquare, FileText, Plus, Search } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';

const API = '/admin/core/crm/vendor-tasks';

export default function MisNotasView() {
  const { t } = useTranslation();
  const [data, setData] = useState<{ asignadas: any[]; notas: any[]; personales: any[] }>({ asignadas: [], notas: [], personales: [] });
  const [loading, setLoading] = useState(true);
  const [newTask, setNewTask] = useState('');
  const [searchNotas, setSearchNotas] = useState('');

  const load = async () => {
    setLoading(true);
    try { const res = await api.get(`${API}/mine`); setData(res.data); } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const toggleComplete = async (id: string, completada: boolean) => {
    try { await api.patch(`${API}/${id}/completar`, { completada }); load(); } catch {}
  };

  const createPersonal = async () => {
    if (!newTask.trim()) return;
    try { await api.post(`${API}/personal`, { contenido: newTask.trim() }); setNewTask(''); load(); } catch {}
  };

  const deadlineColor = (task: any) => {
    if (task.completada) return 'text-green-400 line-through';
    if (!task.fecha_limite) return 'text-white/40';
    return new Date(task.fecha_limite) < new Date() ? 'text-red-400' : 'text-amber-400';
  };

  const filteredNotas = data.notas.filter(n => !searchNotas || n.contenido.toLowerCase().includes(searchNotas.toLowerCase()));

  if (loading) return <div className="h-full flex items-center justify-center text-white/40">{t('common.loading')}</div>;

  return (
    <div className="flex flex-col h-full">
      <div className="shrink-0 px-4 py-4 border-b border-white/[0.06]">
        <h1 className="text-lg font-semibold text-white">{t('vendor_tasks.title')}</h1>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-6">
        {/* Section 1: Assigned Tasks */}
        <section>
          <h2 className="text-sm font-semibold text-white/70 mb-2 flex items-center gap-2"><CheckSquare size={14} /> {t('vendor_tasks.assigned')}</h2>
          {data.asignadas.length === 0 ? <p className="text-xs text-white/30">{t('vendor_tasks.no_tasks')}</p> : (
            <div className="space-y-1">
              {data.asignadas.map(task => (
                <div key={task.id} className={`flex items-start gap-3 px-3 py-2 rounded-lg bg-white/[0.03] border ${task.completada ? 'border-green-500/20' : task.fecha_limite && new Date(task.fecha_limite) < new Date() ? 'border-red-500/20' : 'border-white/[0.06]'}`}>
                  <input type="checkbox" checked={task.completada} onChange={() => toggleComplete(task.id, !task.completada)} className="mt-1 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm ${task.completada ? 'text-white/40 line-through' : 'text-white/80'}`}>{task.contenido}</p>
                    {task.fecha_limite && <p className={`text-[10px] ${deadlineColor(task)}`}>{new Date(task.fecha_limite).toLocaleDateString()}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Section 2: Admin Notes */}
        <section>
          <h2 className="text-sm font-semibold text-white/70 mb-2 flex items-center gap-2"><FileText size={14} /> {t('vendor_tasks.admin_notes')}</h2>
          <div className="relative mb-2">
            <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-white/30" />
            <input type="text" value={searchNotas} onChange={e => setSearchNotas(e.target.value)} placeholder={t('vendor_tasks.search_notes')}
              className="w-full pl-7 pr-3 py-1.5 bg-white/[0.05] text-white text-xs border border-white/[0.08] rounded-lg" />
          </div>
          {filteredNotas.length === 0 ? <p className="text-xs text-white/30">{t('vendor_tasks.no_notes')}</p> : (
            <div className="space-y-1">
              {filteredNotas.map(note => (
                <div key={note.id} className="px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-sm text-white/80">{note.contenido}</p>
                  <p className="text-[10px] text-white/30 mt-1">{new Date(note.created_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Section 3: Personal Tasks */}
        <section>
          <h2 className="text-sm font-semibold text-white/70 mb-2 flex items-center gap-2"><CheckSquare size={14} /> {t('vendor_tasks.personal')}</h2>
          <div className="flex gap-2 mb-2">
            <input type="text" value={newTask} onChange={e => setNewTask(e.target.value)} placeholder={t('vendor_tasks.new_personal')}
              onKeyDown={e => e.key === 'Enter' && createPersonal()}
              className="flex-1 px-3 py-1.5 bg-white/[0.05] text-white text-xs border border-white/[0.08] rounded-lg" />
            <button onClick={createPersonal} className="px-3 py-1.5 bg-primary text-white text-xs rounded-lg"><Plus size={14} /></button>
          </div>
          {data.personales.length === 0 ? <p className="text-xs text-white/30">{t('vendor_tasks.no_personal')}</p> : (
            <div className="space-y-1">
              {data.personales.map(task => (
                <div key={task.id} className="flex items-start gap-3 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                  <input type="checkbox" checked={task.completada} onChange={() => toggleComplete(task.id, !task.completada)} className="mt-1 shrink-0" />
                  <p className={`text-sm flex-1 ${task.completada ? 'text-white/40 line-through' : 'text-white/80'}`}>{task.contenido}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
