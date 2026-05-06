import { Sidebar } from '@/components/sidebar';
import {
  getSidebarCounts,
  listPuantajApprovals,
  listPuantajPeriods,
  type PuantajApproval,
  type SidebarCounts,
} from '@/lib/api';

import { PuantajOnayView } from './view';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Puantaj Onayları | CRM',
  description: 'Operasyondan gelen aylık puantajları onayla / reddet',
};

export default async function PuantajOnayPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string; durum?: string }>;
}) {
  const { ay, durum } = await searchParams;

  let approvals: PuantajApproval[] = [];
  let counts: SidebarCounts | null = null;
  let periods: string[] = [];
  let error: string | null = null;

  try {
    [approvals, counts, periods] = await Promise.all([
      listPuantajApprovals(
        (durum as 'pending' | 'approved' | 'rejected' | undefined) ?? undefined,
        ay,
      ).catch(() => []),
      getSidebarCounts().catch(() => null),
      listPuantajPeriods().catch(() => []),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="puantaj-onay" counts={counts} />
      <main className="px-8 pt-6 pb-32 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <PuantajOnayView
            initialApprovals={approvals}
            periods={periods}
            activePeriod={ay ?? null}
            activeStatus={(durum as 'pending' | 'approved' | 'rejected') ?? null}
          />
        )}
      </main>
    </div>
  );
}
