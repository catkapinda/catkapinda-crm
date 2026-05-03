import { Sidebar } from '@/components/sidebar';

export default function DashboardPage() {
  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="dashboard" />
      <main className="p-8 max-w-[1500px]">
        <header className="flex justify-between items-start mb-7 gap-5">
          <div>
            <div className="text-[13px] text-text-3 font-medium mb-1.5">
              İyi akşamlar, <span className="text-brand">Ebru</span> 👋
            </div>
            <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
              Genel Bakış
            </h1>
            <div className="text-text-3 text-sm mt-1 font-medium">
              Mart 2026 · 31 günlük dönem · 18 aktif restoran
            </div>
          </div>
          <button className="bg-brand text-white px-3.5 py-2 rounded-[10px] font-medium text-sm shadow-sm hover:bg-brand-dark transition">
            + Yeni
          </button>
        </header>

        <div className="grid grid-cols-4 gap-3.5 mb-7">
          <KpiCard label="Toplam Fatura · KDV hariç" value="4.360.733" suffix="₺" trend="↑ 12.4%" hero />
          <KpiCard label="KDV Dahil" value="5.232.880" suffix="₺" />
          <KpiCard label="Toplam Kesinti" value="1.343.774" suffix="₺" trend="↓ 3.2%" />
          <KpiCard label="Aktif Personel" value="92" sub="85 kurye · 2 joker · 5 yönetim" />
        </div>

        <div className="bg-bg-surface border border-border rounded-2xl p-8 text-center text-text-3 shadow-md">
          <div className="font-display text-xl mb-2">🚧 Kod tarafı kuruluyor</div>
          <div className="text-sm">
            Bu sayfa şu an boilerplate. Sonraki adımlarda Supabase'den canlı veri çekecek, mock-up tasarımı kodla bire bir eşleşecek.
          </div>
        </div>
      </main>
    </div>
  );
}

function KpiCard({
  label, value, suffix, trend, sub, hero,
}: { label: string; value: string; suffix?: string; trend?: string; sub?: string; hero?: boolean }) {
  return (
    <div
      className={`rounded-2xl p-5 shadow-md transition hover:-translate-y-0.5 hover:shadow-lg ${
        hero
          ? 'bg-gradient-to-br from-brand-dark via-brand to-cream-warm text-white'
          : 'bg-bg-surface border border-border'
      }`}
    >
      <div className={`text-xs font-semibold uppercase tracking-wider ${hero ? 'opacity-85' : 'text-text-3'} mb-3.5`}>
        {label}
      </div>
      <div className="font-display text-[36px] font-semibold tracking-tight leading-none num">
        {value}
        {suffix && <span className={`text-base font-medium ml-1 ${hero ? 'opacity-70' : 'text-text-3'}`}>{suffix}</span>}
      </div>
      {(trend || sub) && (
        <div className={`mt-3 text-xs ${hero ? 'opacity-85' : 'text-text-3'} flex items-center gap-2`}>
          {trend && (
            <span className={`px-2 py-0.5 rounded font-bold text-[11px] ${hero ? 'bg-white/20' : 'bg-green-50 text-green-600'}`}>
              {trend}
            </span>
          )}
          {sub && <span>{sub}</span>}
          {trend && !sub && <span>geçen aya göre</span>}
        </div>
      )}
    </div>
  );
}
