import { getRestaurantReports, getSidebarCounts } from '@/lib/api';
import { RaporlarView } from './view';

export const metadata = {
  title: 'Restoran Raporları',
  description: 'Restoran performans raporları ve analizler',
};

export default async function RaporlarPage({
  searchParams,
}: {
  searchParams: Promise<{ period?: string }>;
}) {
  const { period = '2026-03' } = await searchParams;

  const [reports, counts] = await Promise.all([
    getRestaurantReports(period),
    getSidebarCounts(),
  ]);

  return (
    <div className="flex-1 flex flex-col">
      <RaporlarView
        reports={reports}
        period={period}
        counts={counts}
      />
    </div>
  );
}
