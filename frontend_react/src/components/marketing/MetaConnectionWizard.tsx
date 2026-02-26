import React, { useState, useEffect } from 'react';
import { CheckCircle2, ChevronRight, Briefcase, BarChart3, Loader2, Zap, Building2, ShieldCheck } from 'lucide-react';
import api from '../../api/axios';

interface MetaConnectionWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export default function MetaConnectionWizard({ isOpen, onClose, onSuccess }: MetaConnectionWizardProps) {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [entityName, setEntityName] = useState<string>('');
    const [portfolios, setPortfolios] = useState<any[]>([]);
    const [accounts, setAccounts] = useState<any[]>([]);

    const [selectedPortfolio, setSelectedPortfolio] = useState<any>(null);
    const [selectedAccount, setSelectedAccount] = useState<any>(null);

    useEffect(() => {
        if (isOpen) {
            setStep(1);
            setSelectedPortfolio(null);
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
            setEntityName(configRes.data?.company_name || 'Entidad Actual');

            // Cargar Business Managers (Portfolios)
            const { data: portfoliosData } = await api.get('/crm/marketing/meta-portfolios');
            setPortfolios(portfoliosData?.data || []);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Error cargando datos iniciales.');
        } finally {
            setLoading(false);
        }
    };

    const loadAccounts = async (portfolioId?: string) => {
        setLoading(true);
        setError(null);
        try {
            const url = portfolioId
                ? `/crm/marketing/meta-accounts?portfolio_id=${portfolioId}`
                : `/crm/marketing/meta-accounts`;
            const { data } = await api.get(url);
            setAccounts(data?.data || []);
            setStep(3); // Pasar a paso 3 (Ad Accounts)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Error cargando cuentas de anuncios.');
        } finally {
            setLoading(false);
        }
    };

    const handleConnect = async () => {
        if (!selectedAccount) return;
        setLoading(true);
        setError(null);
        try {
            await api.post('/crm/marketing/connect', {
                account_id: selectedAccount.id,
                account_name: selectedAccount.name
            });
            setStep(4); // Éxito
            setTimeout(() => {
                onSuccess();
                onClose();
            }, 2200);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Error al conectar la cuenta. Intentá de nuevo.');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    const totalSteps = 3;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
            <div className="bg-white rounded-[28px] w-full max-w-lg overflow-hidden shadow-2xl my-auto">

                {/* Header */}
                <div className="p-7 border-b border-gray-100 bg-gradient-to-br from-blue-600 to-blue-700">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center text-white">
                            <BarChart3 size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Meta Ads Wizard</h2>
                            <p className="text-blue-100 text-sm">Conecta tu cuenta publicitaria de Meta</p>
                        </div>
                    </div>

                    {/* Step progress */}
                    {step < 4 && (
                        <div className="flex items-center gap-2 mt-5">
                            {[1, 2, 3].map((s) => (
                                <React.Fragment key={s}>
                                    <div className={`flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm transition-all ${step > s ? 'bg-green-400 text-white' :
                                        step === s ? 'bg-white text-blue-700' :
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
                            <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
                            <p className="text-gray-500 font-medium">Cargando datos...</p>
                        </div>
                    ) : (
                        <>
                            {/* STEP 1: Entity Confirmation */}
                            {step === 1 && (
                                <div className="space-y-6">
                                    <div className="text-center space-y-2">
                                        <p className="text-xs font-bold text-blue-600 uppercase tracking-wider">Paso 1 de 3</p>
                                        <h3 className="text-xl font-bold text-gray-900">Confirmar Entidad</h3>
                                        <p className="text-sm text-gray-500">
                                            Vas a conectar Meta Ads a la siguiente entidad de CRM Ventas:
                                        </p>
                                    </div>

                                    <div className="bg-blue-50 border border-blue-100 p-6 rounded-3xl flex flex-col items-center gap-3">
                                        <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center text-blue-600">
                                            <ShieldCheck size={32} />
                                        </div>
                                        <div className="text-center">
                                            <div className="text-lg font-bold text-gray-900">{entityName}</div>
                                            <div className="text-xs text-blue-600 font-semibold uppercase tracking-widest mt-1">Tenant Seleccionado</div>
                                        </div>
                                    </div>

                                    <button
                                        onClick={() => setStep(2)}
                                        className="w-full py-4 bg-gray-900 text-white rounded-2xl font-bold hover:bg-black transition-all shadow-lg flex items-center justify-center gap-2"
                                    >
                                        Siguiente <ChevronRight size={18} />
                                    </button>
                                </div>
                            )}

                            {/* STEP 2: Business Manager */}
                            {step === 2 && (
                                <div className="space-y-4">
                                    <div>
                                        <p className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">Paso 2 de 3</p>
                                        <h3 className="text-lg font-bold text-gray-900">Selecciona el Portafolio (BM)</h3>
                                        <p className="text-sm text-gray-500 mt-1">Elige el Business Manager que contiene tu cuenta de anuncios.</p>
                                    </div>
                                    <div className="grid gap-3 max-h-[300px] overflow-y-auto pr-1">
                                        {portfolios.map(p => (
                                            <button
                                                key={p.id}
                                                onClick={() => {
                                                    setSelectedPortfolio(p);
                                                    loadAccounts(p.id);
                                                }}
                                                className="w-full p-4 rounded-2xl border-2 border-gray-100 hover:border-blue-500 hover:bg-blue-50/50 transition-all text-left flex items-center justify-between group"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className="w-9 h-9 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center group-hover:bg-blue-100 transition-all">
                                                        <Building2 size={18} />
                                                    </div>
                                                    <div>
                                                        <div className="font-bold text-gray-900">{p.name}</div>
                                                        <div className="text-xs text-gray-400">ID: {p.id}</div>
                                                    </div>
                                                </div>
                                                <ChevronRight className="text-gray-300 group-hover:text-blue-500 transition-all" size={18} />
                                            </button>
                                        ))}
                                        {portfolios.length === 0 && !loading && (
                                            <div className="text-center py-8 space-y-4">
                                                <p className="text-gray-500 text-sm">No se encontraron Business Managers.</p>
                                                <button
                                                    onClick={() => loadAccounts()}
                                                    className="w-full py-3 bg-blue-50 text-blue-600 rounded-xl font-bold hover:bg-blue-100 transition-all text-sm"
                                                >
                                                    Listar todas las cuentas de anuncios →
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                    <button
                                        onClick={() => setStep(1)}
                                        className="w-full py-2 text-gray-400 font-bold hover:text-gray-600 transition-all text-xs"
                                    >
                                        ← Volver
                                    </button>
                                </div>
                            )}

                            {/* STEP 3: Ad Account */}
                            {step === 3 && (
                                <div className="space-y-4">
                                    <div>
                                        <p className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">Paso 3 de 3</p>
                                        <h3 className="text-lg font-bold text-gray-900">Elige la Cuenta de Anuncios</h3>
                                        {selectedPortfolio && (
                                            <p className="text-sm text-gray-500 mt-1">
                                                Portafolio: <strong className="text-gray-700">{selectedPortfolio.name}</strong>
                                            </p>
                                        )}
                                    </div>

                                    <div className="grid gap-3 max-h-[260px] overflow-y-auto pr-1">
                                        {accounts.map(a => (
                                            <button
                                                key={a.id}
                                                onClick={() => setSelectedAccount(a)}
                                                className={`w-full p-4 rounded-2xl border-2 transition-all text-left flex items-center justify-between ${selectedAccount?.id === a.id
                                                    ? 'border-blue-600 bg-blue-50'
                                                    : 'border-gray-100 hover:border-blue-400 hover:bg-blue-50/50'
                                                    }`}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all ${selectedAccount?.id === a.id ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500'
                                                        }`}>
                                                        <Briefcase size={16} />
                                                    </div>
                                                    <div>
                                                        <div className="font-bold text-gray-900">{a.name}</div>
                                                        <div className="flex items-center gap-2 mt-0.5">
                                                            <span className="text-[10px] font-bold bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded uppercase">{a.currency}</span>
                                                            {a.account_status === 1 && (
                                                                <span className="text-[10px] font-bold bg-green-100 text-green-700 px-1.5 py-0.5 rounded uppercase">Activa</span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                                {selectedAccount?.id === a.id && (
                                                    <CheckCircle2 className="text-blue-600 shrink-0" size={20} />
                                                )}
                                            </button>
                                        ))}

                                        {accounts.length === 0 && (
                                            <div className="bg-amber-50 rounded-2xl p-5 border border-amber-100 text-center space-y-3">
                                                <p className="font-bold text-amber-900 text-sm">No hay cuentas disponibles</p>
                                                <p className="text-xs text-amber-700">Asegurate de haber dado permiso a este Business Manager en el popup de Meta.</p>
                                                <button
                                                    onClick={() => loadAccounts()}
                                                    className="w-full py-2.5 bg-white border border-amber-200 text-amber-800 rounded-xl text-xs font-bold hover:bg-amber-50 transition-all"
                                                >
                                                    Buscar en todas las cuentas
                                                </button>
                                            </div>
                                        )}
                                    </div>

                                    {/* Manual ID input */}
                                    <div className="pt-4 border-t border-gray-100">
                                        <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">¿No ves tu cuenta?</p>
                                        <input
                                            type="text"
                                            placeholder="Pegar ID manual (ej. act_1234567890...)"
                                            className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition-all font-mono"
                                            onChange={(e) => {
                                                const val = e.target.value.trim();
                                                if (val) {
                                                    setSelectedAccount({ id: val, name: `Cuenta Manual (...${val.slice(-4)})`, currency: '—' });
                                                } else {
                                                    setSelectedAccount(null);
                                                }
                                            }}
                                        />
                                    </div>

                                    {/* Actions */}
                                    <div className="flex gap-3 pt-2">
                                        <button
                                            onClick={() => { setStep(2); setSelectedAccount(null); }}
                                            className="flex-1 py-3.5 text-gray-500 font-bold hover:bg-gray-50 rounded-2xl transition-all text-sm"
                                        >
                                            ← Atrás
                                        </button>
                                        <button
                                            disabled={!selectedAccount || loading}
                                            onClick={handleConnect}
                                            className="flex-2 px-8 py-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 text-sm"
                                        >
                                            {loading ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                                            Confirmar Conexión
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* SUCCESS: Success */}
                            {step === 4 && (
                                <div className="flex flex-col items-center justify-center py-10 gap-5 text-center">
                                    <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
                                        <CheckCircle2 className="text-green-600" size={44} />
                                    </div>
                                    <div>
                                        <h3 className="text-2xl font-bold text-gray-900">¡Conectado!</h3>
                                        <p className="text-gray-500 mt-2 text-sm">
                                            <strong className="text-gray-700">{selectedAccount?.name}</strong> está lista.<br />
                                            Sincronizando campañas y métricas...
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2 text-blue-600">
                                        <Loader2 size={16} className="animate-spin" />
                                        <span className="text-sm font-medium">Cargando datos de Meta Ads...</span>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Footer */}
                {step < 4 && !loading && (
                    <div className="px-7 pb-6 text-center">
                        <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600">
                            Cerrar asistente
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
