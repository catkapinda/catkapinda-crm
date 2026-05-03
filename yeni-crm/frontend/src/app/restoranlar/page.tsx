import { Sidebar } from '@/components/sidebar';
import {
  getPuantajSummaryByRestaurant,
  getSidebarCounts,
  listRestaurants,
  type RestaurantPuantajSummary,
  type Restaurant,
  type SidebarCounts,
} from '@/lib/api';
import { RestaurantsView } from './view';

export const dynamic = 'force-dynamic';

export default async function RestoranlarPage() {
  let restaurants: Restaurant[] = [];
  let perf: RestaurantPuantajSummary[] = [];
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  try {
    [restaurants, perf, counts] = await Promise.all([
      listRestaurants(),
      getPuantajSummaryByRestaurant('2026-03').catch(() => []),
      getSidebarCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="restoranlar" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        <header className="mb-6">
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Satış · <span className="text-brand">Restoranlar</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            Restoranlar
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {error
              ? 'Veriler yüklenemedi'
              : `${restaurants.length} aktif restoran · Mart 2026 performansı yansıtılıyor · karta tıklayıp düzenleyin`}
          </div>
        </header>

        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <RestaurantsView restaurants={restaurants} perf={perf} />
        )}
      </main>
    </div>
  );
}
