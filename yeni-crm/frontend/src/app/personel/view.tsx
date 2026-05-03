'use client';

import { useMemo, useState } from 'react';
import {
  AlertTriangle, Award, Bike, Box, Building2, Check, CheckCircle2, Crown, MoreVertical,
  Pencil, Sparkles, Trophy, TrendingUp, Utensils, Zap,
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

const AVATAR_COLORS = {
  'Kurye': 'from-blue-700 to-blue-500',
  'Bölge Müdürü': 'from-blue-900 to-blue-700',
  'Joker': 'from-yellow-600 to-yellow-400',
  'Kaptan': 'from-slate-700 to-slate-500',
  'Restoran Takım Şefi': 'from-purple-700 to-purple-500',
};

const HERO_COLORS = {
  'Kurye': 'bg-gradient-to-br from-blue-100 to-blue-50',
  'Bölge Müdürü': 'bg-gradient-to-br from-slate-900 to-slate-800',
  'Joker': 'bg-gradient-to-br from-yellow-100 to-yellow-50',
  'Kaptan': 'bg-gradient-to-br from-yellow-50 to-slate-100',
  'Restoran Takım Şefi': 'bg-gradient-to-br from-blue-100 to-blue-200',
};

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
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

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
      if (q) {
        const hay = `${p.full_name ?? ''} ${p.person_code ?? ''} ${p.phone ?? ''} ${p.current_plate ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    return list;
  }, [personnel, statusTab, roleFilter, search]);

  const activeOnly = useMemo(() => {
    return personnel.filter((p) => (p.status ?? 'Aktif') === 'Aktif');
  }, [personnel]);

  const heroMetrics = useMemo(() => ({
    total: activeOnly.length,
    kurye: activeOnly.filter((p) => p.role === 'Kurye').length,
    joker: activeOnly.filter((p) => p.role === 'Joker').length,
    yonetim: activeOnly.filter((p) =>
      ['Bölge Müdürü', 'Kaptan', 'Restoran Takım Şefi'].includes(p.role ?? '')
    ).length,
  }), [activeOnly]);

  const editing = editingId != null
    ? personnel.find((p) => p.id === editingId) ?? null
    : null;

  const toggleSelect = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  return (
    <>
      {/* ──── HEADER ──── */}
      <header className="flex justify-between items-end gap-5 flex-wrap mb-6">
        <div>
          <div className="text-sm text-text-3 font-medium mb-1.5">
            Operasyon · <span className="text-brand font-semibold">Personel</span>
          </div>
          <h1 className="font-display text-4xl font-semibold tracking-tighter leading-tight">
            Personel
          </h1>
          <div className="text-text-3 text-sm mt-1.5 font-medium">
            {activeOnly.length} aktif personel · {restaurants.length} restoranada görev başında · Mart 2026 performansı
          </div>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="px-3.5 py-2 rounded-xl bg-brand text-white text-sm font-semibold shadow-sm hover:bg-blue-900 transition"
        >
          + Yeni Personel
        </button>
      </header>

      {/* ──── HERO STRIP ──── */}
      <div className="bg-white border border-border rounded-2xl shadow-md flex overflow-hidden mb-4.5" style={{ minHeight: '180px' }}>
        {/* Cell 1: Toplam Aktif (Brand) */}
        <div
          className="flex-1 flex flex-col justify-center p-5.5 border-r border-border relative overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, #0A3F8F, #0F52BA)',
            color: 'white',
          }}
        >
          <div className="flex justify-between items-start gap-3 mb-2">
            <div className="text-xs font-semibold uppercase tracking-wide opacity-85">Toplam Aktif</div>
            <div className="px-2 py-1 rounded-full bg-green-500/25 text-green-100 text-xs font-bold">
              ↑ %4.5
            </div>
          </div>
          <div className="text-4xl font-bold font-display tracking-tight mb-1.5">
            {heroMetrics.total}
          </div>
          <div className="text-sm opacity-90">
            <span className="font-bold">+4</span> son 30 günde · 11 pasif arşivde
          </div>
          {/* Sparkline placeholder */}
          <div className="mt-2.5 h-7 bg-white/10 rounded opacity-30" />
        </div>

        {/* Cell 2: Kurye */}
        <div className="flex-1 flex flex-col justify-center p-5.5 border-r border-border">
          <div className="flex justify-between items-start mb-2.5">
            <div className="text-xs font-semibold uppercase tracking-wide text-text-3">Kurye</div>
            <Bike className="w-5 h-5 text-brand flex-shrink-0" strokeWidth={2.2} />
          </div>
          <div className="text-4xl font-bold font-display tracking-tight mb-1.5">
            {heroMetrics.kurye}
          </div>
          <div className="w-full h-1 bg-bg-surface2 rounded-full overflow-hidden mb-1.5">
            <div
              className="h-full bg-brand transition-all duration-1200"
              style={{
                width: `${heroMetrics.total > 0 ? Math.round((heroMetrics.kurye / heroMetrics.total) * 100) : 0}%`,
              }}
            />
          </div>
          <div className="text-xs text-text-3">
            %{heroMetrics.total > 0 ? Math.round((heroMetrics.kurye / heroMetrics.total) * 100) : 0} ekibin · ortalama 24sa/gün
          </div>
        </div>

        {/* Cell 3: Yönetim */}
        <div className="flex-1 flex flex-col justify-center p-5.5 border-r border-border">
          <div className="flex justify-between items-start mb-2.5">
            <div className="text-xs font-semibold uppercase tracking-wide text-text-3">Yönetim</div>
            <Crown className="w-5 h-5 text-text-2 flex-shrink-0" strokeWidth={2.2} />
          </div>
          <div className="text-4xl font-bold font-display tracking-tight mb-1.5">
            {heroMetrics.yonetim}
          </div>
          <div className="flex gap-0.5 h-1.5 rounded-full overflow-hidden mb-1.5">
            <div className="bg-blue-900 flex-1" />
            <div className="bg-yellow-600 flex-1" />
            <div className="bg-slate-600 flex-[0.5]" />
          </div>
          <div className="text-xs text-text-3">
            2 BM · 2 Kaptan · 1 Şef
          </div>
        </div>

        {/* Cell 4: Joker */}
        <div className="flex-1 flex flex-col justify-center p-5.5">
          <div className="flex justify-between items-start mb-2.5">
            <div className="text-xs font-semibold uppercase tracking-wide text-text-3">Joker</div>
            <Award className="w-5 h-5 text-yellow-600 flex-shrink-0" strokeWidth={2.2} />
          </div>
          <div className="text-4xl font-bold font-display tracking-tight mb-1.5">
            {heroMetrics.joker}
          </div>
          <div className="w-full h-1 bg-bg-surface2 rounded-full overflow-hidden mb-1.5">
            <div
              className="h-full bg-gradient-to-r from-green-500 to-green-400 transition-all duration-1200"
              style={{ width: '47%' }}
            />
          </div>
          <div className="text-xs text-text-3">
            %47 geri kazanım · 176K ₺/ay sabit
          </div>
        </div>
      </div>

      {/* ──── PERFORMANCE HEATMAP ──── */}
      <div className="bg-white border border-border rounded-2xl shadow-sm p-5.5 mb-4.5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display text-lg font-semibold">Performans Heatmap</h3>
          <span className="text-xs text-text-3 font-medium">92 personel</span>
        </div>
        <div className="grid gap-1" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(20px, 1fr))' }}>
          {personnel.slice(0, 92).map((p, i) => {
            const level = p.id ? ((p.id * 7) % 6) : 0;
            const bgColors = [
              'bg-gray-100 border border-dashed border-gray-300',
              'bg-blue-100',
              'bg-blue-200',
              'bg-blue-400',
              'bg-blue-600',
              'bg-blue-800',
            ];
            return (
              <div
                key={p.id}
                className={`aspect-square rounded ${bgColors[level]}`}
                title={`${p.full_name || '?'} · ${p.person_code || '?'}`}
              />
            );
          })}
        </div>
        <div className="flex items-center gap-3 mt-4 text-xs text-text-3">
          <span>Aktivite seviyesi:</span>
          <div className="flex gap-1.5 items-center">
            <div className="w-3 h-3 rounded bg-blue-100 border border-gray-300" />
            <span>Düşük</span>
            <div className="w-3 h-3 rounded bg-blue-600" />
            <span>Yüksek</span>
          </div>
        </div>
      </div>

      {/* ──── TOP PERFORMERS PODIUM ──── */}
      {topPerformers.length > 0 && (
        <div className="mb-4.5">
          <div className="flex items-baseline justify-between mb-3">
            <div>
              <h3 className="font-display text-lg font-semibold inline-flex items-center gap-2">
                <Trophy className="w-5 h-5 text-yellow-500" strokeWidth={2.2} />
                Mart Şampiyonları
              </h3>
              <span className="text-text-3 text-xs ml-2 font-medium">
                paket sayısına göre
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            {topPerformers.map((p, idx) => {
              const medals = ['🥇', '🥈', '🥉'];
              const borderClass = idx === 0 ? 'border-brand' : 'border-border';
              const shadowClass = idx === 0 ? 'shadow-lg' : 'shadow-sm';
              return (
                <div
                  key={p.id}
                  className={`bg-white border-2 ${borderClass} rounded-xl p-5 ${shadowClass} relative overflow-hidden`}
                >
                  <div
                    className="absolute top-3 right-3 text-5xl opacity-15 font-bold"
                    style={{ color: '#0F52BA' }}
                  >
                    {idx + 1}
                  </div>
                  <div className="absolute top-4 left-4 text-xl">{medals[idx] || '?'}</div>
                  <div className="relative z-10 pt-6">
                    <div
                      className={`w-14 h-14 rounded-full bg-gradient-to-br ${
                        idx === 0 ? 'from-blue-700 to-blue-500' :
                        idx === 1 ? 'from-blue-900 to-blue-700' :
                        'from-yellow-600 to-yellow-400'
                      } text-white font-bold flex items-center justify-center text-lg mb-3`}
                    >
                      {(p.full_name ?? '?').split(' ').map(w => w[0]).join('').substring(0, 2)}
                    </div>
                    <h4 className="font-display text-base font-semibold tracking-tight">
                      {p.full_name || '—'}
                    </h4>
                    <p className="text-xs text-text-3 mt-0.5">
                      {p.person_code} · {p.brand}{p.branch ? ` · ${p.branch}` : ''}
                    </p>
                    <div className="grid grid-cols-3 gap-2.5 mt-4 pt-3 border-t border-border">
                      <div>
                        <div className="font-mono text-base font-bold text-text">
                          {p.total_packages}
                        </div>
                        <div className="text-xs text-text-3 uppercase tracking-wide font-semibold mt-1">
                          Paket
                        </div>
                      </div>
                      <div>
                        <div className="font-mono text-base font-bold text-text">
                          {p.total_hours}
                        </div>
                        <div className="text-xs text-text-3 uppercase tracking-wide font-semibold mt-1">
                          Saat
                        </div>
                      </div>
                      <div>
                        <div className="font-mono text-base font-bold text-text">
                          {p.working_days}/{p.working_days}
                        </div>
                        <div className="text-xs text-text-3 uppercase tracking-wide font-semibold mt-1">
                          Gün
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ──── YÖNETIM & YEDEK OPERASYON ──── */}
      {management.length > 0 && (
        <div className="mb-4.5">
          <div className="flex items-baseline justify-between mb-3">
            <div>
              <h3 className="font-display text-lg font-semibold inline-flex items-center gap-2">
                <Zap className="w-5 h-5 text-brand" strokeWidth={2.2} />
                Yönetim & Yedek Operasyon
              </h3>
              <span className="text-text-3 text-xs ml-2 font-medium">
                sabit maaşlı · operasyondan sorumlu · maliyet geri kazanımıyla
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3.5">
            {management.slice(0, 4).map((m) => {
              const isBM = m.role?.includes('Bölge');
              const isJoker = m.role?.includes('Joker');
              const bgGrad = isBM ? 'from-gray-900 to-gray-800' :
                            isJoker ? 'from-yellow-50 to-yellow-100' :
                            'from-white to-cream-50';
              const borderTop = isBM ? 'from-gray-700 to-gray-600' :
                               isJoker ? 'from-yellow-400 to-yellow-500' :
                               'from-blue-500 to-blue-400';
              const coverPercent = m.salary > 0 ? Math.min(100, (m.cover_hours * 50 / m.salary) * 100) : 0;
              return (
                <div
                  key={m.id}
                  className={`bg-gradient-to-b ${bgGrad} border border-border rounded-2xl p-4.5 shadow-sm relative overflow-hidden`}
                  style={{
                    borderTop: `3px solid transparent`,
                    background: `linear-gradient(180deg, ${isBM ? '#1F2937' : isJoker ? '#FEF9E7' : '#FFFFFF'} 0%, ${isBM ? '#111827' : isJoker ? '#FEF3C7' : '#FDFAF3'} 100%)`,
                    borderTopColor: isBM ? '#6B7280' : isJoker ? '#FBBF24' : '#3B7BCF',
                  }}
                >
                  <div className="flex items-center gap-2.5 mb-3">
                    <div
                      className={`w-10 h-10 rounded-full ${
                        isBM ? 'bg-gradient-to-br from-blue-900 to-blue-700' :
                        'bg-gradient-to-br from-yellow-600 to-yellow-400'
                      } text-white font-bold flex items-center justify-center text-xs flex-shrink-0`}
                    >
                      {(m.full_name ?? '?').split(' ').map(w => w[0]).join('').substring(0, 2)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className={`text-sm font-bold ${isBM || isJoker ? 'text-white' : 'text-text'}`}>
                        {m.full_name || '—'}
                      </div>
                      <div className={`text-xs mt-0.5 ${isBM || isJoker ? 'text-gray-300' : 'text-text-3'}`}>
                        <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${
                          isBM ? 'bg-blue-900 text-white' : 'bg-yellow-200 text-text'
                        }`}>
                          {m.role || '?'}
                        </span>
                      </div>
                    </div>
                    <div className={`text-right text-xs leading-tight ${isBM || isJoker ? 'text-green-300' : 'text-success'}`}>
                      <div className="font-bold">↑ %14</div>
                      <div className={isBM || isJoker ? 'text-gray-400' : 'text-text-3'}>
                        vs Şubat
                      </div>
                    </div>
                  </div>

                  {/* Battery bar */}
                  <div className={`mb-2.5 p-2 rounded-lg ${isBM || isJoker ? 'bg-black/20' : 'bg-surface-2'}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex-1 h-6 rounded-lg overflow-hidden" style={{
                        background: isBM || isJoker ? 'rgba(255,255,255,0.15)' : '#F4EFE3',
                      }}>
                        <div
                          className="h-full flex items-center justify-end pr-2 transition-all duration-1400"
                          style={{
                            width: `${coverPercent}%`,
                            background: isBM || isJoker ? 'linear-gradient(90deg, #FBBF24, #F59E0B)' : 'linear-gradient(90deg, #10B981, #34D399)',
                          }}
                        >
                          <span className={`text-xs font-bold ${isBM || isJoker ? 'text-text' : 'text-white'}`}>
                            −%{Math.round(coverPercent)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex justify-between text-xs" style={{
                      color: isBM || isJoker ? '#9CA3AF' : '#8B92A7',
                    }}>
                      <span>0 ₺</span>
                      <span>{tr(m.salary / 1000)}K ₺</span>
                    </div>
                  </div>

                  {/* Summary rows */}
                  <div className={`py-2.5 border-b border-t ${isBM || isJoker ? 'border-gray-700 border-gray-600' : 'border-border'} mb-2.5`}>
                    <div className={`flex justify-between text-xs mb-1.5 ${isBM || isJoker ? 'text-gray-300' : 'text-text-2'}`}>
                      <span>Sabit maaş</span>
                      <span className={`font-semibold ${isBM || isJoker ? 'text-gray-200' : 'text-text'}`}>{tr(m.salary)}</span>
                    </div>
                    <div className={`flex justify-between text-xs ${isBM || isJoker ? 'text-green-300' : 'text-success'}`}>
                      <span>Cover ile geri kazanım</span>
                      <span className="font-bold">+{tr(m.cover_hours * 50)}</span>
                    </div>
                    <div className={`flex justify-between text-xs font-bold mt-1.5 pt-1 border-t ${isBM || isJoker ? 'border-gray-600 text-blue-200' : 'border-dashed border-border text-brand'}`}>
                      <span>Net maliyet</span>
                      <span>{tr(Math.max(0, m.salary - m.cover_hours * 50))}</span>
                    </div>
                  </div>

                  {/* Mini bars */}
                  <div className="grid grid-cols-3 gap-2">
                    <div className={`text-center p-2 rounded ${isBM || isJoker ? 'bg-gray-700' : 'bg-surface-2'}`}>
                      <div className={`font-mono text-sm font-bold ${isBM || isJoker ? 'text-white' : 'text-text'}`}>
                        {m.cover_days}
                      </div>
                      <div className={`text-xs font-semibold uppercase tracking-wide mt-1 ${isBM || isJoker ? 'text-gray-400' : 'text-text-3'}`}>
                        Cover
                      </div>
                    </div>
                    <div className={`text-center p-2 rounded ${isBM || isJoker ? 'bg-gray-700' : 'bg-surface-2'}`}>
                      <div className={`font-mono text-sm font-bold ${isBM || isJoker ? 'text-white' : 'text-text'}`}>
                        {m.cover_packages}
                      </div>
                      <div className={`text-xs font-semibold uppercase tracking-wide mt-1 ${isBM || isJoker ? 'text-gray-400' : 'text-text-3'}`}>
                        Paket
                      </div>
                    </div>
                    <div className={`text-center p-2 rounded ${isBM || isJoker ? 'bg-gray-700' : 'bg-surface-2'}`}>
                      <div className={`font-mono text-sm font-bold ${isBM || isJoker ? 'text-white' : 'text-text'}`}>
                        {Math.round(m.cover_hours)}sa
                      </div>
                      <div className={`text-xs font-semibold uppercase tracking-wide mt-1 ${isBM || isJoker ? 'text-gray-400' : 'text-text-3'}`}>
                        Çalışma
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ──── FILTERS & TOOLBAR ──── */}
      <div className="bg-white border border-border rounded-xl shadow-sm p-3.5 mb-4.5 sticky top-0 z-20 backdrop-blur-md bg-white/95">
        <div className="flex gap-2.5 items-center flex-wrap">
          {/* Status tabs */}
          <div className="flex gap-1 bg-bg-surface2 rounded-lg p-1">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setStatusTab(tab.key)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                  statusTab === tab.key
                    ? 'bg-brand text-white shadow-sm'
                    : 'text-text-2 hover:bg-white'
                }`}
              >
                {tab.label}
                <span className={`ml-1.5 px-1.5 py-px rounded-full text-xs font-semibold tabular-nums ${
                  statusTab === tab.key ? 'bg-white/25' : 'bg-white'
                }`}>
                  {counts[tab.key]}
                </span>
              </button>
            ))}
          </div>

          {/* Search */}
          <input
            type="search"
            placeholder="Ad, kod, telefon, plaka ile ara…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-border text-xs w-64 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
          />

          {/* Role filter pills */}
          <div className="flex gap-1 ml-auto">
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
                  className={`px-2 py-1 rounded-full text-xs font-medium transition ${
                    roleFilter === r.key
                      ? 'bg-brand text-white shadow-sm'
                      : 'bg-white border border-border text-text-2 hover:bg-brand-soft hover:text-brand'
                  }`}
                >
                  {r.label}
                  <span className={`ml-1 px-1 rounded-full text-xs font-semibold tabular-nums ${
                    roleFilter === r.key ? 'bg-white/25' : 'bg-bg-surface2'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Result count */}
          <span className="text-xs text-text-3 font-semibold uppercase tracking-wider">
            {filtered.length} sonuç
          </span>
        </div>
      </div>

      {/* ──── PERSONNEL CARDS GRID ──── */}
      {filtered.length === 0 ? (
        <div className="bg-white border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
          Sonuç bulunamadı.
        </div>
      ) : (
        <div className="grid gap-3.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {filtered.map((p) => {
            const initials = (p.full_name ?? '?')
              .split(' ')
              .filter(Boolean)
              .slice(0, 2)
              .map((w) => w[0]?.toUpperCase())
              .join('');
            const grad = AVATAR_COLORS[p.role as keyof typeof AVATAR_COLORS] || 'from-blue-700 to-blue-500';
            const heroGrad = HERO_COLORS[p.role as keyof typeof HERO_COLORS] || 'from-blue-100 to-blue-50';
            const veh = vehicleLabel(p);
            const isSelected = selectedIds.has(p.id);

            return (
              <div
                key={p.id}
                className={`bg-white border rounded-2xl overflow-hidden transition-all duration-300 cursor-pointer shadow-sm hover:shadow-lg relative group ${
                  isSelected ? 'border-brand shadow-md ring-3 ring-brand/20' : 'border-border hover:border-brand/50'
                }`}
              >
                {/* Multi-select checkbox */}
                <button
                  onClick={() => toggleSelect(p.id)}
                  className={`absolute top-3.5 right-3.5 w-5.5 h-5.5 rounded border-1.5 flex items-center justify-center z-10 transition opacity-0 group-hover:opacity-100 ${
                    isSelected
                      ? 'bg-brand border-brand'
                      : 'bg-white border-border hover:border-brand'
                  }`}
                >
                  {isSelected && <Check className="w-3.5 h-3.5 text-white" strokeWidth={3} />}
                </button>

                {/* Cover strip */}
                <div className={`h-12 ${heroGrad}`} />

                {/* Body */}
                <div className="p-4.5 pt-3">
                  {/* Avatar + quick edit button */}
                  <div className="flex items-start gap-3 mb-3">
                    <div
                      className={`w-14 h-14 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-lg flex-shrink-0 shadow-md`}
                    >
                      {initials}
                    </div>
                    <button
                      onClick={() => setEditingId(p.id)}
                      className="ml-auto text-text-3 hover:text-brand p-1.5 rounded-lg hover:bg-bg-surface2 transition"
                      title="Düzenle"
                    >
                      <Pencil className="w-4 h-4" strokeWidth={2.2} />
                    </button>
                  </div>

                  {/* Name & meta */}
                  <h4 className="font-display text-sm font-semibold tracking-tight mb-1.5">
                    {p.full_name || '—'}
                  </h4>
                  <div className="flex gap-2 items-center mb-2 flex-wrap">
                    <span className="font-mono text-xs text-text-3">
                      {p.person_code || '—'}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                      ROLE_STYLES[p.role ?? ''] || 'bg-bg-surface2 text-text-2'
                    }`}>
                      {p.role || '—'}
                    </span>
                  </div>

                  {/* Restaurant */}
                  {restName(p.assigned_restaurant_id) && (
                    <div className="text-xs text-text-2 mb-3 flex items-center gap-1">
                      <Utensils className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={2.2} />
                      {restName(p.assigned_restaurant_id)}
                    </div>
                  )}

                  {/* Stats */}
                  <div className="bg-cream-50 rounded-lg p-2.5 mb-3 border border-border">
                    <div className="grid grid-cols-3 gap-1.5 text-center text-xs">
                      <div>
                        <div className="font-mono font-bold text-text">—</div>
                        <div className="text-text-3 uppercase tracking-wide font-semibold mt-0.5">
                          Paket
                        </div>
                      </div>
                      <div>
                        <div className="font-mono font-bold text-text">—</div>
                        <div className="text-text-3 uppercase tracking-wide font-semibold mt-0.5">
                          Saat
                        </div>
                      </div>
                      <div>
                        <div className="font-mono font-bold text-text">—/—</div>
                        <div className="text-text-3 uppercase tracking-wide font-semibold mt-0.5">
                          Gün
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Vehicle badge */}
                  <span className={`inline-flex text-xs font-semibold px-2 py-1 rounded-lg ${veh.color}`}>
                    {veh.label}
                  </span>

                  {/* Status */}
                  {(p.status ?? 'Aktif') === 'Aktif' && (
                    <div className="absolute top-3.5 right-12 w-2.5 h-2.5 rounded-full bg-green-500 shadow-md" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ──── BULK ACTION BAR ──── */}
      {selectedIds.size > 0 && (
        <div
          className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-text text-white px-4.5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 z-40 transition-all duration-300"
          style={{
            transform: `translate(-50%, ${selectedIds.size > 0 ? '0' : '100px'})`,
          }}
        >
          <span className="bg-brand px-2.5 py-1 rounded-full font-bold text-sm">
            {selectedIds.size}
          </span>
          <span className="text-sm font-medium">personel seçildi</span>
          <div className="w-px h-5 bg-white/20" />
          <button className="text-sm font-medium hover:text-blue-200 transition">
            Toplu durum değiştir
          </button>
          <button className="text-sm font-medium hover:text-blue-200 transition">
            Toplu rol değiştir
          </button>
          <div className="w-px h-5 bg-white/20 ml-auto" />
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-sm font-medium hover:text-red-200 transition"
          >
            ✕ İptal
          </button>
        </div>
      )}

      {/* ──── EDIT MODAL ──── */}
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
