import React from 'react';
import { X } from 'lucide-react';

export interface LeadTag {
  name: string;
  color: string;
}

interface TagBadgeProps {
  tag: LeadTag;
  onRemove?: () => void;
  className?: string;
}

const hexToRgb = (hex: string): string => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
    : '107, 114, 128';
};

export const TagBadge: React.FC<TagBadgeProps> = ({ tag, onRemove, className = '' }) => {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border transition-colors ${className}`}
      style={{
        backgroundColor: `rgba(${hexToRgb(tag.color)}, 0.1)`,
        color: tag.color,
        borderColor: `rgba(${hexToRgb(tag.color)}, 0.2)`,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ backgroundColor: tag.color }}
      />
      {tag.name}
      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-0.5 rounded-full p-0.5 hover:bg-white/10 transition-colors"
          title={`Quitar etiqueta "${tag.name}"`}
        >
          <X className="w-2.5 h-2.5" />
        </button>
      )}
    </span>
  );
};
