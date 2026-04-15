import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from '../../context/LanguageContext';
import { useLeadStatus } from '../../hooks/useLeadStatus';
import { LeadStatusBadge } from './LeadStatusBadge';
import { ChevronDown, Loader2 } from 'lucide-react';
import type { LeadStatus, LeadStatusTransition } from '../../api/leadStatus';

interface LeadStatusSelectorProps {
    leadId: string;
    currentStatusCode: string;
    onChangeSuccess?: () => void;
}

/**
 * Componente que renderiza un Dropdown para cambiar el estado.
 * Cumple la regla de Scroll Isolation y valida los comentarios antes del disparo.
 */
export const LeadStatusSelector: React.FC<LeadStatusSelectorProps> = ({
    leadId,
    currentStatusCode,
    onChangeSuccess
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [commentRequired, setCommentRequired] = useState(false);
    const [commentValue, setCommentValue] = useState('');
    const [pendingStatusCode, setPendingStatusCode] = useState<string | null>(null);

    const dropdownRef = useRef<HTMLDivElement>(null);
    const { t } = useTranslation();

    const {
        statuses,
        transitions,
        isLoadingTransitions,
        changeStatusAsync,
        isUpdating
    } = useLeadStatus(leadId);

    // Scroll Isolation (Close on outside click)
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
                setCommentRequired(false);
                setPendingStatusCode(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleStatusSelect = (toStatusCode: string) => {
        const targetStatusDef = statuses?.find((s: LeadStatus) => s.code === toStatusCode);
        if (targetStatusDef?.requires_comment) {
            setPendingStatusCode(toStatusCode);
            setCommentRequired(true);
            return; // Stop here and wait for comment form submission
        }

        // Direct submission
        submitStatusChange(toStatusCode);
    };

    const submitStatusChange = async (targetCode: string) => {
        try {
            await changeStatusAsync({ leadId, status: targetCode, comment: commentValue });
            setIsOpen(false);
            setCommentRequired(false);
            setPendingStatusCode(null);
            setCommentValue('');
            if (onChangeSuccess) onChangeSuccess();
        } catch (e) {
            // Error is handled inside the hook via Toast
        }
    };

    return (
        <div className="relative inline-block text-left" ref={dropdownRef}>
            <button
                type="button"
                onMouseEnter={() => !isOpen && !isLoadingTransitions && leadId && setIsOpen(false)} // Prefetch hint if wanted via onMouse, disabled due to enabled=!!leadId
                onClick={() => setIsOpen(!isOpen)}
                disabled={isUpdating}
                className="flex items-center gap-1.5 focus:outline-none active:scale-95 transition-all hover:scale-105"
            >
                <LeadStatusBadge statusCode={currentStatusCode} />
                {isUpdating ? <Loader2 className="w-3 h-3 animate-spin text-white/30" /> : <ChevronDown className="w-3.5 h-3.5 text-white/40 hover:text-white transition-colors" />}
            </button>

            {/* Menú Flotante */}
            {isOpen && (
                <div
                    className="absolute z-[9999] mt-2 w-56 rounded-md shadow-xl bg-[#0d1117] border border-white/[0.08] ring-1 ring-white/[0.06] origin-top-right right-0 transform opacity-100 scale-100 transition-all"
                >
                    {commentRequired ? (
                        <div className="p-3">
                            <p className="text-xs font-semibold text-white/50 mb-2">{t('leads.status_selector.comment_required')}</p>
                            <textarea
                                className="w-full text-sm border border-white/[0.06] bg-white/[0.04] text-white rounded-md focus:ring-violet-500 focus:border-violet-500 p-2 mb-2 resize-none placeholder:text-white/30"
                                rows={2}
                                value={commentValue}
                                onChange={(e) => setCommentValue(e.target.value)}
                                placeholder={t('leads.status_selector.reason_placeholder')}
                            />
                            <div className="flex justify-end gap-2">
                                <button onClick={() => setCommentRequired(false)} className="text-xs text-white/40 px-2 py-1 rounded hover:bg-white/[0.06] active:scale-95 transition-all">{t('common.cancel')}</button>
                                <button
                                    disabled={!commentValue.trim() || isUpdating}
                                    onClick={() => pendingStatusCode && submitStatusChange(pendingStatusCode)}
                                    className="text-xs text-white bg-violet-600 px-3 py-1 rounded hover:bg-violet-700 disabled:opacity-50 active:scale-95 transition-all"
                                >
                                    {t('common.confirm') || 'Confirmar'}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="py-1 max-h-60 overflow-y-auto custom-scrollbar" role="menu">
                            <div className="px-3 py-2 text-xs font-semibold text-white/30 uppercase tracking-wider">
                                {t('leads.status_selector.change_status')}
                            </div>

                            {isLoadingTransitions ? (
                                <div className="px-4 py-3 flex items-center justify-center text-white/30 text-sm">
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" /> {t('leads.status_selector.evaluating_workflow')}
                                </div>
                            ) : transitions && transitions.length > 0 ? (
                                transitions.map((transition: LeadStatusTransition) => (
                                    <button
                                        key={transition.id}
                                        onClick={(e) => { e.stopPropagation(); handleStatusSelect(transition.to_status_code); }}
                                        className="w-full text-left flex items-center px-4 py-2 text-sm text-white/70 hover:bg-white/[0.06] hover:text-white active:scale-95 transition-all group"
                                        role="menuitem"
                                    >
                                        <div className="flex flex-col w-full">
                                            <div className="flex items-center">
                                                {/* Optional tiny icon preview left of the status text */}
                                                <span
                                                    className="w-2 h-2 rounded-full mr-2"
                                                    style={{ backgroundColor: transition.to_status_color }}
                                                />
                                                <span className="font-medium">{transition.to_status_name}</span>
                                            </div>
                                            <span className="text-xs text-white/30 ml-4 group-hover:text-violet-400 transition-colors">
                                                {transition.label}
                                            </span>
                                        </div>
                                    </button>
                                ))
                            ) : (
                                <div className="px-4 py-3 text-sm text-white/40 italic">
                                    {t('leads.status_selector.no_valid_transitions')}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};
