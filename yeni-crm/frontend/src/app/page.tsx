import Link from 'next/link';
import {
  ArrowDownRight, ArrowUpRight, Calendar, TrendingUp,
  Plus, Users, Wallet, Activity, Package, Clock, FileText, Sparkles,
  CheckCircle2, CircleDot, Hourglass, Receipt, Trophy,
} from 'lucide-react';

import { Sidebar } from '@/components/sidebar';
import {
  getDashboardSummary,
  getSidebarCounts,
  getDeductionSummaryByType,
  getDashboardAnalytics,
  getManagementSummary,
  getInvoiceSummary,
  type DashboardSummary,
  type SidebarCounts,
  type DashboardAnalytics,
  type ManagementMember,
  type InvoiceSummary,
} from '@/lib/api';

export const dynamic = 'force-dynamic';

// ─────────────────────────────────────────────────────────────
// MOCK / DEMO veriler — modüller geliştirildikçe gerçek API'ye bağlanacak
// ─────────────────────────────────────────────────────────────
const MOCK_PIPELINE = [
  { stage: 'Görüşme', count: 3, color: 'border-brand', items: [
    { name: 'Big Chefs', meta: 'Anadolu · 6 kurye · ~180K' },
    { name: 'Pizzami', meta: '3 şube · saat+prim · ~210K' },
    { name: 'Tatlı Stop', meta: '1 şube · ~80K' },
  ]},
  { stage: 'Teklif', count: 2, color: 'border-brand-light', items: [
    { name: 'Bafra Pide', meta: 'Eşikli · 2 şube · ~145K' },
    { name: 'Burger King', meta: 'Aylık sabit · ~135K' },
  ]},
  { stage: 'Müzakere', count: 1, color: 'border-cream-400', items: [
    { name: "Domino's Pizza", meta: 'Fiyat görüşmesi · ~190K' },
  ]},
  { stage: 'Anlaşma', count: 2, color: 'border-green-500', items: [
    { name: 'Yavuzbey İskender', meta: '15 Mart başladı · 240K' },
    { name: 'SC Petshop', meta: 'Aylık sabit · 79K' },
  ]},
  { stage: 'Olumsuz', count: 4, color: 'border-red-500', items: [
    { name: 'Mado', meta: 'Bütçe dışı · 220K kayıp' },
    { name: 'Komagene', meta: 'İç ekiple yapacak · 90K' },
  ]},
];

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string): string {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function shortMonth(p: string): string {
  const [, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!m) return p;
  const map = ['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'];
  return map[m - 1];
}

// Bugüne yakın 6 ay (4 geçmiş + bu ay + 1 gelecek)
function periodsAroundToday(selected?: string): string[] {
  const today = new Date();
  const y = today.getFullYear();
  const m = today.getMonth() + 1;
  const out: string[] = [];
  for (let offset = -4; offset <= 1; offset++) {
    let nm = m + offset;
    let ny = y;
    while (nm < 1) { nm += 12; ny -= 1; }
    while (nm > 12) { nm -= 12; ny += 1; }
    out.push(`${ny.toString().padStart(4, '0')}-${nm.toString().padStart(2, '0')}`);
  }
  if (selected && !out.includes(selected)) {
    out.push(selected);
    out.sort();
  }
  return out;
}

// ─────────────────────────────────────────────────────────────
// PAGE
// ─────────────────────────────────────────────────────────────
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string }>;
}) {
  const { ay } = await searchParams;
  const period = ay ?? '2026-03';
  const periods = periodsAroundToday(period);

  let summary: DashboardSummary | null = null;
  let counts: SidebarCounts | null = null;
  let deductions: Array<{ deduction_type: string; total: number }> = [];
  let analytics: DashboardAnalytics | null = null;
  let management: ManagementMember[] = [];
  let invoiceSummary: InvoiceSummary | null = null;
  let error: string | null = null;

  try {
    [summary, counts, analytics, management, invoiceSummary] = await Promise.all([
      getDashboardSummary(period),
      getSidebarCounts().catch(() => null),
      getDashboardAnalytics(period),
      getManagementSummary(period).catch(() => []),
      getInvoiceSummary(period).catch(() => null),
    ]);
    deductions = (await getDeductionSummaryByType(period)).map((d) => ({
      deduction_type: d.deduction_type,
      total: d.total,
    }));
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  // Sabit Maliyet Verimliliği — gerçek management verisinden hesapla
  const efficiencyCards = management
    .filter((m) => m.salary > 0)
    .map((m) => {
      const recovery = m.cover_hours * 200 + m.cover_packages * 25;
      const pct = m.salary > 0 ? Math.min(100, (recovery / m.salary) * 100) : 0;
      const netCost = Math.max(0, m.salary - recovery);
      return { ...m, recovery, pct, netCost };
    })
    .sort((a, b) => b.pct - a.pct)
    .slice(0, 3);

  const totalSalary = management.reduce((s, m) => s + m.salary, 0);
  const totalRecovery = management.reduce(
    (s, m) => s + (m.cover_hours * 200 + m.cover_packages * 25),
    0,
  );
  const totalNetCost = Math.max(0, totalSalary - totalRecovery);
  const totalPct = totalSalary > 0 ? (totalRecovery / totalSalary) * 100 : 0;

  // Bekleyen aksiyonlar — gerçek sidebar counts'tan
  const pendingActions = counts ? [
    { key: 'avans', label: 'Avans onayı', count: counts.avans, href: '/talepler/avans', icon: Wallet, urgent: counts.avans > 5 },
    { key: 'puantaj', label: 'Puantaj onayı', count: counts.puantaj_onay, href: '/puantaj-onay', icon: CheckCircle2, urgent: counts.puantaj_onay > 10 },
    { key: 'hakedis', label: 'Hakediş onayı', count: counts.hakedis_onay, href: '/hakedis-onay', icon: Receipt, urgent: counts.hakedis_onay > 5 },
    { key: 'talepler', label: 'Motor/Muhasebe talepleri', count: counts.talepler, href: '/talepler', icon: FileText, urgent: false },
    { key: 'profil', label: 'Profil onayı', count: counts.profil_onay, href: '/profil-onaylari', icon: Users, urgent: false },
  ].filter((a) => a.count > 0) : [];

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen bg-bg">
      <Sidebar active="dashboard" counts={counts} />
      <main className="overflow-auto">
        <div className="px-9 py-7 max-w-[1500px] mx-auto">
          {/* HEADER */}
          <div className="flex justify-between items-start mb-8 gap-5 flex-wrap">
            <div>
              <div className="text-[13px] text-text-3 font-medium mb-1.5">
                İyi akşamlar, <span className="font-semibold text-brand">Ebru</span>
              </div>
              <h1 className="font-display text-3xl font-semibold tracking-tight leading-tight text-text mb-1.5">
                {formatPeriod(period)} · Genel Bakış
              </h1>
              <div className="text-text-3 text-sm font-medium">
                {summary
                  ? `${summary.puantaj_entries.toLocaleString('tr-TR')} puantaj girişi · ${summary.active_restaurants} aktif restoran · ${summary.active_personnel} aktif personel`
                  : '— veri yükleniyor —'}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-1 bg-bg-surface border border-border rounded-xl p-1 shadow-sm flex-wrap">
                {[...periods].reverse().map((p) => {
                  const isActive = p === period;
                  return (
                    <Link
                      key={p}
                      href={`/?ay=${p}`}
                      className={`px-3 py-1.5 rounded-lg text-[12.5px] font-semibold transition whitespace-nowrap ${
                        isActive
                          ? 'bg-brand text-white shadow-sm'
                          : 'text-text-2 hover:bg-bg-surface2'
                      }`}
                    >
                      {formatPeriod(p)}
                    </Link>
                  );
                })}
              </div>
              <button className="bg-brand text-white px-4 py-2 rounded-lg font-medium text-sm hover:bg-brand-dark transition inline-flex items-center gap-1.5">
                <Plus className="w-4 h-4" /> Yeni
              </button>
            </div>
          </div>

          {error ? (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm mb-6">
              <strong>API hatası:</strong> {error}
            </div>
          ) : null}

          {/* AI INSIGHT BANNER */}
          {analytics && analytics.ai_insights.length > 0 ? (
            <div className="bg-gradient-to-r from-cream-soft via-white to-brand-mist border border-cream-200 rounded-2xl p-4 mb-7 flex gap-4 items-start">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-brand to-brand-light flex items-center justify-center text-white">
                <Sparkles className="w-5 h-5" strokeWidth={1.8} />
              </div>
              <div className="flex-1 text-sm text-text-2 leading-relaxed">
                <strong className="text-brand">
                  {analytics.ai_insights[0].severity === 'alert' ? 'Acil dikkat:' :
                   analytics.ai_insights[0].severity === 'warning' ? 'Dikkat:' :
                   'Bilgi:'}
                </strong> {analytics.ai_insights[0].text}
              </div>
            </div>
          ) : null}

          {/* HERO KPI ROW — 4 kart, hepsi gerçek veri */}
          <div className="grid grid-cols-[1.4fr_1fr_1fr_1fr] gap-3.5 mb-6">
            <KpiCardHero analytics={analytics} />

            <KpiCard
              label="Net Kâr"
              icon={<Wallet className="w-3.5 h-3.5" />}
              iconBg="bg-emerald-50 text-emerald-600"
              value={analytics ? (analytics.net_profit / 1_000_000).toFixed(2) : '—'}
              valueSuffix="M ₺"
              subtitle={analytics ? `Maliyet: ${(analytics.total_costs / 1_000_000).toFixed(2)}M ₺` : ''}
            />

            <KpiCard
              label="Tahmini Marj"
              icon={<TrendingUp className="w-3.5 h-3.5" />}
              iconBg="bg-green-50 text-green-600"
              value={analytics ? analytics.margin_pct.toFixed(1) : '—'}
              valueSuffix="%"
              subtitle="Brüt fatura − maliyet"
            />

            <KpiCard
              label="Aktif Personel"
              icon={<Users className="w-3.5 h-3.5" />}
              iconBg="bg-brand-soft text-brand"
              value={summary ? summary.active_personnel.toString() : '—'}
              subtitle={summary ? `${summary.kurye_count} kurye · ${summary.joker_count} joker` : ''}
            />
          </div>

          {/* TAHSİLAT BANNER — gerçek InvoiceSummary verisi */}
          <CollectionBanner invoiceSummary={invoiceSummary} period={period} />

          {/* OPERASYONEL VITAL SIGNS — gerçek summary verisi */}
          <div className="grid grid-cols-5 gap-3 mb-6">
            <VitalCard
              icon={<Activity className="w-4 h-4" />}
              iconColor="text-blue-600 bg-blue-50"
              label="Puantaj girişi"
              value={summary ? summary.puantaj_entries.toLocaleString('tr-TR') : '—'}
              unit="kayıt"
            />
            <VitalCard
              icon={<Clock className="w-4 h-4" />}
              iconColor="text-purple-600 bg-purple-50"
              label="Çalışılan saat"
              value={summary ? summary.total_hours.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) : '—'}
              unit="saat"
            />
            <VitalCard
              icon={<Package className="w-4 h-4" />}
              iconColor="text-orange-600 bg-orange-50"
              label="Toplam paket"
              value={summary ? summary.total_packages.toLocaleString('tr-TR') : '—'}
              unit="paket"
            />
            <VitalCard
              icon={<ArrowDownRight className="w-4 h-4" />}
              iconColor="text-rose-600 bg-rose-50"
              label="Manuel kesinti"
              value={summary ? (summary.total_deductions / 1000).toLocaleString('tr-TR', { maximumFractionDigits: 0 }) : '—'}
              unit="K ₺"
              subtitle={`${deductions.length} tip`}
            />
            <VitalCard
              icon={<Receipt className="w-4 h-4" />}
              iconColor="text-amber-600 bg-amber-50"
              label="Tevkifat"
              value={analytics ? (analytics.tevkifat_total / 1000).toLocaleString('tr-TR', { maximumFractionDigits: 0 }) : '—'}
              unit="K ₺"
              subtitle="2/10 KDV"
            />
          </div>

          {/* SABİT MALİYET VERİMLİLİĞİ — gerçek management */}
          <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6 mb-6">
            <div className="mb-4">
              <h2 className="font-display text-lg font-semibold text-text mb-1">Sabit Maliyet Verimliliği</h2>
              <p className="text-sm text-text-3">
                Yönetim ekibi & Joker — sabit maaşlarını geri kazanma oranları
                {management.length > 0 && ` · ${management.length} kişi`}
              </p>
            </div>

            {efficiencyCards.length === 0 ? (
              <div className="text-sm text-text-3 italic py-6 text-center">
                Bu ay için sabit maaşlı yönetim verisi yok.
              </div>
            ) : (
              <div className="grid grid-cols-4 gap-3">
                {efficiencyCards.map((m) => {
                  const isJoker = m.role === 'Joker';
                  const initials = (m.full_name ?? '?')
                    .split(' ')
                    .filter(Boolean)
                    .slice(0, 2)
                    .map((w) => w[0]?.toUpperCase())
                    .join('');
                  const fmt = (v: number) =>
                    v.toLocaleString('tr-TR', { maximumFractionDigits: 0 });
                  return (
                    <EfficiencyCard
                      key={m.id}
                      initials={initials || '?'}
                      name={m.full_name ?? '—'}
                      role={m.role ?? '—'}
                      trend={`+%${m.pct.toFixed(0)}`}
                      barPercent={Math.min(100, m.pct)}
                      salary={`${fmt(m.salary)} ₺`}
                      recovery={`+${fmt(m.recovery)} ₺`}
                      netCost={`${fmt(m.netCost)} ₺`}
                      cover={String(m.cover_days ?? 0)}
                      packages={String(m.cover_packages ?? 0)}
                      workHours={`${Math.round(m.cover_hours)}sa`}
                      gradientFrom={isJoker ? 'from-amber-600' : 'from-blue-700'}
                      gradientTo={isJoker ? 'to-amber-400' : 'to-blue-500'}
                      isJoker={isJoker}
                    />
                  );
                })}
                <div className="border-2 border-brand rounded-2xl p-5 bg-gradient-to-br from-brand-mist to-bg-surface flex flex-col justify-center">
                  <div className="text-xs font-bold text-brand uppercase tracking-wider mb-3">
                    Toplam Verimlilik
                  </div>
                  <div className="font-display text-2xl font-bold text-brand mb-1">
                    {totalNetCost.toLocaleString('tr-TR', { maximumFractionDigits: 0 })} ₺
                  </div>
                  <div className="text-xs text-text-3 mb-4">Net sabit maliyet</div>
                  <div className="border-t border-brand-border pt-3 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-text-2">Brüt gider</span>
                      <span className="font-mono font-semibold">
                        {totalSalary.toLocaleString('tr-TR', { maximumFractionDigits: 0 })} ₺
                      </span>
                    </div>
                    <div className="flex justify-between text-green-600">
                      <span>Geri kazanım</span>
                      <span className="font-mono font-bold">
                        −{totalRecovery.toLocaleString('tr-TR', { maximumFractionDigits: 0 })} ₺
                      </span>
                    </div>
                  </div>
                  <div className="mt-3 text-xs font-bold text-white bg-green-600 text-center py-1.5 rounded-lg">
                    %{totalPct.toFixed(1)} toplam geri kazanım
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* CHARTS ROW — Trendi + Donut */}
          <div className="grid grid-cols-[1.6fr_1fr] gap-4 mb-6">
            <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6">
              <div className="mb-4">
                <h2 className="font-display text-lg font-semibold text-text">Aylık Fatura Trendi</h2>
                <p className="text-sm text-text-3">Son 3 ay · KDV hariç · gerçek puantaj verisi</p>
              </div>
              <RevenueLargeChart data={analytics?.revenue_trend || []} />
            </div>

            <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6">
              <div className="mb-4">
                <h2 className="font-display text-lg font-semibold text-text">Kesinti Dağılımı</h2>
                <p className="text-sm text-text-3">{formatPeriod(period)} · {analytics?.deduction_breakdown.length || 0} tip</p>
              </div>
              <DonutChart
                deductions={analytics?.deduction_breakdown.map(d => ({
                  deduction_type: d.deduction_type,
                  total: d.total,
                })) || []}
                total={analytics?.deduction_breakdown.reduce((s, d) => s + d.total, 0) || 0}
              />
            </div>
          </div>

          {/* TOP RESTORANLAR — gerçek by_restaurant verisi, yeni tasarım */}
          <TopRestaurantsPanel restaurants={analytics?.by_restaurant || []} period={period} />

          {/* DİKKAT İSTENEN — gerçek bekleyen aksiyonlar (counts) */}
          {pendingActions.length > 0 && (
            <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6 mb-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="font-display text-lg font-semibold text-text">Dikkat İstenen</h2>
                  <p className="text-sm text-text-3">
                    {pendingActions.reduce((s, a) => s + a.count, 0)} aksiyon onayını bekliyor
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-5 gap-3">
                {pendingActions.map((a) => {
                  const Icon = a.icon;
                  return (
                    <Link
                      key={a.key}
                      href={a.href}
                      className={`group rounded-xl border p-4 hover:shadow-md transition ${
                        a.urgent
                          ? 'bg-red-50 border-red-200 hover:border-red-400'
                          : 'bg-bg-surface2 border-border hover:border-brand'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                          a.urgent ? 'bg-red-100 text-red-600' : 'bg-brand-soft text-brand'
                        }`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        {a.urgent && (
                          <span className="bg-red-600 text-white text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded">
                            ACİL
                          </span>
                        )}
                      </div>
                      <div className="font-display text-2xl font-bold text-text mb-1">
                        {a.count}
                      </div>
                      <div className="text-xs text-text-3 font-medium leading-snug">
                        {a.label}
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          {/* SALES PIPELINE — DEMO */}
          <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6 mb-6 relative">
            <span className="absolute top-4 right-4 px-2 py-0.5 rounded-md bg-yellow-100 text-yellow-800 text-[10px] font-bold uppercase tracking-wider border border-yellow-200">
              DEMO · Örnek Veri
            </span>
            <div className="mb-4">
              <h2 className="font-display text-lg font-semibold text-text">Yeni Müşteri Kazanım Hattı</h2>
              <p className="text-sm text-text-3">
                Lead modülü geliştirildikçe gerçek satış pipeline'ı buraya gelecek
              </p>
            </div>

            <div className="grid grid-cols-5 gap-3 mb-6">
              <FunnelStage stage="Görüşme" count="3" value="~470K ₺" sub="tahmini aylık değer" percent={100} color="bg-brand" />
              <FunnelStage stage="Teklif" count="2" value="~280K ₺" sub="teklif iletilmiş" percent={80} color="bg-brand-light" />
              <FunnelStage stage="Müzakere" count="1" value="~190K ₺" sub="aktif görüşme" percent={60} color="bg-cream-400" />
              <FunnelStage stage="Anlaşma" count="2" value="+319K ₺" sub="bu ay kazanılan" percent={40} color="bg-green-500" />
              <FunnelStage stage="Olumsuz" count="4" value="~410K ₺" sub="kaçırılan fırsat" percent={25} color="bg-red-500" />
            </div>

            <div className="grid grid-cols-5 gap-3">
              {MOCK_PIPELINE.map((col) => (
                <div key={col.stage} className={`border-t-3 ${col.color} rounded-lg bg-gradient-to-b from-bg-surface2 to-bg-surface p-3`}>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-text mb-3 flex justify-between items-center">
                    {col.stage}
                    <span className="text-xs font-semibold bg-bg-surface text-text-2 px-2 py-1 rounded-full border border-border">
                      {col.count}
                    </span>
                  </h4>
                  <div className="space-y-2">
                    {col.items.map((item, i) => (
                      <div key={i} className="bg-bg-surface border border-border rounded-lg p-2.5 cursor-pointer hover:shadow-sm transition">
                        <div className="text-xs font-semibold text-text">{item.name}</div>
                        <div className="text-xs text-text-3 mt-1">{item.meta}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* BOTTOM 2 — Bu Ay Beklenen + YoY (DEMO) */}
          <div className="grid grid-cols-2 gap-6 mb-12">
            {/* Bu Ay Beklenen — DEMO */}
            <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6 relative">
              <span className="absolute top-3 right-3 px-2 py-0.5 rounded-md bg-yellow-100 text-yellow-800 text-[9.5px] font-bold uppercase tracking-wider border border-yellow-200">
                DEMO
              </span>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand to-brand-light flex items-center justify-center text-white">
                  <Calendar className="w-5 h-5" strokeWidth={2.2} />
                </div>
                <div>
                  <h3 className="font-display text-base font-semibold">Bu Ay Beklenen</h3>
                  <p className="text-xs text-text-3">3 ödeme noktası · {formatPeriod(period)}</p>
                </div>
              </div>

              <div className="space-y-4 text-sm">
                <TimelineItem date="15" amount="2,7M ₺" text="Kuryelere maaş ödemesi" isFirst />
                <TimelineItem date="25" amount="~800K ₺" text="Avans dağıtımı" />
                <TimelineItem date="30" amount="+5,3M ₺" text="Restoran fatura kesimi" isFinal />
              </div>
            </div>

            {/* YoY — DEMO */}
            <div className="bg-gradient-to-br from-bg-surface to-green-50 border border-border rounded-2xl shadow-md p-6 relative">
              <span className="absolute top-3 right-3 px-2 py-0.5 rounded-md bg-yellow-100 text-yellow-800 text-[9.5px] font-bold uppercase tracking-wider border border-yellow-200">
                DEMO
              </span>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-green-500 to-green-400 flex items-center justify-center text-white">
                  <ArrowUpRight className="w-5 h-5" strokeWidth={2.2} />
                </div>
                <div>
                  <h3 className="font-display text-base font-semibold">Yıllık Büyüme</h3>
                  <p className="text-xs text-text-3">Geçen yıl verisi geldikçe canlanacak</p>
                </div>
              </div>

              <div className="mb-4">
                <div className="font-display text-4xl font-bold text-green-600 mb-1">+%28</div>
                <p className="text-sm text-text-3 font-semibold">örnek büyüme oranı</p>
              </div>

              <div className="mb-2">
                <svg width="100%" height="60" viewBox="0 0 240 60" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="growGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10B981" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path d="M0,48 L20,46 L40,42 L60,38 L80,40 L100,32 L120,30 L140,24 L160,20 L180,18 L200,12 L220,10 L240,6 L240,60 L0,60 Z" fill="url(#growGrad)" />
                  <path d="M0,48 L20,46 L40,42 L60,38 L80,40 L100,32 L120,30 L140,24 L160,20 L180,18 L200,12 L220,10 L240,6" stroke="#10B981" strokeWidth="2" fill="none" strokeLinecap="round" />
                  <circle cx="240" cy="6" r="4" fill="#10B981" stroke="white" strokeWidth="2" />
                </svg>
              </div>

              <div className="border-t border-border pt-3 text-xs text-text-3">
                Geçmiş yıl puantaj verisi sisteme aktarıldıkça gerçek YoY değeri burada görünecek.
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// KPI Hero
// ─────────────────────────────────────────────────────────────
function KpiCardHero({ analytics }: { analytics: DashboardAnalytics | null }) {
  const trend = analytics && analytics.invoiced_kdv_haric > 0;

  return (
    <div className="rounded-2xl p-6 shadow-md border-0 overflow-hidden relative group" style={{
      background: 'linear-gradient(135deg, #0A3F8F 0%, #0F52BA 35%, #3B7BCF 70%, #E8D9B5 100%)',
    }}>
      <div className="absolute inset-0 opacity-30 mix-blend-overlay pointer-events-none" style={{
        backgroundImage: 'radial-gradient(900px circle at 90% -10%, rgba(248, 242, 230, 0.35), transparent 45%), radial-gradient(700px circle at 110% 60%, rgba(232, 217, 181, 0.5), transparent 55%), radial-gradient(500px circle at 10% 100%, rgba(0,0,0,0.18), transparent 50%)',
      }} />

      <div className="absolute inset-0 opacity-[0.06] pointer-events-none" style={{
        backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0)',
        backgroundSize: '16px 16px',
      }} />

      <div className="relative z-10">
        <div className="text-xs font-bold uppercase tracking-widest text-white/85 mb-4">
          Toplam Fatura · KDV hariç
        </div>
        <div className="font-display text-4xl font-bold text-white mb-1 num">
          {analytics ? (analytics.invoiced_kdv_haric / 1_000_000).toFixed(2) : '—'}
          <span className="text-lg font-medium text-white/70 ml-2">M ₺</span>
        </div>
        {trend && (
          <div className="text-xs text-white/85 mt-4 flex items-center gap-2">
            <span className="inline-flex items-center gap-1 bg-white/22 text-white px-2 py-0.5 rounded font-semibold text-[11px]">
              <ArrowUpRight className="w-3 h-3" /> Net kâr {(analytics!.net_profit / 1_000_000).toFixed(2)}M
            </span>
            <span>marj %{analytics!.margin_pct.toFixed(1)}</span>
          </div>
        )}
        <div className="text-xs text-white/70 mt-3 font-medium">
          {analytics ? (
            <>+KDV: {(analytics.invoiced_kdv_dahil / 1_000_000).toFixed(2)}M ₺ · Tevkifat: {(analytics.tevkifat_total / 1_000_000).toFixed(2)}M ₺</>
          ) : (
            'Veri henüz yüklenmedi'
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// KPI Card (basit)
// ─────────────────────────────────────────────────────────────
function KpiCard({
  label, icon, iconBg, value, valueSuffix, subtitle,
}: {
  label: string;
  icon: React.ReactNode;
  iconBg: string;
  value: string;
  valueSuffix?: string;
  subtitle?: string;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-5 shadow-md hover:shadow-lg hover:-translate-y-0.5 transition">
      <div className={`w-7 h-7 rounded-lg ${iconBg} flex items-center justify-center mb-3`}>
        {icon}
      </div>
      <div className="text-xs font-semibold uppercase tracking-wider text-text-3 mb-3">
        {label}
      </div>
      <div className="font-display text-3xl font-bold text-text num">
        {value}
        {valueSuffix && <span className="text-lg text-text-3 font-medium ml-1">{valueSuffix}</span>}
      </div>
      {subtitle && (
        <div className="mt-3 text-xs text-text-3 font-medium">
          {subtitle}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Tahsilat Banner — gerçek InvoiceSummary
// ─────────────────────────────────────────────────────────────
function CollectionBanner({
  invoiceSummary, period,
}: {
  invoiceSummary: InvoiceSummary | null;
  period: string;
}) {
  if (!invoiceSummary || invoiceSummary.count_total === 0) {
    return (
      <div className="bg-gradient-to-br from-bg-surface to-cream-50 border border-cream-200 rounded-2xl p-5 mb-6 flex items-center gap-5">
        <div className="w-11 h-11 rounded-xl bg-cream-200 flex items-center justify-center text-cream-700">
          <Hourglass className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <div className="font-display text-base font-semibold text-text">Tahsilat henüz başlamamış</div>
          <div className="text-xs text-text-3 mt-1">
            {formatPeriod(period)} için fatura kesildikçe burada tahsilat oranı görünecek.
          </div>
        </div>
        <Link href="/faturalar" className="text-xs font-semibold text-brand hover:text-brand-dark transition">
          Faturalara git →
        </Link>
      </div>
    );
  }

  const s = invoiceSummary;
  const collectedM = (s.sum_paid / 1_000_000).toFixed(2);
  const balanceM = (s.sum_balance / 1_000_000).toFixed(2);
  const totalM = (s.sum_incl_vat / 1_000_000).toFixed(2);
  const pct = s.collection_pct;

  return (
    <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6 mb-6">
      <div className="flex items-start justify-between mb-4 gap-4 flex-wrap">
        <div>
          <h2 className="font-display text-lg font-semibold text-text mb-0.5">Tahsilat Durumu</h2>
          <p className="text-sm text-text-3">
            {formatPeriod(period)} · {s.count_total} fatura · {totalM}M ₺ KDV dahil
          </p>
        </div>
        <Link
          href="/faturalar"
          className="text-xs font-semibold text-brand hover:text-brand-dark transition px-3 py-1.5 rounded-lg bg-brand-mist border border-brand-border"
        >
          Faturalar →
        </Link>
      </div>

      <div className="grid grid-cols-[1.2fr_1fr_1fr_1fr] gap-4 items-stretch">
        {/* Big Collection % */}
        <div className="bg-gradient-to-br from-emerald-50 to-emerald-100/50 border border-emerald-200 rounded-xl p-5 relative overflow-hidden">
          <div className="absolute top-3 right-3 w-7 h-7 rounded-lg bg-emerald-500 text-white flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <div className="text-xs font-bold uppercase tracking-wider text-emerald-700 mb-2">
            Tahsilat oranı
          </div>
          <div className="font-display text-4xl font-bold text-emerald-700 num">
            %{pct.toFixed(1)}
          </div>
          <div className="text-xs text-emerald-700/80 mt-2 font-medium">
            {collectedM}M ₺ tahsil edildi
          </div>
          {/* Progress bar */}
          <div className="mt-4 h-2 bg-emerald-200/40 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full"
              style={{ width: `${Math.min(100, pct)}%` }}
            />
          </div>
        </div>

        <CollectionCell
          icon={<CheckCircle2 className="w-4 h-4" />}
          color="text-emerald-600 bg-emerald-50"
          label="Ödendi"
          count={s.count_paid}
          amount={collectedM}
        />
        <CollectionCell
          icon={<CircleDot className="w-4 h-4" />}
          color="text-amber-600 bg-amber-50"
          label="Kısmi ödeme"
          count={s.count_partial}
          amount={s.count_partial > 0 ? ((s.sum_paid - 0) / 1_000_000).toFixed(2) : '0.00'}
          isPartial
        />
        <CollectionCell
          icon={<Hourglass className="w-4 h-4" />}
          color="text-rose-600 bg-rose-50"
          label="Bekliyor"
          count={s.count_pending}
          amount={balanceM}
          isPending
        />
      </div>
    </div>
  );
}

function CollectionCell({
  icon, color, label, count, amount, isPartial, isPending,
}: {
  icon: React.ReactNode;
  color: string;
  label: string;
  count: number;
  amount: string;
  isPartial?: boolean;
  isPending?: boolean;
}) {
  return (
    <div className="bg-bg-surface2 border border-border rounded-xl p-4 flex flex-col justify-between">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${color}`}>
          {icon}
        </div>
        <span className="font-display text-xl font-bold text-text num">
          {count}
        </span>
      </div>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider text-text-3 mb-1">
          {label}
        </div>
        <div className={`text-sm font-mono font-semibold ${
          isPending ? 'text-rose-600' : isPartial ? 'text-amber-600' : 'text-emerald-600'
        }`}>
          {isPending ? '−' : ''}{amount}M ₺
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Vital Sign Card
// ─────────────────────────────────────────────────────────────
function VitalCard({
  icon, iconColor, label, value, unit, subtitle,
}: {
  icon: React.ReactNode;
  iconColor: string;
  label: string;
  value: string;
  unit: string;
  subtitle?: string;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4 shadow-sm hover:shadow-md transition">
      <div className={`w-7 h-7 rounded-lg ${iconColor} flex items-center justify-center mb-3`}>
        {icon}
      </div>
      <div className="text-xs font-semibold uppercase tracking-wider text-text-3 mb-1">
        {label}
      </div>
      <div className="font-display text-xl font-bold text-text num">
        {value}
        <span className="text-xs text-text-3 font-medium ml-1">{unit}</span>
      </div>
      {subtitle && (
        <div className="text-[11px] text-text-3 mt-1.5">
          {subtitle}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Top Restoranlar — yeni tasarım, gerçek by_restaurant verisi
// ─────────────────────────────────────────────────────────────
function TopRestaurantsPanel({
  restaurants, period,
}: {
  restaurants: Array<{ id: number; brand: string; branch: string; courier_count: number; invoiced: number; pricing_model: string }>;
  period: string;
}) {
  if (!restaurants.length) {
    return (
      <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6 mb-6">
        <h2 className="font-display text-lg font-semibold text-text mb-1">Top Restoranlar</h2>
        <p className="text-sm text-text-3">
          {formatPeriod(period)} için puantaj verisi geldikçe restoran sıralaması burada görünecek.
        </p>
      </div>
    );
  }

  const sorted = [...restaurants].sort((a, b) => b.invoiced - a.invoiced);
  const leader = sorted[0];
  const rest = sorted.slice(1, 8);
  const maxInvoiced = leader.invoiced || 1;
  const totalShown = sorted.reduce((s, r) => s + r.invoiced, 0);

  const pricingLabel = (m: string) => {
    if (m === 'hourly_only') return 'Saatlik';
    if (m === 'hourly_plus_package') return 'Saat + Paket';
    if (m === 'threshold_package') return 'Eşikli Paket';
    if (m === 'fixed_monthly') return 'Aylık Sabit';
    return m;
  };

  return (
    <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6 mb-6">
      <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-text mb-1 flex items-center gap-2">
            <Trophy className="w-5 h-5 text-cream-700" />
            Top Restoranlar
          </h2>
          <p className="text-sm text-text-3">
            {formatPeriod(period)} · gerçek puantaj geliri · {sorted.length} restoran
          </p>
        </div>
        <Link
          href="/restoranlar"
          className="text-xs font-semibold text-brand hover:text-brand-dark transition px-3 py-1.5 rounded-lg bg-brand-mist border border-brand-border"
        >
          Tüm restoranlar →
        </Link>
      </div>

      <div className="grid grid-cols-[1.2fr_2fr] gap-5">
        {/* Leader card */}
        <div
          className="rounded-2xl p-5 text-white relative overflow-hidden"
          style={{ background: 'linear-gradient(135deg, #0A3F8F 0%, #0F52BA 50%, #3B7BCF 100%)' }}
        >
          <div className="absolute inset-0 opacity-[0.08]" style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.5) 1px, transparent 0)',
            backgroundSize: '14px 14px',
          }} />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-white/22 flex items-center justify-center">
                <Trophy className="w-4 h-4" />
              </div>
              <span className="text-xs font-bold uppercase tracking-widest text-white/85">
                Birinci
              </span>
            </div>
            <div className="font-display text-2xl font-bold mb-1 leading-tight">
              {leader.brand}
            </div>
            <div className="text-sm text-white/85 mb-4">
              {leader.branch} · {pricingLabel(leader.pricing_model)}
            </div>

            <div className="bg-white/15 backdrop-blur-sm rounded-xl p-3 mb-3">
              <div className="text-[10px] font-bold uppercase tracking-widest text-white/70 mb-1">
                Aylık Fatura
              </div>
              <div className="font-display text-3xl font-bold num">
                {(leader.invoiced / 1000).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}
                <span className="text-base text-white/70 ml-1">K ₺</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-white/12 rounded-lg p-2">
                <div className="text-white/70 text-[10px] uppercase font-semibold tracking-wider">Kurye</div>
                <div className="font-mono font-bold text-base">{leader.courier_count}</div>
              </div>
              <div className="bg-white/12 rounded-lg p-2">
                <div className="text-white/70 text-[10px] uppercase font-semibold tracking-wider">Paylar</div>
                <div className="font-mono font-bold text-base">
                  %{totalShown > 0 ? ((leader.invoiced / totalShown) * 100).toFixed(0) : '0'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bar list */}
        <div className="space-y-2">
          {rest.length === 0 ? (
            <div className="text-sm text-text-3 italic text-center py-8">
              Diğer restoranlar için veri henüz akmıyor.
            </div>
          ) : (
            rest.map((r, idx) => {
              const pct = (r.invoiced / maxInvoiced) * 100;
              return (
                <Link
                  key={r.id}
                  href={`/restoranlar/${r.id}`}
                  className="flex items-center gap-3 p-3 rounded-xl bg-bg-surface2 border border-border hover:border-brand hover:shadow-sm transition group"
                >
                  <div className="w-7 h-7 rounded-lg bg-bg-surface border border-border flex items-center justify-center text-xs font-bold text-text-2 group-hover:bg-brand-soft group-hover:text-brand group-hover:border-brand-border transition">
                    {idx + 2}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-3 mb-1.5">
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-text truncate">
                          {r.brand}
                        </div>
                        <div className="text-[11px] text-text-3 truncate">
                          {r.branch} · {pricingLabel(r.pricing_model)} · {r.courier_count} kurye
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="font-mono font-bold text-sm text-text">
                          {(r.invoiced / 1000).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}K ₺
                        </div>
                      </div>
                    </div>
                    <div className="h-1.5 bg-bg-surface rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-brand to-brand-light rounded-full"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </Link>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Revenue Trend Chart
// ─────────────────────────────────────────────────────────────
function RevenueLargeChart({
  data: providedData,
}: {
  data?: Array<{ period: string; invoiced: number; net_paid: number }>;
}) {
  const data = (providedData || []).map((d) => ({
    label: shortMonth(d.period),
    period: d.period,
    withoutVat: d.invoiced || 0,
    withVat: (d.invoiced || 0) * 1.2,
  }));

  if (data.length === 0) {
    return (
      <div className="h-72 flex items-center justify-center text-text-3 text-sm">
        Bu dönem için trend verisi yok — puantaj girildikçe canlanacak.
      </div>
    );
  }

  const maxVal = Math.max(...data.map((d) => d.withVat)) * 1.1 || 1;
  const h = 220;

  return (
    <div className="h-72 relative" style={{ minHeight: '280px' }}>
      <svg width="100%" height="100%" viewBox="0 0 600 280" preserveAspectRatio="none" style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(30, 64, 255, 0.25)" />
            <stop offset="100%" stopColor="rgba(30, 64, 255, 0)" />
          </linearGradient>
        </defs>

        {[0, 1, 2, 3, 4, 5].map((i) => (
          <line key={i} x1="0" y1={(i * h) / 5 + 20} x2="600" y2={(i * h) / 5 + 20} stroke="#ECEEF3" strokeWidth="1" />
        ))}

        <polyline
          points={data.map((d, i) => `${data.length === 1 ? 300 : (i / (data.length - 1)) * 600},${240 - (d.withoutVat / maxVal) * 200}`).join(' ')}
          fill="none"
          stroke="#1E40FF"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        <path
          d={`M ${data.map((d, i) => `${data.length === 1 ? 300 : (i / (data.length - 1)) * 600},${240 - (d.withoutVat / maxVal) * 200}`).join(' L ')} L 600,240 L 0,240 Z`}
          fill="url(#revGrad)"
        />

        <polyline
          points={data.map((d, i) => `${data.length === 1 ? 300 : (i / (data.length - 1)) * 600},${240 - (d.withVat / maxVal) * 200}`).join(' ')}
          fill="none"
          stroke="#C9AE7A"
          strokeWidth="1.8"
          strokeDasharray="5,5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Data point dots */}
        {data.map((d, i) => (
          <circle
            key={`pt-${i}`}
            cx={data.length === 1 ? 300 : (i / (data.length - 1)) * 600}
            cy={240 - (d.withoutVat / maxVal) * 200}
            r="4"
            fill="#1E40FF"
            stroke="white"
            strokeWidth="2"
          />
        ))}

        {data.map((d, i) => (
          <text
            key={i}
            x={data.length === 1 ? 300 : (i / (data.length - 1)) * 600}
            y="270"
            textAnchor="middle"
            fontSize="11"
            fill="#8B92A7"
            fontWeight="500"
          >
            {d.label}
          </text>
        ))}

        {[0, 1, 2, 3, 4, 5].map((i) => {
          const value = ((maxVal * (5 - i)) / 5) / 1_000_000;
          return (
            <text key={i} x="5" y={(i * h) / 5 + 25} fontSize="11" fill="#8B92A7" textAnchor="start">
              {value.toFixed(1)}M ₺
            </text>
          );
        })}
      </svg>

      <div className="relative z-10 mt-20 px-4 flex justify-end items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-brand" />
          <span className="text-text-2 font-medium">KDV hariç</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="w-4 h-0.5"
            style={{
              backgroundColor: '#C9AE7A',
              backgroundImage: 'linear-gradient(to right, #C9AE7A 50%, transparent 50%)',
              backgroundSize: '5px 1px',
            }}
          />
          <span className="text-text-2 font-medium">KDV dahil</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Donut Chart
// ─────────────────────────────────────────────────────────────
function DonutChart({
  deductions, total,
}: {
  deductions: Array<{ deduction_type: string; total: number }>;
  total: number;
}) {
  if (!deductions.length || !total) {
    return (
      <div className="h-60 flex items-center justify-center text-text-3 text-sm">
        Bu dönem için kesinti verisi yok.
      </div>
    );
  }

  const colors = [
    '#1E40FF', '#3B82F6', '#C9AE7A', '#EF4444', '#F59E0B', '#94A3B8',
  ];

  return (
    <div>
      <div className="h-56 flex items-center justify-center relative mb-4">
        <svg width="180" height="180" viewBox="0 0 180 180">
          {deductions.map((d, i) => {
            const startAngle = deductions.slice(0, i).reduce((s, x) => s + (x.total / total) * 360, 0);
            const endAngle = startAngle + (d.total / total) * 360;
            const radius = 70;

            const startRad = (startAngle - 90) * (Math.PI / 180);
            const endRad = (endAngle - 90) * (Math.PI / 180);

            const x1 = 90 + radius * Math.cos(startRad);
            const y1 = 90 + radius * Math.sin(startRad);
            const x2 = 90 + radius * Math.cos(endRad);
            const y2 = 90 + radius * Math.sin(endRad);

            const largeArc = endAngle - startAngle > 180 ? 1 : 0;

            return (
              <path
                key={i}
                d={`M 90 90 L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`}
                fill={colors[i % colors.length]}
              />
            );
          })}
          <circle cx="90" cy="90" r="45" fill="white" />
        </svg>

        <div className="absolute text-center">
          <div className="text-xs text-text-3 font-semibold uppercase">Toplam</div>
          <div className="font-display text-2xl font-bold text-text">{(total / 1_000_000).toFixed(2)}M ₺</div>
          <div className="text-xs text-text-3 mt-1">{deductions.length} tip</div>
        </div>
      </div>

      <div className="space-y-2">
        {deductions.slice(0, 6).map((d, i) => (
          <div key={i} className="flex items-center gap-3 py-1.5 border-b border-border last:border-0">
            <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: colors[i % colors.length] }} />
            <span className="text-sm text-text-2 font-medium flex-1">{d.deduction_type}</span>
            <span className="text-sm font-semibold text-text num">{(d.total / 1000).toFixed(0)}K ₺</span>
            <span className="text-xs text-text-3 w-12 text-right">{((d.total / total) * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Efficiency Card (Sabit Maliyet panel)
// ─────────────────────────────────────────────────────────────
function EfficiencyCard({
  initials, name, role, trend, barPercent, salary, recovery, netCost,
  cover, packages, workHours, gradientFrom, gradientTo, isJoker,
}: {
  initials: string;
  name: string;
  role: string;
  trend: string;
  barPercent: number;
  salary: string;
  recovery: string;
  netCost: string;
  cover: string;
  packages: string;
  workHours: string;
  gradientFrom: string;
  gradientTo: string;
  isJoker?: boolean;
}) {
  const barColor = isJoker
    ? 'from-amber-600 to-amber-400'
    : 'from-green-500 to-green-400';

  return (
    <div className="border border-border rounded-2xl p-4 bg-gradient-to-b from-bg-surface to-cream-50 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-brand to-brand-light" />

      <div className="flex items-start gap-3 mb-3">
        <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${gradientFrom} ${gradientTo} text-white flex items-center justify-center font-bold text-sm`}>
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-sm text-text truncate">{name}</div>
          <div className="text-xs text-text-3">{role}</div>
          <div className="text-xs font-semibold text-green-600 mt-0.5">{trend}</div>
        </div>
      </div>

      <div className="mb-3">
        <div className="h-7 bg-bg-surface2 border border-border-strong rounded-lg relative overflow-hidden mb-1">
          <div
            className={`h-full bg-gradient-to-r ${barColor} rounded-lg flex items-center justify-end px-2`}
            style={{ width: `${barPercent}%` }}
          >
            <span className="text-white text-xs font-bold font-mono">−%{barPercent.toFixed(1)}</span>
          </div>
        </div>
        <div className="flex justify-between text-xs text-text-3 px-1 font-mono text-[10px]">
          <span>0 ₺</span>
          <span>{isJoker ? '88K ₺' : '100K ₺'}</span>
        </div>
      </div>

      <div className="space-y-1.5 py-3 border-y border-border text-xs mb-3">
        <div className="flex justify-between">
          <span className="text-text-2">Sabit maaş{isJoker ? ' (KDV dahil)' : ''}</span>
          <span className="font-mono font-semibold text-text">{salary}</span>
        </div>
        <div className="flex justify-between text-green-600">
          <span>Cover ile geri kazanım</span>
          <span className="font-mono font-semibold">{recovery}</span>
        </div>
        <div className="flex justify-between font-bold pt-1.5 border-t border-border mt-1.5">
          <span>Net maliyet</span>
          <span className="font-mono text-brand">{netCost}</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="text-center bg-bg-surface2 rounded-lg py-1.5">
          <div className="font-mono font-bold text-sm">{cover}</div>
          <div className="text-xs text-text-3 font-semibold uppercase tracking-wider">Cover</div>
        </div>
        <div className="text-center bg-bg-surface2 rounded-lg py-1.5">
          <div className="font-mono font-bold text-sm">{packages}</div>
          <div className="text-xs text-text-3 font-semibold uppercase tracking-wider">Paket</div>
        </div>
        <div className="text-center bg-bg-surface2 rounded-lg py-1.5">
          <div className="font-mono font-bold text-sm">{workHours}</div>
          <div className="text-xs text-text-3 font-semibold uppercase tracking-wider">Çalışma</div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Mock pipeline pieces
// ─────────────────────────────────────────────────────────────
function FunnelStage({ stage, count, value, sub, percent, color }: any) {
  return (
    <div className="bg-gradient-to-br from-brand-mist to-white border border-brand-border rounded-2xl p-4">
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs font-bold text-text-3 uppercase tracking-wider">{stage}</span>
        <span className={`${color} text-white text-xs font-bold px-2 py-0.5 rounded-full font-mono`}>
          {count}
        </span>
      </div>
      <div className="font-display text-2xl font-bold text-text mb-1">{value}</div>
      <div className="text-xs text-text-3 mb-3">{sub}</div>
      <div className="h-1 bg-bg-surface2 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function TimelineItem({ date, amount, text, isFirst, isFinal }: any) {
  return (
    <div className="relative pl-6 pb-4 last:pb-0">
      <div className="absolute left-0 top-2 w-4 h-4 rounded-full border-3 border-white" style={{
        background: isFirst ? '#0F52BA' : isFinal ? '#C9AE7A' : '#3B7BCF',
        boxShadow: isFirst ? '0 0 0 2px #E8EFFB' : '0 0 0 2px white',
      }} />
      <div className="flex justify-between items-baseline gap-2">
        <span className="font-semibold text-text text-sm">{date}</span>
        <span className="font-display font-bold" style={{ color: isFinal ? '#10B981' : '#0F52BA' }}>
          {amount}
        </span>
      </div>
      <div className="text-xs text-text-3 mt-0.5">{text}</div>
    </div>
  );
}
