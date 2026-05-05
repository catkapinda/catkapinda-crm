import { Sidebar } from '@/components/sidebar';
import {
  getDashboardAnalytics,
  getSidebarCounts,
  type DashboardAnalytics,
  type SidebarCounts,
} from '@/lib/api';

import { KarZararView } from './view';

export const dynamic = 'force-dynamic';

export default async function KarZararPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string }>;
}) {
  const { ay } = await searchParams;
  const period = ay ?? '2026-03';

  let analytics: DashboardAnalytics | null = null;
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  try {
    [analytics, counts] = await Promise.all([
      getDashboardAnalytics(period),
      getSidebarCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="kar-zarar" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : analytics ? (
          <KarZararView analytics={analytics} period={period} />
        ) : (
          <div className="text-text-3 text-sm">Veri yükleniyor…</div>
        )}
      </main>
    </div>
  );
}
