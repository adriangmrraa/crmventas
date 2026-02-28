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
                className="flex items-center gap-1.5 focus:outline-none transition-transform hover:scale-105"
            >
                <LeadStatusBadge statusCode={currentStatusCode} />
                {isUpdating ? <Loader2 className="w-3 h-3 animate-spin text-gray-400" /> : <ChevronDown className="w-3.5 h-3.5 text-gray-500 hover:text-gray-800 transition-colors" />}
            </button>

            {/* Menú Flotante */}
            {isOpen && (
                <div
                    className="absolute z-[9999] mt-2 w-56 rounded-md shadow-2xl bg-white border border-gray-100 ring-1 ring-black ring-opacity-5 origin-top-right right-0 shadow-lg transform opacity-100 scale-100 transition-all"
                >
                    {commentRequired ? (
                        <div className="p-3">
                            <p className="text-xs font-semibold text-gray-600 mb-2">{t('leads.status_selector.comment_required')}</p>
                            <textarea
                                className="w-full text-sm border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 p-2 shadow-sm mb-2 resize-none"
                                rows={2}
                                value={commentValue}
                                onChange={(e) => setCommentValue(e.target.value)}
                                placeholder={t('leads.status_selector.reason_placeholder')}
                            />
                            <div className="flex justify-end gap-2">
                                <button onClick={() => setCommentRequired(false)} className="text-xs text-gray-500 px-2 py-1 rounded hover:bg-gray-100">{t('common.cancel')}</button>
                                <button
                                    disabled={!commentValue.trim() || isUpdating}
                                    onClick={() => pendingStatusCode && submitStatusChange(pendingStatusCode)}
                                    className="text-xs text-white bg-blue-600 px-3 py-1 rounded shadow-sm hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {t('common.confirm') || 'Confirmar'}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="py-1 max-h-60 overflow-y-auto custom-scrollbar" role="menu">
                            <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                {t('leads.status_selector.change_status')}
                            </div>

                            {isLoadingTransitions ? (
                                <div className="px-4 py-3 flex items-center justify-center text-gray-400 text-sm">
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" /> {t('leads.status_selector.evaluating_workflow')}
                                </div>
                            ) : transitions && transitions.length > 0 ? (
                                transitions.map((transition: LeadStatusTransition) => (
                                    <button
                                        key={transition.id}
                                        onClick={(e) => { e.stopPropagation(); handleStatusSelect(transition.to_status_code); }}
                                        className="w-full text-left flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-gray-900 group"
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
                                            <span className="text-xs text-gray-400 ml-4 group-hover:text-blue-500 transition-colors">
                                                {transition.label}
                                            </span>
                                        </div>
                                    </button>
                                ))
                            ) : (
                                <div className="px-4 py-3 text-sm text-gray-500 italic">
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
