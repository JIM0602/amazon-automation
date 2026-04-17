import { motion, AnimatePresence } from 'motion/react';
import { ChevronRight, FileText, Image as ImageIcon, FileSpreadsheet, File } from 'lucide-react';

export interface FileItem {
  id: string;
  name: string;
  type: 'pdf' | 'image' | 'doc' | 'excel';
  size: string;
  createdAt: string;
  url: string;
}

export interface FileSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  files: FileItem[];
  onFilePreview: (file: FileItem) => void;
}

const getFileIcon = (type: FileItem['type']) => {
  switch (type) {
    case 'pdf': return <FileText size={20} />;
    case 'image': return <ImageIcon size={20} />;
    case 'doc': return <File size={20} />;
    case 'excel': return <FileSpreadsheet size={20} />;
    default: return <File size={20} />;
  }
};

export default function FileSidebar({ isOpen, onToggle, files, onFilePreview }: FileSidebarProps) {
  return (
    <AnimatePresence initial={false}>
      <motion.aside
        initial={false}
        animate={{ width: isOpen ? 280 : 0 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="flex flex-col border-r border-[var(--color-glass-border)] bg-[var(--color-glass)] dark:bg-black/20 dark:border-white/10 backdrop-blur-xl h-full flex-shrink-0 overflow-hidden relative z-10"
      >
        <div className="w-[280px] h-full flex flex-col absolute left-0 top-0">
          <div className="flex items-center justify-between h-14 px-4 border-b border-[var(--color-glass-border)] dark:border-white/10 shrink-0">
            <span className="font-semibold text-gray-900 dark:text-white">生成文件</span>
            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-[var(--color-surface-hover)] dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/10 transition-colors"
            >
              <ChevronRight size={18} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
            <div className="flex flex-col gap-2">
              {files.map(file => (
                <button
                  key={file.id}
                  onClick={() => onFilePreview(file)}
                  className="flex items-start gap-3 p-3 rounded-xl transition-colors hover:bg-[var(--color-surface-hover)] dark:hover:bg-white/5 text-left w-full border border-transparent hover:border-[var(--color-glass-border)] dark:hover:border-white/10 group"
                >
                  <div className="shrink-0 p-2 rounded-lg bg-[rgba(255,255,255,0.05)] text-[var(--color-accent)] group-hover:bg-[var(--color-accent)] group-hover:text-white transition-colors">
                    {getFileIcon(file.type)}
                  </div>
                  <div className="flex-1 min-w-0 overflow-hidden">
                    <div className="text-sm font-medium text-gray-900 dark:text-white truncate" title={file.name}>
                      {file.name}
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                      <span>{file.createdAt}</span>
                      <span>•</span>
                      <span>{file.size}</span>
                    </div>
                  </div>
                </button>
              ))}
              {files.length === 0 && (
                <div className="text-center py-8 text-sm text-gray-500">
                  暂无文件
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.aside>
    </AnimatePresence>
  );
}