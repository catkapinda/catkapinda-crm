'use client';

import { useMemo, useState } from 'react';
import {
  AlertTriangle, ArrowDownToLine, Award, Bike, CheckCircle, Crown,
  Lightbulb, MoreVertical, Pencil, Plus, Search, Sparkles, Trophy,
  TrendingUp, Utensils, Zap, Check,
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
  Joker: 'bg-cream-100 text-terra',
  'Bölge Müdürü': 'bg-text text-white',
  Kaptan: 'bg-surface-3 text-text-2',
  'Restoran Takım Şefi': 'bg-cream-100 text-terra',
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
  'Restoran Takım Şefi': 'from-yellow-600 to-yellow-400',
};

const COVER_COLORS = {
  'Kurye': 'bg-gradient-to-br from-blue-100 to-blue-50',
  'Bölge Müdürü': 'bg-gradient-to-br from-slate-900 to-slate-800',
  'Joker': 'bg-gradient-to-br from-yellow-100 to-yellow-50',
  'Kaptan': 'bg-gradient-to-br from-yellow-50 to-slate-100',
  'Restoran Takım Şefi': 'bg-gradient-to-br from-blue-100 to-blue-200',
};

function tr(value: number | null | undefined, digits = 0): string {
  if (value == null || value === 0) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function vehicleLabel(p: Personnel): { label: string; color: string } {
  if (p.vehicle_type === 'Çat Kapında Satış' || p.motor_purchase === 'Evet') {
    return { label: 'ÇK Satış', color: 'bg-purple-50 text-purple-700' };
  }
  if (p.vehicle_type === 'Çat Kapında Kiralık' || p.motor_rental === 'Evet') {
    return { label: 'ÇK Kiralık', color: 'bg-orange-50 text-orange-700' };
  }
  if (p.vehicle_type === 'Kendi Motoru' || p.vehicle_type) {
    return { label: 'Kendi Motoru', color: 'bg-surface-2 text-text-2' };
  }
  return { label: '—', color: 'bg-surface-2 text-text-3' };
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
      <header className="flex justify-between items-start gap-5 mb-4.5">
        <div>
          <div className="text-xs text-text-3 font-semibold uppercase tracking-wider mb-1.5">
            Operasyon · <span className="text-brand">Personel</span>
          </div>
          <h1 className="font-display text-5xl font-semibold tracking-tighter leading-tight mb-1.5">
            Personel
          </h1>
          <div className="text-text-3 text-sm font-medium">
            {activeOnly.length} aktif personel · {restaurants.length} restoranada görev başında · Mart 2026 performansı
          </div>
        </div>
        <div className="flex gap-2">
          <button className="px-3.5 py-2 rounded-lg bg-white border border-border text-text-2 text-xs font-semibold shadow-xs hover:border-border-2 transition inline-flex items-center gap-1.5">
            <Pencil className="w-3.5 h-3.5" strokeWidth={2.2} /> Excel'e aktar
          </button>
          <button
            onClick={() => setCreating(true)}
            className="px-3.5 py-2 rounded-lg bg-brand text-white text-xs font-semibold shadow-sm hover:bg-blue-900 transition"
          >
            + Yeni Personel
          </button>
        </div>
      </header>

      {/* ──── HERO STRIP ──── */}
      <div className="bg-white border border-border rounded-2xl shadow-md flex overflow-hidden mb-4.5">
        {/* Cell 1: Toplam Aktif (Brand gradient) */}
        <div
          className="flex-1 flex flex-col justify-center p-5.5 border-r border-border relative overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, #0A3F8F, #0F52BA)',
            color: 'white',
          }}
        >
          <div className="flex justify-between items-start gap-3 mb-2.5">
            <div className="text-xs font-semibold uppercase tracking-wide opacity-85">Toplam Aktif</div>
            <div className="px-2 py-1 rounded-full bg-green-500/25 text-green-100 text-xs font-bold">
              ↑ %4.5
            </div>
          </div>
          <div className="text-5xl font-bold font-display tracking-tight mb-2">
            {heroMetrics.total}
          </div>
          <div className="text-sm opacity-90">
            <span className="font-bold">+4</span> son 30 günde · 11 pasif arşivde
          </div>
          <div className="mt-2.5 h-7 bg-white/10 rounded opacity-30" />
        </div>

        {/* Cell 2: Kurye */}
        <div className="flex-1 flex flex-col justify-center p-5.5 border-r border-border">
          <div className="flex justify-between items-start gap-3 mb-2.5">
            <div className="text-xs font-semibold uppercase tracking-wide text-text-3">Kurye</div>
            <div className="w-7 h-7 rounded-lg bg-brand-soft flex items-center justify-center text-brand text-sm flex-shrink-0">
              🛵
            </div>
          </div>
          <div className="text-5xl font-bold font-display tracking-tight mb-2">
            {heroMetrics.kurye}
          </div>
          <div className="w-full h-1 bg-surface-2 rounded-full overflow-hidden mb-1.5">
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
          <div className="flex justify-between items-start gap-3 mb-2.5">
            <div className="text-xs font-semibold uppercase tracking-wide text-text-3">Yönetim</div>
            <div className="w-7 h-7 rounded-lg bg-surface-3 flex items-center justify-center text-text-2 text-sm flex-shrink-0">
              👔
            </div>
          </div>
          <div className="text-5xl font-bold font-display tracking-tight mb-2">
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
          <div className="flex justify-between items-start gap-3 mb-2.5">
            <div className="text-xs font-semibold uppercase tracking-wide text-text-3">Joker</div>
            <div className="w-7 h-7 rounded-lg bg-cream-100 flex items-center justify-center text-terra text-sm flex-shrink-0">
              🃏
            </div>
          </div>
          <div className="text-5xl font-bold font-display tracking-tight mb-2">
            {heroMetrics.joker}
          </div>
          <div className="w-full h-1 bg-surface-2 rounded-full overflow-hidden mb-1.5">
            <div
              className="h-full transition-all duration-1200"
              style={{
                width: '47%',
                background: 'linear-gradient(90deg, #10B981, #34D399)',
              }}
            />
          </div>
          <div className="text-xs text-text-3">
            %47 geri kazanım · 176K ₺/ay sabit
          </div>
        </div>
      </div>

      {/* ──── AKILLI İÇGÖRÜ HERO ──── */}
      {insights && (
        <div
          className="rounded-3xl border border-border shadow-sm p-8 mb-4.5 relative overflow-hidden"
          style={{
            background: `radial-gradient(900px circle at 90% -10%, rgba(232,217,181,0.4), transparent 50%),
                        radial-gradient(700px circle at -10% 110%, rgba(15,82,186,0.08), transparent 55%),
                        linear-gradient(135deg, #FFFFFF 0%, #FAF6EE 100%)`,
          }}
        >
          <div className="absolute inset-0" style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, rgba(15, 82, 186, 0.06) 1px, transparent 0)`,
            backgroundSize: '24px 24px',
            maskImage: 'linear-gradient(135deg, transparent 40%, black 80%)',
            pointerEvents: 'none',
          }} />

          <div className="grid grid-cols-3 gap-9 relative z-10">
            {/* Content */}
            <div className="col-span-2">
              <div className="flex items-center gap-2 mb-3" style={{
                display: 'inline-flex',
                padding: '5px 11px',
                background: 'linear-gradient(135deg, #0F52BA, #4F6BFF)',
                color: 'white',
                fontSize: '11px',
                fontWeight: 700,
                borderRadius: '999px',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}>
                <Sparkles className="w-3.5 h-3.5" strokeWidth={2} />
                Akıllı İçgörü · Bu Hafta
              </div>
              <h2 className="font-display text-3xl font-semibold tracking-tight leading-snug text-text mb-3">
                3 kuryen <em style={{ fontStyle: 'normal', background: 'linear-gradient(135deg, #0F52BA, #3B7BCF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>390 paket eşiğini</em> aşmak üzere — ay sonuna kadar restorana ek <em style={{ fontStyle: 'normal', background: 'linear-gradient(135deg, #0F52BA, #3B7BCF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>84.000 ₺</em> fatura kesebilirsin.
              </h2>
              <p className="text-text-2 text-sm leading-relaxed mb-5">
                Köroğlu Pide'deki Oğuzhan Kır 462 pakette, Furkan Ton 450'de. Trendleri sürerse +%55 prim oranına geçecekler. Aynı zamanda Quick China Suadiye'de hedef kurye sayısı 6'ya karşılık 4'te kaldı.
              </p>
              <div className="flex gap-2">
                <button className="px-4 py-2.5 bg-text text-white text-xs font-semibold rounded-lg hover:shadow-lg transition">
                  Detaylı analiz
                </button>
                <button className="px-4 py-2.5 border border-border text-text-2 text-xs font-semibold rounded-lg hover:bg-surface-2 transition">
                  Eylem önerileri
                </button>
              </div>
            </div>

            {/* Insight cards */}
            <div className="grid grid-cols-2 gap-2.5">
              {[
                { icon: '↗', bg: 'bg-green-50', border: 'border-green-200', color: 'text-green-700', title: 'Eşik Aşımı', value: '3 kurye', meta: '<strong>%72</strong> ay sonuna kadar geçecek · <strong>+84K ₺</strong> ek fatura potansiyeli' },
                { icon: '⚠', bg: 'bg-yellow-50', border: 'border-yellow-200', color: 'text-yellow-700', title: 'Eksik Kapasite', value: '2 restoran', meta: 'Quick China Suadiye <strong>4/6</strong> · Köroğlu <strong>5/8</strong> · acil işe alım' },
                { icon: '⚡', bg: 'bg-brand-soft', border: 'border-brand-border', color: 'text-brand', title: 'Verimlilik Liderleri', value: 'Cihan + Selim', meta: 'Sabit maaşlarının <strong>%52</strong>'sini cover yaparak geri kazandılar' },
                { icon: '📋', bg: 'bg-cream-100', border: 'border-cream-300', color: 'text-terra', title: 'Bekleyen Aksiyonlar', value: '7 talep', meta: '3 avans · 2 motor değişikliği · 2 muhasebe geçişi onay bekliyor' },
              ].map((item, i) => (
                <div
                  key={i}
                  className={`${item.bg} border ${item.border} rounded-2xl p-4 cursor-pointer hover:shadow-sm transition relative`}
                  style={{ borderColor: item.border === 'border-green-200' ? 'rgba(16,185,129,0.3)' : item.border === 'border-yellow-200' ? 'rgba(245,158,11,0.3)' : item.border === 'border-brand-border' ? 'var(--brand-border)' : 'var(--cream-300)' }}
                >
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center mb-2 text-lg`} style={{ background: item.bg, color: item.color }}>
                    {item.icon}
                  </div>
                  <div className={`text-xs font-semibold uppercase tracking-wider text-text-3 mb-1`}>
                    {item.title}
                  </div>
                  <div className="font-display text-lg font-semibold text-text leading-tight mb-1">
                    {item.value}
                  </div>
                  <div className="text-xs text-text-2 leading-snug" dangerouslySetInnerHTML={{ __html: item.meta }} />
                </div>
              ))}
            </div>
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
            <span className="text-brand text-xs font-semibold cursor-pointer">Hepsini gör →</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3.5">
            {management.slice(0, 4).map((m) => {
              const isBM = m.role?.includes('Bölge');
              const isJoker = m.role?.includes('Joker');
              const coverPercent = m.salary > 0 ? Math.min(100, (m.cover_hours * 200 + m.cover_packages * 25) / m.salary * 100) : 0;
              const recoveryAmount = m.cover_hours * 200 + m.cover_packages * 25;

              return (
                <div
                  key={m.id}
                  className="border border-border rounded-3xl overflow-hidden shadow-sm hover:shadow-lg transition relative"
                  style={{
                    background: `linear-gradient(180deg, ${isBM ? '#1F2937' : isJoker ? '#FEF9E7' : '#FFFFFF'} 0%, ${isBM ? '#111827' : isJoker ? '#FEF3C7' : '#FDFAF3'} 100%)`,
                    borderTopColor: isBM ? '#6B7280' : isJoker ? '#FBBF24' : '#3B7BCF',
                    borderTopWidth: '3px',
                  }}
                >
                  <div className="p-4.5">
                    <div className="flex items-center gap-2.5 mb-3">
                      <div
                        className="w-10 h-10 rounded-full text-white font-bold flex items-center justify-center text-xs flex-shrink-0"
                        style={{
                          background: isBM ? 'linear-gradient(135deg, #0A3F8F, #1B4FAB)' : 'linear-gradient(135deg, #C9AE7A, #E8D9B5)',
                          color: isJoker ? '#8B7355' : 'white',
                        }}
                      >
                        {(m.full_name ?? '?').split(' ').map(w => w[0]).join('').substring(0, 2)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className={`text-sm font-bold ${isBM || isJoker ? (isBM ? 'text-white' : 'text-text') : 'text-text'}`}>
                          {m.full_name || '—'}
                        </div>
                        <div className={`text-xs mt-0.5 ${isBM || isJoker ? (isBM ? 'text-gray-300' : 'text-text-3') : 'text-text-3'}`}>
                          <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${
                            isBM ? 'bg-blue-900 text-white' : isJoker ? 'bg-yellow-200 text-text' : 'bg-brand-soft text-brand'
                          }`}>
                            {isBM ? 'BM' : isJoker ? 'Joker' : 'Kaptan'}
                          </span>
                        </div>
                      </div>
                      <div className={`text-right text-xs leading-tight ${isBM || isJoker ? (isBM ? 'text-green-300' : 'text-terra') : 'text-success'}`}>
                        <div className="font-bold">↑ %14</div>
                        <div className={isBM || isJoker ? (isBM ? 'text-gray-400' : 'text-text-3') : 'text-text-3'}>vs Şubat</div>
                      </div>
                    </div>

                    {/* Battery */}
                    <div className="mb-2.5">
                      <div className="flex-1 h-7 rounded-lg overflow-hidden mb-1" style={{
                        background: isBM || isJoker ? 'rgba(255,255,255,0.15)' : '#F4EFE3',
                      }}>
                        <div
                          className="h-full flex items-center justify-end pr-2 transition-all duration-1400"
                          style={{
                            width: `${coverPercent}%`,
                            background: isJoker ? 'linear-gradient(90deg, #B45309, #D97706)' : 'linear-gradient(90deg, #10B981, #34D399)',
                          }}
                        >
                          <span className={`text-xs font-bold ${isJoker ? 'text-text' : 'text-white'}`}>
                            −%{Math.round(coverPercent)}
                          </span>
                        </div>
                      </div>
                      <div className="flex justify-between text-xs" style={{
                        color: isBM || isJoker ? '#9CA3AF' : '#8B92A7',
                        fontFamily: 'JetBrains Mono, monospace',
                      }}>
                        <span>0 ₺</span>
                        <span>{tr(m.salary / 1000)}K ₺</span>
                      </div>
                    </div>

                    {/* Summary */}
                    <div className={`py-2.5 border-b border-t ${isBM || isJoker ? (isBM ? 'border-gray-700 border-gray-600' : 'border-cream-300') : 'border-border'} mb-2.5`}>
                      <div className={`flex justify-between text-xs mb-1.5 ${isBM || isJoker ? (isBM ? 'text-gray-300' : 'text-text-2') : 'text-text-2'}`}>
                        <span>Sabit maaş</span>
                        <span className={`font-semibold font-mono ${isBM || isJoker ? (isBM ? 'text-gray-200' : 'text-text') : 'text-text'}`}>{tr(m.salary)}</span>
                      </div>
                      <div className={`flex justify-between text-xs ${isJoker ? 'text-terra' : 'text-success'}`}>
                        <span>Cover ile geri kazanım</span>
                        <span className="font-bold font-mono">+{tr(recoveryAmount)}</span>
                      </div>
                      <div className={`flex justify-between text-xs font-bold mt-1.5 pt-1 border-t ${isBM || isJoker ? (isBM ? 'border-gray-600 text-blue-200' : 'border-cream-200 text-text') : 'border-dashed border-border text-brand'}`}>
                        <span>Net maliyet</span>
                        <span className="font-mono">{tr(Math.max(0, m.salary - recoveryAmount))}</span>
                      </div>
                    </div>

                    {/* Mini bars */}
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { val: m.cover_days, lbl: 'Cover' },
                        { val: m.cover_packages, lbl: 'Paket' },
                        { val: Math.round(m.cover_hours), lbl: 'Çalışma', suffix: 'sa' },
                      ].map((stat, i) => (
                        <div key={i} className={`text-center p-2 rounded ${isBM || isJoker ? (isBM ? 'bg-gray-700' : 'bg-cream-100') : 'bg-surface-2'}`}>
                          <div className={`font-mono text-sm font-bold ${isBM || isJoker ? (isBM ? 'text-white' : 'text-text') : 'text-text'}`}>
                            {stat.val}{stat.suffix || ''}
                          </div>
                          <div className={`text-xs font-semibold uppercase tracking-wide mt-1 ${isBM || isJoker ? (isBM ? 'text-gray-400' : 'text-text-3') : 'text-text-3'}`}>
                            {stat.lbl}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ──── TOP PERFORMERS PODIUM (MART ŞAMPİYONLARI) ──── */}
      {topPerformers.length > 0 && (
        <div className="mb-4.5">
          <div className="flex items-baseline justify-between mb-3">
            <div>
              <h3 className="font-display text-lg font-semibold inline-flex items-center gap-2">
                🏆 Mart Şampiyonları
              </h3>
              <span className="text-text-3 text-xs ml-2 font-medium">
                paket sayısına göre
              </span>
            </div>
            <span className="text-brand text-xs font-semibold cursor-pointer">Tüm sıralama →</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            {topPerformers.map((p, idx) => {
              const medals = ['🥇', '🥈', '🥉'];
              const borderStyle = idx === 0 ? { borderColor: '#0F52BA', borderWidth: '1.5px' } : { borderColor: 'var(--border)', borderWidth: '1px' };
              const shadowStyle = idx === 0 ? 'shadow-lg' : 'shadow-md';

              return (
                <div
                  key={p.id}
                  className={`bg-white rounded-2xl p-5 ${shadowStyle} relative overflow-hidden border cursor-pointer hover:shadow-2xl transition`}
                  style={borderStyle}
                >
                  <div
                    className="absolute top-2 right-3 text-6xl font-bold leading-none"
                    style={{ color: idx === 0 ? 'rgba(15,82,186,0.12)' : 'rgba(15,82,186,0.08)', fontSize: idx === 0 ? '78px' : '56px' }}
                  >
                    {idx + 1}
                  </div>
                  <div className="absolute top-4 left-4 text-2xl">{medals[idx]}</div>

                  <div className="relative z-10 pt-6">
                    <div
                      className="w-14 h-14 rounded-full text-white font-bold flex items-center justify-center text-lg mb-3 shadow-md"
                      style={{
                        background: idx === 0 ? 'linear-gradient(135deg, #0F52BA, #3B7BCF)' :
                                   idx === 1 ? 'linear-gradient(135deg, #0A3F8F, #1B4FAB)' :
                                   'linear-gradient(135deg, #C9AE7A, #E8D9B5)',
                        color: idx === 2 ? '#333' : 'white',
                      }}
                    >
                      {(p.full_name ?? '?').split(' ').map(w => w[0]).join('').substring(0, 2)}
                    </div>

                    <h4 className="font-display text-base font-semibold tracking-tight text-text">
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


      {/* ──── FILTERS & TOOLBAR (STICKY) ──── */}
      <div className="bg-white border border-border rounded-2xl shadow-sm p-3.5 mb-4.5 sticky top-0 z-20 backdrop-blur-md bg-white/95">
        <div className="flex gap-2.5 items-center flex-wrap">
          {/* Search with icon */}
          <div className="flex items-center gap-2 px-3.5 py-2 rounded-lg border border-border bg-white text-xs">
            <Search className="w-3.5 h-3.5 text-text-3 flex-shrink-0" strokeWidth={2} />
            <input
              type="search"
              placeholder="Ad, kod, telefon, plaka ile ara…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 bg-transparent outline-none text-text"
            />
          </div>

          {/* Status tabs */}
          <div className="flex gap-1 bg-surface-2 rounded-lg p-1">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setStatusTab(tab.key)}
                className={`px-3 py-1.5 rounded text-xs font-semibold transition ${
                  statusTab === tab.key
                    ? 'bg-brand text-white shadow-sm'
                    : 'text-text-2 hover:bg-white'
                }`}
              >
                {tab.label}
                <span className={`ml-1.5 px-1.5 rounded-full text-xs font-semibold tabular-nums ${
                  statusTab === tab.key ? 'bg-white/22' : 'bg-white'
                }`}>
                  {counts[tab.key]}
                </span>
              </button>
            ))}
          </div>

          {/* Role filters */}
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
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                    roleFilter === r.key
                      ? 'bg-brand text-white shadow-sm'
                      : 'bg-white border border-border text-text-2 hover:bg-brand-soft hover:text-brand'
                  }`}
                >
                  {r.label}
                  <span className={`ml-1 px-1 rounded-full text-xs font-semibold tabular-nums ${
                    roleFilter === r.key ? 'bg-white/22' : 'bg-surface-2'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Result count */}
          <span className="text-xs text-text-3 font-semibold uppercase tracking-wider whitespace-nowrap">
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
        <>
          <div className="grid gap-3.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
            {filtered.map((p) => {
              const initials = (p.full_name ?? '?')
                .split(' ')
                .filter(Boolean)
                .slice(0, 2)
                .map((w) => w[0]?.toUpperCase())
                .join('');
              const grad = AVATAR_COLORS[p.role as keyof typeof AVATAR_COLORS] || 'from-blue-700 to-blue-500';
              const coverColor = COVER_COLORS[p.role as keyof typeof COVER_COLORS] || 'bg-gradient-to-br from-blue-100 to-blue-50';
              const veh = vehicleLabel(p);
              const isSelected = selectedIds.has(p.id);

              return (
                <div
                  key={p.id}
                  onClick={() => toggleSelect(p.id)}
                  className={`bg-white border rounded-2xl overflow-hidden transition-all duration-300 cursor-pointer shadow-sm hover:shadow-lg relative group ${
                    isSelected ? 'border-brand shadow-md ring-3 ring-brand/20' : 'border-border hover:border-brand/50'
                  }`}
                >
                  {/* Multi-select checkbox */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSelect(p.id);
                    }}
                    className={`absolute top-3.5 right-3.5 w-5.5 h-5.5 rounded border-1.5 flex items-center justify-center z-10 transition opacity-0 group-hover:opacity-100 ${
                      isSelected
                        ? 'bg-brand border-brand'
                        : 'bg-white border-border hover:border-brand'
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5 text-white" strokeWidth={3} />}
                  </button>

                  {/* Cover strip (h-12) */}
                  <div className={`h-12 ${coverColor}`} />

                  {/* Status dot */}
                  {(p.status ?? 'Aktif') === 'Aktif' && (
                    <div className="absolute top-12 right-3.5 w-2.5 h-2.5 rounded-full bg-green-500 shadow-md border-2 border-white" style={{ transform: 'translateY(-50%)' }} />
                  )}

                  {/* Body */}
                  <div className="p-4.5">
                    {/* Avatar */}
                    <div
                      className={`w-14 h-14 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-lg mb-3 shadow-md border-3 border-white`}
                      style={{ marginTop: '-28px', position: 'relative', zIndex: 5 }}
                    >
                      {initials}
                    </div>

                    {/* Name */}
                    <h4 className="font-display text-base font-semibold tracking-tight text-text mb-1">
                      {p.full_name || '—'}
                    </h4>

                    {/* Code + role pills */}
                    <div className="flex gap-1.5 items-center mb-2 flex-wrap">
                      <span className="font-mono text-xs text-text-3">
                        {p.person_code || '—'}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                        ROLE_STYLES[p.role ?? ''] || 'bg-surface-2 text-text-2'
                      }`}>
                        {p.role || '—'}
                      </span>
                    </div>

                    {/* Status pill */}
                    {(p.status ?? 'Aktif') === 'Aktif' && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-green-50 text-green-600 text-xs font-semibold rounded-full border border-green-200 mb-2">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                        Aktif
                      </span>
                    )}

                    {/* Restaurant */}
                    {restName(p.assigned_restaurant_id) && (
                      <div className="text-xs text-text-2 mb-3 flex items-center gap-1.5">
                        <Utensils className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={2} />
                        {restName(p.assigned_restaurant_id)}
                      </div>
                    )}

                    {/* Stats (placeholder) */}
                    <div className="bg-cream-50 rounded-lg p-2 mb-2.5 border border-border">
                      <div className="grid grid-cols-3 gap-1 text-center text-xs">
                        <div>
                          <div className="font-mono font-bold text-text">—</div>
                          <div className="text-text-3 uppercase tracking-wide font-semibold mt-0.5 text-xs">Paket</div>
                        </div>
                        <div>
                          <div className="font-mono font-bold text-text">—</div>
                          <div className="text-text-3 uppercase tracking-wide font-semibold mt-0.5 text-xs">Saat</div>
                        </div>
                        <div>
                          <div className="font-mono font-bold text-text">—/—</div>
                          <div className="text-text-3 uppercase tracking-wide font-semibold mt-0.5 text-xs">Gün</div>
                        </div>
                      </div>
                    </div>

                    {/* Vehicle badge */}
                    <span className={`inline-flex text-xs font-semibold px-2 py-1 rounded-lg ${veh.color}`}>
                      {veh.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Load more button */}
          <div className="text-center py-6">
            <button className="px-3.5 py-2 bg-white border border-border text-text-2 text-xs font-semibold rounded-lg hover:border-border-2 transition">
              ↓ Daha fazla yükle (84 personel daha)
            </button>
          </div>
        </>
      )}

      {/* ──── BULK ACTION BAR (FLOATING) ──── */}
      {selectedIds.size > 0 && (
        <div
          className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-text text-white px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-4 z-40 transition-all duration-300"
          style={{
            transform: `translate(-50%, ${selectedIds.size > 0 ? '0' : '100px'})`,
          }}
        >
          <span className="bg-brand px-2.5 py-1 rounded-full font-bold text-xs">
            {selectedIds.size}
          </span>
          <span className="text-xs font-medium">personel seçildi</span>
          <div className="w-px h-5 bg-white/20" />
          <button className="text-xs font-semibold hover:text-blue-200 transition">
            📤 Excel'e aktar
          </button>
          <button className="text-xs font-semibold hover:text-blue-200 transition">
            🔄 Restoran değiştir
          </button>
          <button className="text-xs font-semibold hover:text-blue-200 transition">
            📅 Toplu puantaj
          </button>
          <button className="text-xs font-semibold hover:text-blue-200 transition">
            💰 Toplu avans
          </button>
          <div className="w-px h-5 bg-white/20 ml-auto" />
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-xs font-semibold hover:text-red-200 transition"
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
