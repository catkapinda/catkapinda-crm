import { Sidebar } from '@/components/sidebar';
import {
  getBoxReturns,
  getSidebarCounts,
  type BoxReturnsListResponse,
  type SidebarCounts,
} from '@/lib/api';
import { BoxReturnsView } from './view';

export const metadata = {
  title: 'Box Geri Alım',
  description: 'Kuryelerden geri alınan ekipman takibi',
};

export const dynamic = 'force-dynamic';

const EMPTY: BoxReturnsListResponse = {
  items: [],
  summary: {
    records_count: 0,
    total_quantity: 0,
    total_payout: 0,
    unique_personnel: 0,
    waived_count: 0,
  },
  condition_options: ['Sağlam', 'Hafif Hasarlı', 'Ağır Hasarlı', 'Kullanılamaz', 'Eksik'],
  item_options: ['Box', 'Çanta', 'Korumalı Mont', 'Yağmurluk', 'Kask', 'Telefon Tutacağı'],
};

export default async function BoxGeriAlimPage() {
  let data: BoxReturnsListResponse = EMPTY;
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  const results = await Promise.allSettled([
    getBoxReturns(),
    getSidebarCounts(),
  ]);
  if (results[0].status === 'fulfilled') data = results[0].value;
  else error = results[0].reason instanceof Error ? results[0].reason.message : 'Veriler yüklenemedi';
  if (results[1].status === 'fulfilled') counts = results[1].value;

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="box-geri-alim" counts={counts} />
      <main className="flex-1 flex flex-col">
        {error && (
          <div className="m-6 bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        )}
        <BoxReturnsView initial={data} counts={counts} />
      </main>
    </div>
  );
}
