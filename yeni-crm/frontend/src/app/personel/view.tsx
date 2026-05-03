'use client';

import { useMemo, useState } from 'react';

import { PersonnelEditModal } from '@/components/personnel-edit-modal';
import type { Personnel, Restaurant } from '@/lib/api';

const ROLE_STYLES: Record<string, { color: string; cover: string }> = {
  Kurye: {
    color: 'bg-brand-soft text-brand',
    cover: 'bg-gradient-to-br from-blue-100 to-blue-200',
  },
  Joker: {
    color: 'bg-cream-100 text-yellow-800',
    cover: 'bg-gradient-to-br from-yellow-100 to-yellow-200',
  },
  'Bölge Müdürü': {
    color: 'bg-text text-white',
    cover: 'bg-gradient-to-br from-slate-800 to-slate-700',
  },
  Kaptan: {
    color: 'bg-purple-100 text-purple-800',
    cover: 'bg-gradient-to-br from-purple-100 to-purple-200',
  },
  'Restoran Takım Şefi': {
    color: 'bg-green-100 text-green-800',
    cover: 'bg-gradient-to-br from-green-100 to-green-200',
  },
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

  const [editingId, setEditingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);

  // Restoran adlarını id'den hızlı bulmak için map
  const restMap = useMemo(() => {
    const m = new Map<number, Restaurant>();
    for (const r of restaurants) m.set(r.id, r);
    return m;
  }, [restaurants]);

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
    return personnel.filter((p) => {
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
  }, [personnel, statusTab, roleFilter, restaurantFilter, search]);

  // Hero metrikleri (statusTab'a değil, hep Aktif'e göre)
  const activeOnly = personnel.filter((p) => (p.status ?? '') === 'Aktif');
  const heroMetrics = {
    total: activeOnly.length,
    kurye: activeOnly.filter((p) => p.role === 'Kurye').length,
    joker: activeOnly.filter((p) => p.role === 'Joker').length,
    yonetim: activeOnly.filter((p) =>
      ['Bölge Müdürü', 'Kaptan', 'Restoran Takım Şefi'].includes(p.role ?? '')
    ).length,
  };

  const editing = editingId != null
    ? personnel.find((p) => p.id === editingId) ?? null
    : null;

  // Restoran adı yardımcı
  const restName = (id: number | null | undefined): string | null => {
    if (id == null) return null;
    const r = restMap.get(id);
    if (!r) return null;
    return `${r.brand}${r.branch ? ` · ${r.branch}` : ''}`;
  };

  return (
    <>
      {/* Header */}
      <header className="flex justify-between items-end gap-5 flex-wrap mb-6">
        <div>
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Operasyon · <span className="text-brand">Personel</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            Personel
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {personnel.length} toplam · {heroMetrics.total} aktif · {restaurants.length} restoranda görev başında
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

      {/* Hero Strip */}
      <div className="bg-bg-surface border border-border rounded-2xl shadow-md flex overflow-hidden mb-5">
        <HeroCell
          label="Toplam Aktif"
          value={heroMetrics.total.toString()}
          brand
          meta="canlı veri · Supabase"
        />
        <HeroCell
          label="Kurye"
          value={heroMetrics.kurye.toString()}
          meta={
            heroMetrics.total > 0
              ? `%${Math.round((heroMetrics.kurye / heroMetrics.total) * 100)} ekibin`
              : ''
          }
        />
        <HeroCell
          label="Yönetim"
          value={heroMetrics.yonetim.toString()}
          meta="BM · Kaptan · Şef"
        />
        <HeroCell
          label="Joker"
          value={heroMetrics.joker.toString()}
          meta="dış kurye"
        />
      </div>

      {/* Toolbar */}
      <div className="bg-bg-surface border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2 sticky top-0 z-10 backdrop-blur-md bg-bg-surface/90">
        {/* Status tab'ları */}
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
          value={restaurantFilter === 'all' ? 'all' : restaurantFilter === 'unassigned' ? 'unassigned' : String(restaurantFilter)}
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

        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
          {filtered.length} sonuç
        </span>
      </div>

      {/* Rol chip'leri */}
      <div className="flex flex-wrap items-center gap-1.5 mb-5">
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider mr-1">
          Rol
        </span>
        {ROLE_FILTERS.map((r) => {
          const count = personnel.filter(
            (p) =>
              (p.status ?? 'Aktif') === statusTab &&
              (r.key === 'all' || p.role === r.key)
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

      {/* Cards */}
      {filtered.length === 0 ? (
        <div className="bg-bg-surface border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
          Sonuç bulunamadı.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
          {filtered.map((p, idx) => (
            <PersonCard
              key={p.id}
              p={p}
              restName={restName(p.assigned_restaurant_id)}
              onEdit={() => setEditingId(p.id)}
              delay={Math.min(idx * 25, 250)}
            />
          ))}
        </div>
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

function HeroCell({
  label, value, meta, brand,
}: { label: string; value: string; meta?: string; brand?: boolean }) {
  return (
    <div
      className={`flex-1 px-5 py-4 border-r border-border last:border-r-0 ${
        brand ? 'bg-gradient-to-br from-brand-dark to-brand text-white' : ''
      }`}
    >
      <div
        className={`text-[11px] font-semibold uppercase tracking-wider ${
          brand ? 'opacity-85' : 'text-text-3'
        }`}
      >
        {label}
      </div>
      <div className="font-display text-2xl font-bold tracking-tight mt-1 num">
        {value}
      </div>
      {meta && (
        <div
          className={`text-[11.5px] mt-1 ${brand ? 'opacity-85' : 'text-text-3'}`}
        >
          {meta}
        </div>
      )}
    </div>
  );
}

function PersonCard({
  p, restName, onEdit, delay = 0,
}: {
  p: Personnel;
  restName: string | null;
  onEdit: () => void;
  delay?: number;
}) {
  const initials = (p.full_name ?? '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  const grad = AVATAR_GRADIENTS[(p.id ?? 0) % AVATAR_GRADIENTS.length];
  const role = p.role ?? '?';
  const style = ROLE_STYLES[role] ?? {
    color: 'bg-bg-surface2 text-text-2',
    cover: 'bg-gradient-to-br from-bg-surface2 to-bg-surface',
  };
  const hasFixed = (p.monthly_fixed_cost ?? 0) > 0;

  return (
    <button
      onClick={onEdit}
      className="group block text-left bg-bg-surface border border-border rounded-2xl shadow-sm overflow-hidden hover:shadow-lg hover:-translate-y-1 hover:border-brand/60 transition-all duration-300 animate-card relative"
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Cover */}
      <div className={`h-12 ${style.cover} relative`}>
        {p.status === 'Aktif' && (
          <div className="w-2.5 h-2.5 rounded-full bg-green-500 ring-2 ring-white absolute top-2.5 right-2.5" />
        )}
        {hasFixed && (
          <div className="absolute top-2 left-3 px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/90 text-brand shadow-sm">
            ₺ Sabit aylık
          </div>
        )}
      </div>

      {/* Body */}
      <div className="px-4 pt-3 pb-4 relative">
        <div
          className={`absolute -top-7 left-4 w-14 h-14 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-base ring-[3px] ring-white shadow-sm`}
        >
          {initials || '?'}
        </div>
        <div className="pt-9">
          <div className="font-display font-semibold text-[15px] tracking-tight truncate">
            {p.full_name ?? '—'}
          </div>
          <div className="flex gap-1.5 items-center mt-1 flex-wrap">
            <span className="font-mono text-[11px] text-text-3 font-medium">
              {p.person_code ?? '—'}
            </span>
            <span className="text-text-3 text-xs">·</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${style.color}`}
            >
              {role}
            </span>
          </div>

          {restName && (
            <div className="mt-2 text-[11.5px] text-text-2 truncate">
              <span className="text-text-3">📍 </span>
              {restName}
            </div>
          )}

          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {p.current_plate && (
              <span className="font-mono text-[11px] text-text-3 bg-bg-surface2 px-2 py-0.5 rounded">
                {p.current_plate}
              </span>
            )}
            {p.phone && (
              <span className="font-mono text-[11px] text-text-2">{p.phone}</span>
            )}
          </div>
        </div>

        {/* Hover edit hint */}
        <div className="mt-3 text-[10.5px] text-text-3 group-hover:text-brand transition flex items-center gap-1 opacity-0 group-hover:opacity-100">
          <span>✎</span>
          <span>düzenlemek için tıkla</span>
        </div>
      </div>

      <style jsx>{`
        :global(.animate-card) {
          animation: card-in 0.4s ease-out both;
        }
        @keyframes card-in {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </button>
  );
}
