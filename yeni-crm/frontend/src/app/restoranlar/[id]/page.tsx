import Link from 'next/link';
import { notFound } from 'next/navigation';

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
  const couriers = data?.couriers ?? [];

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="restoranlar" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {/* Breadcrumb */}
        <div className="text-[13px] text-text-3 font-medium mb-3 flex items-center gap-2">
          <Link href="/restoranlar" className="hover:text-brand transition">
            ← Restoranlar
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
              label="Fatura · KDV Hariç"
              value={tr(totals.total_billing_excl_vat)}
              suffix="₺"
              hero
            />
            <KpiCard
              label="Fatura · KDV Dahil"
              value={tr(totals.total_billing_incl_vat)}
              suffix="₺"
              sub={`KDV %${totals.vat_rate} = ${tr(totals.vat_amount)} ₺`}
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

          {couriers.length === 0 ? (
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
                    <th className="text-right px-4 py-3 font-semibold">KDV Hariç</th>
                    <th className="text-right px-4 py-3 font-semibold bg-brand-soft text-brand">
                      KDV Dahil
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {couriers.map((c) => (
                    <CourierRow key={c.personnel_id ?? Math.random()} c={c} />
                  ))}
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
                      <td className="px-4 py-3 text-right num text-text">
                        {tr(totals.total_billing_excl_vat)} ₺
                      </td>
                      <td className="px-4 py-3 text-right num font-display text-brand text-[15px] bg-brand-soft">
                        {tr(totals.total_billing_incl_vat)} ₺
                      </td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
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
      <td className="px-4 py-3 text-right num text-text">{tr(c.billing_excl_vat)} ₺</td>
      <td className="px-4 py-3 text-right num font-semibold text-brand bg-brand-soft/50">
        {tr(c.billing_incl_vat)} ₺
      </td>
    </tr>
  );
}
