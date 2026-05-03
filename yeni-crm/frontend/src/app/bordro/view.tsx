'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

import type { PayrollResult, PayrollRow } from '@/lib/api';
import { normalizeTr } from '@/lib/format';

const PDF_ICON = '📄';

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

const ROLE_STYLES: Record<string, string> = {
  Kurye: 'bg-brand-soft text-brand',
  Joker: 'bg-cream-100 text-yellow-800',
  'Bölge Müdürü': 'bg-text text-white',
  Kaptan: 'bg-purple-100 text-purple-800',
  'Restoran Takım Şefi': 'bg-green-100 text-green-800',
};

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
  const filteredKesinti = filteredKesintiNonTev + filteredTevkifat;
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
        {/* Gradient bg with mesh feel */}
        <div className="absolute inset-0 bg-gradient-to-br from-brand-dark via-brand to-blue-600" />
        <div className="absolute inset-0 opacity-30 mix-blend-overlay"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 20%, rgba(255,255,255,.4) 0%, transparent 40%), radial-gradient(circle at 80% 70%, rgba(255,200,100,.3) 0%, transparent 50%)',
          }}
        />
        {/* dot pattern */}
        <div className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        <div className="relative px-7 py-7 flex justify-between items-start gap-6 flex-wrap">
          <div className="text-white">
            <div className="text-[12px] font-medium tracking-[0.2em] uppercase text-white/70 mb-2 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-yellow-300 animate-pulse" />
              Finans · Bordro
            </div>
            <h1 className="font-display text-[42px] font-bold tracking-tight leading-none">
              {formatPeriod(period)}
            </h1>
            <div className="text-white/80 text-sm mt-2 font-medium">
              <strong className="text-white text-[15px]">
                {payroll.summary.courier_count}
              </strong>{' '}
              kurye · toplam{' '}
              <strong className="text-white">{m(payroll.summary.total_brut)} ₺</strong>{' '}
              brüt → ödenecek{' '}
              <strong className="text-yellow-300">
                {m(payroll.summary.total_net)} ₺
              </strong>
            </div>
          </div>

          <div className="flex gap-2 items-center">
            {/* Glass period selector */}
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
              ⬇ Tüm Bordrolar
            </button>
          </div>
        </div>

        {/* Footer ribbon — quick stats */}
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
          KPI cards — neon-edge gradient
         ──────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KpiCard
          label="Toplam Brüt"
          value={m(payroll.summary.total_brut)}
          suffix="₺"
          accent="brand"
          icon="💎"
          meta={`${payroll.summary.courier_count} kurye · ${kCompact(payroll.summary.total_brut)} ₺`}
        />
        <KpiCard
          label="Toplam Kesinti"
          value={m(payroll.summary.total_kesinti)}
          suffix="₺"
          accent="danger"
          icon="🧾"
          meta={`tevkifat ${m(payroll.summary.total_tevkifat ?? 0)} ₺ dahil`}
        />
        <KpiCard
          label="Net Ödenecek"
          value={m(payroll.summary.total_net)}
          suffix="₺"
          accent="success"
          icon="💰"
          meta="kuryelere transfer"
        />
        <KpiCard
          label="Kesinti Oranı"
          value={`%${profitMargin.toFixed(1)}`}
          accent="warn"
          icon="📊"
          meta="brütün kesintisi"
        />
      </div>

      {/* ────────────────────────────────────────────────────────────
          GRAFIKLER — donut + restaurant ranking + podium
         ──────────────────────────────────────────────────────────── */}
      <PayrollCharts payroll={payroll} />

      {/* ────────────────────────────────────────────────────────────
          FILTRELER — floating chips
         ──────────────────────────────────────────────────────────── */}
      <div className="bg-white/70 backdrop-blur-sm border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2 sticky top-2 z-10">
        <div className="relative">
          <input
            type="search"
            placeholder="🔍 Kurye ara…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-border text-sm w-64 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
          />
        </div>
        <select
          value={restFilter ?? ''}
          onChange={(e) => setRestFilter(e.target.value || null)}
          className="px-3 py-1.5 rounded-lg border border-border text-sm bg-white focus:outline-none focus:border-brand transition"
        >
          <option value="">🏪 Tüm Restoranlar</option>
          {restaurantOptions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        {(search || restFilter) && (
          <button
            onClick={() => { setSearch(''); setRestFilter(null); }}
            className="text-[11px] text-text-3 hover:text-brand transition px-2 py-1"
          >
            ✕ filtreleri temizle
          </button>
        )}
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
          {filtered.length} sonuç · brüt{' '}
          <span className="text-brand font-mono">{m(filteredBrut)} ₺</span> · net{' '}
          <span className="text-green-700 font-mono">{m(filteredNet)} ₺</span>
        </span>
      </div>

      {/* ────────────────────────────────────────────────────────────
          TABLO — sticky header, color-coded ribbons, hover ring
         ──────────────────────────────────────────────────────────── */}
      {filtered.length === 0 ? (
        <div className="bg-bg-surface border border-border rounded-2xl p-12 text-center">
          <div className="text-4xl mb-3">🔍</div>
          <div className="text-text-3 text-sm">Sonuç bulunamadı.</div>
        </div>
      ) : (
        <div className="bg-white border border-border rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-[13px]">
            <thead className="bg-gradient-to-r from-cream-100 to-cream-50 text-text-3 text-[11px] uppercase tracking-wider sticky top-0 z-10 backdrop-blur-sm">
              <tr>
                <th className="text-left px-3 py-3 font-bold">Kurye</th>
                <th className="text-left px-3 py-3 font-bold">Restoran</th>
                <th className="text-right px-3 py-3 font-bold">Gün/Saat</th>
                <th className="text-right px-3 py-3 font-bold">Paket</th>
                <th className="text-right px-3 py-3 font-bold">Brüt</th>
                <th className="text-right px-3 py-3 font-bold">Kesinti</th>
                <th className="text-right px-3 py-3 font-bold">Tevkifat</th>
                <th className="text-right px-3 py-3 font-bold bg-brand-soft text-brand">
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
              <tr className="border-t-2 border-brand/30 bg-gradient-to-r from-brand-soft/40 to-transparent font-semibold">
                <td colSpan={4} className="px-3 py-3.5 text-text">
                  Toplam ({filtered.length} kurye)
                </td>
                <td className="px-3 py-3.5 text-right num text-text">
                  {m(filteredBrut)} ₺
                </td>
                <td className="px-3 py-3.5 text-right num text-red-600">
                  −{m(filteredKesintiNonTev)} ₺
                </td>
                <td className="px-3 py-3.5 text-right num text-orange-600">
                  −{m(filteredTevkifat)} ₺
                </td>
                <td className="px-3 py-3.5 text-right font-display text-brand text-[16px] num bg-brand-soft">
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

// ──────────────────────────────────────────────────────────────────
// HERO ribbon stat (4 kolonlu mini özet, hero altı)
// ──────────────────────────────────────────────────────────────────
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

// ──────────────────────────────────────────────────────────────────
// KPI Card — gradient border + icon + dramatic number
// ──────────────────────────────────────────────────────────────────
function KpiCard({
  label, value, suffix, meta, accent, icon,
}: {
  label: string;
  value: string;
  suffix?: string;
  meta?: string;
  accent: 'brand' | 'success' | 'danger' | 'warn';
  icon?: string;
}) {
  const ringMap: Record<string, string> = {
    brand: 'before:bg-gradient-to-br before:from-brand before:to-blue-400',
    success: 'before:bg-gradient-to-br before:from-green-500 before:to-emerald-300',
    danger: 'before:bg-gradient-to-br before:from-red-500 before:to-orange-400',
    warn: 'before:bg-gradient-to-br before:from-yellow-500 before:to-amber-300',
  };
  const iconBgMap: Record<string, string> = {
    brand: 'bg-brand-soft text-brand',
    success: 'bg-green-100 text-green-700',
    danger: 'bg-red-100 text-red-700',
    warn: 'bg-yellow-100 text-yellow-800',
  };

  return (
    <div
      className={`relative bg-white rounded-2xl px-5 py-4 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5 overflow-hidden border border-border before:content-[''] before:absolute before:inset-0 before:rounded-2xl before:opacity-0 hover:before:opacity-100 before:transition-opacity before:-z-10 before:m-[-1px] ${ringMap[accent]}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold">
          {label}
        </div>
        {icon && (
          <div className={`w-7 h-7 rounded-lg ${iconBgMap[accent]} flex items-center justify-center text-[14px]`}>
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

// ──────────────────────────────────────────────────────────────────
// PayrollRowItem — tablo satırı + açılır detay
// ──────────────────────────────────────────────────────────────────
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

  return (
    <>
      <tr
        className="border-t border-border hover:bg-cream-50/60 hover:shadow-[inset_3px_0_0_var(--color-brand,#0F52BA)] transition cursor-pointer group"
        onClick={onToggle}
      >
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-2.5">
            <div
              className={`w-9 h-9 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-[12px] flex-shrink-0 shadow-md ring-2 ring-white group-hover:scale-110 transition-transform`}
            >
              {initials || '?'}
            </div>
            <div className="min-w-0">
              <div className="font-medium text-text truncate">
                {r.full_name ?? '—'}
              </div>
              <div className="flex gap-1.5 items-center mt-0.5">
                <span className="text-[10.5px] font-mono text-text-3">
                  {r.person_code ?? ''}
                </span>
                <span
                  className={`px-1.5 py-px rounded text-[10px] font-semibold ${roleStyle}`}
                >
                  {role}
                </span>
                {r.is_fixed_salary && (
                  <span className="px-1.5 py-px rounded text-[10px] font-semibold bg-brand-soft text-brand">
                    Sabit
                  </span>
                )}
              </div>
            </div>
          </div>
        </td>
        <td className="px-3 py-2.5">
          <div className="text-[12px] text-text-2 truncate">
            {r.rest_brand ? (
              <>
                {r.rest_brand}
                {r.rest_branch && (
                  <span className="text-text-3"> · {r.rest_branch}</span>
                )}
              </>
            ) : (
              <span className="text-text-3 italic">— atanmamış —</span>
            )}
          </div>
        </td>
        <td className="px-3 py-2.5 text-right">
          <div className="num font-mono text-[12px]">
            <strong>{r.ana_days}</strong>
            {r.destek_days > 0 && (
              <span className="text-orange-600"> +{r.destek_days}</span>
            )}{' '}
            <span className="text-text-3">gün</span>
          </div>
          <div className="text-[10.5px] text-text-3 num font-mono">
            {tr(r.ana_hours, 1)} sa
          </div>
        </td>
        <td className="px-3 py-2.5 text-right num font-mono text-text-2">
          {tr(r.ana_packages)}
        </td>
        <td className="px-3 py-2.5 text-right">
          <div className="num font-mono font-semibold">
            {m(r.toplam_brut)} ₺
          </div>
          {r.kaptan_bonus > 0 && (
            <div className="text-[10px] text-green-600 font-semibold">
              +{m(r.kaptan_bonus)} kaptan
            </div>
          )}
        </td>
        <td className="px-3 py-2.5 text-right num font-mono text-red-600">
          −{m(r.kesinti_total + r.sabit_total)} ₺
        </td>
        <td className="px-3 py-2.5 text-right num font-mono text-orange-600">
          {r.tevkifat > 0 ? `−${m(r.tevkifat)} ₺` : '—'}
        </td>
        <td className="px-3 py-2.5 text-right num font-display font-bold text-brand text-[14.5px] bg-brand-soft/40 group-hover:bg-brand-soft transition-colors">
          {m(r.net)} ₺
        </td>
        <td
          className="px-2 py-2.5 text-text-3 text-center w-10"
          onClick={(e) => e.stopPropagation()}
        >
          <a
            href={`/api/payroll/${r.id}/pdf?period=${encodeURIComponent(period)}`}
            download
            className="hover:text-brand text-[16px] inline-block hover:scale-110 transition-transform"
            title="PDF indir"
          >
            {PDF_ICON}
          </a>
        </td>
        <td className="px-2 py-2.5 text-text-3 text-[12px] w-8">
          {open ? '▾' : '▸'}
        </td>
      </tr>

      {/* Detay paneli */}
      {open && (
        <tr className="bg-gradient-to-br from-cream-50 to-white border-b-2 border-brand/20">
          <td colSpan={10} className="px-5 py-5">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-[12px]">
              {/* Brüt detay */}
              <div className="bg-white rounded-xl p-4 border border-border shadow-sm">
                <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-3 flex items-center gap-1.5">
                  <span>📊</span> Brüt Hesabı
                </div>
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
                  <div className="mt-3 text-[11px] text-text-3 bg-cream-50 rounded p-2">
                    <strong>Destek satırları:</strong>{' '}
                    {r.destek_lines.map((d, i) => (
                      <span key={i}>
                        Restoran #{d.restaurant_id}: {d.days}g/{tr(d.amount)}₺
                        {i < r.destek_lines.length - 1 ? ' · ' : ''}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Sabit kesintiler */}
              <div className="bg-white rounded-xl p-4 border border-border shadow-sm">
                <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-3 flex items-center gap-1.5">
                  <span>📋</span> Sabit Kesintiler
                </div>
                <div className="space-y-1.5">
                  {r.motor_taksit > 0 && (
                    <DetailRow label="Motor Satış Taksiti" value={`−${m(r.motor_taksit)} ₺`} color="text-red-600" />
                  )}
                  {r.motor_kira > 0 && (
                    <DetailRow
                      label={`Motor Kirası${r.ana_days < 28 ? ` (${r.ana_days} gün)` : ''}`}
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
                  <span>🧾</span> Kesintiler & Zimmet
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
                  <span>💼</span> KDV Tevkifatı (2/10)
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
            <div className="mt-4 pt-4 bg-gradient-to-r from-brand to-blue-600 rounded-xl px-5 py-4 flex items-center justify-between text-white shadow-md">
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

// ──────────────────────────────────────────────────────────────────
// PayrollCharts — Donut + Restoran ranking + Top performer podium
// ──────────────────────────────────────────────────────────────────

function PayrollCharts({ payroll }: { payroll: PayrollResult }) {
  const s = payroll.summary;
  const brut = s.total_brut;
  const kesinti = s.total_kesinti;
  const tevkifat = s.total_tevkifat ?? 0;
  const net = s.total_net;
  const sabitKesinti = kesinti - tevkifat;

  // Restoran bazlı toplam net
  const byRestaurant = useMemo(() => {
    const m = new Map<string, { count: number; brut: number; net: number }>();
    for (const r of payroll.rows) {
      const k = r.rest_brand
        ? `${r.rest_brand}${r.rest_branch ? ' · ' + r.rest_branch : ''}`
        : '— atanmamış —';
      const cur = m.get(k) ?? { count: 0, brut: 0, net: 0 };
      cur.count++;
      cur.brut += r.toplam_brut;
      cur.net += r.net;
      m.set(k, cur);
    }
    return Array.from(m.entries())
      .map(([name, v]) => ({ name, ...v }))
      .sort((a, b) => b.brut - a.brut)
      .slice(0, 8);
  }, [payroll.rows]);

  const maxBrut = Math.max(...byRestaurant.map((r) => r.brut), 1);

  // Top 3 kazançlı kurye (podium)
  const top3 = useMemo(
    () =>
      [...payroll.rows]
        .sort((a, b) => b.net - a.net)
        .slice(0, 3),
    [payroll.rows],
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
      {/* Donut: Brüt dağılımı */}
      <div className="bg-white border border-border rounded-2xl p-5 shadow-sm">
        <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-3 flex items-center gap-1.5">
          <span>🎯</span> Brüt Dağılımı
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

      {/* Restoran bazlı brüt bar chart */}
      <div className="bg-white border border-border rounded-2xl p-5 shadow-sm lg:col-span-2">
        <div className="flex items-baseline justify-between mb-3">
          <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold flex items-center gap-1.5">
            <span>🏪</span> Restoran Bazlı Brüt Hakediş
          </div>
          <div className="text-[11px] text-text-3">
            En yüksek 8 restoran · ay toplamı
          </div>
        </div>
        <div className="space-y-2">
          {byRestaurant.map((r, idx) => {
            const ratio = r.brut / maxBrut;
            return (
              <div
                key={r.name}
                className="grid grid-cols-[170px_1fr_auto] gap-3 items-center text-[12px] group"
              >
                <div className="truncate text-text-2 font-medium flex items-center gap-1.5">
                  <span className="text-[10px] font-mono text-text-3 w-4">
                    #{idx + 1}
                  </span>
                  <span className="truncate">{r.name}</span>{' '}
                  <span className="text-text-3 text-[11px] flex-shrink-0">
                    ({r.count})
                  </span>
                </div>
                <div className="bg-cream-50 rounded-lg h-7 relative overflow-hidden border border-border/60">
                  <div
                    className="h-full bg-gradient-to-r from-brand-dark via-brand to-blue-400 transition-all duration-1000 ease-out group-hover:from-blue-700 group-hover:to-blue-300 shadow-inner relative"
                    style={{ width: `${ratio * 100}%` }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-t from-transparent via-white/10 to-transparent" />
                  </div>
                  <div className="absolute inset-0 flex items-center px-2.5 text-[11px] font-mono font-semibold text-white mix-blend-difference">
                    Net {kCompact(r.net)}
                  </div>
                </div>
                <div className="font-mono font-bold text-[12.5px] text-right min-w-[70px] tabular-nums">
                  {kCompact(r.brut)} ₺
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top 3 podium */}
      <div className="lg:col-span-3 bg-gradient-to-br from-white to-cream-50 border border-border rounded-2xl p-5 shadow-sm">
        <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-4 flex items-center gap-1.5">
          <span>🏆</span> Ay Şampiyonları (en yüksek net)
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {top3.map((p, idx) => {
            const grad = AVATAR_GRADIENTS[(p.id ?? 0) % AVATAR_GRADIENTS.length];
            const initials = (p.full_name ?? '?')
              .split(' ').filter(Boolean).slice(0, 2)
              .map((w) => w[0]?.toUpperCase()).join('');
            const medals = ['🥇', '🥈', '🥉'];
            const podiumStyle = [
              'border-yellow-400 bg-gradient-to-br from-yellow-50 to-white',
              'border-slate-300 bg-gradient-to-br from-slate-50 to-white',
              'border-orange-300 bg-gradient-to-br from-orange-50 to-white',
            ];
            return (
              <div
                key={p.id}
                className={`relative rounded-xl border-2 ${podiumStyle[idx]} p-4 flex items-center gap-3 shadow-sm hover:shadow-md transition`}
              >
                <div className="absolute -top-2 -right-2 text-2xl">{medals[idx]}</div>
                <div
                  className={`w-12 h-12 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-[14px] flex-shrink-0 shadow-md ring-2 ring-white`}
                >
                  {initials || '?'}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-text truncate text-[13px]">
                    {p.full_name}
                  </div>
                  <div className="text-[11px] text-text-3 truncate">
                    {p.rest_brand ?? 'Atanmamış'}
                    {p.rest_branch && ` · ${p.rest_branch}`}
                  </div>
                  <div className="font-display text-[18px] font-bold text-brand mt-1 num tabular-nums">
                    {m(p.net)} ₺
                  </div>
                </div>
              </div>
            );
          })}
        </div>
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
