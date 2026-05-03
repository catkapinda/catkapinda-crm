'use client';

import { useMemo, useState } from 'react';

import { RestaurantEditModal } from '@/components/restaurant-edit-modal';
import type { Restaurant, RestaurantPuantajSummary } from '@/lib/api';

const MODEL_LABELS: Record<string, { label: string; color: string; ring: string }> = {
  hourly_only: {
    label: 'Saatlik',
    color: 'bg-blue-50 text-blue-700',
    ring: 'border-blue-200',
  },
  hourly_plus_package: {
    label: 'Saat + Prim',
    color: 'bg-orange-50 text-orange-700',
    ring: 'border-orange-200',
  },
  threshold_package: {
    label: 'Eşikli (390)',
    color: 'bg-cream-100 text-yellow-900',
    ring: 'border-yellow-200',
  },
  fixed_monthly: {
    label: 'Aylık Sabit',
    color: 'bg-green-50 text-green-700',
    ring: 'border-green-200',
  },
};

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
  const [activeBrand, setActiveBrand] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  // Restoran id'sinden Mart 2026 performansını hızlı bulmak için map
  const perfMap = useMemo(() => {
    const m = new Map<number, RestaurantPuantajSummary>();
    for (const p of perf) {
      if (p.restaurant_id != null) m.set(p.restaurant_id, p);
    }
    return m;
  }, [perf]);

  // Brand filtreleme + arama + anlaşma tipi filtresi
  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    return restaurants.filter((r) => {
      if (activeBrand && r.brand !== activeBrand) return false;
      if (activeModel && r.pricing_model !== activeModel) return false;
      if (q) {
        const hay = `${r.brand ?? ''} ${r.branch ?? ''} ${r.contact_name ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [restaurants, activeBrand, activeModel, search]);

  const editing = editingId != null
    ? restaurants.find((r) => r.id === editingId) ?? null
    : null;

  // Marka chip listesi (frekansa göre sıralı)
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

  return (
    <>
      {/* Hero strip */}
      <div className="bg-bg-surface border border-border rounded-2xl shadow-md flex overflow-hidden mb-6">
        <HeroCell
          label="Toplam Aktif"
          value={restaurants.length.toString()}
          brand
          meta="canlı veri"
        />
        <HeroCell
          label="Saat + Prim"
          value={(byModel['hourly_plus_package'] ?? 0).toString()}
          meta="en yaygın"
          modelKey="hourly_plus_package"
          activeModel={activeModel}
          onClick={(k) => setActiveModel(activeModel === k ? null : k)}
        />
        <HeroCell
          label="Eşikli"
          value={(byModel['threshold_package'] ?? 0).toString()}
          meta="390 paket eşiği"
          modelKey="threshold_package"
          activeModel={activeModel}
          onClick={(k) => setActiveModel(activeModel === k ? null : k)}
        />
        <HeroCell
          label="Aylık Sabit"
          value={(byModel['fixed_monthly'] ?? 0).toString()}
          meta="prim olmadan"
          modelKey="fixed_monthly"
          activeModel={activeModel}
          onClick={(k) => setActiveModel(activeModel === k ? null : k)}
        />
        <HeroCell
          label="Saatlik"
          value={(byModel['hourly_only'] ?? 0).toString()}
          meta="sadece saat"
          modelKey="hourly_only"
          activeModel={activeModel}
          onClick={(k) => setActiveModel(activeModel === k ? null : k)}
        />
      </div>

      {/* Filtre barı */}
      <div className="bg-bg-surface border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2">
        <input
          type="search"
          placeholder="Restoran, şube veya yetkili ara…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-1.5 rounded-lg border border-border text-sm w-64 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
        />

        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-2">
          Marka
        </span>

        <button
          onClick={() => setActiveBrand(null)}
          className={`px-2.5 py-1 rounded-full text-[12px] font-medium transition ${
            activeBrand === null
              ? 'bg-brand text-white shadow-sm'
              : 'bg-bg-surface2 text-text-2 hover:bg-brand-soft hover:text-brand'
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
                : 'bg-bg-surface2 text-text-2 hover:bg-brand-soft hover:text-brand'
            }`}
          >
            {brand}
            <span
              className={`px-1.5 py-px rounded-full text-[10px] tabular-nums ${
                activeBrand === brand ? 'bg-white/25' : 'bg-bg-surface'
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
            className="ml-auto text-[12px] text-text-3 hover:text-brand transition"
          >
            Filtreleri temizle
          </button>
        )}
      </div>

      <div className="text-[12px] text-text-3 font-medium mb-3">
        {filtered.length} sonuç
        {activeBrand ? ` · ${activeBrand}` : ''}
        {activeModel ? ` · ${MODEL_LABELS[activeModel]?.label ?? activeModel}` : ''}
      </div>

      {/* Kart grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((r) => (
          <RestaurantCard
            key={r.id}
            r={r}
            perf={perfMap.get(r.id)}
            onClick={() => setEditingId(r.id)}
          />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="bg-bg-surface border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
          Sonuç bulunamadı.
        </div>
      )}

      {editing && (
        <RestaurantEditModal
          restaurant={editing}
          onClose={() => setEditingId(null)}
        />
      )}
    </>
  );
}

function HeroCell({
  label, value, meta, brand, modelKey, activeModel, onClick,
}: {
  label: string;
  value: string;
  meta?: string;
  brand?: boolean;
  modelKey?: string;
  activeModel?: string | null;
  onClick?: (k: string) => void;
}) {
  const isActive = !!modelKey && activeModel === modelKey;
  const clickable = !!onClick && !!modelKey;

  return (
    <div
      onClick={() => clickable && modelKey && onClick(modelKey)}
      className={`flex-1 px-5 py-4 border-r border-border last:border-r-0 transition ${
        brand ? 'bg-gradient-to-br from-brand-dark to-brand text-white' : ''
      } ${
        clickable ? 'cursor-pointer hover:bg-bg-surface2/50' : ''
      } ${
        isActive ? '!bg-brand-soft text-brand' : ''
      }`}
    >
      <div
        className={`text-[11px] font-semibold uppercase tracking-wider ${
          brand ? 'opacity-85' : isActive ? 'text-brand' : 'text-text-3'
        }`}
      >
        {label}
      </div>
      <div className="font-display text-2xl font-bold tracking-tight mt-1 num">
        {value}
      </div>
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

function RestaurantCard({
  r, perf, onClick,
}: {
  r: Restaurant;
  perf?: RestaurantPuantajSummary;
  onClick: () => void;
}) {
  const model = MODEL_LABELS[r.pricing_model ?? ''] ?? {
    label: r.pricing_model ?? '?',
    color: 'bg-bg-surface2 text-text-2',
    ring: 'border-border',
  };

  // Aylık performans: hedef vs gerçekleşen kurye sayısı oranı (renk göstergesi için)
  const filled = perf?.unique_personnel ?? 0;
  const target = r.target_headcount ?? 0;
  const fillRatio = target > 0 ? filled / target : 0;
  const fillColor =
    fillRatio >= 1 ? 'bg-green-500'
    : fillRatio >= 0.7 ? 'bg-brand'
    : fillRatio >= 0.4 ? 'bg-yellow-500'
    : 'bg-red-500';

  return (
    <button
      onClick={onClick}
      className={`group text-left bg-bg-surface border ${model.ring} rounded-2xl p-5 shadow-sm hover:shadow-lg hover:-translate-y-0.5 hover:border-brand/60 transition-all relative overflow-hidden`}
    >
      {/* Renk şeridi */}
      <div className={`absolute top-0 left-0 right-0 h-1 ${fillColor} opacity-70`} />

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

      {/* Mart 2026 performans badge */}
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

      {/* Hover'da düzenle ipucu */}
      <div className="mt-3 text-[11px] text-text-3 group-hover:text-brand transition flex items-center gap-1">
        <span className="opacity-60 group-hover:opacity-100">✎</span>
        <span>düzenlemek için tıkla</span>
      </div>
    </button>
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
