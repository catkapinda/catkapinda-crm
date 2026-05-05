'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  Activity, ArrowDownToLine, BadgeCheck, Building2,
  ChevronDown, ChevronRight, Filter, Flame, Gem, Layers,
  PieChart, ReceiptText, Search, Sparkles, Store,
  TrendingDown, Trophy, Users, Wallet, X,
} from 'lucide-react';

import type { PayrollResult, PayrollRow } from '@/lib/api';
import { normalizeTr } from '@/lib/format';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string): string {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function tr(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

// Para tutarı — 2 ondalık zorunlu, asla yuvarlama (90.543,50)
function m(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// Kompakt para (135K, 1.2M) hero için
function kCompact(value: number | null | undefined): string {
  if (value == null) return '—';
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return tr(value, 0);
}

// Restoran ataması yoksa rolüne göre anlamlı etiket
// (Joker dış kurye; Bölge Müdürü tüm operasyondan sorumlu — hiçbiri "atanmamış" değil)
function noRestaurantLabel(role: string | null | undefined): string {
  const r = (role ?? '').trim();
  if (r === 'Joker') return 'Havuz · Esnek Atama';
  if (r === 'Bölge Müdürü') return 'Tüm Operasyon';
  if (r === 'Kaptan') return 'Tüm Operasyon';
  return '— atanmamış —';
}

const ROLE_STYLES: Record<string, string> = {
  Kurye: 'bg-brand-soft text-brand',
  Joker: 'bg-cream-100 text-yellow-800',
  'Bölge Müdürü': 'bg-text text-white',
  Kaptan: 'bg-purple-100 text-purple-800',
  'Restoran Takım Şefi': 'bg-green-100 text-green-800',
};

// Anlaşma tipi: kısa Türkçe etiket + renk
type PricingMeta = { label: string; short: string; bg: string; text: string; border: string };
const PRICING_META: Record<string, PricingMeta> = {
  hourly_only: {
    label: 'Saatlik',
    short: 'SAA',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
  },
  hourly_plus_package: {
    label: 'Saat + Prim',
    short: 'SAA+P',
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
  },
  threshold_package: {
    label: 'Eşikli Paket',
    short: 'EŞK',
    bg: 'bg-teal-50',
    text: 'text-teal-700',
    border: 'border-teal-200',
  },
  fixed_monthly: {
    label: 'Aylık Sabit',
    short: 'AY',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
  },
};

function pricingMeta(model: string | null | undefined): PricingMeta | null {
  if (!model) return null;
  return PRICING_META[model] ?? null;
}

const AVATAR_GRADIENTS = [
  'from-blue-700 to-blue-500',
  'from-blue-900 to-blue-700',
  'from-yellow-600 to-yellow-400',
  'from-slate-700 to-slate-500',
  'from-purple-700 to-purple-500',
  'from-green-700 to-green-500',
];

export function BordroView({
  payroll, period, periods,
}: {
  payroll: PayrollResult;
  period: string;
  periods: string[];
}) {
  const [search, setSearch] = useState('');
  const [restFilter, setRestFilter] = useState<string | null>(null);
  const [openRow, setOpenRow] = useState<number | null>(null);

  const restaurantOptions = useMemo(() => {
    const set = new Set<string>();
    for (const r of payroll.rows) {
      if (r.rest_brand) {
        set.add(`${r.rest_brand}${r.rest_branch ? ' · ' + r.rest_branch : ''}`);
      }
    }
    return Array.from(set).sort();
  }, [payroll.rows]);

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    return payroll.rows.filter((r) => {
      if (q) {
        const hay = `${r.full_name ?? ''} ${r.person_code ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      if (restFilter) {
        const k = `${r.rest_brand ?? ''}${r.rest_branch ? ' · ' + r.rest_branch : ''}`;
        if (k !== restFilter) return false;
      }
      return true;
    });
  }, [payroll.rows, search, restFilter]);

  const filteredBrut = filtered.reduce((s, r) => s + r.toplam_brut, 0);
  const filteredKesintiNonTev = filtered.reduce(
    (s, r) => s + r.kesinti_total + r.sabit_total,
    0,
  );
  const filteredTevkifat = filtered.reduce((s, r) => s + r.tevkifat, 0);
  const filteredNet = filtered.reduce((s, r) => s + r.net, 0);

  const profitMargin = payroll.summary.total_brut > 0
    ? (payroll.summary.total_kesinti / payroll.summary.total_brut) * 100
    : 0;

  return (
    <>
      {/* ────────────────────────────────────────────────────────────
          HERO — cinematic gradient header
         ──────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl mb-6 shadow-lg">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-dark via-brand to-blue-600" />
        <div className="absolute inset-0 opacity-30 mix-blend-overlay"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 20%, rgba(255,255,255,.4) 0%, transparent 40%), radial-gradient(circle at 80% 70%, rgba(255,200,100,.3) 0%, transparent 50%)',
          }}
        />
        <div className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        <div className="relative px-7 py-7 flex justify-between items-start gap-6 flex-wrap">
          <div className="text-white">
            <div className="text-[11px] font-medium tracking-[0.2em] uppercase text-white/70 mb-2 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-yellow-300 animate-pulse" />
              Finans · Bordro
            </div>
            <h1 className="font-display text-[42px] font-bold tracking-tight leading-none">
              {formatPeriod(period)}
            </h1>
            <div className="text-white/80 text-sm mt-2 font-medium flex items-center gap-1.5">
              <Users className="w-4 h-4" strokeWidth={2.2} />
              <strong className="text-white text-[15px]">
                {payroll.summary.courier_count}
              </strong>{' '}
              kurye · brüt{' '}
              <strong className="text-white">{m(payroll.summary.total_brut)} ₺</strong>{' '}
              → ödenecek{' '}
              <strong className="text-yellow-300">
                {m(payroll.summary.total_net)} ₺
              </strong>
            </div>
          </div>

          <div className="flex gap-2 items-center">
            <div className="flex items-center gap-1 bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-1 shadow-lg">
              {periods.slice(0, 4).map((p) => {
                const isActive = p === period;
                return (
                  <Link
                    key={p}
                    href={`/bordro?ay=${p}`}
                    className={`px-3 py-1.5 rounded-lg text-[12.5px] font-semibold transition-all ${
                      isActive
                        ? 'bg-white text-brand shadow-md scale-105'
                        : 'text-white/85 hover:bg-white/15'
                    }`}
                  >
                    {formatPeriod(p)}
                  </Link>
                );
              })}
            </div>
            <button className="px-4 py-2 rounded-xl bg-white text-brand text-[13px] font-semibold shadow-md hover:bg-yellow-50 hover:scale-105 transition-all flex items-center gap-1.5">
              <ArrowDownToLine className="w-4 h-4" strokeWidth={2.2} />
              Tüm Bordrolar
            </button>
          </div>
        </div>

        <div className="relative grid grid-cols-2 md:grid-cols-4 border-t border-white/15 backdrop-blur-sm">
          <RibbonStat
            label="Brüt"
            value={`${m(payroll.summary.total_brut)} ₺`}
            color="text-white"
          />
          <RibbonStat
            label="Kesinti"
            value={`−${m(payroll.summary.total_kesinti)} ₺`}
            color="text-red-200"
          />
          <RibbonStat
            label="Tevkifat"
            value={`−${m(payroll.summary.total_tevkifat ?? 0)} ₺`}
            color="text-orange-200"
          />
          <RibbonStat
            label="Net"
            value={`${m(payroll.summary.total_net)} ₺`}
            color="text-yellow-300"
            highlight
          />
        </div>
      </section>

      {/* ────────────────────────────────────────────────────────────
          KPI cards
         ──────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KpiCard
          label="Toplam Brüt"
          value={m(payroll.summary.total_brut)}
          suffix="₺"
          accent="brand"
          icon={<Gem className="w-4 h-4" strokeWidth={2.2} />}
          meta={`${payroll.summary.courier_count} kurye · ${kCompact(payroll.summary.total_brut)} ₺`}
        />
        <KpiCard
          label="Toplam Kesinti"
          value={m(payroll.summary.total_kesinti)}
          suffix="₺"
          accent="danger"
          icon={<ReceiptText className="w-4 h-4" strokeWidth={2.2} />}
          meta={`tevkifat ${m(payroll.summary.total_tevkifat ?? 0)} ₺ dahil`}
        />
        <KpiCard
          label="Net Ödenecek"
          value={m(payroll.summary.total_net)}
          suffix="₺"
          accent="success"
          icon={<Wallet className="w-4 h-4" strokeWidth={2.2} />}
          meta="kuryelere transfer"
        />
        <KpiCard
          label="Kesinti Oranı"
          value={`%${profitMargin.toFixed(1)}`}
          accent="warn"
          icon={<TrendingDown className="w-4 h-4" strokeWidth={2.2} />}
          meta="brütün kesintisi"
        />
      </div>

      {/* ────────────────────────────────────────────────────────────
          GRAFIKLER
         ──────────────────────────────────────────────────────────── */}
      <PayrollCharts payroll={payroll} />

      {/* ────────────────────────────────────────────────────────────
          FILTRELER
         ──────────────────────────────────────────────────────────── */}
      <div className="bg-white/70 backdrop-blur-sm border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2 sticky top-2 z-10">
        <div className="relative flex items-center">
          <Search className="w-4 h-4 absolute left-2.5 text-text-3" strokeWidth={2.2} />
          <input
            type="search"
            placeholder="Kurye ara…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1.5 rounded-lg border border-border text-sm w-64 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
          />
        </div>
        <div className="relative flex items-center">
          <Building2 className="w-4 h-4 absolute left-2.5 text-text-3 pointer-events-none" strokeWidth={2.2} />
          <select
            value={restFilter ?? ''}
            onChange={(e) => setRestFilter(e.target.value || null)}
            className="pl-8 pr-3 py-1.5 rounded-lg border border-border text-sm bg-white focus:outline-none focus:border-brand transition appearance-none"
          >
            <option value="">Tüm Restoranlar</option>
            {restaurantOptions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        {(search || restFilter) && (
          <button
            onClick={() => { setSearch(''); setRestFilter(null); }}
            className="text-[11px] text-text-3 hover:text-brand transition px-2 py-1 flex items-center gap-1"
          >
            <X className="w-3 h-3" strokeWidth={2.2} /> filtreleri temizle
          </button>
        )}
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto flex items-center gap-1">
          <Filter className="w-3 h-3" strokeWidth={2.2} />
          {filtered.length} sonuç · brüt{' '}
          <span className="text-brand font-mono">{m(filteredBrut)} ₺</span> · net{' '}
          <span className="text-green-700 font-mono">{m(filteredNet)} ₺</span>
        </span>
      </div>

      {/* ────────────────────────────────────────────────────────────
          TABLO — premium B2B SaaS density
         ──────────────────────────────────────────────────────────── */}
      {filtered.length === 0 ? (
        <div className="bg-bg-surface border border-border rounded-2xl p-12 text-center">
          <Search className="w-10 h-10 mx-auto text-text-3 mb-3" strokeWidth={1.5} />
          <div className="text-text-3 text-sm">Sonuç bulunamadı.</div>
        </div>
      ) : (
        <div className="bg-white border border-border rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-[13px]">
            <colgroup>
              <col className="w-[260px]" />
              <col className="w-[200px]" />
              <col className="w-[110px]" />
              <col className="w-[80px]" />
              <col />
              <col />
              <col />
              <col />
              <col className="w-[40px]" />
              <col className="w-[28px]" />
            </colgroup>
            <thead className="bg-cream-50/80 text-text-3 text-[10.5px] uppercase tracking-[0.08em] sticky top-0 z-10 backdrop-blur-md border-b border-border">
              <tr>
                <th className="text-left px-4 py-3 font-bold">Kurye</th>
                <th className="text-left px-3 py-3 font-bold">Restoran</th>
                <th className="text-right px-3 py-3 font-bold">Gün · Saat</th>
                <th className="text-right px-3 py-3 font-bold">Paket</th>
                <th className="text-right px-3 py-3 font-bold">Brüt</th>
                <th className="text-right px-3 py-3 font-bold">Kesinti</th>
                <th className="text-right px-3 py-3 font-bold">Tevkifat</th>
                <th className="text-right px-3 py-3 font-bold bg-brand-soft/60 text-brand">
                  Net
                </th>
                <th className="px-2 py-3"></th>
                <th className="px-2 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <PayrollRowItem
                  key={r.id}
                  r={r}
                  period={period}
                  open={openRow === r.id}
                  onToggle={() => setOpenRow(openRow === r.id ? null : r.id)}
                />
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-brand/30 bg-gradient-to-r from-brand-soft/50 to-transparent font-semibold">
                <td colSpan={4} className="px-4 py-3 text-text text-[12.5px]">
                  Toplam ({filtered.length} kurye)
                </td>
                <td className="px-3 py-3 text-right num font-mono text-text tabular-nums">
                  {m(filteredBrut)} ₺
                </td>
                <td className="px-3 py-3 text-right num font-mono text-red-600 tabular-nums">
                  −{m(filteredKesintiNonTev)} ₺
                </td>
                <td className="px-3 py-3 text-right num font-mono text-orange-600 tabular-nums">
                  −{m(filteredTevkifat)} ₺
                </td>
                <td className="px-3 py-3 text-right font-display text-brand text-[15px] num bg-brand-soft tabular-nums">
                  {m(filteredNet)} ₺
                </td>
                <td colSpan={2}></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </>
  );
}

function RibbonStat({
  label, value, color, highlight,
}: { label: string; value: string; color: string; highlight?: boolean }) {
  return (
    <div className={`px-5 py-3 ${highlight ? 'bg-white/10' : ''}`}>
      <div className="text-[10px] uppercase tracking-wider text-white/70 font-semibold mb-0.5">
        {label}
      </div>
      <div className={`font-mono font-bold text-[15px] tabular-nums ${color}`}>
        {value}
      </div>
    </div>
  );
}

function KpiCard({
  label, value, suffix, meta, accent, icon,
}: {
  label: string;
  value: string;
  suffix?: string;
  meta?: string;
  accent: 'brand' | 'success' | 'danger' | 'warn';
  icon?: React.ReactNode;
}) {
  const iconBgMap: Record<string, string> = {
    brand: 'bg-brand-soft text-brand',
    success: 'bg-green-100 text-green-700',
    danger: 'bg-red-100 text-red-700',
    warn: 'bg-yellow-100 text-yellow-800',
  };
  const accentBarMap: Record<string, string> = {
    brand: 'bg-gradient-to-b from-brand to-blue-400',
    success: 'bg-gradient-to-b from-green-500 to-emerald-300',
    danger: 'bg-gradient-to-b from-red-500 to-orange-400',
    warn: 'bg-gradient-to-b from-yellow-500 to-amber-300',
  };

  return (
    <div className="relative bg-white rounded-2xl px-5 py-4 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5 overflow-hidden border border-border">
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${accentBarMap[accent]}`} />
      <div className="flex items-start justify-between mb-2">
        <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold">
          {label}
        </div>
        {icon && (
          <div className={`w-8 h-8 rounded-lg ${iconBgMap[accent]} flex items-center justify-center`}>
            {icon}
          </div>
        )}
      </div>
      <div className="font-display text-[26px] font-bold tracking-tight leading-none num tabular-nums">
        {value}
        {suffix && (
          <span className="text-base font-medium text-text-3 ml-1">
            {suffix}
          </span>
        )}
      </div>
      {meta && (
        <div className="text-[11px] text-text-3 mt-2 font-medium">{meta}</div>
      )}
    </div>
  );
}

function PayrollRowItem({
  r, period, open, onToggle,
}: {
  r: PayrollRow;
  period: string;
  open: boolean;
  onToggle: () => void;
}) {
  const initials = (r.full_name ?? '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  const grad = AVATAR_GRADIENTS[(r.id ?? 0) % AVATAR_GRADIENTS.length];
  const role = r.role ?? '?';
  const roleStyle = ROLE_STYLES[role] ?? 'bg-bg-surface2 text-text-2';
  const totalKesinti = r.kesinti_total + r.sabit_total;

  return (
    <>
      <tr
        className={`border-t border-border/70 transition cursor-pointer group ${
          open ? 'bg-brand-soft/20' : 'hover:bg-cream-50/70'
        }`}
        onClick={onToggle}
      >
        {/* Kurye — kompakt tek satır */}
        <td className="px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <div
              className={`w-8 h-8 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-[11px] flex-shrink-0 shadow ring-2 ring-white`}
            >
              {initials || '?'}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="font-semibold text-text text-[13px] truncate">
                  {r.full_name ?? '—'}
                </span>
                {r.is_fixed_salary && (
                  <span
                    className="px-1.5 py-px rounded text-[9.5px] font-bold bg-brand-soft text-brand inline-flex items-center gap-0.5 flex-shrink-0"
                    title="Sabit aylık"
                  >
                    <BadgeCheck className="w-2.5 h-2.5" strokeWidth={2.5} />
                    SBT
                  </span>
                )}
              </div>
              <div className="flex gap-1.5 items-center text-[10.5px] mt-0.5">
                <span className="font-mono text-text-3">
                  {r.person_code ?? ''}
                </span>
                <span className="text-text-3">·</span>
                <span className={`font-medium ${roleStyle.replace('bg-', 'text-').split(' ').filter(c => c.startsWith('text-')).join(' ') || 'text-text-2'}`}>
                  {role}
                </span>
              </div>
            </div>
          </div>
        </td>

        {/* Restoran — anlaşma tipi badge'i ile */}
        <td className="px-3 py-2.5">
          {r.rest_brand ? (
            <div className="text-[12.5px] text-text truncate flex items-center gap-1.5">
              <span className="w-1 h-4 rounded-full bg-brand/40" />
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="truncate font-medium">{r.rest_brand}</span>
                  {(() => {
                    const pm = pricingMeta(r.pricing_model);
                    if (!pm) return null;
                    return (
                      <span
                        className={`px-1.5 py-px rounded text-[9.5px] font-bold ${pm.bg} ${pm.text} border ${pm.border} inline-flex flex-shrink-0`}
                        title={pm.label}
                      >
                        {pm.short}
                      </span>
                    );
                  })()}
                </div>
                {r.rest_branch && (
                  <div className="text-[10.5px] text-text-3 truncate">
                    {r.rest_branch}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-[12.5px] flex items-center gap-1.5">
              <span className="w-1 h-4 rounded-full bg-text-3/30" />
              <span className="text-text-3 font-medium italic">
                {noRestaurantLabel(r.role)}
              </span>
            </div>
          )}
        </td>

        {/* Gün · Saat — tek satır kompakt */}
        <td className="px-3 py-2.5 text-right">
          <div className="font-mono text-[12px] text-text tabular-nums">
            <strong>{r.ana_days}</strong>
            {r.destek_days > 0 && (
              <span className="text-orange-600 font-semibold">+{r.destek_days}</span>
            )}
            <span className="text-text-3 mx-1">·</span>
            <span className="text-text-2">{tr(r.ana_hours, 0)}</span>
            <span className="text-text-3 text-[10px] ml-0.5">sa</span>
          </div>
        </td>

        {/* Paket */}
        <td className="px-3 py-2.5 text-right num font-mono text-[12px] text-text-2 tabular-nums">
          {r.ana_packages > 0 ? tr(r.ana_packages) : <span className="text-text-3">—</span>}
        </td>

        {/* Brüt */}
        <td className="px-3 py-2.5 text-right">
          <div className="num font-mono font-semibold text-[13px] tabular-nums text-text">
            {m(r.toplam_brut)}
          </div>
          {r.kaptan_bonus > 0 && (
            <div className="text-[9.5px] text-green-700 font-semibold">
              +kaptan {m(r.kaptan_bonus)}
            </div>
          )}
        </td>

        {/* Kesinti */}
        <td className="px-3 py-2.5 text-right num font-mono text-red-600 tabular-nums text-[12.5px]">
          {totalKesinti > 0 ? `−${m(totalKesinti)}` : <span className="text-text-3">—</span>}
        </td>

        {/* Tevkifat */}
        <td className="px-3 py-2.5 text-right num font-mono text-orange-600 tabular-nums text-[12.5px]">
          {r.tevkifat > 0 ? `−${m(r.tevkifat)}` : <span className="text-text-3">—</span>}
        </td>

        {/* Net — accent column */}
        <td className={`px-3 py-2.5 text-right num font-display font-bold text-[14.5px] tabular-nums ${
          open ? 'bg-brand-soft text-brand-dark' : 'bg-brand-soft/35 text-brand group-hover:bg-brand-soft'
        } transition-colors`}>
          {m(r.net)}
        </td>

        {/* PDF download */}
        <td
          className="px-1 py-2.5 text-center"
          onClick={(e) => e.stopPropagation()}
        >
          <a
            href={`/api/payroll/${r.id}/pdf?period=${encodeURIComponent(period)}`}
            download
            rel="noopener"
            className="text-text-3 hover:text-brand inline-flex items-center justify-center w-7 h-7 rounded-md hover:bg-brand-soft transition"
            title="PDF bordro indir"
          >
            <ArrowDownToLine className="w-3.5 h-3.5" strokeWidth={2.2} />
          </a>
        </td>

        {/* Toggle */}
        <td className="px-1 py-2.5 text-text-3 w-7">
          {open ? (
            <ChevronDown className="w-4 h-4 text-brand" strokeWidth={2.2} />
          ) : (
            <ChevronRight className="w-4 h-4" strokeWidth={2.2} />
          )}
        </td>
      </tr>

      {open && (
        <tr className="bg-gradient-to-br from-cream-50 to-white border-b-2 border-brand/20">
          <td colSpan={10} className="px-5 py-5">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-[12px]">
              {/* Brüt detay */}
              <div className="bg-white rounded-xl p-4 border border-border shadow-sm">
                <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-3 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5" strokeWidth={2.2} /> Brüt Hesabı
                </div>
                {/* Anlaşma tipi açıklaması */}
                {(() => {
                  const pm = pricingMeta(r.pricing_model);
                  if (!pm || r.is_fixed_salary) return null;
                  const formulaText: Record<string, string> = {
                    hourly_only: 'Çalışılan saat × restoranın saatlik tarifesi',
                    hourly_plus_package: 'Saat × saatlik tarife + paket × paket primi',
                    threshold_package: 'Saat × saatlik + paket × eşikli tarife (eşik aşılırsa yüksek)',
                    fixed_monthly: 'Restoranın aylık sabit ücreti, ana kuryeye yazılır',
                  };
                  return (
                    <div className={`mb-3 p-2 rounded-lg ${pm.bg} border ${pm.border} flex items-start gap-2`}>
                      <span className={`px-1.5 py-px rounded text-[10px] font-bold ${pm.text} bg-white/80 border ${pm.border} flex-shrink-0`}>
                        {pm.label}
                      </span>
                      <span className={`text-[11px] ${pm.text} leading-snug`}>
                        {formulaText[r.pricing_model || ''] || 'Restoranın anlaşma tipine göre hesap'}
                      </span>
                    </div>
                  );
                })()}
                {r.is_fixed_salary && (
                  <div className="mb-3 p-2 rounded-lg bg-brand-soft border border-brand-border flex items-start gap-2">
                    <span className="px-1.5 py-px rounded text-[10px] font-bold text-brand bg-white/80 border border-brand-border flex-shrink-0">
                      Sabit Aylık Personel
                    </span>
                    <span className="text-[11px] text-brand leading-snug">
                      Saat/paket tarifesi uygulanmaz, monthly_fixed_cost esas alınır
                    </span>
                  </div>
                )}
                <div className="space-y-1.5">
                  <DetailRow
                    label={r.is_fixed_salary ? 'Sabit aylık' : 'Ana atama'}
                    value={`${m(r.ana_brut)} ₺`}
                  />
                  {r.ekstra_mesai_brut > 0 && (
                    <DetailRow
                      label={`Bayram/ekstra mesai (${r.ekstra_mesai_days} gün)`}
                      value={`+${m(r.ekstra_mesai_brut)} ₺`}
                      color="text-purple-700"
                    />
                  )}
                  {r.destek_brut > 0 && (
                    <DetailRow
                      label={`Destek (${r.destek_days} gün)`}
                      value={`+${m(r.destek_brut)} ₺`}
                      color="text-orange-700"
                    />
                  )}
                  {r.kaptan_bonus > 0 && (
                    <DetailRow
                      label="Kaptan bonusu"
                      value={`+${m(r.kaptan_bonus)} ₺`}
                      color="text-green-700"
                    />
                  )}
                  <div className="flex justify-between pt-2 border-t border-border font-bold">
                    <span>Toplam Brüt</span>
                    <span className="num font-mono">{m(r.toplam_brut)} ₺</span>
                  </div>
                </div>
                {r.destek_lines.length > 0 && (
                  <div className="mt-3 bg-orange-50 border border-orange-200 rounded-lg p-2.5 space-y-1.5">
                    <div className="text-[10.5px] uppercase tracking-wider text-orange-700 font-bold flex items-center gap-1">
                      <Sparkles className="w-3 h-3" /> Destek Vardiyaları
                    </div>
                    {r.destek_lines.map((d, i) => {
                      const pm = pricingMeta(d.pricing_model);
                      const restName = d.rest_brand
                        ? `${d.rest_brand}${d.rest_branch ? ' · ' + d.rest_branch : ''}`
                        : `Restoran #${d.restaurant_id}`;
                      return (
                        <div key={i} className="flex items-center justify-between gap-2 text-[11px]">
                          <div className="flex items-center gap-1.5 min-w-0 flex-1">
                            <span className="text-text-2 truncate font-medium">{restName}</span>
                            {pm && (
                              <span className={`px-1 py-px rounded text-[9px] font-bold ${pm.bg} ${pm.text} border ${pm.border} flex-shrink-0`}>
                                {pm.short}
                              </span>
                            )}
                          </div>
                          <div className="text-text-3 font-mono text-[10.5px] flex-shrink-0">
                            {d.days}g · {tr(d.hours, 0)}sa · {d.packages}pk
                          </div>
                          <div className="font-mono font-semibold text-orange-700 flex-shrink-0 min-w-[70px] text-right">
                            +{m(d.amount)} ₺
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Sabit kesintiler */}
              <div className="bg-white rounded-xl p-4 border border-border shadow-sm">
                <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-3 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" strokeWidth={2.2} /> Sabit Kesintiler
                </div>
                <div className="space-y-1.5">
                  {r.motor_taksit > 0 && (
                    <DetailRow label="Motor Satış Taksiti" value={`−${m(r.motor_taksit)} ₺`} color="text-red-600" />
                  )}
                  {r.motor_kira > 0 && (
                    <DetailRow
                      label="Motor Kirası"
                      value={`−${m(r.motor_kira)} ₺`}
                      color="text-red-600"
                    />
                  )}
                  {r.muhasebe > 0 && (
                    <DetailRow label="ÇK Muhasebe Bedeli" value={`−${m(r.muhasebe)} ₺`} color="text-red-600" />
                  )}
                  {r.sirket_acilis > 0 && (
                    <DetailRow label="Şirket Açılışı (1×)" value={`−${m(r.sirket_acilis)} ₺`} color="text-red-600" />
                  )}
                  {r.sabit_total === 0 && (
                    <div className="text-text-3 italic">— sabit kesinti yok —</div>
                  )}
                  <div className="flex justify-between pt-2 border-t border-border font-bold">
                    <span>Sabit Toplam</span>
                    <span className="num font-mono text-red-600">−{m(r.sabit_total)} ₺</span>
                  </div>
                </div>
              </div>

              {/* Manuel + zimmet */}
              <div className="bg-white rounded-xl p-4 border border-border shadow-sm">
                <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-3 flex items-center gap-1.5">
                  <ReceiptText className="w-3.5 h-3.5" strokeWidth={2.2} /> Kesintiler & Zimmet
                </div>
                <div className="space-y-1.5">
                  {r.kesinti_groups.map((g) => (
                    <DetailRow
                      key={g.type}
                      label={normalizeTr(g.type)}
                      value={`−${m(g.total)} ₺`}
                      color="text-red-600"
                    />
                  ))}
                  {r.kesinti_groups.length === 0 && (
                    <div className="text-text-3 italic">— kesinti yok —</div>
                  )}
                  <div className="flex justify-between pt-2 border-t border-border font-bold">
                    <span>Manuel Toplam</span>
                    <span className="num font-mono text-red-600">−{m(r.kesinti_total)} ₺</span>
                  </div>
                </div>
              </div>
            </div>
            {/* Tevkifat detay */}
            {r.tevkifat > 0 && (
              <div className="mt-3 bg-gradient-to-r from-orange-50 to-yellow-50 border border-orange-200 rounded-xl p-4">
                <div className="text-[10.5px] uppercase tracking-wider text-orange-800 font-bold mb-2 flex items-center gap-1.5">
                  <Flame className="w-3.5 h-3.5" strokeWidth={2.2} /> KDV Tevkifatı (2/10)
                </div>
                <div className="grid grid-cols-3 gap-3 text-[11.5px]">
                  <DetailRow
                    label="Fatura matrahı (KDV hariç)"
                    value={`${m(r.tevkifat_breakdown.invoice_base_amount)} ₺`}
                  />
                  <DetailRow
                    label="KDV (%20)"
                    value={`${m(r.tevkifat_breakdown.vat_amount)} ₺`}
                  />
                  <DetailRow
                    label="Tevkifat (%20 × KDV)"
                    value={`−${m(r.tevkifat_breakdown.tevkifat_amount)} ₺`}
                    color="text-orange-700"
                  />
                </div>
              </div>
            )}

            {/* Net büyük gradient bant */}
            <div className="mt-4 bg-gradient-to-r from-brand to-blue-600 rounded-xl px-5 py-4 flex items-center justify-between text-white shadow-md">
              <div className="text-[12px] font-medium opacity-90">
                Brüt {m(r.toplam_brut)} ₺ − Kesinti{' '}
                {m(r.kesinti_total + r.sabit_total)} ₺
                {r.tevkifat > 0 && ` − Tevkifat ${m(r.tevkifat)} ₺`} =
              </div>
              <div className="font-display text-3xl font-bold num tabular-nums">
                {m(r.net)} ₺
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function DetailRow({
  label, value, color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="flex justify-between text-[12px]">
      <span className="text-text-2">{label}</span>
      <span className={`num font-mono ${color ?? ''}`}>{value}</span>
    </div>
  );
}

function PayrollCharts({ payroll }: { payroll: PayrollResult }) {
  const s = payroll.summary;
  const brut = s.total_brut;
  const kesinti = s.total_kesinti;
  const tevkifat = s.total_tevkifat ?? 0;
  const net = s.total_net;
  const sabitKesinti = kesinti - tevkifat;

  // Restoran bazlı agregasyon
  const byRestaurant = useMemo(() => {
    const m = new Map<string, { count: number; brut: number; net: number }>();
    for (const r of payroll.rows) {
      const k = r.rest_brand
        ? `${r.rest_brand}${r.rest_branch ? ' · ' + r.rest_branch : ''}`
        : noRestaurantLabel(r.role);
      const cur = m.get(k) ?? { count: 0, brut: 0, net: 0 };
      cur.count++;
      cur.brut += r.toplam_brut;
      cur.net += r.net;
      m.set(k, cur);
    }
    return Array.from(m.entries())
      .map(([name, v]) => ({ name, ...v }))
      .sort((a, b) => b.brut - a.brut)
      .slice(0, 6);
  }, [payroll.rows]);

  const totalRestBrut = byRestaurant.reduce((s, r) => s + r.brut, 0);

  // Verimlilik metrikleri
  const performers = useMemo(() => {
    const couriers = payroll.rows.filter((r) => r.ana_packages > 0 && r.ana_hours > 0);
    if (couriers.length === 0) return null;

    const enCokPaket = [...couriers].sort((a, b) => b.ana_packages - a.ana_packages)[0];
    const enVerimli = [...couriers].sort(
      (a, b) => (b.ana_packages / b.ana_hours) - (a.ana_packages / a.ana_hours),
    )[0];
    // En verimsiz: en az saatte-paket oranı + minimum saat eşiği
    const enVerimsizCandidates = couriers.filter((r) => r.ana_hours >= 50);
    const enVerimsiz = enVerimsizCandidates.length > 0
      ? [...enVerimsizCandidates].sort(
          (a, b) => (a.ana_packages / a.ana_hours) - (b.ana_packages / b.ana_hours),
        )[0]
      : null;

    return { enCokPaket, enVerimli, enVerimsiz };
  }, [payroll.rows]);

  return (
    <>
      {/* Üst grafikler — Donut + Restoran ranking */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-4">
        {/* Donut: Brüt dağılımı */}
        <div className="lg:col-span-2 bg-white border border-border rounded-2xl p-5 shadow-sm">
          <div className="text-[11px] uppercase tracking-[0.08em] text-text-3 font-bold mb-3 flex items-center gap-1.5">
            <PieChart className="w-3.5 h-3.5" strokeWidth={2.2} /> Brüt Dağılımı
          </div>
          <DonutChart
            segments={[
              { label: 'Net', value: net, color: '#0F52BA' },
              { label: 'Sabit Kesinti', value: sabitKesinti, color: '#EF4444' },
              { label: 'Tevkifat', value: tevkifat, color: '#F59E0B' },
            ]}
            centerLabel="Brüt"
            centerValue={`${kCompact(brut)} ₺`}
          />
        </div>

        {/* Restoran ranking — yeniden tasarım: tile cards */}
        <div className="lg:col-span-3 bg-white border border-border rounded-2xl p-5 shadow-sm">
          <div className="flex items-baseline justify-between mb-3">
            <div className="text-[11px] uppercase tracking-[0.08em] text-text-3 font-bold flex items-center gap-1.5">
              <Store className="w-3.5 h-3.5" strokeWidth={2.2} /> Restoran Bazlı Hakediş
            </div>
            <div className="text-[10.5px] text-text-3">
              {byRestaurant.length} restoran · top 6
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {byRestaurant.map((r, idx) => {
              const share = totalRestBrut > 0 ? (r.brut / totalRestBrut) * 100 : 0;
              return (
                <div
                  key={r.name}
                  className="relative bg-gradient-to-br from-cream-50 to-white border border-border/70 rounded-xl p-3 hover:border-brand/40 hover:shadow-sm transition group"
                >
                  {/* Soft accent ring */}
                  <div
                    className="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl bg-gradient-to-b from-brand to-blue-400"
                    style={{ opacity: 0.3 + (share / 100) * 0.7 }}
                  />
                  <div className="pl-2">
                    <div className="flex items-baseline justify-between mb-1.5">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="text-[10px] font-mono text-text-3 w-4">
                          #{idx + 1}
                        </span>
                        <span className="font-semibold text-text text-[12px] truncate">
                          {r.name}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-text-3 flex-shrink-0">
                        %{share.toFixed(1)}
                      </span>
                    </div>
                    <div className="flex items-baseline justify-between">
                      <div>
                        <div className="font-display text-[16px] font-bold text-brand tabular-nums leading-none">
                          {kCompact(r.brut)} ₺
                        </div>
                        <div className="text-[10px] text-text-3 mt-0.5">
                          net {kCompact(r.net)} ₺ · {r.count} kurye
                        </div>
                      </div>
                      {/* Mini horizontal progress */}
                      <div className="w-16 h-1.5 bg-bg-surface2 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-brand-dark to-brand transition-all duration-700"
                          style={{ width: `${Math.min(100, share * 2)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Verimlilik kartları — En çok paket / En verimli / En verimsiz */}
      {performers && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
          <PerformerCard
            label="En Çok Paket"
            icon={<Trophy className="w-3.5 h-3.5" strokeWidth={2.2} />}
            tone="gold"
            row={performers.enCokPaket}
            metric={`${tr(performers.enCokPaket.ana_packages)} paket`}
            sub={`${tr(performers.enCokPaket.ana_hours, 0)} saatte`}
          />
          <PerformerCard
            label="Saatte En Verimli"
            icon={<Sparkles className="w-3.5 h-3.5" strokeWidth={2.2} />}
            tone="brand"
            row={performers.enVerimli}
            metric={`${(performers.enVerimli.ana_packages / Math.max(performers.enVerimli.ana_hours, 1)).toFixed(2)} paket/sa`}
            sub={`${tr(performers.enVerimli.ana_packages)} paket · ${tr(performers.enVerimli.ana_hours, 0)} sa`}
          />
          {performers.enVerimsiz ? (
            <PerformerCard
              label="En Az Verimli"
              icon={<TrendingDown className="w-3.5 h-3.5" strokeWidth={2.2} />}
              tone="muted"
              row={performers.enVerimsiz}
              metric={`${(performers.enVerimsiz.ana_packages / Math.max(performers.enVerimsiz.ana_hours, 1)).toFixed(2)} paket/sa`}
              sub={`${tr(performers.enVerimsiz.ana_packages)} paket · ${tr(performers.enVerimsiz.ana_hours, 0)} sa`}
            />
          ) : (
            <div className="rounded-2xl border border-dashed border-border bg-cream-50/50 p-4 flex items-center justify-center text-[11px] text-text-3 text-center">
              Verimsiz analizi için en az 50 saat çalışan kurye gerekli.
            </div>
          )}
        </div>
      )}
    </>
  );
}

function PerformerCard({
  label, icon, tone, row, metric, sub,
}: {
  label: string;
  icon: React.ReactNode;
  tone: 'gold' | 'brand' | 'muted';
  row: PayrollRow;
  metric: string;
  sub: string;
}) {
  const grad = AVATAR_GRADIENTS[(row.id ?? 0) % AVATAR_GRADIENTS.length];
  const initials = (row.full_name ?? '?')
    .split(' ').filter(Boolean).slice(0, 2)
    .map((w) => w[0]?.toUpperCase()).join('');

  const toneStyles: Record<string, { card: string; iconBg: string; metricColor: string; ring: string }> = {
    gold: {
      card: 'bg-gradient-to-br from-yellow-50 via-white to-amber-50 border-yellow-300/70',
      iconBg: 'bg-yellow-100 text-yellow-700',
      metricColor: 'text-yellow-700',
      ring: 'ring-yellow-200',
    },
    brand: {
      card: 'bg-gradient-to-br from-brand-soft via-white to-blue-50 border-brand/30',
      iconBg: 'bg-brand-soft text-brand',
      metricColor: 'text-brand',
      ring: 'ring-brand/20',
    },
    muted: {
      card: 'bg-gradient-to-br from-slate-50 via-white to-cream-50 border-slate-200',
      iconBg: 'bg-slate-100 text-slate-600',
      metricColor: 'text-slate-600',
      ring: 'ring-slate-200',
    },
  };
  const t = toneStyles[tone];

  return (
    <div className={`relative rounded-2xl border ${t.card} p-4 shadow-sm hover:shadow-md transition group`}>
      <div className="flex items-center justify-between mb-3">
        <div className="text-[10.5px] uppercase tracking-[0.08em] text-text-3 font-bold flex items-center gap-1.5">
          {icon} {label}
        </div>
        <div className={`w-7 h-7 rounded-lg ${t.iconBg} flex items-center justify-center`}>
          {icon}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div
          className={`w-12 h-12 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-[14px] flex-shrink-0 shadow-md ring-2 ring-white`}
        >
          {initials || '?'}
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-text truncate text-[13px]">
            {row.full_name}
          </div>
          <div className="text-[10.5px] text-text-3 truncate">
            {row.rest_brand
              ? `${row.rest_brand}${row.rest_branch ? ` · ${row.rest_branch}` : ''}`
              : noRestaurantLabel(row.role)}
          </div>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-border/60">
        <div className={`font-display text-[18px] font-bold tabular-nums leading-none ${t.metricColor}`}>
          {metric}
        </div>
        <div className="text-[10.5px] text-text-3 mt-1">{sub}</div>
      </div>
    </div>
  );
}

function DonutChart({
  segments, centerLabel, centerValue,
}: {
  segments: { label: string; value: number; color: string }[];
  centerLabel: string;
  centerValue: string;
}) {
  const total = segments.reduce((s, x) => s + Math.max(0, x.value), 0);
  const r = 60;
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
    <div className="flex items-center gap-4">
      <div className="relative w-[150px] h-[150px] flex-shrink-0">
        <svg width="150" height="150" viewBox="0 0 150 150">
          <defs>
            <filter id="donut-glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <circle
            cx="75" cy="75" r={r}
            fill="none"
            stroke="rgba(0,0,0,0.05)"
            strokeWidth="14"
          />
          {arcs.map((a) => (
            <circle
              key={a.key}
              cx="75" cy="75" r={r}
              fill="none"
              stroke={a.color}
              strokeWidth="14"
              strokeDasharray={a.dash}
              strokeDashoffset={a.dashOffset}
              strokeLinecap="round"
              transform="rotate(-90 75 75)"
              filter="url(#donut-glow)"
              style={{
                transition: 'stroke-dasharray 1s ease',
              }}
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <div className="text-[10px] uppercase tracking-wider text-text-3 font-semibold">
            {centerLabel}
          </div>
          <div className="font-display text-[20px] font-bold tracking-tight text-text num tabular-nums">
            {centerValue}
          </div>
        </div>
      </div>
      <div className="flex-1 space-y-2">
        {arcs.map((a) => (
          <div key={a.key} className="flex items-center gap-2 text-[12px]">
            <span
              className="w-3 h-3 rounded-sm flex-shrink-0 shadow-sm"
              style={{ backgroundColor: a.color }}
            />
            <span className="text-text-2 flex-1">{a.label}</span>
            <span className="font-mono font-semibold tabular-nums">
              %{(a.portion * 100).toFixed(1)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
