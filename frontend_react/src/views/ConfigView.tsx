import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, Globe, Loader2, CheckCircle2, Stethoscope, Users } from 'lucide-react';
import api from '../api/axios';
import { useTranslation } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import PageHeader from '../components/PageHeader';

type UiLanguage = 'es' | 'en' | 'fr';
type NicheType = 'dental' | 'crm_sales';

interface ClinicSettings {
    name: string;
    location?: string;
    hours_start?: string;
    hours_end?: string;
    ui_language: UiLanguage;
    niche_type?: NicheType;
}

const LANGUAGE_OPTIONS: { value: UiLanguage; labelKey: string }[] = [
    { value: 'es', labelKey: 'config.language_es' },
    { value: 'en', labelKey: 'config.language_en' },
    { value: 'fr', labelKey: 'config.language_fr' },
];

export default function ConfigView() {
    const { t, setLanguage } = useTranslation();
    const { updateUser } = useAuth();
    const navigate = useNavigate();
    const [settings, setSettings] = useState<ClinicSettings | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [nicheSaving, setNicheSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [selectedLang, setSelectedLang] = useState<UiLanguage>('en');
    const [nicheType, setNicheType] = useState<NicheType>('dental');

    useEffect(() => {
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        try {
            setLoading(true);
            const res = await api.get<ClinicSettings>('/admin/core/settings/clinic');
            setSettings(res.data);
            setSelectedLang((res.data.ui_language as UiLanguage) || 'en');
            const serverNiche = (res.data.niche_type as NicheType) || 'dental';
            setNicheType(serverNiche);
            updateUser({ niche_type: serverNiche });
        } catch (err) {
            setError(t('config.load_error'));
        } finally {
            setLoading(false);
        }
    };

    const handleLanguageChange = async (value: UiLanguage) => {
        setSelectedLang(value);
        setSuccess(null);
        setError(null);
        setLanguage(value);
        setSaving(true);
        try {
            await api.patch('/admin/core/settings/clinic', { ui_language: value });
            setSettings((prev) => (prev ? { ...prev, ui_language: value } : null));
            setSuccess(t('config.saved'));
        } catch (err) {
            setError(t('config.save_error'));
} finally {
        setSaving(false);
        }
    };

    const handleNicheChange = async (value: NicheType) => {
        if (value === nicheType) return;
        setSuccess(null);
        setError(null);
        setNicheSaving(true);
        try {
            const res = await api.patch<{ status: string; niche_type?: NicheType }>('/admin/core/settings/clinic', { niche_type: value });
            const newNiche = res.data.niche_type ?? value;
            setNicheType(newNiche);
            setSettings((prev) => (prev ? { ...prev, niche_type: newNiche } : null));
            updateUser({ niche_type: newNiche });
            setSuccess(t('config.niche_updated'));
            if (newNiche === 'crm_sales') navigate('/crm/leads', { replace: true });
            else navigate('/', { replace: true });
        } catch (err) {
            setError(t('config.save_error'));
        } finally {
            setNicheSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="p-6 flex items-center justify-center min-h-[200px]">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
        );
    }

    return (
        <div className="p-6 max-w-2xl">
            <PageHeader
                title={t('config.title')}
                subtitle={t('config.subtitle')}
                icon={<Settings size={22} />}
            />

            {settings && (
                <div className="space-y-6">
                    <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center gap-2 mb-4">
                            <Globe size={20} className="text-gray-600" />
                            <h2 className="text-lg font-semibold text-gray-800">{t('config.language_label')}</h2>
                        </div>
                        <p className="text-sm text-gray-500 mb-4">
                            {t('config.language_help')}
                        </p>
                        <div className="flex flex-wrap gap-3">
                            {LANGUAGE_OPTIONS.map((opt) => (
                                <button
                                    key={opt.value}
                                    type="button"
                                    onClick={() => handleLanguageChange(opt.value)}
                                    disabled={saving}
                                    className={`px-4 py-2.5 rounded-xl font-medium transition-colors border-2 min-h-[44px] touch-manipulation ${selectedLang === opt.value
                                            ? 'border-blue-600 bg-blue-50 text-blue-700'
                                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                                        }`}
                                >
                                    {saving && selectedLang === opt.value ? (
                                        <Loader2 className="w-5 h-5 animate-spin inline-block" />
                                    ) : (
                                        t(opt.labelKey)
                                    )}
                                </button>
                            ))}
                        </div>
                        <p className="text-xs text-gray-400 mt-3">
                            {t('config.current_clinic')}: <strong>{settings.name}</strong>
                        </p>
                    </div>

                    {/* Niche switch — handoff-style: one tap to switch Dental ↔ CRM Ventas */}
                    <div className="bg-white border-l-4 border-orange-500 border border-gray-200 rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center gap-2 mb-2">
                            <Users size={20} className="text-orange-600" />
                            <h2 className="text-lg font-semibold text-gray-800">{t('config.niche_label')}</h2>
                        </div>
                        <p className="text-sm text-gray-500 mb-4">
                            {t('config.niche_help')}
                        </p>
                        <div className="flex flex-wrap gap-3">
                            <button
                                type="button"
                                onClick={() => handleNicheChange('dental')}
                                disabled={nicheSaving}
                                className={`inline-flex items-center gap-2 px-5 py-3 rounded-xl font-medium transition-all border-2 min-h-[48px] touch-manipulation ${nicheType === 'dental'
                                    ? 'border-orange-500 bg-orange-50 text-orange-700 shadow-sm'
                                    : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                                    }`}
                            >
                                {nicheSaving && nicheType !== 'dental' ? <Loader2 className="w-5 h-5 animate-spin" /> : <Stethoscope size={20} />}
                                {t('config.niche_dental')}
                            </button>
                            <button
                                type="button"
                                onClick={() => handleNicheChange('crm_sales')}
                                disabled={nicheSaving}
                                className={`inline-flex items-center gap-2 px-5 py-3 rounded-xl font-medium transition-all border-2 min-h-[48px] touch-manipulation ${nicheType === 'crm_sales'
                                    ? 'border-orange-500 bg-orange-50 text-orange-700 shadow-sm'
                                    : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                                    }`}
                            >
                                {nicheSaving && nicheType !== 'crm_sales' ? <Loader2 className="w-5 h-5 animate-spin" /> : <Users size={20} />}
                                {t('config.niche_crm_sales')}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {error && (
                <div className="mt-4 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
                    {error}
                </div>
            )}
            {success && (
                <div className="mt-4 p-4 rounded-xl bg-green-50 border border-green-200 text-green-700 text-sm flex items-center gap-2">
                    <CheckCircle2 size={18} />
                    {success}
                </div>
            )}
        </div>
    );
}
