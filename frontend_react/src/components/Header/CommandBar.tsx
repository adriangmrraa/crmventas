/**
 * 🔍 CommandBar.tsx
 * Búsqueda omnipresente central con Cmd+K / Ctrl+K shortcuts
 *
 * CARACTERÍSTICAS:
 * - Input central flexible con icono de búsqueda (left)
 * - Shortcut display ("⌘K" mac / "Ctrl+K" windows) en right, dimmed
 * - Keyboard listener: Cmd+K (Mac) / Ctrl+K (Windows) → auto focus
 * - Debounce: 300ms en onChange
 * - Placeholder i18n-ready: "header.search_placeholder"
 * - Mobile (sm): Colapsa a icono de lupa
 * - Loading state: Spinner durante búsqueda
 *
 * ANIMACIONES:
 * - Input focus: Transition suave 200ms
 * - Loading spinner: CSS animation infinita
 *
 * INTEGRACIÓN FUTURA:
 * - onSearch(query): callback con debounce 300ms
 * - onCommandKey(): callback cuando se presiona Cmd+K / Ctrl+K
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { useTranslation } from '../../context/LanguageContext';
import type { CommandBarProps } from './types';

export const CommandBar: React.FC<CommandBarProps> = ({
  placeholder,
  onSearch,
  onCommandKey,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const inputRef = useRef<HTMLInputElement>(null);

  const displayPlaceholder = placeholder || t('header.search_placeholder', 'Buscar leads, clientes...');

  /**
   * Detectar Cmd+K (Mac) / Ctrl+K (Windows/Linux) y hacer focus al input
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Detectar platform
      const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform);
      const isCommandKey = isMac ? e.metaKey : e.ctrlKey;

      // Escuchar Cmd+K / Ctrl+K
      if (isCommandKey && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onCommandKey?.();
        // Auto-focus al input
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onCommandKey]);

  /**
   * Manejar cambio de búsqueda con debounce 300ms
   */
  const handleSearchChange = useCallback(
    (value: string) => {
      setQuery(value);

      // Limpiar timer anterior si existe
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Si vacío, buscar inmediatamente y resetear estado
      if (!value.trim()) {
        setIsSearching(false);
        onSearch?.('');
        return;
      }

      // Debounce 300ms para búsquedas
      setIsSearching(true);
      debounceTimerRef.current = setTimeout(() => {
        onSearch?.(value);
        setIsSearching(false);
      }, 300);
    },
    [onSearch]
  );

  /**
   * Limpiar debounce timer al desmontar
   */
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  /**
   * Detectar shortcut display (⌘K para Mac, Ctrl+K para otros)
   */
  const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform);
  const shortcutDisplay = isMac ? '⌘K' : 'Ctrl+K';

  // ============================================
  // RENDER
  // ============================================

  return (
    <div className="flex-1 max-w-2xl mx-auto relative">
      {/* ===== DESKTOP: Full Input visible (hidden on sm) ===== */}
      <div className="hidden sm:block relative">
        <input
          ref={inputRef}
          data-testid="command-bar-input"
          type="text"
          value={query}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder={displayPlaceholder}
          disabled={isLoading}
          className="w-full px-4 py-2 pl-10 pr-16 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder-white/30 focus:placeholder-white/40 transition-all duration-200 focus:bg-white/8 focus:border-medical-500/50 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label={t('header.search_label', 'Search')}
        />

        {/* Search Icon (left) - always visible, not interactive */}
        <Search
          size={18}
          className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40 pointer-events-none"
          aria-hidden="true"
        />

        {/* Shortcut Key Display (right, dimmed) - only visual hint */}
        <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-xs font-medium text-white/20 pointer-events-none bg-white/5 px-2 py-1 rounded border border-white/10 select-none">
          {shortcutDisplay}
        </span>

        {/* Loading Indicator Spinner */}
        {isSearching && (
          <div className="absolute right-12 top-1/2 transform -translate-y-1/2">
            <Loader2
              size={16}
              className="text-medical-500 animate-spin"
              aria-label={t('header.searching', 'Searching')}
            />
          </div>
        )}
      </div>

      {/* ===== MOBILE: Icon button only (visible on sm and below) ===== */}
      <div className="sm:hidden flex items-center justify-center">
        <button
          onClick={() => {
            onCommandKey?.();
            inputRef.current?.focus();
          }}
          disabled={isLoading}
          className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 active:scale-95 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          title={displayPlaceholder}
          aria-label={t('header.open_search', 'Open search')}
        >
          {isLoading ? (
            <Loader2 size={18} className="text-medical-500 animate-spin" />
          ) : (
            <Search size={18} className="text-white/70" />
          )}
        </button>
      </div>

      {/* ===== CSS ANIMATION KEYFRAMES ===== */}
      <style>{`
        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
};

export default CommandBar;
