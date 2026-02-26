import React from 'react';
import * as LucideIcons from 'lucide-react';
import { useLeadStatus } from '../../hooks/useLeadStatus';

interface LeadStatusBadgeProps {
    statusCode: string;
    className?: string;
    showIcon?: boolean;
}

/**
 * Renderiza el badge visual de un estado. Resuelve el color y el icono
 * enrutando desde la cache del `useLeadStatus` para un performance atómico.
 */
export const LeadStatusBadge: React.FC<LeadStatusBadgeProps> = ({
    statusCode,
    className = '',
    showIcon = true
}) => {
    const { statuses, isLoadingStatuses } = useLeadStatus();

    if (isLoadingStatuses && !statuses) {
        return <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 animate-pulse ${className}`}>Cargando...</span>;
    }

    // Fallback si no está el estado (o el cache no cargó)
    const statusDef = statuses?.find(s => s.code === statusCode) || {
        name: statusCode || 'Nuevo',
        color: '#6B7280',
        icon: 'circle',
        badge_style: 'default',
    };

    // Icon parsing dinámico
    // Convertimos 'check-circle' -> 'CheckCircle' (CamelCase)
    const iconName = (statusDef.icon.charAt(0).toUpperCase() + statusDef.icon.slice(1)).replace(/[-_](.)/g, (_, c) => c.toUpperCase());

    // @ts-ignore - Indexing LucideIcons
    const IconComponent = LucideIcons[iconName] || LucideIcons.Circle;

    // Calculamos la saturación del fondo basándonos en el HEX dictaminado por la Base de datos
    // Utilizaremos transparencia inline combinada con tailwind classes genericas 
    const hexToRgb = (hex: string) => {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '107, 114, 128';
    };

    return (
        <span
            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border shadow-sm ${className}`}
            style={{
                backgroundColor: `rgba(${hexToRgb(statusDef.color)}, 0.1)`,
                color: statusDef.color,
                borderColor: `rgba(${hexToRgb(statusDef.color)}, 0.2)`
            }}
        >
            {showIcon && (
                <IconComponent className="w-3 h-3 mr-1.5" strokeWidth={2.5} />
            )}
            {statusDef.name}
        </span>
    );
};
