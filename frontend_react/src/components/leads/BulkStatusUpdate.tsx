import React, { useState } from 'react';
import { Layers, Loader2, Info } from 'lucide-react';
import { useTranslation } from '../../context/LanguageContext';
import { useLeadStatus } from '../../hooks/useLeadStatus';
import { LeadStatusBadge } from './LeadStatusBadge';
import type { LeadStatus } from '../../api/leadStatus';

interface BulkStatusUpdateProps {
    selectedLeadIds: string[];
    onSuccess: () => void;
    onCancel: () => void;
}

export const BulkStatusUpdate: React.FC<BulkStatusUpdateProps> = ({
    selectedLeadIds,
    onSuccess,
    onCancel
}) => {
    const [targetStatus, setTargetStatus] = useState<string>('');
    const [comment, setComment] = useState<string>('');
    const { statuses, isLoadingStatuses, bulkChangeStatus, isUpdating } = useLeadStatus();
    const { t } = useTranslation();

    // Obtenemos solo los activos para el Dropdown
    const activeStatuses = statuses?.filter((s: LeadStatus) => s.is_active) || [];
    const selectedStatusDef = activeStatuses.find((s: LeadStatus) => s.code === targetStatus);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!targetStatus) return;

        try {
            await bulkChangeStatus({
                leadIds: selectedLeadIds,
                status: targetStatus,
                comment: comment || undefined
            });
            onSuccess();
        } catch (e) {
            console.error(e);
            // El hook Toast ya maneja el error genéricamente
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                    <div className="flex items-center gap-2 text-slate-800 font-semibold">
                        <Layers className="w-5 h-5 text-blue-600" />
                        {t('leads.bulk_update.title')}
                    </div>
                    <span className="bg-blue-100 text-blue-700 py-0.5 px-2.5 rounded-full text-xs font-bold">
                        {selectedLeadIds.length} {t('leads.bulk_update.selected')}
                    </span>
                </div>

                {/* Form Body */}
                <form onSubmit={handleSubmit} className="p-6">
                    <div className="space-y-5">

                        {/* Disclaimer */}
                        <div className="bg-blue-50 text-blue-800 p-3 rounded-xl flex gap-3 text-sm border border-blue-100 items-start">
                            <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
                            <p>{t('leads.bulk_update.warning')}</p>
                        </div>

                        {/* Selector de Nuevo Estado */}
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-1.5">{t('leads.bulk_update.new_status')}</label>
                            {isLoadingStatuses ? (
                                <div className="text-sm text-slate-400 flex items-center gap-2"><Loader2 className="animate-spin w-4 h-4" />{t('leads.bulk_update.loading_motors')}</div>
                            ) : (
                                <select
                                    className="w-full text-sm border-slate-200 rounded-xl focus:ring-blue-500 focus:border-blue-500 p-2.5 bg-slate-50 hover:bg-white transition-colors cursor-pointer"
                                    value={targetStatus}
                                    onChange={(e) => setTargetStatus(e.target.value)}
                                    required
                                >
                                    <option value="" disabled>{t('leads.bulk_update.select_status')}</option>
                                    {activeStatuses.map((status: LeadStatus) => (
                                        <option key={status.id} value={status.code}>{status.name}</option>
                                    ))}
                                </select>
                            )}
                            {selectedStatusDef && (
                                <div className="mt-2 text-xs text-slate-500 flex items-center gap-1.5 border-l-2 border-slate-200 pl-2 ml-1">
                                    {t('leads.bulk_update.preview')} <LeadStatusBadge statusCode={selectedStatusDef.code} />
                                </div>
                            )}
                        </div>

                        {/* Comentario (Opcional/Obligatorio) */}
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                                {t('leads.bulk_update.reason_or_comment')} {selectedStatusDef?.requires_comment ? <span className="text-red-500">*</span> : <span className="text-slate-400 font-normal">{t('leads.bulk_update.optional')}</span>}
                            </label>
                            <textarea
                                className="w-full text-sm border-slate-200 rounded-xl focus:ring-blue-500 focus:border-blue-500 p-3 bg-slate-50 hover:bg-white transition-colors custom-scrollbar resize-none"
                                rows={3}
                                placeholder={t('leads.bulk_update.reason_placeholder')}
                                value={comment}
                                onChange={(e) => setComment(e.target.value)}
                                required={selectedStatusDef?.requires_comment}
                            />
                        </div>

                    </div>

                    {/* Footer actions */}
                    <div className="mt-8 flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={onCancel}
                            disabled={isUpdating}
                            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors disabled:opacity-50"
                        >
                            {t('common.cancel')}
                        </button>
                        <button
                            type="submit"
                            disabled={!targetStatus || isUpdating || (selectedStatusDef?.requires_comment && !comment.trim())}
                            className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 shadow-sm rounded-xl transition-all disabled:opacity-50 flex items-center"
                        >
                            {isUpdating ? (
                                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> {t('leads.bulk_update.processing')}</>
                            ) : (
                                t('leads.bulk_update.apply_all')
                            )}
                        </button>
                    </div>
                </form>

            </div>
        </div>
    );
};
