import React, { useState, useEffect } from 'react';
import { 
  BarChart3, TrendingUp, Users, MessageSquare, Target, Clock, 
  Zap, DollarSign, Calendar, Loader2, RefreshCw, Download,
  UserCheck, UserX, PieChart
} from 'lucide-react';
import api from '../api/axios';
import { useTranslation } from '../context/LanguageContext';
import { format } from 'date-fns';
import { es, enUS } from 'date-fns/locale';

interface SellerMetrics {
  seller_id: string;
  tenant_id: number;
  total_conversations: number;
  active_conversations: number;
  conversations_assigned_today: number;
  total_messages_sent: number;
  total_messages_received: number;
  avg_response_time_seconds: number;
  leads_assigned: number;
  leads_converted: number;
  conversion_rate: number;
  prospects_generated: number;
  prospects_converted: number;
  total_chat_minutes: number;
  avg_conversation_duration_minutes: number;
  last_activity_at: string;
  metrics_calculated_at: string;
  metrics_period_start: string;
  metrics_period_end: string;
}

interface SellerMetricsDashboardProps {
  sellerId?: string; // If not provided, shows current user's metrics
  periodDays?: number;
  showTitle?: boolean;
  showRefresh?: boolean;
  className?: string;
}

const SellerMetricsDashboard: React.FC<SellerMetricsDashboardProps> = ({
  sellerId,
  periodDays = 7,
  showTitle = true,
  showRefresh = true,
  className = ''
}) => {
  const { t, language } = useTranslation();
  const [metrics, setMetrics] = useState<SellerMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState(periodDays);
  
  const locale = language === 'es' ? es : enUS;
  
  useEffect(() => {
    fetchMetrics();
  }, [sellerId, period]);
  
  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const targetSellerId = sellerId; // TODO: Get from props or current user
      
      if (!targetSellerId) {
        setError(t('sellers.error_no_seller_id'));
        setLoading(false);
        return;
      }
      
      const response = await api.get(`/admin/core/sellers/${targetSellerId}/metrics`, {
        params: { period_days: period }
      });
      
      if (response.data.success) {
        setMetrics(response.data.metrics);
      } else {
        setError(response.data.message || t('sellers.error_fetching_metrics'));
      }
    } catch (err: any) {
      console.error('Error fetching seller metrics:', err);
      setError(err.response?.data?.detail || t('sellers.error_fetching_metrics'));
    } finally {
      setLoading(false);
    }
  };
  
  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      return `${Math.round(seconds / 60)}m`;
    } else {
      return `${Math.round(seconds / 3600)}h`;
    }
  };
  
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return format(date, 'PP', { locale });
    } catch (err) {
      return dateString;
    }
  };
  
  const exportMetrics = () => {
    if (!metrics) return;
    
    const csvContent = [
      ['Metric', 'Value'],
      ['Total Conversations', metrics.total_conversations],
      ['Active Conversations', metrics.active_conversations],
      ['Conversations Today', metrics.conversations_assigned_today],
      ['Messages Sent', metrics.total_messages_sent],
      ['Messages Received', metrics.total_messages_received],
      ['Avg Response Time', formatTime(metrics.avg_response_time_seconds)],
      ['Leads Assigned', metrics.leads_assigned],
      ['Leads Converted', metrics.leads_converted],
      ['Conversion Rate', `${metrics.conversion_rate}%`],
      ['Prospects Generated', metrics.prospects_generated],
      ['Prospects Converted', metrics.prospects_converted],
      ['Total Chat Minutes', metrics.total_chat_minutes],
      ['Avg Session Duration', `${metrics.avg_conversation_duration_minutes}m`],
      ['Last Activity', formatDate(metrics.last_activity_at)],
      ['Period', `${formatDate(metrics.metrics_period_start)} - ${formatDate(metrics.metrics_period_end)}`]
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seller-metrics-${sellerId}-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };
  
  if (loading) {
    return (
      <div className={`p-8 text-center ${className}`}>
        <Loader2 className="animate-spin mx-auto text-gray-400" size={32} />
        <p className="text-gray-500 text-sm mt-3">{t('sellers.loading_metrics')}</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className={`p-6 text-center ${className}`}>
        <BarChart3 className="mx-auto text-gray-300" size={40} />
        <p className="text-red-500 text-sm mt-3">{error}</p>
        <button
          onClick={fetchMetrics}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 mx-auto"
        >
          <RefreshCw size={16} />
          {t('sellers.retry')}
        </button>
      </div>
    );
  }
  
  if (!metrics) {
    return (
      <div className={`p-6 text-center ${className}`}>
        <BarChart3 className="mx-auto text-gray-300" size={40} />
        <p className="text-gray-500 text-sm mt-3">{t('sellers.no_metrics')}</p>
      </div>
    );
  }
  
  const statCards = [
    {
      title: t('sellers.total_conversations'),
      value: metrics.total_conversations,
      icon: Users,
      color: 'bg-blue-100 text-blue-600',
      trend: metrics.active_conversations > 0 ? 'positive' : 'neutral'
    },
    {
      title: t('sellers.active_conversations'),
      value: metrics.active_conversations,
      icon: MessageSquare,
      color: 'bg-green-100 text-green-600',
      trend: 'positive'
    },
    {
      title: t('sellers.conversion_rate'),
      value: `${metrics.conversion_rate}%`,
      icon: TrendingUp,
      color: 'bg-purple-100 text-purple-600',
      trend: metrics.conversion_rate > 20 ? 'positive' : metrics.conversion_rate > 5 ? 'neutral' : 'negative'
    },
    {
      title: t('sellers.avg_response_time'),
      value: formatTime(metrics.avg_response_time_seconds),
      icon: Clock,
      color: 'bg-yellow-100 text-yellow-600',
      trend: metrics.avg_response_time_seconds < 300 ? 'positive' : metrics.avg_response_time_seconds < 900 ? 'neutral' : 'negative'
    },
    {
      title: t('sellers.leads_converted'),
      value: metrics.leads_converted,
      icon: Target,
      color: 'bg-red-100 text-red-600',
      trend: metrics.leads_converted > 0 ? 'positive' : 'neutral'
    },
    {
      title: t('sellers.total_messages'),
      value: metrics.total_messages_sent + metrics.total_messages_received,
      icon: Zap,
      color: 'bg-indigo-100 text-indigo-600',
      trend: 'positive'
    }
  ];
  
  const detailMetrics = [
    {
      label: t('sellers.messages_sent'),
      value: metrics.total_messages_sent,
      icon: MessageSquare
    },
    {
      label: t('sellers.messages_received'),
      value: metrics.total_messages_received,
      icon: MessageSquare
    },
    {
      label: t('sellers.leads_assigned'),
      value: metrics.leads_assigned,
      icon: UserCheck
    },
    {
      label: t('sellers.prospects_generated'),
      value: metrics.prospects_generated,
      icon: UserCheck
    },
    {
      label: t('sellers.prospects_converted'),
      value: metrics.prospects_converted,
      icon: UserCheck
    },
    {
      label: t('sellers.total_chat_time'),
      value: `${Math.round(metrics.total_chat_minutes)}m`,
      icon: Clock
    },
    {
      label: t('sellers.avg_session_duration'),
      value: `${Math.round(metrics.avg_conversation_duration_minutes)}m`,
      icon: Clock
    },
    {
      label: t('sellers.last_activity'),
      value: formatDate(metrics.last_activity_at),
      icon: Calendar
    }
  ];
  
  return (
    <div className={`bg-white rounded-xl border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
              <BarChart3 size={20} />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">
                {showTitle ? t('sellers.performance_metrics') : t('sellers.metrics')}
              </h3>
              <p className="text-sm text-gray-500">
                {t('sellers.period')}: {formatDate(metrics.metrics_period_start)} - {formatDate(metrics.metrics_period_end)}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {showRefresh && (
              <button
                onClick={fetchMetrics}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                title={t('sellers.refresh')}
              >
                <RefreshCw size={18} />
              </button>
            )}
            
            <button
              onClick={exportMetrics}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              title={t('sellers.export')}
            >
              <Download size={18} />
            </button>
            
            <select
              value={period}
              onChange={(e) => setPeriod(Number(e.target.value))}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            >
              <option value={1}>{t('sellers.last_1_day')}</option>
              <option value={7}>{t('sellers.last_7_days')}</option>
              <option value={30}>{t('sellers.last_30_days')}</option>
              <option value={90}>{t('sellers.last_90_days')}</option>
            </select>
          </div>
        </div>
      </div>
      
      {/* Stats Grid */}
      <div className="p-4 border-b border-gray-100">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {statCards.map((stat, index) => (
            <div key={index} className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className={`p-1.5 rounded-md ${stat.color}`}>
                  <stat.icon size={16} />
                </div>
                <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                  stat.trend === 'positive' ? 'bg-green-100 text-green-700' :
                  stat.trend === 'negative' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {stat.trend === 'positive' ? '↑' : stat.trend === 'negative' ? '↓' : '→'}
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-xs text-gray-500 mt-1">{stat.title}</p>
            </div>
          ))}
        </div>
      </div>
      
      {/* Detailed Metrics */}
      <div className="p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {detailMetrics.map((metric, index) => (
            <div key={index} className="border border-gray-200 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <metric.icon size={14} className="text-gray-400" />
                <span className="text-xs font-medium text-gray-500">{metric.label}</span>
              </div>
              <p className="text-lg font-semibold text-gray-900">{metric.value}</p>
            </div>
          ))}
        </div>
        
        {/* Conversion Insights */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <PieChart size={18} className="text-blue-600" />
              <h4 className="font-medium text-gray-900">{t('sellers.conversion_insights')}</h4>
            </div>
            
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">{t('sellers.lead_conversion')}</span>
                  <span className="font-medium">{metrics.leads_converted} / {metrics.leads_assigned}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-500 h-2 rounded-full" 
                    style={{ width: `${(metrics.leads_converted / Math.max(metrics.leads_assigned, 1)) * 100}%` }}
                  />
                </div>
              </div>
              
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">{t('sellers.prospect_conversion')}</span>
                  <span className="font-medium">{metrics.prospects_converted} / {metrics.prospects_generated}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full" 
                    style={{ width: `${(metrics.prospects_converted / Math.max(metrics.prospects_generated, 1)) * 100}%` }}
                  />
                </div>
              </div>
              
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">{t('sellers.message_ratio')}</span>
                  <span className="font-medium">
                    {Math.round((metrics.total_messages_sent / Math.max(metrics.total_messages_received, 1)) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-purple-500 h-2 rounded-full" 
                    style={{ width: `${Math.min((metrics.total_messages_sent / Math.max(metrics.total_messages_received, 1)) * 100, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
          
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap size={18} className="text-yellow-600" />
              <h4 className="font-medium text-gray-900">{t('sellers.activity_summary')}</h4>
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{t('sellers.conversations_today')}</span>
                <span className="font-medium">{metrics.conversations_assigned_today}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{t('sellers.avg_daily_conversations')}</span>
                <span className="font-medium">
                  {Math.round(metrics.total_conversations / period)}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{t('sellers.avg_daily_messages')}</span>
                <span className="font-medium">
                  {Math.round((metrics.total_messages_sent + metrics.total_messages_received) / period)}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{t('sellers.avg_session_duration')}</span>
                <span className="font-medium">{Math.round(metrics.avg_conversation_duration_minutes)}m</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{t('sellers.response_time_goal')}</span>
                <span className={`font-medium ${
                  metrics.avg_response_time_seconds < 300 ? 'text-green-600' :
                  metrics.avg_response_time_seconds < 900 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {formatTime(metrics.avg_response_time_seconds)}
                </span>
              </div>
            </div>
            
            <div className="mt-4 pt-3 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{t('sellers.performance_score')}</span>
                <span className={`text-lg font-bold ${
                  metrics.conversion_rate > 20 ? 'text-green-600' :
                  metrics.conversion_rate > 10 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {Math.round(
                    (metrics.conversion_rate * 0.4) +
                    ((metrics.leads_converted / Math.max(period, 1)) * 30) +
                    (metrics.active_conversations * 2) +
                    (metrics.avg_response_time_seconds < 300 ? 20 : metrics.avg_response_time_seconds < 600 ? 10 : 0)
                  )}/100
                </span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Recommendations */}
        {metrics.conversion_rate < 10 && (
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start gap-3">
              <Zap size={18} className="text-yellow-600 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-medium text-yellow-800">{t('sellers.improvement_suggestions')}</h4>
                <ul className="mt-2 space-y-1 text-sm text-yellow-700">
                  {metrics.avg_response_time_seconds > 600 && (
                    <li>• {t('sellers.suggestion_response_time')}</li>
                  )}
                  {metrics.leads_converted === 0 && metrics.leads_assigned > 0 && (
                    <li>• {t('sellers.suggestion_follow_up')}</li>
                  )}
                  {metrics.active_conversations < 3 && (
                    <li>• {t('sellers.suggestion_more_conversations')}</li>
                  )}
                  {metrics.total_messages_sent < metrics.total_messages_received * 0.5 && (
                    <li>• {t('sellers.suggestion_engagement')}</li>
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="p-3 bg-gray-50 border-t border-gray-100 text-center">
        <p className="text-xs text-gray-500">
          {t('sellers.metrics_updated')}: {formatDate(metrics.metrics_calculated_at)}
        </p>
      </div>
    </div>
  );
};

export default SellerMetricsDashboard;