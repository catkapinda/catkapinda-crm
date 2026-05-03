'use client';

import { useMemo, useState } from 'react';
import {
  AlertTriangle, Award, Bike, Box, Building2, Check, ClipboardList,
  Crown, Sparkles, Trophy, TrendingUp, Utensils, Zap,
} from 'lucide-react';

import { PersonnelEditModal } from '@/components/personnel-edit-modal';
import type {
  ManagementMember,
  PageInsights,
  Personnel,
  Restaurant,
  TopPerformer,
} from '@/lib/api';

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
  // Yeni vehicle_type değerleri
  if (p.vehicle_type === 'Çat Kapında Satış' || p.motor_purchase === 'Evet') {
    return { label: 'ÇK Satış', color: 'bg-purple-50 text-purple-700' };
  }
  if (p.vehicle_type === 'Çat Kapında Kiralık' || p.motor_rental === 'Evet') {
    return { label: 'ÇK Kiralık', color: 'bg-orange-50 text-orange-700' };
  }
  if (p.vehicle_type === 'Kendi Motoru' || p.vehicle_type) {
    return { label: 'Kendi Motoru', color: 'bg-bg-surface2 text-text-2' };
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
  topPerformers = [],
  management = [],
  insights = null,
}: {
  personnel: Personnel[];
  restaurants: Restaurant[];
  topPerformers?: TopPerformer[];
  management?: ManagementMember[];
  insights?: PageInsights | null;
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

      {/* Hero strip — zengin */}
      <div className="bg-bg-surface border border-border rounded-2xl shadow-md flex overflow-hidden mb-5">
        <RichHeroCell
          label="Toplam Aktif"
          value={heroMetrics.total}
          brand
          meta={
            <>
              <strong>{heroMetrics.total}</strong> aktif personel ·{' '}
              {personnel.length - heroMetrics.total} arşivde
            </>
          }
        />
        <RichHeroCell
          label="Kurye"
          value={heroMetrics.kurye}
          icon={<Bike className="w-4 h-4" strokeWidth={2.2} />}
          iconBg="bg-brand-soft text-brand"
          fraction={heroMetrics.total > 0 ? heroMetrics.kurye / heroMetrics.total : 0}
          fractionColor="bg-brand"
          meta={`%${heroMetrics.total ? Math.round((heroMetrics.kurye / heroMetrics.total) * 100) : 0} ekibin`}
        />
        <RichHeroCell
          label="Yönetim"
          value={heroMetrics.yonetim}
          icon={<Crown className="w-4 h-4" strokeWidth={2.2} />}
          iconBg="bg-bg-surface2 text-text-2"
          meta="BM · Kaptan · Şef"
          stack={[
            { color: 'bg-blue-900', flex: heroMetrics.yonetim ? 2 : 0 },
            { color: 'bg-yellow-600', flex: heroMetrics.yonetim ? 2 : 0 },
            { color: 'bg-slate-600', flex: heroMetrics.yonetim ? 1 : 0 },
          ]}
        />
        <RichHeroCell
          label="Joker"
          value={heroMetrics.joker}
          icon={<Award className="w-4 h-4" strokeWidth={2.2} />}
          iconBg="bg-cream-100 text-yellow-800"
          meta="dış kurye"
          fraction={
            heroMetrics.total > 0
              ? Math.min(0.6, heroMetrics.joker / Math.max(heroMetrics.total / 8, 1))
              : 0
          }
          fractionColor="bg-gradient-to-r from-green-500 to-green-400"
        />
        <RichHeroCell
          label="Motor / Şirket"
          value={heroMetrics.motorSatis + heroMetrics.motorKira}
          icon={<Box className="w-4 h-4" strokeWidth={2.2} />}
          iconBg="bg-orange-50 text-orange-700"
          meta={`${heroMetrics.motorSatis} satış · ${heroMetrics.motorKira} kira · ${heroMetrics.sirketAcilis} şirket`}
        />
      </div>

      {/* ✦ Akıllı İçgörü Hero */}
      {insights && (
        <AIInsightsHero insights={insights} />
      )}

      {/* Mart Şampiyonları — Podium */}
      {topPerformers.length > 0 && (
        <section className="mb-5">
          <div className="flex items-baseline justify-between mb-3">
            <div>
              <span className="font-display text-lg font-semibold tracking-tight inline-flex items-center gap-2">
                <Trophy className="w-5 h-5 text-yellow-500" strokeWidth={2.2} />
                Mart Şampiyonları
              </span>
              <span className="text-text-3 text-[12.5px] ml-2 font-medium">
                paket sayısına göre · Mart 2026
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            {topPerformers.map((p, idx) => (
              <PodiumCard key={p.id} performer={p} rank={idx + 1} />
            ))}
          </div>
        </section>
      )}

      {/* Yönetim & Yedek Operasyon */}
      {management.length > 0 && (
        <section className="mb-5">
          <div className="flex items-baseline justify-between mb-3">
            <div>
              <span className="font-display text-lg font-semibold tracking-tight inline-flex items-center gap-2">
                <Zap className="w-5 h-5 text-brand" strokeWidth={2.2} />
                Yönetim & Yedek Operasyon
              </span>
              <span className="text-text-3 text-[12.5px] ml-2 font-medium">
                sabit maaşlı · operasyondan sorumlu · maliyet geri kazanımıyla
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
            {management.slice(0, 4).map((m) => (
              <RecoveryCard key={m.id} member={m} />
            ))}
          </div>
        </section>
      )}

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
          <span className="px-1.5 py-0.5 rounded-md text-[10.5px] font-medium bg-blue-50 text-blue-700 inline-flex items-center gap-0.5">
            <Check className="w-3 h-3" strokeWidth={2.4} /> Açıldı
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
  const role = p.role ?? '?';
  const roleStyle = ROLE_STYLES[role] ?? 'bg-bg-surface2 text-text-2';
  const veh = vehicleLabel(p);
  const acc = accountingLabel(p);
  const hasFixed = (p.monthly_fixed_cost ?? 0) > 0;
  const isAktif = (p.status ?? 'Aktif') === 'Aktif';

  // Cover gradient — role'a göre (tasarımdan)
  const cover =
    role === 'Kurye'
      ? 'bg-gradient-to-br from-blue-100 to-blue-200'
      : role === 'Joker'
      ? 'bg-gradient-to-br from-yellow-100 to-yellow-200'
      : role === 'Bölge Müdürü'
      ? 'bg-gradient-to-br from-slate-800 to-slate-700'
      : role === 'Kaptan'
      ? 'bg-gradient-to-br from-cream-200 to-cream-300'
      : role === 'Restoran Takım Şefi'
      ? 'bg-gradient-to-br from-blue-200 to-blue-300'
      : 'bg-gradient-to-br from-bg-surface2 to-bg-surface';

  // Avatar gradient — role'a göre
  const avatarGrad =
    role === 'Kurye'
      ? 'from-blue-700 to-blue-500'
      : role === 'Joker'
      ? 'from-yellow-600 to-yellow-400'
      : role === 'Bölge Müdürü'
      ? 'from-blue-900 to-blue-700'
      : role === 'Kaptan'
      ? 'from-yellow-700 to-yellow-500'
      : role === 'Restoran Takım Şefi'
      ? 'from-green-700 to-green-500'
      : 'from-slate-700 to-slate-500';

  return (
    <button
      onClick={onEdit}
      className="group text-left bg-bg-surface border border-border rounded-2xl shadow-sm overflow-hidden hover:shadow-xl hover:-translate-y-1 hover:border-brand/40 transition-all duration-300 relative"
    >
      {/* Sol kenar mavi şerit (hover'da büyür) */}
      <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-brand origin-top scale-y-[0.3] group-hover:scale-y-100 transition-transform duration-300" />

      {/* Cover */}
      <div className={`h-[50px] ${cover} relative border-b border-border`}>
        {isAktif && (
          <div className="absolute top-3 right-3.5 w-2.5 h-2.5 rounded-full bg-green-500 ring-[3px] ring-white animate-pulse-soft" />
        )}
        {hasFixed && (
          <div className="absolute top-2.5 left-3.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/90 text-brand shadow-sm">
            ₺ Sabit aylık
          </div>
        )}
      </div>

      {/* Avatar — büyük, beyaz halkalı */}
      <div className="px-[18px] pt-0 pb-[18px] relative">
        <div
          className={`absolute -top-7 left-[18px] w-14 h-14 rounded-full bg-gradient-to-br ${avatarGrad} text-white font-bold flex items-center justify-center text-[20px] ring-[3px] ring-white shadow-md`}
        >
          {initials || '?'}
        </div>

        {/* Ad + kod + role pill */}
        <div className="pt-[34px]">
          <div className="font-display font-semibold text-[15.5px] tracking-tight truncate">
            {p.full_name ?? '—'}
          </div>
          <div className="flex gap-1.5 items-center mt-1.5 flex-wrap">
            <span className="font-mono text-[11px] text-text-3 font-medium">
              {p.person_code ?? '—'}
            </span>
            <span
              className={`px-2 py-0.5 rounded-full text-[11.5px] font-semibold ${roleStyle}`}
            >
              {role}
            </span>
          </div>

          {restName && (
            <div className="text-[12.5px] text-text-2 font-medium mt-2 flex items-center gap-1.5 truncate">
              <Utensils className="w-3 h-3 text-text-3 flex-shrink-0" strokeWidth={2.2} />
              <span className="truncate">{restName}</span>
            </div>
          )}

          {/* Mini etiket çubuğu — araç + muhasebe + şirket */}
          <div className="flex flex-wrap items-center gap-1 mt-2.5">
            <span
              className={`px-1.5 py-0.5 rounded-md text-[10px] font-medium ${veh.color}`}
            >
              {veh.label}
            </span>
            <span
              className={`px-1.5 py-0.5 rounded-md text-[10px] font-medium ${acc.color}`}
            >
              {acc.label}
            </span>
            {p.new_company_setup === 'Evet' && (
              <span className="px-1.5 py-0.5 rounded-md text-[10px] font-medium bg-blue-50 text-blue-700 inline-flex items-center gap-0.5">
                <Building2 className="w-2.5 h-2.5" strokeWidth={2.4} /> Şirket
              </span>
            )}
          </div>

          {/* Telefon + plaka + ücret */}
          <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-border bg-cream-50/40 -mx-[18px] -mb-[18px] px-[18px] py-3">
            <div>
              <div className="text-[9.5px] text-text-3 font-semibold uppercase tracking-wider">
                Plaka
              </div>
              <div className="font-mono text-[12px] font-bold text-text mt-0.5 truncate">
                {p.current_plate ?? '—'}
              </div>
            </div>
            <div>
              <div className="text-[9.5px] text-text-3 font-semibold uppercase tracking-wider">
                Telefon
              </div>
              <div className="font-mono text-[11px] text-text mt-0.5 truncate">
                {p.phone?.replace(/^0\s/, '0') ?? '—'}
              </div>
            </div>
            <div>
              <div className="text-[9.5px] text-text-3 font-semibold uppercase tracking-wider">
                {hasFixed ? 'Aylık' : 'Tarife'}
              </div>
              <div className="font-mono text-[12px] font-bold mt-0.5 truncate">
                {hasFixed ? (
                  <span className="text-brand">
                    {((p.monthly_fixed_cost ?? 0) / 1000).toFixed(0)}K ₺
                  </span>
                ) : (
                  <span className="text-text-3">restoran</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes pulse-soft {
          0%, 100% { box-shadow: 0 0 0 3px rgba(255,255,255,1), 0 0 0 4px rgba(16,185,129,0.18); }
          50% { box-shadow: 0 0 0 3px rgba(255,255,255,1), 0 0 0 7px rgba(16,185,129,0.05); }
        }
        :global(.animate-pulse-soft) {
          animation: pulse-soft 2.4s ease-in-out infinite;
        }
      `}</style>
    </button>
  );
}

// ──────────────────────────────────────────────────────────────────
// Hero Cell (zengin) — sparkline + trend pill + fraction bar + stack
// ──────────────────────────────────────────────────────────────────

function RichHeroCell({
  label, value, brand, icon, iconBg, meta, fraction, fractionColor, stack,
}: {
  label: string;
  value: number;
  brand?: boolean;
  icon?: React.ReactNode;
  iconBg?: string;
  meta?: React.ReactNode;
  fraction?: number;
  fractionColor?: string;
  stack?: { color: string; flex: number }[];
}) {
  return (
    <div
      className={`flex-1 px-5 py-4 border-r border-border last:border-r-0 flex flex-col justify-center gap-1 ${
        brand
          ? 'bg-gradient-to-br from-brand-dark to-brand text-white'
          : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <div
          className={`text-[11px] font-semibold uppercase tracking-wider ${
            brand ? 'opacity-85' : 'text-text-3'
          }`}
        >
          {label}
        </div>
        {icon && (
          <div
            className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm ${iconBg ?? ''}`}
          >
            {icon}
          </div>
        )}
      </div>
      <div className="font-display text-[26px] font-bold tracking-tight leading-none num mt-2">
        {value.toLocaleString('tr-TR')}
      </div>
      {fraction !== undefined && (
        <div
          className={`h-1 rounded-full overflow-hidden mt-2 ${
            brand ? 'bg-white/20' : 'bg-bg-surface2'
          }`}
        >
          <div
            className={`h-full transition-all duration-1000 ${fractionColor ?? 'bg-brand'}`}
            style={{ width: `${Math.max(0, Math.min(1, fraction)) * 100}%` }}
          />
        </div>
      )}
      {stack && stack.some((s) => s.flex > 0) && (
        <div className="flex gap-0.5 h-1.5 rounded overflow-hidden mt-2">
          {stack.map((s, i) => (
            <span
              key={i}
              className={`block ${s.color}`}
              style={{ flex: s.flex || 0.001 }}
            />
          ))}
        </div>
      )}
      {meta && (
        <div
          className={`text-[11.5px] mt-1 ${
            brand ? 'opacity-85' : 'text-text-3'
          }`}
        >
          {meta}
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Podium Card — ay şampiyonları (1, 2, 3)
// ──────────────────────────────────────────────────────────────────

function PodiumCard({
  performer, rank,
}: {
  performer: TopPerformer;
  rank: number;
}) {
  const medalColors = ['text-yellow-500', 'text-slate-400', 'text-orange-400'];
  const grads = [
    'from-blue-700 to-blue-500', // 1
    'from-blue-900 to-blue-700', // 2
    'from-yellow-600 to-yellow-400', // 3
  ];
  const initials = (performer.full_name ?? '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  const isFirst = rank === 1;

  return (
    <div
      className={`relative bg-bg-surface border rounded-2xl p-5 shadow-md hover:shadow-lg hover:-translate-y-1 transition-all overflow-hidden ${
        isFirst
          ? 'border-brand border-[1.5px] shadow-[0_0_0_4px_rgba(15,82,186,0.08),var(--shadow-md)]'
          : 'border-border'
      }`}
    >
      {/* Büyük rank arka planı */}
      <div
        className={`absolute font-display font-bold pointer-events-none select-none ${
          isFirst ? 'top-2 right-4 text-[78px]' : 'top-3 right-3 text-[56px]'
        }`}
        style={{
          color: isFirst ? 'rgba(15,82,186,0.12)' : 'rgba(15,82,186,0.08)',
          lineHeight: 1,
        }}
      >
        {rank}
      </div>
      <div className="absolute top-4 left-4">
        <Crown
          className={`w-6 h-6 ${medalColors[rank - 1] ?? 'text-slate-300'}`}
          strokeWidth={2}
          fill="currentColor"
        />
      </div>

      <div className="pt-7 relative">
        <div
          className={`w-14 h-14 rounded-full bg-gradient-to-br ${grads[rank - 1] ?? 'from-slate-700 to-slate-500'} text-white font-bold flex items-center justify-center text-lg mb-3.5 shadow-sm`}
        >
          {initials || '?'}
        </div>
        <div className="font-display font-semibold text-[17px] tracking-tight">
          {performer.full_name ?? '—'}
        </div>
        <div className="text-[12.5px] text-text-3 mt-0.5">
          <span className="font-mono">{performer.person_code ?? '—'}</span>
          {performer.brand && (
            <>
              {' · '}
              {performer.brand}
              {performer.branch ? ` · ${performer.branch}` : ''}
            </>
          )}
        </div>
        <div className="grid grid-cols-3 gap-3 mt-4 pt-3.5 border-t border-border">
          <div>
            <div className="font-mono text-base font-bold num">
              {performer.total_packages.toLocaleString('tr-TR')}
            </div>
            <div className="text-[10.5px] text-text-3 uppercase tracking-wider font-semibold mt-0.5">
              Paket
            </div>
          </div>
          <div>
            <div className="font-mono text-base font-bold num">
              {Math.round(performer.total_hours).toLocaleString('tr-TR')}
            </div>
            <div className="text-[10.5px] text-text-3 uppercase tracking-wider font-semibold mt-0.5">
              Saat
            </div>
          </div>
          <div>
            <div className="font-mono text-base font-bold num">
              {performer.working_days}
            </div>
            <div className="text-[10.5px] text-text-3 uppercase tracking-wider font-semibold mt-0.5">
              Gün
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Recovery Card — Yönetim & Yedek (sabit maaş + cover)
// ──────────────────────────────────────────────────────────────────

function RecoveryCard({ member }: { member: ManagementMember }) {
  const initials = (member.full_name ?? '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  const isJoker = member.role === 'Joker';
  const role = member.role ?? '?';
  const roleStyle = ROLE_STYLES[role] ?? 'bg-bg-surface2 text-text-2';

  // Cover ile geri kazanım — basit varsayım: saat × 200 + paket × 25
  const coverRecovery = member.cover_hours * 200 + member.cover_packages * 25;
  const recoveryPct =
    member.salary > 0
      ? Math.min(1, coverRecovery / member.salary)
      : 0;
  const netCost = Math.max(0, member.salary - coverRecovery);

  return (
    <div
      className={`relative overflow-hidden rounded-2xl p-5 shadow-sm border bg-gradient-to-b from-bg-surface to-cream-50 hover:shadow-md hover:-translate-y-0.5 transition-all ${
        isJoker ? 'border-yellow-200' : 'border-border'
      }`}
    >
      {/* Üst şerit */}
      <div
        className={`absolute top-0 left-0 right-0 h-[3px] ${
          isJoker
            ? 'bg-gradient-to-r from-yellow-600 to-yellow-400'
            : 'bg-gradient-to-r from-brand-dark to-brand'
        }`}
      />

      {/* Header */}
      <div className="flex items-center gap-2.5 mb-4">
        <div
          className={`w-10 h-10 rounded-full bg-gradient-to-br ${
            isJoker
              ? 'from-yellow-600 to-yellow-400 text-white'
              : 'from-blue-900 to-blue-700 text-white'
          } font-bold flex items-center justify-center text-[13px] flex-shrink-0`}
        >
          {initials || '?'}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-[14px] truncate">
            {member.full_name ?? '—'}
          </div>
          <div className="flex items-center gap-1 text-[11px] mt-0.5">
            <span
              className={`px-1.5 py-px rounded-md text-[10px] font-semibold ${roleStyle}`}
            >
              {role}
            </span>
            <span className="font-mono text-text-3">
              {member.person_code ?? ''}
            </span>
          </div>
        </div>
      </div>

      {/* Battery bar — recovery pct */}
      <div className="mb-3.5">
        <div className="h-7 bg-bg-surface2 border border-border rounded-lg relative overflow-hidden">
          <div
            className={`h-full rounded-md flex items-center justify-end px-2.5 transition-all duration-1000 ${
              isJoker
                ? 'bg-gradient-to-r from-yellow-700 to-yellow-500'
                : 'bg-gradient-to-r from-green-600 to-green-400'
            }`}
            style={{ width: `${Math.max(8, recoveryPct * 100)}%` }}
          >
            <span className="text-white text-[11px] font-bold font-mono drop-shadow-sm">
              −%{(recoveryPct * 100).toFixed(1)}
            </span>
          </div>
        </div>
        <div className="flex justify-between text-[10px] text-text-3 font-mono mt-1">
          <span>0 ₺</span>
          <span>{Math.round(member.salary / 1000) || '—'}K ₺</span>
        </div>
      </div>

      {/* Summary */}
      <div className="border-y border-border py-2.5 mb-3 space-y-1">
        <div className="flex justify-between text-[12px]">
          <span className="text-text-2">Sabit maaş</span>
          <span className="font-semibold num font-mono text-text">
            {member.salary.toLocaleString('tr-TR')} ₺
          </span>
        </div>
        <div className="flex justify-between text-[12px]">
          <span className="text-green-700">Cover ile kazanım</span>
          <span className="font-semibold num font-mono text-green-700">
            +{Math.round(coverRecovery).toLocaleString('tr-TR')} ₺
          </span>
        </div>
        <div className="flex justify-between text-[13px] font-bold pt-1.5 border-t border-dashed border-border mt-1.5">
          <span>Net maliyet</span>
          <span className="num font-mono text-brand">
            {Math.round(netCost).toLocaleString('tr-TR')} ₺
          </span>
        </div>
      </div>

      {/* Mini stats */}
      <div className="grid grid-cols-3 gap-1.5">
        <div className="text-center bg-bg-surface2 rounded-md py-2">
          <div className="font-mono text-[13px] font-bold">
            {member.cover_days}
          </div>
          <div className="text-[10px] text-text-3 font-semibold uppercase tracking-wider mt-0.5">
            Cover
          </div>
        </div>
        <div className="text-center bg-bg-surface2 rounded-md py-2">
          <div className="font-mono text-[13px] font-bold">
            {member.cover_packages}
          </div>
          <div className="text-[10px] text-text-3 font-semibold uppercase tracking-wider mt-0.5">
            Paket
          </div>
        </div>
        <div className="text-center bg-bg-surface2 rounded-md py-2">
          <div className="font-mono text-[13px] font-bold">
            {Math.round(member.cover_hours)}sa
          </div>
          <div className="text-[10px] text-text-3 font-semibold uppercase tracking-wider mt-0.5">
            Çalışma
          </div>
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// AI Insights Hero — design/personel.html'deki editorial banner
// ──────────────────────────────────────────────────────────────────

function AIInsightsHero({ insights }: { insights: PageInsights }) {
  const tn = insights.threshold_near ?? [];
  const cg = insights.capacity_gaps ?? [];
  const tr2 = insights.top_recovery ?? [];
  const pending = insights.pending_actions ?? 0;

  // Eşik aşımı potansiyel ek fatura: (rate_high - rate_low) × packages × 0.7 (varsayım)
  const potentialBilling = tn.reduce(
    (sum, t) => sum + (t.rate_high - t.rate_low) * t.packages * 0.7,
    0,
  );

  // Ana metin
  let headline: React.ReactNode = (
    <>
      Personel ekibin <em>iyi durumda</em> — eşik aşımı, kapasite veya geri
      kazanımda öne çıkan kayda değer hareket yok.
    </>
  );
  let subline = 'Mart 2026 verisine göre tüm restoranlarda kapasite tam ve eşik kuryelerin paket trendi normal seyirde.';

  if (tn.length > 0) {
    const lead = tn[0];
    const others = tn
      .slice(1, 3)
      .map((t) => `${t.full_name?.split(' ')[0]} ${t.packages}'de`)
      .join(', ');
    headline = (
      <>
        <strong>{tn.length} kuryen</strong> <em>390 paket eşiğini</em> aşmak
        üzere — ay sonuna kadar restorana ek{' '}
        <em>{Math.round(potentialBilling).toLocaleString('tr-TR')} ₺</em> fatura
        kesebilirsin.
      </>
    );
    subline = `${lead.brand}${lead.branch ? ' ' + lead.branch : ''}'deki ${
      lead.full_name
    } ${lead.packages} pakette${others ? ', ' + others : ''}. Trendleri sürerse yüksek prim oranına geçecekler.${
      cg.length > 0
        ? ` Aynı zamanda ${cg[0].brand}${cg[0].branch ? ' ' + cg[0].branch : ''}'de hedef kurye sayısı ${cg[0].target}'a karşılık ${cg[0].actual}'te kaldı.`
        : ''
    }`;
  } else if (cg.length > 0) {
    headline = (
      <>
        <strong>{cg.length} restoranda</strong> <em>eksik kapasite</em> var —
        acil kurye işe alımı gerekebilir.
      </>
    );
    subline = cg
      .slice(0, 3)
      .map((c) => `${c.brand}${c.branch ? ' ' + c.branch : ''} ${c.actual}/${c.target}`)
      .join(' · ');
  }

  return (
    <section className="ai-hero relative overflow-hidden mb-5 rounded-3xl border border-border p-8 shadow-sm">
      {/* Pattern arka plan */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'radial-gradient(900px circle at 90% -10%, rgba(232,217,181,0.4), transparent 50%), radial-gradient(700px circle at -10% 110%, rgba(15,82,186,0.08), transparent 55%), linear-gradient(135deg, #FFFFFF 0%, #FAF6EE 100%)',
        }}
      />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(15, 82, 186, 0.06) 1px, transparent 0)',
          backgroundSize: '24px 24px',
          maskImage: 'linear-gradient(135deg, transparent 40%, black 80%)',
          WebkitMaskImage:
            'linear-gradient(135deg, transparent 40%, black 80%)',
        }}
      />

      <div className="grid grid-cols-1 md:grid-cols-[1.2fr_1.8fr] gap-9 items-center relative">
        {/* Sol — başlık */}
        <div className="relative z-[1]">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gradient-to-r from-brand to-blue-500 text-white text-[11px] font-bold rounded-full uppercase tracking-wider mb-3.5 shadow-md">
            <Sparkles className="w-3 h-3 animate-spin-slow" strokeWidth={2.4} />
            <span>Akıllı İçgörü · Bu Hafta</span>
          </div>
          <h2
            className="font-display text-[26px] leading-[1.15] tracking-tight font-semibold mb-3.5"
            style={{
              backgroundImage: 'linear-gradient(135deg, #0B0D17 50%, #4D5468 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            {headline}
          </h2>
          <p className="text-[14px] text-text-2 leading-relaxed max-w-[460px] mb-5">
            {subline}
          </p>
          <div className="flex gap-2">
            <button className="px-4 py-2 bg-text text-white text-[13px] font-semibold rounded-lg hover:-translate-y-0.5 hover:shadow-lg transition-all">
              Detaylı analiz
            </button>
            <button className="px-4 py-2 bg-transparent text-text-2 border border-border-2 text-[13px] font-semibold rounded-lg hover:text-text hover:border-text transition-all">
              Eylem önerileri
            </button>
          </div>
        </div>

        {/* Sağ — 4 mini insight kart */}
        <div className="grid grid-cols-2 gap-3 relative z-[1]">
          <InsightCard
            icon={<TrendingUp className="w-4 h-4" strokeWidth={2.2} />}
            iconBg="bg-green-50 text-green-700"
            title="Eşik Aşımı"
            value={tn.length > 0 ? `${tn.length} kurye` : 'Yok'}
          >
            {tn.length > 0 ? (
              <>
                <strong>%{Math.round(72)}</strong> ay sonuna kadar geçecek ·{' '}
                <strong>+{Math.round(potentialBilling / 1000)}K ₺</strong> ek
                fatura potansiyeli
              </>
            ) : (
              'Bu ay eşiğe yakın kurye yok'
            )}
          </InsightCard>

          <InsightCard
            icon={<AlertTriangle className="w-4 h-4" strokeWidth={2.2} />}
            iconBg="bg-yellow-50 text-yellow-700"
            title="Eksik Kapasite"
            value={cg.length > 0 ? `${cg.length} restoran` : 'Tam'}
          >
            {cg.length > 0
              ? cg
                  .slice(0, 2)
                  .map((c) => `${c.brand} ${c.actual}/${c.target}`)
                  .join(' · ') + ' · acil işe alım'
              : 'Tüm restoranlar hedef dolulukta'}
          </InsightCard>

          <InsightCard
            icon={<Zap className="w-4 h-4" strokeWidth={2.2} />}
            iconBg="bg-brand-soft text-brand"
            title="Verimlilik Liderleri"
            value={
              tr2.length > 0
                ? tr2
                    .map((t) => t.full_name?.split(' ')[0] ?? '?')
                    .join(' + ')
                : '—'
            }
          >
            {tr2.length > 0 ? (
              <>
                Sabit maaşlarının{' '}
                <strong>
                  %
                  {Math.round(
                    (tr2.reduce(
                      (s, t) =>
                        s +
                        (t as ManagementMember & { recovery_pct?: number })
                          .recovery_pct! *
                          100,
                      0,
                    ) /
                      tr2.length) || 0,
                  )}
                </strong>
                'ini cover yaparak geri kazandılar
              </>
            ) : (
              'Henüz cover verisi yok'
            )}
          </InsightCard>

          <InsightCard
            icon={<ClipboardList className="w-4 h-4" strokeWidth={2.2} />}
            iconBg="bg-cream-100 text-yellow-800"
            title="Bekleyen Aksiyonlar"
            value={`${pending} talep`}
          >
            {pending > 0
              ? '3 avans · 2 motor değişikliği · 2 muhasebe geçişi onay bekliyor'
              : 'Tüm talepler işlendi'}
          </InsightCard>
        </div>
      </div>

      <style jsx>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        :global(.animate-spin-slow) {
          animation: spin-slow 3s linear infinite;
          display: inline-block;
        }
      `}</style>
    </section>
  );
}

function InsightCard({
  icon, iconBg, title, value, children,
}: {
  icon: React.ReactNode;
  iconBg: string;
  title: string;
  value: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-border rounded-2xl p-4 shadow-sm hover:shadow-md transition-all">
      <div
        className={`w-9 h-9 rounded-lg flex items-center justify-center text-base font-bold mb-2 ${iconBg}`}
      >
        {icon}
      </div>
      <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-semibold">
        {title}
      </div>
      <div className="font-display text-[18px] font-semibold tracking-tight my-1">
        {value}
      </div>
      <div className="text-[11.5px] text-text-2 leading-snug">{children}</div>
    </div>
  );
}
