import React, { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { PaginationConfig } from '../types/table';

export function Pagination({
  current,
  pageSize,
  total,
  pageSizeOptions = [10, 20, 50, 100],
  onChange,
}: PaginationConfig) {
  const [jumpPage, setJumpPage] = useState<string>('');

  const totalPages = Math.ceil(total / pageSize);

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages && page !== current) {
      onChange(page, pageSize);
    }
  };

  const handleSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const size = parseInt(e.target.value, 10);
    onChange(1, size);
  };

  const handleJump = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const page = parseInt(jumpPage, 10);
      if (!isNaN(page)) {
        let targetPage = page;
        if (targetPage < 1) targetPage = 1;
        if (targetPage > totalPages) targetPage = totalPages;
        handlePageChange(targetPage);
        setJumpPage('');
      }
    }
  };

  // Generate page numbers
  const getPages = () => {
    const pages = [];
    if (totalPages <= 5) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      if (current <= 3) {
        pages.push(1, 2, 3, 4, '...', totalPages);
      } else if (current >= totalPages - 2) {
        pages.push(1, '...', totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
      } else {
        pages.push(1, '...', current - 1, current, current + 1, '...', totalPages);
      }
    }
    return pages;
  };

  return (
    <div className="flex items-center justify-between px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
      <div className="flex-1 flex items-center justify-between sm:hidden">
        <button
          onClick={() => handlePageChange(current - 1)}
          disabled={current === 1}
          className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          上一页
        </button>
        <button
          onClick={() => handlePageChange(current + 1)}
          disabled={current === totalPages}
          className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          下一页
        </button>
      </div>
      <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-end gap-4">
        <div>
          <span>共 {total} 条</span>
        </div>

        <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px gap-1" aria-label="Pagination">
          <button
            onClick={() => handlePageChange(current - 1)}
            disabled={current === 1}
            className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
          >
            <span className="sr-only">Previous</span>
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </button>
          
          {getPages().map((page, idx) => {
            if (page === '...') {
              return (
                <span
                  key={`ellipsis-${idx}`}
                  className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  ...
                </span>
              );
            }

            return (
              <button
                key={page}
                onClick={() => handlePageChange(page as number)}
                className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium
                  ${current === page
                    ? 'z-10 bg-blue-50 dark:bg-blue-900 border-blue-500 dark:border-blue-500 text-blue-600 dark:text-blue-200'
                    : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
              >
                {page}
              </button>
            );
          })}

          <button
            onClick={() => handlePageChange(current + 1)}
            disabled={current === totalPages}
            className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
          >
            <span className="sr-only">Next</span>
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </nav>

        <div className="flex items-center gap-2">
          <select
            value={pageSize}
            onChange={handleSizeChange}
            className="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500 p-1"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}条/页
              </option>
            ))}
          </select>

          <div className="flex items-center gap-1">
            <span>前往</span>
            <input
              type="text"
              value={jumpPage}
              onChange={(e) => setJumpPage(e.target.value)}
              onKeyDown={handleJump}
              className="w-12 text-center border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-md text-sm p-1 focus:ring-blue-500 focus:border-blue-500"
            />
            <span>页</span>
          </div>
        </div>
      </div>
    </div>
  );
}
