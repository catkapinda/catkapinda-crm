import { Sidebar } from '@/components/sidebar';
import {
  getPuantajMatrix,
  getSidebarCounts,
  listPuantajPeriods,
  type PuantajMatrix,
  type SidebarCounts,
} from '@/lib/api';
import { PuantajGrid } from './grid';

export const dynamic = 'force-dynamic';

export default async function PuantajPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string }>;
}) {
  const { ay } = await searchParams;

  let periods: string[] = [];
  let counts: SidebarCounts | null = null;
  let matrix: PuantajMatrix | null = null;
  let error: string | null = null;

  try {
    [periods, counts] = await Promise.all([
      listPuantajPeriods().catch(() => []),
      getSidebarCounts().catch(() => null),
    ]);
  } catch {
    /* sayaç hatası kritik değil */
  }

  const period = ay && periods.includes(ay) ? ay : periods[0] ?? '2026-03';

  try {
    matrix = await getPuantajMatrix(period);
  } catch (e) {
    error = e instanceof Error ? e.message : 'Veri alınamadı';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="puantaj" counts={counts} />
      <main className="px-8 pt-6 pb-32 max-w-[1700px]">
        {error || !matrix ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error ?? 'Matris alınamadı'}
          </div>
        ) : (
          <PuantajGrid matrix={matrix} period={period} periods={periods} />
        )}
      </main>
    </div>
  );
}
