import Link from 'next/link';

import { Sidebar } from '@/components/sidebar';
import {
  getPuantajSummaryByRestaurant,
  getSidebarCounts,
  listPuantajEntries,
  listPuantajPeriods,
  type PuantajEntry,
  type RestaurantPuantajSummary,
  type SidebarCounts,
} from '@/lib/api';

export const dynamic = 'force-dynamic';

const MODEL_LABELS: Record<string, { label: string; color: string }> = {
  hourly_only: { label: 'Saatlik', color: 'bg-blue-50 text-blue-700' },
  hourly_plus_package: { label: 'Saat + Prim', color: 'bg-orange-50 text-orange-700' },
  threshold_package: { label: 'Eşikli (390)', color: 'bg-cream-100 text-yellow-900' },
  fixed_monthly: { label: 'Aylık Sabit', color: 'bg-green-50 text-green-700' },
};

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(period: string): string {
  const [y, m] = period.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return period;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function formatDateShort(iso: string | null): string {
  if (!iso) return '—';
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return iso;
  return `${m[3]}.${m[2]}`;
}

function tr(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export default async function PuantajPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string }>;
}) {
  const { ay } = await searchParams;

  // Önce mevcut periyotları çek; URL'de ay yoksa en yenisi varsayılan
  let periods: string[] = [];
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  try {
    [periods, counts] = await Promise.all([
      listPuantajPeriods(),
      getSidebarCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  const period = ay && periods.includes(ay) ? ay : periods[0] ?? '2026-03';

  let summary: RestaurantPuantajSummary[] = [];
  let recent: PuantajEntry[] = [];

  if (!error && period) {
    try {
      [summary, recent] = await Promise.all([
        getPuantajSummaryByRestaurant(period),
        listPuantajEntries(period, { limit: 30 }),
      ]);
    } catch (e) {
      error = e instanceof Error ? e.message : 'API hatası';
    }
  }

  const totalHours = summary.reduce((s, r) => s + r.total_hours, 0);
  const totalPackages = summary.reduce((s, r) => s + r.total_packages, 0);
  const totalEntries = summary.reduce((s, r) => s + r.entries, 0);
  const totalAbsences = summary.reduce((s, r) => s + r.absences, 0);
  const uniquePersonnelTotal = recent.length
    ? new Set(recent.map((e) => e.actual_personnel_id).filter(Boolean)).size
    : summary.reduce((s, r) => Math.max(s, r.unique_personnel), 0);

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="puantaj" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {/* Header */}
        <header className="mb-6 flex justify-between items-end gap-5 flex-wrap">
          <div>
            <div className="text-[13px] text-text-3 font-medium mb-1.5">
              Operasyon · <span className="text-brand">Puantaj</span>
            </div>
            <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
              Puantaj
            </h1>
            <div className="text-text-3 text-sm mt-1 font-medium">
              {error
                ? '⚠ Veriler yüklenemedi'
                : `${formatPeriod(period)} · ${tr(totalEntries)} giriş · ${summary.length} restoran`}
            </div>
          </div>

          {/* Ay seçici */}
          <div className="flex gap-1.5 bg-bg-surface border border-border rounded-2xl p-1.5 shadow-sm flex-wrap">
            {periods.slice(0, 6).map((p) => {
              const isActive = p === period;
              return (
                <Link
                  key={p}
                  href={`/puantaj?ay=${p}`}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                    isActive
                      ? 'bg-brand text-white shadow-sm'
                      : 'text-text-2 hover:bg-bg-surface2'
                  }`}
                >
                  {formatPeriod(p)}
                </Link>
              );
            })}
          </div>
        </header>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm mb-6">
            <strong>API hatası:</strong> {error}
          </div>
        )}

        {/* Hero strip */}
        <div className="bg-bg-surface border border-border rounded-2xl shadow-md flex overflow-hidden mb-6">
          <HeroCell label="Toplam Saat" value={tr(Math.round(totalHours))} brand meta="ay genelinde" />
          <HeroCell label="Toplam Paket" value={tr(totalPackages)} meta={`${tr(totalEntries)} kayıt`} />
          <HeroCell label="Çalışan Personel" value={String(uniquePersonnelTotal || '—')} meta="ay içinde aktif" />
          <HeroCell label="Devamsızlık" value={tr(totalAbsences)} meta={totalAbsences > 0 ? 'izin / dinlenme' : '—'} />
        </div>

        {/* Restoran kartları */}
        <section className="mb-8">
          <h2 className="font-display text-lg font-semibold tracking-tight mb-3">
            Restoran bazında özet
          </h2>
          {summary.length === 0 && !error ? (
            <div className="bg-bg-surface border border-border rounded-2xl p-6 text-text-3 text-sm">
              Bu ay için kayıt bulunamadı.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {summary.map((r) => (
                <RestaurantSummaryCard key={r.restaurant_id ?? Math.random()} r={r} />
              ))}
            </div>
          )}
        </section>

        {/* Son girişler */}
        <section>
          <h2 className="font-display text-lg font-semibold tracking-tight mb-3">
            Son girişler
          </h2>
          {recent.length === 0 ? (
            <div className="bg-bg-surface border border-border rounded-2xl p-6 text-text-3 text-sm">
              Kayıt yok.
            </div>
          ) : (
            <div className="bg-bg-surface border border-border rounded-2xl shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-bg-surface2 text-text-3 text-[12px] uppercase tracking-wider">
                  <tr>
                    <th className="text-left px-4 py-2.5 font-semibold">Tarih</th>
                    <th className="text-left px-4 py-2.5 font-semibold">Restoran</th>
                    <th className="text-left px-4 py-2.5 font-semibold">Personel</th>
                    <th className="text-left px-4 py-2.5 font-semibold">Tip</th>
                    <th className="text-right px-4 py-2.5 font-semibold">Saat</th>
                    <th className="text-right px-4 py-2.5 font-semibold">Paket</th>
                    <th className="text-left px-4 py-2.5 font-semibold">Durum</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((e) => (
                    <EntryRow key={e.id} e={e} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function HeroCell({
  label, value, meta, brand,
}: { label: string; value: string; meta?: string; brand?: boolean }) {
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

function RestaurantSummaryCard({ r }: { r: RestaurantPuantajSummary }) {
  const model = MODEL_LABELS[r.pricing_model ?? ''] ?? {
    label: r.pricing_model ?? '—',
    color: 'bg-bg-surface2 text-text-2',
  };
  const avgPkg = r.entries > 0 ? r.total_packages / r.entries : 0;
  const avgHours = r.entries > 0 ? r.total_hours / r.entries : 0;

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-5 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="font-display font-semibold text-[15px] tracking-tight truncate">
            {r.brand ?? '—'}
          </div>
          <div className="text-text-3 text-xs">{r.branch ?? 'Merkez'}</div>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap ${model.color}`}>
          {model.label}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 border-t border-border pt-3">
        <Stat label="Saat" value={tr(Math.round(r.total_hours))} sub={`Ø ${tr(avgHours, 1)}/gün`} />
        <Stat label="Paket" value={tr(r.total_packages)} sub={`Ø ${tr(Math.round(avgPkg))}/gün`} />
        <Stat label="Personel" value={String(r.unique_personnel)} sub={`${tr(r.entries)} giriş`} />
      </div>

      {r.absences > 0 && (
        <div className="mt-3 text-[11px] text-yellow-800 bg-yellow-50 border border-yellow-200 rounded-md px-2 py-1 inline-block">
          {r.absences} devamsızlık
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-text-3">
        {label}
      </div>
      <div className="font-display text-base font-semibold tracking-tight num mt-0.5">{value}</div>
      {sub && <div className="text-[10.5px] text-text-3 mt-0.5">{sub}</div>}
    </div>
  );
}

function EntryRow({ e }: { e: PuantajEntry }) {
  const isAbsent = !!(e.absence_reason && e.absence_reason.trim() !== '');
  const isJoker = e.coverage_type === 'Joker' || e.personnel_role === 'Joker';

  return (
    <tr className="border-t border-border hover:bg-bg-surface2/50 transition">
      <td className="px-4 py-2.5 text-text-2 font-mono text-[12.5px]">{formatDateShort(e.entry_date)}</td>
      <td className="px-4 py-2.5">
        <div className="font-medium text-text">{e.restaurant_brand ?? '—'}</div>
        {e.restaurant_branch && (
          <div className="text-[11px] text-text-3">{e.restaurant_branch}</div>
        )}
      </td>
      <td className="px-4 py-2.5">
        <div className="font-medium text-text">{e.personnel_name ?? '—'}</div>
        <div className="text-[11px] text-text-3 font-mono">{e.person_code ?? ''}</div>
      </td>
      <td className="px-4 py-2.5">
        {isJoker ? (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-cream-100 text-yellow-800">
            Joker
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-brand-soft text-brand">
            {e.personnel_role ?? '—'}
          </span>
        )}
      </td>
      <td className="px-4 py-2.5 text-right font-mono num">
        {isAbsent ? '—' : tr(e.worked_hours, 1)}
      </td>
      <td className="px-4 py-2.5 text-right font-mono num">
        {isAbsent ? '—' : tr(e.package_count)}
      </td>
      <td className="px-4 py-2.5">
        {isAbsent ? (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-yellow-50 text-yellow-800">
            {e.absence_reason}
          </span>
        ) : (
          <span className="text-[11.5px] text-text-3">{e.status ?? 'Normal'}</span>
        )}
      </td>
    </tr>
  );
}
