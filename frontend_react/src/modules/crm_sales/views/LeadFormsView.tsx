/**
 * LeadFormsView — F-02: Lead capture form builder (CEO/secretary).
 */
import { useState, useEffect } from 'react';
import { Plus, Copy, Edit3, Trash2, Link2, ToggleLeft, ToggleRight, X, GripVertical } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';

const API = '/admin/core/crm/forms';

interface FormField { type: string; label: string; placeholder: string; required: boolean; options?: string[] }
interface LeadForm { id: string; name: string; slug: string; fields: FormField[]; thank_you_message: string; redirect_url: string; active: boolean; created_at: string }

export default function LeadFormsView() {
  const { t } = useTranslation();
  const [forms, setForms] = useState<LeadForm[]>([]);
  const [loading, setLoading] = useState(true);
  const [showBuilder, setShowBuilder] = useState(false);
  const [editing, setEditing] = useState<LeadForm | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const load = async () => { setLoading(true); try { const r = await api.get(API); setForms(Array.isArray(r.data) ? r.data : []); } catch {} setLoading(false); };
  useEffect(() => { load(); }, []);

  const handleDelete = async (id: string) => { if (!confirm(t('forms.confirm_delete'))) return; try { await api.delete(`${API}/${id}`); load(); } catch {} };

  const copyLink = (slug: string) => {
    const url = `${window.location.origin}/f/${slug}`;
    navigator.clipboard.writeText(url);
    setCopied(slug);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="shrink-0 px-4 py-4 border-b border-white/[0.06] flex items-center justify-between">
        <h1 className="text-lg font-semibold text-white">{t('forms.title')}</h1>
        <button onClick={() => { setEditing(null); setShowBuilder(true); }} className="flex items-center gap-2 px-3 py-2 bg-primary text-white text-sm rounded-lg hover:bg-violet-700">
          <Plus size={16} /> {t('forms.create')}
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {loading ? <div className="text-center text-white/40 py-8">{t('common.loading')}</div> :
         forms.length === 0 ? <div className="text-center text-white/30 py-8">{t('forms.empty')}</div> :
         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {forms.map(f => (
            <div key={f.id} className="p-4 bg-white/[0.03] border border-white/[0.06] rounded-lg group">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-sm font-medium text-white">{f.name}</h3>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${f.active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                  {f.active ? 'Activo' : 'Inactivo'}
                </span>
              </div>
              <p className="text-xs text-white/40 mb-3">{f.fields.length} campos · slug: {f.slug}</p>
              <div className="flex gap-1">
                <button onClick={() => copyLink(f.slug)} className="p-1.5 rounded hover:bg-white/[0.06] text-white/40" title="Copiar link">
                  {copied === f.slug ? <span className="text-green-400 text-xs">Copiado!</span> : <Copy size={14} />}
                </button>
                <button onClick={() => { setEditing(f); setShowBuilder(true); }} className="p-1.5 rounded hover:bg-white/[0.06] text-white/40"><Edit3 size={14} /></button>
                <button onClick={() => handleDelete(f.id)} className="p-1.5 rounded hover:bg-red-500/10 text-white/40"><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
         </div>}
      </div>
      {showBuilder && <FormBuilderModal form={editing} onClose={() => { setShowBuilder(false); setEditing(null); }} onSaved={() => { setShowBuilder(false); setEditing(null); load(); }} />}
    </div>
  );
}

function FormBuilderModal({ form, onClose, onSaved }: { form: LeadForm | null; onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation();
  const [name, setName] = useState(form?.name || '');
  const [fields, setFields] = useState<FormField[]>(form?.fields || [{ type: 'text', label: 'Nombre', placeholder: 'Tu nombre', required: true }, { type: 'phone', label: 'Telefono', placeholder: '+54...', required: true }, { type: 'email', label: 'Email', placeholder: 'tu@email.com', required: false }]);
  const [thankYou, setThankYou] = useState(form?.thank_you_message || 'Gracias por tu interes. Te contactaremos pronto.');
  const [redirect, setRedirect] = useState(form?.redirect_url || '');
  const [active, setActive] = useState(form?.active ?? true);
  const [saving, setSaving] = useState(false);

  const addField = () => setFields([...fields, { type: 'text', label: '', placeholder: '', required: false }]);
  const removeField = (i: number) => setFields(fields.filter((_, idx) => idx !== i));
  const updateField = (i: number, key: string, val: any) => setFields(fields.map((f, idx) => idx === i ? { ...f, [key]: val } : f));

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (form) await api.put(`${API}/${form.id}`, { name, fields, thank_you_message: thankYou, redirect_url: redirect, active });
      else await api.post(API, { name, fields, thank_you_message: thankYou, redirect_url: redirect });
      onSaved();
    } catch {}
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-[#1a1a2e] border border-white/[0.08] rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
          <h2 className="text-white font-semibold">{form ? t('forms.edit') : t('forms.create')}</h2>
          <button onClick={onClose}><X size={18} className="text-white/50" /></button>
        </div>
        <div className="p-4 space-y-4">
          <input value={name} onChange={e => setName(e.target.value)} placeholder={t('forms.name_placeholder')} className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm" />
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-white/70">{t('forms.fields')}</label>
              <button onClick={addField} className="text-xs text-violet-400 hover:underline">+ {t('forms.add_field')}</button>
            </div>
            {fields.map((f, i) => (
              <div key={i} className="flex gap-2 mb-2 items-center">
                <select value={f.type} onChange={e => updateField(i, 'type', e.target.value)} className="px-2 py-1.5 bg-white/[0.05] text-white text-xs border border-white/[0.08] rounded">
                  <option value="text">Texto</option><option value="email">Email</option><option value="phone">Telefono</option><option value="textarea">Textarea</option><option value="select">Select</option>
                </select>
                <input value={f.label} onChange={e => updateField(i, 'label', e.target.value)} placeholder="Label" className="flex-1 px-2 py-1.5 bg-white/[0.05] text-white text-xs border border-white/[0.08] rounded" />
                <label className="flex items-center gap-1 text-[10px] text-white/40"><input type="checkbox" checked={f.required} onChange={e => updateField(i, 'required', e.target.checked)} /> Req</label>
                <button onClick={() => removeField(i)} className="text-red-400 text-xs">&times;</button>
              </div>
            ))}
          </div>
          <textarea value={thankYou} onChange={e => setThankYou(e.target.value)} placeholder={t('forms.thank_you')} rows={2} className="w-full px-3 py-2 bg-white/[0.05] text-white text-xs border border-white/[0.08] rounded-lg resize-none" />
          <input value={redirect} onChange={e => setRedirect(e.target.value)} placeholder="URL redirect (opcional)" className="w-full px-3 py-2 bg-white/[0.05] text-white text-xs border border-white/[0.08] rounded-lg" />
          {form && (
            <label className="flex items-center gap-2 text-sm text-white/60">
              <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /> Formulario activo
            </label>
          )}
        </div>
        <div className="flex justify-end gap-2 p-4 border-t border-white/[0.06]">
          <button onClick={onClose} className="px-4 py-2 text-white/60 text-sm">{t('common.cancel')}</button>
          <button onClick={handleSave} disabled={saving || !name.trim()} className="px-4 py-2 bg-primary text-white text-sm rounded-lg disabled:opacity-50">
            {saving ? t('common.saving') : t('common.save_changes')}
          </button>
        </div>
      </div>
    </div>
  );
}
