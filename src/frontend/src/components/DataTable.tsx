import React, { useState } from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';
import type { Column, PaginationConfig, SortState, SortOrder } from '../types/table';
import { Pagination } from './Pagination';

export interface DataTableSelection {
  selectedKeys: Set<string>
  onSelectionChange: (keys: Set<string>) => void
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey?: string | ((row: T) => string);
  summaryRow?: Partial<T>;
  pagination?: PaginationConfig;
  onRowClick?: (row: T, index: number) => void;
  onSort?: (key: string, order: SortOrder) => void;
  loading?: boolean;
  emptyText?: string;
  className?: string;
  stickyHeaderOffset?: number;
  selection?: DataTableSelection;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  rowKey,
  summaryRow,
  pagination,
  onRowClick,
  onSort,
  loading = false,
  emptyText = '暂无数据',
  className = '',
  stickyHeaderOffset = 0,
  selection,
}: DataTableProps<T>) {
  const [sortState, setSortState] = useState<SortState>({ key: '', order: null });

  const handleSort = (key: string) => {
    setSortState((prev) => {
      let nextOrder: SortOrder = 'asc';
      if (prev.key === key) {
        if (prev.order === 'asc') nextOrder = 'desc';
        else if (prev.order === 'desc') nextOrder = null;
      }
      if (onSort) onSort(key, nextOrder);
      return { key, order: nextOrder };
    });
  };

  const getRowKey = (row: T, index: number): string => {
    if (typeof rowKey === 'function') {
      return rowKey(row);
    }
    if (typeof rowKey === 'string' && row[rowKey] !== undefined) {
      return String(row[rowKey]);
    }
    return `row-${index}`;
  };

  const allVisibleKeys = React.useMemo(() => data.map((row, i) => getRowKey(row, i)), [data, rowKey]);
  const allSelected = selection && allVisibleKeys.length > 0 && allVisibleKeys.every((k) => selection.selectedKeys.has(k));
  const someSelected = selection && allVisibleKeys.some((k) => selection.selectedKeys.has(k));

  const handleSelectAll = () => {
    if (!selection) return;
    if (allSelected) {
      selection.onSelectionChange(new Set());
    } else {
      selection.onSelectionChange(new Set(allVisibleKeys));
    }
  };

  const handleSelectRow = (key: string) => {
    if (!selection) return;
    const next = new Set(selection.selectedKeys);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    selection.onSelectionChange(next);
  };

  const sortedData = React.useMemo(() => {
    if (!sortState.key || !sortState.order) return data;
    return [...data].sort((a, b) => {
      const valA = a[sortState.key];
      const valB = b[sortState.key];
      if (valA === valB) return 0;
      if (valA == null) return sortState.order === 'asc' ? 1 : -1;
      if (valB == null) return sortState.order === 'asc' ? -1 : 1;
      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortState.order === 'asc' ? valA - valB : valB - valA;
      }
      return sortState.order === 'asc'
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });
  }, [data, sortState]);

  return (
    <div className={`w-full min-h-0 overflow-hidden flex flex-col ${className}`}>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="sticky z-10 bg-gray-50 dark:bg-gray-800" style={{ top: stickyHeaderOffset }}>
            <tr>
              {selection && (
                <th className="w-9 px-2 py-2 bg-gray-50 dark:bg-gray-800">
                  <input
                    type="checkbox"
                    checked={!!allSelected}
                    ref={(el) => { if (el) el.indeterminate = !allSelected && !!someSelected; }}
                    onChange={handleSelectAll}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900"
                  />
                </th>
              )}
              {columns.map((col) => {
                const isSorted = sortState.key === col.key && sortState.order;
                return (
                  <th
                    key={col.key}
                    className={`px-4 py-2 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800
                      ${col.sortable ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700' : ''}
                      ${isSorted ? 'font-bold text-gray-900 dark:text-white' : ''}
                    `}
                    style={{
                      width: col.width,
                      textAlign: col.align || 'left',
                    }}
                    onClick={() => col.sortable && handleSort(col.key)}
                  >
                    <div className={`flex items-center space-x-1 ${col.align === 'center' ? 'justify-center' : col.align === 'right' ? 'justify-end' : 'justify-start'}`}>
                      <span>{col.title}</span>
                      {col.sortable && (
                        <span className="flex flex-col opacity-50 space-y-[-4px]">
                          <ArrowUp className={`h-3 w-3 ${sortState.key === col.key && sortState.order === 'asc' ? 'opacity-100 text-blue-500' : ''}`} />
                          <ArrowDown className={`h-3 w-3 ${sortState.key === col.key && sortState.order === 'desc' ? 'opacity-100 text-blue-500' : ''}`} />
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200 dark:bg-gray-900 dark:divide-gray-800">
            {summaryRow && !loading && data.length > 0 && (
              <tr className="sticky z-[9] bg-gray-100 dark:bg-gray-800 font-bold" style={{ top: stickyHeaderOffset + 33 }}>
                {selection && <td className="w-9 px-2 py-2" />}
                {columns.map((col, idx) => (
                  <td
                    key={`summary-${col.key}`}
                    className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 bg-gray-100 dark:bg-gray-800"
                    style={{ textAlign: col.align || 'left' }}
                  >
                    {idx === 0 ? '合计' : (summaryRow[col.key as keyof Partial<T>] as React.ReactNode) ?? ''}
                  </td>
                ))}
              </tr>
            )}
            
            {loading ? (
              Array.from({ length: 5 }).map((_, rowIndex) => (
                <tr key={`skeleton-${rowIndex}`}>
                  {columns.map((col) => (
                    <td key={`skeleton-${rowIndex}-${col.key}`} className="px-4 py-3 whitespace-nowrap">
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : sortedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (selection ? 1 : 0)} className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  {emptyText}
                </td>
              </tr>
            ) : (
              sortedData.map((row, index) => {
                const rk = getRowKey(row, index);
                return (
                  <tr
                    key={rk}
                    className={`
                      ${onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800' : ''}
                      ${selection && selection.selectedKeys.has(rk) ? 'bg-blue-50 dark:bg-blue-950/30' : ''}
                      transition-colors
                    `}
                    onClick={() => onRowClick && onRowClick(row, index)}
                  >
                    {selection && (
                      <td className="w-9 px-2 py-2" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selection.selectedKeys.has(rk)}
                          onChange={() => handleSelectRow(rk)}
                          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900"
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className="px-4 py-2.5 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300"
                        style={{ textAlign: col.align || 'left' }}
                      >
                        {col.render
                          ? col.render(row[col.key as keyof T], row, index)
                          : (row[col.key as keyof T] as React.ReactNode)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {pagination && !loading && data.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
          <Pagination {...pagination} />
        </div>
      )}
    </div>
  );
}
