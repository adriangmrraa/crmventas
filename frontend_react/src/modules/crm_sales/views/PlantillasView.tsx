/**
 * PlantillasView — SPEC-02: Message Templates with dynamic variables.
 * Full page: category tabs, search, grid, create/edit dialog with variable insertion.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  MessageCircle, Mail, UserCheck, Target, Trophy,
  Plus, Search, Copy, Edit3, Trash2, Eye, X, Check
} from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Plantilla {
  id: string;
  nombre: string;
  categoria: string;
  contenido: string;
  variables: string[];
  uso_count: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

type Categoria = 'all' | 'whatsapp' | 'email' | 'seguimiento' | 'prospeccion' | 'cierre';

const CATEGORIES: { key: Categoria; icon: typeof MessageCircle; color: string }[] = [
  { key: 'all', icon: Check, color: 'text-white/60' },
  { key: 'whatsapp', icon: MessageCircle, color: 'text-green-400' },
  { key: 'email', icon: Mail, color: 'text-violet-400' },
  { key: 'seguimiento', icon: UserCheck, color: 'text-amber-400' },
  { key: 'prospeccion', icon: Target, color: 'text-purple-400' },
  { key: 'cierre', icon: Trophy, color: 'text-emerald-400' },
];

const CATEGORY_BG: Record<string, string> = {
  whatsapp: 'bg-green-500/10 text-green-400 border-green-500/20',
  email: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
  seguimiento: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  prospeccion: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  cierre: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
};

const PREDEFINED_VARS = ['nombre', 'empresa', 'telefono', 'email', 'producto', 'precio', 'fecha'];

const SAMPLE_DATA: Record<string, string> = {
  nombre: 'Juan Perez',
  empresa: 'Soluciones CRM',
  telefono: '+54 11 1234 5678',
  email: 'juan@empresa.com',
  producto: 'Plan Pro',
  precio: '$150.000 ARS',
  fecha: '14 de abril',
};

const API_BASE = '/api/v1/plantillas';

// ─── Main Component ──────────────────────────────────────────────────────────

export default function PlantillasView() {
  const { t } = useTranslation();
  const [plantillas, setPlantillas] = useState<Plantilla[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [activeCategory, setActiveCategory] = useState<Categoria>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingPlantilla, setEditingPlantilla] = useState<Plantilla | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout>>();

  const fetchPlantillas = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (activeCategory !== 'all') params.categoria = activeCategory;
      if (searchQuery) params.q = searchQuery;
      const res = await api.get(API_BASE, { params });
      setPlantillas(res.data.items);
      setTotal(res.data.total);
    } catch {
      setError(t('plantillas.error_loading'));
    } finally {
      setLoading(false);
    }
  }, [activeCategory, searchQuery, t]);

  useEffect(() => { fetchPlantillas(); }, [fetchPlantillas]);

  const handleSearch = (value: string) => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setSearchQuery(value), 300);
  };

  const handleCopy = async (p: Plantilla) => {
    try {
      await navigator.clipboard.writeText(p.contenido);
      setCopiedId(p.id);
      setTimeout(() => setCopiedId(null), 2000);
      api.post(`${API_BASE}/${p.id}/uso`);
      setPlantillas(prev => prev.map(x =>
        x.id === p.id ? { ...x, uso_count: x.uso_count + 1 } : x
      ));
    } catch {
      setError(t('plantillas.error_copy'));
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t('plantillas.confirm_delete'))) return;
    try {
      await api.delete(`${API_BASE}/${id}`);
      fetchPlantillas();
    } catch {
      setError(t('plantillas.error_delete'));
    }
  };

  const handleSaved = () => {
    setShowForm(false);
    setEditingPlantilla(null);
    fetchPlantillas();
  };

  const renderPreview = (contenido: string) => {
    let result = contenido;
    for (const [key, val] of Object.entries(SAMPLE_DATA)) {
      result = result.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), val);
    }
    return result.length > 120 ? result.substring(0, 120) + '...' : result;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="shrink-0 px-4 py-4 border-b border-white/[0.06]">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-semibold text-white">{t('plantillas.title')}</h1>
          <button
            onClick={() => { setEditingPlantilla(null); setShowForm(true); }}
            className="flex items-center gap-2 px-3 py-2 bg-primary text-white text-sm rounded-lg hover:bg-violet-700"
          >
            <Plus size={16} /> {t('plantillas.create')}
          </button>
        </div>

        {/* Category Tabs */}
        <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
          {CATEGORIES.map(({ key, icon: Icon, color }) => (
            <button
              key={key}
              onClick={() => setActiveCategory(key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                activeCategory === key
                  ? 'bg-white/[0.1] ring-1 ring-white/[0.2] text-white'
                  : 'bg-white/[0.03] text-white/50 hover:text-white/70'
              }`}
            >
              <Icon size={14} className={activeCategory === key ? color : ''} />
              {key === 'all' ? t('plantillas.all') : key}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            type="text"
            placeholder={t('plantillas.search')}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-white/[0.05] text-white text-sm border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 placeholder:text-white/30"
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex justify-between">
          {error}
          <button onClick={() => setError(null)}><X size={14} /></button>
        </div>
      )}

      {/* Grid */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-white/40">{t('common.loading')}</div>
        ) : plantillas.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-white/30 text-sm">
            <p>{t('plantillas.empty')}</p>
            <button onClick={() => setShowForm(true)} className="mt-2 text-primary hover:underline">
              {t('plantillas.create_first')}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {plantillas.map((p) => (
              <div
                key={p.id}
                className="group p-4 rounded-lg bg-white/[0.03] hover:bg-white/[0.05] border border-white/[0.06] cursor-pointer transition-colors"
                onClick={() => { setEditingPlantilla(p); setShowForm(true); }}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-medium text-white truncate flex-1">{p.nombre}</h3>
                  <span className={`ml-2 px-2 py-0.5 rounded-full text-[10px] font-medium border ${CATEGORY_BG[p.categoria] || 'bg-white/10 text-white/50'}`}>
                    {p.categoria}
                  </span>
                </div>
                <p className="text-xs text-white/50 mb-3 line-clamp-2">{renderPreview(p.contenido)}</p>
                {p.variables.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {p.variables.map(v => (
                      <span key={v} className="px-1.5 py-0.5 bg-violet-500/10 text-violet-400 text-[10px] rounded">
                        {`{{${v}}}`}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-white/30">{p.uso_count} {t('plantillas.uses')}</span>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleCopy(p); }}
                      className="p-1.5 rounded hover:bg-white/[0.08] text-white/50 hover:text-white"
                      title={t('plantillas.copy')}
                    >
                      {copiedId === p.id ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
                      className="p-1.5 rounded hover:bg-red-500/10 text-white/50 hover:text-red-400"
                      title={t('common.delete')}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Form Dialog */}
      {showForm && (
        <PlantillaFormDialog
          plantilla={editingPlantilla}
          onClose={() => { setShowForm(false); setEditingPlantilla(null); }}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}

// ─── Form Dialog ─────────────────────────────────────────────────────────────

function PlantillaFormDialog({
  plantilla,
  onClose,
  onSaved,
}: {
  plantilla: Plantilla | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [nombre, setNombre] = useState(plantilla?.nombre || '');
  const [categoria, setCategoria] = useState(plantilla?.categoria || 'whatsapp');
  const [contenido, setContenido] = useState(plantilla?.contenido || '');
  const [preview, setPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const detectedVars = contenido.match(/\{\{(\w+)\}\}/g)?.map(v => v.slice(2, -2)) || [];
  const uniqueVars = [...new Set(detectedVars)];

  const insertVariable = (varName: string) => {
    const el = textareaRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const insert = `{{${varName}}}`;
    const newContent = contenido.substring(0, start) + insert + contenido.substring(end);
    setContenido(newContent);
    setTimeout(() => {
      el.focus();
      el.selectionStart = el.selectionEnd = start + insert.length;
    }, 0);
  };

  const renderPreviewText = () => {
    let result = contenido;
    for (const [key, val] of Object.entries(SAMPLE_DATA)) {
      result = result.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), val);
    }
    return result;
  };

  const handleSubmit = async () => {
    if (!nombre.trim() || !contenido.trim()) return;
    setSaving(true);
    setError(null);
    try {
      if (plantilla) {
        await api.put(`${API_BASE}/${plantilla.id}`, { nombre, categoria, contenido });
      } else {
        await api.post(API_BASE, { nombre, categoria, contenido });
      }
      onSaved();
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('plantillas.error_save');
      setError(String(msg));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-[#1a1a2e] border border-white/[0.08] rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
          <h2 className="text-white font-semibold">
            {plantilla ? t('plantillas.edit') : t('plantillas.create')}
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-white/[0.06] rounded"><X size={18} className="text-white/50" /></button>
        </div>

        <div className="p-4 space-y-4">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">{error}</div>
          )}

          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1">{t('plantillas.name')}</label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              maxLength={100}
              className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm focus:ring-2 focus:ring-violet-500/30"
            />
          </div>

          {/* Categoria */}
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1">{t('plantillas.category')}</label>
            <select
              value={categoria}
              onChange={(e) => setCategoria(e.target.value)}
              className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm focus:ring-2 focus:ring-violet-500/30"
            >
              {['whatsapp', 'email', 'seguimiento', 'prospeccion', 'cierre'].map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Variable Buttons */}
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1">{t('plantillas.insert_variable')}</label>
            <div className="flex flex-wrap gap-1">
              {PREDEFINED_VARS.map(v => (
                <button
                  key={v}
                  type="button"
                  onClick={() => insertVariable(v)}
                  className="px-2 py-1 bg-violet-500/10 text-violet-400 text-xs rounded hover:bg-violet-500/20 border border-violet-500/20"
                >
                  {`{{${v}}}`}
                </button>
              ))}
            </div>
          </div>

          {/* Content / Preview Toggle */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-sm font-medium text-white/70">{t('plantillas.content')}</label>
              <button
                type="button"
                onClick={() => setPreview(!preview)}
                className="flex items-center gap-1 text-xs text-white/50 hover:text-white"
              >
                <Eye size={12} /> {preview ? t('plantillas.edit_mode') : t('plantillas.preview_mode')}
              </button>
            </div>
            {preview ? (
              <div className="w-full px-3 py-2 bg-white/[0.05] text-white/80 border border-white/[0.08] rounded-lg text-sm min-h-[120px] whitespace-pre-wrap">
                {renderPreviewText()}
              </div>
            ) : (
              <textarea
                ref={textareaRef}
                value={contenido}
                onChange={(e) => setContenido(e.target.value)}
                maxLength={4000}
                rows={5}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm focus:ring-2 focus:ring-violet-500/30 resize-none"
              />
            )}
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-white/30">{contenido.length}/4000</span>
            </div>
          </div>

          {/* Detected Variables */}
          {uniqueVars.length > 0 && (
            <div>
              <label className="block text-xs text-white/50 mb-1">{t('plantillas.detected_vars')}</label>
              <div className="flex flex-wrap gap-1">
                {uniqueVars.map(v => (
                  <span key={v} className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-xs rounded border border-emerald-500/20">
                    {v}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 p-4 border-t border-white/[0.06]">
          <button onClick={onClose} className="px-4 py-2 text-white/60 text-sm hover:text-white">
            {t('common.cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving || !nombre.trim() || !contenido.trim()}
            className="px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-violet-700 disabled:opacity-50"
          >
            {saving ? t('common.saving') : (plantilla ? t('common.save_changes') : t('plantillas.create'))}
          </button>
        </div>
      </div>
    </div>
  );
}
