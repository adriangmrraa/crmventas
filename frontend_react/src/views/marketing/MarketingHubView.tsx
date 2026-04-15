import { useState, useEffect } from 'react';
import { Megaphone, RefreshCw, ExternalLink, Globe } from 'lucide-react';
import api from '../../api/axios';
import PageHeader from '../../components/PageHeader';
import { useTranslation } from '../../context/LanguageContext';
import MarketingPerformanceCard from '../../components/marketing/MarketingPerformanceCard';
import MetaConnectionWizard from '../../components/marketing/MetaConnectionWizard';
import GoogleConnectionWizard from '../../components/marketing/GoogleConnectionWizard';
import { getCurrentTenantId } from '../../api/axios';
import { useSearchParams } from 'react-router-dom';

export default function MarketingHubView() {
    const { t } = useTranslation();
    const [searchParams, setSearchParams] = useSearchParams();
    const [stats, setStats] = useState<any>(null);
    const [isMetaConnected, setIsMetaConnected] = useState(false);
    const [isGoogleConnected, setIsGoogleConnected] = useState(false);
    const [isMetaWizardOpen, setIsMetaWizardOpen] = useState(false);
    const [isGoogleWizardOpen, setIsGoogleWizardOpen] = useState(false);
    const [timeRange, setTimeRange] = useState('all');
    const [activeTab, setActiveTab] = useState<'campaigns' | 'ads'>('campaigns');
    const [activePlatform, setActivePlatform] = useState<'meta' | 'google'>('meta');

    useEffect(() => {
        loadStats();

        // Manejo de errores de OAuth
        const error = searchParams.get('error');
        if (error) {
            const errorMessages: Record<string, string> = {
                'missing_tenant': t('marketing.errors.missing_tenant'),
                'auth_failed': t('marketing.errors.auth_failed'),
                'token_exchange_failed': t('marketing.errors.token_exchange_failed'),
                'google_auth_failed': t('marketing.errors.google_auth_failed'),
                'invalid_state': t('marketing.errors.invalid_state'),
                'invalid_oauth_type': t('marketing.errors.invalid_oauth_type')
            };
            alert(errorMessages[error] || `${t('common.error')}: ${error}`);
            const newParams = new URLSearchParams(searchParams);
            newParams.delete('error');
            setSearchParams(newParams);
        }

        // Detectar si venimos de un login exitoso de Meta
        if (searchParams.get('success') === 'connected') {
            setIsMetaWizardOpen(true);
            const newParams = new URLSearchParams(searchParams);
            newParams.delete('success');
            setSearchParams(newParams);
        }

        // Detectar si venimos de un login exitoso de Google
        if (searchParams.get('success') === 'google_connected') {
            setIsGoogleWizardOpen(true);
            const newParams = new URLSearchParams(searchParams);
            newParams.delete('success');
            setSearchParams(newParams);
        }

        // Detectar si queremos iniciar reconexión automática desde el banner
        if (searchParams.get('reconnect') === 'true') {
            if (activePlatform === 'meta') {
                handleConnectMeta();
            } else {
                handleConnectGoogle();
            }
            const newParams = new URLSearchParams(searchParams);
            newParams.delete('reconnect');
            setSearchParams(newParams);
        }
    }, [searchParams, timeRange, activePlatform]);

    const loadStats = async () => {
        try {
            // Use combined endpoint to get both Meta and Google stats
            const { data } = await api.get(`/crm/marketing/combined-stats?range=${timeRange}&google_date_range=LAST_30_DAYS`);
            console.log("[MarketingHub] Combined stats data loaded:", data);
            
            const statsData = data.data || data;
            setStats(statsData);
            
            // Set connection status for both platforms
            setIsMetaConnected(statsData?.meta?.meta_connected || false);
            setIsGoogleConnected(statsData?.google?.connected || false);
            
            // Log for debugging
            console.log(`Meta connected: ${isMetaConnected}, Google connected: ${isGoogleConnected}`);
        } catch (error) {
            console.error("Error loading combined marketing stats:", error);
            // Fallback to old endpoint if combined fails
            try {
                const { data } = await api.get(`/crm/marketing/stats?range=${timeRange}`);
                console.log("[MarketingHub] Fallback stats data loaded:", data);
                setStats(data.data || data);
                setIsMetaConnected(data?.data?.meta_connected || data?.meta_connected || false);
                setIsGoogleConnected(false); // Assume Google not connected in fallback
            } catch (fallbackError) {
                console.error("Error loading fallback stats:", fallbackError);
            }
        }
    };

    const handleConnectMeta = async () => {
        try {
            const tenantId = getCurrentTenantId();
            const { data } = await api.get(`/crm/auth/meta/url?state=tenant_${tenantId}`);
            const authUrl = data?.data?.auth_url || data?.url || data?.auth_url;
            if (authUrl) {
                // Redirigir a la página de OAuth de Meta
                window.location.href = authUrl;
            } else {
                console.error("No auth_url in response:", data);
                alert(t('marketing.errors.init_failed'));
            }
        } catch (error) {
            console.error("Error initiating Meta OAuth:", error);
            alert(t('marketing.errors.init_failed'));
        }
    };

    const handleConnectGoogle = async () => {
        try {
            const tenantId = getCurrentTenantId();
            const { data } = await api.get(`/crm/auth/google/ads/url?state=tenant_${tenantId}`);
            const authUrl = data?.data?.auth_url || data?.url || data?.auth_url;
            if (authUrl) {
                // Redirigir a la página de OAuth de Google
                window.location.href = authUrl;
            } else {
                console.error("No auth_url in response:", data);
                alert(t('marketing.errors.google_init_failed'));
            }
        } catch (error) {
            console.error("Error initiating Google OAuth:", error);
            alert(t('marketing.errors.google_init_failed'));
        }
    };

    // Helper function to get data based on active platform
    const getPlatformData = () => {
        if (activePlatform === 'meta') {
            return activeTab === 'campaigns' 
                ? stats?.meta?.campaigns?.campaigns 
                : stats?.meta?.campaigns?.creatives;
        } else {
            // For Google Ads, use the new structure
            return stats?.google?.campaigns || [];
        }
    };

    // Helper function to get currency based on platform
    const getCurrency = () => {
        if (activePlatform === 'meta') {
            return stats?.meta?.currency === 'ARS' ? 'ARS' : '$';
        } else {
            // Google Ads typically uses dollars
            return '$';
        }
    };

    // Helper function to get platform-specific empty state message
    const getEmptyStateMessage = () => {
        if (activePlatform === 'meta') {
            return t('marketing.no_data');
        } else {
            if (!isGoogleConnected) {
                return t('marketing.google_not_connected');
            }
            return t('marketing.google_no_data');
        }
    };

    return (
        <div className="h-full w-full overflow-y-auto bg-white/[0.02]/50">
            <div className="p-4 sm:p-6 pb-24 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <PageHeader
                        title={t('nav.marketing')}
                        subtitle={t('marketing.subtitle')}
                        icon={<Megaphone size={24} />}
                    />

                    <div className="flex flex-wrap items-center gap-3 bg-white/[0.03] p-1.5 rounded-2xl border border-white/[0.06]">
                        {[
                            { id: 'last_30d', label: t('marketing.range_30d') },
                            { id: 'last_90d', label: t('marketing.range_90d') },
                            { id: 'this_year', label: t('marketing.range_year') },
                            { id: 'all', label: t('marketing.range_all') }
                        ].map(range => (
                            <button
                                key={range.id}
                                onClick={() => setTimeRange(range.id)}
                                className={`flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${timeRange === range.id
                                    ? 'bg-gray-900 text-white shadow-lg'
                                    : 'text-white/40 hover:bg-white/[0.02]'
                                    }`}
                            >
                                {range.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Platform Selection Tabs */}
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-3xl p-2">
                    <div className="flex bg-white/[0.04] p-1 rounded-2xl">
                        <button
                            onClick={() => setActivePlatform('meta')}
                            className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-bold transition-all ${activePlatform === 'meta'
                                ? 'bg-white/[0.03] text-white'
                                : 'text-white/40 hover:text-white/70'
                                }`}
                        >
                            <RefreshCw size={16} /> Meta Ads
                        </button>
                        <button
                            onClick={() => setActivePlatform('google')}
                            className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-bold transition-all ${activePlatform === 'google'
                                ? 'bg-white/[0.03] text-white'
                                : 'text-white/40 hover:text-white/70'
                                }`}
                        >
                            <Globe size={16} /> Google Ads
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Real ROI Card - Main Metric */}
                    <div className="lg:col-span-2">
                        <MarketingPerformanceCard 
                            stats={stats?.roi} 
                            loading={!stats} 
                            timeRange={timeRange}
                            platform={activePlatform}
                        />
                    </div>

                    {/* Connection Status Card */}
                    <div className="bg-white/[0.03] border border-white/[0.06] rounded-3xl p-8 flex flex-col justify-between">
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="font-bold text-white flex items-center gap-2">
                                    {activePlatform === 'meta' ? (
                                        <RefreshCw size={18} className={isMetaConnected ? "text-violet-500" : "text-white/30"} />
                                    ) : (
                                        <Globe size={18} className={isGoogleConnected ? "text-green-500" : "text-white/30"} />
                                    )}
                                    {activePlatform === 'meta' ? t('marketing.meta_connection') : t('marketing.google_connection')}
                                </h3>
                                <span className={`px-3 py-1 text-xs font-bold rounded-full ${activePlatform === 'meta' 
                                    ? (isMetaConnected ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400')
                                    : (isGoogleConnected ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400')
                                }`}>
                                    {activePlatform === 'meta' 
                                        ? (isMetaConnected ? t('marketing.connected_active') : t('marketing.connected_disconnected'))
                                        : (isGoogleConnected ? t('marketing.connected_active') : t('marketing.connected_disconnected'))
                                    }
                                </span>
                            </div>
                            <p className="text-sm text-white/40 mb-6">
                                {activePlatform === 'meta'
                                    ? (isMetaConnected ? t('marketing.connected_desc') : t('marketing.disconnected_desc'))
                                    : (isGoogleConnected ? t('marketing.google_connected_desc') : t('marketing.google_disconnected_desc'))
                                }
                            </p>
                        </div>

                        <button
                            onClick={activePlatform === 'meta' ? handleConnectMeta : handleConnectGoogle}
                            className={`w-full py-4 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all ${activePlatform === 'meta'
                                ? (isMetaConnected ? "bg-white/[0.04] text-white hover:bg-white/[0.06]" : "bg-gray-900 text-white hover:bg-black")
                                : (isGoogleConnected ? "bg-white/[0.04] text-white hover:bg-white/[0.06]" : "bg-green-600 text-white hover:bg-green-700")
                                }`}
                        >
                            <ExternalLink size={18} /> 
                            {activePlatform === 'meta'
                                ? (isMetaConnected ? t('marketing.reconnect') : t('marketing.connect'))
                                : (isGoogleConnected ? t('marketing.google_reconnect') : t('marketing.google_connect'))
                            }
                        </button>
                    </div>
                </div>



                {/* Campaign/Ad Table with Tabs */}
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-3xl overflow-hidden mb-12">
                    <div className="p-6 border-b border-white/[0.04] flex flex-col sm:flex-row justify-between items-center gap-4">
                        <div className="flex bg-white/[0.04] p-1 rounded-xl">
                            <button
                                onClick={() => setActiveTab('campaigns')}
                                className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'campaigns'
                                    ? 'bg-white/[0.03] text-white'
                                    : 'text-white/40 hover:text-white/70'
                                    }`}
                            >
                                {t('marketing.tabs.campaigns')}
                            </button>
                            <button
                                onClick={() => setActiveTab('ads')}
                                className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'ads'
                                    ? 'bg-white/[0.03] text-white'
                                    : 'text-white/40 hover:text-white/70'
                                    }`}
                            >
                                {t('marketing.tabs.creatives')}
                            </button>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-sm text-white/40 mr-2 capitalize">{t('marketing.period_label')}: {timeRange.replace('_', ' ')}</span>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        {/* Desktop Table View */}
                        <table className="hidden lg:table w-full text-left border-separate border-spacing-0">
                            <thead className="bg-white/[0.02] text-white/40 text-xs uppercase tracking-wider sticky top-0 z-10">
                                <tr>
                                    <th className="px-6 py-4 font-semibold border-b border-white/[0.04] w-1/3">
                                        {activeTab === 'campaigns' ? t('marketing.table_campaign_ad') : t('marketing.table_ad')}
                                    </th>
                                    <th className="px-6 py-4 font-semibold border-b border-white/[0.04]">{t('marketing.table_spend')}</th>
                                    <th className="px-6 py-4 font-semibold border-b border-white/[0.04]">{t('marketing.table_leads')}</th>
                                    <th className="px-6 py-4 font-semibold border-b border-white/[0.04]">{t('marketing.table_appts')}</th>
                                    <th className="px-6 py-4 font-semibold text-indigo-600 border-b border-white/[0.04]">{t('marketing.table_roi')}</th>
                                    <th className="px-6 py-4 font-semibold border-b border-white/[0.04]">{t('marketing.table_status')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {getPlatformData()?.map((c: any, index: number) => (
                                    <tr key={c.ad_id || c.id || `campaign-${index}`} className="hover:bg-violet-500/10/30 transition-colors group">
                                        <td className="px-6 py-4">
                                            <div className="font-bold text-white group-hover:text-violet-400 transition-colors">
                                                {c.ad_name || c.name || `Campaign ${index + 1}`}
                                            </div>
                                            <div className="text-xs text-white/30 font-medium">
                                                {c.campaign_name || c.channel_type || 'Google Ads'}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 font-bold text-white/70">
                                            {getCurrency()} {Number(c.spend || c.cost || 0).toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 font-medium text-white/50">{c.leads || c.conversions || 0}</td>
                                        <td className="px-6 py-4">
                                            <span className="font-bold text-green-400 bg-green-500/10 px-2.5 py-1 rounded-lg">
                                                {c.opportunities || Math.floor((c.conversions || 0) * 0.3)}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2.5 py-1 rounded-lg font-bold border ${(c.roi || 0) >= 0
                                                ? 'bg-indigo-50 text-indigo-700 border-indigo-100'
                                                : 'bg-rose-50 text-rose-700 border-rose-100'}`}>
                                                {(c.roi || 0) > 0 ? '+' : ''}{Math.round((c.roi || 0) * 100)}%
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`flex items-center gap-1.5 text-sm font-bold ${c.status === 'active' || c.status === 'ENABLED' ? 'text-green-400' : (c.status === 'paused' || c.status === 'PAUSED' || c.status === 'archived') ? 'text-amber-600' : 'text-white/30'}`}>
                                                <div className={`w-2 h-2 rounded-full ${c.status === 'active' || c.status === 'ENABLED' ? 'bg-green-500 animate-pulse' : (c.status === 'paused' || c.status === 'PAUSED' || c.status === 'archived') ? 'bg-amber-500' : 'bg-gray-300'}`}></div>
                                                <span className="capitalize">{c.status || 'Unknown'}</span>
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>

                        {/* Mobile Cards View (Stacking Pattern) */}
                        <div className="lg:hidden divide-y divide-gray-100">
                            {getPlatformData()?.map((c: any, index: number) => (
                                <div key={c.ad_id || c.id || `campaign-mobile-${index}`} className="p-5 space-y-4 hover:bg-white/[0.02] transition-colors">
                                    <div className="flex justify-between items-start">
                                        <div className="flex-1 min-w-0 pr-4">
                                            <div className="font-black text-white leading-tight mb-1">
                                                {c.ad_name || c.name || `Campaign ${index + 1}`}
                                            </div>
                                            <div className="text-[10px] text-white/30 font-bold uppercase tracking-wider">
                                                {c.campaign_name || c.channel_type || 'Google Ads'}
                                            </div>
                                        </div>
                                        <span className={`flex items-center gap-1 text-[10px] font-black uppercase px-2 py-1 rounded-full border ${c.status === 'active' || c.status === 'ENABLED' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-white/[0.04] text-white/40 border-white/[0.06]'}`}>
                                            <div className={`w-1.5 h-1.5 rounded-full ${c.status === 'active' || c.status === 'ENABLED' ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                                            {c.status || 'Unknown'}
                                        </span>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4 pt-2">
                                        <div>
                                            <div className="text-[10px] text-white/30 font-bold uppercase mb-1">{t('marketing.table_spend')}</div>
                                            <div className="font-black text-white">{getCurrency()}{Number(c.spend || c.cost || 0).toLocaleString()}</div>
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-indigo-400 font-bold uppercase mb-1">{t('marketing.table_roi')}</div>
                                            <div className={`font-black ${(c.roi || 0) >= 0 ? 'text-indigo-600' : 'text-rose-600'}`}>
                                                {(c.roi || 0) > 0 ? '+' : ''}{Math.round((c.roi || 0) * 100)}%
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-white/30 font-bold uppercase mb-1">{t('marketing.table_leads')}</div>
                                            <div className="font-bold text-white/70">{c.leads || c.conversions || 0}</div>
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-green-500 font-bold uppercase mb-1">{t('marketing.table_appts')}</div>
                                            <div className="font-black text-green-400">{c.opportunities || Math.floor((c.conversions || 0) * 0.3)}</div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Empty State */}
                        {!getPlatformData()?.length && (
                            <div className="px-6 py-20 text-center text-white/30 italic">
                                {activePlatform === 'meta' ? (
                                    <Megaphone className="w-10 h-10 mx-auto mb-4 opacity-20" />
                                ) : (
                                    <Globe className="w-10 h-10 mx-auto mb-4 opacity-20" />
                                )}
                                {getEmptyStateMessage()}
                            </div>
                        )}
                    </div>
                </div>

                <div className="h-20" /> {/* Spacer for extra breathing room at the bottom */}

                {/* Meta Connection Wizard Modal */}
                <MetaConnectionWizard
                    isOpen={isMetaWizardOpen}
                    onClose={() => setIsMetaWizardOpen(false)}
                    onSuccess={() => {
                        setIsMetaWizardOpen(false);
                        loadStats();
                    }}
                />

                {/* Google Connection Wizard Modal */}
                <GoogleConnectionWizard
                    isOpen={isGoogleWizardOpen}
                    onClose={() => setIsGoogleWizardOpen(false)}
                    onSuccess={() => {
                        setIsGoogleWizardOpen(false);
                        loadStats();
                    }}
                />
            </div>
        </div>
    );
}
