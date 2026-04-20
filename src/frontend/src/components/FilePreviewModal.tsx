import { useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, Download } from 'lucide-react';

interface FilePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileName: string;
  fileType: string;
  fileUrl: string;
}

export default function FilePreviewModal({
  isOpen,
  onClose,
  fileName,
  fileType,
  fileUrl
}: FilePreviewModalProps) {
  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden'; // Prevent scrolling when modal is open
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-50 flex flex-col bg-black/70 backdrop-blur-sm"
          onClick={onClose}
        >
          {/* Top Bar */}
          <div 
            className="flex items-center justify-between p-4 bg-black/40 text-white shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="font-medium truncate max-w-[80%]">{fileName}</div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
              title="关闭 (Esc)"
            >
              <X size={24} />
            </button>
          </div>

          {/* Preview Area */}
          <div 
            className="flex-1 overflow-hidden flex items-center justify-center p-4 relative"
            onClick={(e) => e.stopPropagation()}
          >
            {fileType === 'pdf' ? (
              <iframe 
                src={fileUrl} 
                className="w-full h-full bg-white rounded shadow-lg"
                title={fileName}
              />
            ) : fileType === 'image' ? (
              <img 
                src={fileUrl} 
                alt={fileName}
                className="max-w-full max-h-full object-contain rounded shadow-lg"
              />
            ) : (
              <div className="text-white/80 flex flex-col items-center gap-4">
                <div className="p-6 bg-white/10 rounded-lg backdrop-blur-md border border-white/20">
                  <p className="text-lg">不支持预览，请下载查看</p>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Bar */}
          <div 
            className="p-4 bg-black/40 flex justify-center shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            <a
              href={fileUrl}
              download={fileName}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors shadow-lg"
            >
              <Download size={18} />
              <span>下载文件</span>
            </a>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
