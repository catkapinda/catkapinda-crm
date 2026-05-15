import { Sidebar } from '@/components/sidebar';
import {
  getCollections,
  getSidebarCounts,
  type CollectionsListResponse,
  type SidebarCounts,
} from '@/lib/api';
import { TahsilatlarView } from './view';

export const metadata = {
  title: 'Tahsilatlar',
  description: 'Restoran fatura tahsilat takibi',
};

export const dynamic = 'force-dynamic';

export default async function TahsilatlarPage({
  searchParams,
}: {
  searchParams: Promise<{ period?: string }>;
}) {
  const { period = '2026-04' } = await searchParams;

  let data: CollectionsListResponse | null = null;
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  const results = await Promise.allSettled([
    getCollections({ period }),
    getSidebarCounts(),
  ]);
  if (results[0].status === 'fulfilled') data = results[0].value;
  else error = results[0].reason instanceof Error ? results[0].reason.message : 'Veriler yüklenemedi';
  if (results[1].status === 'fulfilled') counts = results[1].value;

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="tahsilatlar" counts={counts} />
      <main className="flex-1 flex flex-col">
        {error && (
          <div className="m-6 bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        )}
        <TahsilatlarView initial={data} period={period} counts={counts} />
      </main>
    </div>
  );
}
