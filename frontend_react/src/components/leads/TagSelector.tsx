import React, { useState, useEffect, useRef } from 'react';
import { Tag, Search, Plus, Check, ChevronDown, Loader2 } from 'lucide-react';
import { apiGet, apiPost, apiDelete } from '../../api/axios';
import { TagBadge, type LeadTag } from './TagBadge';

const CRM_TAGS_BASE = '/admin/core/crm/lead-tags';
const CRM_LEADS_BASE = '/admin/core/crm/leads';

const PRESET_COLORS = [
  '#8F3DFF', // blue
  '#10B981', // emerald
  '#F59E0B', // amber
  '#EF4444', // red
  '#8B5CF6', // violet
  '#EC4899', // pink
  '#06B6D4', // cyan
  '#F97316', // orange
  '#84CC16', // lime
  '#6366F1', // indigo
];

interface TagSelectorProps {
  leadId: string;
  currentTags: string[];
  onTagsChange: (tags: string[]) => void;
}

export const TagSelector: React.FC<TagSelectorProps> = ({
  leadId,
  currentTags,
  onTagsChange,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [availableTags, setAvailableTags] = useState<LeadTag[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [newTagColor, setNewTagColor] = useState(PRESET_COLORS[0]);
  const [saving, setSaving] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setShowCreateForm(false);
        setSearchTerm('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Fetch available tags when opened
  useEffect(() => {
    if (isOpen) {
      fetchTags();
      setTimeout(() => searchRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const fetchTags = async () => {
    try {
      setLoading(true);
      const data = await apiGet<LeadTag[]>(CRM_TAGS_BASE);
      setAvailableTags(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('[TagSelector] Failed to fetch tags:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = async (tagName: string) => {
    if (currentTags.includes(tagName)) return;
    try {
      setSaving(true);
      await apiPost(`${CRM_LEADS_BASE}/${leadId}/tags`, { tag_name: tagName });
      onTagsChange([...currentTags, tagName]);
    } catch (err) {
      console.error('[TagSelector] Failed to add tag:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveTag = async (tagName: string) => {
    try {
      setSaving(true);
      await apiDelete(`${CRM_LEADS_BASE}/${leadId}/tags/${encodeURIComponent(tagName)}`);
      onTagsChange(currentTags.filter((t) => t !== tagName));
    } catch (err) {
      console.error('[TagSelector] Failed to remove tag:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateTag = async () => {
    const trimmed = newTagName.trim();
    if (!trimmed) return;
    try {
      setSaving(true);
      await apiPost<LeadTag>(CRM_TAGS_BASE, { name: trimmed, color: newTagColor });
      // Add to available list and assign to lead
      setAvailableTags((prev) => [...prev, { name: trimmed, color: newTagColor }]);
      await handleAddTag(trimmed);
      setNewTagName('');
      setNewTagColor(PRESET_COLORS[0]);
      setShowCreateForm(false);
    } catch (err) {
      console.error('[TagSelector] Failed to create tag:', err);
    } finally {
      setSaving(false);
    }
  };

  const filteredTags = availableTags.filter((tag) =>
    tag.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getTagDef = (tagName: string): LeadTag => {
    return availableTags.find((t) => t.name === tagName) || { name: tagName, color: '#6B7280' };
  };

  return (
    <div ref={containerRef} className="relative">
      {/* Current tags + trigger */}
      <div className="flex flex-wrap items-center gap-1.5">
        {currentTags.map((tagName) => (
          <TagBadge
            key={tagName}
            tag={getTagDef(tagName)}
            onRemove={() => handleRemoveTag(tagName)}
          />
        ))}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-white/40 hover:text-white/60 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] hover:border-white/[0.1] rounded-full transition-colors"
        >
          <Tag className="w-3 h-3" />
          <span>{currentTags.length === 0 ? 'Añadir etiqueta' : ''}</span>
          <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Dropdown popover */}
      {isOpen && (
        <div className="absolute z-50 mt-2 left-0 w-64 bg-[#1a1a2e] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/40 overflow-hidden">
          {/* Search */}
          <div className="p-2 border-b border-white/[0.06]">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/30" />
              <input
                ref={searchRef}
                type="text"
                placeholder="Buscar etiquetas..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-white/[0.04] border border-white/[0.06] rounded-lg outline-none focus:ring-1 focus:ring-medical-500 text-white placeholder:text-white/30"
              />
            </div>
          </div>

          {/* Tag list */}
          <div className="max-h-48 overflow-y-auto p-1">
            {loading ? (
              <div className="flex items-center justify-center py-4 text-white/40">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
            ) : filteredTags.length === 0 && searchTerm ? (
              <div className="px-3 py-3 text-xs text-white/30 text-center">
                No se encontraron etiquetas
              </div>
            ) : (
              filteredTags.map((tag) => {
                const isActive = currentTags.includes(tag.name);
                return (
                  <button
                    key={tag.name}
                    type="button"
                    disabled={saving}
                    onClick={() => (isActive ? handleRemoveTag(tag.name) : handleAddTag(tag.name))}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs rounded-lg transition-colors ${
                      isActive
                        ? 'bg-white/[0.06] text-white'
                        : 'text-white/60 hover:bg-white/[0.04] hover:text-white'
                    }`}
                  >
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: tag.color }}
                    />
                    <span className="flex-1 text-left truncate">{tag.name}</span>
                    {isActive && <Check className="w-3.5 h-3.5 text-medical-500 shrink-0" />}
                  </button>
                );
              })
            )}
          </div>

          {/* Create new tag */}
          <div className="border-t border-white/[0.06]">
            {showCreateForm ? (
              <div className="p-3 space-y-2">
                <input
                  type="text"
                  placeholder="Nombre de la etiqueta"
                  value={newTagName}
                  onChange={(e) => setNewTagName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleCreateTag();
                    }
                  }}
                  className="w-full px-3 py-1.5 text-xs bg-white/[0.04] border border-white/[0.06] rounded-lg outline-none focus:ring-1 focus:ring-medical-500 text-white placeholder:text-white/30"
                  autoFocus
                />
                <div className="flex flex-wrap gap-1.5">
                  {PRESET_COLORS.map((color) => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => setNewTagColor(color)}
                      className={`w-5 h-5 rounded-full border-2 transition-all ${
                        newTagColor === color
                          ? 'border-white scale-110'
                          : 'border-transparent hover:border-white/30'
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
                <div className="flex gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateForm(false);
                      setNewTagName('');
                    }}
                    className="flex-1 py-1.5 text-xs text-white/40 hover:text-white/60 bg-white/[0.03] border border-white/[0.06] rounded-lg transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={handleCreateTag}
                    disabled={!newTagName.trim() || saving}
                    className="flex-1 py-1.5 text-xs text-white bg-medical-600 hover:bg-medical-700 rounded-lg transition-colors disabled:opacity-50 font-medium"
                  >
                    {saving ? 'Creando...' : 'Crear'}
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowCreateForm(true)}
                className="w-full flex items-center gap-2 px-3 py-2.5 text-xs text-white/40 hover:text-white/60 hover:bg-white/[0.03] transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Crear nueva etiqueta
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
