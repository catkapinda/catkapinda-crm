'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, ArrowDownToLine, Building2, Check, CheckCircle2,
  Clock, Filter, Receipt, Search, TrendingUp, Wallet, X,
} from 'lucide-react';

import {
  type InvoiceSummary,
  type RestaurantInvoice,
  markInvoicePaid,
  upsertInvoice,
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

function kCompact(value: number | null | undefined): string {
  if (value == null) return '—';
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return value.toLocaleString('tr-TR', { maximumFractionDigits: 0 });
}

type StatusKey = 'all' | 'Beklemede' | 'Kısmi' | 'Ödendi';

const STATUS_META: Record<string, { color: string; bg: string; text: string; ring: string }> = {
  'Beklemede': {
    color: 'orange',
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    ring: 'border-orange-200',
  },
  'Kısmi': {
    color: 'blue',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    ring: 'border-blue-200',
  },
  'Ödendi': {
    color: 'green',
    bg: 'bg-green-50',
    text: 'text-green-700',
    ring: 'border-green-200',
  },
};

export function FaturalarView({
  invoices, summary, period,
}: {
  invoices: RestaurantInvoice[];
  summary: InvoiceSummary | null;
  period: string;
}) {
  const router = useRouter();
  const [statusTab, setStatusTab] = useState<StatusKey>('all');
  const [search, setSearch] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingInvoice, setEditingInvoice] = useState<RestaurantInvoice | null>(null);

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    return invoices.filter((inv) => {
      if (statusTab !== 'all' && inv.status !== statusTab) return false;
      if (q) {
        const hay = `${inv.rest_brand ?? ''} ${inv.rest_branch ?? ''} ${inv.invoice_no ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [invoices, statusTab, search]);

  const filteredTotals = useMemo(() => {
    const t = { excl: 0, vat: 0, incl: 0, paid: 0, balance: 0 };
    for (const i of filtered) {
      t.excl += i.amount_excl_vat;
      t.vat += i.vat_amount;
      t.incl += i.amount_incl_vat;
      t.paid += i.paid_amount;
      t.balance += i.balance;
    }
    return t;
  }, [filtered]);

  async function handleMarkPaid(inv: RestaurantInvoice, fullPayment: boolean) {
    if (busyId != null) return;
    const amount = fullPayment ? inv.amount_incl_vat : 0;
    const action = fullPayment ? 'ÖDENDİ' : 'BEKLEMEDE';
    if (!confirm(
      `${inv.rest_brand} ${inv.rest_branch ?? ''} faturasını ${action} olarak işaretle?\n` +
      `Tutar: ${m(inv.amount_incl_vat)} ₺ (KDV dahil)`
    )) return;
    setBusyId(inv.restaurant_id);
    setError(null);
    try {
      await markInvoicePaid(inv.restaurant_id, period, amount);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Güncellenemedi');
    } finally {
      setBusyId(null);
    }
  }

  async function handlePartialPay(inv: RestaurantInvoice) {
    const ans = prompt(
      `${inv.rest_brand} — ödenen tutarı gir (₺):\n` +
      `(Toplam: ${m(inv.amount_incl_vat)})`,
      String(inv.paid_amount || ''),
    );
    if (ans == null) return;
    const amt = parseFloat(ans.replace(',', '.'));
    if (isNaN(amt) || amt < 0) {
      setError('Geçersiz tutar');
      return;
    }
    setBusyId(inv.restaurant_id);
    setError(null);
    try {
      await markInvoicePaid(inv.restaurant_id, period, amt);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Güncellenemedi');
    } finally {
      setBusyId(null);
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
              ? `${summary.count_total} restoran · toplam ${m(summary.sum_incl_vat)} ₺ (KDV dahil) · tahsilat ${summary.collection_pct.toFixed(1)}%`
              : '— veri yükleniyor —'}
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
          icon={<CheckCircle2 className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="success"
          label="Tahsil Edilen"
          value={summary ? m(summary.sum_paid) : '—'}
          suffix="₺"
          sub={summary ? `${summary.count_paid} ödendi · ${summary.count_partial} kısmi` : ''}
        />
        <KpiCard
          icon={<Clock className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="warn"
          label="Bekleyen Bakiye"
          value={summary ? m(summary.sum_balance) : '—'}
          suffix="₺"
          sub={summary ? `${summary.count_pending} bekleyen fatura` : ''}
        />
        <KpiCard
          icon={<TrendingUp className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="purple"
          label="Tahsilat Oranı"
          value={summary ? `%${summary.collection_pct.toFixed(1)}` : '—'}
          sub="ödenen / toplam"
        />
      </div>

      {/* STATUS TABS + SEARCH */}
      <div className="bg-white border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2 sticky top-2 z-10 backdrop-blur-sm">
        <div className="flex items-center gap-1 bg-bg-surface2 rounded-lg p-1">
          {(['all', 'Beklemede', 'Kısmi', 'Ödendi'] as StatusKey[]).map((s) => {
            const active = statusTab === s;
            const label = s === 'all' ? 'Tümü' : s;
            const count = s === 'all'
              ? invoices.length
              : invoices.filter((i) => i.status === s).length;
            const tone = s === 'Beklemede' ? 'bg-orange-600' : s === 'Kısmi' ? 'bg-blue-600' : s === 'Ödendi' ? 'bg-green-600' : 'bg-text';
            return (
              <button
                key={s}
                onClick={() => setStatusTab(s)}
                className={`px-3 py-1.5 rounded-md text-[12.5px] font-semibold transition flex items-center gap-1.5 ${
                  active ? `${tone} text-white shadow` : 'text-text-2 hover:bg-white'
                }`}
              >
                {label}
                <span className={`px-1.5 py-px rounded-full text-[10px] tabular-nums ${
                  active ? 'bg-white/25 text-white' : 'bg-bg-surface text-text-3'
                }`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="relative flex items-center ml-2">
          <Search className="w-3.5 h-3.5 absolute left-2.5 text-text-3" strokeWidth={2.2} />
          <input
            type="search"
            placeholder="Restoran / fatura no ara…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1.5 rounded-lg border border-border text-sm w-64 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
          />
        </div>

        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto inline-flex items-center gap-1">
          <Filter className="w-3 h-3" strokeWidth={2.2} />
          {filtered.length} sonuç · KDV dahil <span className="text-brand font-mono">{m(filteredTotals.incl)} ₺</span>
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
          <div className="text-text-2 font-medium">Bu sekmede fatura yok.</div>
        </div>
      ) : (
        <div className="bg-white border border-border rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-[13px]">
            <thead className="bg-cream-50/80 text-text-3 text-[10.5px] uppercase tracking-[0.08em] border-b border-border">
              <tr>
                <th className="text-left px-4 py-3 font-bold">Restoran</th>
                <th className="text-left px-3 py-3 font-bold">Fatura No</th>
                <th className="text-right px-3 py-3 font-bold">Kurye</th>
                <th className="text-right px-3 py-3 font-bold">KDV Hariç</th>
                <th className="text-right px-3 py-3 font-bold">KDV</th>
                <th className="text-right px-3 py-3 font-bold bg-brand-soft/60 text-brand">KDV Dahil</th>
                <th className="text-right px-3 py-3 font-bold">Ödenen</th>
                <th className="text-right px-3 py-3 font-bold">Bakiye</th>
                <th className="text-center px-3 py-3 font-bold">Durum</th>
                <th className="text-center px-3 py-3 font-bold">Aksiyon</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((inv) => (
                <InvoiceRow
                  key={`${inv.restaurant_id}-${period}`}
                  inv={inv}
                  busy={busyId === inv.restaurant_id}
                  onMarkPaid={() => handleMarkPaid(inv, true)}
                  onUnmark={() => handleMarkPaid(inv, false)}
                  onPartial={() => handlePartialPay(inv)}
                />
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-brand/30 bg-gradient-to-r from-brand-soft/50 to-transparent font-semibold">
                <td colSpan={3} className="px-4 py-3 text-text text-[12.5px]">
                  Toplam ({filtered.length} restoran)
                </td>
                <td className="px-3 py-3 text-right num font-mono text-text tabular-nums">
                  {m(filteredTotals.excl)} ₺
                </td>
                <td className="px-3 py-3 text-right num font-mono text-text-2 tabular-nums">
                  {m(filteredTotals.vat)} ₺
                </td>
                <td className="px-3 py-3 text-right font-display text-brand text-[15px] num bg-brand-soft tabular-nums">
                  {m(filteredTotals.incl)} ₺
                </td>
                <td className="px-3 py-3 text-right num font-mono text-green-700 tabular-nums">
                  {m(filteredTotals.paid)} ₺
                </td>
                <td className="px-3 py-3 text-right num font-mono text-orange-700 tabular-nums">
                  {m(filteredTotals.balance)} ₺
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
  inv, busy, onMarkPaid, onUnmark, onPartial,
}: {
  inv: RestaurantInvoice;
  busy: boolean;
  onMarkPaid: () => void;
  onUnmark: () => void;
  onPartial: () => void;
}) {
  const meta = STATUS_META[inv.status] ?? STATUS_META['Beklemede'];

  return (
    <tr className="border-t border-border/70 hover:bg-cream-50/70 transition group">
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

      {/* Fatura no */}
      <td className="px-3 py-2.5">
        <span className={`text-[11.5px] font-mono ${inv.invoice_no ? 'text-text-2' : 'text-text-3 italic'}`}>
          {inv.invoice_no ?? '— atanmamış'}
        </span>
      </td>

      {/* Kurye sayısı */}
      <td className="px-3 py-2.5 text-right num font-mono text-[12.5px] text-text-2 tabular-nums">
        {inv.courier_count}
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

      {/* Ödenen */}
      <td className="px-3 py-2.5 text-right num font-mono text-[12.5px] text-green-700 tabular-nums">
        {inv.paid_amount > 0 ? m(inv.paid_amount) : <span className="text-text-3">—</span>}
      </td>

      {/* Bakiye */}
      <td className="px-3 py-2.5 text-right num font-mono text-[12.5px] text-orange-700 tabular-nums">
        {inv.balance > 0 ? m(inv.balance) : <span className="text-text-3">0,00</span>}
      </td>

      {/* Durum */}
      <td className="px-3 py-2.5 text-center">
        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-bold ${meta.bg} ${meta.text}`}>
          {inv.status === 'Ödendi' && <CheckCircle2 className="w-3 h-3" strokeWidth={2.4} />}
          {inv.status === 'Beklemede' && <Clock className="w-3 h-3" strokeWidth={2.4} />}
          {inv.status === 'Kısmi' && <Wallet className="w-3 h-3" strokeWidth={2.4} />}
          {inv.status}
        </span>
      </td>

      {/* Aksiyon */}
      <td className="px-3 py-2.5 text-center">
        <div className="inline-flex items-center gap-1">
          {inv.status === 'Ödendi' ? (
            <button
              onClick={onUnmark}
              disabled={busy}
              className="px-2 py-1 rounded-md bg-white border border-border text-text-3 text-[10.5px] font-semibold hover:bg-cream-50 transition disabled:opacity-50"
              title="Ödendi işaretini kaldır"
            >
              Geri al
            </button>
          ) : (
            <>
              <button
                onClick={onMarkPaid}
                disabled={busy}
                className="px-2 py-1 rounded-md bg-green-600 text-white text-[10.5px] font-semibold hover:bg-green-700 transition disabled:opacity-50 inline-flex items-center gap-1"
                title="Tamamen ödendi olarak işaretle"
              >
                <Check className="w-3 h-3" strokeWidth={2.4} /> Ödendi
              </button>
              <button
                onClick={onPartial}
                disabled={busy}
                className="px-2 py-1 rounded-md bg-white border border-border text-text-2 text-[10.5px] font-semibold hover:border-brand hover:text-brand transition disabled:opacity-50"
                title="Kısmi ödeme gir"
              >
                Kısmi
              </button>
            </>
          )}
          {/* Detay link — restoran sayfasına */}
          <Link
            href={`/restoranlar/${inv.restaurant_id}?ay=${encodeURIComponent(inv.period)}`}
            className="px-1.5 py-1 rounded-md text-text-3 hover:text-brand hover:bg-brand-soft transition"
            title="Restoran detay"
          >
            <Building2 className="w-3.5 h-3.5" strokeWidth={2.2} />
          </Link>
        </div>
      </td>
    </tr>
  );
}
