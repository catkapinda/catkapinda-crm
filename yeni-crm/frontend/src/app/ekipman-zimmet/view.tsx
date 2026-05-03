'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';

import {
  type EquipmentAssignment,
  type EquipmentCatalogItem,
  type Personnel,
  createEquipmentAssignment,
} from '@/lib/api';
import { normalizeTr } from '@/lib/format';

const ITEM_ICONS: Record<string, string> = {
  'Korumalı Mont': '🧥',
  Yağmurluk: '🌧️',
  Tshirt: '👕',
  Polar: '🧶',
  Yelek: '🦺',
  'Göğüs Çantası': '🎒',
  Box: '📦',
  Punch: '⏱️',
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

export function EkipmanView({
  assignments, catalog, personnel,
}: {
  assignments: EquipmentAssignment[];
  catalog: EquipmentCatalogItem[];
  personnel: Personnel[];
}) {
  const [tab, setTab] = useState<'assignments' | 'catalog'>('assignments');
  const [search, setSearch] = useState('');
  const [creating, setCreating] = useState(false);

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    return assignments.filter((a) => {
      if (q) {
        const hay = `${a.personnel_name ?? ''} ${a.person_code ?? ''} ${a.item_name ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [assignments, search]);

  // Hero metrikleri
  const totalAssignments = assignments.length;
  const totalAmount = assignments.reduce((s, a) => s + a.total_amount, 0);
  const ongoing = assignments.filter(
    (a) => a.taksit_kesilen < a.installment_count,
  ).length;
  const itemBreakdown = useMemo(() => {
    const m = new Map<string, { count: number; amount: number }>();
    for (const a of assignments) {
      const k = a.item_name ?? 'Diğer';
      const cur = m.get(k) ?? { count: 0, amount: 0 };
      m.set(k, {
        count: cur.count + a.quantity,
        amount: cur.amount + a.total_amount,
      });
    }
    return Array.from(m.entries())
      .map(([name, v]) => ({ name, ...v }))
      .sort((a, b) => b.amount - a.amount);
  }, [assignments]);

  return (
    <>
      <header className="flex justify-between items-end gap-5 flex-wrap mb-5">
        <div>
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Operasyon · <span className="text-brand">Ekipman & Zimmet</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            Ekipman & Zimmet
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {totalAssignments} zimmet · {ongoing} taksit aktif · toplam{' '}
            <strong className="text-brand">{tr(totalAmount)} ₺</strong>
          </div>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="px-4 py-2.5 rounded-xl bg-brand text-white text-sm font-semibold shadow-sm hover:bg-brand-dark transition flex items-center gap-2"
        >
          <span className="text-base">+</span>
          <span>Yeni Zimmet</span>
        </button>
      </header>

      {/* Hero strip — ekipman bazında özet */}
      <div className="bg-bg-surface border border-border rounded-2xl shadow-md flex overflow-hidden mb-5">
        <div className="flex-1 px-5 py-4 border-r border-border bg-gradient-to-br from-brand-dark to-brand text-white">
          <div className="text-[10.5px] font-semibold uppercase tracking-wider opacity-85">
            Toplam
          </div>
          <div className="font-display text-[26px] font-bold tracking-tight num mt-1">
            {totalAssignments}
          </div>
          <div className="text-[11px] mt-1 opacity-85">
            {tr(totalAmount)} ₺ tutarında
          </div>
        </div>
        {itemBreakdown.slice(0, 5).map((b) => (
          <div
            key={b.name}
            className="flex-1 px-5 py-4 border-r border-border last:border-r-0"
          >
            <div className="text-[10.5px] font-semibold uppercase tracking-wider text-text-3">
              {ITEM_ICONS[normalizeTr(b.name)] ?? ITEM_ICONS[b.name] ?? '📦'} {normalizeTr(b.name)}
            </div>
            <div className="font-display text-[22px] font-bold tracking-tight num mt-1">
              {b.count}
            </div>
            <div className="text-[10.5px] mt-0.5 text-text-3">
              {tr(b.amount)} ₺
            </div>
          </div>
        ))}
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 bg-bg-surface border border-border rounded-2xl p-1.5 shadow-sm w-fit mb-4">
        <button
          onClick={() => setTab('assignments')}
          className={`px-4 py-2 rounded-lg text-[13px] font-semibold transition ${
            tab === 'assignments'
              ? 'bg-brand text-white shadow-sm'
              : 'text-text-2 hover:bg-bg-surface2'
          }`}
        >
          Zimmetler ({assignments.length})
        </button>
        <button
          onClick={() => setTab('catalog')}
          className={`px-4 py-2 rounded-lg text-[13px] font-semibold transition ${
            tab === 'catalog'
              ? 'bg-brand text-white shadow-sm'
              : 'text-text-2 hover:bg-bg-surface2'
          }`}
        >
          Katalog ({catalog.length})
        </button>
      </div>

      {tab === 'assignments' ? (
        <>
          <div className="bg-bg-surface border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2">
            <input
              type="search"
              placeholder="Kurye, kod, ekipman ara…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-border text-sm w-64 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
            />
            <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
              {filtered.length} sonuç
            </span>
          </div>

          {filtered.length === 0 ? (
            <div className="bg-bg-surface border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
              Zimmet kaydı yok.
            </div>
          ) : (
            <div className="bg-bg-surface border border-border rounded-2xl shadow-sm overflow-hidden">
              <table className="w-full text-[13px]">
                <thead className="bg-bg-surface2 text-text-3 text-[11px] uppercase tracking-wider">
                  <tr>
                    <th className="text-left px-3 py-2.5 font-semibold">Tarih</th>
                    <th className="text-left px-3 py-2.5 font-semibold">Kurye</th>
                    <th className="text-left px-3 py-2.5 font-semibold">Ekipman</th>
                    <th className="text-right px-3 py-2.5 font-semibold">Adet</th>
                    <th className="text-right px-3 py-2.5 font-semibold">Birim ₺</th>
                    <th className="text-right px-3 py-2.5 font-semibold">Toplam</th>
                    <th className="text-left px-3 py-2.5 font-semibold">Taksit</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((a) => {
                    const inProgress = a.taksit_kesilen < a.installment_count;
                    const completed = a.taksit_kesilen >= a.installment_count;
                    return (
                      <tr
                        key={a.id}
                        className="border-t border-border hover:bg-bg-surface2/40 transition"
                      >
                        <td className="px-3 py-2.5 font-mono text-[12px] text-text-2 whitespace-nowrap">
                          {formatDate(a.issue_date)}
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="font-medium text-text">
                            {a.personnel_name ?? '—'}
                          </div>
                          <div className="text-[10.5px] text-text-3 font-mono">
                            {a.person_code ?? ''}
                          </div>
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="text-base mr-1">
                            {ITEM_ICONS[normalizeTr(a.item_name)] ?? ITEM_ICONS[a.item_name] ?? '📦'}
                          </span>
                          {normalizeTr(a.item_name)}
                        </td>
                        <td className="px-3 py-2.5 text-right num">
                          {a.quantity}
                        </td>
                        <td className="px-3 py-2.5 text-right num text-text-2">
                          {tr(a.unit_sale_price)} ₺
                        </td>
                        <td className="px-3 py-2.5 text-right num font-semibold text-text">
                          {tr(a.total_amount)} ₺
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 max-w-[80px] h-1.5 bg-bg-surface2 rounded-full overflow-hidden">
                              <div
                                className={`h-full transition-all ${
                                  completed
                                    ? 'bg-green-500'
                                    : 'bg-brand'
                                }`}
                                style={{
                                  width: `${
                                    (a.taksit_kesilen / a.installment_count) *
                                    100
                                  }%`,
                                }}
                              />
                            </div>
                            <span className="text-[11px] font-mono whitespace-nowrap">
                              {a.taksit_kesilen}/{a.installment_count}
                            </span>
                            {inProgress && (
                              <span className="text-[10px] text-text-3">
                                ({tr(a.per_installment)} ₺/ay)
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
          {catalog.map((item) => (
            <div
              key={item.name}
              className="bg-bg-surface border border-border rounded-2xl p-5 shadow-sm hover:shadow-md transition-all"
            >
              <div className="text-3xl mb-2">{ITEM_ICONS[item.name] ?? '📦'}</div>
              <div className="font-display font-semibold text-[16px] tracking-tight">
                {item.name}
              </div>
              <div className="text-[11.5px] text-text-3 mt-0.5">
                {item.category}
              </div>
              <div className="border-t border-border mt-3 pt-3 flex justify-between items-baseline">
                <span className="text-[10.5px] text-text-3 uppercase tracking-wider font-semibold">
                  Önerilen
                </span>
                <span className="font-display text-[18px] font-bold text-brand num">
                  {tr(item.default_price)} ₺
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {creating && (
        <NewAssignmentModal
          personnel={personnel}
          catalog={catalog}
          onClose={() => setCreating(false)}
        />
      )}
    </>
  );
}

function NewAssignmentModal({
  personnel, catalog, onClose,
}: {
  personnel: Personnel[];
  catalog: EquipmentCatalogItem[];
  onClose: () => void;
}) {
  const router = useRouter();
  const [form, setForm] = useState({
    personnel_id: 0,
    item_name: catalog[0]?.name ?? 'Box',
    quantity: 1,
    unit_sale_price: catalog[0]?.default_price ?? 0,
    installment_count: 2,
    issue_date: new Date().toISOString().slice(0, 10),
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function selectItem(name: string) {
    const item = catalog.find((c) => c.name === name);
    setForm((p) => ({
      ...p,
      item_name: name,
      unit_sale_price: item?.default_price ?? p.unit_sale_price,
    }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.personnel_id) {
      setError('Kurye seç');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createEquipmentAssignment(form);
      onClose();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kaydedilemedi');
    } finally {
      setSaving(false);
    }
  }

  const total = form.quantity * form.unit_sale_price;
  const perInstallment = total / Math.max(form.installment_count, 1);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-start justify-center p-4 overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-bg-surface rounded-2xl shadow-2xl w-full max-w-xl my-8 border border-border">
        <div className="bg-gradient-to-r from-brand-dark to-brand text-white px-6 py-4 rounded-t-2xl flex justify-between items-start">
          <div>
            <div className="text-[11px] uppercase tracking-wider opacity-80 font-semibold">
              Yeni Zimmet
            </div>
            <div className="font-display text-lg font-semibold tracking-tight mt-0.5">
              Ekipman zimmet ataması
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

          <label className="block">
            <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
              Ekipman *
            </span>
            <div className="grid grid-cols-4 gap-1.5">
              {catalog.map((c) => (
                <button
                  key={c.name}
                  type="button"
                  onClick={() => selectItem(c.name)}
                  className={`p-2 rounded-lg border text-[11.5px] font-medium transition ${
                    form.item_name === c.name
                      ? 'border-brand bg-brand-soft text-brand'
                      : 'border-border hover:border-brand/40 text-text-2'
                  }`}
                >
                  <div className="text-lg mb-0.5">
                    {ITEM_ICONS[c.name] ?? '📦'}
                  </div>
                  {c.name}
                </button>
              ))}
            </div>
          </label>

          <div className="grid grid-cols-3 gap-3">
            <label className="block">
              <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
                Adet
              </span>
              <input
                type="number"
                min={1}
                value={form.quantity}
                onChange={(e) =>
                  setForm((p) => ({ ...p, quantity: parseInt(e.target.value, 10) || 1 }))
                }
                className="input num"
              />
            </label>
            <label className="block">
              <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
                Birim Fiyat (₺)
              </span>
              <input
                type="number"
                step="any"
                value={form.unit_sale_price || ''}
                onChange={(e) =>
                  setForm((p) => ({ ...p, unit_sale_price: parseFloat(e.target.value) || 0 }))
                }
                className="input num"
              />
            </label>
            <label className="block">
              <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
                Taksit Sayısı
              </span>
              <select
                value={form.installment_count}
                onChange={(e) =>
                  setForm((p) => ({ ...p, installment_count: parseInt(e.target.value, 10) }))
                }
                className="input"
              >
                <option value={1}>Tek seferlik</option>
                <option value={2}>2 taksit</option>
                <option value={3}>3 taksit</option>
                <option value={4}>4 taksit</option>
                <option value={6}>6 taksit</option>
              </select>
            </label>
          </div>

          {/* Canlı özet */}
          <div className="bg-brand-soft/40 border border-brand/15 rounded-lg p-3 flex flex-wrap gap-3">
            <div>
              <div className="text-[10.5px] font-semibold text-text-3 uppercase tracking-wider">
                Toplam
              </div>
              <div className="font-display text-[18px] font-bold text-text num">
                {tr(total)} ₺
              </div>
            </div>
            <div>
              <div className="text-[10.5px] font-semibold text-text-3 uppercase tracking-wider">
                Aylık Taksit
              </div>
              <div className="font-display text-[18px] font-bold text-brand num">
                {tr(perInstallment)} ₺
              </div>
            </div>
            <div className="ml-auto text-[11px] text-text-3 self-center">
              {form.installment_count} ay boyunca aylık kesilir
            </div>
          </div>

          <label className="block">
            <span className="text-[12px] font-semibold text-text-2 mb-1.5 block">
              Verme Tarihi
            </span>
            <input
              type="date"
              value={form.issue_date}
              onChange={(e) =>
                setForm((p) => ({ ...p, issue_date: e.target.value }))
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
              {saving ? 'Kaydediliyor…' : '+ Zimmeti Ekle'}
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
