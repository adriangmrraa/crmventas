import React, { useState, useEffect } from 'react';
import { X, Calendar, User, FileText } from 'lucide-react';
import { useTranslation } from '../../../context/LanguageContext';

export interface AgendaEventFormData {
  seller_id: number;
  title: string;
  start_datetime: string;
  end_datetime: string;
  notes: string;
}

export interface SellerOption {
  id: number;
  first_name: string;
  last_name?: string;
  email?: string;
  is_active: boolean;
}

interface AgendaEventFormProps {
  isOpen: boolean;
  onClose: () => void;
  initialData: Partial<AgendaEventFormData> & { id?: string };
  sellers: SellerOption[];
  onSubmit: (data: AgendaEventFormData) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
  isEditing: boolean;
}

const toLocalDatetimeInput = (isoOrDate: string | Date): string => {
  const d = new Date(isoOrDate);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

export default function AgendaEventForm({
  isOpen,
  onClose,
  initialData,
  sellers,
  onSubmit,
  onDelete,
  isEditing,
}: AgendaEventFormProps) {
  const { t } = useTranslation();
  const [formData, setFormData] = useState<AgendaEventFormData>({
    seller_id: 0,
    title: '',
    start_datetime: '',
    end_datetime: '',
    notes: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const firstSellerId = sellers.length > 0 ? sellers[0].id : 0;
      setFormData({
        seller_id: initialData.seller_id || firstSellerId,
        title: initialData.title || '',
        start_datetime: initialData.start_datetime ? toLocalDatetimeInput(initialData.start_datetime) : '',
        end_datetime: initialData.end_datetime ? toLocalDatetimeInput(initialData.end_datetime) : '',
        notes: initialData.notes || '',
      });
      setError(null);
    }
  }, [isOpen, initialData, sellers]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      setError(t('agenda_crm.title_required'));
      return;
    }
    if (!formData.start_datetime || !formData.end_datetime) {
      setError(t('agenda_crm.datetime_required'));
      return;
    }
    const start = new Date(formData.start_datetime);
    const end = new Date(formData.end_datetime);
    if (end <= start) {
      setError(t('agenda_crm.end_after_start'));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await onSubmit({
        ...formData,
        start_datetime: start.toISOString(),
        end_datetime: end.toISOString(),
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || t('agenda_crm.save_error'));
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-[#0d1117] rounded-2xl border border-white/[0.08] shadow-2xl max-w-md w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-white/[0.04]">
          <h2 className="text-lg font-semibold text-white">
            {isEditing ? t('agenda_crm.form_edit') : t('agenda_crm.form_new')}
          </h2>
          <button type="button" onClick={onClose} className="p-2 rounded-lg hover:bg-white/[0.04] text-white/40">
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 text-red-400 text-sm border border-red-500/20">{error}</div>
          )}
          <div>
            <label className="block text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">
              {t('agenda_crm.seller')}
            </label>
            <select
              value={formData.seller_id || ''}
              onChange={(e) => setFormData({ ...formData, seller_id: Number(e.target.value) })}
              className="w-full px-3 py-2 text-white bg-white/[0.04] border border-white/[0.08] rounded-xl focus:ring-2 focus:ring-violet-500 focus:border-violet-500"
              required
            >
              <option value="" className="bg-[#0d1117] text-white">{t('agenda_crm.select_seller')}</option>
              {sellers.map((s) => (
                <option key={s.id} value={s.id} className="bg-[#0d1117] text-white">
                  {s.first_name} {s.last_name || ''}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">
              {t('agenda_crm.title')} *
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-3 py-2 text-white bg-white/[0.04] border border-white/[0.08] rounded-xl placeholder-white/30 focus:ring-2 focus:ring-violet-500 focus:border-violet-500"
              placeholder={t('agenda_crm.title_placeholder')}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">
                {t('agenda_crm.start')} *
              </label>
              <input
                type="datetime-local"
                value={formData.start_datetime}
                onChange={(e) => setFormData({ ...formData, start_datetime: e.target.value })}
                className="w-full px-3 py-2 text-white bg-white/[0.04] border border-white/[0.08] rounded-xl placeholder-white/30 focus:ring-2 focus:ring-violet-500 focus:border-violet-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">
                {t('agenda_crm.end')} *
              </label>
              <input
                type="datetime-local"
                value={formData.end_datetime}
                onChange={(e) => setFormData({ ...formData, end_datetime: e.target.value })}
                className="w-full px-3 py-2 text-white bg-white/[0.04] border border-white/[0.08] rounded-xl placeholder-white/30 focus:ring-2 focus:ring-violet-500 focus:border-violet-500"
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">
              {t('agenda_crm.notes')}
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full px-3 py-2 text-white bg-white/[0.04] border border-white/[0.08] rounded-xl placeholder-white/30 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 resize-none"
              rows={3}
              placeholder={t('agenda_crm.notes_placeholder')}
            />
          </div>
          <div className="flex gap-2 pt-4 border-t border-white/[0.04]">
            {isEditing && onDelete && initialData.id && (
              <button
                type="button"
                onClick={() => onDelete(initialData.id!).then(() => onClose())}
                className="px-4 py-2 rounded-xl border border-red-500/20 text-red-400 hover:bg-red-500/10 active:scale-95 transition-all"
              >
                {t('agenda_crm.cancel_event')}
              </button>
            )}
            <div className="flex-1" />
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-xl bg-white/[0.06] text-white/70 hover:bg-white/[0.08] active:scale-95 transition-all">
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-50 active:scale-95 transition-all"
            >
              {loading ? t('common.loading') : t('agenda_crm.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
