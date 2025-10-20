interface HeatmapRow {
  label: string;
  values: number[];
}

interface Props {
  rows: HeatmapRow[];
}

const hourLabels = Array.from({ length: 24 }, (_, index) => `${index}:00`);

export default function UsageHeatmap({ rows }: Props) {
  const max = Math.max(...rows.flatMap((row) => row.values));

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] table-fixed border-separate border-spacing-1">
        <thead>
          <tr>
            <th className="w-24 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Day</th>
            {hourLabels.map((hour) => (
              <th key={hour} className="text-center text-[10px] font-medium text-slate-500">
                {hour}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td className="text-xs font-medium uppercase tracking-wide text-slate-300">{row.label}</td>
              {row.values.map((value, index) => {
                const intensity = max === 0 ? 0 : value / max;
                const background = `rgba(34, 211, 238, ${0.15 + intensity * 0.65})`;
                return (
                  <td
                    key={`${row.label}-${index}`}
                    style={{ backgroundColor: intensity === 0 ? 'rgba(15, 23, 42, 0.6)' : background }}
                    className="h-6 rounded-md text-center text-[10px] text-slate-900"
                    title={`${row.label} @ ${hourLabels[index]} → ${value} active users`}
                  >
                    {value > 0 ? value : ''}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
