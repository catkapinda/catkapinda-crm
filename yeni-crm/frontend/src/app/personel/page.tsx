import { Sidebar } from '@/components/sidebar';
import {
  getManagementSummary,
  getPageInsights,
  getPersonnelStats,
  getSidebarCounts,
  getTopPerformers,
  listPersonnel,
  listRestaurants,
  type ManagementMember,
  type PageInsights,
  type Personnel,
  type PersonnelStats,
  type Restaurant,
  type SidebarCounts,
  type TopPerformer,
} from '@/lib/api';
import { PersonnelView } from './view';

export const dynamic = 'force-dynamic';

const PERIOD_RE = /^\d{4}-(0[1-9]|1[0-2])$/;

function defaultPeriod(): string {
  // Bugün - 1 ay (son tamamlanan ay)
  const now = new Date();
  const d = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

export default async function PersonelPage({
  searchParams,
}: {
  searchParams: Promise<{ period?: string | string[] }>;
}) {
  const sp = await searchParams;
  const rawPeriod = typeof sp.period === 'string' ? sp.period : '';
  const period = PERIOD_RE.test(rawPeriod) ? rawPeriod : defaultPeriod();

  let allPersonnel: Personnel[] = [];
  let restaurants: Restaurant[] = [];
  let counts: SidebarCounts | null = null;
  let topPerformers: TopPerformer[] = [];
  let management: ManagementMember[] = [];
  let insights: PageInsights | null = null;
  let stats: PersonnelStats[] = [];
  let error: string | null = null;

  try {
    [allPersonnel, restaurants, counts, topPerformers, management, insights, stats] =
      await Promise.all([
        listPersonnel(),
        listRestaurants().catch(() => []),
        getSidebarCounts().catch(() => null),
        getTopPerformers(period, 3).catch(() => []),
        getManagementSummary(period).catch(() => []),
        getPageInsights(period).catch(() => null),
        getPersonnelStats(period).catch(() => []),
      ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="personel" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <PersonnelView
            personnel={allPersonnel}
            restaurants={restaurants}
            topPerformers={topPerformers}
            management={management}
            insights={insights}
            stats={stats}
            period={period}
          />
        )}
      </main>
    </div>
  );
}
