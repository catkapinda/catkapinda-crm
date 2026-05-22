'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Activity, AlertTriangle, BarChart3, Building2, Calendar, Check,
  ChevronDown, ChevronRight, Loader2, Mail, Package, Send, Sparkles,
  TrendingDown, TrendingUp, Users, X,
  type LucideIcon,
} from 'lucide-react';

import type {
  AiInsightCard,
  AiInsightsResponse,
  RestaurantReports,
  SidebarCounts,
} from '@/lib/api';
import {
  getRestaurantReportPdfUrl,
  getRestaurantsAiInsights,
} from '@/lib/api';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string): string {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

/**
 * CRM Mart 2026'da başlatıldı. Daha eski dönem seçmek anlamlı değil.
 * Bu helper, bugünden geri 6 aya kadar inip MIN_PERIOD'da duran liste döner.
 */
const MIN_PERIOD = '2026-03';

function recentPeriodOptions(maxCount = 6): { value: string; label: string }[] {
  const now = new Date();
  const out: { value: string; label: string }[] = [];
  for (let i = 0; i < maxCount; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    out.push({ value, label: `${TR_MONTHS[d.getMonth()]} ${d.getFullYear()}` });
    if (value === MIN_PERIOD) break;
  }
  return out;
}

function m(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function tr(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function getTurnoverColor(pct: number): string {
  if (pct < 5) return 'bg-green-100 text-green-800';
  if (pct < 15) return 'bg-emerald-100 text-emerald-800';
  if (pct < 30) return 'bg-yellow-100 text-yellow-800';
  if (pct < 50) return 'bg-orange-100 text-orange-800';
  return 'bg-red-100 text-red-800';
}

// ─────────────────────────────────────────────────────────────
// Mail/PDF modal state — view içinde tek kanal (her tabloya prop drilling
// yerine ortak handler taşıyoruz).
// ─────────────────────────────────────────────────────────────
type ReportTarget = {
  restaurantId: number;
  brand: string;
  branch: string;
};

export function RaporlarView({
  reports,
  period,
  counts,
  aiInsights = null,
}: {
  reports: RestaurantReports;
  period: string;
  counts?: SidebarCounts | null;
  aiInsights?: AiInsightsResponse | null;
}) {
  void counts;
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'turnover' | 'efficiency' | 'cost' | 'growth'>(
    'turnover'
  );
  const [sortKey, setSortKey] = useState<string>('');
  const [sortDesc, setSortDesc] = useState(false);

  // PDF modal state
  const [reportTarget, setReportTarget] = useState<ReportTarget | null>(null);
  const openReport = (t: ReportTarget) => setReportTarget(t);
  const closeReport = () => setReportTarget(null);

  // Period selector
  const periodOptions = useMemo(() => recentPeriodOptions(6), []);
  const [periodPickerOpen, setPeriodPickerOpen] = useState(false);
  function changePeriod(next: string) {
    setPeriodPickerOpen(false);
    if (next === period) return;
    router.push(`/raporlar?period=${next}`);
  }

  // KPI Kartları
  const totalPackages = useMemo(() => {
    return reports.package_growth.reduce((s, r) => s + r.current_packages, 0);
  }, [reports.package_growth]);

  const totalBilling = useMemo(() => {
    return reports.cost_per_package.by_restaurant.reduce((s, r) => s + r.billing_excl_vat, 0);
  }, [reports.cost_per_package]);

  const avgPackageCost = reports.cost_per_package.overall;

  // Ortalama verim (tüm kuryeler)
  const avgEfficiency = useMemo(() => {
    if (reports.courier_efficiency.length === 0) return 0;
    const sum = reports.courier_efficiency.reduce((s, c) => s + c.packages_per_hour, 0);
    return sum / reports.courier_efficiency.length;
  }, [reports.courier_efficiency]);

  return (
    <div className="flex-1 flex flex-col gap-6 p-6">
      {/* ────────────────────────────────────────────────────────────
          HERO Header
         ──────────────────────────────────────────────────────────── */}
      <section className="relative z-20 rounded-3xl mb-2 shadow-lg">
        {/* Dekoratif katman — overflow-hidden burada (period dropdown serbest) */}
        <div className="absolute inset-0 overflow-hidden rounded-3xl pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-br from-brand-dark via-brand to-blue-600" />
          <div className="absolute inset-0 opacity-30 mix-blend-overlay"
            style={{
              backgroundImage:
                'radial-gradient(circle at 20% 20%, rgba(255,255,255,.4) 0%, transparent 40%), radial-gradient(circle at 80% 70%, rgba(255,200,100,.3) 0%, transparent 50%)',
            }}
          />
          <div className="absolute inset-0 opacity-[0.07]"
            style={{
              backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />
        </div>

        <div className="relative px-7 py-7 text-white flex items-start justify-between gap-6">
          <div>
            <div className="text-[11px] font-medium tracking-[0.2em] uppercase text-white/70 mb-2 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-yellow-300 animate-pulse" />
              Finans
            </div>
            <h1 className="text-4xl font-bold mb-1">Restoran Performans Raporları</h1>
            <div className="text-white/80">
              {formatPeriod(period)} · {reports.turnover.length} restoran
            </div>
          </div>

          {/* Period selector — hero üst-sağ köşede */}
          <div className="relative">
            <button
              onClick={() => setPeriodPickerOpen((v) => !v)}
              className="px-3.5 py-2 rounded-lg bg-white/15 backdrop-blur-sm border border-white/25 text-white text-xs font-semibold hover:bg-white/25 transition inline-flex items-center gap-2"
            >
              <Calendar className="w-3.5 h-3.5" strokeWidth={2.2} />
              <span>{formatPeriod(period)}</span>
              <ChevronDown
                className={`w-3.5 h-3.5 transition-transform ${
                  periodPickerOpen ? 'rotate-180' : ''
                }`}
                strokeWidth={2.4}
              />
            </button>
            {periodPickerOpen && (
              <>
                <div
                  className="fixed inset-0 z-30"
                  onClick={() => setPeriodPickerOpen(false)}
                />
                <div className="absolute right-0 mt-1.5 z-40 w-52 bg-white border border-border rounded-xl shadow-2xl overflow-hidden">
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
                            : 'text-text-2 hover:bg-bg-surface2'
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
        </div>
      </section>

      {/* ────────────────────────────────────────────────────────────
          KPI Cards
         ──────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Toplam Paket"
          value={tr(totalPackages, 0)}
          icon={Package}
          color="bg-blue-50 text-brand"
        />
        <KPICard
          title="Toplam Fatura (KDV H.)"
          value={m(totalBilling)}
          icon={BarChart3}
          color="bg-emerald-50 text-emerald-700"
        />
        <KPICard
          title="Ort. Paket Başı Maliyet"
          value={m(avgPackageCost)}
          icon={Building2}
          color="bg-amber-50 text-amber-700"
        />
        <KPICard
          title="Ort. Verim (Paket/Saat)"
          value={tr(avgEfficiency, 2)}
          icon={Activity}
          color="bg-purple-50 text-purple-700"
        />
      </div>

      {/* ────────────────────────────────────────────────────────────
          AI Insights Hero — Claude'un yorumladığı 4 kartlık özet
         ──────────────────────────────────────────────────────────── */}
      <RestaurantsAiHero
        initial={aiInsights}
        period={period}
      />

      {/* ────────────────────────────────────────────────────────────
          Tabs
         ──────────────────────────────────────────────────────────── */}
      <div className="flex gap-2 border-b border-border">
        <TabButton
          label="Turn Over"
          active={activeTab === 'turnover'}
          onClick={() => setActiveTab('turnover')}
        />
        <TabButton
          label="Saat-Paket Verimi"
          active={activeTab === 'efficiency'}
          onClick={() => setActiveTab('efficiency')}
        />
        <TabButton
          label="Paket Başı Maliyet"
          active={activeTab === 'cost'}
          onClick={() => setActiveTab('cost')}
        />
        <TabButton
          label="Aylık Büyüme"
          active={activeTab === 'growth'}
          onClick={() => setActiveTab('growth')}
        />
      </div>

      {/* Content */}
      <div>
        {activeTab === 'turnover' && (
          <TurnoverTable data={reports.turnover} onOpenReport={openReport} />
        )}
        {activeTab === 'efficiency' && (
          <EfficiencyTable data={reports.courier_efficiency} />
        )}
        {activeTab === 'cost' && (
          <CostPerPackageSection data={reports.cost_per_package} onOpenReport={openReport} />
        )}
        {activeTab === 'growth' && (
          <GrowthTable data={reports.package_growth} onOpenReport={openReport} />
        )}
      </div>

      {/* PDF Preview + Maile Gönder Modal */}
      {reportTarget && (
        <ReportPreviewModal
          target={reportTarget}
          period={period}
          onClose={closeReport}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────

function KPICard({
  title, value, icon: Icon, color,
}: {
  title: string;
  value: string;
  icon: typeof Package;
  color: string;
}) {
  return (
    <div className="bg-white rounded-2xl border border-border p-6 shadow-sm hover:shadow-md transition">
      <div className={`inline-flex p-3 rounded-xl ${color} mb-4`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="text-sm text-text-3 font-medium mb-1">{title}</div>
      <div className="text-2xl font-bold text-text">{value}</div>
    </div>
  );
}

function TabButton({
  label, active, onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-3 font-medium text-sm transition-colors ${
        active
          ? 'text-brand border-b-2 border-brand'
          : 'text-text-3 hover:text-text-2 border-b-2 border-transparent'
      }`}
    >
      {label}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// TURNOVER TABLE
// ─────────────────────────────────────────────────────────────

function TurnoverTable({
  data,
  onOpenReport,
}: {
  data: RestaurantReports['turnover'];
  onOpenReport: (t: ReportTarget) => void;
}) {
  const [sort, setSort] = useState({ key: 'turnover_pct', desc: true });

  const sorted = useMemo(() => {
    const s = [...data];
    s.sort((a, b) => {
      let aVal: any = a[sort.key as keyof typeof a];
      let bVal: any = b[sort.key as keyof typeof b];
      const c = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sort.desc ? -c : c;
    });
    return s;
  }, [data, sort]);

  const toggleSort = (key: string) => {
    if (sort.key === key) {
      setSort({ key, desc: !sort.desc });
    } else {
      setSort({ key, desc: true });
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-border overflow-hidden shadow-sm">
      <table className="w-full">
        <thead className="bg-bg-surface2">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
              onClick={() => toggleSort('brand')}>
              <div className="flex items-center gap-2">
                Restoran
                {sort.key === 'brand' && (
                  sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                )}
              </div>
            </th>
            <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
              onClick={() => toggleSort('active_count')}>
              <div className="flex items-center justify-end gap-2">
                Aktif Kurye
                {sort.key === 'active_count' && (
                  sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                )}
              </div>
            </th>
            <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
              onClick={() => toggleSort('started_count')}>
              <div className="flex items-center justify-end gap-2">
                Giriş
                {sort.key === 'started_count' && (
                  sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                )}
              </div>
            </th>
            <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
              onClick={() => toggleSort('exited_count')}>
              <div className="flex items-center justify-end gap-2">
                Çıkış
                {sort.key === 'exited_count' && (
                  sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                )}
              </div>
            </th>
            <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
              onClick={() => toggleSort('turnover_pct')}>
              <div className="flex items-center justify-end gap-2">
                Churn %
                {sort.key === 'turnover_pct' && (
                  sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                )}
              </div>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {sorted.map((row) => (
            <tr key={row.restaurant_id} className="hover:bg-bg-surface2 transition group">
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <div>
                    <div className="text-sm font-medium text-text">{row.brand}</div>
                    {row.branch && <div className="text-xs text-text-3 mt-0.5">{row.branch}</div>}
                  </div>
                  <ReportIconButton
                    onClick={() => onOpenReport({
                      restaurantId: row.restaurant_id,
                      brand: row.brand,
                      branch: row.branch,
                    })}
                  />
                </div>
              </td>
              <td className="px-6 py-4 text-right text-sm font-medium text-text">
                {row.active_count}
              </td>
              <td className="px-6 py-4 text-right text-sm text-text-2">
                {row.started_count > 0 && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-50 text-green-700 rounded-md font-medium">
                    <TrendingUp className="w-3 h-3" />
                    {row.started_count}
                  </span>
                )}
              </td>
              <td className="px-6 py-4 text-right text-sm text-text-2">
                {row.exited_count > 0 && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-50 text-red-700 rounded-md font-medium">
                    <TrendingDown className="w-3 h-3" />
                    {row.exited_count}
                  </span>
                )}
              </td>
              <td className="px-6 py-4 text-right">
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-bold ${getTurnoverColor(row.turnover_pct)}`}>
                  {tr(row.turnover_pct, 1)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// EFFICIENCY TABLE
// ─────────────────────────────────────────────────────────────

function EfficiencyTable({
  data,
}: {
  data: RestaurantReports['courier_efficiency'];
}) {
  const [sort, setSort] = useState({ key: 'packages_per_hour', desc: true });

  const sorted = useMemo(() => {
    const s = [...data];
    s.sort((a, b) => {
      let aVal: any = a[sort.key as keyof typeof a];
      let bVal: any = b[sort.key as keyof typeof b];
      const c = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sort.desc ? -c : c;
    });
    return s;
  }, [data, sort]);

  const toggleSort = (key: string) => {
    if (sort.key === key) {
      setSort({ key, desc: !sort.desc });
    } else {
      setSort({ key, desc: true });
    }
  };

  // Top 10 + Bottom 5
  const top10 = sorted.slice(0, 10);
  const bottom5 = sorted.slice(-5).reverse();

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-border overflow-hidden shadow-sm">
        <div className="px-6 py-4 bg-bg-surface2 border-b border-border">
          <h3 className="text-sm font-bold text-text">En Verimli Kuryeler (Top 10)</h3>
        </div>
        <table className="w-full">
          <thead className="bg-bg-surface2">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-bold text-text-3 uppercase tracking-wider">
                Kurye
              </th>
              <th className="px-6 py-3 text-left text-xs font-bold text-text-3 uppercase tracking-wider">
                Restoran
              </th>
              <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
                onClick={() => toggleSort('packages_per_hour')}>
                <div className="flex items-center justify-end gap-2">
                  Paket/Saat
                  {sort.key === 'packages_per_hour' && (
                    sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                  )}
                </div>
              </th>
              <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider">
                Paket
              </th>
              <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider">
                Saat
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {top10.map((row) => (
              <tr key={row.personnel_id} className="hover:bg-bg-surface2 transition">
                <td className="px-6 py-4">
                  <div className="text-sm font-medium text-text">{row.full_name}</div>
                  <div className="text-xs text-text-3 mt-0.5">{row.person_code}</div>
                </td>
                <td className="px-6 py-4 text-sm text-text-2">{row.rest_brand}</td>
                <td className="px-6 py-4 text-right">
                  <div className="inline-block px-3 py-1 bg-green-50 text-green-700 rounded-full font-bold text-sm">
                    {tr(row.packages_per_hour, 2)}
                  </div>
                </td>
                <td className="px-6 py-4 text-right text-sm text-text-2">{row.packages}</td>
                <td className="px-6 py-4 text-right text-sm text-text-2">{tr(row.hours, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {bottom5.length > 0 && (
        <div className="bg-white rounded-2xl border border-border overflow-hidden shadow-sm">
          <div className="px-6 py-4 bg-bg-surface2 border-b border-border">
            <h3 className="text-sm font-bold text-text">En Düşük Verimli Kuryeler (Bottom 5)</h3>
          </div>
          <table className="w-full">
            <thead className="bg-bg-surface2">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-bold text-text-3 uppercase tracking-wider">
                  Kurye
                </th>
                <th className="px-6 py-3 text-left text-xs font-bold text-text-3 uppercase tracking-wider">
                  Restoran
                </th>
                <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider">
                  Paket/Saat
                </th>
                <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider">
                  Paket
                </th>
                <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider">
                  Saat
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {bottom5.map((row) => (
                <tr key={row.personnel_id} className="hover:bg-bg-surface2 transition">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-text">{row.full_name}</div>
                    <div className="text-xs text-text-3 mt-0.5">{row.person_code}</div>
                  </td>
                  <td className="px-6 py-4 text-sm text-text-2">{row.rest_brand}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="inline-block px-3 py-1 bg-orange-50 text-orange-700 rounded-full font-bold text-sm">
                      {tr(row.packages_per_hour, 2)}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-text-2">{row.packages}</td>
                  <td className="px-6 py-4 text-right text-sm text-text-2">{tr(row.hours, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// COST PER PACKAGE
// ─────────────────────────────────────────────────────────────

function CostPerPackageSection({
  data,
  onOpenReport,
}: {
  data: RestaurantReports['cost_per_package'];
  onOpenReport: (t: ReportTarget) => void;
}) {
  const [sort, setSort] = useState({ key: 'cost_per_package', desc: true });

  const sorted = useMemo(() => {
    const s = [...data.by_restaurant];
    s.sort((a, b) => {
      let aVal: any = a[sort.key as keyof typeof a];
      let bVal: any = b[sort.key as keyof typeof b];
      const c = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sort.desc ? -c : c;
    });
    return s;
  }, [data.by_restaurant, sort]);

  const toggleSort = (key: string) => {
    if (sort.key === key) {
      setSort({ key, desc: !sort.desc });
    } else {
      setSort({ key, desc: true });
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-2xl border border-border p-6 shadow-sm">
        <div className="inline-flex items-center gap-3 px-4 py-2 bg-brand-soft rounded-xl">
          <Package className="w-5 h-5 text-brand" />
          <div>
            <div className="text-xs font-medium text-brand/70">Genel Ortalama</div>
            <div className="text-2xl font-bold text-brand">{m(data.overall)}</div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-border overflow-hidden shadow-sm">
        <div className="px-6 py-4 bg-bg-surface2 border-b border-border">
          <h3 className="text-sm font-bold text-text">Restoran Bazlı Paket Başı Maliyet</h3>
        </div>
        <table className="w-full">
          <thead className="bg-bg-surface2">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
                onClick={() => toggleSort('brand')}>
                <div className="flex items-center gap-2">
                  Restoran
                  {sort.key === 'brand' && (
                    sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                  )}
                </div>
              </th>
              <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
                onClick={() => toggleSort('billing_excl_vat')}>
                <div className="flex items-center justify-end gap-2">
                  Toplam Fatura
                  {sort.key === 'billing_excl_vat' && (
                    sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                  )}
                </div>
              </th>
              <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
                onClick={() => toggleSort('packages')}>
                <div className="flex items-center justify-end gap-2">
                  Paket
                  {sort.key === 'packages' && (
                    sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                  )}
                </div>
              </th>
              <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
                onClick={() => toggleSort('cost_per_package')}>
                <div className="flex items-center justify-end gap-2">
                  Paket Başı Maliyet
                  {sort.key === 'cost_per_package' && (
                    sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                  )}
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {sorted.map((row) => (
              <tr key={row.restaurant_id} className="hover:bg-bg-surface2 transition group">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <div>
                      <div className="text-sm font-medium text-text">{row.brand}</div>
                      {row.branch && <div className="text-xs text-text-3 mt-0.5">{row.branch}</div>}
                    </div>
                    <ReportIconButton
                      onClick={() => onOpenReport({
                        restaurantId: row.restaurant_id,
                        brand: row.brand,
                        branch: row.branch,
                      })}
                    />
                  </div>
                </td>
                <td className="px-6 py-4 text-right text-sm font-medium text-text">
                  {m(row.billing_excl_vat)}
                </td>
                <td className="px-6 py-4 text-right text-sm text-text-2">
                  {tr(row.packages, 0)}
                </td>
                <td className="px-6 py-4 text-right">
                  <span className="inline-block px-3 py-1 bg-blue-50 text-brand rounded-full font-bold text-sm">
                    {m(row.cost_per_package)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// GROWTH TABLE
// ─────────────────────────────────────────────────────────────

function GrowthTable({
  data,
  onOpenReport,
}: {
  data: RestaurantReports['package_growth'];
  onOpenReport: (t: ReportTarget) => void;
}) {
  const [sort, setSort] = useState({ key: 'growth_pct', desc: true });

  const sorted = useMemo(() => {
    const s = [...data];
    s.sort((a, b) => {
      let aVal: any = a[sort.key as keyof typeof a];
      let bVal: any = b[sort.key as keyof typeof b];
      const c = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sort.desc ? -c : c;
    });
    return s;
  }, [data, sort]);

  const toggleSort = (key: string) => {
    if (sort.key === key) {
      setSort({ key, desc: !sort.desc });
    } else {
      setSort({ key, desc: true });
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-border overflow-hidden shadow-sm">
      <table className="w-full">
        <thead className="bg-bg-surface2">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
              onClick={() => toggleSort('brand')}>
              <div className="flex items-center gap-2">
                Restoran
                {sort.key === 'brand' && (
                  sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                )}
              </div>
            </th>
            <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
              onClick={() => toggleSort('previous_packages')}>
              <div className="flex items-center justify-end gap-2">
                Önceki Ay
                {sort.key === 'previous_packages' && (
                  sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                )}
              </div>
            </th>
            <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
              onClick={() => toggleSort('current_packages')}>
              <div className="flex items-center justify-end gap-2">
                Bu Ay
                {sort.key === 'current_packages' && (
                  sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                )}
              </div>
            </th>
            <th className="px-6 py-3 text-right text-xs font-bold text-text-3 uppercase tracking-wider cursor-pointer hover:bg-bg-surface"
              onClick={() => toggleSort('growth_pct')}>
              <div className="flex items-center justify-end gap-2">
                Büyüme %
                {sort.key === 'growth_pct' && (
                  sort.desc ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                )}
              </div>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {sorted.map((row) => (
            <tr key={row.restaurant_id} className="hover:bg-bg-surface2 transition group">
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <div>
                    <div className="text-sm font-medium text-text">{row.brand}</div>
                    {row.branch && <div className="text-xs text-text-3 mt-0.5">{row.branch}</div>}
                  </div>
                  <ReportIconButton
                    onClick={() => onOpenReport({
                      restaurantId: row.restaurant_id,
                      brand: row.brand,
                      branch: row.branch,
                    })}
                  />
                </div>
              </td>
              <td className="px-6 py-4 text-right text-sm font-medium text-text">
                {tr(row.previous_packages, 0)}
              </td>
              <td className="px-6 py-4 text-right text-sm font-medium text-text">
                {tr(row.current_packages, 0)}
              </td>
              <td className="px-6 py-4 text-right">
                <div className="flex items-center justify-end gap-2">
                  <span className={`inline-block px-3 py-1 rounded-full font-bold text-sm ${
                    row.growth_pct >= 0
                      ? 'bg-green-50 text-green-700'
                      : 'bg-red-50 text-red-700'
                  }`}>
                    {row.growth_pct >= 0 ? '+' : ''}{tr(row.growth_pct, 1)}%
                  </span>
                  {row.growth_pct >= 0 ? (
                    <TrendingUp className="w-4 h-4 text-green-700" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-700" />
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


// ──────────────────────────────────────────────────────────────────
// RestaurantsAiHero — Claude'un restoran raporlarından ürettiği
// 4 kartlık akıllı içgörü. AI yoksa hero gizlenir (sessizce).
// ──────────────────────────────────────────────────────────────────

const AI_CARD_META: Record<string, { Icon: LucideIcon; tone: 'emerald' | 'amber' | 'blue' | 'rose' }> = {
  turnover_riski: { Icon: Users, tone: 'rose' },
  verim_lideri: { Icon: TrendingUp, tone: 'emerald' },
  maliyet_baskisi: { Icon: AlertTriangle, tone: 'amber' },
  buyume_trendi: { Icon: Activity, tone: 'blue' },
};

function RestaurantsAiHero({
  initial, period,
}: {
  initial: AiInsightsResponse | null;
  period: string;
}) {
  const [aiData, setAiData] = useState<AiInsightsResponse | null>(initial);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [expandActions, setExpandActions] = useState(false);

  const ai = aiData?.payload?.ai ?? null;

  // Hero gizlensin eğer AI hiç yoksa (API_KEY yok veya servis çöktü)
  if (!ai) return null;

  const cards = (ai.cards ?? []) as AiInsightCard[];
  const actions = ai.actions ?? [];

  async function handleRefresh() {
    if (refreshing) return;
    setRefreshing(true);
    setRefreshError(null);
    try {
      const fresh = await getRestaurantsAiInsights(period, true);
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
    return `${Math.floor(diffHr / 24)} gün önce`;
  }, [aiData?.generated_at]);

  return (
    <section
      className="rounded-3xl border border-border shadow-sm p-7 relative overflow-hidden"
      style={{
        background: `radial-gradient(900px circle at 92% -8%, rgba(56,189,248,0.16), transparent 50%),
                    radial-gradient(700px circle at -8% 110%, rgba(15,82,186,0.12), transparent 55%),
                    linear-gradient(135deg, #FFFFFF 0%, #F4F8FE 100%)`,
      }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(15,82,186,0.07) 1px, transparent 0)',
          backgroundSize: '22px 22px',
          maskImage: 'linear-gradient(135deg, transparent 35%, black 80%)',
        }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-7 relative z-10">
        {/* Sol: anlatım */}
        <div className="lg:col-span-2">
          <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider text-white shadow-sm bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-500">
              <Sparkles className="w-3.5 h-3.5" strokeWidth={2.4} />
              AI Üretimi · Claude
              <span className="ml-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-white/25 text-[9.5px] font-semibold tracking-normal">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                {aiData?.stale ? 'Eski' : 'Canlı'}
              </span>
            </div>
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
          </div>

          <h2 className="font-display text-[26px] font-semibold tracking-tight leading-snug text-text mb-3">
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
          </h2>

          <p className="text-text-2 text-[13.5px] leading-relaxed mb-5">
            {ai.narrative}
          </p>

          {actions.length > 0 && (
            <button
              onClick={() => setExpandActions((v) => !v)}
              className={[
                'px-4 py-2.5 text-xs font-semibold rounded-lg transition',
                expandActions
                  ? 'bg-blue-50 border border-blue-300 text-blue-700'
                  : 'bg-text text-white hover:shadow-lg',
              ].join(' ')}
            >
              {expandActions ? 'Önerileri gizle' : `Eylem önerileri (${actions.length})`}
            </button>
          )}

          {refreshError && (
            <div className="mt-3 text-[11.5px] text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-1.5 inline-block">
              {refreshError}
            </div>
          )}
        </div>

        {/* Sağ: 4 kart */}
        <div className="grid grid-cols-2 gap-2.5">
          {cards.map((card) => {
            const meta = AI_CARD_META[card.key] ?? AI_CARD_META.turnover_riski;
            const tone = card.tone === 'positive' ? 'emerald'
                       : card.tone === 'warning' ? 'amber'
                       : card.tone === 'info' ? 'blue'
                       : meta.tone;
            const toneClasses: Record<string, string> = {
              emerald: 'border-emerald-200 bg-emerald-50/60',
              amber: 'border-amber-200 bg-amber-50/60',
              blue: 'border-blue-200 bg-blue-50/60',
              rose: 'border-rose-200 bg-rose-50/60',
            };
            const iconColor: Record<string, string> = {
              emerald: 'text-emerald-600',
              amber: 'text-amber-600',
              blue: 'text-blue-600',
              rose: 'text-rose-600',
            };
            const Icon = meta.Icon;
            return (
              <div
                key={card.key}
                className={`relative rounded-xl border p-3.5 ${toneClasses[tone]}`}
              >
                <Icon className={`w-4 h-4 ${iconColor[tone]} mb-2`} strokeWidth={2.2} />
                <div className="text-[10px] uppercase tracking-wider font-bold text-text-3">
                  {card.label}
                </div>
                <div className="font-display text-[18px] font-semibold text-text leading-tight mt-1 mb-1">
                  {card.value}
                </div>
                <div className="text-[11px] text-text-2 leading-snug">
                  {card.sub}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Eylem önerileri açılır panel */}
      {expandActions && actions.length > 0 && (
        <div className="relative z-10 mt-6 pt-6 border-t border-blue-200/60">
          <div className="text-[11px] font-bold uppercase tracking-wider text-text-3 mb-3">
            Eylem Önerileri ({actions.length})
          </div>
          <ul className="space-y-2.5">
            {actions.map((a, i) => {
              const priority = a.priority ?? 'orta';
              const priColor = priority === 'yuksek' ? 'bg-rose-100 text-rose-800'
                             : priority === 'orta' ? 'bg-amber-100 text-amber-800'
                             : 'bg-slate-100 text-slate-700';
              return (
                <li key={i} className="bg-white border border-border rounded-xl p-3.5">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${priColor}`}>
                      {priority}
                    </span>
                    <span className="font-semibold text-[13.5px] text-text">{a.title}</span>
                  </div>
                  <div className="text-[12.5px] text-text-2 leading-relaxed">
                    {a.detail}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}


// ──────────────────────────────────────────────────────────────────
// Mail PDF — restoran satırlarına eklenen küçük ✉️ ikon butonu
// ──────────────────────────────────────────────────────────────────

function ReportIconButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      title="Performans raporunu mailile"
      aria-label="Performans raporu maile gönder"
      className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-md hover:bg-brand-soft text-text-3 hover:text-brand"
    >
      <Mail className="w-4 h-4" strokeWidth={2.2} />
    </button>
  );
}


// ──────────────────────────────────────────────────────────────────
// PDF Preview + Maile Gönder Modal
// ──────────────────────────────────────────────────────────────────

function ReportPreviewModal({
  target, period, onClose,
}: {
  target: ReportTarget;
  period: string;
  onClose: () => void;
}) {
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<
    { kind: 'success' | 'error'; message: string } | null
  >(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);

  const pdfUrl = useMemo(
    () => getRestaurantReportPdfUrl(target.restaurantId, period, false),
    [target.restaurantId, period],
  );

  // ESC ile kapat
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  async function handleSend() {
    if (sending) return;
    setSending(true);
    setSendResult(null);
    try {
      const url = `/api/restaurant-reports/${target.restaurantId}/send-email?period=${encodeURIComponent(period)}`;
      const res = await fetch(url, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail?.message ?? err?.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setSendResult({
        kind: 'success',
        message: data?.message ?? `Rapor ${data?.recipient ?? 'restorana'} gönderildi.`,
      });
    } catch (e) {
      setSendResult({
        kind: 'error',
        message: e instanceof Error ? e.message : 'Mail gönderilemedi.',
      });
    } finally {
      setSending(false);
    }
  }

  const restLabel = target.branch
    ? `${target.brand} · ${target.branch}`
    : target.brand;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(11, 13, 23, 0.55)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-3xl shadow-2xl flex flex-col overflow-hidden"
        style={{ width: 'min(96vw, 980px)', height: 'min(92vh, 920px)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="px-6 py-4 flex items-center justify-between border-b border-border"
          style={{
            background: 'linear-gradient(135deg, #0A3F8F 0%, #0F52BA 60%, #2563EB 100%)',
          }}
        >
          <div className="text-white">
            <div className="text-[10px] uppercase tracking-[0.18em] font-bold opacity-80">
              Performans Raporu · {formatPeriod(period)}
            </div>
            <div className="text-lg font-semibold mt-0.5">{restLabel}</div>
          </div>
          <button
            onClick={onClose}
            aria-label="Kapat"
            className="p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/15 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* PDF preview */}
        <div className="flex-1 relative bg-bg-surface2 overflow-hidden">
          {!iframeLoaded && (
            <div className="absolute inset-0 flex items-center justify-center text-text-3">
              <div className="flex items-center gap-2 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                Rapor yükleniyor (AI yorumu üretiliyor, ~15 sn)…
              </div>
            </div>
          )}
          <iframe
            src={pdfUrl}
            title={`${restLabel} performans raporu`}
            className="w-full h-full border-0"
            onLoad={() => setIframeLoaded(true)}
          />
        </div>

        {/* Footer / Actions */}
        <div className="px-6 py-4 border-t border-border bg-white flex items-center justify-between gap-4">
          <div className="text-xs text-text-3">
            <strong className="text-text-2">Gönderim öncesi raporu inceleyin.</strong>{' '}
            Mail butonu, restoranın <code>contact_email</code> alanına PDF eki ile gönderim yapar.
          </div>
          <div className="flex items-center gap-2">
            {sendResult && (
              <span className={`text-xs px-3 py-1.5 rounded-md font-medium ${
                sendResult.kind === 'success'
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border border-rose-200'
              }`}>
                {sendResult.message}
              </span>
            )}
            <a
              href={pdfUrl}
              download={`performans_${target.brand.replace(/\s+/g, '_')}_${period}.pdf`}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-border text-text-2 hover:bg-bg-surface2 transition"
            >
              PDF indir
            </a>
            <button
              onClick={handleSend}
              disabled={sending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-brand text-white hover:bg-brand-dark transition disabled:opacity-60"
            >
              {sending ? (
                <><Loader2 className="w-4 h-4 animate-spin" />Gönderiliyor…</>
              ) : (
                <><Send className="w-4 h-4" />Maile Gönder</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
