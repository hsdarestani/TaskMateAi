import { useMemo } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

ChartJS.register(ArcElement, Tooltip, Legend);

interface Props {
  languages: Array<{ code: string; label: string; value: number }>;
}

export default function LanguageDonut({ languages }: Props) {
  const chartData = useMemo(
    () => ({
      labels: languages.map((item) => item.label),
      datasets: [
        {
          label: 'Locale mix',
          data: languages.map((item) => item.value),
          backgroundColor: ['#34d399', '#38bdf8', '#facc15', '#a855f7'],
          borderWidth: 0
        }
      ]
    }),
    [languages]
  );

  return (
    <div className="mx-auto h-64 w-64">
      <Doughnut data={chartData} options={{ plugins: { legend: { labels: { color: '#cbd5f5' } } } }} />
    </div>
  );
}
