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
        return 'bg-purple-100 text-purple-700';
      case 'setter':
        return 'bg-blue-100 text-blue-700';
      case 'closer':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };
  
  if (loading) {
    return (
      <div className={`p-4 text-center ${className}`}>
        <Loader2 className="animate-spin mx-auto text-gray-400" size={20} />
        <p className="text-gray-500 text-sm mt-2">{t('sellers.loading_history')}</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className={`p-4 text-center ${className}`}>
        <p className="text-red-500 text-sm">{error}</p>
        <button
          onClick={fetchHistory}
          className="mt-2 text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1 mx-auto"
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
        <History className="mx-auto text-gray-300" size={24} />
        <p className="text-gray-500 text-sm mt-2">{t('sellers.no_history')}</p>
      </div>
    );
  }
  
  const displayHistory = maxItems ? history.slice(0, maxItems) : history;
  
  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      {showTitle && (
        <div className="p-3 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History size={16} className="text-gray-600" />
              <h4 className="font-medium text-gray-900">{t('sellers.assignment_history')}</h4>
            </div>
            <span className="text-xs text-gray-500">
              {history.length} {t('sellers.items')}
            </span>
          </div>
        </div>
      )}
      
      <div className="divide-y divide-gray-100">
        {displayHistory.map((item, index) => (
          <div key={index} className="p-3">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <div className={`px-2 py-0.5 text-xs rounded ${getRoleColor(item.seller_role)}`}>
                    {item.seller_role ? t(`roles.${item.seller_role}`) : t('roles.seller')}
                  </div>
                  
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    {getSourceIcon(item.source)}
                    <span>{getSourceLabel(item.source)}</span>
                  </div>
                </div>
                
                <div className="mb-2">
                  <p className="font-medium text-gray-900">
                    {item.seller_name || t('sellers.unknown_seller')}
                  </p>
                  {item.reason && (
                    <p className="text-sm text-gray-600 mt-1">{item.reason}</p>
                  )}
                </div>
                
                <div className="flex items-center gap-4 text-xs text-gray-500">
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
                  <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                    {t('sellers.current')}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {maxItems && history.length > maxItems && (
        <div className="p-3 border-t border-gray-100 text-center">
          <button
            onClick={() => {/* TODO: Show full history modal */}}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1 mx-auto"
          >
            {t('sellers.view_all_history')} ({history.length})
            <ExternalLink size={14} />
          </button>
        </div>
      )}
      
      <div className="p-2 bg-gray-50 border-t border-gray-100 text-center">
        <button
          onClick={fetchHistory}
          className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 mx-auto"
        >
          <RefreshCw size={12} />
          {t('sellers.refresh')}
        </button>
      </div>
    </div>
  );
};

export default AssignmentHistory;