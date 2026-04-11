export interface Column<T = Record<string, unknown>> {
  key: string;
  title: string;
  width?: string | number;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
  render?: (value: unknown, row: T, index: number) => React.ReactNode;
}

export interface PaginationConfig {
  current: number;
  pageSize: number;
  total: number;
  pageSizeOptions?: number[];
  onChange: (page: number, pageSize: number) => void;
}

export type SortOrder = 'asc' | 'desc' | null;

export interface SortState {
  key: string;
  order: SortOrder;
}
