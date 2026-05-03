import { Sidebar } from '@/components/sidebar';
import {
  getDeductionSummaryByType,
  getDeductionTypes,
  getSidebarCounts,
  listDeductions,
  listPersonnel,
  type Deduction,
  type DeductionByType,
  type Personnel,
  type SidebarCounts,
} from '@/lib/api';
import { KesintilerView } from './view';

export const dynamic = 'force-dynamic';

export default async function KesintilerPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string }>;
}) {
  const { ay } = await searchParams;
  const period = ay ?? '2026-03';

  let deductions: Deduction[] = [];
  let personnel: Personnel[] = [];
  let counts: SidebarCounts | null = null;
  let typesByMonth: DeductionByType[] = [];
  let allTypes: string[] = [];
  let error: string | null = null;

  try {
    [deductions, personnel, counts, typesByMonth, allTypes] =
      await Promise.all([
        listDeductions({ period }),
        listPersonnel('Aktif').catch(() => []),
        getSidebarCounts().catch(() => null),
        getDeductionSummaryByType(period).catch(() => []),
        getDeductionTypes().catch(() => []),
      ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="kesintiler" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <KesintilerView
            deductions={deductions}
            personnel={personnel}
            typesByMonth={typesByMonth}
            allTypes={allTypes}
            period={period}
          />
        )}
      </main>
    </div>
  );
}
