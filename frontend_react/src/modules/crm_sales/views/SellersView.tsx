import React, { useState, useEffect } from 'react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import {
    UserCheck, UserX, Clock, ShieldCheck, Mail, AlertTriangle, User, Users,
    Lock, Unlock, X, Building2, BarChart3, Plus, Phone, Save, Settings, Edit
} from 'lucide-react';

const CRM_PREFIX = '/admin/core/crm';

interface StaffUser {
    id: string;
    email: string;
    role: string;
    status: 'pending' | 'active' | 'suspended';
    created_at: string;
    first_name?: string;
    last_name?: string;
}

interface SellerRow {
    id: number;
    tenant_id: number;
    user_id: string;
    first_name?: string;
    last_name?: string;
    email?: string;
    phone_number?: string;
    is_active?: boolean;
    role: string;
}

interface TenantOption {
    id: number;
    clinic_name: string;
}

type KpisByRowRecord = Record<string, { total_leads: number; by_status: Record<string, number> }>;

const SellersView: React.FC = () => {
    const { t } = useTranslation();
    const [users, setUsers] = useState<StaffUser[]>([]);
    const [sellers, setSellers] = useState<SellerRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'requests' | 'sellers'>('requests');
    const [selectedSeller, setSelectedSeller] = useState<SellerRow | null>(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [sellerRows, setSellerRows] = useState<SellerRow[]>([]);
    const [entities, setEntities] = useState<TenantOption[]>([]);
    const [showLinkForm, setShowLinkForm] = useState(false);
    const [linkFormData, setLinkFormData] = useState({ tenant_id: null as number | null, phone: '' });
    const [linkFormSubmitting, setLinkFormSubmitting] = useState(false);
    const [editingRow, setEditingRow] = useState<SellerRow | null>(null);
    const [editFormData, setEditFormData] = useState({
        first_name: '', last_name: '', email: '', phone_number: '', is_active: true,
    });
    const [editFormSubmitting, setEditFormSubmitting] = useState(false);
    const [kpisByRow, setKpisByRow] = useState<KpisByRowRecord>({});

    useEffect(() => {
        fetchUsers();
        fetchSellers();
    }, []);

    useEffect(() => {
        api.get<TenantOption[]>(`/admin/core/chat/tenants`).then((res) => {
            setEntities(res.data || []);
        }).catch(() => setEntities([]));
    }, []);

    useEffect(() => {
        if (!selectedSeller) {
            setSellerRows([]);
            setKpisByRow({});
            return;
        }
        setDetailLoading(true);
        api.get<SellerRow[]>(`${CRM_PREFIX}/sellers/by-user/${selectedSeller.user_id}`)
            .then((res) => setSellerRows(res.data || []))
            .catch(() => setSellerRows([]))
            .finally(() => setDetailLoading(false));
    }, [selectedSeller?.user_id]);

    const fetchUsers = async () => {
        try {
            const response = await api.get<StaffUser[]>('/admin/core/users');
            setUsers(response.data || []);
        } catch {
            setError(t('approvals.error_load_users'));
        } finally {
            setLoading(false);
        }
    };

    const fetchSellers = async () => {
        try {
            const response = await api.get<SellerRow[]>(`${CRM_PREFIX}/sellers`);
            setSellers(response.data || []);
        } catch {
            setSellers([]);
        }
    };

    const handleAction = async (userId: string, action: 'active' | 'suspended') => {
        try {
            await api.post(`/admin/core/users/${userId}/status`, { status: action });
            setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, status: action } : u)));
            if (action === 'active') fetchSellers();
        } catch {
            alert(t('alerts.error_process'));
        }
    };

    const closeDetailModal = () => {
        setSelectedSeller(null);
        setShowLinkForm(false);
        setLinkFormData({ tenant_id: null, phone: '' });
        setKpisByRow({});
    };

    const loadKpis = async (row: SellerRow) => {
        const key = `${row.id}-${row.tenant_id}`;
        if (kpisByRow[key]) return;
        try {
            const now = new Date();
            const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
            const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);
            const res = await api.get(`${CRM_PREFIX}/sellers/${row.id}/analytics`, {
                params: { tenant_id: row.tenant_id, start_date: start, end_date: end },
            });
            setKpisByRow((prev) => ({ ...prev, [key]: { total_leads: res.data.total_leads || 0, by_status: res.data.by_status || {} } }));
        } catch {
            setKpisByRow((prev) => ({ ...prev, [key]: { total_leads: 0, by_status: {} } }));
        }
    };

    const handleRemoveAccess = async () => {
        if (!selectedSeller || !confirm(t('sellers.confirm_remove_access'))) return;
        try {
            await api.post(`/admin/core/users/${selectedSeller.user_id}/status`, { status: 'suspended' });
            closeDetailModal();
            fetchUsers();
            fetchSellers();
        } catch {
            alert(t('approvals.error_process'));
        }
    };

    const handleLinkToEntitySubmit = async (e: React.FormEvent) => {
        if (!selectedSeller) return;
        const tenant_id = linkFormData.tenant_id ?? entities[0]?.id;
        if (!tenant_id) {
            alert(t('sellers.select_entity'));
            return;
        }
        e.preventDefault();
        setLinkFormSubmitting(true);
        try {
            await api.post(`${CRM_PREFIX}/sellers`, {
                first_name: selectedSeller.first_name || '',
                last_name: selectedSeller.last_name || '',
                email: selectedSeller.email,
                phone_number: linkFormData.phone || undefined,
                tenant_id,
                role: selectedSeller.role,
            });
            const res = await api.get<SellerRow[]>(`${CRM_PREFIX}/sellers/by-user/${selectedSeller.user_id}`);
            setSellerRows(res.data || []);
            setShowLinkForm(false);
            setLinkFormData({ tenant_id: null, phone: '' });
            fetchSellers();
        } catch (err: any) {
            alert(err?.response?.data?.detail || t('sellers.error_link_entity'));
        } finally {
            setLinkFormSubmitting(false);
        }
    };

    const openEditModal = (row: SellerRow) => {
        setEditingRow(row);
        setEditFormData({
            first_name: row.first_name || '',
            last_name: row.last_name || '',
            email: row.email || '',
            phone_number: row.phone_number || '',
            is_active: row.is_active ?? true,
        });
    };

    const closeEditModal = () => {
        setEditingRow(null);
    };

    const handleEditSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingRow) return;
        setEditFormSubmitting(true);
        try {
            await api.put(`${CRM_PREFIX}/sellers/${editingRow.id}`, {
                first_name: editFormData.first_name,
                last_name: editFormData.last_name,
                email: editFormData.email,
                phone_number: editFormData.phone_number || undefined,
                is_active: editFormData.is_active,
            });
            closeEditModal();
            if (selectedSeller && selectedSeller.user_id) {
                const res = await api.get<SellerRow[]>(`${CRM_PREFIX}/sellers/by-user/${selectedSeller.user_id}`);
                setSellerRows(res.data || []);
            }
            fetchSellers();
        } catch (err: any) {
            alert(err?.response?.data?.detail || t('approvals.error_save'));
        } finally {
            setEditFormSubmitting(false);
        }
    };

    const requests = users.filter((u) => u.status === 'pending' && (u.role === 'setter' || u.role === 'closer'));

    if (loading) return <div className="p-6">{t('sellers.loading')}</div>;

    return (
        <div className="view active flex flex-col h-full min-h-0 overflow-hidden p-6">
            <div className="flex justify-between items-center mb-6 shrink-0">
                <div>
                    <h1 className="view-title flex items-center gap-3">
                        <ShieldCheck color="var(--accent)" />
                        {t('sellers.page_title')}
                    </h1>
                    <p className="text-secondary">{t('sellers.page_subtitle')}</p>
                </div>
            </div>

            <div className="flex gap-4 mb-4 border-b border-gray-200 pb-px shrink-0">
                <button
                    onClick={() => setActiveTab('requests')}
                    className={`pb-3 px-6 font-semibold transition-all relative rounded-t-xl ${activeTab === 'requests' ? 'text-medical-600' : 'text-gray-500 hover:text-medical-700'}`}
                >
                    <div className="flex items-center gap-2">
                        {t('sellers.requests')}
                        {requests.length > 0 && (
                            <span className="bg-danger text-white text-[10px] px-1.5 py-0.5 rounded-full shadow-sm">
                                {requests.length}
                            </span>
                        )}
                    </div>
                    {activeTab === 'requests' && (
                        <>
                            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-medical-600" />
                            <div className="absolute inset-0 bg-medical-400/10 blur-xl rounded-full -z-10 shadow-[0_0_20px_rgba(0,102,204,0.15)]" />
                        </>
                    )}
                </button>
                <button
                    onClick={() => setActiveTab('sellers')}
                    className={`pb-3 px-6 font-semibold transition-all relative rounded-t-xl ${activeTab === 'sellers' ? 'text-medical-600' : 'text-gray-500 hover:text-medical-700'}`}
                >
                    {t('sellers.sellers_tab')}
                    {activeTab === 'sellers' && (
                        <>
                            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-medical-600" />
                            <div className="absolute inset-0 bg-medical-400/10 blur-xl rounded-full -z-10 shadow-[0_0_20px_rgba(0,102,204,0.15)]" />
                        </>
                    )}
                </button>
            </div>

            {error ? (
                <div className="glass p-6 text-center border-red-500/20 shrink-0">
                    <AlertTriangle color="#ff4d4d" size={48} className="mx-auto mb-4" />
                    <p className="text-red-400">{error}</p>
                </div>
            ) : (
                <div className="flex-1 min-h-0 overflow-y-auto pb-4">
                    <div className="grid gap-4">
                        {activeTab === 'requests' ? (
                            requests.length === 0 ? (
                                <div className="glass p-12 text-center">
                                    <Clock size={48} className="mx-auto mb-4 opacity-50" />
                                    <h3 className="text-xl font-medium mb-2">{t('sellers.no_requests')}</h3>
                                    <p className="text-secondary">{t('sellers.no_requests_hint')}</p>
                                </div>
                            ) : (
                                requests.map((user) => (
                                    <SellerUserCard key={user.id} user={user} onAction={handleAction} isRequest />
                                ))
                            )
                        ) : sellers.length === 0 ? (
                            <div className="glass p-12 text-center">
                                <Users size={48} className="mx-auto mb-4 opacity-50" />
                                <h3 className="text-xl font-medium mb-2">{t('sellers.no_sellers')}</h3>
                                <p className="text-secondary">{t('sellers.no_sellers_hint')}</p>
                            </div>
                        ) : (
                            sellers.map((seller) => (
                                <SellerCard
                                    key={`${seller.id}-${seller.tenant_id}`}
                                    seller={seller}
                                    onCardClick={() => setSelectedSeller(seller)}
                                    onConfigClick={() => {
                                        setSelectedSeller(seller);
                                        api.get<SellerRow[]>(`${CRM_PREFIX}/sellers/by-user/${seller.user_id}`)
                                            .then((res) => {
                                                const rows = res.data || [];
                                                if (rows.length > 0) openEditModal(rows[0]);
                                            })
                                            .catch(() => {});
                                    }}
                                />
                            ))
                        )}
                    </div>
                </div>
            )}

            {/* Modal detalle vendedor */}
            {selectedSeller && (
                <div
                    className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
                    onClick={(e) => e.target === e.currentTarget && closeDetailModal()}
                >
                    <div className="bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl w-full max-w-6xl h-[92dvh] sm:h-auto sm:max-h-[92vh] flex flex-col overflow-hidden">
                        <div className="flex items-center justify-between gap-3 px-4 py-4 sm:px-6 border-b border-gray-100 shrink-0">
                            <h2 className="text-lg sm:text-xl font-bold text-gray-900 truncate min-w-0">
                                {selectedSeller.first_name || ''} {selectedSeller.last_name || ''}
                            </h2>
                            <div className="flex items-center gap-2 shrink-0">
                                <button
                                    type="button"
                                    onClick={() => {
                                        api.get<SellerRow[]>(`${CRM_PREFIX}/sellers/by-user/${selectedSeller.user_id}`).then((res) => {
                                            const rows = res.data || [];
                                            if (rows.length > 0) openEditModal(rows[0]);
                                        });
                                    }}
                                    className="p-2.5 min-w-[44px] min-h-[44px] rounded-xl border border-gray-200 hover:bg-gray-100 text-gray-600"
                                    title={t('sellers.edit_seller')}
                                >
                                    <Settings size={20} />
                                </button>
                                <button type="button" onClick={closeDetailModal} className="p-2.5 min-w-[44px] min-h-[44px] rounded-xl text-gray-400 hover:bg-gray-100">
                                    <X size={24} />
                                </button>
                            </div>
                        </div>
                        <div className="flex-1 overflow-y-auto min-h-0 px-4 py-4 sm:px-6 space-y-6">
                            <div className="flex flex-wrap gap-3 items-start">
                                <div className="role-badge shrink-0" data-role={selectedSeller.role}>
                                    {selectedSeller.role === 'setter' ? t('sellers.setter') : t('sellers.closer')}
                                </div>
                                <p className="text-sm text-gray-600 flex items-center gap-2">
                                    <Mail size={14} />
                                    {selectedSeller.email}
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => {
                                    setShowLinkForm(true);
                                    setLinkFormData((p) => ({ ...p, tenant_id: entities[0]?.id ?? null }));
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-700"
                            >
                                <Plus size={18} />
                                {sellerRows.length > 0 ? t('sellers.link_to_another_entity') : t('sellers.link_to_entity')}
                            </button>

                            {showLinkForm && (
                                <form onSubmit={handleLinkToEntitySubmit} className="glass p-4 rounded-xl space-y-4">
                                    <h3 className="text-sm font-semibold text-gray-800">{t('sellers.link_to_entity')}</h3>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-xs font-medium text-gray-600 mb-1">{t('sellers.choose_entity')}</label>
                                            <select
                                                value={linkFormData.tenant_id ?? ''}
                                                onChange={(e) => setLinkFormData((p) => ({ ...p, tenant_id: e.target.value ? parseInt(e.target.value, 10) : null }))}
                                                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                required
                                            >
                                                <option value="">{t('sellers.choose_entity')}</option>
                                                {entities.map((c) => (
                                                    <option key={c.id} value={c.id}>{c.clinic_name}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1"><Phone size={12} /> {t('approvals.phone')}</label>
                                            <input
                                                type="text"
                                                value={linkFormData.phone}
                                                onChange={(e) => setLinkFormData((p) => ({ ...p, phone: e.target.value }))}
                                                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                            />
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button type="submit" disabled={linkFormSubmitting} className="btn-icon-labeled success">
                                            <Save size={18} />
                                            {linkFormSubmitting ? t('common.saving') : t('approvals.save_and_link')}
                                        </button>
                                        <button type="button" onClick={() => { setShowLinkForm(false); setLinkFormData({ tenant_id: null, phone: '' }); }} className="btn-icon-labeled">
                                            {t('common.cancel')}
                                        </button>
                                    </div>
                                </form>
                            )}

                            {detailLoading ? (
                                <p className="text-gray-500">{t('sellers.loading_entities')}</p>
                            ) : sellerRows.length > 0 ? (
                                <>
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                                            <Building2 size={16} />
                                            {t('sellers.assigned_entities')}
                                        </h3>
                                        <ul className="list-disc list-inside text-sm text-gray-600">
                                            {sellerRows.map((p) => (
                                                <li key={p.id}>
                                                    {entities.find((c) => c.id === p.tenant_id)?.clinic_name || `Entidad ${p.tenant_id}`}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div className="border border-gray-200 rounded-xl overflow-hidden">
                                        <h3 className="text-sm font-semibold text-gray-700 p-4 flex items-center gap-2">
                                            <BarChart3 size={16} />
                                            {t('sellers.kpis_leads')}
                                        </h3>
                                        <div className="p-4 border-t border-gray-200 space-y-4">
                                            {sellerRows.map((row) => {
                                                const key = `${row.id}-${row.tenant_id}`;
                                                return (
                                                    <div key={key} className="text-sm">
                                                        <p className="font-medium text-gray-700 mb-1">
                                                            {entities.find((c) => c.id === row.tenant_id)?.clinic_name || `Entidad ${row.tenant_id}`}
                                                        </p>
                                                        {!kpisByRow[key] ? (
                                                            <button type="button" onClick={() => loadKpis(row)} className="text-blue-600 hover:underline text-xs">
                                                                {t('sellers.load_kpis')}
                                                            </button>
                                                        ) : null}
                                                        {kpisByRow[key] && (
                                                            <ul className="text-gray-600 mt-1 space-y-0.5">
                                                                <li>{t('sellers.total_leads')}: <strong>{kpisByRow[key].total_leads}</strong></li>
                                                                {Object.entries(kpisByRow[key].by_status).map(([status, count]) => (
                                                                    <li key={status}>{status}: <strong>{count}</strong></li>
                                                                ))}
                                                            </ul>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={handleRemoveAccess}
                                        className="btn-icon-labeled danger"
                                    >
                                        <Lock size={18} />
                                        {t('sellers.remove_access')}
                                    </button>
                                </>
                            ) : (
                                <p className="text-gray-500 text-sm">{t('sellers.not_linked_hint')}</p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Modal Editar vendedor */}
            {editingRow && (
                <div
                    className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
                    onClick={(e) => e.target === e.currentTarget && closeEditModal()}
                >
                    <div className="bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl w-full max-w-lg flex flex-col overflow-hidden">
                        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-100">
                            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                                <Edit size={20} />
                                {t('sellers.edit_seller')}
                            </h2>
                            <button type="button" onClick={closeEditModal} className="p-2 rounded-xl text-gray-400 hover:bg-gray-100">
                                <X size={24} />
                            </button>
                        </div>
                        <form onSubmit={handleEditSubmit} className="p-4 space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">{t('sellers.first_name')}</label>
                                <input
                                    type="text"
                                    value={editFormData.first_name}
                                    onChange={(e) => setEditFormData((p) => ({ ...p, first_name: e.target.value }))}
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">{t('sellers.last_name')}</label>
                                <input
                                    type="text"
                                    value={editFormData.last_name}
                                    onChange={(e) => setEditFormData((p) => ({ ...p, last_name: e.target.value }))}
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">{t('approvals.email')}</label>
                                <input
                                    type="email"
                                    value={editFormData.email}
                                    onChange={(e) => setEditFormData((p) => ({ ...p, email: e.target.value }))}
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">{t('approvals.phone')}</label>
                                <input
                                    type="text"
                                    value={editFormData.phone_number}
                                    onChange={(e) => setEditFormData((p) => ({ ...p, phone_number: e.target.value }))}
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                />
                            </div>
                            <label className="flex items-center gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={editFormData.is_active}
                                    onChange={(e) => setEditFormData((p) => ({ ...p, is_active: e.target.checked }))}
                                    className="w-4 h-4 rounded border-gray-300 text-blue-600"
                                />
                                <span className="text-sm font-medium text-gray-700">{t('approvals.active')}</span>
                            </label>
                            <div className="flex gap-2 pt-2">
                                <button type="button" onClick={closeEditModal} className="flex-1 py-2 rounded-xl border border-gray-300 text-gray-700">
                                    {t('common.cancel')}
                                </button>
                                <button type="submit" disabled={editFormSubmitting} className="flex-1 py-2 rounded-xl bg-blue-600 text-white font-medium disabled:opacity-50">
                                    {editFormSubmitting ? t('common.saving') : t('common.save_changes')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            <style>{`
                .glass { background: white; border: 1px solid #e5e7eb; border-radius: 16px; }
                .role-badge { padding: 4px 10px; border-radius: 8px; font-size: 0.7rem; font-weight: 700; background: #f8f9fa; }
                .role-badge[data-role='setter'] { color: #004085; background: #cce5ff; }
                .role-badge[data-role='closer'] { color: #155724; background: #d4edda; }
                .btn-icon-labeled { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 10px; font-size: 0.9rem; border: 1px solid #dee2e6; background: #fff; color: #495057; }
                .btn-icon-labeled.danger { border-color: #f5c6cb; background: #f8d7da; color: #721c24; }
                .btn-icon-labeled.success { border-color: #c3e6cb; background: #d4edda; color: #155724; }
                .btn-icon-labeled.warning { border-color: #ffeeba; background: #fff3cd; color: #856404; }
            `}</style>
        </div>
    );
};

interface SellerUserCardProps {
    user: StaffUser;
    onAction: (id: string, action: 'active' | 'suspended') => void;
    isRequest?: boolean;
}

const SellerUserCard: React.FC<SellerUserCardProps> = ({ user, onAction, isRequest }) => {
    const { t } = useTranslation();
    return (
        <div className="glass p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className={`role-badge shrink-0 ${user.status === 'suspended' ? 'opacity-40' : ''}`} data-role={user.role}>
                    {user.role === 'setter' ? t('sellers.setter') : t('sellers.closer')}
                </div>
                <div className="min-w-0 flex-1">
                    <div className="font-medium flex items-center gap-2">
                        <User size={14} className="opacity-50 shrink-0" />
                        {user.first_name || t('approvals.no_name')} {user.last_name || ''}
                    </div>
                    <div className="text-sm flex items-center gap-2 opacity-70 truncate">
                        <Mail size={12} className="shrink-0" />
                        {user.email}
                    </div>
                </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
                {isRequest ? (
                    <>
                        <button onClick={() => onAction(user.id, 'active')} className="btn-icon-labeled success">
                            <UserCheck size={18} /> {t('approvals.approve')}
                        </button>
                        <button onClick={() => onAction(user.id, 'suspended')} className="btn-icon-labeled danger">
                            <UserX size={18} /> {t('approvals.reject')}
                        </button>
                    </>
                ) : (
                    user.status === 'active' ? (
                        <button onClick={() => onAction(user.id, 'suspended')} className="btn-icon-labeled warning">
                            <Lock size={18} /> {t('approvals.suspend')}
                        </button>
                    ) : (
                        <button onClick={() => onAction(user.id, 'active')} className="btn-icon-labeled success">
                            <Unlock size={18} /> {t('approvals.reactivate')}
                        </button>
                    )
                )}
            </div>
        </div>
    );
};

interface SellerCardProps {
    seller: SellerRow;
    onCardClick: () => void;
    onConfigClick: () => void;
}

const SellerCard: React.FC<SellerCardProps> = ({ seller, onCardClick, onConfigClick }) => {
    const { t } = useTranslation();
    return (
        <div className="glass p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div
                className="flex items-center gap-4 flex-1 min-w-0 cursor-pointer hover:opacity-90"
                onClick={onCardClick}
                role="button"
            >
                <div className="role-badge shrink-0" data-role={seller.role}>
                    {seller.role === 'setter' ? t('sellers.setter') : t('sellers.closer')}
                </div>
                <div className="min-w-0 flex-1">
                    <div className="font-medium flex items-center gap-2">
                        <User size={14} className="opacity-50 shrink-0" />
                        {seller.first_name || ''} {seller.last_name || ''}
                    </div>
                    <div className="text-sm flex items-center gap-2 opacity-70 truncate">
                        <Mail size={12} className="shrink-0" />
                        {seller.email}
                    </div>
                </div>
            </div>
            <div className="flex items-center gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                <button type="button" onClick={onConfigClick} className="p-2.5 min-w-[44px] min-h-[44px] rounded-xl border border-gray-200 hover:bg-gray-100" title={t('sellers.edit_seller')}>
                    <Settings size={20} />
                </button>
            </div>
        </div>
    );
};

export default SellersView;
