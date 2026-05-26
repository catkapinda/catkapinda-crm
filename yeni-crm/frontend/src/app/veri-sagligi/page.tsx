import { Sidebar } from '@/components/sidebar';
import {
  getDataHealth,
  getSidebarCounts,
  type DataHealthResponse,
  type SidebarCounts,
} from '@/lib/api';

import { VeriSagligiView } from './view';

export const dynamic = 'force-dynamic';

export default async function VeriSagligiPage({
  searchParams,
}: {
  searchParams: Promise<{ period?: string }>;
}) {
  const { period = '2026-03' } = await searchParams;

  let data: DataHealthResponse | null = null;
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  try {
    [data, counts] = await Promise.all([
      getDataHealth(period),
      getSidebarCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'Veri sağlığı kontrolü başarısız';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="veri-sagligi" counts={counts} />
      <main className="p-6 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : data ? (
          <VeriSagligiView data={data} period={period} />
        ) : (
          <div className="text-text-3 text-sm">Veri yükleniyor…</div>
        )}
      </main>
    </div>
  );
}
