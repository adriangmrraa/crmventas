/**
 * StatusAlertsCluster.tsx
 * Help dropdown (?) + Notification bell with dropdown + Status indicators
 *
 * Changes (v1.1):
 * - Help icon now opens a support dropdown (email + docs link)
 * - Bell icon replaced with NotificationBell component (real data, dropdown slides DOWN)
 * - Status dot remains unchanged
 */

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from '../../context/LanguageContext';
import {
  HelpCircle,
  Wifi,
  WifiOff,
  AlertCircle,
  MoreVertical,
  Mail,
  BookOpen,
  MessageCircle,
  ExternalLink,
} from 'lucide-react';
import type { StatusAlertsClusterProps } from './types';
import NotificationBell from '../NotificationBell';

export const StatusAlertsCluster: React.FC<StatusAlertsClusterProps> = ({
  hasNewGuide = false,
  notificationCount = 0,
  onHelpClick,
  onNotificationClick,
  isOnline = true,
  connectionStatus = 'online',
}) => {
  const { t } = useTranslation();
  const [showTooltip, setShowTooltip] = useState<string | null>(null);
  const [showHelpDropdown, setShowHelpDropdown] = useState(false);
  const helpDropdownRef = useRef<HTMLDivElement>(null);

  // Close help dropdown on outside click
  useEffect(() => {
    if (!showHelpDropdown) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (helpDropdownRef.current && !helpDropdownRef.current.contains(e.target as Node)) {
        setShowHelpDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showHelpDropdown]);

  // Connection status helpers
  const getStatusColor = () => {
    if (connectionStatus === 'online' || isOnline) return '#28a745';
    if (connectionStatus === 'unstable') return '#ffc107';
    return '#dc3545';
  };

  const getStatusIcon = () => {
    if (connectionStatus === 'unstable') return <AlertCircle size={16} />;
    if (connectionStatus === 'online' || isOnline) return <Wifi size={16} />;
    return <WifiOff size={16} />;
  };

  const getStatusLabel = () => {
    if (connectionStatus === 'online' || isOnline) return t('header.status_online') || 'Online';
    if (connectionStatus === 'unstable') return t('header.status_unstable') || 'Unstable';
    return t('header.offline') || 'Offline';
  };

  const handleHelpClick = () => {
    if (onHelpClick) {
      onHelpClick();
    } else {
      setShowHelpDropdown(!showHelpDropdown);
    }
  };

  return (
    <div className="flex items-center gap-2 sm:gap-4">
      {/* ─── Help Icon with Dropdown ─── */}
      <div className="relative" ref={helpDropdownRef}>
        <button
          onClick={handleHelpClick}
          onMouseEnter={() => setShowTooltip('help')}
          onMouseLeave={() => setShowTooltip(null)}
          className={`flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200 ${
            hasNewGuide ? 'animate-pulse' : ''
          }`}
          title={t('header.help_tooltip')}
          aria-label="Help"
        >
          <HelpCircle
            size={18}
            className={`text-white/70 ${hasNewGuide ? 'text-medical-400' : ''}`}
            style={
              hasNewGuide
                ? { animation: 'pulseSoft 2s ease-in-out infinite' }
                : undefined
            }
          />
        </button>

        {/* Help Dropdown */}
        {showHelpDropdown && (
          <div
            className="absolute top-full right-0 mt-2 w-64 bg-[#0d1117] rounded-xl shadow-2xl shadow-black/40 border border-white/[0.08] z-50 overflow-hidden"
            style={{
              animation: 'helpDropdownIn 0.2s ease-out forwards',
            }}
          >
            <div className="px-4 py-3 border-b border-white/[0.06]">
              <p className="text-sm font-semibold text-white/90">
                {t('header.help_title') || 'Ayuda y Soporte'}
              </p>
              <p className="text-xs text-white/40 mt-0.5">
                {t('header.help_subtitle') || 'Estamos para ayudarte'}
              </p>
            </div>

            <div className="p-2">
              {/* Support email */}
              <a
                href="mailto:soporte@codexy.com"
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.06] transition-colors group"
                onClick={() => setShowHelpDropdown(false)}
              >
                <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center flex-shrink-0">
                  <Mail size={16} className="text-violet-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white/80 font-medium">Soporte</p>
                  <p className="text-xs text-white/40 truncate">soporte@codexy.com</p>
                </div>
                <ExternalLink size={14} className="text-white/20 group-hover:text-white/40 flex-shrink-0" />
              </a>

              {/* Documentation */}
              <a
                href="https://docs.codexy.com"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.06] transition-colors group"
                onClick={() => setShowHelpDropdown(false)}
              >
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                  <BookOpen size={16} className="text-emerald-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white/80 font-medium">
                    {t('header.help_docs') || 'Documentacion'}
                  </p>
                  <p className="text-xs text-white/40">
                    {t('header.help_docs_desc') || 'Guias y tutoriales'}
                  </p>
                </div>
                <ExternalLink size={14} className="text-white/20 group-hover:text-white/40 flex-shrink-0" />
              </a>

              {/* WhatsApp support */}
              <a
                href="https://wa.me/+5491100000000"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.06] transition-colors group"
                onClick={() => setShowHelpDropdown(false)}
              >
                <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center flex-shrink-0">
                  <MessageCircle size={16} className="text-green-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white/80 font-medium">WhatsApp</p>
                  <p className="text-xs text-white/40">
                    {t('header.help_whatsapp_desc') || 'Chat en vivo'}
                  </p>
                </div>
                <ExternalLink size={14} className="text-white/20 group-hover:text-white/40 flex-shrink-0" />
              </a>
            </div>

            <div className="px-4 py-2.5 border-t border-white/[0.06] bg-white/[0.02]">
              <p className="text-[10px] text-white/30 text-center">
                v1.0 &middot; CRM Ventas by Codexy
              </p>
            </div>
          </div>
        )}

        {/* Tooltip (only when dropdown is closed) */}
        {showTooltip === 'help' && !showHelpDropdown && (
          <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-slate-900 text-white text-xs rounded-lg border border-white/10 whitespace-nowrap shadow-lg pointer-events-none">
            {t('header.help_tooltip') || 'Ayuda'}
            <div className="absolute top-full right-2 w-2 h-2 bg-slate-900 border-r border-b border-white/10 transform rotate-45" />
          </div>
        )}
      </div>

      {/* ─── Notification Bell (uses NotificationBell component with real data) ─── */}
      <NotificationBell
        useSocket={true}
        fallbackToApi={true}
        autoRefresh={true}
        refreshInterval={30000}
      />

      {/* ─── Status Dot with Connection Info ─── */}
      <div className="relative group hidden sm:block">
        <button
          onMouseEnter={() => setShowTooltip('status')}
          onMouseLeave={() => setShowTooltip(null)}
          className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-200"
          title={getStatusLabel()}
          aria-label={`Status: ${getStatusLabel()}`}
        >
          <div className="text-white/70">{getStatusIcon()}</div>
        </button>

        {/* Status Dot Indicator */}
        <div
          className={`absolute top-1 right-1 w-3 h-3 rounded-full border-2 border-slate-900 ${
            connectionStatus === 'unstable' ? 'animate-pulse' : ''
          }`}
          style={{ backgroundColor: getStatusColor() }}
        />

        {/* Tooltip */}
        {showTooltip === 'status' && (
          <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-slate-900 text-white text-xs rounded-lg border border-white/10 whitespace-nowrap shadow-lg pointer-events-none">
            {getStatusLabel()}
            <div className="absolute top-full right-2 w-2 h-2 bg-slate-900 border-r border-b border-white/10 transform rotate-45" />
          </div>
        )}
      </div>

      {/* Animations */}
      <style>{`
        @keyframes pulseSoft {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes helpDropdownIn {
          from {
            opacity: 0;
            transform: translateY(-8px) scale(0.96);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>
    </div>
  );
};

export default StatusAlertsCluster;
