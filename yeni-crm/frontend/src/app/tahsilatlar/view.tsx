'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, AlertTriangle, Calendar, Check, CheckCircle2,
  ChevronDown, Clock, Coins, Edit3, Loader2, Phone, Search,
  TrendingUp, Users, Wallet, X,
} from 'lucide-react';

import {
  getCollections,
  upsertCollection,
  type CollectionItem,
  type CollectionsListResponse,
  type SidebarCounts,
} from '@/lib/api';

const TR_MONTHS = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
const MIN_PERIOD = '2026-03';

function formatPeriod(p: string) {
  const [y, m] = p.split('-').map(Number);
  if (!y || !m) return p;
  return `${TR_MONTHS[m-1]} ${y}`;
}
function recentPeriodOptions(max = 6) {
  const now = new Date();
  const out: { value: string; label: string }[] = [];
  for (let i = 0; i < max; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const v = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
    out.push({ value: v, label: `${TR_MONTHS[d.getMonth()]} ${d.getFullYear()}` });
    if (v === MIN_PERIOD) break;
  }
  return out;
}

function m(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function tr(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR');
}
function fmtDate(d: string | null | undefined) {
  if (!d) return '—';
  const [y, mo, da] = d.split('-').map(Number);
  if (!y || !mo || !da) return d;
  return `${da} ${TR_MONTHS[mo-1]}`;
}

function statusTone(status: string, isOverdue: boolean): { bg: string; text: string; border: string } {
  if (isOverdue) return { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' };
  switch (status) {
    case 'Tahsil Edildi': return { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' };
    case 'Kısmi Tahsilat': return { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' };
    case 'Geciken': return { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' };
    case 'İptal': return { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200' };
    case 'Bekliyor':
    default: return { bg: 'bg-blue-50', text: 'text-brand-dark', border: 'border-blue-200' };
  }
}

export function TahsilatlarView({
  initial,
  period,
  counts,
}: {
  initial: CollectionsListResponse | null;
  period: string;
  counts?: SidebarCounts | null;
}) {
  void counts;
  const router = useRouter();
  const [data, setData] = useState<CollectionsListResponse | null>(initial);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [editing, setEditing] = useState<CollectionItem | null>(null);

  // Period selector
  const periodOptions = useMemo(() => recentPeriodOptions(6), []);
  const [pickerOpen, setPickerOpen] = useState(false);

  async function reload(p: string = period) {
    setLoading(true);
    try {
      const fresh = await getCollections({
        period: p,
        status: statusFilter || undefined,
        search: search || undefined,
      });
      setData(fresh);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  // Debounced filter reload
  useEffect(() => {
    const t = setTimeout(() => reload(period), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, statusFilter]);

  function changePeriod(p: string) {
    setPickerOpen(false);
    if (p === period) return;
    router.push(`/tahsilatlar?period=${p}`);
  }

  const items = data?.items ?? [];
  const summary = data?.summary;
  const statusOptions = data?.status_options ?? ['Bekliyor', 'Kısmi Tahsilat', 'Tahsil Edildi', 'Geciken', 'İptal'];

  return (
    <div className="flex-1 flex flex-col gap-6 p-6">
      {/* ────────── HERO ────────── */}
      <section className="relative overflow-hidden rounded-3xl shadow-lg">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-dark via-brand to-blue-600" />
        <div
          className="absolute inset-0 opacity-30 mix-blend-overlay"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 20%, rgba(255,255,255,.4) 0%, transparent 40%), radial-gradient(circle at 80% 70%, rgba(255,200,100,.3) 0%, transparent 50%)',
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />
        <div className="relative px-7 py-7 text-white flex items-start justify-between gap-6">
          <div>
            <div className="text-[11px] font-medium tracking-[0.2em] uppercase text-white/70 mb-2 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-yellow-300 animate-pulse" />
              Finans · Tahsilat Takibi
            </div>
            <h1 className="text-4xl font-bold mb-1 flex items-center gap-3">
              <Coins className="w-8 h-8" />
              Tahsilatlar
            </h1>
            <div className="text-white/80">
              {formatPeriod(period)} dönemi · {summary?.restaurant_count ?? 0} restoran
            </div>
          </div>
          <div className="relative">
            <button
              onClick={() => setPickerOpen((v) => !v)}
              className="px-3.5 py-2 rounded-lg bg-white/15 backdrop-blur-sm border border-white/25 text-white text-xs font-semibold hover:bg-white/25 transition inline-flex items-center gap-2"
            >
              <Calendar className="w-3.5 h-3.5" strokeWidth={2.2} />
              <span>{formatPeriod(period)}</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${pickerOpen ? 'rotate-180' : ''}`} strokeWidth={2.4} />
            </button>
            {pickerOpen && (
              <>
                <div className="fixed inset-0 z-30" onClick={() => setPickerOpen(false)} />
                <div className="absolute right-0 mt-1.5 z-40 w-52 bg-white border border-border rounded-xl shadow-2xl overflow-hidden">
                  <div className="px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-text-3 border-b border-border/60">
                    Dönem seç
                  </div>
                  {periodOptions.map((opt) => {
                    const active = opt.value === period;
                    return (
                      <button
                        key={opt.value}
                        onClick={() => changePeriod(opt.value)}
                        className={`w-full text-left px-3 py-2 text-xs font-semibold flex items-center justify-between transition ${
                          active ? 'bg-brand-soft text-brand' : 'text-text-2 hover:bg-bg-surface2'
                        }`}
                      >
                        <span>{opt.label}</span>
                        {active && <Check className="w-3.5 h-3.5" strokeWidth={3} />}
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ────────── KPI ────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={Wallet}
          label="Toplam Fatura"
          value={m(summary?.total_invoice ?? 0) + ' ₺'}
          sub={`${tr(summary?.restaurant_count ?? 0)} restoran`}
          color="bg-blue-50 text-brand"
        />
        <KPICard
          icon={CheckCircle2}
          label="Tahsil Edilen"
          value={m(summary?.total_collected ?? 0) + ' ₺'}
          sub={`${tr(summary?.collected_count ?? 0)} restoran tamamlandı`}
          color="bg-emerald-50 text-emerald-700"
        />
        <KPICard
          icon={Clock}
          label="Bekleyen"
          value={m(summary?.total_open ?? 0) + ' ₺'}
          sub={`${tr(summary?.pending_count ?? 0)} restoran açık`}
          color="bg-amber-50 text-amber-700"
        />
        <KPICard
          icon={AlertTriangle}
          label="Geciken"
          value={m(summary?.overdue_amount ?? 0) + ' ₺'}
          sub={`${tr(summary?.overdue_count ?? 0)} restoran vadesi geçti`}
          color="bg-rose-50 text-rose-700"
        />
      </div>

      {/* ────────── FILTERS ────────── */}
      <section className="bg-white rounded-2xl border border-border p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Restoran, sorumlu, not ara…"
              className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <StatusChip
              active={statusFilter === ''}
              onClick={() => setStatusFilter('')}
              label="Tümü"
              count={summary?.restaurant_count ?? 0}
              tone="default"
            />
            <StatusChip
              active={statusFilter === 'Bekliyor'}
              onClick={() => setStatusFilter('Bekliyor')}
              label="Bekliyor"
              count={summary?.pending_count ?? 0}
              tone="info"
            />
            <StatusChip
              active={statusFilter === 'Tahsil Edildi'}
              onClick={() => setStatusFilter('Tahsil Edildi')}
              label="Tahsil Edildi"
              count={summary?.collected_count ?? 0}
              tone="success"
            />
            <StatusChip
              active={statusFilter === 'Geciken'}
              onClick={() => setStatusFilter('Geciken')}
              label="Geciken"
              count={summary?.overdue_count ?? 0}
              tone="danger"
            />
          </div>
        </div>
      </section>

      {/* ────────── TABLE ────────── */}
      <section className="bg-white rounded-2xl border border-border overflow-hidden shadow-sm relative">
        {loading && (
          <div className="absolute top-3 right-3 text-text-3 z-10">
            <Loader2 className="w-4 h-4 animate-spin" />
          </div>
        )}
        {items.length === 0 ? (
          <div className="p-12 text-center">
            <Coins className="w-12 h-12 mx-auto text-text-3 mb-3" strokeWidth={1.5} />
            <div className="text-text-2 font-medium mb-1">Bu kriterlere uyan tahsilat yok</div>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-bg-surface2">
              <tr>
                <Th>Restoran</Th>
                <Th>Durum</Th>
                <Th className="text-right">Fatura</Th>
                <Th className="text-right">Tahsil Edilen</Th>
                <Th className="text-right">Kalan</Th>
                <Th>Vade</Th>
                <Th>Son Temas</Th>
                <Th>Sorumlu</Th>
                <Th className="text-right">İşlem</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((row, idx) => {
                const tone = statusTone(row.status, row.is_overdue);
                return (
                  <tr key={`${row.restaurant_id}-${idx}`} className="hover:bg-bg-surface2/60 transition group">
                    <td className="px-6 py-3.5">
                      <div className="text-sm font-medium text-text">{row.brand}</div>
                      {row.branch && <div className="text-xs text-text-3 mt-0.5">{row.branch}</div>}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${tone.bg} ${tone.text} ${tone.border}`}>
                        {row.is_overdue && <AlertTriangle className="w-3 h-3" strokeWidth={2.4} />}
                        {row.is_overdue ? 'Geciken' : row.status}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-right text-sm font-medium text-text">
                      {m(row.invoice_amount)} ₺
                    </td>
                    <td className="px-6 py-3.5 text-right text-sm font-semibold text-emerald-700">
                      {m(row.collected_amount)} ₺
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <span className={`text-sm font-bold ${row.remaining_amount > 0 ? 'text-rose-700' : 'text-text-3'}`}>
                        {m(row.remaining_amount)} ₺
                      </span>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`text-xs ${row.is_overdue ? 'font-bold text-rose-700' : 'text-text-2'}`}>
                        {fmtDate(row.due_date)}
                      </span>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="text-xs text-text-2 inline-flex items-center gap-1.5">
                        {row.last_contact_date && <Phone className="w-3 h-3 text-text-3" />}
                        {fmtDate(row.last_contact_date)}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-xs text-text-2">
                      {row.responsible_name || '—'}
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <button
                        onClick={() => setEditing(row)}
                        className="opacity-0 group-hover:opacity-100 transition p-2 rounded-lg hover:bg-brand-soft text-text-3 hover:text-brand"
                        title="Düzenle"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      {editing && (
        <CollectionModal
          item={editing}
          period={period}
          statusOptions={statusOptions}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload(); }}
        />
      )}
    </div>
  );
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <th className={`px-6 py-3 text-xs font-bold uppercase tracking-wider text-text-3 ${className}`}>
      {children}
    </th>
  );
}

function StatusChip({
  active, onClick, label, count, tone,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
  tone: 'default' | 'info' | 'success' | 'danger';
}) {
  const styles = active
    ? {
        default: 'bg-text text-white border-text',
        info: 'bg-brand text-white border-brand',
        success: 'bg-emerald-600 text-white border-emerald-600',
        danger: 'bg-rose-600 text-white border-rose-600',
      }[tone]
    : 'bg-white text-text-2 border-border hover:border-brand/40';

  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition inline-flex items-center gap-1.5 ${styles}`}
    >
      <span>{label}</span>
      <span className={`text-[10px] tabular-nums ${active ? 'opacity-90' : 'opacity-60'}`}>
        {count}
      </span>
    </button>
  );
}

function KPICard({
  icon: Icon, label, value, sub, color,
}: {
  icon: typeof Wallet;
  label: string;
  value: string;
  sub: string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-2xl border border-border p-5 shadow-sm hover:shadow-md transition">
      <div className={`inline-flex p-2.5 rounded-xl ${color} mb-3`}>
        <Icon className="w-4 h-4" strokeWidth={2.2} />
      </div>
      <div className="text-xs text-text-3 font-semibold uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className="text-xl font-bold text-text mb-0.5">{value}</div>
      <div className="text-xs text-text-3">{sub}</div>
    </div>
  );
}

function CollectionModal({
  item, period, statusOptions, onClose, onSaved,
}: {
  item: CollectionItem;
  period: string;
  statusOptions: string[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    invoice_amount: item.invoice_amount ?? 0,
    collected_amount: item.collected_amount ?? 0,
    status: item.status,
    due_date: item.due_date ?? '',
    last_contact_date: item.last_contact_date ?? '',
    payment_date: item.paid_at ?? '',
    responsible_name: item.responsible_name ?? '',
    note: item.note ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const remaining = Math.max(0, form.invoice_amount - form.collected_amount);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await upsertCollection({
        restaurant_id: item.restaurant_id,
        collection_month: period,
        invoice_amount: form.invoice_amount,
        collected_amount: form.collected_amount,
        status: form.status,
        due_date: form.due_date || null,
        last_contact_date: form.last_contact_date || null,
        responsible_name: form.responsible_name,
        note: form.note,
        // payment_date for paid_at
        ...(form.payment_date ? { paid_at: form.payment_date } as Partial<CollectionItem> : {}),
      });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Kayıt başarısız.');
    } finally {
      setSaving(false);
    }
  }

  async function markCollected() {
    setSaving(true);
    setError(null);
    try {
      await upsertCollection({
        restaurant_id: item.restaurant_id,
        collection_month: period,
        invoice_amount: form.invoice_amount,
        collected_amount: form.invoice_amount, // tam tahsilat
        status: 'Tahsil Edildi',
        due_date: form.due_date || null,
        last_contact_date: today,
        responsible_name: form.responsible_name,
        note: form.note,
      });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Kayıt başarısız.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(11,13,23,0.55)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-3xl shadow-2xl flex flex-col overflow-hidden w-full max-w-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="px-6 py-4 flex items-center justify-between border-b border-border"
          style={{ background: 'linear-gradient(135deg, #0A3F8F 0%, #0F52BA 60%, #2563EB 100%)' }}
        >
          <div className="text-white">
            <div className="text-[10px] uppercase tracking-[0.18em] font-bold opacity-80">
              {formatPeriod(period)} · Tahsilat Düzenle
            </div>
            <div className="text-lg font-semibold mt-0.5">
              {item.brand}{item.branch ? ` · ${item.branch}` : ''}
            </div>
          </div>
          <button onClick={onClose} aria-label="Kapat" className="p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/15 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Fatura Tutarı (₺) *">
              <input
                type="number"
                step="0.01"
                min={0}
                value={form.invoice_amount}
                onChange={(e) => setForm({ ...form, invoice_amount: Number(e.target.value) })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none"
              />
            </Field>
            <Field label="Tahsil Edilen (₺)">
              <input
                type="number"
                step="0.01"
                min={0}
                value={form.collected_amount}
                onChange={(e) => setForm({ ...form, collected_amount: Number(e.target.value) })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none"
              />
            </Field>
          </div>

          {form.invoice_amount > 0 && (
            <div className={`rounded-lg p-3 border ${remaining > 0 ? 'bg-rose-50 border-rose-200' : 'bg-emerald-50 border-emerald-200'}`}>
              <div className="text-[10px] uppercase tracking-wider font-bold text-text-3 mb-0.5">
                Kalan tutar
              </div>
              <div className={`text-lg font-bold ${remaining > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
                {m(remaining)} ₺
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <Field label="Durum">
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none bg-white"
              >
                {statusOptions.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="Vade Tarihi">
              <input
                type="date"
                value={form.due_date || ''}
                onChange={(e) => setForm({ ...form, due_date: e.target.value })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none"
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Son Temas Tarihi">
              <input
                type="date"
                value={form.last_contact_date || ''}
                onChange={(e) => setForm({ ...form, last_contact_date: e.target.value })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none"
              />
            </Field>
            <Field label="Sorumlu">
              <input
                type="text"
                value={form.responsible_name}
                onChange={(e) => setForm({ ...form, responsible_name: e.target.value })}
                placeholder="Tahsilatı takip eden kişi"
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none"
              />
            </Field>
          </div>

          <Field label="Not">
            <textarea
              value={form.note}
              onChange={(e) => setForm({ ...form, note: e.target.value })}
              rows={3}
              className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 resize-none"
              placeholder="Görüşme notu, anlaşılan ödeme planı, vs."
            />
          </Field>

          {error && (
            <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2 flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {error}
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={markCollected}
              disabled={saving || form.invoice_amount <= 0}
              className="inline-flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition disabled:opacity-50"
              title="Faturanın tamamı tahsil edildi olarak işaretle"
            >
              <CheckCircle2 className="w-4 h-4" />
              Tamamen Tahsil Edildi
            </button>
            <div className="flex items-center gap-2">
              <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium rounded-lg border border-border text-text-2 hover:bg-bg-surface2 transition">
                Vazgeç
              </button>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-brand text-white hover:bg-brand-dark transition disabled:opacity-60"
              >
                {saving ? <><Loader2 className="w-4 h-4 animate-spin" />Kaydediliyor…</> : 'Kaydet'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-text-3 uppercase tracking-wider mb-1.5">
        {label}
      </label>
      {children}
    </div>
  );
}
