'use client';

import { useMemo, useState } from 'react';

import { PersonnelEditModal } from '@/components/personnel-edit-modal';
import type { Personnel, Restaurant } from '@/lib/api';

const ROLE_STYLES: Record<string, string> = {
  Kurye: 'bg-brand-soft text-brand',
  Joker: 'bg-cream-100 text-yellow-800',
  'Bölge Müdürü': 'bg-text text-white',
  Kaptan: 'bg-purple-100 text-purple-800',
  'Restoran Takım Şefi': 'bg-green-100 text-green-800',
};

const STATUS_TABS = [
  { key: 'Aktif', label: 'Aktif' },
  { key: 'Pasif', label: 'Pasif' },
  { key: 'Kara Liste', label: 'Kara Liste' },
] as const;

const ROLE_FILTERS = [
  { key: 'all', label: 'Tümü' },
  { key: 'Kurye', label: 'Kurye' },
  { key: 'Joker', label: 'Joker' },
  { key: 'Bölge Müdürü', label: 'BM' },
  { key: 'Kaptan', label: 'Kaptan' },
  { key: 'Restoran Takım Şefi', label: 'Takım Şefi' },
] as const;

const AVATAR_GRADIENTS = [
  'from-blue-700 to-blue-500',
  'from-blue-900 to-blue-700',
  'from-yellow-600 to-yellow-400',
  'from-slate-700 to-slate-500',
  'from-purple-700 to-purple-500',
  'from-green-700 to-green-500',
];

type SortKey = 'code' | 'name' | 'role' | 'restaurant' | 'fixed' | 'start';
type SortDir = 'asc' | 'desc';

function tr(value: number | null | undefined, digits = 0): string {
  if (value == null || value === 0) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return '—';
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return iso;
  return `${m[3]}.${m[2]}.${m[1].slice(2)}`;
}

function vehicleLabel(p: Personnel): { label: string; color: string } {
  if (p.motor_purchase === 'Evet') {
    return { label: 'Satış motoru', color: 'bg-purple-50 text-purple-700' };
  }
  if (p.motor_rental === 'Evet') {
    return { label: 'ÇK kiralık', color: 'bg-orange-50 text-orange-700' };
  }
  if (p.vehicle_type) {
    return { label: 'Kendi motoru', color: 'bg-bg-surface2 text-text-2' };
  }
  return { label: '—', color: 'bg-bg-surface2 text-text-3' };
}

function accountingLabel(p: Personnel): { label: string; color: string } {
  const t = p.accounting_type ?? '';
  if (t === 'Çat Kapında Muhasebe') {
    return { label: 'ÇK muhasebe', color: 'bg-blue-50 text-blue-700' };
  }
  if (t === 'Kendi Muhasebecisi' || t === 'Kendi muhasebesi') {
    return { label: 'Kendi muhasebecisi', color: 'bg-bg-surface2 text-text-2' };
  }
  if (t) {
    return { label: t, color: 'bg-bg-surface2 text-text-2' };
  }
  return { label: '—', color: 'bg-bg-surface2 text-text-3' };
}

export function PersonnelView({
  personnel,
  restaurants,
}: {
  personnel: Personnel[];
  restaurants: Restaurant[];
}) {
  const [statusTab, setStatusTab] = useState<'Aktif' | 'Pasif' | 'Kara Liste'>('Aktif');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [restaurantFilter, setRestaurantFilter] = useState<number | 'all' | 'unassigned'>('all');
  const [search, setSearch] = useState('');
  const [view, setView] = useState<'table' | 'card'>('table');
  const [sortKey, setSortKey] = useState<SortKey>('code');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const [editingId, setEditingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);

  const restMap = useMemo(() => {
    const m = new Map<number, Restaurant>();
    for (const r of restaurants) m.set(r.id, r);
    return m;
  }, [restaurants]);

  const restName = (id: number | null | undefined): string | null => {
    if (id == null) return null;
    const r = restMap.get(id);
    if (!r) return null;
    return `${r.brand}${r.branch ? ` · ${r.branch}` : ''}`;
  };

  const counts = useMemo(() => {
    const c = { Aktif: 0, Pasif: 0, 'Kara Liste': 0 };
    for (const p of personnel) {
      const s = p.status ?? 'Aktif';
      if (s in c) c[s as keyof typeof c]++;
    }
    return c;
  }, [personnel]);

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    let list = personnel.filter((p) => {
      if ((p.status ?? 'Aktif') !== statusTab) return false;
      if (roleFilter !== 'all' && p.role !== roleFilter) return false;
      if (restaurantFilter === 'unassigned') {
        if (p.assigned_restaurant_id != null) return false;
      } else if (restaurantFilter !== 'all') {
        if (p.assigned_restaurant_id !== restaurantFilter) return false;
      }
      if (q) {
        const hay = `${p.full_name ?? ''} ${p.person_code ?? ''} ${p.phone ?? ''} ${p.current_plate ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    list = [...list].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1;
      switch (sortKey) {
        case 'name':
          return dir * (a.full_name ?? '').localeCompare(b.full_name ?? '', 'tr-TR');
        case 'role':
          return dir * (a.role ?? '').localeCompare(b.role ?? '', 'tr-TR');
        case 'restaurant': {
          const ra = restName(a.assigned_restaurant_id) ?? '';
          const rb = restName(b.assigned_restaurant_id) ?? '';
          return dir * ra.localeCompare(rb, 'tr-TR');
        }
        case 'fixed':
          return dir * ((a.monthly_fixed_cost ?? 0) - (b.monthly_fixed_cost ?? 0));
        case 'start':
          return dir * (a.start_date ?? '').localeCompare(b.start_date ?? '');
        default:
          return dir * (a.person_code ?? '').localeCompare(b.person_code ?? '');
      }
    });

    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personnel, statusTab, roleFilter, restaurantFilter, search, sortKey, sortDir, restMap]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  const activeOnly = personnel.filter((p) => (p.status ?? '') === 'Aktif');
  const heroMetrics = {
    total: activeOnly.length,
    kurye: activeOnly.filter((p) => p.role === 'Kurye').length,
    joker: activeOnly.filter((p) => p.role === 'Joker').length,
    yonetim: activeOnly.filter((p) =>
      ['Bölge Müdürü', 'Kaptan', 'Restoran Takım Şefi'].includes(p.role ?? '')
    ).length,
    sabitAylik: activeOnly.filter((p) => (p.monthly_fixed_cost ?? 0) > 0).length,
    motorSatis: activeOnly.filter((p) => p.motor_purchase === 'Evet').length,
    motorKira: activeOnly.filter((p) => p.motor_rental === 'Evet').length,
    sirketAcilis: activeOnly.filter((p) => p.new_company_setup === 'Evet').length,
  };

  const editing = editingId != null
    ? personnel.find((p) => p.id === editingId) ?? null
    : null;

  return (
    <>
      {/* Header */}
      <header className="flex justify-between items-end gap-5 flex-wrap mb-5">
        <div>
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Operasyon · <span className="text-brand">Personel</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            Personel
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {personnel.length} toplam · {heroMetrics.total} aktif ·{' '}
            {heroMetrics.sabitAylik} sabit aylık ·{' '}
            {heroMetrics.motorSatis + heroMetrics.motorKira} motor sözleşmeli
          </div>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="px-4 py-2.5 rounded-xl bg-brand text-white text-sm font-semibold shadow-sm hover:bg-brand-dark transition flex items-center gap-2"
        >
          <span className="text-base">+</span>
          <span>Yeni Personel</span>
        </button>
      </header>

      {/* Hero strip — daha bilgi yoğun */}
      <div className="bg-bg-surface border border-border rounded-2xl shadow-md flex overflow-hidden mb-4">
        <HeroCell
          label="Toplam Aktif"
          value={heroMetrics.total.toString()}
          brand
          meta="canlı veri"
        />
        <HeroCell
          label="Kurye"
          value={heroMetrics.kurye.toString()}
          meta={`${heroMetrics.yonetim} yönetici`}
        />
        <HeroCell
          label="Joker"
          value={heroMetrics.joker.toString()}
          meta="dış kurye"
        />
        <HeroCell
          label="Sabit Aylık"
          value={heroMetrics.sabitAylik.toString()}
          meta="hakedişi belirli"
        />
        <HeroCell
          label="Motor Sözleşmesi"
          value={(heroMetrics.motorSatis + heroMetrics.motorKira).toString()}
          meta={`${heroMetrics.motorSatis} satış · ${heroMetrics.motorKira} kira`}
        />
        <HeroCell
          label="Şirket Açılışı"
          value={heroMetrics.sirketAcilis.toString()}
          meta="şahıs şirketi"
        />
      </div>

      {/* Sticky Toolbar */}
      <div className="bg-bg-surface border border-border rounded-2xl p-3 shadow-sm mb-3 flex flex-wrap items-center gap-2 sticky top-0 z-20 backdrop-blur-md bg-bg-surface/95">
        <div className="flex gap-1 bg-bg-surface2 rounded-lg p-1">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setStatusTab(tab.key)}
              className={`px-3 py-1.5 rounded-md text-[12.5px] font-medium transition flex items-center gap-1.5 ${
                statusTab === tab.key
                  ? 'bg-brand text-white shadow-sm'
                  : 'text-text-2 hover:bg-bg-surface'
              }`}
            >
              {tab.label}
              <span
                className={`px-1.5 py-px rounded-full text-[10px] tabular-nums ${
                  statusTab === tab.key ? 'bg-white/25' : 'bg-bg-surface'
                }`}
              >
                {counts[tab.key]}
              </span>
            </button>
          ))}
        </div>

        <input
          type="search"
          placeholder="İsim, kod, telefon, plaka…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-1.5 rounded-lg border border-border text-sm w-56 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
        />

        <select
          value={
            restaurantFilter === 'all'
              ? 'all'
              : restaurantFilter === 'unassigned'
              ? 'unassigned'
              : String(restaurantFilter)
          }
          onChange={(e) => {
            const v = e.target.value;
            if (v === 'all') setRestaurantFilter('all');
            else if (v === 'unassigned') setRestaurantFilter('unassigned');
            else setRestaurantFilter(parseInt(v, 10));
          }}
          className="px-3 py-1.5 rounded-lg border border-border text-sm bg-bg-surface focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
        >
          <option value="all">Tüm restoranlar</option>
          <option value="unassigned">Atanmamış / Joker</option>
          {restaurants.map((r) => (
            <option key={r.id} value={r.id}>
              {r.brand} {r.branch ? `· ${r.branch}` : ''}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-1 bg-bg-surface2 rounded-lg p-1 ml-auto">
          <button
            onClick={() => setView('table')}
            className={`px-2.5 py-1 rounded-md text-[12px] font-medium transition ${
              view === 'table'
                ? 'bg-brand text-white shadow-sm'
                : 'text-text-2 hover:bg-bg-surface'
            }`}
            title="Tablo görünümü"
          >
            ≡ Tablo
          </button>
          <button
            onClick={() => setView('card')}
            className={`px-2.5 py-1 rounded-md text-[12px] font-medium transition ${
              view === 'card'
                ? 'bg-brand text-white shadow-sm'
                : 'text-text-2 hover:bg-bg-surface'
            }`}
            title="Kart görünümü"
          >
            ◫ Kart
          </button>
        </div>

        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider">
          {filtered.length} sonuç
        </span>
      </div>

      {/* Rol chip'leri */}
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider mr-1">
          Rol
        </span>
        {ROLE_FILTERS.map((r) => {
          const count = personnel.filter(
            (p) =>
              (p.status ?? 'Aktif') === statusTab &&
              (r.key === 'all' || p.role === r.key),
          ).length;
          return (
            <button
              key={r.key}
              onClick={() => setRoleFilter(r.key)}
              className={`px-2.5 py-1 rounded-full text-[12px] font-medium transition flex items-center gap-1.5 ${
                roleFilter === r.key
                  ? 'bg-brand text-white shadow-sm'
                  : 'bg-bg-surface border border-border text-text-2 hover:bg-brand-soft hover:text-brand hover:border-brand/30'
              }`}
            >
              {r.label}
              <span
                className={`px-1.5 py-px rounded-full text-[10px] tabular-nums ${
                  roleFilter === r.key ? 'bg-white/25' : 'bg-bg-surface2'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* İçerik */}
      {filtered.length === 0 ? (
        <div className="bg-bg-surface border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
          Sonuç bulunamadı.
        </div>
      ) : view === 'table' ? (
        <PersonnelTable
          personnel={filtered}
          restName={restName}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={toggleSort}
          onEdit={(id) => setEditingId(id)}
        />
      ) : (
        <PersonnelCardGrid
          personnel={filtered}
          restName={restName}
          onEdit={(id) => setEditingId(id)}
        />
      )}

      {creating && (
        <PersonnelEditModal
          personnel={null}
          restaurants={restaurants}
          mode="create"
          onClose={() => setCreating(false)}
        />
      )}
      {editing && (
        <PersonnelEditModal
          personnel={editing}
          restaurants={restaurants}
          mode="edit"
          onClose={() => setEditingId(null)}
        />
      )}
    </>
  );
}

// ──────────────────────────────────────────────────────────────────
// Tablo görünümü — kompakt, çok bilgi
// ──────────────────────────────────────────────────────────────────

function PersonnelTable({
  personnel, restName, sortKey, sortDir, onSort, onEdit,
}: {
  personnel: Personnel[];
  restName: (id: number | null | undefined) => string | null;
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (k: SortKey) => void;
  onEdit: (id: number) => void;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-2xl shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead className="bg-bg-surface2 text-text-3 text-[11px] uppercase tracking-wider sticky top-[60px] z-10">
            <tr>
              <SortableTh
                label="Personel"
                k="code"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
                width="w-[230px]"
              />
              <SortableTh
                label="Rol"
                k="role"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
              />
              <SortableTh
                label="Restoran"
                k="restaurant"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
              />
              <th className="text-left px-3 py-2.5 font-semibold">Telefon</th>
              <th className="text-left px-3 py-2.5 font-semibold">Plaka</th>
              <th className="text-left px-3 py-2.5 font-semibold">Araç</th>
              <th className="text-left px-3 py-2.5 font-semibold">Muhasebe</th>
              <th className="text-left px-3 py-2.5 font-semibold">Şirket</th>
              <SortableTh
                label="Aylık ₺"
                k="fixed"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
                align="right"
              />
              <SortableTh
                label="Başl."
                k="start"
                sortKey={sortKey}
                sortDir={sortDir}
                onSort={onSort}
              />
            </tr>
          </thead>
          <tbody>
            {personnel.map((p) => (
              <PersonnelRow
                key={p.id}
                p={p}
                restName={restName(p.assigned_restaurant_id)}
                onClick={() => onEdit(p.id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SortableTh({
  label, k, sortKey, sortDir, onSort, align = 'left', width,
}: {
  label: string;
  k: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (k: SortKey) => void;
  align?: 'left' | 'right';
  width?: string;
}) {
  const active = sortKey === k;
  return (
    <th
      className={`px-3 py-2.5 font-semibold cursor-pointer select-none ${
        align === 'right' ? 'text-right' : 'text-left'
      } ${width ?? ''} ${active ? 'text-brand' : 'hover:text-text-2'}`}
      onClick={() => onSort(k)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <span className="text-[9px] opacity-60">
          {active ? (sortDir === 'asc' ? '▲' : '▼') : '⇅'}
        </span>
      </span>
    </th>
  );
}

function PersonnelRow({
  p, restName, onClick,
}: {
  p: Personnel;
  restName: string | null;
  onClick: () => void;
}) {
  const initials = (p.full_name ?? '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  const grad = AVATAR_GRADIENTS[(p.id ?? 0) % AVATAR_GRADIENTS.length];
  const role = p.role ?? '?';
  const roleStyle = ROLE_STYLES[role] ?? 'bg-bg-surface2 text-text-2';
  const veh = vehicleLabel(p);
  const acc = accountingLabel(p);
  const hasFixed = (p.monthly_fixed_cost ?? 0) > 0;
  const fixedAmount = p.monthly_fixed_cost ?? 0;

  return (
    <tr
      onClick={onClick}
      className="border-t border-border hover:bg-bg-surface2/40 transition cursor-pointer"
    >
      {/* Personel: avatar + isim + kod */}
      <td className="px-3 py-2">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-8 h-8 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-[11px] flex-shrink-0`}
          >
            {initials || '?'}
          </div>
          <div className="min-w-0">
            <div className="font-medium text-text truncate">
              {p.full_name ?? '—'}
            </div>
            <div className="text-[10.5px] text-text-3 font-mono">
              {p.person_code ?? '—'}
            </div>
          </div>
        </div>
      </td>
      {/* Rol */}
      <td className="px-3 py-2">
        <span
          className={`px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ${roleStyle} whitespace-nowrap`}
        >
          {role}
        </span>
      </td>
      {/* Restoran */}
      <td className="px-3 py-2">
        {restName ? (
          <span className="text-text-2 text-[12px]">{restName}</span>
        ) : (
          <span className="text-text-3 text-[11.5px]">—</span>
        )}
      </td>
      {/* Telefon */}
      <td className="px-3 py-2 font-mono text-[12px] text-text-2 whitespace-nowrap">
        {p.phone ?? <span className="text-text-3">—</span>}
      </td>
      {/* Plaka */}
      <td className="px-3 py-2 font-mono text-[11.5px] text-text-2 whitespace-nowrap">
        {p.current_plate ?? <span className="text-text-3">—</span>}
      </td>
      {/* Araç */}
      <td className="px-3 py-2">
        <span
          className={`px-1.5 py-0.5 rounded-md text-[10.5px] font-medium ${veh.color} whitespace-nowrap`}
        >
          {veh.label}
        </span>
      </td>
      {/* Muhasebe */}
      <td className="px-3 py-2">
        <span
          className={`px-1.5 py-0.5 rounded-md text-[10.5px] font-medium ${acc.color} whitespace-nowrap`}
        >
          {acc.label}
        </span>
      </td>
      {/* Şirket açılışı */}
      <td className="px-3 py-2">
        {p.new_company_setup === 'Evet' ? (
          <span className="px-1.5 py-0.5 rounded-md text-[10.5px] font-medium bg-blue-50 text-blue-700">
            ✓ Açıldı
          </span>
        ) : (
          <span className="text-text-3 text-[11px]">—</span>
        )}
      </td>
      {/* Aylık */}
      <td className="px-3 py-2 text-right">
        {hasFixed ? (
          <div>
            <div className="num text-[12.5px] font-semibold text-brand">
              {tr(fixedAmount)} ₺
            </div>
            {(p.fixed_monthly_billing ?? 0) > 0 && (
              <div className="num text-[10.5px] text-text-3">
                fatura {tr(p.fixed_monthly_billing)} ₺
              </div>
            )}
          </div>
        ) : (
          <span className="text-text-3 text-[11px]">—</span>
        )}
      </td>
      {/* Başlangıç */}
      <td className="px-3 py-2 font-mono text-[11px] text-text-3 whitespace-nowrap">
        {formatDateShort(p.start_date)}
      </td>
    </tr>
  );
}

// ──────────────────────────────────────────────────────────────────
// Kart görünümü (alternatif)
// ──────────────────────────────────────────────────────────────────

function PersonnelCardGrid({
  personnel, restName, onEdit,
}: {
  personnel: Personnel[];
  restName: (id: number | null | undefined) => string | null;
  onEdit: (id: number) => void;
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
      {personnel.map((p) => (
        <PersonCard
          key={p.id}
          p={p}
          restName={restName(p.assigned_restaurant_id)}
          onEdit={() => onEdit(p.id)}
        />
      ))}
    </div>
  );
}

function HeroCell({
  label, value, meta, brand,
}: { label: string; value: string; meta?: string; brand?: boolean }) {
  return (
    <div
      className={`flex-1 px-4 py-3 border-r border-border last:border-r-0 ${
        brand ? 'bg-gradient-to-br from-brand-dark to-brand text-white' : ''
      }`}
    >
      <div
        className={`text-[10px] font-semibold uppercase tracking-wider ${
          brand ? 'opacity-85' : 'text-text-3'
        }`}
      >
        {label}
      </div>
      <div className="font-display text-xl font-bold tracking-tight mt-0.5 num">
        {value}
      </div>
      {meta && (
        <div
          className={`text-[10.5px] mt-0.5 ${
            brand ? 'opacity-85' : 'text-text-3'
          }`}
        >
          {meta}
        </div>
      )}
    </div>
  );
}

function PersonCard({
  p, restName, onEdit,
}: {
  p: Personnel;
  restName: string | null;
  onEdit: () => void;
}) {
  const initials = (p.full_name ?? '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  const grad = AVATAR_GRADIENTS[(p.id ?? 0) % AVATAR_GRADIENTS.length];
  const role = p.role ?? '?';
  const roleStyle = ROLE_STYLES[role] ?? 'bg-bg-surface2 text-text-2';
  const veh = vehicleLabel(p);
  const acc = accountingLabel(p);
  const hasFixed = (p.monthly_fixed_cost ?? 0) > 0;

  return (
    <button
      onClick={onEdit}
      className="text-left bg-bg-surface border border-border rounded-xl p-3.5 shadow-sm hover:shadow-md hover:-translate-y-0.5 hover:border-brand/40 transition-all"
    >
      <div className="flex items-center gap-2.5 mb-2.5">
        <div
          className={`w-10 h-10 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-[12px] flex-shrink-0`}
        >
          {initials || '?'}
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-medium text-text text-sm truncate">
            {p.full_name ?? '—'}
          </div>
          <div className="text-[10.5px] text-text-3 font-mono">
            {p.person_code ?? '—'}
          </div>
        </div>
        <span
          className={`px-1.5 py-0.5 rounded-md text-[10px] font-semibold ${roleStyle} whitespace-nowrap`}
        >
          {role}
        </span>
      </div>

      {restName && (
        <div className="text-[11.5px] text-text-2 mb-2 truncate">
          📍 {restName}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-1 mb-2">
        <span
          className={`px-1.5 py-0.5 rounded-md text-[10px] font-medium ${veh.color}`}
        >
          🏍️ {veh.label}
        </span>
        <span
          className={`px-1.5 py-0.5 rounded-md text-[10px] font-medium ${acc.color}`}
        >
          📊 {acc.label}
        </span>
        {p.new_company_setup === 'Evet' && (
          <span className="px-1.5 py-0.5 rounded-md text-[10px] font-medium bg-blue-50 text-blue-700">
            🏢 Şirket
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-[11px] pt-2 border-t border-border">
        <span className="font-mono text-text-3">{p.phone ?? '—'}</span>
        {hasFixed ? (
          <span className="num font-semibold text-brand">
            {tr(p.monthly_fixed_cost)} ₺/ay
          </span>
        ) : (
          <span className="text-text-3">—</span>
        )}
      </div>
    </button>
  );
}
