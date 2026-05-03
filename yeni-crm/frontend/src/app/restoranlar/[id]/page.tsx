import Link from 'next/link';
import { notFound } from 'next/navigation';
import { AlertTriangle, ChevronLeft } from 'lucide-react';

import { Sidebar } from '@/components/sidebar';
import {
  getRestaurantMonthly,
  getSidebarCounts,
  listPuantajPeriods,
  type CourierBilling,
  type RestaurantMonthly,
  type SidebarCounts,
} from '@/lib/api';

import { RestaurantDetailHeader } from './header';

export const dynamic = 'force-dynamic';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(period: string): string {
  const [y, m] = period.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return period;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function tr(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

const MODEL_LABELS: Record<string, string> = {
  hourly_only: 'Saatlik',
  hourly_plus_package: 'Saat + Prim',
  threshold_package: 'Eşikli (390)',
  fixed_monthly: 'Aylık Sabit',
};

export default async function RestaurantDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ ay?: string }>;
}) {
  const { id } = await params;
  const { ay } = await searchParams;
  const restaurantId = parseInt(id, 10);
  if (Number.isNaN(restaurantId)) notFound();

  let periods: string[] = [];
  let counts: SidebarCounts | null = null;
  try {
    [periods, counts] = await Promise.all([
      listPuantajPeriods().catch(() => []),
      getSidebarCounts().catch(() => null),
    ]);
  } catch {
    // sayaç hatası kritik değil
  }

  const period = ay && periods.includes(ay) ? ay : periods[0] ?? '2026-03';

  let data: RestaurantMonthly | null = null;
  let error: string | null = null;
  try {
    data = await getRestaurantMonthly(restaurantId, period);
  } catch (e) {
    error = e instanceof Error ? e.message : 'Veri alınamadı';
  }

  if (!data && !error) notFound();

  const r = data?.restaurant;
  const totals = data?.totals;
  const allCouriers = data?.couriers ?? [];

  // Aktif (ay içinde gerçekten çalışmış) ve plan-only (gelmemiş) ayrımı
  const activeCouriers = allCouriers.filter((c) => c.working_days > 0);
  const noShowCouriers = allCouriers.filter((c) => c.working_days === 0);
  const noShowAbsenceTotal = noShowCouriers.reduce(
    (sum, c) => sum + c.absences,
    0,
  );

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="restoranlar" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {/* Breadcrumb */}
        <div className="text-[13px] text-text-3 font-medium mb-3 flex items-center gap-2">
          <Link href="/restoranlar" className="hover:text-brand transition inline-flex items-center gap-0.5">
            <ChevronLeft className="w-3.5 h-3.5" strokeWidth={2.2} /> Restoranlar
          </Link>
          {r && (
            <>
              <span>·</span>
              <span className="text-text-2">{r.brand}</span>
              {r.branch && <span className="text-text-3">/ {r.branch}</span>}
            </>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm mb-6">
            <strong>API hatası:</strong> {error}
          </div>
        )}

        {r && (
          <RestaurantDetailHeader
            restaurant={r}
            period={period}
            periods={periods}
            modelLabel={MODEL_LABELS[r.pricing_model ?? ''] ?? r.pricing_model ?? ''}
          />
        )}

        {/* KPI strip */}
        {totals && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-6">
            <KpiCard
              label={`${formatPeriod(period)} Saat`}
              value={tr(Math.round(totals.total_hours))}
              sub={`${tr(totals.total_working_days)} mesai günü`}
            />
            <KpiCard
              label="Paket"
              value={tr(totals.total_packages)}
              sub={`${tr(totals.total_entries)} puantaj kaydı`}
            />
            <KpiCard
              label="Fatura · KDV Dahil"
              value={tr(totals.total_billing_incl_vat)}
              suffix="₺"
              sub={`KDV hariç ${tr(totals.total_billing_excl_vat)} ₺`}
              hero
            />
            <KpiCard
              label={`KDV %${totals.vat_rate}`}
              value={tr(totals.vat_amount)}
              suffix="₺"
              sub="restorandan +KDV alınır"
              hero
            />
          </div>
        )}

        {/* Kurye bazında fatura kırılımı */}
        <section>
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="font-display text-xl font-semibold tracking-tight">
              Kurye Bazında Fatura Kırılımı
            </h2>
            <span className="text-[12px] text-text-3 font-medium">
              {totals?.courier_count ?? 0} kurye
              {totals?.support_count ? ` · ${totals.support_count} destek` : ''}
            </span>
          </div>

          {activeCouriers.length === 0 && noShowCouriers.length === 0 ? (
            <div className="bg-bg-surface border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
              Bu ay için kayıt bulunamadı.
            </div>
          ) : (
            <div className="bg-bg-surface border border-border rounded-2xl shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-bg-surface2 text-text-3 text-[12px] uppercase tracking-wider">
                  <tr>
                    <th className="text-left px-4 py-3 font-semibold">Kurye</th>
                    <th className="text-left px-4 py-3 font-semibold">Tip</th>
                    <th className="text-right px-4 py-3 font-semibold">Gün</th>
                    <th className="text-right px-4 py-3 font-semibold">Saat</th>
                    <th className="text-right px-4 py-3 font-semibold">Paket</th>
                    <th className="text-right px-4 py-3 font-semibold">Devamsızlık</th>
                    <th className="text-left px-4 py-3 font-semibold">Hesaplama</th>
                    <th className="text-right px-4 py-3 font-semibold bg-brand-soft text-brand">
                      Fatura (KDV dahil)
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {activeCouriers.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-8 text-center text-text-3 text-sm">
                        Bu ay çalışan kurye yok.
                      </td>
                    </tr>
                  ) : (
                    activeCouriers.map((c) => (
                      <CourierRow key={c.personnel_id ?? Math.random()} c={c} />
                    ))
                  )}
                </tbody>
                {totals && (
                  <tfoot>
                    <tr className="border-t-2 border-border bg-bg-surface2/50 font-semibold">
                      <td colSpan={2} className="px-4 py-3 text-text">
                        Toplam
                      </td>
                      <td className="px-4 py-3 text-right text-text num">
                        {totals.total_working_days}
                      </td>
                      <td className="px-4 py-3 text-right text-text num">
                        {tr(Math.round(totals.total_hours))}
                      </td>
                      <td className="px-4 py-3 text-right text-text num">
                        {tr(totals.total_packages)}
                      </td>
                      <td className="px-4 py-3 text-right text-text num">
                        {totals.total_absences}
                      </td>
                      <td className="px-4 py-3 text-text-3 text-[11.5px]">
                        KDV %{totals.vat_rate} → {tr(totals.vat_amount)} ₺
                      </td>
                      <td className="px-4 py-3 text-right bg-brand-soft">
                        <div className="num font-display text-brand text-[16px] font-bold">
                          {tr(totals.total_billing_incl_vat)} ₺
                        </div>
                        <div className="text-[10.5px] text-text-3 mt-0.5">
                          KDV hariç {tr(totals.total_billing_excl_vat)} ₺
                        </div>
                      </td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          )}

          {/* Plan yapılıp gelmeyen kuryeler */}
          {noShowCouriers.length > 0 && (
            <details className="mt-4 bg-yellow-50/40 border border-yellow-200 rounded-2xl overflow-hidden">
              <summary className="px-4 py-3 cursor-pointer flex items-center justify-between gap-3 hover:bg-yellow-50 transition">
                <div className="flex items-center gap-2 text-sm">
                  <AlertTriangle className="w-4 h-4 text-yellow-700" strokeWidth={2.2} />
                  <span className="font-semibold text-yellow-900">
                    Plan yapıldı, çalışmadı
                  </span>
                  <span className="text-yellow-800 text-[12px]">
                    {noShowCouriers.length} kişi · {noShowAbsenceTotal} devamsızlık
                  </span>
                </div>
                <span className="text-[11px] text-yellow-700 group-open:rotate-90 transition">
                  detay ▾
                </span>
              </summary>
              <div className="border-t border-yellow-200 bg-bg-surface">
                <table className="w-full text-sm">
                  <thead className="bg-yellow-50/60 text-yellow-900 text-[11.5px] uppercase tracking-wider">
                    <tr>
                      <th className="text-left px-4 py-2.5 font-semibold">Kurye</th>
                      <th className="text-left px-4 py-2.5 font-semibold">Rol</th>
                      <th className="text-left px-4 py-2.5 font-semibold">Durum</th>
                      <th className="text-right px-4 py-2.5 font-semibold">Devamsızlık</th>
                    </tr>
                  </thead>
                  <tbody>
                    {noShowCouriers.map((c) => (
                      <tr
                        key={c.personnel_id ?? Math.random()}
                        className="border-t border-yellow-100"
                      >
                        <td className="px-4 py-2.5">
                          <div className="font-medium text-text-2">
                            {c.full_name ?? '—'}
                          </div>
                          <div className="text-[11px] text-text-3 font-mono">
                            {c.person_code ?? ''}
                          </div>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="text-[11.5px] text-text-2">
                            {c.role ?? '—'}
                          </span>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="px-2 py-0.5 rounded-full text-[10.5px] font-semibold bg-yellow-50 text-yellow-800 border border-yellow-200">
                            {c.is_support ? '↪ Destek planı' : 'Plan'}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-right num text-yellow-800">
                          {c.absences}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="px-4 py-2.5 text-[11.5px] text-text-3 bg-bg-surface2/40 border-t border-yellow-100">
                  Bu kişiler bu ay puantaja yazıldı ama gelmediği için fatura
                  hesabına dahil edilmedi.
                </div>
              </div>
            </details>
          )}
        </section>
      </main>
    </div>
  );
}

function KpiCard({
  label, value, suffix, sub, hero,
}: {
  label: string;
  value: string;
  suffix?: string;
  sub?: string;
  hero?: boolean;
}) {
  return (
    <div
      className={`rounded-2xl p-5 shadow-md transition hover:-translate-y-0.5 hover:shadow-lg ${
        hero
          ? 'bg-gradient-to-br from-brand-dark via-brand to-cream-warm text-white'
          : 'bg-bg-surface border border-border'
      }`}
    >
      <div
        className={`text-[11px] font-semibold uppercase tracking-wider ${
          hero ? 'opacity-85' : 'text-text-3'
        } mb-3`}
      >
        {label}
      </div>
      <div className="font-display text-[28px] font-semibold tracking-tight leading-none num">
        {value}
        {suffix && (
          <span
            className={`text-base font-medium ml-1 ${
              hero ? 'opacity-70' : 'text-text-3'
            }`}
          >
            {suffix}
          </span>
        )}
      </div>
      {sub && (
        <div className={`mt-2.5 text-[11.5px] ${hero ? 'opacity-85' : 'text-text-3'}`}>
          {sub}
        </div>
      )}
    </div>
  );
}

function CourierRow({ c }: { c: CourierBilling }) {
  const isJoker = c.role === 'Joker';
  const isManager = c.role === 'Bölge Müdürü' || c.role === 'Kaptan' || c.role === 'Restoran Takım Şefi';

  return (
    <tr className="border-t border-border hover:bg-bg-surface2/50 transition align-top">
      <td className="px-4 py-3">
        <div className="font-medium text-text">{c.full_name ?? '—'}</div>
        <div className="text-[11px] text-text-3 font-mono">{c.person_code ?? ''}</div>
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-col gap-1">
          <span
            className={`px-2 py-0.5 rounded-full text-[10.5px] font-semibold inline-block w-fit ${
              isJoker
                ? 'bg-cream-100 text-yellow-800'
                : isManager
                ? 'bg-text text-white'
                : 'bg-brand-soft text-brand'
            }`}
          >
            {c.role ?? '—'}
          </span>
          {c.is_support && (
            <span className="px-2 py-0.5 rounded-full text-[10.5px] font-semibold bg-orange-50 text-orange-700 border border-orange-200 inline-block w-fit">
              ↪ Destek
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-right num text-text-2">{c.working_days}</td>
      <td className="px-4 py-3 text-right num text-text-2">{tr(c.total_hours, 1)}</td>
      <td className="px-4 py-3 text-right num text-text-2">{tr(c.total_packages)}</td>
      <td className="px-4 py-3 text-right num">
        {c.absences > 0 ? (
          <span className="text-yellow-800">{c.absences}</span>
        ) : (
          <span className="text-text-3">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-[11.5px] text-text-3">
        {c.billing_breakdown.length === 0 ? (
          <span>—</span>
        ) : (
          <div className="space-y-0.5">
            {c.billing_breakdown.map((line, i) => (
              <div key={i} className="leading-tight">
                {line.label}{' '}
                <span className="text-text-2 font-mono">
                  = {tr(line.amount, 0)} ₺
                </span>
              </div>
            ))}
          </div>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="num font-display text-[15px] font-semibold text-brand">
          {tr(c.billing_incl_vat)} ₺
        </div>
        <div className="text-[10.5px] text-text-3 mt-0.5">
          KDV hariç {tr(c.billing_excl_vat)} ₺
        </div>
      </td>
    </tr>
  );
}
