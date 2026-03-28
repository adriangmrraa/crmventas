import { useState, useEffect } from 'react';
import {
  MessageCircle, Instagram, Facebook, Link2, CheckCircle2,
  AlertCircle, Loader2, RefreshCw, ExternalLink, Wifi, WifiOff,
  Phone, Settings2
} from 'lucide-react';
import api from '../../api/axios';
import MetaConnectionWizard from '../marketing/MetaConnectionWizard';

type ChannelTab = 'whatsapp' | 'instagram' | 'facebook' | 'meta';

interface ChannelBinding {
  channel: string;
  connected: boolean;
  account_id?: string;
  account_name?: string;
  phone_number?: string;
  page_name?: string;
  connected_at?: string;
}

interface YCloudStatus {
  connected: boolean;
  phone_number?: string;
  display_name?: string;
  quality_rating?: string;
  api_key_configured?: boolean;
}

export default function IntegrationsView() {
  const [activeTab, setActiveTab] = useState<ChannelTab>('whatsapp');
  const [bindings, setBindings] = useState<ChannelBinding[]>([]);
  const [ycloudStatus, setYcloudStatus] = useState<YCloudStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [showMetaWizard, setShowMetaWizard] = useState(false);

  useEffect(() => {
    loadIntegrationData();
  }, []);

  const loadIntegrationData = async () => {
    setLoading(true);
    try {
      const [bindingsRes, ycloudRes] = await Promise.allSettled([
        api.get('/admin/core/integrations/channel-bindings'),
        api.get('/admin/core/integrations/ycloud-status'),
      ]);

      if (bindingsRes.status === 'fulfilled') {
        setBindings(bindingsRes.value.data?.bindings || []);
      }
      if (ycloudRes.status === 'fulfilled') {
        setYcloudStatus(ycloudRes.value.data || null);
      }
    } catch (err) {
      console.error('Error loading integration data:', err);
    } finally {
      setLoading(false);
    }
  };

  const tabs: { id: ChannelTab; label: string; icon: React.ReactNode; color: string }[] = [
    { id: 'whatsapp', label: 'WhatsApp', icon: <MessageCircle size={18} />, color: 'text-green-400' },
    { id: 'instagram', label: 'Instagram', icon: <Instagram size={18} />, color: 'text-purple-400' },
    { id: 'facebook', label: 'Facebook', icon: <Facebook size={18} />, color: 'text-blue-400' },
    { id: 'meta', label: 'Meta Connection', icon: <Link2 size={18} />, color: 'text-white/70' },
  ];

  const getBindingForChannel = (channel: string) =>
    bindings.find(b => b.channel === channel);

  const renderChannelStatus = (channel: string, binding: ChannelBinding | undefined) => (
    <div className="flex items-center gap-2 mt-2">
      {binding?.connected ? (
        <>
          <Wifi size={14} className="text-green-400" />
          <span className="text-sm text-green-400 font-medium">Conectado</span>
        </>
      ) : (
        <>
          <WifiOff size={14} className="text-white/30" />
          <span className="text-sm text-white/30">No conectado</span>
        </>
      )}
    </div>
  );

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/[0.06] flex items-center justify-center">
            <Link2 size={20} className="text-white/70" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Integraciones</h1>
            <p className="text-sm text-white/40">Canales de mensajeria y conexiones</p>
          </div>
        </div>
        <button
          onClick={loadIntegrationData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[0.04] text-white/70 hover:bg-white/[0.08] border border-white/[0.06] text-sm transition-all disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Actualizar
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-white/[0.03] rounded-xl border border-white/[0.06] mb-6">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center
              ${activeTab === tab.id
                ? 'bg-white/[0.08] text-white shadow-sm'
                : 'text-white/40 hover:text-white/70 hover:bg-white/[0.03]'
              }`}
          >
            <span className={activeTab === tab.id ? tab.color : ''}>{tab.icon}</span>
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={32} className="animate-spin text-white/30" />
        </div>
      ) : (
        <div className="space-y-4">
          {/* WhatsApp Tab */}
          {activeTab === 'whatsapp' && (
            <div className="space-y-4">
              {/* YCloud Config Status */}
              <div className="p-5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                    <MessageCircle size={20} className="text-green-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">WhatsApp Business API</h3>
                    <p className="text-xs text-white/40">via YCloud</p>
                  </div>
                  {ycloudStatus?.connected ? (
                    <CheckCircle2 size={20} className="text-green-400 ml-auto" />
                  ) : (
                    <AlertCircle size={20} className="text-yellow-400 ml-auto" />
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <p className="text-xs text-white/40 mb-1">Estado</p>
                    <div className="flex items-center gap-2">
                      {ycloudStatus?.connected ? (
                        <>
                          <div className="w-2 h-2 rounded-full bg-green-400" />
                          <span className="text-sm text-green-400 font-medium">Activo</span>
                        </>
                      ) : (
                        <>
                          <div className="w-2 h-2 rounded-full bg-yellow-400" />
                          <span className="text-sm text-yellow-400 font-medium">Sin configurar</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <p className="text-xs text-white/40 mb-1">Numero conectado</p>
                    <div className="flex items-center gap-2">
                      <Phone size={14} className="text-white/50" />
                      <span className="text-sm text-white/80 font-mono">
                        {ycloudStatus?.phone_number || 'No configurado'}
                      </span>
                    </div>
                  </div>

                  {ycloudStatus?.display_name && (
                    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <p className="text-xs text-white/40 mb-1">Nombre visible</p>
                      <span className="text-sm text-white/80">{ycloudStatus.display_name}</span>
                    </div>
                  )}

                  {ycloudStatus?.quality_rating && (
                    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <p className="text-xs text-white/40 mb-1">Calidad</p>
                      <span className={`text-sm font-medium ${
                        ycloudStatus.quality_rating === 'GREEN' ? 'text-green-400' :
                        ycloudStatus.quality_rating === 'YELLOW' ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                        {ycloudStatus.quality_rating}
                      </span>
                    </div>
                  )}

                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <p className="text-xs text-white/40 mb-1">API Key</p>
                    <span className={`text-sm font-medium ${ycloudStatus?.api_key_configured ? 'text-green-400' : 'text-red-400'}`}>
                      {ycloudStatus?.api_key_configured ? 'Configurada' : 'No configurada'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Channel Binding */}
              {(() => {
                const binding = getBindingForChannel('whatsapp');
                return (
                  <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-white/60">Channel Binding</span>
                      {renderChannelStatus('whatsapp', binding)}
                    </div>
                    {binding?.connected_at && (
                      <p className="text-xs text-white/30 mt-1">
                        Conectado el {new Date(binding.connected_at).toLocaleDateString('es-AR')}
                      </p>
                    )}
                  </div>
                );
              })()}
            </div>
          )}

          {/* Instagram Tab */}
          {activeTab === 'instagram' && (
            <div className="space-y-4">
              <div className="p-5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                    <Instagram size={20} className="text-purple-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Instagram Direct</h3>
                    <p className="text-xs text-white/40">via Meta Graph API</p>
                  </div>
                </div>

                {(() => {
                  const binding = getBindingForChannel('instagram');
                  return binding?.connected ? (
                    <div className="space-y-3">
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <p className="text-xs text-white/40 mb-1">Cuenta conectada</p>
                        <span className="text-sm text-white/80">{binding.account_name || binding.account_id}</span>
                      </div>
                      {renderChannelStatus('instagram', binding)}
                    </div>
                  ) : (
                    <div className="text-center py-6">
                      <Instagram size={40} className="text-white/10 mx-auto mb-3" />
                      <p className="text-sm text-white/40 mb-3">Instagram no esta conectado</p>
                      <button
                        onClick={() => { setActiveTab('meta'); setShowMetaWizard(true); }}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 text-sm hover:bg-purple-500/20 transition-colors"
                      >
                        <ExternalLink size={14} />
                        Conectar via Meta
                      </button>
                    </div>
                  );
                })()}
              </div>
            </div>
          )}

          {/* Facebook Tab */}
          {activeTab === 'facebook' && (
            <div className="space-y-4">
              <div className="p-5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                    <Facebook size={20} className="text-blue-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Facebook Messenger</h3>
                    <p className="text-xs text-white/40">via Meta Graph API</p>
                  </div>
                </div>

                {(() => {
                  const binding = getBindingForChannel('facebook');
                  return binding?.connected ? (
                    <div className="space-y-3">
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <p className="text-xs text-white/40 mb-1">Pagina conectada</p>
                        <span className="text-sm text-white/80">{binding.page_name || binding.account_id}</span>
                      </div>
                      {renderChannelStatus('facebook', binding)}
                    </div>
                  ) : (
                    <div className="text-center py-6">
                      <Facebook size={40} className="text-white/10 mx-auto mb-3" />
                      <p className="text-sm text-white/40 mb-3">Facebook Messenger no esta conectado</p>
                      <button
                        onClick={() => { setActiveTab('meta'); setShowMetaWizard(true); }}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 text-sm hover:bg-blue-500/20 transition-colors"
                      >
                        <ExternalLink size={14} />
                        Conectar via Meta
                      </button>
                    </div>
                  );
                })()}
              </div>
            </div>
          )}

          {/* Meta Connection Tab */}
          {activeTab === 'meta' && (
            <div className="space-y-4">
              <div className="p-5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-white/[0.06] flex items-center justify-center">
                    <Settings2 size={20} className="text-white/60" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Meta Business Suite</h3>
                    <p className="text-xs text-white/40">Conectar Instagram y Facebook via Meta</p>
                  </div>
                </div>

                <p className="text-sm text-white/50 mb-4">
                  Conecta tu cuenta de Meta Business Suite para habilitar Instagram Direct y Facebook Messenger como canales de atencion.
                </p>

                <button
                  onClick={() => setShowMetaWizard(true)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
                >
                  <Link2 size={16} />
                  Configurar conexion Meta
                </button>
              </div>

              {/* All Channel Bindings Summary */}
              <div className="p-5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <h3 className="font-semibold text-white mb-4">Resumen de canales</h3>
                <div className="space-y-3">
                  {['whatsapp', 'instagram', 'facebook'].map(ch => {
                    const binding = getBindingForChannel(ch);
                    const channelConfig: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
                      whatsapp: { icon: <MessageCircle size={16} />, label: 'WhatsApp', color: 'text-green-400' },
                      instagram: { icon: <Instagram size={16} />, label: 'Instagram', color: 'text-purple-400' },
                      facebook: { icon: <Facebook size={16} />, label: 'Facebook', color: 'text-blue-400' },
                    };
                    const cfg = channelConfig[ch]!;

                    return (
                      <div key={ch} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <div className="flex items-center gap-3">
                          <span className={cfg.color}>{cfg.icon}</span>
                          <span className="text-sm text-white/80">{cfg.label}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {binding?.connected ? (
                            <>
                              <div className="w-2 h-2 rounded-full bg-green-400" />
                              <span className="text-xs text-green-400">Activo</span>
                            </>
                          ) : (
                            <>
                              <div className="w-2 h-2 rounded-full bg-white/20" />
                              <span className="text-xs text-white/30">Inactivo</span>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Meta Connection Wizard Modal */}
      <MetaConnectionWizard
        isOpen={showMetaWizard}
        onClose={() => setShowMetaWizard(false)}
        onSuccess={() => {
          setShowMetaWizard(false);
          loadIntegrationData();
        }}
      />
    </div>
  );
}
