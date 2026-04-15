/**
 * DriveFileIcon — SPEC-01: Renders an icon based on MIME type.
 */
import {
  FileText,
  Image,
  FileVideo,
  FileAudio,
  FileSpreadsheet,
  FileArchive,
  File,
} from 'lucide-react';

interface DriveFileIconProps {
  mimeType: string;
  size?: number;
}

export default function DriveFileIcon({ mimeType, size = 18 }: DriveFileIconProps) {
  const category = mimeType.split('/')[0];
  const subtype = mimeType.split('/')[1] || '';

  if (category === 'image') return <Image size={size} className="text-green-400/70" />;
  if (category === 'video') return <FileVideo size={size} className="text-purple-400/70" />;
  if (category === 'audio') return <FileAudio size={size} className="text-orange-400/70" />;

  if (mimeType === 'application/pdf') return <FileText size={size} className="text-red-400/70" />;

  if (subtype.includes('spreadsheet') || subtype.includes('excel'))
    return <FileSpreadsheet size={size} className="text-emerald-400/70" />;

  if (subtype.includes('zip') || subtype.includes('compressed'))
    return <FileArchive size={size} className="text-amber-400/70" />;

  if (subtype.includes('word') || subtype.includes('document'))
    return <FileText size={size} className="text-violet-400/70" />;

  return <File size={size} className="text-white/40" />;
}
