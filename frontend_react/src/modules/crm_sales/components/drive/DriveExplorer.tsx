/**
 * DriveExplorer — SPEC-01: Main container for the Drive file system.
 * Manages folder navigation, file listing, upload, and breadcrumb state.
 */
import { useState, useEffect, useCallback } from 'react';
import { FolderPlus, Upload, Grid, List, ChevronRight, Home } from 'lucide-react';
import api from '../../../../api/axios';
import { useTranslation } from '../../../../context/LanguageContext';
import DriveFileIcon from './DriveFileIcon';

interface DriveFolder {
  id: string;
  nombre: string;
  client_id: number;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
}

interface DriveFile {
  id: string;
  nombre: string;
  mime_type: string;
  size_bytes: number;
  folder_id: string;
  created_at: string;
}

interface BreadcrumbItem {
  id: string;
  nombre: string;
}

interface DriveExplorerProps {
  clientId: number;
}

const API_BASE = '/api/v1/drive';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DriveExplorer({ clientId }: DriveExplorerProps) {
  const { t } = useTranslation();
  const [folders, setFolders] = useState<DriveFolder[]>([]);
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [breadcrumb, setBreadcrumb] = useState<BreadcrumbItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(() =>
    (localStorage.getItem('drive_view_mode') as 'grid' | 'list') || 'grid'
  );
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const loadContents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const folderParams: Record<string, string> = { client_id: String(clientId) };
      if (currentFolderId) folderParams.parent_id = currentFolderId;

      const [foldersRes, filesRes] = await Promise.all([
        api.get(`${API_BASE}/folders`, { params: folderParams }),
        currentFolderId
          ? api.get(`${API_BASE}/files`, { params: { folder_id: currentFolderId } })
          : Promise.resolve({ data: [] }),
      ]);

      setFolders(foldersRes.data);
      setFiles(filesRes.data);

      // Load breadcrumb
      if (currentFolderId) {
        const bcRes = await api.get(`${API_BASE}/folders/${currentFolderId}/breadcrumb`);
        setBreadcrumb(bcRes.data.breadcrumb || []);
      } else {
        setBreadcrumb([]);
      }
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('drive.error_loading');
      setError(String(message));
    } finally {
      setLoading(false);
    }
  }, [clientId, currentFolderId, t]);

  useEffect(() => {
    loadContents();
  }, [loadContents]);

  const toggleView = () => {
    const next = viewMode === 'grid' ? 'list' : 'grid';
    setViewMode(next);
    localStorage.setItem('drive_view_mode', next);
  };

  const navigateToFolder = (folderId: string | null) => {
    setCurrentFolderId(folderId);
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    try {
      await api.post(`${API_BASE}/folders`, {
        nombre: newFolderName.trim(),
        client_id: clientId,
        parent_id: currentFolderId,
      });
      setNewFolderName('');
      setShowCreateFolder(false);
      loadContents();
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('drive.error_create_folder');
      setError(String(message));
    }
  };

  const handleUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0 || !currentFolderId) return;

    setUploading(true);
    setError(null);

    for (const file of Array.from(fileList)) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('folder_id', currentFolderId);
        formData.append('client_id', String(clientId));

        await api.post(`${API_BASE}/files/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } catch (err: unknown) {
        const message = err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : t('drive.error_upload');
        setError(String(message));
      }
    }

    setUploading(false);
    loadContents();
  };

  const handleDownload = async (fileId: string, fileName: string) => {
    try {
      const res = await api.get(`${API_BASE}/files/${fileId}/download`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch {
      setError(t('drive.error_download'));
    }
  };

  const handleDeleteFile = async (fileId: string) => {
    if (!confirm(t('drive.confirm_delete_file'))) return;
    try {
      await api.delete(`${API_BASE}/files/${fileId}`);
      loadContents();
    } catch {
      setError(t('drive.error_delete'));
    }
  };

  const handleDeleteFolder = async (folderId: string) => {
    if (!confirm(t('drive.confirm_delete_folder'))) return;
    try {
      await api.delete(`${API_BASE}/folders/${folderId}`);
      loadContents();
    } catch {
      setError(t('drive.error_delete'));
    }
  };

  // Drag & Drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (currentFolderId) setDragActive(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (currentFolderId) handleUpload(e.dataTransfer.files);
  };

  return (
    <div
      className="flex flex-col h-full"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Header: Breadcrumb + Actions */}
      <div className="shrink-0 px-4 py-3 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between gap-3">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1 text-sm text-white/60 min-w-0 overflow-hidden">
          <button
            onClick={() => navigateToFolder(null)}
            className="hover:text-white shrink-0 flex items-center gap-1"
          >
            <Home size={14} />
            <span>{t('drive.root')}</span>
          </button>
          {breadcrumb.map((item) => (
            <span key={item.id} className="flex items-center gap-1 shrink-0">
              <ChevronRight size={12} className="text-white/30" />
              <button
                onClick={() => navigateToFolder(item.id)}
                className="hover:text-white truncate max-w-[120px]"
              >
                {item.nombre}
              </button>
            </span>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowCreateFolder(true)}
            className="p-2 rounded-lg hover:bg-white/[0.06] text-white/60 hover:text-white"
            title={t('drive.new_folder')}
          >
            <FolderPlus size={18} />
          </button>
          {currentFolderId && (
            <label className="p-2 rounded-lg hover:bg-white/[0.06] text-white/60 hover:text-white cursor-pointer">
              <Upload size={18} />
              <input
                type="file"
                multiple
                className="hidden"
                onChange={(e) => handleUpload(e.target.files)}
              />
            </label>
          )}
          <button
            onClick={toggleView}
            className="p-2 rounded-lg hover:bg-white/[0.06] text-white/60 hover:text-white"
          >
            {viewMode === 'grid' ? <List size={18} /> : <Grid size={18} />}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            {t('common.close')}
          </button>
        </div>
      )}

      {/* Create Folder Modal */}
      {showCreateFolder && (
        <div className="mx-4 mt-2 p-3 bg-white/[0.04] border border-white/[0.08] rounded-lg flex items-center gap-2">
          <input
            type="text"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            placeholder={t('drive.folder_name')}
            className="flex-1 px-3 py-1.5 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm focus:ring-2 focus:ring-blue-500/30"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateFolder();
              if (e.key === 'Escape') setShowCreateFolder(false);
            }}
          />
          <button
            onClick={handleCreateFolder}
            className="px-3 py-1.5 bg-primary text-white text-sm rounded-lg hover:bg-blue-700"
          >
            {t('common.create')}
          </button>
          <button
            onClick={() => setShowCreateFolder(false)}
            className="px-3 py-1.5 text-white/60 text-sm hover:text-white"
          >
            {t('common.cancel')}
          </button>
        </div>
      )}

      {/* Upload indicator */}
      {uploading && (
        <div className="mx-4 mt-2 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg text-blue-400 text-sm flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          {t('drive.uploading')}
        </div>
      )}

      {/* Drag overlay */}
      {dragActive && currentFolderId && (
        <div className="mx-4 mt-2 p-8 border-2 border-dashed border-blue-500/40 rounded-lg bg-blue-500/5 text-center text-blue-400 text-sm">
          {t('drive.drop_files')}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-white/40">
            {t('common.loading')}
          </div>
        ) : folders.length === 0 && files.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-white/30 text-sm">
            <p>{currentFolderId ? t('drive.empty_folder') : t('drive.no_folders')}</p>
            {!currentFolderId && (
              <button
                onClick={() => setShowCreateFolder(true)}
                className="mt-2 text-primary hover:underline"
              >
                {t('drive.create_first_folder')}
              </button>
            )}
          </div>
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {folders.map((folder) => (
              <div
                key={folder.id}
                className="group relative p-3 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] cursor-pointer transition-colors"
                onClick={() => navigateToFolder(folder.id)}
              >
                <div className="flex flex-col items-center gap-2">
                  <FolderPlus size={32} className="text-yellow-400/70" />
                  <span className="text-sm text-white/80 truncate w-full text-center">
                    {folder.nombre}
                  </span>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id); }}
                  className="absolute top-1 right-1 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/20 text-red-400 text-xs"
                >
                  &times;
                </button>
              </div>
            ))}
            {files.map((file) => (
              <div
                key={file.id}
                className="group relative p-3 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] cursor-pointer transition-colors"
                onClick={() => handleDownload(file.id, file.nombre)}
              >
                <div className="flex flex-col items-center gap-2">
                  <DriveFileIcon mimeType={file.mime_type} size={32} />
                  <span className="text-sm text-white/80 truncate w-full text-center">
                    {file.nombre}
                  </span>
                  <span className="text-xs text-white/40">
                    {formatFileSize(file.size_bytes)}
                  </span>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.id); }}
                  className="absolute top-1 right-1 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/20 text-red-400 text-xs"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
        ) : (
          /* List View */
          <div className="space-y-1">
            {folders.map((folder) => (
              <div
                key={folder.id}
                className="group flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/[0.04] cursor-pointer"
                onClick={() => navigateToFolder(folder.id)}
              >
                <FolderPlus size={18} className="text-yellow-400/70 shrink-0" />
                <span className="flex-1 text-sm text-white/80 truncate">{folder.nombre}</span>
                <span className="text-xs text-white/30">
                  {new Date(folder.created_at).toLocaleDateString()}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id); }}
                  className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/20 text-red-400 text-xs"
                >
                  &times;
                </button>
              </div>
            ))}
            {files.map((file) => (
              <div
                key={file.id}
                className="group flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/[0.04] cursor-pointer"
                onClick={() => handleDownload(file.id, file.nombre)}
              >
                <DriveFileIcon mimeType={file.mime_type} size={18} />
                <span className="flex-1 text-sm text-white/80 truncate">{file.nombre}</span>
                <span className="text-xs text-white/30">{formatFileSize(file.size_bytes)}</span>
                <span className="text-xs text-white/30">
                  {new Date(file.created_at).toLocaleDateString()}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.id); }}
                  className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/20 text-red-400 text-xs"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
