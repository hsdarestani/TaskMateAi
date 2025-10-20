import { type ReactNode } from 'react';

interface Column<T extends object> {
  key: keyof T;
  label: string;
  render?: (item: T) => ReactNode;
  width?: string;
}

interface Props<T extends object> {
  columns: Column<T>[];
  data: T[];
  emptyLabel?: string;
}

export default function DataTable<T extends { id?: string | number } & Record<string, unknown>>({ columns, data, emptyLabel }: Props<T>) {
  return (
    <div className="overflow-x-auto rounded-3xl border border-white/5 bg-slate-900/40">
      <table className="min-w-full divide-y divide-white/5 text-sm">
        <thead className="text-xs uppercase tracking-wide text-slate-400">
          <tr>
            {columns.map((column) => (
              <th key={column.key as string} className="px-4 py-3 text-left" style={{ width: column.width }}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5 text-slate-200">
          {data.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-4 py-6 text-center text-sm text-slate-500">
                {emptyLabel ?? 'No records found'}
              </td>
            </tr>
          )}
          {data.map((item, index) => (
            <tr key={String(item['id'] ?? `${index}`)} className="hover:bg-white/5">
              {columns.map((column) => (
                <td key={String(column.key)} className="px-4 py-3">
                  {column.render ? column.render(item) : (item[column.key] as ReactNode)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
