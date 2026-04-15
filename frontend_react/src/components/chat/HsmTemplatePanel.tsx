import { useState, useEffect, useMemo } from 'react';
import {
  X, Search, Send, ChevronRight, ChevronDown,
  Loader2, CheckCircle2, AlertCircle, FileText
} from 'lucide-react';
import api from '../../api/axios';

// ============================================
// INTERFACES
// ============================================

interface HsmVariable {
  placeholder: string;   // e.g. "{{nombre}}"
  key: string;           // e.g. "nombre"
  value: string;
}

interface HsmTemplate {
  id: string;
  name: string;
  category: string;
  language: string;
  status: string;
  body_text: string;
  variables_count: number;
  sent_count?: number;
  delivered_count?: number;
  read_count?: number;
}

interface LeadContextForHsm {
  leadName?: string;
  phone?: string;
}

interface HsmTemplatePanelProps {
  isOpen: boolean;
  onClose: () => void;
  phoneNumber: string;
  leadContext?: LeadContextForHsm;
  vendorName?: string;
  tenantName?: string;
  onSendSuccess?: () => void;
}

// ============================================
// CATEGORY CONFIG
// ============================================

const CATEGORY_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  prospeccion:              { label: 'Prospeccion',             color: 'text-violet-300',   bg: 'bg-violet-500/10' },
  previo_llamada:           { label: 'Previo a llamada',       color: 'text-purple-300', bg: 'bg-purple-500/10' },
  ventana_24hs:             { label: 'Ventana 24hs',           color: 'text-amber-300',  bg: 'bg-amber-500/10' },
  apertura_conversacion:    { label: 'Apertura conversacion',  color: 'text-green-300',  bg: 'bg-green-500/10' },
  marketing_masivo:         { label: 'Marketing masivo',       color: 'text-pink-300',   bg: 'bg-pink-500/10' },
  MARKETING:                { label: 'Marketing',              color: 'text-pink-300',   bg: 'bg-pink-500/10' },
  UTILITY:                  { label: 'Utilidad',               color: 'text-cyan-300',   bg: 'bg-cyan-500/10' },
  AUTHENTICATION:           { label: 'Autenticacion',          color: 'text-orange-300', bg: 'bg-orange-500/10' },
};

const getCategoryConfig = (cat: string) =>
  CATEGORY_CONFIG[cat] || { label: cat, color: 'text-white/60', bg: 'bg-white/[0.05]' };

// ============================================
// VARIABLE EXTRACTION
// ============================================

/** Extract named variables like {{nombre}} from body text */
function extractVariables(bodyText: string): string[] {
  const matches = bodyText.match(/\{\{(\w+)\}\}/g);
  if (!matches) return [];
  // Deduplicate preserving order
  const seen = new Set<string>();
  const result: string[] = [];
  for (const m of matches) {
    if (!seen.has(m)) {
      seen.add(m);
      result.push(m);
    }
  }
  return result;
}

/** Also handle numbered placeholders like {{1}}, {{2}} */
function extractNumberedVariables(bodyText: string): string[] {
  const matches = bodyText.match(/\{\{\d+\}\}/g);
  if (!matches) return [];
  const seen = new Set<string>();
  const result: string[] = [];
  for (const m of matches) {
    if (!seen.has(m)) {
      seen.add(m);
      result.push(m);
    }
  }
  return result;
}

/** Variable labels for numbered placeholders */
const NUMBERED_VAR_LABELS: Record<string, string> = {
  '{{1}}': 'Variable 1',
  '{{2}}': 'Variable 2',
  '{{3}}': 'Variable 3',
  '{{4}}': 'Variable 4',
  '{{5}}': 'Variable 5',
};

/** Variable labels for named placeholders */
const NAMED_VAR_LABELS: Record<string, string> = {
  '{{nombre}}':   'Nombre del lead',
  '{{servicio}}': 'Servicio',
  '{{fecha}}':    'Fecha',
  '{{hora}}':     'Hora',
  '{{link}}':     'Enlace',
  '{{vendedor}}': 'Nombre del vendedor',
  '{{empresa}}':  'Nombre de la empresa',
};

// ============================================
// COMPONENT
// ============================================

export default function HsmTemplatePanel({
  isOpen,
  onClose,
  phoneNumber,
  leadContext,
  vendorName,
  tenantName,
  onSendSuccess,
}: HsmTemplatePanelProps) {
  const [templates, setTemplates] = useState<HsmTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // ── Fetch templates ──────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;

    const fetchTemplates = async () => {
      setLoading(true);
      try {
        const res = await api.get('/admin/core/crm/hsm-templates');
        if (!cancelled) {
          // Only show approved (or pending for testing) — exclude REJECTED
          const all: HsmTemplate[] = res.data?.data ?? [];
          setTemplates(all.filter(t => t.status !== 'REJECTED'));
        }
      } catch (err) {
        console.error('[HSM] Failed to fetch templates:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchTemplates();
    return () => { cancelled = true; };
  }, [isOpen]);

  // ── Auto-dismiss toast ──────────────────────────────────────────
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(timer);
  }, [toast]);

  // ── Pre-fill variables when expanding a template ────────────────
  const handleExpand = (template: HsmTemplate) => {
    if (expandedId === template.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(template.id);

    // Detect variable style
    const namedVars = extractVariables(template.body_text);
    const numberedVars = extractNumberedVariables(template.body_text);
    const allVars = namedVars.length > 0 ? namedVars : numberedVars;

    const prefilled: Record<string, string> = {};
    for (const v of allVars) {
      const key = v.replace(/[{}]/g, '');
      // Pre-fill known values
      if (key === 'nombre' || key === '1') {
        prefilled[v] = leadContext?.leadName || '';
      } else if (key === 'vendedor' || key === '2') {
        prefilled[v] = vendorName || '';
      } else if (key === 'empresa' || key === '3') {
        prefilled[v] = tenantName || '';
      } else {
        prefilled[v] = '';
      }
    }
    setVariableValues(prefilled);
  };

  // ── Group and filter templates ──────────────────────────────────
  const grouped = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    const filtered = templates.filter(t => {
      if (!q) return true;
      return (
        t.name.toLowerCase().includes(q) ||
        t.category.toLowerCase().includes(q) ||
        t.body_text.toLowerCase().includes(q)
      );
    });

    const groups: Record<string, HsmTemplate[]> = {};
    for (const t of filtered) {
      const cat = t.category || 'otros';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(t);
    }
    return groups;
  }, [templates, searchQuery]);

  // ── Toggle category collapse ────────────────────────────────────
  const toggleCategory = (cat: string) => {
    setCollapsedCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  // ── Send template ──────────────────────────────────────────────
  const handleSend = async (template: HsmTemplate) => {
    if (!phoneNumber) {
      setToast({ type: 'error', message: 'No hay numero de telefono seleccionado.' });
      return;
    }

    // Build ordered variables list
    const namedVars = extractVariables(template.body_text);
    const numberedVars = extractNumberedVariables(template.body_text);
    const allVars = namedVars.length > 0 ? namedVars : numberedVars;
    const orderedValues = allVars.map(v => variableValues[v] || '');

    // Validate all variables filled
    if (orderedValues.some(v => !v.trim())) {
      setToast({ type: 'error', message: 'Completa todas las variables antes de enviar.' });
      return;
    }

    setSending(true);
    try {
      await api.post(`/admin/core/crm/hsm-templates/${template.id}/send`, {
        phone_number: phoneNumber,
        variables: orderedValues,
      });
      setToast({ type: 'success', message: `Plantilla "${template.name}" enviada correctamente.` });
      setExpandedId(null);
      onSendSuccess?.();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Error al enviar la plantilla.';
      setToast({ type: 'error', message: detail });
    } finally {
      setSending(false);
    }
  };

  // ── Render preview with highlighted variables ───────────────────
  const renderPreview = (text: string, maxLen = 120) => {
    const truncated = text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
    // Highlight {{...}} placeholders
    return truncated.replace(
      /\{\{(\w+)\}\}/g,
      '<span class="text-medical-400 font-medium">{{$1}}</span>'
    );
  };

  // ── Render filled preview ───────────────────────────────────────
  const renderFilledPreview = (text: string) => {
    let result = text;
    for (const [placeholder, value] of Object.entries(variableValues)) {
      if (value.trim()) {
        result = result.replaceAll(placeholder, `<span class="text-green-400 font-medium">${value}</span>`);
      } else {
        result = result.replaceAll(
          placeholder,
          `<span class="text-red-400/70 font-medium">${placeholder}</span>`
        );
      }
    }
    return result;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[420px] z-50 flex flex-col bg-[#0a0a0f] border-l border-white/[0.06] shadow-2xl animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <FileText className="text-medical-400" size={20} />
          <h2 className="text-lg font-semibold text-white">Plantillas HSM</h2>
          <span className="text-xs text-white/40">({templates.length})</span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-white/60 hover:text-white transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-white/[0.06]">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={16} />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Buscar plantilla por nombre o categoria..."
            className="w-full pl-9 pr-4 py-2 bg-white/[0.04] border border-white/[0.06] rounded-lg text-white text-sm placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-medical-500/50"
          />
        </div>
      </div>

      {/* Toast notification */}
      {toast && (
        <div className={`mx-3 mt-2 px-4 py-2.5 rounded-lg flex items-center gap-2 text-sm animate-fade-in ${
          toast.type === 'success'
            ? 'bg-green-500/10 border border-green-500/20 text-green-400'
            : 'bg-red-500/10 border border-red-500/20 text-red-400'
        }`}>
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Template list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12 text-white/40">
            <Loader2 className="animate-spin mr-2" size={20} />
            <span>Cargando plantillas...</span>
          </div>
        ) : Object.keys(grouped).length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-white/40">
            <FileText size={32} className="mb-2 opacity-40" />
            <span>No se encontraron plantillas</span>
          </div>
        ) : (
          Object.entries(grouped).map(([category, categoryTemplates]) => {
            const catConfig = getCategoryConfig(category);
            const isCollapsed = collapsedCategories.has(category);

            return (
              <div key={category} className="border-b border-white/[0.04]">
                {/* Category header */}
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full flex items-center gap-2 px-4 py-2.5 hover:bg-white/[0.03] transition-colors"
                >
                  {isCollapsed ? (
                    <ChevronRight size={14} className="text-white/40" />
                  ) : (
                    <ChevronDown size={14} className="text-white/40" />
                  )}
                  <span className={`text-xs font-semibold uppercase tracking-wider ${catConfig.color}`}>
                    {catConfig.label}
                  </span>
                  <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${catConfig.bg} ${catConfig.color}`}>
                    {categoryTemplates.length}
                  </span>
                </button>

                {/* Template cards */}
                {!isCollapsed && categoryTemplates.map(tmpl => {
                  const isExpanded = expandedId === tmpl.id;
                  const namedVars = extractVariables(tmpl.body_text);
                  const numberedVars = extractNumberedVariables(tmpl.body_text);
                  const allVars = namedVars.length > 0 ? namedVars : numberedVars;

                  return (
                    <div key={tmpl.id} className="mx-2 mb-1">
                      {/* Card header */}
                      <button
                        onClick={() => handleExpand(tmpl)}
                        className={`w-full text-left px-3 py-2.5 rounded-lg transition-all ${
                          isExpanded
                            ? 'bg-white/[0.06] border border-white/[0.08]'
                            : 'hover:bg-white/[0.04] border border-transparent'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-sm font-medium text-white truncate">
                                {tmpl.name.replace(/_/g, ' ')}
                              </span>
                              {tmpl.status === 'APPROVED' && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20 flex-shrink-0">
                                  Aprobada
                                </span>
                              )}
                              {tmpl.status === 'PENDING_APPROVAL' && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 flex-shrink-0">
                                  Pendiente
                                </span>
                              )}
                            </div>
                            <p
                              className="text-xs text-white/40 line-clamp-2"
                              dangerouslySetInnerHTML={{ __html: renderPreview(tmpl.body_text) }}
                            />
                          </div>
                          <ChevronRight
                            size={14}
                            className={`text-white/30 mt-1 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                          />
                        </div>
                      </button>

                      {/* Expanded: variable inputs + send */}
                      {isExpanded && (
                        <div className="px-3 pb-3 pt-1 space-y-3 animate-fade-in">
                          {/* Full preview */}
                          <div className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                            <p className="text-xs text-white/50 mb-1 font-medium">Vista previa:</p>
                            <p
                              className="text-sm text-white/80 leading-relaxed"
                              dangerouslySetInnerHTML={{ __html: renderFilledPreview(tmpl.body_text) }}
                            />
                          </div>

                          {/* Variable inputs */}
                          {allVars.length > 0 && (
                            <div className="space-y-2">
                              <p className="text-xs text-white/50 font-medium">Variables:</p>
                              {allVars.map(v => {
                                const key = v.replace(/[{}]/g, '');
                                const label = NAMED_VAR_LABELS[v] || NUMBERED_VAR_LABELS[v] || key;
                                return (
                                  <div key={v} className="flex items-center gap-2">
                                    <span className="text-xs text-medical-400 font-mono w-24 flex-shrink-0 truncate">
                                      {v}
                                    </span>
                                    <input
                                      type="text"
                                      value={variableValues[v] || ''}
                                      onChange={e => setVariableValues(prev => ({ ...prev, [v]: e.target.value }))}
                                      placeholder={label}
                                      className="flex-1 px-3 py-1.5 bg-white/[0.04] border border-white/[0.08] rounded text-sm text-white placeholder:text-white/25 focus:outline-none focus:ring-1 focus:ring-medical-500/50"
                                    />
                                  </div>
                                );
                              })}
                            </div>
                          )}

                          {/* Send button */}
                          <button
                            onClick={() => handleSend(tmpl)}
                            disabled={sending}
                            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-medical-600 hover:bg-medical-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
                          >
                            {sending ? (
                              <>
                                <Loader2 className="animate-spin" size={16} />
                                Enviando...
                              </>
                            ) : (
                              <>
                                <Send size={16} />
                                Enviar plantilla
                              </>
                            )}
                          </button>

                          {/* Stats */}
                          {(tmpl.sent_count ?? 0) > 0 && (
                            <div className="flex items-center gap-3 text-[10px] text-white/30">
                              <span>Enviadas: {tmpl.sent_count}</span>
                              {(tmpl.delivered_count ?? 0) > 0 && <span>Entregadas: {tmpl.delivered_count}</span>}
                              {(tmpl.read_count ?? 0) > 0 && <span>Leidas: {tmpl.read_count}</span>}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })
        )}
      </div>

      {/* Footer info */}
      <div className="p-3 border-t border-white/[0.06] text-xs text-white/30 text-center">
        Enviando a: <span className="text-white/50 font-mono">{phoneNumber || '---'}</span>
      </div>
    </div>
  );
}
