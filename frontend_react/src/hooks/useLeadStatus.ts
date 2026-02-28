import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { leadStatusApi } from '../api/leadStatus';
import type { LeadStatus, LeadStatusTransition, LeadStatusHistoryItem } from '../api/leadStatus';
import toast from 'react-hot-toast';

/**
 * Hook avanzado para manejo optimista de estados.
 * Incorpora Optimistic Updates, invalidación de lista de Leads y manejo genérico de transiciones.
 */
export function useLeadStatus(leadId?: string) {
    const queryClient = useQueryClient();
    const [isUpdating, setIsUpdating] = useState(false);

    // 1. Obtener estados maestros del tenant (Raramente cambia)
    const {
        data: statuses,
        isLoading: isLoadingStatuses
    } = useQuery({
        queryKey: ['lead-statuses'],
        queryFn: () => leadStatusApi.getStatuses().then(res => res.data),
        staleTime: 1000 * 60 * 60, // 1 hora
    });

    // 2. Obtener transiciones disponibles para un lead específico
    const {
        data: transitions,
        isLoading: isLoadingTransitions,
        refetch: refetchTransitions
    } = useQuery({
        queryKey: ['lead-transitions', leadId],
        queryFn: () => leadId ? leadStatusApi.getAvailableTransitions(leadId).then(res => res.data) : [],
        enabled: !!leadId,
    });

    // 3. Obtener el historial completo
    const {
        data: historyData,
        isLoading: isLoadingHistory
    } = useQuery({
        queryKey: ['lead-history', leadId],
        queryFn: () => leadId ? leadStatusApi.getHistory(leadId).then(res => res.data) : { timeline: [] },
        enabled: !!leadId,
    });

    // 4. Mutación: Cambio unitario Optimizista
    const changeStatusMutation = useMutation({
        mutationFn: (variables: { status: string; leadId: string; comment?: string; metadata?: any }) => {
            setIsUpdating(true);
            return leadStatusApi.changeStatus(variables.leadId, variables.status, variables.comment, variables.metadata);
        },
        // Al intentar enviar (optimistic ui fallback)
        onMutate: async (newStatusData) => {
            // Cancelar cualquier refetch outgoing
            await queryClient.cancelQueries({ queryKey: ['leads'] });

            // Snapshot del estado previo
            const previousLeads = queryClient.getQueryData(['leads']);

            // Actualizar optimísticamente la vista lista
            queryClient.setQueryData(['leads'], (old: any) => {
                if (!old || !old.pages) return old;
                return {
                    ...old,
                    pages: old.pages.map((page: any) =>
                        page.map((lead: any) => lead.id === newStatusData.leadId ? { ...lead, status: newStatusData.status } : lead)
                    )
                };
            });

            return { previousLeads };
        },
        onError: (err: any, newStatusData, context: any) => {
            // Rollback UI
            if (context?.previousLeads) {
                queryClient.setQueryData(['leads'], context.previousLeads);
            }
            toast.error(err.response?.data?.detail || "Error al cambiar el estado");
        },
        onSettled: (data, error, variables) => {
            setIsUpdating(false);
            // Validar server truth por las dudas
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['lead', variables.leadId] });
            queryClient.invalidateQueries({ queryKey: ['lead-transitions', variables.leadId] });
            queryClient.invalidateQueries({ queryKey: ['lead-history', variables.leadId] });
        },
        onSuccess: (data, variables) => {
            const statusObj = statuses?.find(s => s.code === variables.status);
            toast.success(`Estado del lead actualizado a ${statusObj?.name || variables.status}`);
        }
    });

    // Mutación Pura: Batch Operations (Aquí no hacemos UI optimista de lista porque son muchos)
    const bulkStatusMutation = useMutation({
        mutationFn: (variables: { leadIds: string[]; status: string; comment?: string }) => {
            return leadStatusApi.bulkChangeStatus(variables.leadIds, variables.status, variables.comment);
        },
        onSuccess: (res, variables) => {
            const data: any = res.data;
            if (data.successful > 0) toast.success(`${data.successful} leads actualizados correctamente.`);
            if (data.failed > 0) toast.error(`${data.failed} leads fallaron al actualizarse.`);
            queryClient.invalidateQueries({ queryKey: ['leads'] });
        },
        onError: () => {
            toast.error("Ocurrió un error general realizando la actualización en lote.");
        }
    });


    return {
        statuses,
        isLoadingStatuses,
        transitions,
        isLoadingTransitions,
        refetchTransitions,
        history: historyData?.timeline || [],
        isLoadingHistory,
        changeStatus: changeStatusMutation.mutate,
        changeStatusAsync: changeStatusMutation.mutateAsync,
        bulkChangeStatus: bulkStatusMutation.mutateAsync,
        isUpdating: changeStatusMutation.isPending || isUpdating || bulkStatusMutation.isPending
    };
}
