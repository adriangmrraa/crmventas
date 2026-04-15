/**
 * PublicFormView — F-02: Public lead capture form (no auth required).
 */
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface FormField { type: string; label: string; placeholder: string; required: boolean; options?: string[] }

export default function PublicFormView() {
  const { slug } = useParams<{ slug: string }>();
  const [form, setForm] = useState<{ name: string; fields: FormField[]; thank_you_message: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [thankYou, setThankYou] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get(`${API_BASE}/f/${slug}`);
        setForm(res.data);
        const initial: Record<string, string> = {};
        res.data.fields?.forEach((f: FormField) => { initial[f.label] = ''; });
        setValues(initial);
      } catch { setError('Formulario no encontrado o inactivo.'); }
      setLoading(false);
    })();
  }, [slug]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    // Validate required fields
    for (const field of form.fields) {
      if (field.required && !values[field.label]?.trim()) {
        setError(`El campo "${field.label}" es obligatorio.`);
        return;
      }
    }
    setSubmitting(true); setError(null);
    try {
      const res = await axios.post(`${API_BASE}/f/${slug}/submit`, values);
      setThankYou(res.data.thank_you_message || 'Gracias!');
      if (res.data.redirect_url) { window.location.href = res.data.redirect_url; return; }
      setSubmitted(true);
    } catch (err: any) {
      setError(err.response?.status === 429 ? 'Demasiados envios. Intenta en unos minutos.' : 'Error al enviar. Intenta de nuevo.');
    }
    setSubmitting(false);
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-gray-50"><Loader2 className="animate-spin text-violet-500" size={32} /></div>;
  if (error && !form) return <div className="min-h-screen flex items-center justify-center bg-gray-50"><div className="text-center"><AlertCircle size={48} className="mx-auto text-red-400 mb-4" /><p className="text-gray-600">{error}</p></div></div>;
  if (submitted) return <div className="min-h-screen flex items-center justify-center bg-gray-50"><div className="text-center max-w-md"><CheckCircle size={48} className="mx-auto text-green-500 mb-4" /><p className="text-gray-800 text-lg font-medium">{thankYou}</p></div></div>;

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-6">
        <h1 className="text-xl font-bold text-gray-900 mb-6">{form?.name}</h1>
        {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          {form?.fields.map((field, i) => (
            <div key={i}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label} {field.required && <span className="text-red-500">*</span>}
              </label>
              {field.type === 'textarea' ? (
                <textarea value={values[field.label] || ''} onChange={e => setValues({ ...values, [field.label]: e.target.value })}
                  placeholder={field.placeholder} rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-violet-500 focus:border-violet-500" />
              ) : field.type === 'select' ? (
                <select value={values[field.label] || ''} onChange={e => setValues({ ...values, [field.label]: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-violet-500">
                  <option value="">{field.placeholder || 'Seleccionar...'}</option>
                  {field.options?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                </select>
              ) : (
                <input type={field.type === 'email' ? 'email' : field.type === 'phone' ? 'tel' : 'text'}
                  value={values[field.label] || ''} onChange={e => setValues({ ...values, [field.label]: e.target.value })}
                  placeholder={field.placeholder}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-violet-500 focus:border-violet-500" />
              )}
            </div>
          ))}
          <button type="submit" disabled={submitting}
            className="w-full py-3 bg-[#8F3DFF] text-white font-medium rounded-lg hover:bg-[#7B2FE6] disabled:opacity-50 transition-colors">
            {submitting ? 'Enviando...' : 'Enviar'}
          </button>
        </form>
      </div>
    </div>
  );
}
