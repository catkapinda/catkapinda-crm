'use client';

import { useEffect, useState } from 'react';
import {
  AlertCircle, Box, CheckCircle2, Coins,
  Edit2, Loader2, Package, Plus, Search, Trash2, Users, X,
} from 'lucide-react';

import {
  createBoxReturn,
  deleteBoxReturn,
  getBoxReturns,
  listPersonnel,
  updateBoxReturn,
  type BoxReturn,
  type BoxReturnsListResponse,
  type Personnel,
  type SidebarCounts,
} from '@/lib/api';

const TR_MONTHS = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];

function m(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function tr(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR');
}
function fmtDate(d: string | null | undefined): string {
  if (!d) return '—';
  try {
    const [y, mo, da] = d.split('-').map(Number);
    if (!y || !mo || !da) return d;
    return `${da} ${TR_MONTHS[mo-1]} ${y}`;
  } catch {
    return d;
  }
}

function conditionTone(cond: string): { bg: string; text: string } {
  switch (cond) {
    case 'Sağlam': return { bg: 'bg-emerald-50', text: 'text-emerald-700' };
    case 'Hafif Hasarlı': return { bg: 'bg-amber-50', text: 'text-amber-700' };
    case 'Ağır Hasarlı': return { bg: 'bg-orange-50', text: 'text-orange-700' };
    case 'Kullanılamaz': return { bg: 'bg-rose-50', text: 'text-rose-700' };
    case 'Eksik': return { bg: 'bg-red-50', text: 'text-red-700' };
    default: return { bg: 'bg-bg-surface2', text: 'text-text-2' };
  }
}

export function BoxReturnsView({
  initial,
  counts,
}: {
  initial: BoxReturnsListResponse;
  counts?: SidebarCounts | null;
}) {
  void counts;
  const [data, setData] = useState<BoxReturnsListResponse>(initial);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [condition, setCondition] = useState<string>('');
  const [personnelId, setPersonnelId] = useState<number | null>(null);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const [personnel, setPersonnel] = useState<Personnel[]>([]);
  const [editing, setEditing] = useState<BoxReturn | null>(null);
  const [creating, setCreating] = useState(false);

  // Personel listesini bir kez çek (aktif)
  useEffect(() => {
    listPersonnel('Aktif')
      .then((data) => setPersonnel(data || []))
      .catch(() => setPersonnel([]));
  }, []);

  async function reload() {
    setLoading(true);
    try {
      const fresh = await getBoxReturns({
        search: search || undefined,
        condition: condition || undefined,
        personnel_id: personnelId || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      setData(fresh);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  // Filtreler değişince yenile (debounced search)
  useEffect(() => {
    const t = setTimeout(reload, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, condition, personnelId, dateFrom, dateTo]);

  const { items, summary, condition_options } = data;

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
              Operasyon · Saha Envanteri
            </div>
            <h1 className="text-4xl font-bold mb-1 flex items-center gap-3">
              <Box className="w-8 h-8" />
              Box Geri Alım
            </h1>
            <div className="text-white/80">
              Kuryeden teslim alınan ekipman takibi · {summary.records_count} kayıt
            </div>
          </div>
          <button
            onClick={() => setCreating(true)}
            className="px-4 py-2.5 rounded-xl bg-white text-brand text-sm font-semibold inline-flex items-center gap-2 shadow-md hover:shadow-lg transition"
          >
            <Plus className="w-4 h-4" strokeWidth={2.4} />
            Yeni Geri Alım
          </button>
        </div>
      </section>

      {/* ────────── KPI ────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={Package}
          label="Toplam Kayıt"
          value={tr(summary.records_count)}
          sub={`${tr(summary.total_quantity)} adet ekipman`}
          color="bg-blue-50 text-brand"
        />
        <KPICard
          icon={Users}
          label="Etkilenen Kurye"
          value={tr(summary.unique_personnel)}
          sub="Geri alım yapılan"
          color="bg-purple-50 text-purple-700"
        />
        <KPICard
          icon={Coins}
          label="Toplam Ödeme"
          value={m(summary.total_payout) + ' ₺'}
          sub="Kuryeye geri ödenen tutar"
          color="bg-amber-50 text-amber-700"
        />
        <KPICard
          icon={CheckCircle2}
          label="Muaf Tutulan"
          value={tr(summary.waived_count)}
          sub="Tahsil edilmeyen kayıt"
          color="bg-emerald-50 text-emerald-700"
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
              placeholder="Kurye, ekipman, not ara…"
              className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 transition"
            />
          </div>
          <select
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            className="px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none bg-white"
          >
            <option value="">Tüm kondisyon</option>
            {condition_options.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select
            value={personnelId ?? ''}
            onChange={(e) => setPersonnelId(e.target.value ? Number(e.target.value) : null)}
            className="px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none bg-white min-w-[180px]"
          >
            <option value="">Tüm kuryeler</option>
            {personnel
              .filter((p) => p.status === 'Aktif' || p.status === null)
              .map((p) => (
                <option key={p.id} value={p.id}>{p.full_name} ({p.person_code})</option>
              ))}
          </select>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none bg-white"
            title="Başlangıç tarihi"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none bg-white"
            title="Bitiş tarihi"
          />
          {(search || condition || personnelId || dateFrom || dateTo) && (
            <button
              onClick={() => {
                setSearch(''); setCondition(''); setPersonnelId(null);
                setDateFrom(''); setDateTo('');
              }}
              className="px-3 py-2.5 text-xs font-semibold text-text-3 hover:text-text-2 inline-flex items-center gap-1.5"
            >
              <X className="w-3.5 h-3.5" /> Temizle
            </button>
          )}
        </div>
      </section>

      {/* ────────── TABLE ────────── */}
      <section className="bg-white rounded-2xl border border-border overflow-hidden shadow-sm">
        {loading && (
          <div className="absolute top-3 right-3 text-text-3">
            <Loader2 className="w-4 h-4 animate-spin" />
          </div>
        )}
        {items.length === 0 ? (
          <div className="p-12 text-center">
            <Box className="w-12 h-12 mx-auto text-text-3 mb-3" strokeWidth={1.5} />
            <div className="text-text-2 font-medium mb-1">Henüz kayıt yok</div>
            <div className="text-text-3 text-sm">
              "Yeni Geri Alım" butonuyla ilk kaydı oluşturabilirsin.
            </div>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-bg-surface2">
              <tr>
                <Th>Tarih</Th>
                <Th>Kurye</Th>
                <Th>Ekipman</Th>
                <Th className="text-center">Adet</Th>
                <Th>Kondisyon</Th>
                <Th className="text-right">Ödeme</Th>
                <Th>Not</Th>
                <Th className="text-right">İşlem</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((row) => {
                const tone = conditionTone(row.condition_status);
                return (
                  <tr key={row.id} className="hover:bg-bg-surface2/60 transition group">
                    <td className="px-6 py-3.5">
                      <div className="text-sm font-medium text-text">{fmtDate(row.return_date)}</div>
                    </td>
                    <td className="px-6 py-3.5">
                      <div className="text-sm font-medium text-text">{row.personnel_name}</div>
                      <div className="text-xs text-text-3 mt-0.5">
                        {row.person_code}{row.rest_brand ? ` · ${row.rest_brand}` : ''}
                      </div>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 text-brand-dark text-xs font-semibold rounded-md">
                        <Package className="w-3 h-3" strokeWidth={2.4} />
                        {row.item_name}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-center text-sm font-bold text-text">
                      {row.quantity}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${tone.bg} ${tone.text}`}>
                        {row.condition_status}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <div className="text-sm font-semibold text-text">
                        {m(row.payout_amount)} ₺
                      </div>
                      {row.waived && (
                        <div className="text-[10px] text-text-3 mt-0.5 uppercase tracking-wider font-bold">
                          Muaf
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-3.5">
                      <div className="text-xs text-text-2 max-w-xs truncate">{row.notes || '—'}</div>
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <div className="inline-flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                        <button
                          onClick={() => setEditing(row)}
                          className="p-2 rounded-lg hover:bg-brand-soft text-text-3 hover:text-brand transition"
                          title="Düzenle"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={async () => {
                            if (!confirm(`${row.personnel_name} için ${fmtDate(row.return_date)} kaydını silmek istiyor musun?`)) return;
                            await deleteBoxReturn(row.id);
                            reload();
                          }}
                          className="p-2 rounded-lg hover:bg-rose-50 text-text-3 hover:text-rose-600 transition"
                          title="Sil"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      {/* ────────── MODAL ────────── */}
      {(creating || editing) && (
        <BoxReturnModal
          initial={editing}
          personnel={personnel}
          conditionOptions={condition_options}
          itemOptions={data.item_options}
          onClose={() => { setCreating(false); setEditing(null); }}
          onSaved={() => { setCreating(false); setEditing(null); reload(); }}
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

function KPICard({
  icon: Icon, label, value, sub, color,
}: {
  icon: typeof Package;
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
      <div className="text-2xl font-bold text-text mb-0.5">{value}</div>
      <div className="text-xs text-text-3">{sub}</div>
    </div>
  );
}

function BoxReturnModal({
  initial, personnel, conditionOptions, itemOptions, onClose, onSaved,
}: {
  initial: BoxReturn | null;
  personnel: Personnel[];
  conditionOptions: string[];
  itemOptions: string[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    personnel_id: initial?.personnel_id ?? 0,
    return_date: initial?.return_date ?? today,
    item_name: initial?.item_name ?? 'Box',
    quantity: initial?.quantity ?? 1,
    condition_status: initial?.condition_status ?? 'Sağlam',
    payout_amount: initial?.payout_amount ?? 0,
    waived: initial?.waived ?? false,
    notes: initial?.notes ?? '',
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.personnel_id) { setError('Kurye seçilmeli.'); return; }
    setSaving(true);
    setError(null);
    try {
      if (initial) {
        await updateBoxReturn(initial.id, form);
      } else {
        await createBoxReturn(form);
      }
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
        className="bg-white rounded-3xl shadow-2xl flex flex-col overflow-hidden w-full max-w-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="px-6 py-4 flex items-center justify-between border-b border-border"
          style={{ background: 'linear-gradient(135deg, #0A3F8F 0%, #0F52BA 60%, #2563EB 100%)' }}
        >
          <div className="text-white">
            <div className="text-[10px] uppercase tracking-[0.18em] font-bold opacity-80">
              {initial ? 'Geri Alım Düzenle' : 'Yeni Geri Alım'}
            </div>
            <div className="text-lg font-semibold mt-0.5 flex items-center gap-2">
              <Box className="w-5 h-5" /> {form.item_name}
            </div>
          </div>
          <button onClick={onClose} aria-label="Kapat" className="p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/15 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <Field label="Kurye *">
            <select
              value={form.personnel_id || ''}
              onChange={(e) => setForm({ ...form, personnel_id: Number(e.target.value) })}
              className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 bg-white"
              required
            >
              <option value="">Kurye seç…</option>
              {personnel.map((p) => (
                <option key={p.id} value={p.id}>{p.full_name} ({p.person_code})</option>
              ))}
            </select>
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Tarih *">
              <input
                type="date"
                value={form.return_date}
                onChange={(e) => setForm({ ...form, return_date: e.target.value })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
                required
              />
            </Field>
            <Field label="Ekipman">
              <select
                value={form.item_name}
                onChange={(e) => setForm({ ...form, item_name: e.target.value })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none bg-white"
              >
                {itemOptions.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Adet *">
              <input
                type="number"
                min={1}
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none"
                required
              />
            </Field>
            <Field label="Kondisyon *">
              <select
                value={form.condition_status}
                onChange={(e) => setForm({ ...form, condition_status: e.target.value })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none bg-white"
                required
              >
                {conditionOptions.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Ödeme (₺)">
              <input
                type="number"
                step="0.01"
                min={0}
                value={form.payout_amount}
                onChange={(e) => setForm({ ...form, payout_amount: Number(e.target.value) })}
                className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none"
              />
            </Field>
            <Field label="Muaf tutuldu mu?">
              <label className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-border text-sm cursor-pointer hover:border-brand/40 transition">
                <input
                  type="checkbox"
                  checked={form.waived}
                  onChange={(e) => setForm({ ...form, waived: e.target.checked })}
                  className="w-4 h-4 accent-brand"
                />
                <span className="text-text-2">Tahsil edilmedi</span>
              </label>
            </Field>
          </div>

          <Field label="Not">
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={3}
              className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 resize-none"
              placeholder="Opsiyonel açıklama…"
            />
          </Field>

          {error && (
            <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2 flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
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
