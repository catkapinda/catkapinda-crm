import {
  getRestaurantReports,
  getRestaurantsAiInsights,
  getSidebarCounts,
  type AiInsightsResponse,
  type RestaurantReports,
  type SidebarCounts,
} from '@/lib/api';
import { RaporlarView } from './view';

export const metadata = {
  title: 'Restoran Raporları',
  description: 'Restoran performans raporları ve analizler',
};

const EMPTY_REPORTS: RestaurantReports = {
  period: '',
  previous_period: '',
  turnover: [],
  courier_efficiency: [],
  cost_per_package: { overall: 0, by_restaurant: [], by_courier: [] },
  package_growth: [],
};

export default async function RaporlarPage({
  searchParams,
}: {
  searchParams: Promise<{ period?: string }>;
}) {
  const { period = '2026-03' } = await searchParams;

  // Her fetch'i ayrı try/catch ile sar — biri fail olsa bile sayfa
  // crash etmesin (Node fetch keep-alive cache + Render instance
  // değişimi sırasında ECONNREFUSED olabilir).
  let reports: RestaurantReports = EMPTY_REPORTS;
  let counts: SidebarCounts | null = null;
  let aiInsights: AiInsightsResponse | null = null;
  let error: string | null = null;

  const results = await Promise.allSettled([
    getRestaurantReports(period),
    getSidebarCounts(),
    getRestaurantsAiInsights(period, false, { revalidate: 60 }),
  ]);

  if (results[0].status === 'fulfilled') reports = results[0].value;
  else error = results[0].reason instanceof Error ? results[0].reason.message : 'Raporlar yüklenemedi';

  if (results[1].status === 'fulfilled') counts = results[1].value;
  if (results[2].status === 'fulfilled') aiInsights = results[2].value;

  return (
    <div className="flex-1 flex flex-col">
      {error && (
        <div className="m-6 bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
          <strong>API hatası:</strong> {error}
        </div>
      )}
      <RaporlarView
        reports={reports}
        period={period}
        counts={counts}
        aiInsights={aiInsights}
      />
    </div>
  );
}
