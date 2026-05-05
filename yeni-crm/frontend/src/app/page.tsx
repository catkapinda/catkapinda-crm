import {
  ArrowDownRight, ArrowUpRight, Calendar, AlertCircle, TrendingUp,
  Plus, Search, ChevronDown, Users, Store, CalendarDays,
} from 'lucide-react';

import { Sidebar } from '@/components/sidebar';
import {
  getDashboardSummary,
  getSidebarCounts,
  getDeductionSummaryByType,
  getDashboardAnalytics,
  getManagementSummary,
  type DashboardSummary,
  type SidebarCounts,
  type DashboardAnalytics,
  type ManagementMember,
} from '@/lib/api';

export const dynamic = 'force-dynamic';

// MOCK / DEMO — gerçek pipeline modülü gelene kadar tasarım gösterimi
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

export default async function DashboardPage() {
  let summary: DashboardSummary | null = null;
  let counts: SidebarCounts | null = null;
  let deductions: Array<{ deduction_type: string; total: number }> = [];
  let analytics: DashboardAnalytics | null = null;
  let management: ManagementMember[] = [];
  let error: string | null = null;

  try {
    [summary, counts, analytics, management] = await Promise.all([
      getDashboardSummary('2026-03'),
      getSidebarCounts().catch(() => null),
      getDashboardAnalytics('2026-03'),
      getManagementSummary('2026-03').catch(() => []),
    ]);
    deductions = (await getDeductionSummaryByType('2026-03')).map((d) => ({
      deduction_type: d.deduction_type,
      total: d.total,
    }));
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  const totalDeductions = deductions.reduce((s, d) => s + d.total, 0);

  // Sabit Maliyet Verimliliği — gerçek management verisinden hesapla
  // Backend mantığı: recovery_amount = cover_hours * 200 + cover_packages * 25
  // recovery_pct = min(1.0, recovery_amount / salary)
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

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen bg-bg">
      <Sidebar active="dashboard" counts={counts} />
      <main className="overflow-auto">
        <div className="px-9 py-7 max-w-[1500px] mx-auto">
          {/* HEADER */}
          <div className="flex justify-between items-start mb-8 gap-5">
            <div>
              <div className="text-[13px] text-text-3 font-medium mb-1.5">
                İyi akşamlar, <span className="font-semibold text-brand">Ebru</span>
              </div>
              <h1 className="font-display text-3xl font-semibold tracking-tight leading-tight text-text mb-1.5">
                Genel Bakış
              </h1>
              <div className="text-text-3 text-sm font-medium">
                {summary
                  ? `Mart 2026 · ${summary.puantaj_entries.toLocaleString('tr-TR')} puantaj girişi · ${summary.active_restaurants} aktif restoran`
                  : '— veri yükleniyor —'}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="bg-bg-surface border border-border rounded-lg px-3 py-2 flex items-center gap-2 text-sm text-text-3">
                <Search className="w-4 h-4" />
                <span>Ara…</span>
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
                <AlertCircle className="w-5 h-5" strokeWidth={1.8} />
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

          {/* KPI ROW */}
          <div className="grid grid-cols-[1.4fr_1fr_1fr_1fr] gap-3.5 mb-7">
            {/* Hero KPI */}
            <KpiCardHero analytics={analytics} />

            {/* Regular KPIs */}
            <KpiCard
              label="Tahmini Marj"
              icon={<TrendingUp className="w-3.5 h-3.5" />}
              iconBg="bg-green-50 text-green-600"
              value={analytics ? analytics.margin_pct.toFixed(1) : '—'}
              valueSuffix="%"
              trend={{ direction: 'up', value: '8.7%', label: 'brüt fatura - kesinti' }}
            />

            <KpiCard
              label="Kesintiler"
              icon={<ArrowDownRight className="w-3.5 h-3.5" />}
              iconBg="bg-orange-50 text-orange-700"
              value={summary ? ((summary.total_deductions / 1_000_000).toFixed(2)) : '—'}
              valueSuffix="M ₺"
              trend={{ direction: 'down', value: '3.2%', label: `${deductions.length} kesinti tipi` }}
            />

            <KpiCard
              label="Aktif Personel"
              icon={<Users className="w-3.5 h-3.5" />}
              iconBg="bg-brand-soft text-brand"
              value={summary ? summary.active_personnel.toString() : '—'}
              trend={{ direction: 'up', value: '+4', label: summary ? `${summary.kurye_count} kurye · ${summary.joker_count} joker` : '' }}
            />
          </div>

          {/* Sabit Maliyet Verimliliği Panel — gerçek management verisinden */}
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
                {/* Toplam Verimlilik */}
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

          {/* CHARTS ROW */}
          <div className="grid grid-cols-[1.6fr_1fr] gap-4 mb-6">
            {/* Revenue Chart */}
            <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6">
              <div className="mb-4">
                <h2 className="font-display text-lg font-semibold text-text">Aylık Fatura Trendi</h2>
                <p className="text-sm text-text-3">Son 6 ay · KDV hariç</p>
              </div>
              <RevenueLargeChart data={analytics?.revenue_trend || []} />
            </div>

            {/* Deductions Donut */}
            <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6">
              <div className="mb-4">
                <h2 className="font-display text-lg font-semibold text-text">Kesinti Dağılımı</h2>
                <p className="text-sm text-text-3">Mart 2026 · {analytics?.deduction_breakdown.length || 0} kayıt</p>
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

          {/* Restaurant Network */}
          <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6 mb-6">
            <div className="mb-4">
              <h2 className="font-display text-lg font-semibold text-text">Restoran Performans Ağı</h2>
              <p className="text-sm text-text-3">balon büyüklüğü = aylık fatura · pozisyon = anlaşma tipi · tıkla detay</p>
            </div>
            <NetworkVisualization restaurants={analytics?.by_restaurant || []} />
          </div>

          {/* Sales Pipeline — DEMO / örnek tasarım, gerçek lead modülü gelene kadar */}
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

            {/* Funnel Summary */}
            <div className="grid grid-cols-5 gap-3 mb-6">
              <FunnelStage stage="Görüşme" count="3" value="~470K ₺" sub="tahmini aylık değer" percent={100} color="bg-brand" />
              <FunnelStage stage="Teklif" count="2" value="~280K ₺" sub="teklif iletilmiş" percent={80} color="bg-brand-light" />
              <FunnelStage stage="Müzakere" count="1" value="~190K ₺" sub="aktif görüşme" percent={60} color="bg-cream-400" />
              <FunnelStage stage="Anlaşma" count="2" value="+319K ₺" sub="bu ay kazanılan" percent={40} color="bg-green-500" />
              <FunnelStage stage="Olumsuz" count="4" value="~410K ₺" sub="kaçırılan fırsat" percent={25} color="bg-red-500" />
            </div>

            {/* Kanban */}
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

          {/* Bottom 3 Grid — DEMO içerikler, gerçek modüller hazır olunca dolacak */}
          <div className="grid grid-cols-3 gap-6 mb-12">
            {/* Expected Payments */}
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
                  <p className="text-xs text-text-3">3 ödeme noktası · Nisan 2026</p>
                </div>
              </div>

              <div className="space-y-4 text-sm">
                <TimelineItem date="15 Nis" amount="2,7M ₺" text="Mart kuryeleri maaş ödemesi" isFirst />
                <TimelineItem date="25 Nis" amount="~800K ₺" text="Nisan avans dağıtımı" />
                <TimelineItem date="30 Nis" amount="+5,3M ₺" text="Nisan restoran fatura kesimi" isFinal />
              </div>
            </div>

            {/* Attention Required */}
            <div className="bg-bg-surface border border-border rounded-2xl shadow-md p-6 relative">
              <span className="absolute top-3 right-3 px-2 py-0.5 rounded-md bg-yellow-100 text-yellow-800 text-[9.5px] font-bold uppercase tracking-wider border border-yellow-200">
                DEMO
              </span>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-yellow-500 to-yellow-400 flex items-center justify-center text-white">
                  <AlertCircle className="w-5 h-5" strokeWidth={2.2} />
                </div>
                <div>
                  <h3 className="font-display text-base font-semibold">Dikkat İstenen</h3>
                  <p className="text-xs text-text-3">6 aksiyon bekliyor · 1 acil</p>
                </div>
              </div>

              <div className="space-y-2 text-sm">
                <AlertItem
                  title="Avans onayı bekliyor"
                  subtitle="Eren Kayır, Yusuf Erdal, Ali Cem"
                  badge="3"
                  bgColor="bg-brand-mist"
                  borderColor="border-brand"
                />
                <AlertItem
                  title="Köroğlu Pide kurye eksik"
                  subtitle="3/6 atanmış · 2 hafta sürdü"
                  badge="3/6"
                  badgeColor="text-red-600"
                  bgColor="bg-red-50"
                  borderColor="border-red-500"
                  isUrgent
                />
                <AlertItem
                  title="İdari ceza karar bekliyor"
                  subtitle="2 dosya · son 5 günde"
                  badge="2"
                  badgeColor="text-text"
                  bgColor="bg-cream-50"
                  borderColor="border-cream-400"
                />
              </div>
            </div>

            {/* YoY Growth */}
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
                  <p className="text-xs text-text-3">Mart 2025 → Mart 2026</p>
                </div>
              </div>

              <div className="mb-4">
                <div className="font-display text-4xl font-bold text-green-600 mb-1">+%28</div>
                <p className="text-sm text-text-3 font-semibold">YoY büyüme</p>
              </div>

              <div className="mb-4">
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

              <div className="border-t border-border pt-3 text-xs">
                <div className="flex justify-between mb-2">
                  <div>
                    <div className="text-text-3 font-medium mb-1">Geçen yıl Mart</div>
                    <div className="font-mono font-bold">3.404.250 ₺</div>
                  </div>
                  <div className="text-right">
                    <div className="text-text-3 font-medium mb-1">Bu yıl Mart</div>
                    <div className="font-mono font-bold text-green-600">4.360.733 ₺</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Components
// ─────────────────────────────────────────────────────────────

function KpiCardHero({ analytics }: { analytics: DashboardAnalytics | null }) {
  if (!analytics) return (
    <div className="rounded-2xl p-6 shadow-md border-0 overflow-hidden relative group" style={{
      background: 'linear-gradient(135deg, #0A3F8F 0%, #0F52BA 35%, #3B7BCF 70%, #E8D9B5 100%)',
    }}>
      <div className="text-xs font-bold uppercase tracking-widest text-white/85 mb-4">Toplam Fatura · KDV hariç</div>
      <div className="font-display text-4xl font-bold text-white mb-1 num">—</div>
    </div>
  );

  return (
    <div className="rounded-2xl p-6 shadow-md border-0 overflow-hidden relative group" style={{
      background: 'linear-gradient(135deg, #0A3F8F 0%, #0F52BA 35%, #3B7BCF 70%, #E8D9B5 100%)',
    }}>
      {/* Radial gradients */}
      <div className="absolute inset-0 opacity-30 mix-blend-overlay pointer-events-none" style={{
        backgroundImage: 'radial-gradient(900px circle at 90% -10%, rgba(248, 242, 230, 0.35), transparent 45%), radial-gradient(700px circle at 110% 60%, rgba(232, 217, 181, 0.5), transparent 55%), radial-gradient(500px circle at 10% 100%, rgba(0,0,0,0.18), transparent 50%)',
      }} />

      {/* Mesh pattern */}
      <div className="absolute inset-0 opacity-[0.06] pointer-events-none" style={{
        backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0)',
        backgroundSize: '16px 16px',
      }} />

      <div className="relative z-10">
        <div className="text-xs font-bold uppercase tracking-widest text-white/85 mb-4">
          Toplam Fatura · KDV hariç
        </div>
        <div className="font-display text-4xl font-bold text-white mb-1 num">
          {(analytics.invoiced_kdv_haric / 1_000_000).toFixed(2)}
          <span className="text-lg font-medium text-white/70 ml-2">M ₺</span>
        </div>
        <div className="text-xs text-white/85 mt-4 flex items-center gap-2">
          <span className="inline-flex items-center gap-1 bg-white/22 text-white px-2 py-0.5 rounded font-semibold text-[11px]">
            <ArrowUpRight className="w-3 h-3" /> 12.4%
          </span>
          <span>geçen aya göre</span>
        </div>
        <div className="text-xs text-white/70 mt-3 font-medium">
          +KDV: {(analytics.invoiced_kdv_dahil / 1_000_000).toFixed(2)}M ₺ · Tevkifat: {(analytics.tevkifat_total / 1_000_000).toFixed(2)}M ₺
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label, icon, iconBg, value, valueSuffix, trend,
}: {
  label: string;
  icon: React.ReactNode;
  iconBg: string;
  value: string;
  valueSuffix?: string;
  trend?: { direction: 'up' | 'down'; value: string; label: string };
}) {
  const trendBg = trend?.direction === 'up' ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600';
  const TrendIcon = trend?.direction === 'up' ? ArrowUpRight : ArrowDownRight;

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
      {trend && (
        <div className="mt-3 flex items-center gap-2 text-xs">
          <span className={`inline-flex items-center gap-1 ${trendBg} px-2 py-1 rounded font-semibold`}>
            <TrendIcon className="w-3 h-3" /> {trend.value}
          </span>
          <span className="text-text-3">{trend.label}</span>
        </div>
      )}
    </div>
  );
}

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

function RevenueLargeChart({ data: providedData }: { data?: Array<{ period: string; invoiced: number; net_paid: number }> }) {
  // Transform backend data or use fallback
  const data = (providedData || []).map(d => {
    const month = d.period.split('-')[1];
    const monthMap: Record<string, string> = {
      '10': 'Eki', '11': 'Kas', '12': 'Ara', '01': 'Oca', '02': 'Şub', '03': 'Mar',
      '04': 'Nis', '05': 'May', '06': 'Haz', '07': 'Tem', '08': 'Ağu', '09': 'Eyl'
    };
    return {
      month: monthMap[month] || month,
      withoutVat: d.invoiced || 0,
      withVat: (d.invoiced || 0) * 1.2,
    };
  });

  if (data.length === 0) {
    // Fallback mock data
    const fallback = [
      { month: 'Eki', withoutVat: 3120000, withVat: 3744000 },
      { month: 'Kas', withoutVat: 3380000, withVat: 4056000 },
      { month: 'Ara', withoutVat: 3680000, withVat: 4416000 },
      { month: 'Oca', withoutVat: 3850000, withVat: 4620000 },
      { month: 'Şub', withoutVat: 3880000, withVat: 4656000 },
      { month: 'Mar', withoutVat: 4360733, withVat: 5232880 },
    ];
    data.push(...fallback);
  }

  const maxVal = 5232880;
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

        {/* Grid lines */}
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <line key={i} x1="0" y1={(i * h) / 5 + 20} x2="600" y2={(i * h) / 5 + 20} stroke="#ECEEF3" strokeWidth="1" />
        ))}

        {/* Primary line (without VAT) */}
        <polyline
          points={data.map((d, i) => `${(i / (data.length - 1)) * 600},${240 - (d.withoutVat / maxVal) * 200}`).join(' ')}
          fill="none"
          stroke="#1E40FF"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Area under primary line */}
        <path
          d={`M ${data.map((d, i) => `${(i / (data.length - 1)) * 600},${240 - (d.withoutVat / maxVal) * 200}`).join(' L ')} L 600,240 L 0,240 Z`}
          fill="url(#revGrad)"
        />

        {/* Secondary line (with VAT - dashed) */}
        <polyline
          points={data.map((d, i) => `${(i / (data.length - 1)) * 600},${240 - (d.withVat / maxVal) * 200}`).join(' ')}
          fill="none"
          stroke="#C9AE7A"
          strokeWidth="1.8"
          strokeDasharray="5,5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* X-axis labels */}
        {data.map((d, i) => (
          <text key={i} x={(i / (data.length - 1)) * 600} y="270" textAnchor="middle" fontSize="11" fill="#8B92A7" fontWeight="500">
            {d.month}
          </text>
        ))}

        {/* Y-axis labels */}
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <text key={i} x="5" y={(i * h) / 5 + 25} fontSize="11" fill="#8B92A7" textAnchor="start">
            {((5 - i) * 1).toFixed(1)}M ₺
          </text>
        ))}
      </svg>

      <div className="relative z-10 mt-20 px-4 flex justify-end items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-brand" />
          <span className="text-text-2 font-medium">KDV hariç</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5" style={{ backgroundColor: '#C9AE7A', backgroundImage: 'linear-gradient(to right, #C9AE7A 50%, transparent 50%)', backgroundSize: '5px 1px' }} />
          <span className="text-text-2 font-medium">KDV dahil</span>
        </div>
      </div>
    </div>
  );
}

function DonutChart({ deductions, total }: { deductions: Array<{ deduction_type: string; total: number }>; total: number }) {
  if (!deductions.length || !total) {
    return (
      <div className="h-60 flex items-center justify-center text-text-3">
        Veri yok
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

          {/* Inner circle for donut */}
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

function NetworkVisualization({ restaurants }: { restaurants?: Array<{ id: number; brand: string; branch: string; courier_count: number; invoiced: number; pricing_model: string }> }) {
  // For now, keep the mock visualization structure but data would be rendered with real values
  // In production, this would dynamically position bubbles based on pricing_model and size by invoiced
  return (
    <div className="relative w-full bg-gradient-to-b from-bg-surface to-cream-50 rounded-xl p-6 min-h-96">
      <svg width="100%" height="360" viewBox="0 0 800 360" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="netLineDash" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0F52BA" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#0F52BA" stopOpacity="0.04" />
          </linearGradient>
        </defs>

        {/* Connector lines */}
        {[
          { x1: '50%', y1: '22%', x2: '80%', y2: '46%' },
          { x1: '20%', y1: '38%', x2: '50%', y2: '22%' },
          { x1: '50%', y1: '22%', x2: '36%', y2: '76%' },
          { x1: '80%', y1: '46%', x2: '66%', y2: '80%' },
          { x1: '20%', y1: '38%', x2: '12%', y2: '70%' },
          { x1: '50%', y1: '22%', x2: '62%', y2: '52%' },
          { x1: '62%', y1: '52%', x2: '66%', y2: '80%' },
          { x1: '66%', y1: '80%', x2: '90%', y2: '82%' },
        ].map((line, i) => (
          <line
            key={i}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="url(#netLineDash)"
            strokeWidth="1.5"
            strokeDasharray="3,4"
          />
        ))}
      </svg>

      {/* Bubbles overlay */}
      <div className="absolute inset-0 p-6">
        <NetworkBubble left="50%" top="22%" size="xl" name="Quick China" subtitle="Ataşehir" value="492K ₺" />
        <NetworkBubble left="80%" top="46%" size="lg" name="Köroğlu Pide" subtitle="Merkez" value="365K ₺" terra />
        <NetworkBubble left="20%" top="38%" size="lg" name="SushiCo" subtitle="Sancaktepe" value="358K ₺" />
        <NetworkBubble left="62%" top="52%" size="md" name="Quick China" subtitle="Suadiye" value="351K ₺" />
        <NetworkBubble left="36%" top="76%" size="md" name="SushiCo" subtitle="Beyoğlu" value="346K ₺" />
        <NetworkBubble left="12%" top="70%" size="md" name="Doğu" subtitle="Otomotiv" value="334K ₺" />
        <NetworkBubble left="66%" top="80%" size="sm" name="SushiCo" subtitle="Çengelköy" value="286K ₺" />
        <NetworkBubble left="90%" top="82%" size="sm" name="SC" subtitle="Petshop" value="79K ₺" cream />
      </div>

      <div className="flex gap-4 mt-6 flex-wrap text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: 'linear-gradient(135deg, #0A3F8F, #0F52BA)' }} />
          <span className="text-text-2">Saat + Prim · Saatlik</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: 'linear-gradient(135deg, #1B4FAB, #3B7BCF)' }} />
          <span className="text-text-2">Eşikli</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: 'linear-gradient(135deg, #C9AE7A, #E8D9B5)' }} />
          <span className="text-text-2">Aylık Sabit</span>
        </div>
        <div className="ml-auto text-text-3">+ 10 restoran daha</div>
      </div>
    </div>
  );
}

function NetworkBubble({ left, top, size, name, subtitle, value, terra, cream }: any) {
  const sizeMap = {
    xl: 'w-32 h-32 text-lg',
    lg: 'w-28 h-28 text-base',
    md: 'w-24 h-24 text-sm',
    sm: 'w-20 h-20 text-xs',
  };

  const bgGradient = cream
    ? 'linear-gradient(135deg, #C9AE7A, #E8D9B5)'
    : terra
    ? 'linear-gradient(135deg, #1B4FAB, #3B7BCF)'
    : 'linear-gradient(135deg, #0A3F8F, #0F52BA)';

  const textColor = cream ? 'text-text' : 'text-white';

  return (
    <div className="absolute" style={{ left, top, transform: 'translate(-50%, -50%)' }}>
      <div
        className={`${sizeMap[size as keyof typeof sizeMap]} rounded-full border-4 border-white shadow-lg flex flex-col items-center justify-center font-bold ${textColor}`}
        style={{ background: bgGradient }}
      >
        <div className="text-center px-2 leading-tight">
          {name}
          <br />
          {subtitle}
        </div>
        <div className="text-xs mt-1 font-mono opacity-90">{value}</div>
      </div>
    </div>
  );
}

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

function AlertItem({ title, subtitle, badge, badgeColor, bgColor, borderColor, isUrgent }: any) {
  return (
    <div className={`${bgColor} border-l-3 ${borderColor} px-3 py-2.5 rounded-lg flex justify-between items-start gap-2`}>
      <div>
        <div className="font-semibold text-text text-xs">
          {title}
          {isUrgent && <span className="bg-red-600 text-white text-[9px] font-bold px-1.5 py-0.5 rounded ml-2">ACİL</span>}
        </div>
        <div className="text-xs text-text-3 mt-0.5">{subtitle}</div>
      </div>
      <span className={`${badgeColor} font-bold text-xs px-2 py-1 rounded-full flex-shrink-0`}>
        {badge}
      </span>
    </div>
  );
}
