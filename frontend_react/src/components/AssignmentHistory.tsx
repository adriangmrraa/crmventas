import React, { useState, useEffect } from 'react';
import { History, User, Clock, Calendar, RefreshCw, ExternalLink, Loader2 } from 'lucide-react';
import api from '../api/axios';
import { useTranslation } from '../context/LanguageContext';
import { format } from 'date-fns';
import { es, enUS } from 'date-fns/locale';

interface AssignmentHistoryItem {
  seller_id: string;
  seller_name?: string;
  seller_role?: string;
  assigned_at: string;
  assigned_by: string;
  assigned_by_name?: string;
  source: string;
  reason?: string;
}

interface AssignmentHistoryProps {
  phone: string;
  leadId?: string;
  maxItems?: number;
  showTitle?: boolean;
  className?: string;
}

const AssignmentHistory: React.FC<AssignmentHistoryProps> = ({
  phone,
  leadId,
  maxItems = 5,
  showTitle = true,
  className = ''
}) => {
  const { t, language } = useTranslation();
  const [history, setHistory] = useState<AssignmentHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const locale = language === 'es' ? es : enUS;
  
  useEffect(() => {
    fetchHistory();
  }, [phone, leadId]);
  
  const fetchHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Try to get from lead assignment history first
      if (leadId) {
        const leadResponse = await api.get(`/admin/core/crm/leads/${leadId}`);
        if (leadResponse.data.success && leadResponse.data.lead.assignment_history) {
          const leadHistory = leadResponse.data.lead.assignment_history;
          if (Array.isArray(leadHistory) && leadHistory.length > 0) {
            setHistory(leadHistory);
            setLoading(false);
            return;
          }
        }
      }
      
      // Fallback: get from chat messages
      const response = await api.get(`/admin/core/sellers/conversations/${phone}/assignment`);
      
      if (response.data.success && response.data.assignment) {
        const assignment = response.data.assignment;
        setHistory([{
          seller_id: assignment.assigned_seller_id,
          seller_name: assignment.seller_first_name 
            ? `${assignment.seller_first_name} ${assignment.seller_last_name}`
            : undefined,
          seller_role: assignment.seller_role,
          assigned_at: assignment.assigned_at,
          assigned_by: assignment.assigned_by,
          assigned_by_name: assignment.assigned_by_first_name
            ? `${assignment.assigned_by_first_name} ${assignment.assigned_by_last_name}`
            : undefined,
          source: assignment.assignment_source
        }]);
      } else {
        setHistory([]);
      }
    } catch (err: any) {
      console.error('Error fetching assignment history:', err);
      setError(err.response?.data?.detail || t('sellers.error_fetching_history'));
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };
  
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return format(date, 'PPpp', { locale });
    } catch (err) {
      return dateString;
    }
  };
  
  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'auto':
        return <span className="text-sm">🤖</span>;
      case 'auto_round_robin':
        return <span className="text-sm">🔄</span>;
      case 'auto_performance':
        return <span className="text-sm">📈</span>;
      case 'auto_specialty':
        return <span className="text-sm">🎯</span>;
      case 'prospecting':
        return <span className="text-sm">🔍</span>;
      case 'reassignment':
        return <span className="text-sm">🔄</span>;
      default:
        return <User size={14} />;
    }
  };
  
  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'auto':
        return t('sellers.source_auto');
      case 'auto_round_robin':
        return t('sellers.source_round_robin');
      case 'auto_performance':
        return t('sellers.source_performance');
      case 'auto_specialty':
        return t('sellers.source_specialty');
      case 'prospecting':
        return t('sellers.source_prospecting');
      case 'reassignment':
        return t('sellers.source_reassignment');
      default:
        return t('sellers.source_manual');
    }
  };
  
  const getRoleColor = (role?: string) => {
    switch (role) {
      case 'ceo':
        return 'bg-purple-500/10 text-purple-400';
      case 'setter':
        return 'bg-violet-500/100/10 text-violet-400';
      case 'closer':
        return 'bg-green-500/100/10 text-green-400';
      default:
        return 'bg-white/[0.03]/[0.04] text-white/70';
    }
  };
  
  if (loading) {
    return (
      <div className={`p-4 text-center ${className}`}>
        <Loader2 className="animate-spin mx-auto text-white/30" size={20} />
        <p className="text-white/40 text-sm mt-2">{t('sellers.loading_history')}</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className={`p-4 text-center ${className}`}>
        <p className="text-red-500 text-sm">{error}</p>
        <button
          onClick={fetchHistory}
          className="mt-2 text-sm text-violet-400 hover:text-violet-300 font-medium flex items-center gap-1 mx-auto"
        >
          <RefreshCw size={14} />
          {t('sellers.retry')}
        </button>
      </div>
    );
  }
  
  if (history.length === 0) {
    return (
      <div className={`p-4 text-center ${className}`}>
        <History className="mx-auto text-white/20" size={24} />
        <p className="text-white/40 text-sm mt-2">{t('sellers.no_history')}</p>
      </div>
    );
  }
  
  const displayHistory = maxItems ? history.slice(0, maxItems) : history;
  
  return (
    <div className={`bg-white/[0.03]/[0.03] rounded-lg border border-white/[0.06] ${className}`}>
      {showTitle && (
        <div className="p-3 border-b border-white/[0.04]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History size={16} className="text-white/50" />
              <h4 className="font-medium text-white">{t('sellers.assignment_history')}</h4>
            </div>
            <span className="text-xs text-white/40">
              {history.length} {t('sellers.items')}
            </span>
          </div>
        </div>
      )}
      
      <div className="divide-y divide-white/[0.04]">
        {displayHistory.map((item, index) => (
          <div key={index} className="p-3">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <div className={`px-2 py-0.5 text-xs rounded ${getRoleColor(item.seller_role)}`}>
                    {item.seller_role ? t(`roles.${item.seller_role}`) : t('roles.seller')}
                  </div>
                  
                  <div className="flex items-center gap-1 text-xs text-white/40">
                    {getSourceIcon(item.source)}
                    <span>{getSourceLabel(item.source)}</span>
                  </div>
                </div>
                
                <div className="mb-2">
                  <p className="font-medium text-white">
                    {item.seller_name || t('sellers.unknown_seller')}
                  </p>
                  {item.reason && (
                    <p className="text-sm text-white/50 mt-1">{item.reason}</p>
                  )}
                </div>
                
                <div className="flex items-center gap-4 text-xs text-white/40">
                  <div className="flex items-center gap-1">
                    <Calendar size={12} />
                    <span>{formatDate(item.assigned_at)}</span>
                  </div>
                  
                  {item.assigned_by_name && (
                    <div className="flex items-center gap-1">
                      <User size={12} />
                      <span>{t('sellers.assigned_by')}: {item.assigned_by_name}</span>
                    </div>
                  )}
                </div>
              </div>
              
              {index === 0 && (
                <div className="ml-2">
                  <span className="px-2 py-0.5 text-xs bg-green-500/100/10 text-green-400 rounded-full">
                    {t('sellers.current')}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {maxItems && history.length > maxItems && (
        <div className="p-3 border-t border-white/[0.04] text-center">
          <button
            onClick={() => {/* TODO: Show full history modal */}}
            className="text-sm text-violet-400 hover:text-violet-300 font-medium flex items-center gap-1 mx-auto"
          >
            {t('sellers.view_all_history')} ({history.length})
            <ExternalLink size={14} />
          </button>
        </div>
      )}
      
      <div className="p-2 bg-white/[0.03]/[0.02] border-t border-white/[0.04] text-center">
        <button
          onClick={fetchHistory}
          className="text-xs text-white/40 hover:text-white/70 flex items-center gap-1 mx-auto"
        >
          <RefreshCw size={12} />
          {t('sellers.refresh')}
        </button>
      </div>
    </div>
  );
};

export default AssignmentHistory;