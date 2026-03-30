import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, MessageSquare, StickyNote, ArrowRight, Search as SearchIcon } from 'lucide-react';
import api from '../../api/axios';
import { CommandBar } from './CommandBar';
import { useTranslation } from '../../context/LanguageContext';

interface SearchResults {
  leads: any[];
  notes: any[];
  messages: any[];
}

export const GlobalSearch: React.FC = () => {
  const [results, setResults] = useState<SearchResults | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleSearch = useCallback(async (query: string) => {
    if (!query || query.length < 2) {
      setResults(null);
      setIsOpen(false);
      return;
    }

    setIsLoading(true);
    setIsOpen(true);
    try {
      const { data } = await api.get('/admin/core/search', { params: { query } });
      setResults(data);
    } catch (err) {
      console.error('Global search error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const navigateToLead = (leadId: string) => {
    setIsOpen(false);
    navigate(`/leads/${leadId}`);
  };

  const hasResults = results && (results.leads.length > 0 || results.notes.length > 0 || results.messages.length > 0);

  return (
    <div className="flex-1 max-w-2xl mx-auto relative" ref={dropdownRef}>
      <CommandBar 
        onSearch={handleSearch} 
        isLoading={isLoading}
        onCommandKey={() => setIsOpen(true)}
      />

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-[#0d1117] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden backdrop-blur-xl animate-scaleIn origin-top">
          {!isLoading && !hasResults && (
            <div className="p-8 text-center">
              <SearchIcon size={32} className="mx-auto text-white/10 mb-2" />
              <p className="text-white/40 text-sm">{t('search.no_results')}</p>
            </div>
          )}

          {hasResults && (
            <div className="max-h-[70vh] overflow-y-auto p-2 space-y-4">
              {/* LEADS */}
              {results.leads.length > 0 && (
                <div>
                  <h3 className="px-3 py-1 text-[10px] font-bold text-white/30 uppercase tracking-wider">Leads</h3>
                  <div className="space-y-1 mt-1">
                    {results.leads.map(lead => (
                      <button
                        key={lead.id}
                        onClick={() => navigateToLead(lead.id)}
                        className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors text-left group"
                      >
                        <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0">
                          <User size={14} className="text-blue-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-white truncate">{lead.first_name} {lead.last_name}</p>
                          <p className="text-xs text-white/40 truncate">{lead.email || lead.phone_number}</p>
                        </div>
                        <ArrowRight size={14} className="text-white/0 group-hover:text-white/20 transition-all -translate-x-2 group-hover:translate-x-0" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* NOTES */}
              {results.notes.length > 0 && (
                <div>
                  <h3 className="px-3 py-1 text-[10px] font-bold text-white/30 uppercase tracking-wider">Notas</h3>
                  <div className="space-y-1 mt-1">
                    {results.notes.map(note => (
                      <button
                        key={note.id}
                        onClick={() => navigateToLead(note.lead_id)}
                        className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors text-left group"
                      >
                        <div className="w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center shrink-0">
                          <StickyNote size={14} className="text-yellow-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-white/60 line-clamp-1">{note.content}</p>
                          <p className="text-[10px] text-white/30">{note.first_name} {note.last_name}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* MESSAGES */}
              {results.messages.length > 0 && (
                <div>
                  <h3 className="px-3 py-1 text-[10px] font-bold text-white/30 uppercase tracking-wider">Mensajes</h3>
                  <div className="space-y-1 mt-1">
                    {results.messages.map(msg => (
                      <button
                        key={msg.id}
                        onClick={() => msg.phone_number && navigate(`/chats?phone=${msg.phone_number}`)}
                        className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors text-left group"
                      >
                        <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center shrink-0">
                          <MessageSquare size={14} className="text-green-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-white/60 line-clamp-1">{msg.content}</p>
                          <p className="text-[10px] text-white/30">{msg.first_name || msg.from_number}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
