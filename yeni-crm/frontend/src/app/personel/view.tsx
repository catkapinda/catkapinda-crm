'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertTriangle, ArrowDown, ArrowDownToLine, ArrowUp, ArrowUpRight, Award,
  Bike, Calendar, Check, ChevronRight, Inbox, LayoutGrid, List, Pencil, Phone,
  Plus, Search, ShieldCheck, Sparkles, Target, TrendingUp, Users,
  Utensils, Zap,
  type LucideIcon,
} from 'lucide-react';

import { PersonnelEditModal } from '@/components/personnel-edit-modal';
import type {
  AiInsightsResponse,
  ManagementMember,
  PageInsights,
  Personnel,
  PersonnelStats,
  Restaurant,
  TopPerformer,
} from '@/lib/api';
import { getAiInsights } from '@/lib/api';

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

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function periodToLabel(period: string, withYear = true): string {
  const [y, m] = period.split('-').map(Number);
  if (!y || !m) return period;
  return withYear ? `${TR_MONTHS[m - 1]} ${y}` : TR_MONTHS[m - 1];
}

function periodMaxDaysOf(period: string): number {
  const [y, m] = period.split('-').map(Number);
  if (!y || !m) return 30;
  return new Date(y, m, 0).getDate();
}

function recentPeriodOptions(count = 6): { value: string; label: string }[] {
  const now = new Date();
  const out: { value: string; label: string }[] = [];
  for (let i = 0; i < count; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    out.push({ value, label: `${TR_MONTHS[d.getMonth()]} ${d.getFullYear()}` });
  }
  return out;
}

export function PersonnelView({
  personnel,
  restaurants,
  topPerformers = [],
  management = [],
  insights = null,
  stats = [],
  period = '2026-03',
  aiInsights = null,
}: {
  personnel: Personnel[];
  restaurants: Restaurant[];
  topPerformers?: TopPerformer[];
  management?: ManagementMember[];
  insights?: PageInsights | null;
  stats?: PersonnelStats[];
  period?: string;
  aiInsights?: AiInsightsResponse | null;
}) {
  const router = useRouter();

  // Personel id → aylık stats eşlemesi (kart bazlı paket/saat/gün için)
  const statsMap = useMemo(() => {
    const m = new Map<number, PersonnelStats>();
    for (const s of stats) m.set(s.personnel_id, s);
    return m;
  }, [stats]);

  // Period'a göre dinamik
  const periodLabel = useMemo(() => periodToLabel(period), [period]);
  const periodLabelShort = useMemo(() => periodToLabel(period, false), [period]);
  const periodMaxDays = useMemo(() => periodMaxDaysOf(period), [period]);
  const periodOptions = useMemo(() => recentPeriodOptions(6), []);
  const [periodPickerOpen, setPeriodPickerOpen] = useState(false);

  function changePeriod(next: string) {
    setPeriodPickerOpen(false);
    if (next === period) return;
    router.push(`/personel?period=${next}`);
  }
  const [statusTab, setStatusTab] = useState<'Aktif' | 'Pasif' | 'Kara Liste'>('Aktif');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [sortKey, setSortKey] = useState<'name' | 'code' | 'packages' | 'hours' | 'days'>('name');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

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

    // Sort
    const dir = sortDir === 'asc' ? 1 : -1;
    list = [...list].sort((a, b) => {
      const sa = statsMap.get(a.id);
      const sb = statsMap.get(b.id);
      switch (sortKey) {
        case 'code':
          return (a.person_code ?? '').localeCompare(b.person_code ?? '', 'tr-TR') * dir;
        case 'packages':
          return ((sa?.total_packages ?? 0) - (sb?.total_packages ?? 0)) * dir;
        case 'hours':
          return ((sa?.total_hours ?? 0) - (sb?.total_hours ?? 0)) * dir;
        case 'days':
          return ((sa?.working_days ?? 0) - (sb?.working_days ?? 0)) * dir;
        case 'name':
        default:
          return (a.full_name ?? '').localeCompare(b.full_name ?? '', 'tr-TR') * dir;
      }
    });
    return list;
  }, [personnel, statusTab, roleFilter, search, sortKey, sortDir, statsMap]);

  const activeOnly = useMemo(() => {
    return personnel.filter((p) => (p.status ?? 'Aktif') === 'Aktif');
  }, [personnel]);

  const heroMetrics = useMemo(() => {
    const total = activeOnly.length;
    const kurye = activeOnly.filter((p) => p.role === 'Kurye').length;
    const joker = activeOnly.filter((p) => p.role === 'Joker').length;
    const bm = activeOnly.filter((p) => p.role === 'Bölge Müdürü').length;
    const kaptan = activeOnly.filter((p) => p.role === 'Kaptan').length;
    const sef = activeOnly.filter((p) => p.role === 'Restoran Takım Şefi').length;
    const yonetim = bm + kaptan + sef;
    const pasif = personnel.length - total;
    return { total, kurye, joker, yonetim, bm, kaptan, sef, pasif };
  }, [activeOnly, personnel]);

  // Joker recovery — sabit maaş cover'lığını insights'tan al
  const jokerRecovery = useMemo(() => {
    const jokers = (insights?.top_recovery ?? []).filter((m) => m.role === 'Joker');
    if (jokers.length === 0) return { pct: 0, totalSalary: 0 };
    let totalSalary = 0;
    let totalCover = 0;
    for (const m of jokers) {
      totalSalary += m.salary;
      totalCover += m.cover_hours * 200 + m.cover_packages * 25;
    }
    const pct = totalSalary > 0 ? Math.min(100, Math.round((totalCover / totalSalary) * 100)) : 0;
    return { pct, totalSalary };
  }, [insights]);

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
            {activeOnly.length} aktif personel · {restaurants.length} restoranada görev başında · {periodLabel} performansı
          </div>
        </div>
        <div className="flex gap-2 items-start">
          {/* Period selector — premium dropdown */}
          <div className="relative">
            <button
              onClick={() => setPeriodPickerOpen((v) => !v)}
              className="px-3.5 py-2 rounded-lg bg-white border border-border text-text-2 text-xs font-semibold shadow-xs hover:border-brand/40 transition inline-flex items-center gap-2"
            >
              <Calendar className="w-3.5 h-3.5 text-brand" strokeWidth={2.2} />
              <span className="text-text">{periodLabel}</span>
              <ArrowDown className={`w-3 h-3 text-text-3 transition-transform ${periodPickerOpen ? 'rotate-180' : ''}`} strokeWidth={2.4} />
            </button>
            {periodPickerOpen && (
              <>
                {/* Click-outside backdrop */}
                <div
                  className="fixed inset-0 z-30"
                  onClick={() => setPeriodPickerOpen(false)}
                />
                <div className="absolute right-0 mt-1.5 z-40 w-48 bg-white border border-border rounded-xl shadow-xl overflow-hidden animate-hero-fade-in">
                  <div className="px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-text-3 border-b border-border/60">
                    Dönem seç
                  </div>
                  {periodOptions.map((opt) => {
                    const active = opt.value === period;
                    return (
                      <button
                        key={opt.value}
                        onClick={() => changePeriod(opt.value)}
                        className={`w-full text-left px-3 py-2 text-xs font-semibold flex items-center justify-between transition ${
                          active
                            ? 'bg-brand-soft text-brand'
                            : 'text-text-2 hover:bg-surface-2'
                        }`}
                      >
                        <span>{opt.label}</span>
                        {active && <Check className="w-3.5 h-3.5" strokeWidth={3} />}
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>
          <button className="px-3.5 py-2 rounded-lg bg-white border border-border text-text-2 text-xs font-semibold shadow-xs hover:border-border-2 transition inline-flex items-center gap-1.5">
            <ArrowDownToLine className="w-3.5 h-3.5" strokeWidth={2.2} /> Excel'e aktar
          </button>
          <button
            onClick={() => setCreating(true)}
            className="px-3.5 py-2 rounded-lg bg-brand text-white text-xs font-semibold shadow-sm hover:bg-blue-900 transition inline-flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" strokeWidth={2.4} /> Yeni Personel
          </button>
        </div>
      </header>

      {/* ──── KPI HERO — premium 4 kart ──── */}
      <div className="grid grid-cols-4 gap-3.5 mb-5">
        {/* 1. Toplam Aktif — primary mavi gradient */}
        <KpiHeroCard
          variant="brand"
          Icon={Users}
          label="Toplam Aktif"
          value={heroMetrics.total}
          sub={
            heroMetrics.pasif > 0
              ? `${heroMetrics.pasif} pasif arşivde`
              : 'tüm kayıtlar aktif'
          }
          subBold={`${heroMetrics.total} kişi`}
          progress={100}
        />

        {/* 2. Kurye — saha ekibi ana kütle */}
        <KpiHeroCard
          variant="blue"
          Icon={Bike}
          label="Kurye"
          value={heroMetrics.kurye}
          sub={`ekibin %${heroMetrics.total > 0 ? Math.round((heroMetrics.kurye / heroMetrics.total) * 100) : 0}'i sahada`}
          progress={heroMetrics.total > 0 ? (heroMetrics.kurye / heroMetrics.total) * 100 : 0}
        />

        {/* 3. Yönetim — BM + Kaptan + Şef gerçek dağılım */}
        <KpiHeroCard
          variant="slate"
          Icon={ShieldCheck}
          label="Yönetim"
          value={heroMetrics.yonetim}
          sub={
            <>
              {heroMetrics.bm > 0 && <><strong>{heroMetrics.bm}</strong> BM</>}
              {heroMetrics.bm > 0 && (heroMetrics.kaptan > 0 || heroMetrics.sef > 0) && ' · '}
              {heroMetrics.kaptan > 0 && <><strong>{heroMetrics.kaptan}</strong> Kaptan</>}
              {heroMetrics.kaptan > 0 && heroMetrics.sef > 0 && ' · '}
              {heroMetrics.sef > 0 && <><strong>{heroMetrics.sef}</strong> Şef</>}
              {heroMetrics.yonetim === 0 && <>operasyondan sorumlu kayıt yok</>}
            </>
          }
          progress={heroMetrics.total > 0 ? (heroMetrics.yonetim / heroMetrics.total) * 100 : 0}
        />

        {/* 4. Joker — sabit maaş cover oranı */}
        <KpiHeroCard
          variant="amber"
          Icon={Sparkles}
          label="Joker"
          value={heroMetrics.joker}
          sub={
            jokerRecovery.totalSalary > 0
              ? <><strong>%{jokerRecovery.pct}</strong> sabit maaş cover oranı</>
              : <>esnek atama · havuz</>
          }
          progress={jokerRecovery.pct}
        />
      </div>

      {/* ──── AKILLI İÇGÖRÜ HERO — gerçek veriye bağlı dinamik anlatım ──── */}
      {insights && (
        <SmartInsightsHero
          insights={insights}
          aiInsights={aiInsights}
          period={period}
        />
      )}

      {/* ──── BÖLGE MÜDÜRÜ & JOKER MAAŞLARI — sadece bizim cebimizden ödenen sabit maaşlılar ──── */}
      {management.length > 0 && (() => {
        // Sadece BM ve Joker — Kaptan ve RTŞ ayrı kategoriler:
        // - Kaptan: aslında Kurye, +3000₺ unvan farkı (ana kurye listesinde sayılır)
        // - RTŞ: maaşı restoran tarafından karşılanır (Quick China'ya faturalı)
        const bmJoker = management.filter((m) =>
          m.role === 'Bölge Müdürü' || m.role === 'Joker'
        );
        const rts = management.filter((m) => m.role === 'Restoran Takım Şefi');

        const toplamSabitMaas = bmJoker.reduce((s, m) => s + (m.salary || 0), 0);
        const toplamCover = bmJoker.reduce(
          (s, m) => s + (m.cover_hours * 200 + m.cover_packages * 25),
          0,
        );
        const aktifRestoran = restaurants.filter((r) => r.active !== 0).length;
        const restoranBasiMaliyet = aktifRestoran > 0 ? toplamSabitMaas / aktifRestoran : 0;
        const netPozisyon = toplamCover - toplamSabitMaas;
        const coverPct = toplamSabitMaas > 0
          ? Math.min(100, Math.round((toplamCover / toplamSabitMaas) * 100))
          : 0;

        return (
          <div className="mb-5">
            {/* Header */}
            <div className="flex items-baseline justify-between mb-3">
              <div>
                <h3 className="font-display text-lg font-semibold inline-flex items-center gap-2">
                  <Zap className="w-5 h-5 text-brand" strokeWidth={2.2} />
                  Bölge Müdürü & Joker Maaşları
                </h3>
                <span className="text-text-3 text-[12.5px] ml-2 font-medium">
                  sabit maaşlı · bizim cebimizden · saha cover ile geri kazanım
                </span>
              </div>
            </div>

            {/* Özet — operasyonel maliyet özeti */}
            <div className="grid grid-cols-4 gap-3 mb-4">
              <SummaryCard
                tone="rose"
                label="Toplam Sabit Maaş"
                value={`${formatTL(toplamSabitMaas)} ₺`}
                sub={`${bmJoker.length} kişi (${bmJoker.filter(m => m.role === 'Bölge Müdürü').length} BM · ${bmJoker.filter(m => m.role === 'Joker').length} Joker)`}
              />
              <SummaryCard
                tone="blue"
                label="Restoran Başı Maliyet"
                value={`${formatTL(restoranBasiMaliyet)} ₺`}
                sub={`${aktifRestoran} aktif restorana bölündü`}
              />
              <SummaryCard
                tone="emerald"
                label="Saha Cover Geri Kazanım"
                value={`${formatTL(toplamCover)} ₺`}
                sub={`maaşların %${coverPct}'i geri kazanıldı`}
              />
              <SummaryCard
                tone={netPozisyon >= 0 ? 'emerald' : 'amber'}
                label={netPozisyon >= 0 ? 'Net Kar' : 'Net Maliyet (kayıp)'}
                value={`${netPozisyon >= 0 ? '+' : '−'}${formatTL(Math.abs(netPozisyon))} ₺`}
                sub={netPozisyon >= 0 ? 'cover, maaşı geçti' : 'maaş > cover · ek paket motivasyonu gerekli'}
              />
            </div>

            {/* Kart listesi — premium yeni nesil tasarım */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
              {bmJoker.slice(0, 4).map((m) => (
                <ManagementCard
                  key={m.id}
                  member={m}
                  onEdit={() => setEditingId(m.id)}
                />
              ))}
            </div>

            {/* RTŞ — Recep'in attığı paketler şirkete ek kar (restoran maliyetiyle ilgisi yok) */}
            {rts.length > 0 && <RTSSection rts={rts} restMap={restMap} />}
          </div>
        );
      })()}

      {/* ──── TOP PERFORMERS PODIUM (MART ŞAMPİYONLARI) ──── */}
      {topPerformers.length > 0 && (
        <div className="mb-4.5">
          <div className="flex items-baseline justify-between mb-3">
            <div>
              <h3 className="font-display text-lg font-semibold inline-flex items-center gap-2">
                🏆 {periodLabelShort} Şampiyonları
              </h3>
              <span className="text-text-3 text-xs ml-2 font-medium">
                paket sayısına göre
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                setSortKey('packages');
                setSortDir('desc');
                setViewMode('list');
                setRoleFilter('Kurye');
                setStatusTab('Aktif');
                setTimeout(() => {
                  document.getElementById('personnel-list')?.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start',
                  });
                }, 60);
              }}
              className="text-brand text-xs font-semibold inline-flex items-center gap-1 hover:gap-1.5 hover:text-brand-dark transition-all"
            >
              Tüm sıralama
              <ArrowUpRight className="w-3.5 h-3.5" strokeWidth={2.4} />
            </button>
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

        {/* Second row: sort + view toggle */}
        <div className="flex gap-2.5 items-center mt-2.5 pt-2.5 border-t border-border/60">
          <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider">
            Sırala
          </span>
          <div className="flex gap-1">
            {([
              { key: 'name', label: 'Ad' },
              { key: 'code', label: 'Kod' },
              { key: 'packages', label: 'Paket' },
              { key: 'hours', label: 'Saat' },
              { key: 'days', label: 'Gün' },
            ] as const).map((s) => {
              const active = sortKey === s.key;
              return (
                <button
                  key={s.key}
                  onClick={() => {
                    if (active) {
                      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
                    } else {
                      setSortKey(s.key);
                      setSortDir(s.key === 'name' || s.key === 'code' ? 'asc' : 'desc');
                    }
                  }}
                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold transition ${
                    active
                      ? 'bg-text text-white shadow-sm'
                      : 'bg-white border border-border text-text-2 hover:border-text/30'
                  }`}
                >
                  {s.label}
                  {active && (sortDir === 'asc'
                    ? <ArrowUp className="w-3 h-3" strokeWidth={2.5} />
                    : <ArrowDown className="w-3 h-3" strokeWidth={2.5} />)}
                </button>
              );
            })}
          </div>

          <div className="ml-auto flex items-center gap-1 bg-surface-2 rounded-lg p-1">
            <button
              onClick={() => setViewMode('list')}
              aria-label="Liste görünümü"
              title="Liste görünümü"
              className={`p-1.5 rounded transition ${
                viewMode === 'list'
                  ? 'bg-white shadow-sm text-brand'
                  : 'text-text-3 hover:text-text-2'
              }`}
            >
              <List className="w-4 h-4" strokeWidth={2.2} />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              aria-label="Kart görünümü"
              title="Kart görünümü"
              className={`p-1.5 rounded transition ${
                viewMode === 'grid'
                  ? 'bg-white shadow-sm text-brand'
                  : 'text-text-3 hover:text-text-2'
              }`}
            >
              <LayoutGrid className="w-4 h-4" strokeWidth={2.2} />
            </button>
          </div>
        </div>
      </div>

      {/* ──── PERSONNEL LIST / GRID ──── */}
      {filtered.length === 0 ? (
        <div className="bg-white border border-border rounded-2xl p-8 text-center text-text-3 text-sm">
          Sonuç bulunamadı.
        </div>
      ) : viewMode === 'list' ? (
        <>
          {/* Premium row liste */}
          <div id="personnel-list" className="bg-white border border-border rounded-2xl shadow-sm overflow-hidden divide-y divide-border/60">
            {/* Column headers */}
            <div className="hidden lg:grid grid-cols-[44px_minmax(220px,1.4fr)_minmax(160px,1fr)_280px_120px] items-center gap-4 px-5 py-2.5 bg-surface-2/40 text-[10px] font-bold uppercase tracking-wider text-text-3">
              <div></div>
              <div>Personel</div>
              <div>Restoran · Araç</div>
              <div className="text-center">{periodLabel} · Paket / Saat / Gün</div>
              <div></div>
            </div>

            {filtered.map((p) => {
              const initials = (p.full_name ?? '?')
                .split(' ').filter(Boolean).slice(0, 2)
                .map((w) => w[0]?.toUpperCase()).join('');
              const grad = AVATAR_COLORS[p.role as keyof typeof AVATAR_COLORS] || 'from-blue-700 to-blue-500';
              const veh = vehicleLabel(p);
              const isSelected = selectedIds.has(p.id);
              const status = p.status ?? 'Aktif';
              const s = statsMap.get(p.id);
              const hasData = !!s && (s.total_packages > 0 || s.total_hours > 0 || s.working_days > 0);
              const statusBar =
                status === 'Aktif' ? 'bg-emerald-500'
                : status === 'Pasif' ? 'bg-slate-300'
                : 'bg-rose-500';

              return (
                <div
                  key={p.id}
                  onClick={() => setEditingId(p.id)}
                  className={`group relative flex items-center gap-4 px-5 py-3 pl-6 cursor-pointer transition-all duration-150 ${
                    isSelected ? 'bg-brand-soft/40' : 'hover:bg-surface-2/40'
                  }`}
                  title="Düzenlemek için tıkla"
                >
                  {/* Status accent bar (sol) */}
                  <div className={`absolute left-0 top-0 bottom-0 w-1 ${statusBar} ${
                    status === 'Aktif' ? '' : 'opacity-60'
                  }`} />

                  {/* Multi-select checkbox (hover'da) */}
                  <button
                    onClick={(e) => { e.stopPropagation(); toggleSelect(p.id); }}
                    aria-label={isSelected ? 'Seçimi kaldır' : 'Seç'}
                    className={`w-5 h-5 rounded-md border-1.5 flex items-center justify-center flex-shrink-0 transition ${
                      isSelected
                        ? 'bg-brand border-brand opacity-100'
                        : 'bg-white border-border opacity-0 group-hover:opacity-100 hover:border-brand'
                    }`}
                  >
                    {isSelected && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
                  </button>

                  {/* Avatar + identity (1.4fr) */}
                  <div className="flex items-center gap-3 min-w-0 flex-1 lg:flex-initial lg:min-w-[220px] lg:max-w-[420px]">
                    <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${grad} text-white font-semibold flex items-center justify-center text-sm shadow-sm flex-shrink-0`}>
                      {initials}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                        <h4 className="font-display text-[14.5px] font-semibold text-text truncate">
                          {p.full_name || '—'}
                        </h4>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider whitespace-nowrap ${
                          ROLE_STYLES[p.role ?? ''] || 'bg-surface-2 text-text-2'
                        }`}>
                          {p.role || '—'}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[11.5px] text-text-3">
                        <span className="font-mono tabular-nums">{p.person_code || '—'}</span>
                        {p.phone && (
                          <>
                            <span>·</span>
                            <span className="inline-flex items-center gap-0.5 truncate">
                              <Phone className="w-3 h-3" strokeWidth={2} />
                              <span className="tabular-nums">{p.phone}</span>
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Restaurant + vehicle (orta sütun) */}
                  <div className="hidden lg:flex flex-col gap-0.5 min-w-0 flex-1 max-w-[200px]">
                    {restName(p.assigned_restaurant_id) ? (
                      <span className="text-xs text-text-2 inline-flex items-center gap-1.5 truncate">
                        <Utensils className="w-3 h-3 text-text-3 flex-shrink-0" strokeWidth={2} />
                        <span className="truncate">{restName(p.assigned_restaurant_id)}</span>
                      </span>
                    ) : (
                      <span className="text-xs text-text-3 italic">Atanmamış</span>
                    )}
                    <span className={`inline-flex w-fit text-[10px] font-semibold px-1.5 py-0.5 rounded ${veh.color}`}>
                      {veh.label}
                    </span>
                  </div>

                  {/* Stats inline strip */}
                  <div className={`hidden md:flex items-center gap-4 px-3.5 py-1.5 rounded-lg border flex-shrink-0 ${
                    hasData ? 'bg-blue-50/50 border-blue-100' : 'bg-surface-2/50 border-border/70'
                  }`} style={{ width: 280 }}>
                    <Metric
                      label="Paket"
                      value={hasData ? (s!.total_packages).toLocaleString('tr-TR') : '—'}
                      active={hasData}
                    />
                    <div className="w-px h-7 bg-border/60" />
                    <Metric
                      label="Saat"
                      value={hasData ? Math.round(s!.total_hours).toLocaleString('tr-TR') : '—'}
                      active={hasData}
                    />
                    <div className="w-px h-7 bg-border/60" />
                    <Metric
                      label="Gün"
                      value={hasData ? `${s!.working_days}/${periodMaxDays}` : '—'}
                      active={hasData}
                    />
                  </div>

                  {/* Edit action */}
                  <div className="flex items-center gap-2 flex-shrink-0 ml-auto lg:ml-0" style={{ width: 120 }}>
                    <button
                      onClick={(e) => { e.stopPropagation(); setEditingId(p.id); }}
                      aria-label="Bilgileri düzenle"
                      className="opacity-60 group-hover:opacity-100 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-border text-text-2 text-xs font-semibold transition-all duration-200 group-hover:bg-brand group-hover:text-white group-hover:border-brand group-hover:shadow-md"
                    >
                      <Pencil className="w-3.5 h-3.5" strokeWidth={2.2} />
                      Düzenle
                    </button>
                    <ChevronRight className="w-4 h-4 text-text-3 opacity-0 group-hover:opacity-100 transition" strokeWidth={2.2} />
                  </div>
                </div>
              );
            })}
          </div>
        </>
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
                  onClick={() => setEditingId(p.id)}
                  className={`bg-white border rounded-2xl overflow-hidden transition-all duration-300 cursor-pointer shadow-sm hover:shadow-lg hover:-translate-y-0.5 relative group ${
                    isSelected ? 'border-brand shadow-md ring-3 ring-brand/20' : 'border-border hover:border-brand/40'
                  }`}
                  title="Düzenlemek için tıkla"
                >
                  {/* Multi-select checkbox (sol üst, hover'da görünür) */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSelect(p.id);
                    }}
                    aria-label={isSelected ? 'Seçimi kaldır' : 'Seç'}
                    className={`absolute top-3 left-3 w-5 h-5 rounded-md border-1.5 flex items-center justify-center z-10 transition shadow-sm ${
                      isSelected
                        ? 'bg-brand border-brand opacity-100'
                        : 'bg-white/90 backdrop-blur-sm border-border hover:border-brand opacity-0 group-hover:opacity-100'
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5 text-white" strokeWidth={3} />}
                  </button>

                  {/* Edit button (sağ üst, hep görünür — daha belirgin hover'da) */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingId(p.id);
                    }}
                    aria-label="Bilgileri düzenle"
                    className="absolute top-3 right-3 z-10 inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-white/95 backdrop-blur-sm border border-border text-text-2 text-xs font-semibold shadow-sm hover:bg-brand hover:text-white hover:border-brand hover:shadow-md transition-all duration-200"
                  >
                    <Pencil className="w-3.5 h-3.5" strokeWidth={2.2} />
                    <span className="hidden group-hover:inline">Düzenle</span>
                  </button>

                  {/* Cover strip (h-12) */}
                  <div className={`h-12 ${coverColor}`} />

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

                    {/* Stats (seçili dönemin aylık aggregate — backend stats'tan) */}
                    {(() => {
                      const s = statsMap.get(p.id);
                      const pkts = s?.total_packages ?? 0;
                      const hrs = s?.total_hours ?? 0;
                      const days = s?.working_days ?? 0;
                      const hasData = pkts > 0 || hrs > 0 || days > 0;
                      return (
                        <div className={[
                          'rounded-lg p-2 mb-2.5 border',
                          hasData ? 'bg-blue-50/60 border-blue-100' : 'bg-cream-50 border-border',
                        ].join(' ')}>
                          <div className="grid grid-cols-3 gap-1 text-center text-xs">
                            <div>
                              <div className={`font-mono font-bold ${hasData ? 'text-blue-700' : 'text-text-3'}`}>
                                {hasData ? pkts.toLocaleString('tr-TR') : '—'}
                              </div>
                              <div className="text-text-3 uppercase tracking-wide font-semibold mt-0.5 text-xs">Paket</div>
                            </div>
                            <div>
                              <div className={`font-mono font-bold ${hasData ? 'text-blue-700' : 'text-text-3'}`}>
                                {hasData ? Math.round(hrs).toLocaleString('tr-TR') : '—'}
                              </div>
                              <div className="text-text-3 uppercase tracking-wide font-semibold mt-0.5 text-xs">Saat</div>
                            </div>
                            <div>
                              <div className={`font-mono font-bold ${hasData ? 'text-blue-700' : 'text-text-3'}`}>
                                {hasData ? `${days}/${periodMaxDays}` : '—/—'}
                              </div>
                              <div className="text-text-3 uppercase tracking-wide font-semibold mt-0.5 text-xs">Gün</div>
                            </div>
                          </div>
                        </div>
                      );
                    })()}

                    {/* Vehicle badge */}
                    <span className={`inline-flex text-xs font-semibold px-2 py-1 rounded-lg ${veh.color}`}>
                      {veh.label}
                    </span>
                  </div>
                </div>
              );
            })}
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

// ──────────────────────────────────────────────────────────────────
// Akıllı İçgörü Hero — gerçek insights verisinden anlatım üretir
// ──────────────────────────────────────────────────────────────────
// AI kart key'lerine ikon + fallback tone eşlemesi
const AI_CARD_META: Record<string, { Icon: LucideIcon; tone: 'emerald' | 'amber' | 'blue' | 'rose' }> = {
  esik_asimi: { Icon: TrendingUp, tone: 'emerald' },
  eksik_kapasite: { Icon: AlertTriangle, tone: 'amber' },
  verimlilik: { Icon: Award, tone: 'blue' },
  bekleyen_aksiyon: { Icon: Inbox, tone: 'rose' },
};

function SmartInsightsHero({
  insights, aiInsights, period,
}: {
  insights: PageInsights;
  aiInsights: AiInsightsResponse | null;
  period: string;
}) {
  // Hangi alt panel açık: detay listeleri / eylem önerileri / yok
  const [expanded, setExpanded] = useState<'detail' | 'actions' | null>(null);

  // AI state — refresh için canlı tutulur
  const [aiData, setAiData] = useState<AiInsightsResponse | null>(aiInsights);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const ai = aiData?.payload?.ai ?? null;
  const aiCards = ai?.cards ?? null;

  async function handleRefresh() {
    if (refreshing) return;
    setRefreshing(true);
    setRefreshError(null);
    try {
      const fresh = await getAiInsights(period, true);
      if (fresh) {
        setAiData(fresh);
      } else {
        setRefreshError('AI servisine ulaşılamadı.');
      }
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : 'Yenileme başarısız.');
    } finally {
      setRefreshing(false);
    }
  }

  const generatedAtLabel = useMemo(() => {
    if (!aiData?.generated_at) return null;
    const d = new Date(aiData.generated_at);
    if (Number.isNaN(d.getTime())) return null;
    const now = new Date();
    const diffMin = Math.max(0, Math.floor((now.getTime() - d.getTime()) / 60000));
    if (diffMin < 1) return 'az önce';
    if (diffMin < 60) return `${diffMin} dakika önce`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr} saat önce`;
    const diffDay = Math.floor(diffHr / 24);
    return `${diffDay} gün önce`;
  }, [aiData?.generated_at]);

  // Eşik aşımı potansiyel ek fatura — paket eşiğini aşma trendiyle
  // her kurye için (eşik+50 paket × rate_high) kaba potansiyel
  const thresholdPotential = useMemo(() => {
    return insights.threshold_near.reduce((sum, t) => {
      const projected = Math.max(t.threshold, t.packages) + 50;
      const extraPackages = Math.max(0, projected - t.threshold);
      return sum + extraPackages * (t.rate_high || 0);
    }, 0);
  }, [insights.threshold_near]);

  // Geri kazanım %'leri — top_recovery'den
  const topRecovery = useMemo(() => {
    return insights.top_recovery.slice(0, 2).map((m) => ({
      name: m.full_name?.split(' ')[0] ?? '—',
      pct: m.salary > 0
        ? Math.min(100, Math.round(((m.cover_hours * 200 + m.cover_packages * 25) / m.salary) * 100))
        : 0,
    }));
  }, [insights.top_recovery]);

  // Kapasite açığı toplam (target - actual) farkları
  const capacityGap = useMemo(() => {
    return insights.capacity_gaps.reduce((s, g) => s + Math.max(0, g.target - g.actual), 0);
  }, [insights.capacity_gaps]);

  const top1 = insights.threshold_near[0];
  const top2 = insights.threshold_near[1];
  const cap1 = insights.capacity_gaps[0];

  // Hero başlığı — gerçek sayılarla dinamik
  const headlineParts: { text: string; em?: boolean }[] = [];
  if (insights.threshold_near.length > 0) {
    headlineParts.push({ text: `${insights.threshold_near.length} kuryen ` });
    headlineParts.push({
      text: `${top1?.threshold ?? 390} paket eşiğini`,
      em: true,
    });
    headlineParts.push({ text: ' aşmak üzere — ay sonuna kadar ek ' });
    headlineParts.push({
      text: `${formatTL(thresholdPotential)} ₺`,
      em: true,
    });
    headlineParts.push({ text: ' fatura potansiyeli.' });
  } else if (insights.capacity_gaps.length > 0) {
    headlineParts.push({ text: `${insights.capacity_gaps.length} restoranda ` });
    headlineParts.push({ text: `kapasite açığı`, em: true });
    headlineParts.push({ text: ` — toplam ${capacityGap} kuryelik boşluk.` });
  } else {
    headlineParts.push({ text: 'Tüm operasyon dengede — ' });
    headlineParts.push({ text: 'eşik / kapasite uyarısı yok', em: true });
    headlineParts.push({ text: '.' });
  }

  return (
    <div
      className="rounded-3xl border border-border shadow-sm p-7 mb-5 relative overflow-hidden animate-hero-fade-in"
      style={{
        background: `radial-gradient(900px circle at 92% -8%, rgba(56,189,248,0.16), transparent 50%),
                    radial-gradient(700px circle at -8% 110%, rgba(15,82,186,0.12), transparent 55%),
                    linear-gradient(135deg, #FFFFFF 0%, #F4F8FE 100%)`,
      }}
    >
      {/* Dot pattern overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(15,82,186,0.07) 1px, transparent 0)',
          backgroundSize: '22px 22px',
          maskImage: 'linear-gradient(135deg, transparent 35%, black 80%)',
        }}
      />

      <div className="grid grid-cols-3 gap-7 relative z-10">
        {/* Sol: dinamik anlatım */}
        <div className="col-span-2">
          <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider text-white shadow-sm bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-500">
              <Sparkles className="w-3.5 h-3.5" strokeWidth={2.4} />
              {ai ? 'AI Üretimi · Claude' : 'Akıllı İçgörü · Bu Hafta'}
              <span className="ml-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-white/25 text-[9.5px] font-semibold tracking-normal">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-soft" />
                {aiData?.stale ? 'Eski' : 'Canlı'}
              </span>
            </div>

            {/* Cache yaşı + Yenile butonu */}
            {ai && (
              <div className="inline-flex items-center gap-2 text-[11px] text-text-3">
                {generatedAtLabel && (
                  <span className="font-medium">{generatedAtLabel} üretildi</span>
                )}
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-white border border-border hover:border-brand/40 hover:text-brand transition disabled:opacity-60 font-semibold"
                  title="AI'a tekrar üret"
                >
                  <span className={refreshing ? 'animate-spin' : ''}>↻</span>
                  {refreshing ? 'Yenileniyor…' : 'AI yenile'}
                </button>
              </div>
            )}
          </div>

          <h2 className="font-display text-[28px] font-semibold tracking-tight leading-snug text-text mt-1 mb-3">
            {ai?.headline ? (
              <span
                style={{
                  background: 'linear-gradient(135deg, #0B0D17 0%, #0F52BA 70%, #38BDF8 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  fontWeight: 600,
                }}
              >
                {ai.headline}
              </span>
            ) : (
              headlineParts.map((p, i) => p.em ? (
                <em
                  key={i}
                  style={{
                    fontStyle: 'normal',
                    background: 'linear-gradient(135deg, #0F52BA, #38BDF8)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    fontWeight: 700,
                  }}
                >
                  {p.text}
                </em>
              ) : (
                <span key={i}>{p.text}</span>
              ))
            )}
          </h2>

          <p className="text-text-2 text-[13.5px] leading-relaxed mb-5">
            {ai?.narrative ? (
              ai.narrative
            ) : top1 ? (
              <>
                <strong>{top1.brand ?? '—'}{top1.branch ? ` · ${top1.branch}` : ''}</strong>{' '}
                restoranındaki <strong>{top1.full_name ?? '—'}</strong>{' '}
                {top1.packages} pakette
                {top2 ? (
                  <>
                    , <strong>{top2.full_name?.split(' ')[0] ?? '—'}</strong> {top2.packages} pakette
                  </>
                ) : null}
                . Eşik (<strong>{top1.threshold}</strong> paket) aşılınca
                paket başı tarife <strong>{formatTL(top1.rate_low)} ₺</strong> →{' '}
                <strong>{formatTL(top1.rate_high)} ₺</strong>'ye yükseliyor (paket başı{' '}
                <strong>+%{Math.round(((top1.rate_high - top1.rate_low) / Math.max(top1.rate_low, 1)) * 100)}</strong>) — restoranın ödediği faturaya yansıyacak.
                {cap1 ? (
                  <>
                    {' '}Aynı zamanda{' '}
                    <strong>{cap1.brand}{cap1.branch ? ` · ${cap1.branch}` : ''}</strong>{' '}
                    için hedef <strong>{cap1.target} kurye</strong>, aktif{' '}
                    <strong>{cap1.actual}</strong> — kapasite{' '}
                    {cap1.actual === 0 ? 'tamamen boş' : `${cap1.target - cap1.actual} eksik`}.
                  </>
                ) : null}
              </>
            ) : cap1 ? (
              <>
                Restoran kapasitelerinde açık var:{' '}
                <strong>{cap1.brand}{cap1.branch ? ` · ${cap1.branch}` : ''}</strong>{' '}
                için hedef <strong>{cap1.target} kurye</strong>, aktif{' '}
                <strong>{cap1.actual}</strong>
                {cap1.actual === 0 ? ' — kapasite tamamen boş' : ` — ${cap1.target - cap1.actual} kurye eksik`}.
                Acil işe alım önerilir.
              </>
            ) : (
              <>Eşik aşımı veya eksik kapasite tespit edilmedi. Operasyon ölçek kırmızı çizgileri içinde.</>
            )}
          </p>

          <div className="flex gap-2">
            <button
              onClick={() => setExpanded(expanded === 'detail' ? null : 'detail')}
              className={[
                'px-4 py-2.5 text-xs font-semibold rounded-lg transition flex items-center gap-1.5',
                expanded === 'detail'
                  ? 'bg-text/90 text-white shadow-lg'
                  : 'bg-text text-white hover:shadow-lg',
              ].join(' ')}
            >
              <ArrowUpRight className="w-3.5 h-3.5" strokeWidth={2.4} />
              {expanded === 'detail' ? 'Detayı gizle' : 'Detaylı analiz'}
            </button>
            <button
              onClick={() => setExpanded(expanded === 'actions' ? null : 'actions')}
              className={[
                'px-4 py-2.5 text-xs font-semibold rounded-lg transition',
                expanded === 'actions'
                  ? 'bg-blue-50 border border-blue-300 text-blue-700'
                  : 'border border-border text-text-2 hover:bg-bg-surface2',
              ].join(' ')}
            >
              {expanded === 'actions' ? 'Önerileri gizle' : 'Eylem önerileri'}
            </button>
          </div>
        </div>

        {/* Sağ: 4 dinamik kart — AI varsa AI'dan, yoksa deterministik */}
        <div className="grid grid-cols-2 gap-2.5">
          {aiCards && aiCards.length === 4 ? (
            aiCards.map((card) => {
              // key'e göre ikon ve ton eşle (görsel tutarlılık için)
              const meta = AI_CARD_META[card.key] ?? AI_CARD_META.bekleyen_aksiyon;
              return (
                <InsightCard
                  key={card.key}
                  tone={card.tone === 'positive' ? 'emerald'
                       : card.tone === 'warning' ? 'amber'
                       : card.tone === 'info' ? 'blue'
                       : meta.tone}
                  Icon={meta.Icon}
                  label={card.label}
                  value={card.value}
                  metaJsx={<>{card.sub}</>}
                />
              );
            })
          ) : (
            <>
              <InsightCard
                tone="emerald"
                Icon={TrendingUp}
                label="Eşik Aşımı"
                value={`${insights.threshold_near.length} kurye`}
                metaJsx={
                  insights.threshold_near.length > 0 ? (
                    <>
                      <strong>+{formatTL(thresholdPotential)} ₺</strong> ek fatura potansiyeli
                    </>
                  ) : (
                    <>Bu ay eşik yakını yok</>
                  )
                }
              />
              <InsightCard
                tone="amber"
                Icon={AlertTriangle}
                label="Eksik Kapasite"
                value={`${insights.capacity_gaps.length} restoran`}
                metaJsx={
                  cap1 ? (
                    <>
                      <strong>{cap1.brand}</strong>{' '}{cap1.actual}/{cap1.target}
                      {capacityGap > 0 ? <> · toplam <strong>{capacityGap} açık</strong></> : null}
                    </>
                  ) : (
                    <>Hedef kapasite tam</>
                  )
                }
              />
              <InsightCard
                tone="blue"
                Icon={Award}
                label="Verimlilik Liderleri"
                value={
                  topRecovery.length > 0
                    ? topRecovery.map((r) => r.name).join(' + ')
                    : '—'
                }
                metaJsx={
                  topRecovery.length > 0 ? (
                    <>
                      Sabit maaşının <strong>%{topRecovery[0].pct}</strong>'sini cover ile geri kazandı
                    </>
                  ) : (
                    <>Sabit maaşlı veri yok</>
                  )
                }
              />
              <InsightCard
                tone="rose"
                Icon={Inbox}
                label="Bekleyen Aksiyonlar"
                value={`${insights.pending_actions} talep`}
                metaJsx={<>onay/red için bekliyor</>}
              />
            </>
          )}
        </div>
      </div>

      {/* AI refresh hatası — küçük banner */}
      {refreshError && (
        <div className="relative z-10 mt-3 text-[11.5px] text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-1.5 inline-block">
          {refreshError}
        </div>
      )}

      {/* Detaylı analiz / Eylem önerileri açılır panel */}
      {expanded === 'detail' && (
        <div className="relative z-10 mt-6 pt-6 border-t border-blue-200/60 grid grid-cols-3 gap-5 animate-hero-fade-in">
          <DetailColumn
            title="Eşik Yakını Kuryeler"
            empty="Eşiğe yaklaşan yok"
            tone="emerald"
          >
            {insights.threshold_near.map((t) => {
              const pct = Math.min(100, Math.round((t.packages / Math.max(t.threshold, 1)) * 100));
              return (
                <li key={t.id} className="bg-white/70 rounded-lg px-3 py-2 border border-emerald-100">
                  <div className="flex justify-between items-baseline gap-2">
                    <span className="font-semibold text-[13px] text-text truncate">
                      {t.full_name}
                    </span>
                    <span className="text-[11px] text-text-3 font-mono whitespace-nowrap">
                      {t.packages}/{t.threshold}
                    </span>
                  </div>
                  <div className="text-[11px] text-text-3 mt-0.5">
                    {t.brand}{t.branch ? ` · ${t.branch}` : ''}
                  </div>
                  {/* Progress bar — eşiğin %X'inde */}
                  <div className="mt-1.5 h-1.5 bg-emerald-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-emerald-400 to-emerald-600 rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </DetailColumn>

          <DetailColumn
            title="Kapasite Açıkları"
            empty="Tüm restoranlar dolu"
            tone="amber"
          >
            {insights.capacity_gaps.map((g) => {
              const fill = Math.round((g.actual / Math.max(g.target, 1)) * 100);
              return (
                <li key={g.id} className="bg-white/70 rounded-lg px-3 py-2 border border-amber-100">
                  <div className="flex justify-between items-baseline gap-2">
                    <span className="font-semibold text-[13px] text-text truncate">
                      {g.brand}
                    </span>
                    <span className="text-[11px] text-text-3 font-mono whitespace-nowrap">
                      {g.actual}/{g.target}
                    </span>
                  </div>
                  <div className="text-[11px] text-text-3 mt-0.5">
                    {g.branch ?? '—'} · {g.target - g.actual} kurye eksik
                  </div>
                  <div className="mt-1.5 h-1.5 bg-amber-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-400 to-amber-600 rounded-full transition-all"
                      style={{ width: `${fill}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </DetailColumn>

          <DetailColumn
            title="Verimlilik Liderleri"
            empty="Sabit maaşlı veri yok"
            tone="blue"
          >
            {insights.top_recovery.map((m) => {
              const cover = m.cover_hours * 200 + m.cover_packages * 25;
              const pct = m.salary > 0 ? Math.min(100, Math.round((cover / m.salary) * 100)) : 0;
              return (
                <li key={m.id} className="bg-white/70 rounded-lg px-3 py-2 border border-blue-100">
                  <div className="flex justify-between items-baseline gap-2">
                    <span className="font-semibold text-[13px] text-text truncate">
                      {m.full_name}
                    </span>
                    <span className="text-[11px] text-blue-700 font-bold whitespace-nowrap">
                      %{pct}
                    </span>
                  </div>
                  <div className="text-[11px] text-text-3 mt-0.5">
                    {m.role} · {m.cover_packages} paket · {Math.round(m.cover_hours)} sa
                  </div>
                  <div className="mt-1.5 h-1.5 bg-blue-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </DetailColumn>
        </div>
      )}

      {expanded === 'actions' && (
        <div className="relative z-10 mt-6 pt-6 border-t border-blue-200/60 animate-hero-fade-in">
          <div className="text-[11px] font-bold uppercase tracking-wider text-blue-700 mb-3">
            Önerilen Eylemler
          </div>
          <ul className="space-y-2.5">
            {buildActionItems(insights, thresholdPotential, capacityGap).map((a, i) => (
              <li
                key={i}
                className="flex items-start gap-3 bg-white/70 rounded-xl border border-border px-4 py-3"
              >
                <span className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-white shadow-sm ${a.tone}`}>
                  <a.Icon className="w-3.5 h-3.5" strokeWidth={2.4} />
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-semibold text-text">
                    {a.title}
                  </div>
                  <div className="text-[12px] text-text-2 mt-0.5 leading-relaxed">
                    {a.detail}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function DetailColumn({
  title, tone, empty, children,
}: {
  title: string;
  tone: 'emerald' | 'amber' | 'blue';
  empty: string;
  children: React.ReactNode;
}) {
  const labelTone = {
    emerald: 'text-emerald-700',
    amber: 'text-amber-700',
    blue: 'text-blue-700',
  }[tone];
  const childArray = Array.isArray(children) ? children : [children];
  const isEmpty = !childArray || childArray.length === 0 || childArray.every((c) => !c);
  return (
    <div>
      <div className={`text-[11px] font-bold uppercase tracking-wider mb-2 ${labelTone}`}>
        {title}
      </div>
      {isEmpty ? (
        <div className="text-[12px] text-text-3 italic px-3 py-2">{empty}</div>
      ) : (
        <ul className="space-y-1.5">{children}</ul>
      )}
    </div>
  );
}

function buildActionItems(
  insights: PageInsights,
  thresholdPotential: number,
  capacityGap: number,
): { title: string; detail: string; Icon: typeof Target; tone: string }[] {
  const out: { title: string; detail: string; Icon: typeof Target; tone: string }[] = [];

  if (insights.threshold_near.length > 0 && thresholdPotential > 0) {
    out.push({
      title: `${insights.threshold_near.length} kuryeyi eşik aşımı için takipte tut`,
      detail: `Eşiği geçtiklerinde paket başı tarife yüksek seviyeye atlayacak — ay sonuna kadar yaklaşık ${formatTL(thresholdPotential)} ₺ ek fatura. Restoran müdürlerini bilgilendir, motivasyon planla.`,
      Icon: TrendingUp,
      tone: 'bg-gradient-to-br from-emerald-500 to-emerald-700',
    });
  }

  if (insights.capacity_gaps.length > 0) {
    const totalGap = capacityGap;
    out.push({
      title: `${insights.capacity_gaps.length} restorana toplam ${totalGap} kurye al`,
      detail: `Aktif personel hedefin altında. Joker yönlendirmesi (kısa vadeli) + işe alım (kalıcı) paralel başlat. Öncelik: en büyük açıktan başla.`,
      Icon: AlertTriangle,
      tone: 'bg-gradient-to-br from-amber-500 to-amber-700',
    });
  }

  if (insights.top_recovery.length > 0) {
    const m = insights.top_recovery[0];
    const cover = m.cover_hours * 200 + m.cover_packages * 25;
    const pct = m.salary > 0 ? Math.round((cover / m.salary) * 100) : 0;
    out.push({
      title: `${m.full_name?.split(' ')[0] ?? 'Lider'} verimlilik liderini öne çıkar`,
      detail: `Sabit maaşının %${pct}'sini saha cover ile geri kazandırdı. Bu modeli diğer yönetim/yedek personele örnek olarak paylaş — ay başı toplantı veya ekip içi tanıtım önerilir.`,
      Icon: Award,
      tone: 'bg-gradient-to-br from-blue-500 to-blue-700',
    });
  }

  if (insights.pending_actions > 0) {
    out.push({
      title: `${insights.pending_actions} bekleyen kurye talebini bugün karara bağla`,
      detail: `Avans / motor / muhasebe talepleri bekliyor. Geç kalan onaylar kurye memnuniyetini düşürür ve avans gecikmeleri kasaya yansır.`,
      Icon: Inbox,
      tone: 'bg-gradient-to-br from-rose-500 to-rose-700',
    });
  }

  if (out.length === 0) {
    out.push({
      title: 'Operasyon dengede — fırsat aramaya geç',
      detail: 'Eşik aşımı veya kapasite açığı yok. Performans top performer\'ları analiz et, restoran satışlarını artırma fırsatları üzerine odaklan.',
      Icon: Sparkles,
      tone: 'bg-gradient-to-br from-blue-500 to-cyan-500',
    });
  }

  return out;
}

function InsightCard({
  tone, Icon, label, value, metaJsx,
}: {
  tone: 'emerald' | 'amber' | 'blue' | 'rose';
  Icon: typeof Target;
  label: string;
  value: string;
  metaJsx: React.ReactNode;
}) {
  const palettes = {
    emerald: {
      bg: 'bg-emerald-50/80',
      border: 'border-emerald-200',
      iconBg: 'bg-emerald-100',
      iconText: 'text-emerald-700',
      label: 'text-emerald-800',
    },
    amber: {
      bg: 'bg-amber-50/80',
      border: 'border-amber-200',
      iconBg: 'bg-amber-100',
      iconText: 'text-amber-700',
      label: 'text-amber-800',
    },
    blue: {
      bg: 'bg-blue-50/80',
      border: 'border-blue-200',
      iconBg: 'bg-blue-100',
      iconText: 'text-blue-700',
      label: 'text-blue-800',
    },
    rose: {
      bg: 'bg-rose-50/80',
      border: 'border-rose-200',
      iconBg: 'bg-rose-100',
      iconText: 'text-rose-700',
      label: 'text-rose-800',
    },
  } as const;
  const p = palettes[tone];
  return (
    <div
      className={[
        p.bg, p.border,
        'rounded-2xl border p-3.5 backdrop-blur-sm',
        'transition-all duration-200',
        'hover:shadow-md hover:-translate-y-0.5 cursor-pointer',
      ].join(' ')}
    >
      <div className="flex items-start justify-between mb-2">
        <div className={`w-8 h-8 rounded-lg ${p.iconBg} ${p.iconText} flex items-center justify-center shadow-sm`}>
          <Icon className="w-4 h-4" strokeWidth={2.4} />
        </div>
      </div>
      <div className={`text-[10.5px] font-bold uppercase tracking-wider ${p.label} mb-1`}>
        {label}
      </div>
      <div className="font-display text-[16px] font-semibold text-text leading-tight mb-1">
        {value}
      </div>
      <div className="text-[11.5px] text-text-2 leading-snug">
        {metaJsx}
      </div>
    </div>
  );
}

function formatTL(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return Math.round(value).toLocaleString('tr-TR');
}

// ──────────────────────────────────────────────────────────────────
// Management Card — Çat Kapında brand: saks mavisi + krem
// SVG donut · brand gradient ring · krem zemin · subtle pattern
// ──────────────────────────────────────────────────────────────────
function ManagementCard({
  member, onEdit,
}: {
  member: ManagementMember;
  onEdit: () => void;
}) {
  const isBM = member.role?.includes('Bölge');
  const recovery = member.cover_hours * 200 + member.cover_packages * 25;
  const recoveryPct = member.salary > 0
    ? Math.min(100, Math.round((recovery / member.salary) * 100))
    : 0;
  const netCost = Math.max(0, member.salary - recovery);
  const initials = (member.full_name ?? '?')
    .split(' ').filter(Boolean).slice(0, 2)
    .map((w) => w[0]?.toUpperCase()).join('');

  // SVG donut math
  const radius = 32;
  const stroke = 6;
  const size = 80;
  const c = 2 * Math.PI * radius;
  const dashOffset = c * (1 - recoveryPct / 100);

  // Stable unique id per kart (gradient defs)
  const gradId = `mgmt-grad-${member.id}`;

  // Cover oranı tonu
  const tonal =
    recoveryPct >= 50
      ? { tint: 'text-brand-dark', chipBg: 'bg-brand-soft', chipText: 'text-brand-dark', label: 'güçlü cover' }
      : recoveryPct >= 25
      ? { tint: 'text-cream-400', chipBg: 'bg-cream-100', chipText: 'text-text', label: 'orta cover' }
      : { tint: 'text-text-2', chipBg: 'bg-cream-soft', chipText: 'text-text-2', label: 'düşük cover' };

  return (
    <div
      onClick={onEdit}
      className="group relative cursor-pointer rounded-2xl overflow-hidden transition-all duration-300 border border-cream-200 shadow-sm hover:shadow-lg hover:-translate-y-0.5"
      style={{
        // Çat Kapında krem zemin → beyazımsı geçiş
        background: 'linear-gradient(160deg, #FDFAF3 0%, #FFFFFF 60%)',
      }}
    >
      {/* Saks mavisi top accent bar — Çat Kapında signature */}
      <div className="h-1.5" style={{
        background: 'linear-gradient(90deg, #0A3F8F 0%, #0F52BA 50%, #3B7BCF 100%)',
      }} />

      {/* Decorative brand orb (sağ üstte saks mavisi blur) */}
      <div
        className="absolute -top-10 -right-10 w-32 h-32 rounded-full pointer-events-none opacity-40"
        style={{
          background: isBM
            ? 'radial-gradient(circle, rgba(15,82,186,0.18) 0%, transparent 65%)'
            : 'radial-gradient(circle, rgba(201,174,122,0.32) 0%, transparent 65%)',
        }}
      />

      {/* Subtle dot grid (Çat Kapında textile dokusu) */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.06]"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, #0F52BA 1px, transparent 0)',
          backgroundSize: '14px 14px',
        }}
      />

      <div className="relative z-10 p-5">
        {/* Header — avatar + ad/kod + role pill */}
        <div className="flex items-start gap-3 mb-4">
          <div
            className="w-11 h-11 rounded-xl text-white font-bold flex items-center justify-center text-[13px] flex-shrink-0 shadow-sm"
            style={{
              background: isBM
                ? 'linear-gradient(135deg, #0A3F8F 0%, #0F52BA 100%)'
                : 'linear-gradient(135deg, #C9AE7A 0%, #E8D9B5 100%)',
              color: isBM ? '#FFFFFF' : '#5A4A30',
            }}
          >
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-display text-[15px] font-semibold text-text truncate leading-tight">
              {member.full_name || '—'}
            </div>
            <div className="text-[10.5px] text-text-3 font-mono tabular-nums mt-0.5">
              {member.person_code ?? ''}
            </div>
          </div>
          {/* Role badge (Çat Kapında brand) */}
          <span
            className="px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider flex-shrink-0"
            style={{
              background: isBM ? '#0F52BA' : '#F0E6D0',
              color: isBM ? '#FFFFFF' : '#5A4A30',
              boxShadow: isBM ? '0 2px 6px rgba(15,82,186,0.25)' : 'none',
            }}
          >
            {isBM ? 'BM' : 'Joker'}
          </span>
        </div>

        {/* Hero — donut + net maliyet */}
        <div className="flex items-center gap-3.5 mb-4">
          {/* SVG donut — brand gradient ring */}
          <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="-rotate-90">
              <defs>
                <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0F52BA" />
                  <stop offset="100%" stopColor="#3B7BCF" />
                </linearGradient>
              </defs>
              {/* Track */}
              <circle
                cx={size / 2} cy={size / 2} r={radius}
                stroke="#F4EFE3" strokeWidth={stroke} fill="none"
              />
              {/* Progress */}
              <circle
                cx={size / 2} cy={size / 2} r={radius}
                stroke={`url(#${gradId})`}
                strokeWidth={stroke}
                fill="none"
                strokeDasharray={c}
                strokeDashoffset={dashOffset}
                strokeLinecap="round"
                style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.22, 1, 0.36, 1)' }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
              <div className={`font-display text-[18px] font-bold tabular-nums ${tonal.tint}`}>
                %{recoveryPct}
              </div>
              <div className="text-[8.5px] uppercase tracking-wider font-bold text-text-3 mt-0.5">
                Cover
              </div>
            </div>
          </div>

          {/* Net maliyet hero */}
          <div className="min-w-0 flex-1">
            <div className="text-[9.5px] uppercase tracking-wider font-bold text-text-3 mb-0.5">
              Net Maliyet
            </div>
            <div className="font-display text-[24px] font-semibold text-text leading-none tabular-nums">
              {tr(netCost)}
              <span className="text-text-3 text-base font-normal ml-0.5">₺</span>
            </div>
            <div className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded mt-2 text-[10px] font-semibold ${tonal.chipBg} ${tonal.chipText}`}>
              {tonal.label}
            </div>
          </div>
        </div>

        {/* Visual breakdown bar — krem (maaş) + saks mavisi (cover) */}
        <div className="mb-4">
          <div className="flex h-2 rounded-full overflow-hidden" style={{ background: '#EDE5D2' }}>
            <div
              style={{
                width: `${100 - recoveryPct}%`,
                background: 'linear-gradient(90deg, #C9AE7A, #E8D9B5)',
              }}
            />
            <div
              style={{
                width: `${recoveryPct}%`,
                background: 'linear-gradient(90deg, #0F52BA, #3B7BCF)',
              }}
            />
          </div>
          <div className="flex justify-between mt-1.5 text-[10px] font-semibold tabular-nums">
            <span className="text-text-2">Maaş {tr(member.salary)} ₺</span>
            <span className="text-brand">↺ {tr(recovery)} ₺</span>
          </div>
        </div>

        {/* Footer — 3 stat */}
        <div className="grid grid-cols-3 gap-2 pt-3 border-t border-cream-200">
          <ManagementStat label="Cover" value={member.cover_days} />
          <ManagementStat label="Paket" value={member.cover_packages} />
          <ManagementStat
            label="Çalışma"
            value={Math.round(member.cover_hours)}
            unit="sa"
          />
        </div>

        {/* Hover edit chip — sağ alt */}
        <button
          onClick={(e) => { e.stopPropagation(); onEdit(); }}
          aria-label="Bilgileri düzenle"
          className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-all duration-200 px-2 py-1 rounded-md bg-brand text-white text-[10px] font-bold inline-flex items-center gap-1 shadow-md"
        >
          <Pencil className="w-3 h-3" strokeWidth={2.4} />
          Düzenle
        </button>
      </div>
    </div>
  );
}

function ManagementStat({
  label, value, unit,
}: {
  label: string;
  value: number;
  unit?: string;
}) {
  return (
    <div className="text-center">
      <div className="font-mono text-[15px] font-bold tabular-nums text-text leading-tight">
        {value.toLocaleString('tr-TR')}{unit ? <span className="text-[11px] text-text-3 font-normal ml-0.5">{unit}</span> : null}
      </div>
      <div className="text-[9.5px] text-text-3 uppercase tracking-wider font-bold mt-0.5">
        {label}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Inline metric (paket / saat / gün) — liste satırı için
// ──────────────────────────────────────────────────────────────────
function Metric({
  label, value, active,
}: {
  label: string;
  value: string;
  active: boolean;
}) {
  return (
    <div className="text-center min-w-[60px] flex-1">
      <div className={`font-mono text-[14px] font-bold tabular-nums leading-tight ${
        active ? 'text-blue-700' : 'text-text-3'
      }`}>
        {value}
      </div>
      <div className="text-[9px] text-text-3 uppercase tracking-wider font-bold mt-0.5">
        {label}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Yönetim özet kartı — toplam maaş / restoran başı / cover / net
// ──────────────────────────────────────────────────────────────────
function SummaryCard({
  tone, label, value, sub,
}: {
  tone: 'rose' | 'blue' | 'emerald' | 'amber';
  label: string;
  value: string;
  sub?: string;
}) {
  const palettes = {
    rose: { bg: 'bg-rose-50/70', border: 'border-rose-200', label: 'text-rose-700', value: 'text-rose-900' },
    blue: { bg: 'bg-blue-50/70', border: 'border-blue-200', label: 'text-blue-700', value: 'text-blue-900' },
    emerald: { bg: 'bg-emerald-50/70', border: 'border-emerald-200', label: 'text-emerald-700', value: 'text-emerald-900' },
    amber: { bg: 'bg-amber-50/70', border: 'border-amber-200', label: 'text-amber-700', value: 'text-amber-900' },
  } as const;
  const p = palettes[tone];
  return (
    <div className={`rounded-2xl border ${p.bg} ${p.border} p-3.5`}>
      <div className={`text-[10.5px] font-bold uppercase tracking-[0.1em] ${p.label} mb-1.5`}>
        {label}
      </div>
      <div className={`font-display text-[20px] font-bold tabular-nums tracking-tight ${p.value} leading-tight`}>
        {value}
      </div>
      {sub && (
        <div className="text-[11.5px] text-text-3 mt-1 leading-snug">
          {sub}
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Restoran Takım Şefleri — attıkları paketler şirkete ek kâr (paket × oran)
// ──────────────────────────────────────────────────────────────────
function RTSSection({
  rts, restMap,
}: {
  rts: ManagementMember[];
  restMap: Map<number, Restaurant>;
}) {
  // RTŞ paket başı net oranı — KDV hariç, faturada %20 KDV eklenir
  const RTS_RATE = 32;
  const KDV = 0.20;
  void restMap;

  if (rts.length === 0) return null;

  return (
    <div className="mt-3 space-y-1.5">
      {rts.map((m) => {
        const net = m.cover_packages * RTS_RATE;
        const kdv = net * KDV;
        const brut = net + kdv;
        return (
          <div
            key={m.id}
            className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-cream-200 bg-cream-50/60"
          >
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-cream-200 text-text flex-shrink-0">
              RTŞ
            </span>
            <span className="font-semibold text-[13.5px] text-text truncate">
              {m.full_name}
            </span>
            <span className="text-[11.5px] text-text-3 font-mono tabular-nums truncate">
              {m.person_code}
            </span>
            <span className="ml-auto text-[12px] text-text-2 inline-flex items-baseline gap-1.5 whitespace-nowrap">
              <span className="font-mono tabular-nums font-semibold text-text">{m.cover_packages}</span>
              <span className="text-text-3">paket × {RTS_RATE} ₺</span>
              <span className="text-text-3">+ KDV</span>
              <span className="text-text-3">=</span>
              <span className="font-mono tabular-nums font-bold text-brand-dark">
                +{Math.round(brut).toLocaleString('tr-TR')} ₺
              </span>
              <span className="text-[10.5px] text-text-3 font-medium">şirkete kar</span>
              <span
                className="text-[10px] text-text-3 font-mono tabular-nums"
                title={`Net ${net.toLocaleString('tr-TR')} ₺ · KDV %20 ${Math.round(kdv).toLocaleString('tr-TR')} ₺`}
              >
                ({net.toLocaleString('tr-TR')}+{Math.round(kdv).toLocaleString('tr-TR')})
              </span>
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Premium KPI Hero Kartı — 4 kart aynı dilde, gradient + progress
// ──────────────────────────────────────────────────────────────────
function KpiHeroCard({
  variant, Icon, label, value, sub, subBold, progress,
}: {
  variant: 'brand' | 'blue' | 'slate' | 'amber';
  Icon: LucideIcon;
  label: string;
  value: number;
  sub: React.ReactNode;
  subBold?: string;
  progress?: number;
}) {
  // Tüm kartlar aynı tasarım dilinde, sadece tone değişiyor
  const palettes = {
    brand: {
      bg: 'bg-gradient-to-br from-blue-700 via-blue-600 to-blue-500',
      text: 'text-white',
      label: 'text-blue-100/90',
      sub: 'text-white/85',
      iconBg: 'bg-white/20 ring-1 ring-white/30',
      iconText: 'text-white',
      progressBg: 'bg-white/20',
      progressFill: 'bg-gradient-to-r from-cyan-300 to-white',
      shadow: 'shadow-[0_8px_24px_rgba(15,82,186,0.35)]',
    },
    blue: {
      bg: 'bg-white',
      text: 'text-text',
      label: 'text-blue-700',
      sub: 'text-text-3',
      iconBg: 'bg-blue-100',
      iconText: 'text-blue-700',
      progressBg: 'bg-blue-100',
      progressFill: 'bg-gradient-to-r from-blue-400 to-blue-600',
      shadow: 'shadow-sm',
    },
    slate: {
      bg: 'bg-white',
      text: 'text-text',
      label: 'text-slate-700',
      sub: 'text-text-3',
      iconBg: 'bg-slate-100',
      iconText: 'text-slate-700',
      progressBg: 'bg-slate-100',
      progressFill: 'bg-gradient-to-r from-slate-500 to-slate-700',
      shadow: 'shadow-sm',
    },
    amber: {
      bg: 'bg-white',
      text: 'text-text',
      label: 'text-amber-700',
      sub: 'text-text-3',
      iconBg: 'bg-amber-100',
      iconText: 'text-amber-700',
      progressBg: 'bg-amber-100',
      progressFill: 'bg-gradient-to-r from-amber-400 to-amber-600',
      shadow: 'shadow-sm',
    },
  } as const;
  const p = palettes[variant];

  return (
    <div
      className={[
        p.bg, p.text, p.shadow,
        'rounded-2xl p-5 border border-border/60',
        'transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg',
        'relative overflow-hidden',
      ].join(' ')}
    >
      {/* Top-right ikon */}
      <div className="flex items-start justify-between mb-3">
        <div className={`text-[10.5px] font-bold uppercase tracking-[0.12em] ${p.label}`}>
          {label}
        </div>
        <div className={`w-9 h-9 rounded-xl ${p.iconBg} ${p.iconText} flex items-center justify-center shadow-sm`}>
          <Icon className="w-4 h-4" strokeWidth={2.4} />
        </div>
      </div>

      {/* Sayı */}
      <div className="font-display text-[40px] font-bold tracking-tight tabular-nums leading-none mb-2.5">
        {value.toLocaleString('tr-TR')}
      </div>

      {/* Progress bar — 0..100% */}
      {typeof progress === 'number' && (
        <div className={`h-1 rounded-full overflow-hidden mb-2 ${p.progressBg}`}>
          <div
            className={`h-full ${p.progressFill} transition-all duration-700 ease-out rounded-full`}
            style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
          />
        </div>
      )}

      {/* Alt bilgi */}
      <div className={`text-[12px] leading-snug ${p.sub}`}>
        {subBold && <span className="font-semibold">{subBold}{' · '}</span>}
        {sub}
      </div>
    </div>
  );
}
