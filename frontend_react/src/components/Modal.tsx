import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showClose?: boolean;
}

const sizeClasses: Record<string, string> = {
  sm: 'lg:max-w-md',
  md: 'lg:max-w-lg',
  lg: 'lg:max-w-2xl',
  xl: 'lg:max-w-4xl',
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  showClose = true,
}) => {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      <style>{`
        @keyframes modalIn {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
      `}</style>

      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
        onClick={onClose}
      />

      {/* Container: bottom sheet on mobile, centered on desktop */}
      <div
        className="fixed inset-0 z-50 flex items-end lg:items-center lg:justify-center lg:p-4"
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        {/* Content card */}
        <div
          className={`
            w-full ${sizeClasses[size]}
            bg-[#0d1117] border border-white/[0.08]
            rounded-t-2xl lg:rounded-2xl
            max-h-[92vh] lg:max-h-[85vh]
            shadow-2xl shadow-black/40
            flex flex-col
            overflow-hidden
          `}
          style={{ animation: 'modalIn 300ms ease-out' }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          {(title || showClose) && (
            <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between shrink-0">
              {title && (
                <h2 className="text-lg font-bold text-white">{title}</h2>
              )}
              {showClose && (
                <button
                  onClick={onClose}
                  className="w-8 h-8 rounded-full bg-white/[0.04] hover:bg-white/[0.08] flex items-center justify-center text-white/30 hover:text-white/60 active:scale-90 transition-all ml-auto"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          )}

          {/* Body */}
          <div className="p-5 overflow-y-auto flex-1 min-h-0">
            {children}
          </div>

          {/* Footer */}
          {footer && (
            <div className="px-5 py-4 border-t border-white/[0.06] bg-white/[0.02] rounded-b-2xl flex justify-end gap-3 shrink-0">
              {footer}
            </div>
          )}
        </div>
      </div>
    </>
  );
};
