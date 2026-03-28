import React, { useState, useEffect } from 'react';
import { X, Calendar, User, Clock, FileText, DollarSign, Building2, AlertTriangle, Trash2, Check } from 'lucide-react';
import type { Appointment, Patient, Professional } from '../views/AgendaView';
import api from '../api/axios';
import { useTranslation } from '../context/LanguageContext';

interface AppointmentFormProps {
    isOpen: boolean;
    onClose: () => void;
    initialData: Partial<Appointment>;
    professionals: Professional[];
    patients: Patient[];
    onSubmit: (data: any) => Promise<void>;
    onDelete?: (id: string) => Promise<void>;
    isEditing: boolean;
}

type TabType = 'general' | 'negocio' | 'billing';

export default function AppointmentForm({
    isOpen,
    onClose,
    initialData,
    professionals,
    patients,
    onSubmit,
    onDelete,
    isEditing
}: AppointmentFormProps) {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState<TabType>('general');
    const [formData, setFormData] = useState({
        patient_id: '',
        professional_id: '',
        appointment_datetime: '',
        appointment_type: 'checkup',
        notes: '',
        duration_minutes: 30
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [collisionWarning, setCollisionWarning] = useState<string | null>(null);

    // Treatment types with base_price
    const [treatmentTypes, setTreatmentTypes] = useState<any[]>([]);
    useEffect(() => {
        api.get('/admin/treatment_types', { params: { only_active: true } })
            .then(res => setTreatmentTypes(res.data))
            .catch(() => setTreatmentTypes([
                { code: 'checkup', name: 'Consulta' },
                { code: 'cleaning', name: 'Limpieza' },
                { code: 'emergency', name: 'Urgencia' }
            ]));
    }, []);

    // Business info state (Negocio tab)
    const [businessData, setBusinessData] = useState({
        company_name: '', industry: '', company_size: '', budget_range: '', decision_maker: '', pain_points: ''
    });

    // Billing state
    const [billingData, setBillingData] = useState({
        billing_amount: '', billing_installments: '', billing_notes: '', payment_status: 'pending',
        deal_value: '', commission_estimate: '', payment_method: '',
    });
    const [billingSaving, setBillingSaving] = useState(false);
    const [billingSuccess, setBillingSuccess] = useState<string | null>(null);
    const [fullAppointment, setFullAppointment] = useState<any>(null);

    // Format date for datetime-local input: local YYYY-MM-DDTHH:mm (avoid UTC display bug)
    const toLocalDatetimeInput = (isoOrDate: string | Date): string => {
        const d = new Date(isoOrDate);
        const pad = (n: number) => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };

    // Initialize form data
    useEffect(() => {
        if (isOpen) {
            setFormData({
                patient_id: initialData.patient_id?.toString() || '',
                professional_id: initialData.professional_id?.toString() || (professionals.length > 0 ? professionals[0].id.toString() : ''),
                appointment_datetime: initialData.appointment_datetime ? toLocalDatetimeInput(initialData.appointment_datetime) : '',
                appointment_type: initialData.appointment_type || 'checkup',
                notes: initialData.notes || '',
                duration_minutes: initialData.duration_minutes || 30
            });
            setError(null);
            setCollisionWarning(null);
            setActiveTab('general');
            setBillingSuccess(null);
            setFullAppointment(null);

            // Fetch full appointment for billing data
            if (isEditing && initialData.id) {
                api.get(`/admin/appointments/${initialData.id}`)
                    .then(res => {
                        const apt = res.data;
                        setFullAppointment(apt);
                        let amount = apt.billing_amount != null && apt.billing_amount > 0 ? String(apt.billing_amount) : '';
                        if (!amount && apt.appointment_type && treatmentTypes.length > 0) {
                            const tt = treatmentTypes.find((t: any) => t.code === apt.appointment_type);
                            if (tt?.base_price && tt.base_price > 0) amount = String(tt.base_price);
                        }
                        setBillingData({
                            billing_amount: amount,
                            billing_installments: apt.billing_installments != null ? String(apt.billing_installments) : '',
                            billing_notes: apt.billing_notes || '',
                            payment_status: apt.payment_status || 'pending',
                            deal_value: apt.deal_value != null ? String(apt.deal_value) : '',
                            commission_estimate: apt.commission_estimate != null ? String(apt.commission_estimate) : '',
                            payment_method: apt.payment_method || '',
                        });
                    })
                    .catch(() => {
                        setBillingData({ billing_amount: '', billing_installments: '', billing_notes: '', payment_status: 'pending', deal_value: '', commission_estimate: '', payment_method: '' });
                    });
            } else {
                setBillingData({ billing_amount: '', billing_installments: '', billing_notes: '', payment_status: 'pending', deal_value: '', commission_estimate: '', payment_method: '' });
            }
        }
    }, [isOpen, initialData, professionals, isEditing]);

    // Fix race condition: auto-fill billing when treatmentTypes load after appointment data
    useEffect(() => {
        if (!fullAppointment || !treatmentTypes.length) return;
        setBillingData(prev => {
            if (prev.billing_amount || !fullAppointment.appointment_type) return prev;
            const tt = treatmentTypes.find((t: any) => t.code === fullAppointment.appointment_type);
            if (tt?.base_price && tt.base_price > 0) {
                return { ...prev, billing_amount: String(tt.base_price) };
            }
            return prev;
        });
    }, [treatmentTypes, fullAppointment]);

    // Check collisions
    const checkCollisions = async (profId: string, dateStr: string) => {
        if (!profId || !dateStr) return;
        try {
            const response = await api.get('/admin/appointments/check-collisions', {
                params: {
                    professional_id: profId,
                    datetime_str: dateStr,
                    duration_minutes: formData.duration_minutes,
                    exclude_appointment_id: isEditing ? initialData.id : undefined
                }
            });

            if (response.data.has_collisions) {
                const conflicts = [];
                if (response.data.conflicting_appointments?.length) conflicts.push('Turno existente');
                if (response.data.conflicting_blocks?.length) conflicts.push('Bloqueo GCal');
                setCollisionWarning(`⚠️ Conflicto detectado: ${conflicts.join(', ')}`);
            } else {
                setCollisionWarning(null);
            }
        } catch (err) {
            console.error('Error checking collisions:', err);
        }
    };

    const handleChange = (field: string, value: any) => {
        setFormData(prev => {
            const newData = { ...prev, [field]: value };
            if (field === 'professional_id' || field === 'appointment_datetime' || field === 'duration_minutes') {
                checkCollisions(newData.professional_id || prev.professional_id, newData.appointment_datetime || prev.appointment_datetime);
            }
            return newData;
        });
    };

    const handleSubmit = async () => {
        if (!formData.patient_id || !formData.professional_id || !formData.appointment_datetime) {
            setError('Por favor complete los campos requeridos');
            return;
        }

        setLoading(true);
        try {
            // Send datetime as ISO so backend parses correctly (datetime-local gives local YYYY-MM-DDThh:mm)
            const payload = {
                ...formData,
                appointment_datetime: new Date(formData.appointment_datetime).toISOString(),
            };
            await onSubmit(payload);
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.message || 'Error al guardar');
        } finally {
            setLoading(false);
        }
    };

    // Close on Escape key
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleEsc);
        return () => window.removeEventListener('keydown', handleEsc);
    }, [onClose]);

    if (!isOpen) return null;

    const handleDelete = async () => {
        if (!onDelete || !initialData.id) return;
        if (confirm(t('alerts.confirm_delete_appointment'))) {
            setLoading(true);
            try {
                await onDelete(initialData.id);
                onClose();
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
    };

    const renderTabButton = (id: TabType, label: string, icon: any) => (
        <button
            type="button"
            onClick={() => setActiveTab(id)}
            className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === id
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-white/40 hover:text-white/70 hover:bg-white/[0.04]'
                }`}
        >
            {React.createElement(icon, { size: 16 })}
            {label}
        </button>
    );

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/20 backdrop-blur-sm z-[60] transition-opacity duration-300"
                onClick={onClose}
            />

            {/* Slide-over Panel */}
            <div
                className={`fixed inset-y-0 right-0 z-[70] w-full md:w-[450px] bg-[#0d1117] backdrop-blur-xl shadow-2xl shadow-black/20 transform transition-transform duration-300 ease-out border-l border-white/[0.06] flex flex-col ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
            >
                <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.04] bg-white/[0.02]">
                    <div>
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            {isEditing ? t('agenda.form_edit_appointment') : t('agenda.form_new_appointment')}
                            {isEditing && initialData.patient_id && (() => {
                                const leadPatient = patients.find(p => String(p.id) === String(initialData.patient_id));
                                return leadPatient ? (
                                    <span className="text-base font-normal text-white/60">— {leadPatient.first_name} {leadPatient.last_name}</span>
                                ) : null;
                            })()}
                        </h2>
                        <div className="flex items-center gap-2">
                            <p className="text-xs text-white/40">Sales CRM</p>
                            {(initialData as any)?.source && (
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
                                    {(initialData as any).source}
                                </span>
                            )}
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/[0.06] rounded-full text-white/30 hover:text-white/60 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="flex border-b border-white/[0.04] bg-white/[0.02]">
                    {renderTabButton('general', t('agenda.tab_general'), FileText)}
                    {renderTabButton('negocio', 'Negocio', Building2)}
                    {renderTabButton('billing', 'Facturacion', DollarSign)}
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {error && (
                        <div className="p-3 bg-red-500/10 text-red-400 text-sm rounded-lg flex items-center gap-2">
                            <AlertTriangle size={16} />
                            {error}
                        </div>
                    )}

                    {activeTab === 'general' && (
                        <div className="space-y-5">
                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">{t('agenda.patient')}</label>
                                <div className="relative">
                                    <User className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" size={18} />
                                    <select
                                        className="w-full pl-10 pr-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white focus:bg-white/[0.06] focus:border-blue-500 focus:ring-0 transition-all text-sm cursor-pointer"
                                        value={formData.patient_id}
                                        onChange={(e) => handleChange('patient_id', e.target.value)}
                                        disabled={isEditing}
                                    >
                                        <option value="" className="bg-[#0d1117] text-white">{t('agenda.select_patient')}</option>
                                        {patients.map(p => (
                                            <option key={p.id} value={p.id} className="bg-[#0d1117] text-white">{p.first_name} {p.last_name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">{t('agenda.professional')}</label>
                                <div className="relative">
                                    <User className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" size={18} />
                                    <select
                                        className="w-full pl-10 pr-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white focus:bg-white/[0.06] focus:border-blue-500 focus:ring-0 transition-all text-sm cursor-pointer"
                                        value={formData.professional_id}
                                        onChange={(e) => handleChange('professional_id', e.target.value)}
                                    >
                                        <option value="" className="bg-[#0d1117] text-white">{t('agenda.select_professional')}</option>
                                        {professionals.map(p => (
                                            <option key={p.id} value={p.id} className="bg-[#0d1117] text-white">{p.first_name} {p.last_name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">{t('agenda.date_time')}</label>
                                    <div className="relative">
                                        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" size={18} />
                                        <input
                                            type="datetime-local"
                                            className="w-full pl-10 pr-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white focus:bg-white/[0.06] focus:border-blue-500 focus:ring-0 transition-all text-sm"
                                            value={formData.appointment_datetime}
                                            onChange={(e) => handleChange('appointment_datetime', e.target.value)}
                                        />
                                    </div>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">{t('agenda.duration_min')}</label>
                                    <div className="relative">
                                        <Clock className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" size={18} />
                                        <select
                                            className="w-full pl-10 pr-4 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white focus:bg-white/[0.06] focus:border-blue-500 focus:ring-0 transition-all text-sm cursor-pointer"
                                            value={formData.duration_minutes}
                                            onChange={(e) => handleChange('duration_minutes', parseInt(e.target.value))}
                                        >
                                            <option value="15" className="bg-[#0d1117] text-white">15 min</option>
                                            <option value="30" className="bg-[#0d1117] text-white">30 min</option>
                                            <option value="45" className="bg-[#0d1117] text-white">45 min</option>
                                            <option value="60" className="bg-[#0d1117] text-white">60 min</option>
                                            <option value="90" className="bg-[#0d1117] text-white">90 min</option>
                                            <option value="120" className="bg-[#0d1117] text-white">2 horas</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            {collisionWarning && (
                                <div className="p-3 bg-yellow-500/10 text-yellow-400 text-xs rounded-lg flex items-start gap-2 border border-yellow-500/20">
                                    <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                                    <span>{collisionWarning}</span>
                                </div>
                            )}

                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">{t('agenda.appointment_type')}</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {(treatmentTypes.length > 0 ? treatmentTypes : [
                                        { code: 'checkup', name: 'Consulta' }, { code: 'cleaning', name: 'Limpieza' },
                                        { code: 'ortho', name: 'Ortodoncia' }, { code: 'surgery', name: 'Cirugía' },
                                        { code: 'emergency', name: 'Urgencia' }
                                    ]).map((s: any) => (
                                        <button
                                            key={s.code}
                                            type="button"
                                            onClick={() => {
                                                handleChange('appointment_type', s.code);
                                                if (s.base_price && s.base_price > 0) {
                                                    setBillingData(prev => ({ ...prev, billing_amount: String(s.base_price) }));
                                                }
                                            }}
                                            className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${formData.appointment_type === s.code
                                                ? 'bg-blue-500/10 border-blue-500/20 text-blue-400'
                                                : 'bg-white/[0.03] border-white/[0.06] text-white/50 hover:bg-white/[0.04]'
                                                }`}
                                        >
                                            {s.name || s.code}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">{t('agenda.notes')}</label>
                                <textarea
                                    className="w-full p-3 bg-white/[0.04] border border-white/[0.08] text-white rounded-lg focus:bg-white/[0.06] focus:border-blue-500 focus:ring-0 transition-all text-sm min-h-[100px]"
                                    placeholder={t('agenda.notes_placeholder')}
                                    value={formData.notes}
                                    onChange={(e) => handleChange('notes', e.target.value)}
                                />
                            </div>
                        </div>
                    )}

                    {activeTab === 'negocio' && (
                        <div className="space-y-5">
                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">Empresa</label>
                                <input
                                    type="text"
                                    placeholder="Nombre de la empresa"
                                    className="w-full px-3 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/40 placeholder-white/20"
                                    value={businessData.company_name}
                                    onChange={(e) => setBusinessData(prev => ({ ...prev, company_name: e.target.value }))}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">Industria</label>
                                    <select
                                        className="w-full px-3 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/40 cursor-pointer"
                                        value={businessData.industry}
                                        onChange={(e) => setBusinessData(prev => ({ ...prev, industry: e.target.value }))}
                                    >
                                        <option value="" className="bg-[#0d1117] text-white">Seleccionar...</option>
                                        <option value="tecnologia" className="bg-[#0d1117] text-white">Tecnologia</option>
                                        <option value="salud" className="bg-[#0d1117] text-white">Salud</option>
                                        <option value="educacion" className="bg-[#0d1117] text-white">Educacion</option>
                                        <option value="retail" className="bg-[#0d1117] text-white">Retail</option>
                                        <option value="finanzas" className="bg-[#0d1117] text-white">Finanzas</option>
                                        <option value="manufactura" className="bg-[#0d1117] text-white">Manufactura</option>
                                        <option value="servicios" className="bg-[#0d1117] text-white">Servicios</option>
                                        <option value="otro" className="bg-[#0d1117] text-white">Otro</option>
                                    </select>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">Tamano empresa</label>
                                    <select
                                        className="w-full px-3 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/40 cursor-pointer"
                                        value={businessData.company_size}
                                        onChange={(e) => setBusinessData(prev => ({ ...prev, company_size: e.target.value }))}
                                    >
                                        <option value="" className="bg-[#0d1117] text-white">Seleccionar...</option>
                                        <option value="1-10" className="bg-[#0d1117] text-white">1-10 empleados</option>
                                        <option value="11-50" className="bg-[#0d1117] text-white">11-50 empleados</option>
                                        <option value="51-200" className="bg-[#0d1117] text-white">51-200 empleados</option>
                                        <option value="201-500" className="bg-[#0d1117] text-white">201-500 empleados</option>
                                        <option value="500+" className="bg-[#0d1117] text-white">500+ empleados</option>
                                    </select>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">Rango de presupuesto</label>
                                    <select
                                        className="w-full px-3 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/40 cursor-pointer"
                                        value={businessData.budget_range}
                                        onChange={(e) => setBusinessData(prev => ({ ...prev, budget_range: e.target.value }))}
                                    >
                                        <option value="" className="bg-[#0d1117] text-white">Seleccionar...</option>
                                        <option value="<5k" className="bg-[#0d1117] text-white">Menos de $5,000</option>
                                        <option value="5k-15k" className="bg-[#0d1117] text-white">$5,000 - $15,000</option>
                                        <option value="15k-50k" className="bg-[#0d1117] text-white">$15,000 - $50,000</option>
                                        <option value="50k-100k" className="bg-[#0d1117] text-white">$50,000 - $100,000</option>
                                        <option value="100k+" className="bg-[#0d1117] text-white">$100,000+</option>
                                    </select>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">Decision maker</label>
                                    <input
                                        type="text"
                                        placeholder="Nombre del decisor"
                                        className="w-full px-3 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/40 placeholder-white/20"
                                        value={businessData.decision_maker}
                                        onChange={(e) => setBusinessData(prev => ({ ...prev, decision_maker: e.target.value }))}
                                    />
                                </div>
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider">Pain points</label>
                                <textarea
                                    rows={3}
                                    placeholder="Problemas o necesidades del lead..."
                                    className="w-full px-3 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm resize-none focus:outline-none focus:border-blue-500/40 placeholder-white/20"
                                    value={businessData.pain_points}
                                    onChange={(e) => setBusinessData(prev => ({ ...prev, pain_points: e.target.value }))}
                                />
                            </div>
                        </div>
                    )}

                    {activeTab === 'billing' && (
                        <div className="space-y-5 p-1">
                            {!isEditing && (
                                <div className="text-center py-6 text-white/30 bg-white/[0.02] rounded-xl border border-white/[0.06]">
                                    <DollarSign size={32} className="mx-auto mb-2 opacity-30" />
                                    <p className="text-sm">Guarda la reunion primero para facturar</p>
                                </div>
                            )}
                            {isEditing && (
                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs font-semibold text-white/50">Monto ($)</label>
                                            <input type="number" step="0.01" placeholder="0.00"
                                                className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/40 placeholder-white/20"
                                                value={billingData.billing_amount}
                                                onChange={(e) => setBillingData(prev => ({ ...prev, billing_amount: e.target.value }))} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-white/50">Valor del deal ($)</label>
                                            <input type="number" step="0.01" placeholder="0.00"
                                                className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/40 placeholder-white/20"
                                                value={billingData.deal_value}
                                                onChange={(e) => setBillingData(prev => ({ ...prev, deal_value: e.target.value }))} />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs font-semibold text-white/50">Comision estimada ($)</label>
                                            <input type="number" step="0.01" placeholder="0.00"
                                                className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/40 placeholder-white/20"
                                                value={billingData.commission_estimate}
                                                onChange={(e) => setBillingData(prev => ({ ...prev, commission_estimate: e.target.value }))} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-white/50">Metodo de pago</label>
                                            <select
                                                className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500/40 cursor-pointer"
                                                value={billingData.payment_method}
                                                onChange={(e) => setBillingData(prev => ({ ...prev, payment_method: e.target.value }))}
                                            >
                                                <option value="" className="bg-[#0d1117] text-white">Seleccionar...</option>
                                                <option value="transferencia" className="bg-[#0d1117] text-white">Transferencia</option>
                                                <option value="tarjeta" className="bg-[#0d1117] text-white">Tarjeta</option>
                                                <option value="efectivo" className="bg-[#0d1117] text-white">Efectivo</option>
                                                <option value="cheque" className="bg-[#0d1117] text-white">Cheque</option>
                                                <option value="otro" className="bg-[#0d1117] text-white">Otro</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="text-xs font-semibold text-white/50">Notas de facturacion</label>
                                        <textarea rows={3} placeholder="Observaciones..."
                                            className="mt-1 w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-sm resize-none focus:outline-none focus:border-blue-500/40 placeholder-white/20"
                                            value={billingData.billing_notes}
                                            onChange={(e) => setBillingData(prev => ({ ...prev, billing_notes: e.target.value }))} />
                                    </div>
                                    <div>
                                        <label className="text-xs font-semibold text-white/50 mb-2 block">Estado de pago</label>
                                        <div className="grid grid-cols-3 gap-2">
                                            {['pending', 'partial', 'paid'].map(ps => (
                                                <button key={ps} type="button"
                                                    onClick={() => setBillingData(prev => ({ ...prev, payment_status: ps }))}
                                                    className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                                                        billingData.payment_status === ps
                                                            ? ps === 'paid' ? 'bg-green-500/15 border-green-500/30 text-green-400'
                                                            : ps === 'partial' ? 'bg-yellow-500/15 border-yellow-500/30 text-yellow-400'
                                                            : 'bg-blue-500/15 border-blue-500/30 text-blue-400'
                                                        : 'bg-white/[0.03] border-white/[0.06] text-white/40 hover:bg-white/[0.04]'
                                                    }`}>
                                                    {ps === 'pending' ? 'Pendiente' : ps === 'partial' ? 'Parcial' : 'Pagado'}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="flex items-center justify-between pt-3 border-t border-white/[0.06]">
                                        {billingSuccess && (
                                            <span className="text-xs text-green-400 flex items-center gap-1">Guardado</span>
                                        )}
                                        {!billingSuccess && <span />}
                                        <button type="button" disabled={billingSaving}
                                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 active:scale-95 transition-all disabled:opacity-50"
                                            onClick={async () => {
                                                setBillingSaving(true); setBillingSuccess(null);
                                                try {
                                                    await api.put(`/admin/appointments/${initialData.id}/billing`, {
                                                        billing_amount: billingData.billing_amount ? parseFloat(billingData.billing_amount) : null,
                                                        billing_installments: billingData.billing_installments ? parseInt(billingData.billing_installments) : null,
                                                        billing_notes: billingData.billing_notes || null,
                                                        payment_status: billingData.payment_status,
                                                        deal_value: billingData.deal_value ? parseFloat(billingData.deal_value) : null,
                                                        commission_estimate: billingData.commission_estimate ? parseFloat(billingData.commission_estimate) : null,
                                                        payment_method: billingData.payment_method || null,
                                                    });
                                                    setBillingSuccess('Guardado');
                                                    setTimeout(() => setBillingSuccess(null), 3000);
                                                } catch (err) { console.error('Error saving billing:', err); }
                                                finally { setBillingSaving(false); }
                                            }}>
                                            {billingSaving ? <div className="w-4 h-4 border-2 border-gray-900 border-t-transparent rounded-full animate-spin" /> : <DollarSign size={16} />}
                                            Guardar facturacion
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="sticky bottom-0 bg-[#0d1117]/90 backdrop-blur-md border-t border-white/[0.04] p-4 flex items-center justify-between gap-4">
                    {isEditing && onDelete ? (
                        <button
                            type="button"
                            onClick={handleDelete}
                            className="p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                        >
                            <Trash2 size={20} />
                        </button>
                    ) : <div />}

                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-white/50 hover:bg-white/[0.06] rounded-lg transition-colors"
                        >
                            {t('common.cancel')}
                        </button>
                        <button
                            type="button"
                            onClick={handleSubmit}
                            disabled={loading}
                            className={`px-6 py-2 text-sm font-medium text-white rounded-lg shadow-lg shadow-blue-500/30 flex items-center gap-2 transition-all ${loading ? 'bg-blue-400 cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 hover:scale-[1.02]'
                                }`}
                        >
                            {loading ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Check size={16} />}
                            {isEditing ? t('common.save_changes') : t('agenda.schedule_appointment')}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}
