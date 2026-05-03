'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';

import { RestaurantEditModal } from '@/components/restaurant-edit-modal';
import type { Restaurant, RestaurantPuantajSummary } from '@/lib/api';

const MODEL_LABELS: Record<string, { label: string; color: string; ring: string; gradient: string }> = {
  hourly_only: {
    label: 'Saatlik',
    color: 'bg-blue-50 text-blue-700',
    ring: 'border-blue-200',
    gradient: 'from-blue-500/8 to-blue-600/4',
  },
  hourly_plus_package: {
    label: 'Saat + Prim',
    color: 'bg-orange-50 text-orange-700',
    ring: 'border-orange-200',
    gradient: 'from-orange-500/8 to-orange-600/4',
  },
  threshold_package: {
    label: 'Eşikli (390)',
    color: 'bg-cream-100 text-yellow-900',
    ring: 'border-yellow-200',
    gradient: 'from-yellow-500/8 to-yellow-600/4',
  },
  fixed_monthly: {
    label: 'Aylık Sabit',
    color: 'bg-green-50 text-green-700',
    ring: 'border-green-200',
    gradient: 'from-green-500/8 to-green-600/4',
  },
};

type SortKey = 'brand' | 'packages' | 'hours' | 'fill' | 'absences';

function tr(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function RestaurantsView({
  restaurants,
  perf,
}: {
  restaurants: Restaurant[];
  perf: RestaurantPuantajSummary[];
}) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [activeBrand, setActiveBrand] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('brand');
  const [view, setView] = useState<'grid' | 'group'>('grid');

  const perfMap = useMemo(() => {
    const m = new Map<number, RestaurantPuantajSummary>();
    for (const p of perf) {
      if (p.restaurant_id != null) m.set(p.restaurant_id, p);
    }
    return m;
  }, [perf]);

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    let list = restaurants.filter((r) => {
      if (activeBrand && r.brand !== activeBrand) return false;
      if (activeModel && r.pricing_model !== activeModel) return false;
      if (q) {
        const hay = `${r.brand ?? ''} ${r.branch ?? ''} ${r.contact_name ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    list = [...list].sort((a, b) => {
      const pa = perfMap.get(a.id);
      const pb = perfMap.get(b.id);
      switch (sortKey) {
        case 'packages':
          return (pb?.total_packages ?? 0) - (pa?.total_packages ?? 0);
        case 'hours':
          return (pb?.total_hours ?? 0) - (pa?.total_hours ?? 0);
        case 'absences':
          return (pb?.absences ?? 0) - (pa?.absences ?? 0);
        case 'fill': {
          const fa = a.target_headcount ? (pa?.unique_personnel ?? 0) / a.target_headcount : 0;
          const fb = b.target_headcount ? (pb?.unique_personnel ?? 0) / b.target_headcount : 0;
          return fb - fa;
        }
        default:
          return (a.brand ?? '').localeCompare(b.brand ?? '', 'tr-TR') ||
            (a.branch ?? '').localeCompare(b.branch ?? '', 'tr-TR');
      }
    });

    return list;
  }, [restaurants, activeBrand, activeModel, search, sortKey, perfMap]);

  // Brand bazlı gruplama (group view için)
  const groups = useMemo(() => {
    const m = new Map<string, Restaurant[]>();
    for (const r of filtered) {
      const k = r.brand ?? '—';
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(r);
    }
    return Array.from(m.entries()).sort((a, b) => b[1].length - a[1].length);
  }, [filtered]);

  const editing = editingId != null
    ? restaurants.find((r) => r.id === editingId) ?? null
    : null;

  const brandList = useMemo(() => {
    const counts = new Map<string, number>();
    for (const r of restaurants) {
      if (r.brand) counts.set(r.brand, (counts.get(r.brand) ?? 0) + 1);
    }
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'tr-TR'));
  }, [restaurants]);

  const byModel = useMemo(() => {
    const m: Record<string, number> = {};
    for (const r of restaurants) {
      const k = r.pricing_model ?? 'unknown';
      m[k] = (m[k] ?? 0) + 1;
    }
    return m;
  }, [restaurants]);

  // Toplam Mart 2026 — hero için
  const monthTotals = useMemo(() => {
    const t = perf.reduce(
      (acc, p) => {
        acc.hours += p.total_hours;
        acc.packages += p.total_packages;
        acc.absences += p.absences;
        return acc;
      },
      { hours: 0, packages: 0, absences: 0 }
    );
    return t;
  }, [perf]);

  return (
    <>
      {/* Header — Yeni Müşteri butonu */}
      <header className="flex justify-between items-center gap-5 flex-wrap mb-4">
        <div className="text-[12.5px] text-text-3 font-medium">
          {restaurants.length} aktif restoran · karta tıklayıp düzenle
        </div>
        <button
          onClick={() => setCreating(true)}
          className="px-4 py-2 rounded-xl bg-brand text-white text-sm font-semibold shadow-sm hover:bg-brand-dark transition flex items-center gap-2"
        >
          <span className="text-base">+</span>
          <span>Yeni Müşteri / Restoran</span>
        </button>
      </header>

      {/* Hero strip */}
      <div className="bg-bg-surface border border-border rounded-2xl shadow-md flex overflow-hidden mb-5">
        <HeroCell
          label="Toplam Aktif"
          value={restaurants.length.toString()}
          brand
          meta={`${monthTotals.packages.toLocaleString('tr-TR')} paket / ${Math.round(monthTotals.hours).toLocaleString('tr-TR')} saat`}
        />
        <ModelCell
          label="Saat + Prim"
          value={byModel['hourly_plus_package'] ?? 0}
          modelKey="hourly_plus_package"
          activeModel={activeModel}
          onClick={(k) => setActiveModel(activeModel === k ? null : k)}
        />
        <ModelCell
          label="Eşikli"
          value={byModel['threshold_package'] ?? 0}
          modelKey="threshold_package"
          activeModel={activeModel}
          onClick={(k) => setActiveModel(activeModel === k ? null : k)}
        />
        <ModelCell
          label="Aylık Sabit"
          value={byModel['fixed_monthly'] ?? 0}
          modelKey="fixed_monthly"
          activeModel={activeModel}
          onClick={(k) => setActiveModel(activeModel === k ? null : k)}
        />
        <ModelCell
          label="Saatlik"
          value={byModel['hourly_only'] ?? 0}
          modelKey="hourly_only"
          activeModel={activeModel}
          onClick={(k) => setActiveModel(activeModel === k ? null : k)}
        />
      </div>

      {/* Toolbar */}
      <div className="bg-bg-surface border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2 sticky top-0 z-10 backdrop-blur-md bg-bg-surface/90">
        <input
          type="search"
          placeholder="Marka, şube, yetkili ara…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-1.5 rounded-lg border border-border text-sm w-56 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
        />

        <div className="flex items-center gap-1 bg-bg-surface2 rounded-lg p-1">
          <SortPill active={sortKey === 'brand'} onClick={() => setSortKey('brand')}>A→Z</SortPill>
          <SortPill active={sortKey === 'packages'} onClick={() => setSortKey('packages')}>Paket ▾</SortPill>
          <SortPill active={sortKey === 'hours'} onClick={() => setSortKey('hours')}>Saat ▾</SortPill>
          <SortPill active={sortKey === 'fill'} onClick={() => setSortKey('fill')}>Doluluk ▾</SortPill>
          <SortPill active={sortKey === 'absences'} onClick={() => setSortKey('absences')}>Devamsızlık ▾</SortPill>
        </div>

        <div className="flex items-center gap-1 bg-bg-surface2 rounded-lg p-1">
          <SortPill active={view === 'grid'} onClick={() => setView('grid')}>◫ Kart</SortPill>
          <SortPill active={view === 'group'} onClick={() => setView('group')}>≡ Marka</SortPill>
        </div>

        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
          {filtered.length} sonuç
        </span>
      </div>

      {/* Brand filter chip'leri */}
      <div className="flex flex-wrap items-center gap-1.5 mb-5">
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider mr-1">
          Marka
        </span>
        <button
          onClick={() => setActiveBrand(null)}
          className={`px-2.5 py-1 rounded-full text-[12px] font-medium transition ${
            activeBrand === null
              ? 'bg-brand text-white shadow-sm'
              : 'bg-bg-surface border border-border text-text-2 hover:bg-brand-soft hover:text-brand hover:border-brand/30'
          }`}
        >
          Tümü
        </button>
        {brandList.map(([brand, count]) => (
          <button
            key={brand}
            onClick={() => setActiveBrand(activeBrand === brand ? null : brand)}
            className={`px-2.5 py-1 rounded-full text-[12px] font-medium transition flex items-center gap-1.5 ${
              activeBrand === brand
                ? 'bg-brand text-white shadow-sm'
                : 'bg-bg-surface border border-border text-text-2 hover:bg-brand-soft hover:text-brand hover:border-brand/30'
            }`}
          >
            {brand}
            <span
              className={`px-1.5 py-px rounded-full text-[10px] tabular-nums ${
                activeBrand === brand ? 'bg-white/25' : 'bg-bg-surface2'
              }`}
            >
              {count}
            </span>
          </button>
        ))}
        {(activeBrand || activeModel || search) && (
          <button
            onClick={() => {
              setActiveBrand(null);
              setActiveModel(null);
              setSearch('');
            }}
            className="ml-auto text-[12px] text-text-3 hover:text-brand transition underline-offset-2 hover:underline"
          >
            ✕ filtreleri temizle
          </button>
        )}
      </div>

      {/* İçerik */}
      {view === 'grid' ? (
        <CardGrid
          items={filtered}
          perfMap={perfMap}
          onEdit={(id) => setEditingId(id)}
        />
      ) : (
        <div className="space-y-6">
          {groups.map(([brand, items]) => (
            <div key={brand}>
              <div className="flex items-baseline gap-3 mb-2.5">
                <h3 className="font-display text-lg font-semibold tracking-tight">
                  {brand}
                </h3>
                <span className="text-[12px] text-text-3 font-medium">
                  {items.length} şube
                </span>
                <div className="flex-1 border-b border-border" />
              </div>
              <CardGrid
                items={items}
                perfMap={perfMap}
                onEdit={(id) => setEditingId(id)}
              />
            </div>
          ))}
        </div>
      )}

      {filtered.length === 0 && (
        <div className="bg-bg-surface border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
          Sonuç bulunamadı.
        </div>
      )}

      {editing && (
        <RestaurantEditModal
          restaurant={editing}
          onClose={() => setEditingId(null)}
          mode="edit"
        />
      )}
      {creating && (
        <RestaurantEditModal
          restaurant={null}
          onClose={() => setCreating(false)}
          mode="create"
        />
      )}
    </>
  );
}

function CardGrid({
  items, perfMap, onEdit,
}: {
  items: Restaurant[];
  perfMap: Map<number, RestaurantPuantajSummary>;
  onEdit: (id: number) => void;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
      {items.map((r, idx) => (
        <RestaurantCard
          key={r.id}
          r={r}
          perf={perfMap.get(r.id)}
          onEdit={() => onEdit(r.id)}
          delay={Math.min(idx * 30, 300)}
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
      className={`flex-1 px-5 py-4 border-r border-border last:border-r-0 ${
        brand ? 'bg-gradient-to-br from-brand-dark to-brand text-white' : ''
      }`}
    >
      <div className={`text-[11px] font-semibold uppercase tracking-wider ${brand ? 'opacity-85' : 'text-text-3'}`}>
        {label}
      </div>
      <div className="font-display text-2xl font-bold tracking-tight mt-1 num">{value}</div>
      {meta && <div className={`text-[11.5px] mt-1 ${brand ? 'opacity-85' : 'text-text-3'}`}>{meta}</div>}
    </div>
  );
}

function ModelCell({
  label, value, modelKey, activeModel, onClick,
}: {
  label: string;
  value: number;
  modelKey: string;
  activeModel: string | null;
  onClick: (k: string) => void;
}) {
  const isActive = activeModel === modelKey;
  return (
    <button
      onClick={() => onClick(modelKey)}
      className={`flex-1 px-5 py-4 border-r border-border last:border-r-0 transition text-left cursor-pointer ${
        isActive
          ? 'bg-brand-soft'
          : 'hover:bg-bg-surface2/60'
      }`}
    >
      <div
        className={`text-[11px] font-semibold uppercase tracking-wider ${
          isActive ? 'text-brand' : 'text-text-3'
        }`}
      >
        {label}
      </div>
      <div
        className={`font-display text-2xl font-bold tracking-tight mt-1 num ${
          isActive ? 'text-brand' : ''
        }`}
      >
        {value}
      </div>
      <div className={`text-[11.5px] mt-1 ${isActive ? 'text-brand/75' : 'text-text-3'}`}>
        {isActive ? 'filtre aktif' : 'filtrele →'}
      </div>
    </button>
  );
}

function SortPill({
  children, active, onClick,
}: { children: React.ReactNode; active?: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 rounded-md text-[12px] font-medium transition ${
        active
          ? 'bg-brand text-white shadow-sm'
          : 'text-text-2 hover:bg-bg-surface'
      }`}
    >
      {children}
    </button>
  );
}

function RestaurantCard({
  r, perf, onEdit, delay = 0,
}: {
  r: Restaurant;
  perf?: RestaurantPuantajSummary;
  onEdit: () => void;
  delay?: number;
}) {
  const model = MODEL_LABELS[r.pricing_model ?? ''] ?? {
    label: r.pricing_model ?? '?',
    color: 'bg-bg-surface2 text-text-2',
    ring: 'border-border',
    gradient: 'from-bg-surface2 to-bg-surface2',
  };

  const filled = perf?.unique_personnel ?? 0;
  const target = r.target_headcount ?? 0;
  const fillRatio = target > 0 ? filled / target : 0;
  const fillColor =
    fillRatio >= 1 ? 'bg-green-500'
    : fillRatio >= 0.7 ? 'bg-brand'
    : fillRatio >= 0.4 ? 'bg-yellow-500'
    : 'bg-red-500';

  return (
    <Link
      href={`/restoranlar/${r.id}`}
      className={`group block bg-bg-surface border ${model.ring} rounded-2xl p-5 shadow-sm hover:shadow-xl hover:-translate-y-1 hover:border-brand/60 transition-all duration-300 relative overflow-hidden animate-card`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Gradient backdrop */}
      <div
        className={`absolute inset-0 bg-gradient-to-br ${model.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none`}
      />

      {/* Renk şeridi */}
      <div className={`absolute top-0 left-0 right-0 h-1 ${fillColor} opacity-70`} />

      <div className="relative">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <div className="font-display font-semibold text-lg tracking-tight truncate">
              {r.brand ?? '—'}
            </div>
            <div className="text-text-3 text-sm">{r.branch ?? 'Merkez'}</div>
          </div>
          <span
            className={`px-2 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap ${model.color}`}
          >
            {model.label}
          </span>
        </div>

        {/* Anlaşma detay */}
        <div className="border-t border-border pt-3 space-y-1.5 text-sm mb-3">
          {r.pricing_model === 'fixed_monthly' ? (
            <Row
              label="Aylık tutar"
              value={`${tr(r.fixed_monthly_fee)} ₺`}
            />
          ) : (
            <>
              {r.hourly_rate != null && r.hourly_rate > 0 && (
                <Row label="Saatlik" value={`${tr(r.hourly_rate)} ₺/saat`} />
              )}
              {r.pricing_model === 'hourly_plus_package' &&
                r.package_rate != null &&
                r.package_rate > 0 && (
                  <Row label="Paket primi" value={`${tr(r.package_rate)} ₺/paket`} />
                )}
              {r.pricing_model === 'threshold_package' && (
                <>
                  <Row
                    label={`≤ ${r.package_threshold ?? 390} paket`}
                    value={`${tr(r.package_rate_low)} ₺/paket`}
                  />
                  <Row
                    label={`> ${r.package_threshold ?? 390} paket`}
                    value={`${tr(r.package_rate_high)} ₺/paket`}
                  />
                </>
              )}
            </>
          )}
          {r.contact_name && <Row label="Yetkili" value={r.contact_name} />}
        </div>

        {/* Mart 2026 performans */}
        <div className="border-t border-border pt-3">
          <div className="flex items-center justify-between text-[11px] mb-1.5">
            <span className="text-text-3 font-semibold uppercase tracking-wider">
              Mart 2026
            </span>
            <span className="font-mono text-text-2">
              {filled}/{target || '—'} kurye
            </span>
          </div>
          {perf ? (
            <div className="grid grid-cols-3 gap-2 text-xs">
              <PerfStat label="Saat" value={tr(Math.round(perf.total_hours))} />
              <PerfStat label="Paket" value={tr(perf.total_packages)} />
              <PerfStat
                label="Devamsızlık"
                value={String(perf.absences)}
                warn={perf.absences > 15}
              />
            </div>
          ) : (
            <div className="text-[11.5px] text-text-3">veri yok</div>
          )}
        </div>

        {/* Action footer */}
        <div className="mt-4 flex items-center justify-between gap-2">
          <span className="text-[12px] text-text-2 group-hover:text-brand transition flex items-center gap-1.5 font-medium">
            <span>Detayı görüntüle</span>
            <span className="opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition">→</span>
          </span>
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onEdit();
            }}
            className="text-[11px] text-text-3 hover:text-brand transition px-2 py-1 rounded-md hover:bg-brand-soft"
            title="Düzenle"
          >
            ✎ Düzenle
          </button>
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
    </Link>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-text-3">{label}</span>
      <span className="font-semibold text-text num">{value}</span>
    </div>
  );
}

function PerfStat({
  label, value, warn,
}: { label: string; value: string; warn?: boolean }) {
  return (
    <div className={`rounded-md px-2 py-1.5 ${warn ? 'bg-yellow-50' : 'bg-bg-surface2'}`}>
      <div className="text-[10px] uppercase tracking-wider text-text-3 font-semibold">
        {label}
      </div>
      <div
        className={`font-display text-sm font-semibold mt-0.5 num ${
          warn ? 'text-yellow-800' : 'text-text'
        }`}
      >
        {value}
      </div>
    </div>
  );
}
