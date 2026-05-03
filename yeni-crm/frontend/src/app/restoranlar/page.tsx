import { Sidebar } from '@/components/sidebar';
import { listRestaurants, type Restaurant } from '@/lib/api';

export const dynamic = 'force-dynamic';

const MODEL_LABELS: Record<string, { label: string; color: string }> = {
  hourly_only: { label: 'Sadece Saatlik', color: 'bg-blue-50 text-blue-700' },
  hourly_plus_package: { label: 'Saat + Prim', color: 'bg-orange-50 text-orange-700' },
  threshold_package: { label: 'Eşikli (390)', color: 'bg-cream-100 text-yellow-900' },
  fixed_monthly: { label: 'Aylık Sabit', color: 'bg-green-50 text-green-700' },
};

export default async function RestoranlarPage() {
  let restaurants: Restaurant[] = [];
  let error: string | null = null;
  try {
    restaurants = await listRestaurants();
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  const byModel = restaurants.reduce<Record<string, number>>((acc, r) => {
    const m = r.pricing_model ?? 'unknown';
    acc[m] = (acc[m] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="restoranlar" />
      <main className="p-8 max-w-[1500px]">
        <header className="mb-6">
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Satış · <span className="text-brand">Restoranlar</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">Restoranlar</h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {error ? '⚠ Veriler yüklenemedi' : `${restaurants.length} aktif restoran · ${Object.keys(byModel).length} farklı anlaşma tipi`}
          </div>
        </header>

        <div className="bg-bg-surface border border-border rounded-2xl shadow-md flex overflow-hidden mb-6">
          <HeroCell label="Toplam Aktif" value={restaurants.length.toString()} brand meta="canlı veri" />
          <HeroCell label="Saat + Prim" value={(byModel['hourly_plus_package'] ?? 0).toString()} meta="en yaygın anlaşma" />
          <HeroCell label="Eşikli" value={(byModel['threshold_package'] ?? 0).toString()} meta="390 paket eşiği" />
          <HeroCell label="Aylık Sabit" value={(byModel['fixed_monthly'] ?? 0).toString()} meta="prim olmadan" />
        </div>

        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {restaurants.map(r => (
              <RestaurantCard key={r.id} r={r} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function HeroCell({ label, value, meta, brand }: { label: string; value: string; meta?: string; brand?: boolean }) {
  return (
    <div
      className={`flex-1 px-5 py-4 border-r border-border last:border-r-0 ${
        brand ? 'bg-gradient-to-br from-brand-dark to-brand text-white' : ''
      }`}
    >
      <div className={`text-[11px] font-semibold uppercase tracking-wider ${brand ? 'opacity-85' : 'text-text-3'}`}>
        {label}
      </div>
      <div className="font-display text-2xl font-bold tracking-tight mt-1 num">{value}</div>
      {meta && <div className={`text-[11.5px] mt-1 ${brand ? 'opacity-85' : 'text-text-3'}`}>{meta}</div>}
    </div>
  );
}

function RestaurantCard({ r }: { r: Restaurant }) {
  const model = MODEL_LABELS[r.pricing_model ?? ''] ?? { label: r.pricing_model ?? '?', color: 'bg-bg-surface2 text-text-2' };

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-5 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="font-display font-semibold text-lg tracking-tight truncate">{r.brand ?? '—'}</div>
          <div className="text-text-3 text-sm">{r.branch ?? 'Merkez'}</div>
        </div>
        <span className={`px-2 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap ${model.color}`}>
          {model.label}
        </span>
      </div>

      <div className="border-t border-border pt-3 space-y-1.5 text-sm">
        {r.pricing_model === 'fixed_monthly' ? (
          <Row label="Aylık tutar" value={`${(r.fixed_monthly_fee ?? 0).toLocaleString('tr-TR')} ₺`} />
        ) : (
          <>
            {r.hourly_rate != null && r.hourly_rate > 0 && (
              <Row label="Saatlik" value={`${r.hourly_rate.toLocaleString('tr-TR')} ₺/saat`} />
            )}
            {r.pricing_model === 'hourly_plus_package' && r.package_rate != null && r.package_rate > 0 && (
              <Row label="Paket primi" value={`${r.package_rate.toLocaleString('tr-TR')} ₺/paket`} />
            )}
            {r.pricing_model === 'threshold_package' && (
              <>
                <Row label="≤ 390 paket" value={`${(r.package_rate_low ?? 0).toLocaleString('tr-TR')} ₺/paket`} />
                <Row label="> 390 paket" value={`${(r.package_rate_high ?? 0).toLocaleString('tr-TR')} ₺/paket`} />
              </>
            )}
          </>
        )}
        {r.target_headcount != null && r.target_headcount > 0 && (
          <Row label="Hedef kurye" value={`${r.target_headcount} kişi`} />
        )}
        {r.contact_name && (
          <Row label="Yetkili" value={r.contact_name} />
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-text-3">{label}</span>
      <span className="font-semibold text-text num">{value}</span>
    </div>
  );
}
