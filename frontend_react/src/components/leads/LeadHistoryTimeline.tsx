import React from 'react';
import { History, X, User } from 'lucide-react';
import { useLeadStatus } from '../../hooks/useLeadStatus';
import { LeadStatusBadge } from './LeadStatusBadge';
import type { LeadStatusHistoryItem } from '../../api/leadStatus';

interface LeadHistoryTimelineProps {
    leadId: string;
    leadName: string;
    onClose: () => void;
}

export const LeadHistoryTimeline: React.FC<LeadHistoryTimelineProps> = ({ leadId, leadName, onClose }) => {
    const { history, isLoadingHistory } = useLeadStatus(leadId);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col h-[80vh] max-h-[600px] animate-in fade-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50 shrink-0">
                    <div className="flex items-center gap-2 text-slate-800 font-semibold">
                        <History className="w-5 h-5 text-blue-600" />
                        <div>
                            <h3>Historial de Estados</h3>
                            <p className="text-xs text-slate-500 font-normal">Lead: {leadName}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-1.5 hover:bg-slate-200 rounded-lg text-slate-500 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Timeline Body */}
                <div className="flex-1 overflow-y-auto p-6 bg-slate-50 relative custom-scrollbar">
                    {isLoadingHistory ? (
                        <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-400"></div>
                            <p className="text-sm">Recopilando Audit Log...</p>
                        </div>
                    ) : history.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
                            <History className="w-12 h-12 text-slate-200" />
                            <p className="text-sm font-medium">Sin cambios registrados aún.</p>
                        </div>
                    ) : (
                        <div className="space-y-6 before:absolute before:inset-0 before:ml-[31px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
                            {history.map((event: LeadStatusHistoryItem) => (
                                <div key={event.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                                    {/* Timeline Marker */}
                                    <div className="flex items-center justify-center w-6 h-6 rounded-full border-2 border-white bg-blue-100 text-blue-600 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                                        <div className="w-2 h-2 rounded-full bg-blue-600"></div>
                                    </div>

                                    {/* Card */}
                                    <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl shadow-sm bg-white border border-slate-100 hover:border-slate-300 transition-colors cursor-default">
                                        <div className="flex flex-wrap items-center justify-between mb-1 gap-2">
                                            <div className="flex gap-2 items-center flex-wrap">
                                                {event.from_status_code ? (
                                                    <>
                                                        <LeadStatusBadge statusCode={event.from_status_code} showIcon={false} />
                                                        <span className="text-slate-400 text-xs">➔</span>
                                                        <LeadStatusBadge statusCode={event.to_status_code} showIcon={false} />
                                                    </>
                                                ) : (
                                                    <LeadStatusBadge statusCode={event.to_status_code} />
                                                )}
                                            </div>
                                            <time className="text-xs text-slate-400 font-medium whitespace-nowrap">
                                                {new Date(event.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                                            </time>
                                        </div>

                                        {event.comment && (
                                            <div className="mt-3 p-3 bg-slate-50/80 rounded-lg text-sm text-slate-600 border border-slate-100 italic">
                                                "{event.comment}"
                                            </div>
                                        )}

                                        <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                                            <User className="w-3.5 h-3.5" />
                                            {event.changed_by_name ? `Por: ${event.changed_by_name}` : 'Sistema / Auto'}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
