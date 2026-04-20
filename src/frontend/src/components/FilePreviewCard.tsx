import { FileText, Image as ImageIcon, FileSpreadsheet, File, Eye, Download } from 'lucide-react';

export interface FilePreviewCardProps {
  fileName: string;
  fileType: 'pdf' | 'image' | 'doc' | 'excel';
  fileSize: string;
  fileUrl: string;
  onPreview: () => void;
  onDownload: () => void;
}

export function FilePreviewCard({
  fileName,
  fileType,
  fileSize,
  fileUrl,
  onPreview,
  onDownload,
}: FilePreviewCardProps) {
  const getIcon = () => {
    switch (fileType) {
      case 'pdf':
      case 'doc':
        return <FileText className="w-8 h-8 text-blue-500" />;
      case 'image':
        return <ImageIcon className="w-8 h-8 text-purple-500" />;
      case 'excel':
        return <FileSpreadsheet className="w-8 h-8 text-green-500" />;
      default:
        return <File className="w-8 h-8 text-gray-500" />;
    }
  };

  return (
    <div className="glass rounded-xl p-4 flex items-center gap-4 bg-white/5 dark:bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
      <div className="flex-shrink-0 p-2.5 bg-gray-100/50 dark:bg-gray-800/50 rounded-lg border border-gray-200/50 dark:border-gray-700/50">
        {getIcon()}
      </div>
      
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate" title={fileName}>
          {fileName}
        </h4>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {fileSize}
        </p>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={onPreview}
          className="px-3 py-1.5 text-sm flex items-center gap-1.5 text-gray-700 dark:text-gray-200 bg-gray-100/80 dark:bg-gray-800/80 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors border border-gray-200/50 dark:border-gray-700/50"
        >
          <Eye className="w-4 h-4" />
          <span>预览</span>
        </button>
        <a
          href={fileUrl}
          download
          onClick={onDownload}
          className="px-3 py-1.5 text-sm flex items-center gap-1.5 text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-sm"
        >
          <Download className="w-4 h-4" />
          <span>下载</span>
        </a>
      </div>
    </div>
  );
}
