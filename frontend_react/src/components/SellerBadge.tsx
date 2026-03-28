import React from 'react';
import { User, UserCheck, UserX, Bot, Crown, Target, Zap } from 'lucide-react';
import { useTranslation } from '../context/LanguageContext';

interface SellerBadgeProps {
  sellerId?: string | null;
  sellerName?: string;
  sellerRole?: string;
  assignedAt?: string;
  source?: string;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  className?: string;
}

const SellerBadge: React.FC<SellerBadgeProps> = ({
  sellerId,
  sellerName,
  sellerRole,
  assignedAt,
  source = 'manual',
  showLabel = true,
  size = 'md',
  onClick,
  className = ''
}) => {
  const { t } = useTranslation();
  
  // If no seller assigned, show "AGENTE IA" badge
  if (!sellerId) {
    return (
      <div 
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.03]/[0.04] text-white/70 border border-white/[0.06] ${className}`}
        onClick={onClick}
      >
        <Bot size={size === 'sm' ? 12 : size === 'md' ? 14 : 16} />
        {showLabel && (
          <span className={`font-medium ${size === 'sm' ? 'text-xs' : size === 'md' ? 'text-sm' : 'text-base'}`}>
            {t('sellers.agent_ia')}
          </span>
        )}
      </div>
    );
  }
  
  // Determine badge color based on role
  const getRoleConfig = () => {
    switch (sellerRole) {
      case 'ceo':
        return {
          bg: 'bg-purple-500/10',
          text: 'text-purple-400',
          border: 'border-purple-500/20',
          icon: Crown,
          label: t('roles.ceo')
        };
      case 'setter':
        return {
          bg: 'bg-blue-500/100/10',
          text: 'text-blue-400',
          border: 'border-blue-500/20',
          icon: Target,
          label: t('roles.setter')
        };
      case 'closer':
        return {
          bg: 'bg-green-500/100/10',
          text: 'text-green-400',
          border: 'border-green-500/20',
          icon: Zap,
          label: t('roles.closer')
        };
      case 'professional':
        return {
          bg: 'bg-indigo-500/10',
          text: 'text-indigo-400',
          border: 'border-indigo-500/20',
          icon: UserCheck,
          label: t('roles.professional')
        };
      default:
        return {
          bg: 'bg-white/[0.03]/[0.04]',
          text: 'text-white/70',
          border: 'border-white/[0.06]',
          icon: User,
          label: sellerRole || t('roles.seller')
        };
    }
  };
  
  const roleConfig = getRoleConfig();
  const Icon = roleConfig.icon;
  
  // Format assigned time
  const formatTime = (dateString?: string) => {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffMins < 60) {
      return t('sellers.assigned_minutes_ago', { minutes: diffMins });
    } else if (diffHours < 24) {
      return t('sellers.assigned_hours_ago', { hours: diffHours });
    } else {
      return t('sellers.assigned_days_ago', { days: diffDays });
    }
  };
  
  // Get source icon
  const getSourceIcon = () => {
    switch (source) {
      case 'auto':
        return <span className="text-xs">🤖</span>;
      case 'prospecting':
        return <span className="text-xs">🔍</span>;
      case 'reassignment':
        return <span className="text-xs">🔄</span>;
      default:
        return <span className="text-xs">👤</span>;
    }
  };
  
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-sm gap-1.5',
    lg: 'px-3 py-1.5 text-base gap-2'
  };
  
  const iconSize = {
    sm: 12,
    md: 14,
    lg: 16
  };
  
  return (
    <div 
      className={`inline-flex items-center ${sizeClasses[size]} rounded-full ${roleConfig.bg} ${roleConfig.text} ${roleConfig.border} border ${onClick ? 'cursor-pointer hover:opacity-90 transition-opacity' : ''} ${className}`}
      onClick={onClick}
      title={`${sellerName || t('sellers.unknown_seller')} (${roleConfig.label}) - ${formatTime(assignedAt)}`}
    >
      <Icon size={iconSize[size]} />
      
      {showLabel && (
        <>
          <span className="font-medium truncate max-w-[120px]">
            {sellerName || t('sellers.unknown_seller')}
          </span>
          
          {sellerRole && sellerRole !== 'professional' && (
            <span className={`${size === 'sm' ? 'text-[10px]' : 'text-xs'} font-semibold opacity-80`}>
              {roleConfig.label}
            </span>
          )}
          
          {source && source !== 'manual' && (
            <span className="ml-0.5 opacity-70">
              {getSourceIcon()}
            </span>
          )}
        </>
      )}
      
      {assignedAt && !showLabel && (
        <span className={`${size === 'sm' ? 'text-[10px]' : 'text-xs'} opacity-70 ml-1`}>
          {formatTime(assignedAt)}
        </span>
      )}
    </div>
  );
};

export default SellerBadge;