/**
 * ManualesView — SPEC-03: Knowledge Base with categories, search, and Markdown.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { Book, Plus, Search, Edit3, Trash2, X, ChevronDown, ChevronUp } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import { useAuth } from '../../../context/AuthContext';

const API = '/admin/core/manuales';
const CATS = ['general', 'guion_ventas', 'objeciones', 'producto', 'proceso', 'onboarding'];
const CAT_COLORS: Record<string, string> = { general: 'bg-blue-500/10 text-blue-400', guion_ventas: 'bg-violet-500/10 text-violet-400', objeciones: 'bg-rose-500/10 text-rose-400', producto: 'bg-emerald-500/10 text-emerald-400', proceso: 'bg-amber-500/10 text-amber-400', onboarding: 'bg-cyan-500/10 text-cyan-400' };

function renderMarkdown(text: string): string {
  return text
    .replace(/^### (.+)$/gm, '<h4 class="text-xs font-semibold text-white/70 mt-2">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="text-sm font-semibold text-white/80 mt-3">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 class="text-base font-bold text-white mt-3">$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 text-white/70 text-sm">$1</li>')
    .replace(/\n/g, '<br/>');
}

function stripMarkdown(text: string): string {
  return text.replace(/[#*\-]/g, '').trim();
}

export default function ManualesView() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const canEdit = user?.role === 'ceo' || user?.role === 'secretary';
  const [manuales, setManuales] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [catFilter, setCatFilter] = useState<string>('');
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const searchTimer = useRef<ReturnType<typeof setTimeout>>();
  const [searchQ, setSearchQ] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (catFilter) params.categoria = catFilter;
      if (searchQ) params.q = searchQ;
      const res = await api.get(API, { params });
      setManuales(res.data.items);
    } catch {}
    setLoading(false);
  }, [catFilter, searchQ]);

  useEffect(() => { load(); }, [load]);

  const handleSearch = (v: string) => {
    setSearch(v);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setSearchQ(v), 300);
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t('manuales.confirm_delete'))) return;
    try { await api.delete(`${API}/${id}`); load(); } catch {}
  };

  const toggleExpand = (id: string) => {
    setExpanded(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  };

  const grouped = CATS.reduce((acc, cat) => {
    const items = manuales.filter(m => m.categoria === cat);
    if (items.length > 0) acc[cat] = items;
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <div className="flex flex-col h-full">
      <div className="shrink-0 px-4 py-4 border-b border-white/[0.06]">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-semibold text-white flex items-center gap-2"><Book size={18} /> {t('manuales.title')}</h1>
          {canEdit && <button onClick={() => { setEditing(null); setShowForm(true); }} className="flex items-center gap-2 px-3 py-2 bg-primary text-white text-sm rounded-lg hover:bg-blue-700"><Plus size={16} /> {t('manuales.create')}</button>}
        </div>
        <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
          <button onClick={() => setCatFilter('')} className={`px-3 py-1.5 rounded-full text-xs font-medium ${!catFilter ? 'bg-white/[0.1] text-white ring-1 ring-white/20' : 'bg-white/[0.03] text-white/50'}`}>{t('manuales.all')}</button>
          {CATS.map(c => <button key={c} onClick={() => setCatFilter(c)} className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap ${catFilter === c ? 'bg-white/[0.1] text-white ring-1 ring-white/20' : 'bg-white/[0.03] text-white/50'}`}>{c.replace('_', ' ')}</button>)}
        </div>
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input type="text" value={search} onChange={e => handleSearch(e.target.value)} placeholder={t('manuales.search')}
            className="w-full pl-9 pr-3 py-2 bg-white/[0.05] text-white text-sm border border-white/[0.08] rounded-lg" />
        </div>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
        {loading ? <div className="text-center text-white/40 py-8">{t('common.loading')}</div> :
         Object.keys(grouped).length === 0 ? <div className="text-center text-white/30 py-8">{t('manuales.empty')}</div> :
         Object.entries(grouped).map(([cat, items]) => (
          <section key={cat}>
            <h2 className="text-sm font-semibold text-white/60 mb-2 capitalize">{cat.replace('_', ' ')}</h2>
            <div className="space-y-2">
              {items.map((m: any) => (
                <div key={m.id} className="rounded-lg bg-white/[0.03] border border-white/[0.06]">
                  <div className="flex items-center justify-between px-4 py-3 cursor-pointer" onClick={() => toggleExpand(m.id)}>
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${CAT_COLORS[m.categoria] || 'bg-white/10 text-white/50'}`}>{m.categoria}</span>
                      <h3 className="text-sm font-medium text-white truncate">{m.titulo}</h3>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {canEdit && <>
                        <button onClick={e => { e.stopPropagation(); setEditing(m); setShowForm(true); }} className="p-1 hover:bg-white/[0.06] rounded text-white/40"><Edit3 size={14} /></button>
                        <button onClick={e => { e.stopPropagation(); handleDelete(m.id); }} className="p-1 hover:bg-red-500/10 rounded text-white/40"><Trash2 size={14} /></button>
                      </>}
                      {expanded.has(m.id) ? <ChevronUp size={14} className="text-white/30" /> : <ChevronDown size={14} className="text-white/30" />}
                    </div>
                  </div>
                  {!expanded.has(m.id) && <p className="px-4 pb-3 text-xs text-white/40">{stripMarkdown(m.contenido).substring(0, 150)}...</p>}
                  {expanded.has(m.id) && <div className="px-4 pb-4 text-sm text-white/70" dangerouslySetInnerHTML={{ __html: renderMarkdown(m.contenido) }} />}
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
      {showForm && <ManualFormDialog manual={editing} onClose={() => { setShowForm(false); setEditing(null); }} onSaved={() => { setShowForm(false); setEditing(null); load(); }} />}
    </div>
  );
}

function ManualFormDialog({ manual, onClose, onSaved }: { manual: any; onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation();
  const [titulo, setTitulo] = useState(manual?.titulo || '');
  const [contenido, setContenido] = useState(manual?.contenido || '');
  const [categoria, setCategoria] = useState(manual?.categoria || 'general');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!titulo.trim() || !contenido.trim()) return;
    setSaving(true);
    try {
      if (manual) await api.put(`${API}/${manual.id}`, { titulo, contenido, categoria });
      else await api.post(API, { titulo, contenido, categoria });
      onSaved();
    } catch {}
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-[#1a1a2e] border border-white/[0.08] rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
          <h2 className="text-white font-semibold">{manual ? t('manuales.edit') : t('manuales.create')}</h2>
          <button onClick={onClose}><X size={18} className="text-white/50" /></button>
        </div>
        <div className="p-4 space-y-4">
          <input type="text" value={titulo} onChange={e => setTitulo(e.target.value)} placeholder={t('manuales.titulo')} className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm" />
          <select value={categoria} onChange={e => setCategoria(e.target.value)} className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm">
            {CATS.map(c => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}
          </select>
          <div>
            <textarea value={contenido} onChange={e => setContenido(e.target.value)} rows={10} placeholder={t('manuales.content_hint')}
              className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm resize-none" />
            <p className="text-[10px] text-white/30 mt-1">{t('manuales.markdown_hint')}</p>
          </div>
        </div>
        <div className="flex justify-end gap-2 p-4 border-t border-white/[0.06]">
          <button onClick={onClose} className="px-4 py-2 text-white/60 text-sm">{t('common.cancel')}</button>
          <button onClick={handleSubmit} disabled={saving || !titulo.trim() || !contenido.trim()} className="px-4 py-2 bg-primary text-white text-sm rounded-lg disabled:opacity-50">
            {saving ? t('common.saving') : t('common.save_changes')}
          </button>
        </div>
      </div>
    </div>
  );
}
