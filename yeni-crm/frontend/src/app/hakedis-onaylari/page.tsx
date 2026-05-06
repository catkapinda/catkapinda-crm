import { Sidebar } from '@/components/sidebar';
import {
  getSidebarCounts,
  listPayrollSignatures,
  listPuantajPeriods,
  type PayrollSignature,
  type SidebarCounts,
} from '@/lib/api';

import { HakedisOnayView } from './view';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Hakediş Onayları | CRM',
  description: 'İmzalanan bordrolar ve ödeme takibi',
};

export default async function HakedisOnayPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string; durum?: string }>;
}) {
  const { ay, durum } = await searchParams;

  let signatures: PayrollSignature[] = [];
  let counts: SidebarCounts | null = null;
  let periods: string[] = [];
  let error: string | null = null;

  try {
    [counts, periods] = await Promise.all([
      getSidebarCounts().catch(() => null),
      listPuantajPeriods().catch(() => []),
    ]);
  } catch {
    /* sidebar / period hatası kritik değil */
  }

  // Aktif period: URL'den geldiyse onu kullan, yoksa periods[0] (en yeni)
  const activePeriod = ay && periods.length > 0 && periods.includes(ay)
    ? ay
    : (periods[0] ?? '2026-03');

  try {
    signatures = await listPayrollSignatures(activePeriod);
  } catch (e) {
    error = e instanceof Error ? e.message : 'Veri alınamadı';
  }

  const activeStatus = (
    durum === 'odenecek' || durum === 'odendi' || durum === 'imzalanmadi'
      ? durum
      : null
  ) as 'odenecek' | 'odendi' | 'imzalanmadi' | null;

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="hakedis-onay" counts={counts} />
      <main className="px-8 pt-6 pb-32 max-w-[1700px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <HakedisOnayView
            initialSignatures={signatures}
            periods={periods}
            activePeriod={activePeriod}
            activeStatus={activeStatus}
          />
        )}
      </main>
    </div>
  );
}
