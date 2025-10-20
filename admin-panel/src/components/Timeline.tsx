interface TimelineItem {
  id: string;
  title: string;
  timestamp: string;
  description?: string;
  status?: 'pending' | 'completed' | 'failed';
}

interface Props {
  items: TimelineItem[];
}

const statusColors: Record<NonNullable<TimelineItem['status']>, string> = {
  pending: 'bg-amber-400/80',
  completed: 'bg-emerald-400/80',
  failed: 'bg-rose-400/80'
};

export default function Timeline({ items }: Props) {
  return (
    <ol className="relative space-y-6 border-l border-white/5 pl-6">
      {items.map((item, index) => (
        <li key={item.id} className="space-y-1">
          <span
            className={`absolute -left-[11px] mt-1 h-5 w-5 rounded-full border border-slate-900 ${
              item.status ? statusColors[item.status] : 'bg-cyan-400/80'
            }`}
          />
          <div className="flex items-center justify-between text-sm text-slate-400">
            <p className="font-medium text-slate-200">{item.title}</p>
            <time dateTime={item.timestamp}>{item.timestamp}</time>
          </div>
          {item.description && <p className="text-sm text-slate-400">{item.description}</p>}
          {index !== items.length - 1 && <div className="border-b border-white/5 pt-4" />}
        </li>
      ))}
    </ol>
  );
}
