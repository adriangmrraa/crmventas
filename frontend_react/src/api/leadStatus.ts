import api from './axios';

export interface LeadStatus {
    id: string;
    tenant_id: number;
    name: string;
    code: string;
    color: string;
    icon: string;
    description?: string;
    category?: string;
    badge_style: string;
    is_active: boolean;
    is_initial: boolean;
    is_final: boolean;
    requires_comment: boolean;
    sort_order: number;
}

export interface LeadStatusTransition {
    id: string;
    from_status_code: string | null;
    to_status_code: string;
    label: string;
    description?: string;
    icon?: string;
    button_style: string;
    requires_approval: boolean;
    approval_role?: string;
    to_status_name: string;
    to_status_color: string;
    to_status_icon: string;
}

export interface LeadStatusHistoryItem {
    id: string;
    lead_id: string;
    tenant_id: number;
    from_status_code?: string;
    to_status_code: string;
    changed_by_user_id?: string;
    changed_by_name?: string;
    comment?: string;
    created_at: string;
    from_status_name?: string;
    from_status_color?: string;
    to_status_name: string;
    to_status_color: string;
}

export const leadStatusApi = {
    // Configuración core
    getStatuses: (includeInactive = false) =>
        api.get<LeadStatus[]>('/admin/core/crm/lead-statuses', { params: { include_inactive: includeInactive } }),

    // Workflow validado por Backend Sovereign
    getAvailableTransitions: (leadId: string) =>
        api.get<LeadStatusTransition[]>(`/admin/core/crm/leads/${leadId}/available-transitions`),

    // Mutaciones seguras
    changeStatus: (leadId: string, status: string, comment?: string, metadata?: Record<string, any>) =>
        api.post(`/admin/core/crm/leads/${leadId}/status`, { status, comment, metadata }),

    bulkChangeStatus: (leadIds: string[], status: string, comment?: string) =>
        api.post('/admin/core/crm/leads/bulk-status', { lead_ids: leadIds, status, comment }),

    // Trazabilidad y reportes (CQRS - Read Side)
    getHistory: (leadId: string, limit = 50, offset = 0) =>
        api.get<{ timeline: LeadStatusHistoryItem[] }>(`/admin/core/crm/leads/${leadId}/status-history`, { params: { limit, offset } }),
};
