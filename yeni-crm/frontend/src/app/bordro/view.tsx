'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

import type { PayrollResult, PayrollRow } from '@/lib/api';

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
  const filteredKesinti = filtered.reduce((s, r) => s + r.kesinti_total + r.sabit_total, 0);
  const filteredNet = filtered.reduce((s, r) => s + r.net, 0);

  return (
    <>
      {/* Header */}
      <header className="flex justify-between items-end gap-5 flex-wrap mb-5">
        <div>
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Finans · <span className="text-brand">Bordro</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            {formatPeriod(period)} Bordrosu
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {payroll.summary.courier_count} kurye · brüt{' '}
            <strong>{tr(payroll.summary.total_brut)} ₺</strong> · kesinti{' '}
            <strong className="text-red-600">−{tr(payroll.summary.total_kesinti)} ₺</strong> · net{' '}
            <strong className="text-brand">{tr(payroll.summary.total_net)} ₺</strong>
          </div>
        </div>
        <div className="flex gap-2 items-center">
          <div className="flex items-center gap-1 bg-bg-surface border border-border rounded-xl p-1 shadow-sm">
            {periods.slice(0, 4).map((p) => {
              const isActive = p === period;
              return (
                <Link
                  key={p}
                  href={`/bordro?ay=${p}`}
                  className={`px-3 py-1.5 rounded-lg text-[12.5px] font-medium transition ${
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
          <button className="px-4 py-2 rounded-xl bg-brand text-white text-[13px] font-semibold shadow-sm hover:bg-brand-dark transition flex items-center gap-1.5">
            ⬇ Bordrolar (PDF)
          </button>
        </div>
      </header>

      {/* Hero Strip — 4 cell */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <HeroCard
          label="Toplam Brüt"
          value={tr(Math.round(payroll.summary.total_brut))}
          suffix="₺"
          accent="brand"
          meta={`${payroll.summary.courier_count} kurye`}
        />
        <HeroCard
          label="Toplam Kesinti"
          value={tr(Math.round(payroll.summary.total_kesinti))}
          suffix="₺"
          accent="danger"
          meta="motor + muhasebe + şirket + manuel + zimmet"
        />
        <HeroCard
          label="Toplam Net"
          value={tr(Math.round(payroll.summary.total_net))}
          suffix="₺"
          accent="success"
          meta="kuryelere ödenecek"
        />
        <HeroCard
          label="Kar Marjı"
          value={
            payroll.summary.total_brut > 0
              ? `%${(
                  (payroll.summary.total_kesinti / payroll.summary.total_brut) *
                  100
                ).toFixed(1)}`
              : '—'
          }
          accent="warn"
          meta="kesinti / brüt"
        />
      </div>

      {/* Filters */}
      <div className="bg-bg-surface border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2">
        <input
          type="search"
          placeholder="Kurye ara…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-1.5 rounded-lg border border-border text-sm w-64 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
        />
        <select
          value={restFilter ?? ''}
          onChange={(e) => setRestFilter(e.target.value || null)}
          className="px-3 py-1.5 rounded-lg border border-border text-sm bg-bg-surface focus:outline-none focus:border-brand transition"
        >
          <option value="">Tüm Restoranlar</option>
          {restaurantOptions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
          {filtered.length} sonuç · brüt {tr(Math.round(filteredBrut))} ₺ · net{' '}
          {tr(Math.round(filteredNet))} ₺
        </span>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="bg-bg-surface border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
          Sonuç bulunamadı.
        </div>
      ) : (
        <div className="bg-bg-surface border border-border rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-[13px]">
            <thead className="bg-bg-surface2 text-text-3 text-[11px] uppercase tracking-wider">
              <tr>
                <th className="text-left px-3 py-2.5 font-semibold">Kurye</th>
                <th className="text-left px-3 py-2.5 font-semibold">Restoran</th>
                <th className="text-right px-3 py-2.5 font-semibold">Gün/Saat</th>
                <th className="text-right px-3 py-2.5 font-semibold">Paket</th>
                <th className="text-right px-3 py-2.5 font-semibold">Brüt</th>
                <th className="text-right px-3 py-2.5 font-semibold">Kesinti</th>
                <th className="text-right px-3 py-2.5 font-semibold bg-brand-soft text-brand">
                  Net
                </th>
                <th className="px-2 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <PayrollRowItem
                  key={r.id}
                  r={r}
                  open={openRow === r.id}
                  onToggle={() => setOpenRow(openRow === r.id ? null : r.id)}
                />
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-border bg-bg-surface2/50 font-semibold">
                <td colSpan={4} className="px-3 py-3 text-text">
                  Toplam ({filtered.length} kurye)
                </td>
                <td className="px-3 py-3 text-right num text-text">
                  {tr(filteredBrut)} ₺
                </td>
                <td className="px-3 py-3 text-right num text-red-600">
                  −{tr(filteredKesinti)} ₺
                </td>
                <td className="px-3 py-3 text-right font-display text-brand text-[15px] num bg-brand-soft">
                  {tr(filteredNet)} ₺
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </>
  );
}

function HeroCard({
  label, value, suffix, meta, accent,
}: {
  label: string;
  value: string;
  suffix?: string;
  meta?: string;
  accent: 'brand' | 'success' | 'danger' | 'warn';
}) {
  const accentMap: Record<string, string> = {
    brand: 'bg-brand',
    success: 'bg-green-500',
    danger: 'bg-red-500',
    warn: 'bg-yellow-500',
  };
  return (
    <div className="relative bg-bg-surface border border-border rounded-2xl px-5 py-4 shadow-sm overflow-hidden">
      <div
        className={`absolute left-0 top-0 bottom-0 w-[3px] ${accentMap[accent]}`}
      />
      <div className="text-[11px] uppercase tracking-wider text-text-3 font-semibold mb-2">
        {label}
      </div>
      <div className="font-display text-[26px] font-bold tracking-tight leading-none num">
        {value}
        {suffix && (
          <span className="text-base font-medium text-text-3 ml-1">
            {suffix}
          </span>
        )}
      </div>
      {meta && (
        <div className="text-[11px] text-text-3 mt-2">{meta}</div>
      )}
    </div>
  );
}

function PayrollRowItem({
  r, open, onToggle,
}: {
  r: PayrollRow;
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
        className="border-t border-border hover:bg-bg-surface2/40 transition cursor-pointer"
        onClick={onToggle}
      >
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-2.5">
            <div
              className={`w-8 h-8 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-[11px] flex-shrink-0`}
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
            {tr(Math.round(r.ana_hours))} sa
          </div>
        </td>
        <td className="px-3 py-2.5 text-right num font-mono text-text-2">
          {tr(r.ana_packages)}
        </td>
        <td className="px-3 py-2.5 text-right">
          <div className="num font-mono font-semibold">
            {tr(r.toplam_brut)} ₺
          </div>
          {r.kaptan_bonus > 0 && (
            <div className="text-[10px] text-green-600 font-semibold">
              +{tr(r.kaptan_bonus)} kaptan
            </div>
          )}
        </td>
        <td className="px-3 py-2.5 text-right num font-mono text-red-600">
          −{tr(r.kesinti_total + r.sabit_total)} ₺
        </td>
        <td className="px-3 py-2.5 text-right num font-display font-bold text-brand text-[14.5px] bg-brand-soft/40">
          {tr(r.net)} ₺
        </td>
        <td className="px-2 py-2.5 text-text-3 text-[12px] w-8">
          {open ? '▾' : '▸'}
        </td>
      </tr>

      {/* Detay paneli */}
      {open && (
        <tr className="bg-cream-50/50 border-b border-border">
          <td colSpan={8} className="px-5 py-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[12px]">
              {/* Brüt detay */}
              <div>
                <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-semibold mb-2">
                  📊 Brüt Hesabı
                </div>
                <div className="space-y-1">
                  <DetailRow
                    label="Ana atama"
                    value={`${tr(r.ana_brut)} ₺`}
                  />
                  {r.destek_brut > 0 && (
                    <DetailRow
                      label={`Destek (${r.destek_days} gün)`}
                      value={`+${tr(r.destek_brut)} ₺`}
                      color="text-orange-700"
                    />
                  )}
                  {r.kaptan_bonus > 0 && (
                    <DetailRow
                      label="Kaptan bonusu"
                      value={`+${tr(r.kaptan_bonus)} ₺`}
                      color="text-green-700"
                    />
                  )}
                  <div className="flex justify-between pt-1 border-t border-border font-semibold">
                    <span>Toplam Brüt</span>
                    <span className="num font-mono">{tr(r.toplam_brut)} ₺</span>
                  </div>
                </div>
                {r.destek_lines.length > 0 && (
                  <div className="mt-3 text-[11px] text-text-3">
                    Destek satırları:{' '}
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
              <div>
                <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-semibold mb-2">
                  📋 Sabit Kesintiler
                </div>
                <div className="space-y-1">
                  {r.motor_taksit > 0 && (
                    <DetailRow label="Motor taksiti" value={`−${tr(r.motor_taksit)} ₺`} color="text-red-600" />
                  )}
                  {r.muhasebe > 0 && (
                    <DetailRow label="ÇK Muhasebe bedeli" value={`−${tr(r.muhasebe)} ₺`} color="text-red-600" />
                  )}
                  {r.sirket_acilis > 0 && (
                    <DetailRow label="Şirket açılışı (1×)" value={`−${tr(r.sirket_acilis)} ₺`} color="text-red-600" />
                  )}
                  {r.sabit_total === 0 && (
                    <div className="text-text-3 italic">— sabit kesinti yok —</div>
                  )}
                  <div className="flex justify-between pt-1 border-t border-border font-semibold">
                    <span>Sabit Toplam</span>
                    <span className="num font-mono text-red-600">−{tr(r.sabit_total)} ₺</span>
                  </div>
                </div>
              </div>

              {/* Manuel + zimmet */}
              <div>
                <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-semibold mb-2">
                  🧾 Kesintiler & Zimmet
                </div>
                <div className="space-y-1">
                  {r.kesinti_groups.map((g) => (
                    <DetailRow
                      key={g.type}
                      label={`${g.type} (${g.count})`}
                      value={`−${tr(g.total)} ₺`}
                      color="text-red-600"
                    />
                  ))}
                  {r.kesinti_groups.length === 0 && (
                    <div className="text-text-3 italic">— kesinti yok —</div>
                  )}
                  <div className="flex justify-between pt-1 border-t border-border font-semibold">
                    <span>Manuel Toplam</span>
                    <span className="num font-mono text-red-600">−{tr(r.kesinti_total)} ₺</span>
                  </div>
                </div>
              </div>
            </div>
            {/* Net büyük */}
            <div className="mt-4 pt-3 border-t-2 border-brand/20 flex items-center justify-between">
              <div className="text-[11.5px] text-text-3">
                Brüt {tr(r.toplam_brut)} ₺ − Kesinti{' '}
                {tr(r.kesinti_total + r.sabit_total)} ₺ =
              </div>
              <div className="font-display text-2xl font-bold text-brand num">
                Net {tr(r.net)} ₺
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
