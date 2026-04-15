import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Facebook,
  Instagram,
  MessageCircle,
  Plug,
  Unplug,
  RefreshCw,
  Save,
  AlertTriangle,
  Phone,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import api, { BACKEND_URL } from '../../api/axios';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Asset {
  id: number;
  platform: string;
  asset_type: string;
  asset_id: string;
  asset_name: string;
  parent_asset_id: string | null;
  metadata: Record<string, any>;
}

interface Binding {
  id: number;
  channel: string;
  asset_id: string;
  asset_name: string;
  active: boolean;
}

interface StatusData {
  connected: boolean;
  token_valid?: boolean;
  token_expires_at?: number;
  token_scopes?: string[];
  channels: { facebook: boolean; instagram: boolean; whatsapp: boolean };
  assets: Asset[];
  bindings: Binding[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const META_APP_ID = import.meta.env.VITE_META_APP_ID || '';

const SCOPES = [
  'pages_show_list',
  'pages_manage_metadata',
  'pages_messaging',
  'instagram_basic',
  'instagram_manage_messages',
  'business_management',
  'whatsapp_business_management',
  'whatsapp_business_messaging',
].join(',');

function channelIcon(ch: string, size = 18) {
  switch (ch) {
    case 'facebook':
      return <Facebook size={size} />;
    case 'instagram':
      return <Instagram size={size} />;
    case 'whatsapp':
      return <MessageCircle size={size} />;
    default:
      return <Plug size={size} />;
  }
}

function channelLabel(ch: string) {
  switch (ch) {
    case 'facebook':
      return 'Facebook Pages';
    case 'instagram':
      return 'Instagram';
    case 'whatsapp':
      return 'WhatsApp';
    default:
      return ch;
  }
}

function channelColor(ch: string) {
  switch (ch) {
    case 'facebook':
      return 'text-violet-400 bg-violet-500/10 border-violet-500/20';
    case 'instagram':
      return 'text-pink-400 bg-pink-500/10 border-pink-500/20';
    case 'whatsapp':
      return 'text-green-400 bg-green-500/10 border-green-500/20';
    default:
      return 'text-white/40 bg-white/5 border-white/10';
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function MetaConnectionPanel() {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Selected asset IDs for channel binding
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set());
  const [showAssets, setShowAssets] = useState(false);

  // ------- Fetch status -------
  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get('/admin/meta/status');
      const d: StatusData = data.data;
      setStatus(d);
      // Pre-select currently bound asset IDs
      const bound = new Set(d.bindings.filter((b) => b.active).map((b) => b.asset_id));
      setSelectedAssets(bound);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error loading Meta connection status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // ------- Facebook Login (Embedded Signup) -------
  const handleConnect = () => {
    setError(null);
    setSuccess(null);

    // Load Facebook SDK if not loaded
    if (!(window as any).FB) {
      loadFbSdk(() => triggerLogin());
    } else {
      triggerLogin();
    }
  };

  const loadFbSdk = (cb: () => void) => {
    (window as any).fbAsyncInit = function () {
      (window as any).FB.init({
        appId: META_APP_ID,
        cookie: true,
        xfbml: false,
        version: 'v19.0',
      });
      cb();
    };
    const script = document.createElement('script');
    script.src = 'https://connect.facebook.net/en_US/sdk.js';
    script.async = true;
    script.defer = true;
    document.body.appendChild(script);
  };

  const triggerLogin = () => {
    setConnecting(true);
    (window as any).FB.login(
      async (response: any) => {
        if (response.authResponse) {
          const code = response.authResponse.code;
          if (code) {
            await exchangeCode(code);
          } else {
            // If we got an access token instead of code, still try with access_token
            // This happens when response_type is not 'code'
            setError('Facebook returned a token instead of a code. Please try again.');
            setConnecting(false);
          }
        } else {
          setError('Facebook login was cancelled or failed.');
          setConnecting(false);
        }
      },
      {
        scope: SCOPES,
        response_type: 'code',
        override_default_response_type: true,
      },
    );
  };

  const exchangeCode = async (code: string) => {
    try {
      const { data } = await api.post('/admin/meta/connect', { code });
      setSuccess('Meta account connected successfully! Select which channels to activate below.');
      setShowAssets(true);
      await fetchStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error connecting Meta account');
    } finally {
      setConnecting(false);
    }
  };

  // ------- Disconnect -------
  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect Meta? All tokens, assets, and channel bindings will be removed.')) {
      return;
    }
    setDisconnecting(true);
    setError(null);
    setSuccess(null);
    try {
      await api.delete('/admin/meta/disconnect');
      setSuccess('Meta account disconnected.');
      setSelectedAssets(new Set());
      await fetchStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error disconnecting');
    } finally {
      setDisconnecting(false);
    }
  };

  // ------- Select channels -------
  const toggleAsset = (assetId: string) => {
    setSelectedAssets((prev) => {
      const next = new Set(prev);
      if (next.has(assetId)) {
        next.delete(assetId);
      } else {
        next.add(assetId);
      }
      return next;
    });
  };

  const handleSaveChannels = async () => {
    if (selectedAssets.size === 0) {
      setError('Select at least one asset to activate.');
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const { data } = await api.post('/admin/meta/select-channels', {
        asset_ids: Array.from(selectedAssets),
      });
      setSuccess(data.data?.message || 'Channels activated.');
      await fetchStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error activating channels');
    } finally {
      setSaving(false);
    }
  };

  // ------- Render -------
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
      </div>
    );
  }

  const connected = status?.connected ?? false;
  const tokenValid = status?.token_valid ?? false;

  // Separate assets by platform
  const pageAssets = (status?.assets || []).filter((a) => a.platform === 'facebook' && a.asset_type === 'page');
  const igAssets = (status?.assets || []).filter((a) => a.platform === 'instagram');
  const wabaAssets = (status?.assets || []).filter((a) => a.platform === 'whatsapp' && a.asset_type === 'waba');
  const phoneAssets = (status?.assets || []).filter((a) => a.platform === 'whatsapp' && a.asset_type === 'phone_number');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Meta Channels</h2>
          <p className="text-sm text-white/40 mt-1">
            Connect Facebook Pages, Instagram, and WhatsApp to your CRM.
          </p>
        </div>
        <button
          onClick={fetchStatus}
          disabled={loading}
          className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-white/40 hover:text-white transition-all"
          title="Refresh"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-sm font-medium flex items-start gap-3">
          <AlertTriangle size={18} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-2xl text-green-400 text-sm font-medium flex items-start gap-3">
          <CheckCircle2 size={18} className="shrink-0 mt-0.5" />
          <span>{success}</span>
        </div>
      )}

      {/* Connection status badges */}
      <div className="grid grid-cols-3 gap-3">
        {(['facebook', 'instagram', 'whatsapp'] as const).map((ch) => {
          const active = status?.channels[ch] ?? false;
          const color = channelColor(ch);
          return (
            <div
              key={ch}
              className={`p-4 rounded-2xl border ${color} flex flex-col items-center gap-2 transition-all`}
            >
              <div className="opacity-80">{channelIcon(ch, 24)}</div>
              <span className="text-xs font-bold uppercase tracking-wider">{channelLabel(ch)}</span>
              {active ? (
                <span className="text-[10px] font-bold bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
                  ACTIVE
                </span>
              ) : connected ? (
                <span className="text-[10px] font-bold bg-white/10 text-white/30 px-2 py-0.5 rounded-full">
                  NOT SELECTED
                </span>
              ) : (
                <span className="text-[10px] font-bold bg-white/10 text-white/30 px-2 py-0.5 rounded-full">
                  DISCONNECTED
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Token status */}
      {connected && (
        <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-3">
            {tokenValid ? (
              <CheckCircle2 className="text-green-400" size={18} />
            ) : (
              <XCircle className="text-red-400" size={18} />
            )}
            <div>
              <span className="text-sm font-bold text-white">
                {tokenValid ? 'Token valid' : 'Token expired or invalid'}
              </span>
              {status?.token_expires_at && (
                <p className="text-xs text-white/30">
                  Expires: {new Date(status.token_expires_at * 1000).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>
          {!tokenValid && (
            <button
              onClick={handleConnect}
              disabled={connecting}
              className="text-xs font-bold text-violet-400 hover:text-violet-300 transition-all"
            >
              Re-authenticate
            </button>
          )}
        </div>
      )}

      {/* Connect / Disconnect button */}
      {!connected ? (
        <button
          onClick={handleConnect}
          disabled={connecting}
          className="w-full py-4 bg-violet-600 hover:bg-violet-700 text-white rounded-2xl font-bold transition-all flex items-center justify-center gap-3 disabled:opacity-50"
        >
          {connecting ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Facebook size={18} />
          )}
          {connecting ? 'Connecting...' : 'Connect with Facebook'}
        </button>
      ) : (
        <div className="flex gap-3">
          <button
            onClick={() => setShowAssets(!showAssets)}
            className="flex-1 py-3 bg-white/[0.04] hover:bg-white/[0.08] text-white rounded-2xl font-bold transition-all flex items-center justify-center gap-2 text-sm"
          >
            {showAssets ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            {showAssets ? 'Hide Assets' : 'Manage Channels'}
          </button>
          <button
            onClick={handleDisconnect}
            disabled={disconnecting}
            className="px-6 py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-2xl font-bold transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-50"
          >
            {disconnecting ? <Loader2 size={16} className="animate-spin" /> : <Unplug size={16} />}
            Disconnect
          </button>
        </div>
      )}

      {/* Asset selection panel */}
      {connected && showAssets && (
        <div className="space-y-4 p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
          <p className="text-sm font-bold text-white/60 uppercase tracking-wider">
            Select channels to activate
          </p>

          {/* Facebook Pages */}
          {pageAssets.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-bold text-violet-400 flex items-center gap-2">
                <Facebook size={14} /> Facebook Pages
              </p>
              {pageAssets.map((a) => (
                <AssetCheckbox
                  key={a.asset_id}
                  asset={a}
                  checked={selectedAssets.has(a.asset_id)}
                  onToggle={() => toggleAsset(a.asset_id)}
                />
              ))}
            </div>
          )}

          {/* Instagram */}
          {igAssets.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-bold text-pink-400 flex items-center gap-2">
                <Instagram size={14} /> Instagram Accounts
              </p>
              {igAssets.map((a) => (
                <AssetCheckbox
                  key={a.asset_id}
                  asset={a}
                  checked={selectedAssets.has(a.asset_id)}
                  onToggle={() => toggleAsset(a.asset_id)}
                />
              ))}
            </div>
          )}

          {/* WhatsApp */}
          {(wabaAssets.length > 0 || phoneAssets.length > 0) && (
            <div className="space-y-2">
              <p className="text-xs font-bold text-green-400 flex items-center gap-2">
                <MessageCircle size={14} /> WhatsApp
              </p>
              {wabaAssets.map((a) => (
                <AssetCheckbox
                  key={a.asset_id}
                  asset={a}
                  checked={selectedAssets.has(a.asset_id)}
                  onToggle={() => toggleAsset(a.asset_id)}
                  subtitle={`WABA ID: ${a.asset_id}`}
                />
              ))}
              {phoneAssets.map((a) => (
                <AssetCheckbox
                  key={a.asset_id}
                  asset={a}
                  checked={selectedAssets.has(a.asset_id)}
                  onToggle={() => toggleAsset(a.asset_id)}
                  icon={<Phone size={14} />}
                  subtitle={a.metadata?.verified_name || a.asset_id}
                />
              ))}
            </div>
          )}

          {(status?.assets || []).length === 0 && (
            <p className="text-sm text-white/30 text-center py-6">
              No assets discovered. Try reconnecting your Meta account.
            </p>
          )}

          {/* Save button */}
          {(status?.assets || []).length > 0 && (
            <button
              onClick={handleSaveChannels}
              disabled={saving || selectedAssets.size === 0}
              className="w-full py-3.5 bg-green-600 hover:bg-green-700 text-white rounded-2xl font-bold transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-40"
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {saving ? 'Saving...' : `Activate ${selectedAssets.size} Channel(s)`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: Asset checkbox row
// ---------------------------------------------------------------------------

function AssetCheckbox({
  asset,
  checked,
  onToggle,
  icon,
  subtitle,
}: {
  asset: Asset;
  checked: boolean;
  onToggle: () => void;
  icon?: React.ReactNode;
  subtitle?: string;
}) {
  return (
    <button
      onClick={onToggle}
      className={`w-full p-3 rounded-xl text-left flex items-center gap-3 transition-all ${
        checked
          ? 'bg-violet-500/10 border border-violet-500/30'
          : 'bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.12]'
      }`}
    >
      <div
        className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-all ${
          checked ? 'bg-violet-500 border-violet-500' : 'border-white/20'
        }`}
      >
        {checked && <CheckCircle2 size={12} className="text-white" />}
      </div>
      {icon && <span className="text-white/40">{icon}</span>}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-white truncate">{asset.asset_name || asset.asset_id}</p>
        {subtitle && <p className="text-[11px] text-white/30 truncate">{subtitle}</p>}
      </div>
      <span className="text-[10px] font-bold uppercase tracking-wider text-white/20 shrink-0">
        {asset.asset_type.replace('_', ' ')}
      </span>
    </button>
  );
}
