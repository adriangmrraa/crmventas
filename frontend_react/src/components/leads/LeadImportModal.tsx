import React, { useState, useRef, useCallback } from 'react';
import { Upload, X, FileSpreadsheet, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import api from '../../api/axios';

interface LeadImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

type ModalState = 'UPLOAD' | 'PREVIEW' | 'EXECUTING' | 'RESULT';

interface PreviewData {
  columns: string[];
  mapping: Record<string, string>;
  rows: Record<string, unknown>[];
  total: number;
  duplicates: number;
  sample: Record<string, unknown>[];
}

interface ImportResult {
  created: number;
  updated: number;
  skipped: number;
}

const LeadImportModal: React.FC<LeadImportModalProps> = ({ isOpen, onClose, onComplete }) => {
  const [state, setState] = useState<ModalState>('UPLOAD');
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [onDuplicate, setOnDuplicate] = useState<'skip' | 'update'>('skip');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<File | null>(null);

  const reset = useCallback(() => {
    setState('UPLOAD');
    setPreview(null);
    setResult(null);
    setError(null);
    setIsDragging(false);
    setOnDuplicate('skip');
    fileRef.current = null;
  }, []);

  const handleClose = useCallback(() => {
    reset();
    onClose();
  }, [reset, onClose]);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    fileRef.current = file;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setState('EXECUTING');
      const res = await api.post('/admin/core/crm/leads/import/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPreview(res.data);
      setState('PREVIEW');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(axiosErr.response?.data?.detail || axiosErr.message || 'Error al procesar el archivo');
      setState('UPLOAD');
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
    [handleFile]
  );

  const handleImport = useCallback(async () => {
    if (!preview) return;
    setError(null);
    setState('EXECUTING');

    try {
      const res = await api.post('/admin/core/crm/leads/import/execute', {
        rows: preview.rows,
        mapping: preview.mapping,
        on_duplicate: onDuplicate,
      });
      setResult(res.data);
      setState('RESULT');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(axiosErr.response?.data?.detail || axiosErr.message || 'Error al importar');
      setState('PREVIEW');
    }
  }, [preview, onDuplicate]);

  const handleResultClose = useCallback(() => {
    onComplete();
    handleClose();
  }, [onComplete, handleClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={handleClose}
    >
      <div
        className="bg-[#0d1117] rounded-2xl border border-white/[0.08] max-w-lg w-full p-6 relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-white text-lg font-semibold">Importar Leads</h2>
          <button
            onClick={handleClose}
            className="text-white/40 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/[0.06]"
          >
            <X size={18} />
          </button>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-2">
            <AlertCircle size={16} className="text-red-400 mt-0.5 shrink-0" />
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* UPLOAD state */}
        {state === 'UPLOAD' && (
          <div>
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`
                border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer
                ${isDragging
                  ? 'border-blue-500/50 bg-blue-500/[0.06]'
                  : 'border-white/[0.12] hover:border-blue-500/30 hover:bg-white/[0.02]'
                }
              `}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload size={36} className="text-white/30 mx-auto mb-3" />
              <p className="text-white/70 text-sm font-medium mb-1">
                Arrastra un CSV o Excel
              </p>
              <p className="text-white/30 text-xs mb-4">
                Formatos aceptados: .csv, .xlsx
              </p>
              <button
                type="button"
                className="px-4 py-2 bg-white/[0.06] hover:bg-white/[0.1] text-white text-sm rounded-lg border border-white/[0.08] transition-all active:scale-95"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                Buscar archivos
              </button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx"
              className="hidden"
              onChange={handleFileInput}
            />
          </div>
        )}

        {/* PREVIEW state */}
        {state === 'PREVIEW' && preview && (
          <div>
            {/* File info */}
            <div className="flex items-center gap-2 mb-4 p-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
              <FileSpreadsheet size={18} className="text-blue-400" />
              <span className="text-white/70 text-sm">
                {preview.total} registros encontrados
              </span>
              {preview.duplicates > 0 && (
                <span className="ml-auto text-amber-400/80 text-xs">
                  {preview.duplicates} duplicados
                </span>
              )}
            </div>

            {/* Column mapping table */}
            <div className="mb-4 rounded-xl border border-white/[0.06] overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-white/[0.04]">
                    <th className="text-left text-white/50 font-medium px-3 py-2">Columna CSV</th>
                    <th className="text-left text-white/50 font-medium px-3 py-2">Campo</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(preview.mapping).map(([csvCol, dbField]) => (
                    <tr key={csvCol} className="border-t border-white/[0.04]">
                      <td className="text-white/70 px-3 py-2">{csvCol}</td>
                      <td className="text-white px-3 py-2 font-mono text-xs">{dbField}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Sample rows */}
            {preview.sample && preview.sample.length > 0 && (
              <div className="mb-4 rounded-xl border border-white/[0.06] overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-white/[0.04]">
                      {Object.values(preview.mapping).map((field) => (
                        <th key={field} className="text-left text-white/50 font-medium px-2 py-2 whitespace-nowrap">
                          {field}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.sample.slice(0, 5).map((row, i) => (
                      <tr key={i} className="border-t border-white/[0.04]">
                        {Object.values(preview.mapping).map((field) => (
                          <td key={field} className="text-white/60 px-2 py-1.5 whitespace-nowrap max-w-[120px] truncate">
                            {String(row[field] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Duplicate strategy */}
            {preview.duplicates > 0 && (
              <div className="mb-4">
                <label className="text-white/50 text-xs block mb-2">Si hay duplicados:</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setOnDuplicate('skip')}
                    className={`px-3 py-1.5 text-xs rounded-lg border transition-all active:scale-95 ${
                      onDuplicate === 'skip'
                        ? 'bg-white/[0.1] border-white/[0.15] text-white'
                        : 'bg-white/[0.04] border-white/[0.06] text-white/50 hover:text-white/70'
                    }`}
                  >
                    Omitir
                  </button>
                  <button
                    onClick={() => setOnDuplicate('update')}
                    className={`px-3 py-1.5 text-xs rounded-lg border transition-all active:scale-95 ${
                      onDuplicate === 'update'
                        ? 'bg-white/[0.1] border-white/[0.15] text-white'
                        : 'bg-white/[0.04] border-white/[0.06] text-white/50 hover:text-white/70'
                    }`}
                  >
                    Actualizar
                  </button>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 mt-5">
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm text-white/50 hover:text-white bg-white/[0.04] hover:bg-white/[0.06] rounded-lg border border-white/[0.06] transition-all active:scale-95"
              >
                Cancelar
              </button>
              <button
                onClick={handleImport}
                className="px-4 py-2 text-sm bg-white text-[#0a0e1a] font-medium rounded-lg hover:bg-white/90 transition-all active:scale-95"
              >
                Importar {preview.total} leads
              </button>
            </div>
          </div>
        )}

        {/* EXECUTING state */}
        {state === 'EXECUTING' && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 size={32} className="text-blue-400 animate-spin mb-4" />
            <p className="text-white/60 text-sm">Importando...</p>
          </div>
        )}

        {/* RESULT state */}
        {state === 'RESULT' && result && (
          <div>
            <div className="flex flex-col items-center py-6 mb-4">
              <CheckCircle size={40} className="text-green-400 mb-3" />
              <p className="text-white font-medium mb-5">Importacion completada</p>

              <div className="flex gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20">
                  <span className="text-green-400 text-sm font-medium">{result.created}</span>
                  <span className="text-green-400/70 text-xs">creados</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <span className="text-blue-400 text-sm font-medium">{result.updated}</span>
                  <span className="text-blue-400/70 text-xs">actualizados</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08]">
                  <span className="text-white/50 text-sm font-medium">{result.skipped}</span>
                  <span className="text-white/30 text-xs">omitidos</span>
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleResultClose}
                className="px-4 py-2 text-sm bg-white text-[#0a0e1a] font-medium rounded-lg hover:bg-white/90 transition-all active:scale-95"
              >
                Cerrar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LeadImportModal;
