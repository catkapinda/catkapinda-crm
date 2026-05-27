'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import {
  ArrowRight, ArrowUpDown, Building2, Filter, LayoutGrid, List, Package,
  Pencil, Plus, Search, Sparkles, Store, TrendingUp, Users, X,
} from 'lucide-react';

import { RestaurantEditModal } from '@/components/restaurant-edit-modal';
import type { Restaurant, RestaurantPuantajSummary } from '@/lib/api';

const MODEL_META: Record<
  string,
  { label: string; accentClass: string; chipClass: string; barClass: string }
> = {
  hourly_only: {
    label: 'Saatlik',
    accentClass: 'from-sky-500/80 to-blue-500/80',
    chipClass: 'bg-sky-50 text-sky-800 ring-1 ring-sky-200',
    barClass: 'bg-sky-500',
  },
  hourly_plus_package: {
    label: 'Saat + Prim',
    accentClass: 'from-orange-500/80 to-amber-500/80',
    chipClass: 'bg-orange-50 text-orange-800 ring-1 ring-orange-200',
    barClass: 'bg-orange-500',
  },
  threshold_package: {
    label: 'Eşikli (390)',
    accentClass: 'from-amber-500/80 to-yellow-500/80',
    chipClass: 'bg-amber-50 text-amber-900 ring-1 ring-amber-200',
    barClass: 'bg-amber-500',
  },
  fixed_monthly: {
    label: 'Aylık Sabit',
    accentClass: 'from-emerald-500/80 to-green-500/80',
    chipClass: 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200',
    barClass: 'bg-emerald-500',
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

  const monthTotals = useMemo(() => {
    return perf.reduce(
      (acc, p) => {
        acc.hours += p.total_hours;
        acc.packages += p.total_packages;
        acc.absences += p.absences;
        acc.uniquePersonnel += p.unique_personnel;
        return acc;
      },
      { hours: 0, packages: 0, absences: 0, uniquePersonnel: 0 }
    );
  }, [perf]);

  const targetTotal = useMemo(
    () => restaurants.reduce((acc, r) => acc + (r.target_headcount ?? 0), 0),
    [restaurants],
  );
  const fillPct = targetTotal > 0
    ? Math.round((monthTotals.uniquePersonnel / targetTotal) * 100)
    : 0;

  const totalBrands = brandList.length;

  return (
    <div className="flex flex-col gap-7">
      {/* ───────── HERO — animated mesh gradient + live KPI strip ───────── */}
      <section className="relative rounded-[28px] overflow-hidden shadow-[0_25px_60px_-15px_rgba(15,82,186,0.35)]">
        {/* Animated background layers */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a2a6f] via-[#0F52BA] to-[#1e4ed8] animate-mesh-shift" />
        <div
          className="absolute inset-0 opacity-50 mix-blend-overlay animate-mesh-shift"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 30%, rgba(255,255,255,.5) 0%, transparent 45%), radial-gradient(circle at 75% 75%, rgba(255,200,100,.4) 0%, transparent 50%), radial-gradient(circle at 50% 100%, rgba(120,180,255,.3) 0%, transparent 60%)',
            animationDuration: '20s',
          }}
        />
        {/* Floating orbs */}
        <div className="absolute -top-10 -right-10 w-72 h-72 rounded-full bg-amber-300/20 blur-3xl animate-float-a pointer-events-none" />
        <div className="absolute -bottom-20 -left-10 w-96 h-96 rounded-full bg-blue-300/20 blur-3xl animate-float-b pointer-events-none" />
        {/* Dot grid */}
        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage: 'radial-gradient(circle, white 1px, transparent 1.5px)',
            backgroundSize: '22px 22px',
          }}
        />

        <div className="relative px-8 py-9 text-white">
          <div className="flex items-start justify-between gap-6 flex-wrap mb-7">
            <div>
              <div className="text-[11px] font-semibold tracking-[0.28em] uppercase text-white/70 mb-2.5 flex items-center gap-2">
                <span className="relative flex w-2 h-2">
                  <span className="absolute inset-0 rounded-full bg-amber-300 animate-ping opacity-75" />
                  <span className="relative w-2 h-2 rounded-full bg-amber-300" />
                </span>
                Satış · Restoranlar
              </div>
              <h1 className="font-display text-[42px] leading-[1.05] font-bold tracking-tight mb-2 flex items-center gap-3">
                <span className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-white/15 backdrop-blur-md ring-1 ring-white/25">
                  <Building2 className="w-6 h-6" strokeWidth={2.2} />
                </span>
                Restoran Operasyonu
              </h1>
              <p className="text-white/75 text-[15px] max-w-xl leading-relaxed">
                <span className="text-white font-semibold">{restaurants.length}</span> aktif müşteri ·{' '}
                <span className="text-white font-semibold">{totalBrands}</span> marka ·
                tarife, kapasite ve kurye taleplerini tek panelden yönet.
              </p>
            </div>
            <button
              onClick={() => setCreating(true)}
              className="group relative px-5 py-3 rounded-2xl bg-white text-brand-dark text-[13px] font-bold shadow-lg shadow-black/20 hover:shadow-xl hover:-translate-y-0.5 transition-all inline-flex items-center gap-2 overflow-hidden"
            >
              <span className="absolute inset-0 bg-gradient-to-r from-amber-200/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              <Plus className="w-4 h-4 relative" strokeWidth={2.6} />
              <span className="relative">Yeni Müşteri</span>
            </button>
          </div>

          {/* HERO Live KPI strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/10 rounded-2xl overflow-hidden ring-1 ring-white/15 backdrop-blur-md">
            <HeroStat
              icon={Store}
              label="Aktif restoran"
              value={tr(restaurants.length)}
              sub={`${totalBrands} marka`}
            />
            <HeroStat
              icon={Users}
              label="Çalışan kurye"
              value={tr(monthTotals.uniquePersonnel)}
              sub={
                targetTotal > 0
                  ? `${fillPct}% doluluk (hedef ${tr(targetTotal)})`
                  : 'hedef yok'
              }
              accent={fillPct >= 85 ? 'amber' : undefined}
            />
            <HeroStat
              icon={Package}
              label="Aylık paket"
              value={tr(monthTotals.packages)}
              sub="son tamamlanan ay"
            />
            <HeroStat
              icon={TrendingUp}
              label="Aylık saat"
              value={tr(Math.round(monthTotals.hours))}
              sub={`${monthTotals.absences} devamsızlık`}
            />
          </div>
        </div>
      </section>

      {/* ───────── Pricing Model KPI row ───────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <ModelKpiCard
          icon={Package}
          label="Saat + Prim"
          accent="orange"
          value={byModel['hourly_plus_package'] ?? 0}
          active={activeModel === 'hourly_plus_package'}
          onClick={() => setActiveModel(activeModel === 'hourly_plus_package' ? null : 'hourly_plus_package')}
        />
        <ModelKpiCard
          icon={Sparkles}
          label="Eşikli (390)"
          accent="amber"
          value={byModel['threshold_package'] ?? 0}
          active={activeModel === 'threshold_package'}
          onClick={() => setActiveModel(activeModel === 'threshold_package' ? null : 'threshold_package')}
        />
        <ModelKpiCard
          icon={Store}
          label="Aylık Sabit"
          accent="emerald"
          value={byModel['fixed_monthly'] ?? 0}
          active={activeModel === 'fixed_monthly'}
          onClick={() => setActiveModel(activeModel === 'fixed_monthly' ? null : 'fixed_monthly')}
        />
        <ModelKpiCard
          icon={Building2}
          label="Saatlik"
          accent="sky"
          value={byModel['hourly_only'] ?? 0}
          active={activeModel === 'hourly_only'}
          onClick={() => setActiveModel(activeModel === 'hourly_only' ? null : 'hourly_only')}
        />
      </div>

      {/* ───────── Toolbar — sticky glass ───────── */}
      <div className="sticky top-2 z-20 bg-white/85 backdrop-blur-xl border border-border rounded-2xl px-3 py-2.5 shadow-sm flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-3" strokeWidth={2.2} />
          <input
            type="search"
            placeholder="Marka, şube, yetkili…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl border border-border text-[13px] bg-bg-surface focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition placeholder:text-text-3"
          />
        </div>

        <div className="hidden md:flex items-center gap-1 bg-bg-surface2/60 rounded-xl p-1 ring-1 ring-border/60">
          <SortPill active={sortKey === 'brand'} onClick={() => setSortKey('brand')}>A–Z</SortPill>
          <SortPill active={sortKey === 'packages'} onClick={() => setSortKey('packages')}>
            <span className="inline-flex items-center gap-1">Paket <ArrowUpDown className="w-3 h-3" strokeWidth={2.2} /></span>
          </SortPill>
          <SortPill active={sortKey === 'hours'} onClick={() => setSortKey('hours')}>
            <span className="inline-flex items-center gap-1">Saat <ArrowUpDown className="w-3 h-3" strokeWidth={2.2} /></span>
          </SortPill>
          <SortPill active={sortKey === 'fill'} onClick={() => setSortKey('fill')}>
            <span className="inline-flex items-center gap-1">Doluluk <ArrowUpDown className="w-3 h-3" strokeWidth={2.2} /></span>
          </SortPill>
        </div>

        <div className="flex items-center gap-1 bg-bg-surface2/60 rounded-xl p-1 ring-1 ring-border/60">
          <SortPill active={view === 'grid'} onClick={() => setView('grid')}>
            <LayoutGrid className="w-3.5 h-3.5" strokeWidth={2.2} />
          </SortPill>
          <SortPill active={view === 'group'} onClick={() => setView('group')}>
            <List className="w-3.5 h-3.5" strokeWidth={2.2} />
          </SortPill>
        </div>

        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
          {filtered.length} sonuç
        </span>
      </div>

      {/* ───────── Brand chips ───────── */}
      <div className="flex flex-wrap items-center gap-1.5 -mt-2">
        <span className="text-[10.5px] text-text-3 font-bold uppercase tracking-[0.18em] mr-1 inline-flex items-center gap-1">
          <Filter className="w-3 h-3" strokeWidth={2.4} />
          Marka
        </span>
        <button
          onClick={() => setActiveBrand(null)}
          className={`px-2.5 py-1 rounded-full text-[12px] font-semibold transition ${
            activeBrand === null
              ? 'bg-brand text-white shadow-sm shadow-brand/30'
              : 'bg-bg-surface border border-border text-text-2 hover:bg-brand-soft hover:text-brand hover:border-brand/30'
          }`}
        >
          Tümü
        </button>
        {brandList.map(([brand, count]) => (
          <button
            key={brand}
            onClick={() => setActiveBrand(activeBrand === brand ? null : brand)}
            className={`px-2.5 py-1 rounded-full text-[12px] font-semibold transition inline-flex items-center gap-1.5 ${
              activeBrand === brand
                ? 'bg-brand text-white shadow-sm shadow-brand/30'
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
            className="ml-auto text-[12px] text-text-3 hover:text-brand transition underline-offset-2 hover:underline inline-flex items-center gap-1 font-medium"
          >
            <X className="w-3 h-3" strokeWidth={2.4} /> filtreleri temizle
          </button>
        )}
      </div>

      {/* ───────── Kartlar ───────── */}
      {view === 'grid' ? (
        <CardGrid
          items={filtered}
          perfMap={perfMap}
          onEdit={(id) => setEditingId(id)}
        />
      ) : (
        <div className="space-y-7">
          {groups.map(([brand, items]) => (
            <div key={brand}>
              <div className="flex items-baseline gap-3 mb-3">
                <h3 className="font-display text-xl font-bold tracking-tight">
                  {brand}
                </h3>
                <span className="text-[11px] text-text-3 font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-bg-surface2">
                  {items.length} şube
                </span>
                <div className="flex-1 h-px bg-gradient-to-r from-border to-transparent" />
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
        <div className="bg-bg-surface border border-border rounded-2xl p-12 text-center">
          <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-bg-surface2 flex items-center justify-center text-text-3">
            <Building2 className="w-7 h-7" strokeWidth={1.6} />
          </div>
          <div className="font-display font-bold text-text mb-1">Sonuç bulunamadı</div>
          <div className="text-text-3 text-sm">Filtre veya arama terimini sadeleştir.</div>
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
    </div>
  );
}

// ────────────────────────────────────────────────────────────────

function HeroStat({
  icon: Icon, label, value, sub, accent,
}: {
  icon: typeof Building2;
  label: string;
  value: string;
  sub?: string;
  accent?: 'amber';
}) {
  return (
    <div className="bg-white/[0.06] px-5 py-4 group transition-colors hover:bg-white/[0.1]">
      <div className="flex items-center gap-2 text-[10.5px] font-bold uppercase tracking-[0.16em] text-white/65 mb-1.5">
        <Icon className="w-3.5 h-3.5" strokeWidth={2.2} />
        {label}
      </div>
      <div className={`font-display text-[26px] leading-none font-bold tracking-tight tabular-nums ${
        accent === 'amber' ? 'text-amber-200' : 'text-white'
      }`}>
        {value}
      </div>
      {sub && <div className="text-[11.5px] text-white/65 mt-1.5 font-medium">{sub}</div>}
    </div>
  );
}

function ModelKpiCard({
  icon: Icon, label, value, accent, active, onClick,
}: {
  icon: typeof Building2;
  label: string;
  value: number;
  accent: 'sky' | 'orange' | 'amber' | 'emerald';
  active: boolean;
  onClick: () => void;
}) {
  const barMap: Record<string, string> = {
    sky: 'bg-gradient-to-b from-sky-500 to-blue-400',
    orange: 'bg-gradient-to-b from-orange-500 to-amber-400',
    amber: 'bg-gradient-to-b from-amber-500 to-yellow-300',
    emerald: 'bg-gradient-to-b from-emerald-500 to-green-300',
  };
  const iconBgMap: Record<string, string> = {
    sky: 'bg-sky-50 text-sky-700',
    orange: 'bg-orange-50 text-orange-700',
    amber: 'bg-amber-50 text-amber-700',
    emerald: 'bg-emerald-50 text-emerald-700',
  };
  return (
    <button
      onClick={onClick}
      className={`group relative bg-white rounded-2xl px-5 py-4 shadow-sm border overflow-hidden text-left transition-all duration-300 hover:shadow-xl hover:-translate-y-1 ${
        active
          ? 'border-brand ring-2 ring-brand/30 shadow-md'
          : 'border-border hover:border-brand/40'
      }`}
    >
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${barMap[accent]}`} />
      <div className="flex items-start justify-between mb-2.5">
        <div className="text-[10.5px] uppercase tracking-[0.16em] text-text-3 font-bold">
          {label}
        </div>
        <div className={`w-8 h-8 rounded-xl ${iconBgMap[accent]} flex items-center justify-center transition-transform group-hover:scale-110 group-hover:rotate-3`}>
          <Icon className="w-4 h-4" strokeWidth={2.2} />
        </div>
      </div>
      <div className="font-display text-[28px] font-bold tracking-tight leading-none tabular-nums">
        {value}
      </div>
      <div className="text-[11px] text-text-3 mt-2 font-medium inline-flex items-center gap-1">
        {active ? (
          <span className="text-brand font-bold">Filtre aktif</span>
        ) : (
          <>tıkla <ArrowRight className="w-3 h-3 opacity-60 group-hover:translate-x-0.5 transition-transform" strokeWidth={2.4} /></>
        )}
      </div>
    </button>
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
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {items.map((r, idx) => (
        <RestaurantCard
          key={r.id}
          r={r}
          perf={perfMap.get(r.id)}
          onEdit={() => onEdit(r.id)}
          delay={Math.min(idx * 28, 320)}
        />
      ))}
    </div>
  );
}

function SortPill({
  children, active, onClick,
}: { children: React.ReactNode; active?: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1.5 rounded-lg text-[12px] font-semibold transition ${
        active
          ? 'bg-white text-brand shadow-sm ring-1 ring-brand/20'
          : 'text-text-2 hover:bg-bg-surface hover:text-text'
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
  const model = MODEL_META[r.pricing_model ?? ''] ?? {
    label: r.pricing_model ?? '?',
    accentClass: 'from-slate-400/60 to-slate-500/60',
    chipClass: 'bg-bg-surface2 text-text-2 ring-1 ring-border',
    barClass: 'bg-slate-400',
  };

  const filled = perf?.unique_personnel ?? 0;
  const target = r.target_headcount ?? 0;
  const fillRatio = target > 0 ? Math.min(1, filled / target) : 0;
  const fillPct = Math.round(fillRatio * 100);
  const fillColorClass =
    fillRatio >= 1 ? 'text-emerald-700 bg-emerald-50 ring-emerald-200'
    : fillRatio >= 0.7 ? 'text-brand bg-brand-soft ring-brand/20'
    : fillRatio >= 0.4 ? 'text-amber-700 bg-amber-50 ring-amber-200'
    : 'text-red-700 bg-red-50 ring-red-200';
  const barFillClass =
    fillRatio >= 1 ? 'bg-emerald-500'
    : fillRatio >= 0.7 ? 'bg-brand'
    : fillRatio >= 0.4 ? 'bg-amber-500'
    : 'bg-red-500';

  return (
    <Link
      href={`/restoranlar/${r.id}`}
      className="group relative bg-white border border-border rounded-2xl p-5 shadow-sm hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 overflow-hidden animate-card"
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Animated gradient border on hover */}
      <div
        className={`absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r ${model.accentClass} opacity-90 transition-transform duration-300 origin-left scale-x-100`}
      />
      {/* Soft hover backdrop */}
      <div
        className={`absolute inset-0 bg-gradient-to-br ${model.accentClass} opacity-0 group-hover:opacity-[0.04] transition-opacity duration-500 pointer-events-none`}
      />

      <div className="relative">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <div className="font-display font-bold text-[17px] tracking-tight truncate text-text">
              {r.brand ?? '—'}
            </div>
            <div className="text-text-3 text-[12.5px] mt-0.5 truncate">
              {r.branch ?? 'Merkez'}
            </div>
          </div>
          <span
            className={`shrink-0 px-2.5 py-1 rounded-full text-[10.5px] font-bold uppercase tracking-wider ${model.chipClass}`}
          >
            {model.label}
          </span>
        </div>

        {/* Tarife satırları */}
        <div className="rounded-xl bg-bg-surface2/40 ring-1 ring-border/60 px-3.5 py-2.5 space-y-1.5 mb-3">
          {r.pricing_model === 'fixed_monthly' ? (
            <Row label="Aylık sabit" value={`${tr(r.fixed_monthly_fee)} ₺`} bold />
          ) : (
            <>
              {r.hourly_rate != null && r.hourly_rate > 0 && (
                <Row label="Saat ücreti" value={`${tr(r.hourly_rate)} ₺`} />
              )}
              {r.pricing_model === 'hourly_plus_package' &&
                r.package_rate != null && r.package_rate > 0 && (
                  <Row label="Paket primi" value={`${tr(r.package_rate)} ₺`} />
              )}
              {r.pricing_model === 'threshold_package' && (
                <>
                  <Row
                    label={`≤ ${r.package_threshold ?? 390} paket`}
                    value={`${tr(r.package_rate_low)} ₺`}
                  />
                  <Row
                    label={`> ${r.package_threshold ?? 390} paket`}
                    value={`${tr(r.package_rate_high)} ₺`}
                  />
                </>
              )}
            </>
          )}
        </div>

        {/* Doluluk bar */}
        {target > 0 && (
          <div className="mb-3">
            <div className="flex items-center justify-between text-[10.5px] font-bold uppercase tracking-wider mb-1">
              <span className="text-text-3">Kurye doluluğu</span>
              <span className={`tabular-nums px-1.5 py-0.5 rounded-md ring-1 ${fillColorClass}`}>
                {filled}/{target} · {fillPct}%
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-bg-surface2 overflow-hidden">
              <div
                className={`h-full rounded-full ${barFillClass} transition-all duration-700`}
                style={{ width: `${fillPct}%` }}
              />
            </div>
          </div>
        )}

        {/* Mart 2026 stats grid */}
        <div className="grid grid-cols-3 gap-1.5">
          <PerfStat label="Saat" value={perf ? tr(Math.round(perf.total_hours)) : '—'} />
          <PerfStat label="Paket" value={perf ? tr(perf.total_packages) : '—'} />
          <PerfStat
            label="Devamsız"
            value={perf ? String(perf.absences) : '—'}
            warn={(perf?.absences ?? 0) > 15}
          />
        </div>

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-border/60 flex items-center justify-between gap-2">
          <span className="text-[12px] text-text-2 group-hover:text-brand transition flex items-center gap-1.5 font-bold">
            <span>Detayı aç</span>
            <ArrowRight className="w-3.5 h-3.5 -translate-x-1 opacity-0 group-hover:opacity-100 group-hover:translate-x-0 transition" strokeWidth={2.4} />
          </span>
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onEdit();
            }}
            className="text-[11px] text-text-3 hover:text-brand transition px-2 py-1 rounded-md hover:bg-brand-soft inline-flex items-center gap-1 font-semibold"
            title="Düzenle"
          >
            <Pencil className="w-3 h-3" strokeWidth={2.4} /> Düzenle
          </button>
        </div>
      </div>

      <style jsx>{`
        :global(.animate-card) {
          animation: card-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
        }
        @keyframes card-in {
          from { opacity: 0; transform: translateY(10px) scale(0.985); }
          to   { opacity: 1; transform: translateY(0)  scale(1); }
        }
      `}</style>
    </Link>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex justify-between text-[12.5px]">
      <span className="text-text-3">{label}</span>
      <span className={`tabular-nums text-text ${bold ? 'font-bold' : 'font-semibold'}`}>{value}</span>
    </div>
  );
}

function PerfStat({
  label, value, warn,
}: { label: string; value: string; warn?: boolean }) {
  return (
    <div className={`rounded-lg px-2 py-2 ring-1 transition ${
      warn
        ? 'bg-amber-50 ring-amber-200'
        : 'bg-bg-surface2/60 ring-border/60'
    }`}>
      <div className="text-[9.5px] uppercase tracking-[0.14em] text-text-3 font-bold">
        {label}
      </div>
      <div
        className={`font-display text-[15px] font-bold tracking-tight mt-0.5 tabular-nums ${
          warn ? 'text-amber-900' : 'text-text'
        }`}
      >
        {value}
      </div>
    </div>
  );
}
