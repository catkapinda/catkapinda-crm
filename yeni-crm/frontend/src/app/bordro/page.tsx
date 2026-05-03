import { Sidebar } from '@/components/sidebar';
import {
  getPayroll,
  getSidebarCounts,
  listPuantajPeriods,
  type PayrollResult,
  type SidebarCounts,
} from '@/lib/api';
import { BordroView } from './view';

export const dynamic = 'force-dynamic';

export default async function BordroPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string }>;
}) {
  const { ay } = await searchParams;

  let periods: string[] = [];
  let counts: SidebarCounts | null = null;
  let payroll: PayrollResult | null = null;
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
    payroll = await getPayroll(period);
  } catch (e) {
    error = e instanceof Error ? e.message : 'Veri alınamadı';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="bordro" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error || !payroll ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error ?? 'Bordro alınamadı'}
          </div>
        ) : (
          <BordroView payroll={payroll} period={period} periods={periods} />
        )}
      </main>
    </div>
  );
}
