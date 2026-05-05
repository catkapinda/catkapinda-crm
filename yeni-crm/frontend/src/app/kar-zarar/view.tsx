'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  ArrowDownToLine, ArrowUpRight, ArrowDownRight, Building2, Coins,
  Filter, PieChart, Receipt, Search, TrendingDown, TrendingUp,
  Wallet,
} from 'lucide-react';

import type { DashboardAnalytics } from '@/lib/api';

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

function k(value: number | null | undefined): string {
  if (value == null) return '—';
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return value.toLocaleString('tr-TR', { maximumFractionDigits: 0 });
}

type SortKey = 'brand' | 'invoiced' | 'cost' | 'profit' | 'margin' | 'couriers';
type SortDir = 'asc' | 'desc';

export function KarZararView({
  analytics, period,
}: {
  analytics: DashboardAnalytics;
  period: string;
}) {
  const [sortKey, setSortKey] = useState<SortKey>('profit');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [search, setSearch] = useState('');

  const totalRev = analytics.invoiced_kdv_haric;
  const totalCost = analytics.total_costs;
  const netProfit = analytics.net_profit;
  const marginPct = analytics.margin_pct;

  // Restoran bazlı kâr-zarar
  // Her restoranın kâr = invoiced - net_paid - allocated_management_share
  // Yönetim maliyeti restoranlar arasında (kurye sayısına göre) paylaştırılır
  const totalCouriers = analytics.by_restaurant.reduce(
    (s, r) => s + r.courier_count, 0
  );
  const mgmtPerCourier = totalCouriers > 0
    ? analytics.total_management_salary / totalCouriers
    : 0;

  const restaurantRows = useMemo(() => {
    const rows = analytics.by_restaurant.map((r) => {
      const allocated_mgmt = r.courier_count * mgmtPerCourier;
      const cost = r.net_paid + allocated_mgmt;
      const profit = r.invoiced - cost;
      const margin = r.invoiced > 0 ? (profit / r.invoiced) * 100 : 0;
      return {
        ...r,
        allocated_mgmt,
        cost,
        profit,
        margin,
      };
    });

    const q = search.trim().toLocaleLowerCase('tr-TR');
    let filtered = rows;
    if (q) {
      filtered = rows.filter((r) =>
        `${r.brand ?? ''} ${r.branch ?? ''}`.toLocaleLowerCase('tr-TR').includes(q)
      );
    }

    return [...filtered].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1;
      switch (sortKey) {
        case 'brand': return dir * (a.brand ?? '').localeCompare(b.brand ?? '', 'tr');
        case 'invoiced': return dir * (a.invoiced - b.invoiced);
        case 'cost': return dir * (a.cost - b.cost);
        case 'profit': return dir * (a.profit - b.profit);
        case 'margin': return dir * (a.margin - b.margin);
        case 'couriers': return dir * (a.courier_count - b.courier_count);
      }
    });
  }, [analytics.by_restaurant, mgmtPerCourier, sortKey, sortDir, search]);

  // Gider kırılımı (donut chart için)
  const costBreakdown = [
    {
      label: 'Kuryelere Net Ödeme',
      value: analytics.total_courier_net,
      color: '#0F52BA',
    },
    {
      label: 'Yönetim Maaşları',
      value: analytics.total_management_salary,
      color: '#9A3412',
    },
    {
      label: 'KDV Tevkifatı',
      value: analytics.tevkifat_total,
      color: '#F59E0B',
    },
  ];

  // Trend için aylar
  const trend = analytics.revenue_trend;

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  }

  return (
    <>
      {/* HEADER */}
      <header className="flex justify-between items-end gap-5 flex-wrap mb-6">
        <div>
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Finans · <span className="text-brand font-semibold">Kâr-Zarar Raporu</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            {formatPeriod(period)} Kâr-Zarar
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            Brüt fatura − tüm giderler · {analytics.by_restaurant.length} restoran ·
            net kâr <strong className={netProfit >= 0 ? 'text-green-700' : 'text-red-700'}>
              {m(netProfit)} ₺
            </strong> ({marginPct.toFixed(1)}% marj)
          </div>
        </div>
        <button className="px-4 py-2 rounded-xl bg-white border border-border text-text-2 text-[13px] font-semibold shadow-xs hover:border-border-strong transition flex items-center gap-1.5">
          <ArrowDownToLine className="w-4 h-4" strokeWidth={2.2} /> Excel'e aktar
        </button>
      </header>

      {/* HERO STRIP — 4 KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <KpiCard
          icon={<Receipt className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="brand"
          label="Toplam Gelir"
          value={m(totalRev)}
          suffix="₺"
          sub="Brüt fatura (KDV hariç)"
        />
        <KpiCard
          icon={<Wallet className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="warn"
          label="Toplam Gider"
          value={m(totalCost)}
          suffix="₺"
          sub={`Kurye + yönetim`}
        />
        <KpiCard
          icon={netProfit >= 0
            ? <TrendingUp className="w-3.5 h-3.5" strokeWidth={2.2} />
            : <TrendingDown className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent={netProfit >= 0 ? 'success' : 'danger'}
          label="Net Kâr"
          value={m(netProfit)}
          suffix="₺"
          sub={netProfit >= 0 ? 'aylık operasyonel kâr' : 'aylık net zarar'}
        />
        <KpiCard
          icon={<Coins className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="purple"
          label="Marj Oranı"
          value={`%${marginPct.toFixed(1)}`}
          sub="kâr / gelir"
        />
      </div>

      {/* TREND + GIDER KIRILIM */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-5">
        {/* Trend (6 aylık gelir vs gider) */}
        <div className="lg:col-span-2 bg-white border border-border rounded-2xl p-5 shadow-sm">
          <div className="flex items-baseline justify-between mb-4">
            <div>
              <h2 className="font-display text-[15px] font-semibold text-text">
                6 Aylık Trend
              </h2>
              <p className="text-[12px] text-text-3 mt-0.5">
                Gelir, gider ve kâr karşılaştırması (KDV hariç)
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <Legend dot="#0F52BA" label="Gelir" />
              <Legend dot="#EF4444" label="Gider" />
              <Legend dot="#10B981" label="Kâr" />
            </div>
          </div>
          <TrendChart trend={trend} />
        </div>

        {/* Gider kırılımı donut */}
        <div className="bg-white border border-border rounded-2xl p-5 shadow-sm">
          <div className="text-[11px] uppercase tracking-[0.08em] text-text-3 font-bold mb-3 flex items-center gap-1.5">
            <PieChart className="w-3.5 h-3.5" strokeWidth={2.2} /> Gider Kırılımı
          </div>
          <DonutChart segments={costBreakdown} centerValue={`${k(totalCost)} ₺`} centerLabel="Toplam" />
        </div>
      </div>

      {/* GELIR / GIDER DETAY */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
        {/* Gelir kalemleri */}
        <div className="bg-white border border-border rounded-2xl p-5 shadow-sm">
          <div className="flex items-center gap-1.5 mb-3">
            <ArrowUpRight className="w-4 h-4 text-green-700" strokeWidth={2.2} />
            <h2 className="font-display text-[15px] font-semibold text-text">Gelir Kalemleri</h2>
          </div>
          <div className="space-y-2">
            <DetailRow
              label="Brüt Fatura (KDV hariç)"
              value={m(analytics.invoiced_kdv_haric)}
              accent="text-text"
            />
            <DetailRow
              label={`KDV (%20)`}
              value={`+${m(analytics.invoiced_kdv_dahil - analytics.invoiced_kdv_haric)}`}
              accent="text-text-2"
            />
            <div className="pt-2 border-t border-border">
              <DetailRow
                label="KDV Dahil Toplam"
                value={m(analytics.invoiced_kdv_dahil)}
                bold
              />
            </div>
            <DetailRow
              label="− KDV Tevkifatı (devlete giden)"
              value={`−${m(analytics.tevkifat_total)}`}
              accent="text-orange-700"
            />
            <div className="pt-2 border-t border-border">
              <DetailRow
                label="Net Tahsil Edilebilir"
                value={m(analytics.invoiced_kdv_dahil - analytics.tevkifat_total)}
                accent="text-brand"
                bold
              />
            </div>
          </div>
        </div>

        {/* Gider kalemleri */}
        <div className="bg-white border border-border rounded-2xl p-5 shadow-sm">
          <div className="flex items-center gap-1.5 mb-3">
            <ArrowDownRight className="w-4 h-4 text-red-700" strokeWidth={2.2} />
            <h2 className="font-display text-[15px] font-semibold text-text">Gider Kalemleri</h2>
          </div>
          <div className="space-y-2">
            <DetailRow
              label="Kuryelere Net Ödeme"
              value={m(analytics.total_courier_net)}
              accent="text-text"
            />
            <DetailRow
              label="Yönetim Maaşları (BM · Kaptan · RTS · Joker)"
              value={m(analytics.total_management_salary)}
              accent="text-text"
            />
            <div className="pt-2 border-t border-border">
              <DetailRow
                label="Toplam Operasyonel Gider"
                value={m(analytics.total_costs)}
                accent="text-red-700"
                bold
              />
            </div>
            <div className="pt-2 mt-1">
              <DetailRow
                label="Net Operasyonel Kâr"
                value={m(netProfit)}
                accent={netProfit >= 0 ? 'text-green-700' : 'text-red-700'}
                bold
              />
              <div className="flex justify-between text-[11px] text-text-3 mt-1">
                <span>Marj</span>
                <span className={`font-mono font-bold ${netProfit >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  %{marginPct.toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* RESTORAN BAZLI KÂR-ZARAR */}
      <div className="bg-white border border-border rounded-2xl shadow-sm overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-border bg-cream-50/60">
          <div>
            <h2 className="font-display text-[15px] font-semibold text-text flex items-center gap-2">
              <Building2 className="w-4 h-4 text-brand" strokeWidth={2.2} />
              Restoran Bazlı Kâr-Zarar
            </h2>
            <p className="text-[11.5px] text-text-3 mt-0.5">
              Yönetim gideri kurye sayısına göre orantılı dağıtılmıştır
              ({m(mgmtPerCourier)} ₺/kurye)
            </p>
          </div>
          <div className="relative flex items-center">
            <Search className="w-3.5 h-3.5 absolute left-2.5 text-text-3" strokeWidth={2.2} />
            <input
              type="search"
              placeholder="Restoran ara…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-lg border border-border text-sm w-56 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
            />
          </div>
        </div>

        <table className="w-full text-[13px]">
          <thead className="bg-bg-surface text-text-3 text-[10.5px] uppercase tracking-[0.08em] border-b border-border">
            <tr>
              <SortableTH label="Restoran" k="brand" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('brand')} align="left" />
              <SortableTH label="Kurye" k="couriers" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('couriers')} align="right" />
              <SortableTH label="Gelir" k="invoiced" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('invoiced')} align="right" />
              <SortableTH label="Kurye Net" k="cost" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('cost')} align="right" />
              <th className="text-right px-3 py-3 font-bold text-text-3">Yönetim Payı</th>
              <SortableTH label="Net Kâr" k="profit" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('profit')} align="right" accent />
              <SortableTH label="Marj %" k="margin" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('margin')} align="right" />
            </tr>
          </thead>
          <tbody>
            {restaurantRows.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center text-text-3 py-12 italic">
                  Sonuç yok
                </td>
              </tr>
            ) : restaurantRows.map((r, idx) => (
              <tr key={r.id} className="border-t border-border/70 hover:bg-cream-50/70 transition group">
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2.5">
                    <span className="text-[10.5px] font-mono text-text-3 w-5">#{idx + 1}</span>
                    <span className="w-1 h-7 rounded-full bg-brand/40" />
                    <Link
                      href={`/restoranlar/${r.id}?ay=${period}`}
                      className="min-w-0 hover:text-brand transition"
                    >
                      <div className="font-semibold text-[13px] truncate">{r.brand}</div>
                      {r.branch && <div className="text-[10.5px] text-text-3 truncate">{r.branch}</div>}
                    </Link>
                  </div>
                </td>
                <td className="px-3 py-2.5 text-right num font-mono text-[12px] text-text-2 tabular-nums">
                  {r.courier_count}
                </td>
                <td className="px-3 py-2.5 text-right num font-mono text-[12.5px] text-text tabular-nums">
                  {m(r.invoiced)}
                </td>
                <td className="px-3 py-2.5 text-right num font-mono text-[12.5px] text-red-700 tabular-nums">
                  −{m(r.net_paid)}
                </td>
                <td className="px-3 py-2.5 text-right num font-mono text-[11.5px] text-orange-700 tabular-nums">
                  −{m(r.allocated_mgmt)}
                </td>
                <td className={`px-3 py-2.5 text-right num font-display font-bold text-[14px] tabular-nums ${
                  r.profit >= 0 ? 'bg-green-50/60 text-green-700' : 'bg-red-50/60 text-red-700'
                } group-hover:opacity-90 transition`}>
                  {r.profit >= 0 ? '+' : ''}{m(r.profit)}
                </td>
                <td className="px-3 py-2.5 text-right">
                  <span className={`inline-block px-2 py-0.5 rounded-md text-[11px] font-bold ${
                    r.margin >= 30 ? 'bg-green-100 text-green-700' :
                    r.margin >= 15 ? 'bg-yellow-100 text-yellow-700' :
                    r.margin >= 0 ? 'bg-orange-100 text-orange-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    %{r.margin.toFixed(1)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-brand/30 bg-gradient-to-r from-brand-soft/40 to-transparent font-semibold">
              <td className="px-4 py-3 text-text text-[12.5px]">
                Toplam ({restaurantRows.length} restoran)
              </td>
              <td className="px-3 py-3 text-right num font-mono tabular-nums">
                {restaurantRows.reduce((s, r) => s + r.courier_count, 0)}
              </td>
              <td className="px-3 py-3 text-right num font-mono text-text tabular-nums">
                {m(restaurantRows.reduce((s, r) => s + r.invoiced, 0))}
              </td>
              <td className="px-3 py-3 text-right num font-mono text-red-700 tabular-nums">
                −{m(restaurantRows.reduce((s, r) => s + r.net_paid, 0))}
              </td>
              <td className="px-3 py-3 text-right num font-mono text-orange-700 tabular-nums">
                −{m(restaurantRows.reduce((s, r) => s + r.allocated_mgmt, 0))}
              </td>
              <td className={`px-3 py-3 text-right font-display text-[15px] num tabular-nums ${
                restaurantRows.reduce((s, r) => s + r.profit, 0) >= 0
                  ? 'bg-green-50 text-green-700'
                  : 'bg-red-50 text-red-700'
              }`}>
                {m(restaurantRows.reduce((s, r) => s + r.profit, 0))}
              </td>
              <td className="px-3 py-3 text-right num font-mono text-text-2 tabular-nums text-[12px]">
                ortalama
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </>
  );
}

// ─── KPI Card ─────────────────────────────────────────────
function KpiCard({
  icon, accent, label, value, suffix, sub,
}: {
  icon: React.ReactNode;
  accent: 'brand' | 'success' | 'danger' | 'warn' | 'purple';
  label: string;
  value: string;
  suffix?: string;
  sub: string;
}) {
  const ringMap: Record<string, string> = {
    brand: 'bg-gradient-to-b from-brand to-blue-400',
    success: 'bg-gradient-to-b from-green-500 to-emerald-300',
    danger: 'bg-gradient-to-b from-red-500 to-orange-400',
    warn: 'bg-gradient-to-b from-orange-500 to-amber-300',
    purple: 'bg-gradient-to-b from-purple-500 to-fuchsia-300',
  };
  const iconBgMap: Record<string, string> = {
    brand: 'bg-brand-soft text-brand',
    success: 'bg-green-100 text-green-700',
    danger: 'bg-red-100 text-red-700',
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
        {suffix && <span className="text-[14px] font-medium text-text-3 ml-1">{suffix}</span>}
      </div>
      <div className="text-[11px] text-text-3 mt-2 font-medium">{sub}</div>
    </div>
  );
}

// ─── Detail Row ────────────────────────────────────────────
function DetailRow({
  label, value, accent, bold,
}: { label: string; value: string; accent?: string; bold?: boolean }) {
  return (
    <div className="flex justify-between items-baseline text-[13px]">
      <span className={`${bold ? 'font-semibold' : 'font-medium'} text-text-2`}>{label}</span>
      <span className={`font-mono tabular-nums ${bold ? 'font-bold text-[15px]' : 'font-semibold text-[13.5px]'} ${accent ?? 'text-text'}`}>
        {value} ₺
      </span>
    </div>
  );
}

// ─── Sortable TH ───────────────────────────────────────────
function SortableTH({
  label, k, sortKey, sortDir, onClick, align, accent,
}: {
  label: string;
  k: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
  onClick: () => void;
  align: 'left' | 'right';
  accent?: boolean;
}) {
  const active = sortKey === k;
  const arrow = active ? (sortDir === 'asc' ? '▲' : '▼') : '';
  return (
    <th
      className={`px-3 py-3 font-bold cursor-pointer hover:text-brand transition ${
        align === 'right' ? 'text-right' : 'text-left'
      } ${accent ? 'bg-brand-soft/50 text-brand' : ''}`}
      onClick={onClick}
    >
      {label} <span className="text-[8px] opacity-60">{arrow}</span>
    </th>
  );
}

// ─── Legend Dot ───────────────────────────────────────────
function Legend({ dot, label }: { dot: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-text-2">
      <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: dot }} />
      <span>{label}</span>
    </div>
  );
}

// ─── Donut Chart ──────────────────────────────────────────
function DonutChart({
  segments, centerValue, centerLabel,
}: {
  segments: { label: string; value: number; color: string }[];
  centerValue: string;
  centerLabel: string;
}) {
  const total = segments.reduce((s, x) => s + Math.max(0, x.value), 0);
  const r = 56;
  const circumference = 2 * Math.PI * r;

  let offset = 0;
  const arcs = segments.map((s, i) => {
    const portion = total > 0 ? Math.max(0, s.value) / total : 0;
    const length = portion * circumference;
    const dash = `${length} ${circumference}`;
    const dashOffset = -offset;
    offset += length;
    return { ...s, dash, dashOffset, portion, key: i };
  });

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-[140px] h-[140px]">
        <svg width="140" height="140" viewBox="0 0 140 140">
          <circle cx="70" cy="70" r={r} fill="none" stroke="rgba(0,0,0,0.05)" strokeWidth="14" />
          {arcs.map((a) => (
            <circle
              key={a.key}
              cx="70" cy="70" r={r}
              fill="none"
              stroke={a.color}
              strokeWidth="14"
              strokeDasharray={a.dash}
              strokeDashoffset={a.dashOffset}
              strokeLinecap="round"
              transform="rotate(-90 70 70)"
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-[10px] uppercase tracking-wider text-text-3 font-semibold">
            {centerLabel}
          </div>
          <div className="font-display text-[16px] font-bold tracking-tight num tabular-nums">
            {centerValue}
          </div>
        </div>
      </div>
      <div className="w-full mt-3 space-y-1.5">
        {arcs.map((a) => (
          <div key={a.key} className="flex items-center gap-2 text-[11.5px]">
            <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: a.color }} />
            <span className="text-text-2 flex-1 truncate">{a.label}</span>
            <span className="font-mono font-semibold tabular-nums text-text">
              {k(a.value)} ₺
            </span>
            <span className="font-mono text-text-3 tabular-nums w-10 text-right">
              %{(a.portion * 100).toFixed(1)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Trend Chart ──────────────────────────────────────────
function TrendChart({ trend }: { trend: { period: string; invoiced: number; net_paid: number }[] }) {
  if (trend.length === 0) {
    return (
      <div className="h-[220px] flex items-center justify-center text-text-3 text-sm">
        Trend verisi yok
      </div>
    );
  }

  // Her ay için kâr hesapla (gelir - net_paid; basitleştirilmiş, yönetim maaşı dahil değil)
  // Burada gerçek kâr için yönetim maaşı da eklenmeli — mevcut data ile yaklaşık
  const points = trend.map((t) => ({
    period: t.period,
    invoiced: t.invoiced,
    cost: t.net_paid,
    profit: t.invoiced - t.net_paid,
  }));

  const maxValue = Math.max(...points.map((p) => Math.max(p.invoiced, p.cost, p.profit)));
  const minValue = Math.min(...points.map((p) => Math.min(p.invoiced, p.cost, p.profit, 0)));
  const range = maxValue - minValue || 1;

  const W = 600;
  const H = 220;
  const PAD = { top: 10, right: 10, bottom: 30, left: 50 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  function xOf(i: number): number {
    return PAD.left + (i / Math.max(points.length - 1, 1)) * innerW;
  }
  function yOf(v: number): number {
    return PAD.top + innerH - ((v - minValue) / range) * innerH;
  }

  function pathFor(getValue: (p: typeof points[number]) => number): string {
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xOf(i)} ${yOf(getValue(p))}`).join(' ');
  }

  const gridYs = [0, 0.25, 0.5, 0.75, 1].map((f) => PAD.top + f * innerH);

  return (
    <div className="relative">
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="overflow-visible">
        {/* Grid */}
        {gridYs.map((y, i) => (
          <line key={i} x1={PAD.left} x2={W - PAD.right} y1={y} y2={y}
            stroke="rgba(0,0,0,0.05)" strokeDasharray="3 3" />
        ))}

        {/* Paths */}
        <path d={pathFor((p) => p.invoiced)} fill="none" stroke="#0F52BA" strokeWidth="2.5" />
        <path d={pathFor((p) => p.cost)} fill="none" stroke="#EF4444" strokeWidth="2.5" />
        <path d={pathFor((p) => p.profit)} fill="none" stroke="#10B981" strokeWidth="2.5" strokeDasharray="0" />

        {/* Points */}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={xOf(i)} cy={yOf(p.invoiced)} r="4" fill="#0F52BA" />
            <circle cx={xOf(i)} cy={yOf(p.cost)} r="4" fill="#EF4444" />
            <circle cx={xOf(i)} cy={yOf(p.profit)} r="4" fill="#10B981" />
            {/* X label */}
            <text x={xOf(i)} y={H - 8} textAnchor="middle"
              fontSize="10" fill="#8B92A7" fontFamily="JetBrains Mono">
              {p.period.slice(5, 7)}/{p.period.slice(2, 4)}
            </text>
          </g>
        ))}

        {/* Y axis labels */}
        {[0, 0.5, 1].map((f) => {
          const v = minValue + (1 - f) * range;
          return (
            <text key={f} x={PAD.left - 6} y={PAD.top + f * innerH + 4}
              textAnchor="end" fontSize="10" fill="#8B92A7" fontFamily="JetBrains Mono">
              {k(v)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
