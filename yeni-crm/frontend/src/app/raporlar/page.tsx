import {
  getRestaurantReports,
  getRestaurantsAiInsights,
  getSidebarCounts,
} from '@/lib/api';
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

  const [reports, counts, aiInsights] = await Promise.all([
    getRestaurantReports(period),
    getSidebarCounts(),
    // AI Insights — backend ANTHROPIC_API_KEY yoksa null döner,
    // hero gizlenir. 60s revalidate (cache 48h backend tarafında).
    getRestaurantsAiInsights(period, false, { revalidate: 60 }).catch(() => null),
  ]);

  return (
    <div className="flex-1 flex flex-col">
      <RaporlarView
        reports={reports}
        period={period}
        counts={counts}
        aiInsights={aiInsights}
      />
    </div>
  );
}
