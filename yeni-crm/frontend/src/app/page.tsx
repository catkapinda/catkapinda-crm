import { Sidebar } from '@/components/sidebar';
import { getDashboardSummary, type DashboardSummary } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function DashboardPage() {
  let summary: DashboardSummary | null = null;
  let error: string | null = null;
  try {
    summary = await getDashboardSummary('2026-03');
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

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
              {summary
                ? `Mart 2026 · ${summary.puantaj_entries.toLocaleString('tr-TR')} puantaj girişi · ${summary.active_restaurants} aktif restoran`
                : '— veri yükleniyor —'}
            </div>
          </div>
          <button className="bg-brand text-white px-3.5 py-2 rounded-[10px] font-medium text-sm shadow-sm hover:bg-brand-dark transition">
            + Yeni
          </button>
        </header>

        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm mb-6">
            <strong>API hatası:</strong> {error}
          </div>
        ) : null}

        <div className="grid grid-cols-4 gap-3.5 mb-7">
          <KpiCard
            label="Toplam Saat"
            value={summary ? Math.round(summary.total_hours).toLocaleString('tr-TR') : '—'}
            sub="Mart 2026 puantajı"
            hero
          />
          <KpiCard
            label="Toplam Paket"
            value={summary ? summary.total_packages.toLocaleString('tr-TR') : '—'}
            sub={summary ? `${summary.puantaj_entries} kayıt` : ''}
          />
          <KpiCard
            label="Toplam Kesinti · Mart"
            value={summary ? Math.round(summary.total_deductions).toLocaleString('tr-TR') : '—'}
            suffix="₺"
          />
          <KpiCard
            label="Aktif Personel"
            value={summary ? summary.active_personnel.toString() : '—'}
            sub={summary ? `${summary.kurye_count} kurye · ${summary.joker_count} joker` : ''}
          />
        </div>

        <div className="bg-gradient-to-br from-brand-mist to-cream-soft border border-brand-border rounded-2xl p-6 mb-6">
          <div className="font-display text-lg font-semibold mb-2">🚀 Sistem Canlı</div>
          <div className="text-sm text-text-2 leading-relaxed">
            Çat Kapında v3 yayında. Veriler Supabase'den canlı çekiliyor. Şu an kullanılabilir:
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-4">
            <a href="/personel" className="bg-bg-surface border border-border rounded-lg p-3 hover:border-brand transition">
              <div className="font-semibold text-sm">👥 Personel</div>
              <div className="text-xs text-text-3">{summary?.active_personnel ?? 92} kurye listesi</div>
            </a>
            <a href="/restoranlar" className="bg-bg-surface border border-border rounded-lg p-3 hover:border-brand transition">
              <div className="font-semibold text-sm">🍽 Restoranlar</div>
              <div className="text-xs text-text-3">{summary?.active_restaurants ?? 18} aktif anlaşma</div>
            </a>
            <div className="bg-bg-surface2 border border-border rounded-lg p-3 opacity-60">
              <div className="font-semibold text-sm">📅 Puantaj</div>
              <div className="text-xs text-text-3">yakında</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function KpiCard({
  label, value, suffix, sub, hero,
}: { label: string; value: string; suffix?: string; sub?: string; hero?: boolean }) {
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
      {sub && (
        <div className={`mt-3 text-xs ${hero ? 'opacity-85' : 'text-text-3'}`}>
          {sub}
        </div>
      )}
    </div>
  );
}
