'use client';

import { useMemo, useState } from 'react';
import {
  AlertCircle, Building2, ChevronDown, ChevronRight, Filter,
  Receipt, Search, Users2, X,
} from 'lucide-react';

import {
  type CourierBilling,
  type InvoiceSummary,
  type RestaurantInvoice,
  type RestaurantMonthly,
  getRestaurantMonthly,
} from '@/lib/api';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string): string {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function m(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function n(value: number | null | undefined, digits = 1): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function FaturalarView({
  invoices, summary, period,
}: {
  invoices: RestaurantInvoice[];
  summary: InvoiceSummary | null;
  period: string;
}) {
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [breakdownCache, setBreakdownCache] = useState<Record<number, RestaurantMonthly>>({});
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    if (!q) return invoices;
    return invoices.filter((inv) => {
      const hay = `${inv.rest_brand ?? ''} ${inv.rest_branch ?? ''} ${inv.invoice_no ?? ''}`
        .toLocaleLowerCase('tr-TR');
      return hay.includes(q);
    });
  }, [invoices, search]);

  const totals = useMemo(() => {
    const t = { excl: 0, vat: 0, incl: 0, courier: 0 };
    for (const i of filtered) {
      t.excl += i.amount_excl_vat;
      t.vat += i.vat_amount;
      t.incl += i.amount_incl_vat;
      t.courier += i.courier_count || 0;
    }
    return t;
  }, [filtered]);

  async function toggleExpand(inv: RestaurantInvoice) {
    const rid = inv.restaurant_id;
    const isOpen = !!expanded[rid];
    if (isOpen) {
      setExpanded((e) => ({ ...e, [rid]: false }));
      return;
    }
    setExpanded((e) => ({ ...e, [rid]: true }));
    if (breakdownCache[rid]) return; // önbellekte
    setLoadingId(rid);
    setError(null);
    try {
      const data = await getRestaurantMonthly(rid, period);
      setBreakdownCache((c) => ({ ...c, [rid]: data }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Kırılım yüklenemedi');
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <>
      {/* HEADER */}
      <header className="flex justify-between items-end gap-5 flex-wrap mb-6">
        <div>
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Finans · <span className="text-brand font-semibold">Faturalar</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            {formatPeriod(period)} Faturaları
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {summary
              ? `${summary.count_total} restoran · toplam ${m(summary.sum_incl_vat)} ₺ (KDV dahil)`
              : '— veri yükleniyor —'}
            <span className="text-text-3 text-xs ml-2 opacity-70">
              · Ödeme takibi /tahsilatlar sayfasında
            </span>
          </div>
        </div>
      </header>

      {/* HERO STRIP — 4 KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <KpiCard
          icon={<Receipt className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="brand"
          label="Toplam Fatura"
          value={summary ? m(summary.sum_incl_vat) : '—'}
          suffix="₺"
          sub={summary ? `${summary.count_total} restoran · KDV dahil` : ''}
        />
        <KpiCard
          icon={<Receipt className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="purple"
          label="KDV Hariç"
          value={summary ? m(summary.sum_excl_vat) : '—'}
          suffix="₺"
          sub="matrah toplamı"
        />
        <KpiCard
          icon={<Receipt className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="warn"
          label="Toplam KDV"
          value={summary ? m(summary.sum_vat) : '—'}
          suffix="₺"
          sub="hesaplanan KDV"
        />
        <KpiCard
          icon={<Users2 className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="success"
          label="Kurye Sayısı"
          value={summary ? String(totals.courier || 0) : '—'}
          sub={`${invoices.length} restoran toplamı`}
        />
      </div>

      {/* SEARCH */}
      <div className="bg-white border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2">
        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 absolute left-2.5 text-text-3" strokeWidth={2.2} />
          <input
            type="search"
            placeholder="Restoran / fatura no ara…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1.5 rounded-lg border border-border text-sm w-72 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
          />
        </div>
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto inline-flex items-center gap-1">
          <Filter className="w-3 h-3" strokeWidth={2.2} />
          {filtered.length} sonuç · KDV dahil <span className="text-brand font-mono">{m(totals.incl)} ₺</span>
        </span>
      </div>

      {/* ERROR */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-sm mb-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" strokeWidth={2.2} />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-600 hover:text-red-800">
            <X className="w-4 h-4" strokeWidth={2.4} />
          </button>
        </div>
      )}

      {/* TABLE */}
      {filtered.length === 0 ? (
        <div className="bg-white border border-border rounded-2xl p-12 text-center">
          <Receipt className="w-10 h-10 mx-auto text-text-3 mb-3" strokeWidth={1.5} />
          <div className="text-text-2 font-medium">Bu dönemde fatura yok.</div>
        </div>
      ) : (
        <div className="bg-white border border-border rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-[13px]">
            <thead className="bg-cream-50/80 text-text-3 text-[10.5px] uppercase tracking-[0.08em] border-b border-border">
              <tr>
                <th className="text-left px-3 py-3 font-bold w-8"></th>
                <th className="text-left px-4 py-3 font-bold">Restoran</th>
                <th className="text-right px-3 py-3 font-bold">Kurye</th>
                <th className="text-right px-3 py-3 font-bold">KDV Hariç</th>
                <th className="text-right px-3 py-3 font-bold">KDV</th>
                <th className="text-right px-3 py-3 font-bold bg-brand-soft/60 text-brand">KDV Dahil</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((inv) => {
                const isOpen = !!expanded[inv.restaurant_id];
                const breakdown = breakdownCache[inv.restaurant_id];
                const isLoading = loadingId === inv.restaurant_id;
                return (
                  <InvoiceRow
                    key={`${inv.restaurant_id}-${period}`}
                    inv={inv}
                    period={period}
                    isOpen={isOpen}
                    isLoading={isLoading}
                    breakdown={breakdown}
                    onToggle={() => toggleExpand(inv)}
                  />
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-brand/30 bg-gradient-to-r from-brand-soft/50 to-transparent font-semibold">
                <td colSpan={2} className="px-4 py-3 text-text text-[12.5px]">
                  Toplam ({filtered.length} restoran)
                </td>
                <td className="px-3 py-3 text-right num font-mono text-text-2 tabular-nums">
                  {totals.courier}
                </td>
                <td className="px-3 py-3 text-right num font-mono text-text tabular-nums">
                  {m(totals.excl)} ₺
                </td>
                <td className="px-3 py-3 text-right num font-mono text-text-2 tabular-nums">
                  {m(totals.vat)} ₺
                </td>
                <td className="px-3 py-3 text-right font-display text-brand text-[15px] num bg-brand-soft tabular-nums">
                  {m(totals.incl)} ₺
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </>
  );
}

function KpiCard({
  icon, accent, label, value, suffix, sub,
}: {
  icon: React.ReactNode;
  accent: 'brand' | 'success' | 'warn' | 'purple';
  label: string;
  value: string;
  suffix?: string;
  sub: string;
}) {
  const ringMap: Record<string, string> = {
    brand: 'bg-gradient-to-b from-brand to-blue-400',
    success: 'bg-gradient-to-b from-green-500 to-emerald-300',
    warn: 'bg-gradient-to-b from-orange-500 to-amber-300',
    purple: 'bg-gradient-to-b from-purple-500 to-fuchsia-300',
  };
  const iconBgMap: Record<string, string> = {
    brand: 'bg-brand-soft text-brand',
    success: 'bg-green-100 text-green-700',
    warn: 'bg-orange-100 text-orange-700',
    purple: 'bg-purple-100 text-purple-700',
  };

  return (
    <div className="relative bg-white rounded-2xl px-5 py-4 shadow-sm border border-border overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition">
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${ringMap[accent]}`} />
      <div className="flex items-start justify-between mb-2">
        <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold">
          {label}
        </div>
        <div className={`w-7 h-7 rounded-lg ${iconBgMap[accent]} flex items-center justify-center`}>
          {icon}
        </div>
      </div>
      <div className="font-display text-[24px] font-bold tracking-tight leading-none num tabular-nums">
        {value}
        {suffix && (
          <span className="text-[14px] font-medium text-text-3 ml-1">{suffix}</span>
        )}
      </div>
      <div className="text-[11px] text-text-3 mt-2 font-medium">{sub}</div>
    </div>
  );
}

function InvoiceRow({
  inv, period, isOpen, isLoading, breakdown, onToggle,
}: {
  inv: RestaurantInvoice;
  period: string;
  isOpen: boolean;
  isLoading: boolean;
  breakdown?: RestaurantMonthly;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className="border-t border-border/70 hover:bg-cream-50/70 transition cursor-pointer group"
        onClick={onToggle}
      >
        {/* Expand */}
        <td className="px-3 py-2.5 text-text-3">
          {isOpen ? (
            <ChevronDown className="w-4 h-4" strokeWidth={2.4} />
          ) : (
            <ChevronRight className="w-4 h-4 group-hover:text-brand transition" strokeWidth={2.4} />
          )}
        </td>

        {/* Restoran */}
        <td className="px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <span className="w-1 h-7 rounded-full bg-brand/40" />
            <div className="min-w-0">
              <div className="font-semibold text-text text-[13px] truncate">
                {inv.rest_brand ?? '—'}
              </div>
              {inv.rest_branch && (
                <div className="text-[10.5px] text-text-3 truncate">
                  {inv.rest_branch}
                </div>
              )}
            </div>
          </div>
        </td>

        {/* Kurye sayısı */}
        <td className="px-3 py-2.5 text-right num font-mono text-[12.5px] text-text-2 tabular-nums">
          {inv.courier_count || 0}
        </td>

        {/* KDV hariç */}
        <td className="px-3 py-2.5 text-right num font-mono text-[12.5px] tabular-nums">
          {m(inv.amount_excl_vat)}
        </td>

        {/* KDV */}
        <td className="px-3 py-2.5 text-right num font-mono text-[12px] text-text-3 tabular-nums">
          <div>{m(inv.vat_amount)}</div>
          <div className="text-[10px]">%{inv.vat_rate}</div>
        </td>

        {/* KDV dahil — accent */}
        <td className="px-3 py-2.5 text-right num font-display font-bold text-brand text-[14px] bg-brand-soft/40 group-hover:bg-brand-soft transition tabular-nums">
          {m(inv.amount_incl_vat)}
        </td>
      </tr>

      {/* Genişletilmiş kırılım */}
      {isOpen && (
        <tr className="bg-cream-50/40 border-t border-border/60">
          <td colSpan={6} className="px-4 py-3">
            {isLoading ? (
              <div className="text-text-3 text-[12px] italic px-4 py-3">
                Kurye kırılımı yükleniyor…
              </div>
            ) : breakdown ? (
              <CourierBreakdown breakdown={breakdown} restaurantId={inv.restaurant_id} period={period} />
            ) : (
              <div className="text-text-3 text-[12px] italic px-4 py-3">
                Kırılım yok.
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function CourierBreakdown({
  breakdown, restaurantId, period,
}: {
  breakdown: RestaurantMonthly;
  restaurantId: number;
  period: string;
}) {
  const couriers = breakdown.couriers || [];
  const totals = breakdown.totals;

  if (couriers.length === 0) {
    return (
      <div className="text-text-3 text-[12px] italic px-4 py-3">
        Bu ay için kurye kaydı yok.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-white overflow-hidden">
      <div className="px-4 py-2 flex items-center justify-between bg-bg-surface2 border-b border-border">
        <div className="text-[11px] uppercase tracking-wider font-bold text-text-2 inline-flex items-center gap-2">
          <Users2 className="w-3.5 h-3.5" strokeWidth={2.4} />
          Kurye Kırılımı — {couriers.length} kişi
          {totals.support_count > 0 && (
            <span className="text-[10px] text-orange-700 bg-orange-50 px-1.5 py-0.5 rounded-md border border-orange-200">
              {totals.support_count} destek
            </span>
          )}
        </div>
        <a
          href={`/restoranlar/${restaurantId}?ay=${encodeURIComponent(period)}`}
          className="text-[11px] text-brand hover:underline inline-flex items-center gap-1 font-semibold"
        >
          <Building2 className="w-3 h-3" strokeWidth={2.4} />
          Restoran sayfasına git
        </a>
      </div>
      <table className="w-full text-[12.5px]">
        <thead className="bg-bg-surface text-text-3 text-[10px] uppercase tracking-wider">
          <tr>
            <th className="text-left px-3 py-2 font-bold">Kurye</th>
            <th className="text-left px-3 py-2 font-bold">Rol</th>
            <th className="text-right px-3 py-2 font-bold">Gün</th>
            <th className="text-right px-3 py-2 font-bold">Saat</th>
            <th className="text-right px-3 py-2 font-bold">Paket</th>
            <th className="text-left px-3 py-2 font-bold">Hesap</th>
            <th className="text-right px-3 py-2 font-bold">KDV Hariç</th>
            <th className="text-right px-3 py-2 font-bold">KDV Dahil</th>
          </tr>
        </thead>
        <tbody>
          {couriers.map((c, idx) => (
            <CourierRow key={c.personnel_id ?? idx} c={c} />
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-brand/30 bg-brand-soft/30 font-semibold">
            <td colSpan={2} className="px-3 py-2 text-text text-[11.5px]">
              Restoran toplamı
            </td>
            <td className="px-3 py-2 text-right tabular-nums text-text-2">
              {totals.total_working_days}
            </td>
            <td className="px-3 py-2 text-right tabular-nums text-text-2">
              {n(totals.total_hours, 1)}
            </td>
            <td className="px-3 py-2 text-right tabular-nums text-text-2">
              {totals.total_packages}
            </td>
            <td className="px-3 py-2 text-text-3 text-[10.5px]">
              KDV %{totals.vat_rate}
            </td>
            <td className="px-3 py-2 text-right font-mono text-text tabular-nums">
              {m(totals.total_billing_excl_vat)}
            </td>
            <td className="px-3 py-2 text-right font-display text-brand text-[14px] tabular-nums">
              {m(totals.total_billing_incl_vat)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function CourierRow({ c }: { c: CourierBilling }) {
  const isJoker = (c.role ?? '').toLowerCase().includes('joker');
  const isManager =
    c.role === 'Bölge Müdürü' || c.role === 'Kaptan' || c.role === 'Restoran Takım Şefi';

  return (
    <tr className="border-t border-border/60 hover:bg-cream-50/70 transition align-top">
      <td className="px-3 py-2">
        <div className="font-medium text-text text-[12.5px]">{c.full_name ?? '—'}</div>
        <div className="text-[10px] text-text-3 font-mono">{c.person_code ?? ''}</div>
      </td>
      <td className="px-3 py-2">
        <div className="flex flex-col gap-1">
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold inline-block w-fit ${
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
            <span className="px-2 py-0.5 rounded-full text-[9.5px] font-semibold bg-orange-50 text-orange-700 border border-orange-200 inline-block w-fit">
              ↪ Destek
            </span>
          )}
        </div>
      </td>
      <td className="px-3 py-2 text-right tabular-nums text-text-2">{c.working_days}</td>
      <td className="px-3 py-2 text-right tabular-nums text-text-2">{n(c.total_hours, 1)}</td>
      <td className="px-3 py-2 text-right tabular-nums text-text-2">{c.total_packages}</td>
      <td className="px-3 py-2 text-[10.5px] text-text-3">
        {c.billing_breakdown.length === 0 ? (
          <span>—</span>
        ) : (
          <div className="space-y-0.5">
            {c.billing_breakdown.map((line, i) => (
              <div key={i} className="leading-tight">
                {line.label}{' '}
                {line.amount !== 0 && (
                  <span className="text-text-2 font-mono">
                    = {m(line.amount)} ₺
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </td>
      <td className="px-3 py-2 text-right font-mono tabular-nums text-text">
        {m(c.billing_excl_vat)}
      </td>
      <td className="px-3 py-2 text-right font-display font-semibold text-brand text-[13.5px] tabular-nums">
        {m(c.billing_incl_vat)}
      </td>
    </tr>
  );
}
