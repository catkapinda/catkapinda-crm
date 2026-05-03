'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';

import {
  type Deduction,
  type DeductionByType,
  type Personnel,
  createDeduction,
} from '@/lib/api';
import { normalizeTr } from '@/lib/format';

const TYPE_COLORS: Record<string, string> = {
  Yakıt: 'bg-orange-50 text-orange-700 border-orange-200',
  Avans: 'bg-purple-50 text-purple-700 border-purple-200',
  HGS: 'bg-blue-50 text-blue-700 border-blue-200',
  'Trafik Cezası': 'bg-red-50 text-red-700 border-red-200',
  'İdari Ceza': 'bg-red-50 text-red-700 border-red-200',
  Bakım: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  'Ağır Bakım': 'bg-yellow-100 text-yellow-800 border-yellow-300',
  Kaza: 'bg-red-100 text-red-800 border-red-300',
  Elcik: 'bg-bg-surface2 text-text-2 border-border',
  'Telefon Tutacağı': 'bg-bg-surface2 text-text-2 border-border',
  Kask: 'bg-bg-surface2 text-text-2 border-border',
  'Motor Hasar': 'bg-red-50 text-red-700 border-red-200',
  'Fatura Edilemeyen Tutar': 'bg-cream-100 text-yellow-900 border-yellow-200',
  'Zimmet Taksiti': 'bg-brand-soft text-brand border-brand/20',
};

function tr(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return iso;
  return `${m[3]}.${m[2]}.${m[1].slice(2)}`;
}

const PERIODS = ['2026-03', '2026-02', '2026-01'];

export function KesintilerView({
  deductions, personnel, typesByMonth, allTypes, period,
}: {
  deductions: Deduction[];
  personnel: Personnel[];
  typesByMonth: DeductionByType[];
  allTypes: string[];
  period: string;
}) {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    return deductions.filter((d) => {
      if (typeFilter && d.deduction_type !== typeFilter) return false;
      if (q) {
        const hay =
          `${d.personnel_name ?? ''} ${d.person_code ?? ''} ${d.deduction_type ?? ''} ${d.notes ?? ''}`
            .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [deductions, search, typeFilter]);

  const total = filtered.reduce((s, d) => s + d.amount, 0);
  const totalAll = deductions.reduce((s, d) => s + d.amount, 0);
  const uniquePersonnel = new Set(deductions.map((d) => d.personnel_id)).size;

  // Tip bazında ekstrayı UI için
  const topTypes = typesByMonth.slice(0, 6);

  return (
    <>
      {/* Header */}
      <header className="flex justify-between items-end gap-5 flex-wrap mb-5">
        <div>
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Operasyon · <span className="text-brand">Kesintiler</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            Kesintiler
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {formatPeriod(period)} · {deductions.length} kayıt ·{' '}
            {uniquePersonnel} kurye · toplam{' '}
            <strong className="text-brand">{tr(totalAll)} ₺</strong>
          </div>
        </div>
        <div className="flex gap-2 items-center">
          <div className="flex gap-1 bg-bg-surface border border-border rounded-xl p-1 shadow-sm">
            {PERIODS.map((p) => (
              <Link
                key={p}
                href={`/kesintiler?ay=${p}`}
                className={`px-2.5 py-1 rounded-lg text-[12.5px] font-medium transition ${
                  p === period
                    ? 'bg-brand text-white shadow-sm'
                    : 'text-text-2 hover:bg-bg-surface2'
                }`}
              >
                {formatPeriod(p)}
              </Link>
            ))}
          </div>
          <button
            onClick={() => setCreating(true)}
            className="px-4 py-2.5 rounded-xl bg-brand text-white text-sm font-semibold shadow-sm hover:bg-brand-dark transition flex items-center gap-2"
          >
            <span className="text-base">+</span>
            <span>Yeni Kesinti</span>
          </button>
        </div>
      </header>

      {/* Tip bazında özet hero */}
      {topTypes.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
          <button
            onClick={() => setTypeFilter(null)}
            className={`text-left bg-gradient-to-br rounded-2xl p-4 shadow-md transition hover:-translate-y-0.5 hover:shadow-lg ${
              typeFilter === null
                ? 'from-brand-dark to-brand text-white'
                : 'from-bg-surface to-bg-surface border border-border'
            }`}
          >
            <div
              className={`text-[10.5px] font-semibold uppercase tracking-wider ${
                typeFilter === null ? 'opacity-85' : 'text-text-3'
              }`}
            >
              Toplam
            </div>
            <div className="font-display text-[22px] font-bold tracking-tight num mt-1">
              {tr(totalAll)} ₺
            </div>
            <div
              className={`text-[10.5px] mt-1 ${
                typeFilter === null ? 'opacity-85' : 'text-text-3'
              }`}
            >
              {deductions.length} kayıt
            </div>
          </button>
          {topTypes.map((t) => {
            const active = typeFilter === t.deduction_type;
            return (
              <button
                key={t.deduction_type}
                onClick={() =>
                  setTypeFilter(active ? null : t.deduction_type)
                }
                className={`text-left rounded-2xl p-4 shadow-sm border transition hover:-translate-y-0.5 hover:shadow-md ${
                  active
                    ? 'border-brand bg-brand-soft shadow-md'
                    : 'border-border bg-bg-surface'
                }`}
              >
                <div className="text-[10.5px] font-semibold uppercase tracking-wider text-text-3">
                  {normalizeTr(t.deduction_type)}
                </div>
                <div
                  className={`font-display text-[19px] font-bold tracking-tight num mt-1 ${
                    active ? 'text-brand' : ''
                  }`}
                >
                  {tr(t.total)} ₺
                </div>
                <div className="text-[10.5px] mt-0.5 text-text-3">
                  {t.count} kayıt
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Toolbar */}
      <div className="bg-bg-surface border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2">
        <input
          type="search"
          placeholder="Kurye, kod, tip, not…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-1.5 rounded-lg border border-border text-sm w-64 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
        />
        {typeFilter && (
          <button
            onClick={() => setTypeFilter(null)}
            className="text-[12px] text-brand hover:underline"
          >
            ✕ {typeFilter} filtresini kaldır
          </button>
        )}
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
          {filtered.length} sonuç · {tr(total)} ₺
        </span>
      </div>

      {/* Tablo */}
      {filtered.length === 0 ? (
        <div className="bg-bg-surface border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
          Sonuç bulunamadı.
        </div>
      ) : (
        <div className="bg-bg-surface border border-border rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-[13px]">
            <thead className="bg-bg-surface2 text-text-3 text-[11px] uppercase tracking-wider">
              <tr>
                <th className="text-left px-3 py-2.5 font-semibold">Tarih</th>
                <th className="text-left px-3 py-2.5 font-semibold">Kurye</th>
                <th className="text-left px-3 py-2.5 font-semibold">Tip</th>
                <th className="text-left px-3 py-2.5 font-semibold">Açıklama</th>
                <th className="text-right px-3 py-2.5 font-semibold">Tutar</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => {
                const tc = TYPE_COLORS[d.deduction_type] ?? 'bg-bg-surface2 text-text-2 border-border';
                return (
                  <tr
                    key={d.id}
                    className="border-t border-border hover:bg-bg-surface2/40 transition"
                  >
                    <td className="px-3 py-2.5 font-mono text-[12px] text-text-2 whitespace-nowrap">
                      {formatDate(d.deduction_date)}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-text">
                        {d.personnel_name ?? '—'}
                      </div>
                      <div className="text-[10.5px] text-text-3 font-mono">
                        {d.person_code ?? ''}
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className={`px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold border ${tc} whitespace-nowrap`}
                      >
                        {normalizeTr(d.deduction_type)}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-[12px] text-text-2">
                      {d.notes ? (
                        normalizeTr(d.notes)
                      ) : d.equipment_name ? (
                        <span className="text-text-3">
                          {normalizeTr(d.equipment_name)}
                          {d.equipment_total_installments
                            ? ` · ${d.equipment_total_installments} taksit`
                            : ''}
                        </span>
                      ) : (
                        <span className="text-text-3">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono num font-semibold text-red-600">
                      −{tr(d.amount)} ₺
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-border bg-bg-surface2/50 font-semibold">
                <td colSpan={4} className="px-3 py-3 text-text">
                  Filtrelenmiş Toplam
                </td>
                <td className="px-3 py-3 text-right font-display text-brand text-[15px] num">
                  {tr(total)} ₺
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {creating && (
        <NewDeductionModal
          personnel={personnel}
          types={allTypes}
          onClose={() => setCreating(false)}
        />
      )}
    </>
  );
}

function formatPeriod(period: string): string {
  const months = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
    'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
  const [y, m] = period.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return period;
  return `${months[m - 1]} ${y}`;
}

function NewDeductionModal({
  personnel, types, onClose,
}: {
  personnel: Personnel[];
  types: string[];
  onClose: () => void;
}) {
  const router = useRouter();
  const [form, setForm] = useState({
    personnel_id: 0,
    deduction_type: types[0] ?? 'Yakıt',
    amount: 0,
    deduction_date: new Date().toISOString().slice(0, 10),
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.personnel_id || !form.amount) {
      setError('Kurye ve tutar gerekli');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createDeduction(form);
      onClose();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kaydedilemedi');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-start justify-center p-4 overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-bg-surface rounded-2xl shadow-2xl w-full max-w-lg my-8 border border-border">
        <div className="bg-gradient-to-r from-brand-dark to-brand text-white px-6 py-4 rounded-t-2xl flex justify-between items-start">
          <div>
            <div className="text-[11px] uppercase tracking-wider opacity-80 font-semibold">
              Yeni Kesinti
            </div>
            <div className="font-display text-lg font-semibold tracking-tight mt-0.5">
              Kuryenin hakedişinden düşülecek tutar
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-white/80 hover:text-white text-2xl leading-none w-8 h-8 flex items-center justify-center rounded-md hover:bg-white/10 transition"
          >
            ×
          </button>
        </div>

        <form onSubmit={submit} className="p-5 space-y-4">
          <label className="block">
            <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
              Kurye *
            </span>
            <select
              value={form.personnel_id}
              onChange={(e) =>
                setForm((p) => ({ ...p, personnel_id: parseInt(e.target.value, 10) || 0 }))
              }
              className="input"
              required
            >
              <option value={0}>— seç —</option>
              {personnel.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.full_name} ({p.person_code})
                </option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
                Tip *
              </span>
              <select
                value={form.deduction_type}
                onChange={(e) =>
                  setForm((p) => ({ ...p, deduction_type: e.target.value }))
                }
                className="input"
              >
                {types.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
                Tutar (₺) *
              </span>
              <input
                type="number"
                step="any"
                value={form.amount || ''}
                onChange={(e) =>
                  setForm((p) => ({ ...p, amount: parseFloat(e.target.value) || 0 }))
                }
                className="input num"
                required
              />
            </label>
          </div>

          <label className="block">
            <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
              Tarih
            </span>
            <input
              type="date"
              value={form.deduction_date}
              onChange={(e) =>
                setForm((p) => ({ ...p, deduction_date: e.target.value }))
              }
              className="input"
            />
          </label>

          <label className="block">
            <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
              Açıklama
            </span>
            <input
              type="text"
              value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
              placeholder="örn. 31.03 yakıt fişi"
              className="input"
            />
          </label>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-2.5 text-red-700 text-[12px]">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium text-text-2 hover:bg-bg-surface2 transition"
              disabled={saving}
            >
              Vazgeç
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-brand text-white shadow-sm hover:bg-brand-dark transition disabled:opacity-60"
            >
              {saving ? 'Kaydediliyor…' : '+ Kesintiyi Ekle'}
            </button>
          </div>
        </form>

        <style jsx>{`
          :global(.input) {
            width: 100%;
            padding: 9px 12px;
            border-radius: 10px;
            border: 1px solid var(--border, #E2E5EC);
            background: var(--bg-surface, #FFFFFF);
            font-size: 13.5px;
            color: var(--text, #0B0D17);
            transition: border-color 0.15s, box-shadow 0.15s;
          }
          :global(.input:focus) {
            outline: none;
            border-color: #0F52BA;
            box-shadow: 0 0 0 3px rgba(15, 82, 186, 0.12);
          }
        `}</style>
      </div>
    </div>
  );
}
