import React, { useState, useEffect } from 'react';
import { CheckCircle2, ChevronRight, Globe, BarChart3, Loader2, Zap, Building2, ShieldCheck, CreditCard } from 'lucide-react';
import api from '../../api/axios';
import { useTranslation } from '../../context/LanguageContext';

interface GoogleConnectionWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export default function GoogleConnectionWizard({ isOpen, onClose, onSuccess }: GoogleConnectionWizardProps) {
    const { t } = useTranslation();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [entityName, setEntityName] = useState<string>('');
    const [customerAccounts, setCustomerAccounts] = useState<any[]>([]);
    const [selectedAccount, setSelectedAccount] = useState<any>(null);

    useEffect(() => {
        if (isOpen) {
            setStep(1);
            setSelectedAccount(null);
            setError(null);
            loadInitialData();
        }
    }, [isOpen]);

    const loadInitialData = async () => {
        setLoading(true);
        setError(null);
        try {
            // Cargar configuración para obtener el nombre de la entidad
            const configRes = await api.get('/admin/config/deployment');
            setEntityName(configRes.data?.company_name || t('marketing.google_wizard.current_entity'));

            // Cargar cuentas de Google Ads accesibles
            const { data: accountsData } = await api.get('/crm/auth/google/ads/test-connection');
            
            if (accountsData?.data?.customer_ids && accountsData.data.customer_ids.length > 0) {
                setCustomerAccounts(accountsData.data.customer_ids.map((id: string) => ({
                    id,
                    name: `Google Ads Account ${id}`,
                    type: 'GOOGLE_ADS'
                })));
                setStep(2); // Pasar al paso de selección de cuenta
            } else {
                setError(t('marketing.google_wizard.no_accounts_found'));
            }
        } catch (err: any) {
            console.error("Error loading Google Ads data:", err);
            setError(err.response?.data?.detail || t('marketing.google_wizard.initial_data_error'));
        } finally {
            setLoading(false);
        }
    };

    const handleConnect = async () => {
        if (!selectedAccount) return;
        setLoading(true);
        setError(null);
        try {
            // En Google Ads, la conexión ya se realizó en el OAuth callback
            // Solo necesitamos confirmar y cerrar el wizard
            setStep(3); // Éxito
            setTimeout(() => {
                onSuccess();
                onClose();
            }, 2200);
        } catch (err: any) {
            setError(err.response?.data?.detail || t('marketing.google_wizard.connection_error'));
        } finally {
            setLoading(false);
        }
    };

    const handleTestConnection = async () => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await api.get('/crm/auth/google/ads/test-connection');
            
            if (data?.data?.connected) {
                setCustomerAccounts(data.data.customer_ids.map((id: string) => ({
                    id,
                    name: `Google Ads Account ${id}`,
                    type: 'GOOGLE_ADS'
                })));
                setStep(2);
            } else {
                setError(data?.data?.message || t('marketing.google_wizard.connection_test_failed'));
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || t('marketing.google_wizard.connection_test_error'));
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    const totalSteps = 2;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
            <div className="bg-white rounded-[28px] w-full max-w-lg overflow-hidden shadow-2xl my-auto">

                {/* Header */}
                <div className="p-7 border-b border-gray-100 bg-gradient-to-br from-green-600 to-green-700">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center text-white">
                            <Globe size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">{t('marketing.google_wizard.title')}</h2>
                            <p className="text-green-100 text-sm">{t('marketing.google_wizard.subtitle')}</p>
                        </div>
                    </div>

                    {/* Step progress */}
                    {step < 3 && (
                        <div className="flex items-center gap-2 mt-5">
                            {[1, 2].map((s) => (
                                <React.Fragment key={s}>
                                    <div className={`flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm transition-all ${step > s ? 'bg-green-400 text-white' :
                                        step === s ? 'bg-white text-green-700' :
                                            'bg-white/20 text-white/60'
                                        }`}>
                                        {step > s ? <CheckCircle2 size={16} /> : s}
                                    </div>
                                    {s < totalSteps && (
                                        <div className={`flex-1 h-0.5 transition-all ${step > s ? 'bg-green-400' : 'bg-white/20'}`} />
                                    )}
                                </React.Fragment>
                            ))}
                        </div>
                    )}
                </div>

                {/* Content */}
                <div className="p-7">
                    {error && (
                        <div className="mb-5 p-4 bg-red-50 text-red-700 rounded-2xl text-sm font-medium border border-red-100">
                            {error}
                        </div>
                    )}

                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-12 gap-4">
                            <Loader2 className="w-10 h-10 text-green-600 animate-spin" />
                            <p className="text-gray-500 font-medium">{t('marketing.google_wizard.loading')}</p>
                        </div>
                    ) : (
                        <>
                            {/* STEP 1: Entity Confirmation */}
                            {step === 1 && (
                                <div className="space-y-6">
                                    <div className="text-center space-y-2">
                                        <p className="text-xs font-bold text-green-600 uppercase tracking-wider">
                                            {t('marketing.google_wizard.step', { current: 1, total: 2 })}
                                        </p>
                                        <h3 className="text-xl font-bold text-gray-900">
                                            {t('marketing.google_wizard.confirm_entity_title')}
                                        </h3>
                                        <p className="text-sm text-gray-500">
                                            {t('marketing.google_wizard.confirm_entity_description')}
                                        </p>
                                    </div>

                                    <div className="bg-green-50 border border-green-100 p-6 rounded-3xl flex flex-col items-center gap-3">
                                        <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center text-green-600">
                                            <ShieldCheck size={32} />
                                        </div>
                                        <div className="text-center">
                                            <div className="text-lg font-bold text-gray-900">{entityName}</div>
                                            <div className="text-xs text-green-600 font-semibold uppercase tracking-widest mt-1">
                                                {t('marketing.google_wizard.selected_tenant')}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-4">
                                        <div className="bg-blue-50 border border-blue-100 p-4 rounded-2xl">
                                            <div className="flex items-start gap-3">
                                                <Zap className="w-5 h-5 text-blue-600 mt-0.5" />
                                                <div>
                                                    <p className="text-sm font-medium text-gray-900">
                                                        {t('marketing.google_wizard.oauth_completed')}
                                                    </p>
                                                    <p className="text-xs text-gray-500 mt-1">
                                                        {t('marketing.google_wizard.oauth_completed_description')}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>

                                        <button
                                            onClick={handleTestConnection}
                                            className="w-full py-4 bg-gray-900 text-white rounded-2xl font-bold hover:bg-black transition-all shadow-lg flex items-center justify-center gap-2"
                                        >
                                            {t('marketing.google_wizard.test_connection')}
                                            <ChevronRight size={18} />
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* STEP 2: Select Google Ads Account */}
                            {step === 2 && (
                                <div className="space-y-4">
                                    <div>
                                        <p className="text-xs font-bold text-green-600 uppercase tracking-wider mb-1">
                                            {t('marketing.google_wizard.step', { current: 2, total: 2 })}
                                        </p>
                                        <h3 className="text-lg font-bold text-gray-900">
                                            {t('marketing.google_wizard.select_account_title')}
                                        </h3>
                                        <p className="text-sm text-gray-500 mt-1">
                                            {t('marketing.google_wizard.select_account_description')}
                                        </p>
                                    </div>

                                    <div className="grid gap-3 max-h-[260px] overflow-y-auto pr-1">
                                        {customerAccounts.map(account => (
                                            <button
                                                key={account.id}
                                                onClick={() => setSelectedAccount(account)}
                                                className={`w-full p-4 rounded-2xl border-2 transition-all text-left flex items-center justify-between ${selectedAccount?.id === account.id
                                                    ? 'border-green-600 bg-green-50'
                                                    : 'border-gray-100 hover:border-green-400 hover:bg-green-50/50'
                                                    }`}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all ${selectedAccount?.id === account.id ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-500'
                                                        }`}>
                                                        <CreditCard size={18} />
                                                    </div>
                                                    <div>
                                                        <div className="font-bold text-gray-900">{account.name}</div>
                                                        <div className="text-xs text-gray-400">ID: {account.id}</div>
                                                    </div>
                                                </div>
                                                {selectedAccount?.id === account.id ? (
                                                    <CheckCircle2 className="text-green-600" size={18} />
                                                ) : (
                                                    <ChevronRight className="text-gray-300" size={18} />
                                                )}
                                            </button>
                                        ))}
                                    </div>

                                    <div className="flex gap-3 pt-2">
                                        <button
                                            onClick={() => setStep(1)}
                                            className="flex-1 py-3 border border-gray-200 text-gray-600 rounded-xl font-bold hover:bg-gray-50 transition-all"
                                        >
                                            {t('marketing.google_wizard.back')}
                                        </button>
                                        <button
                                            onClick={handleConnect}
                                            disabled={!selectedAccount}
                                            className={`flex-1 py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2 ${selectedAccount
                                                ? 'bg-green-600 text-white hover:bg-green-700'
                                                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                                }`}
                                        >
                                            {t('marketing.google_wizard.finish')}
                                            <CheckCircle2 size={18} />
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* STEP 3: Success */}
                            {step === 3 && (
                                <div className="text-center space-y-6 py-4">
                                    <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                                        <CheckCircle2 className="w-12 h-12 text-green-600" />
                                    </div>
                                    <div>
                                        <h3 className="text-2xl font-bold text-gray-900">
                                            {t('marketing.google_wizard.success_title')}
                                        </h3>
                                        <p className="text-gray-500 mt-2">
                                            {t('marketing.google_wizard.success_description')}
                                        </p>
                                        {selectedAccount && (
                                            <div className="mt-4 inline-flex items-center gap-2 bg-green-50 text-green-700 px-4 py-2 rounded-full text-sm font-medium">
                                                <Globe size={14} />
                                                {selectedAccount.name}
                                            </div>
                                        )}
                                    </div>
                                    <div className="pt-4">
                                        <div className="text-xs text-gray-400 font-medium">
                                            {t('marketing.google_wizard.redirecting')}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}