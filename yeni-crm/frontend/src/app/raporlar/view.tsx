'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Activity, BarChart3, Building2, ChevronDown, ChevronRight,
  Package, TrendingDown, TrendingUp,
} from 'lucide-react';

import type { RestaurantReports, SidebarCounts } from '@/lib/api';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string): string {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
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

export function RaporlarView({
  reports,
  period,
  counts,
}: {
  reports: RestaurantReports;
  period: string;
  counts?: SidebarCounts | null;
}) {
  const [activeTab, setActiveTab] = useState<'turnover' | 'efficiency' | 'cost' | 'growth'>(
    'turnover'
  );
  const [sortKey, setSortKey] = useState<string>('');
  const [sortDesc, setSortDesc] = useState(false);

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
      <section className="relative overflow-hidden rounded-3xl mb-2 shadow-lg">
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

        <div className="relative px-7 py-7 text-white">
          <div className="text-[11px] font-medium tracking-[0.2em] uppercase text-white/70 mb-2 flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-yellow-300 animate-pulse" />
            Finans
          </div>
          <h1 className="text-4xl font-bold mb-1">Restoran Performans Raporları</h1>
          <div className="text-white/80">
            {formatPeriod(period)} · {reports.turnover.length} restoran
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
          <TurnoverTable data={reports.turnover} />
        )}
        {activeTab === 'efficiency' && (
          <EfficiencyTable data={reports.courier_efficiency} />
        )}
        {activeTab === 'cost' && (
          <CostPerPackageSection data={reports.cost_per_package} />
        )}
        {activeTab === 'growth' && (
          <GrowthTable data={reports.package_growth} />
        )}
      </div>
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
}: {
  data: typeof RestaurantReports.prototype.turnover;
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
            <tr key={row.restaurant_id} className="hover:bg-bg-surface2 transition">
              <td className="px-6 py-4">
                <div className="text-sm font-medium text-text">{row.brand}</div>
                {row.branch && <div className="text-xs text-text-3 mt-0.5">{row.branch}</div>}
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
  data: typeof RestaurantReports.prototype.courier_efficiency;
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
}: {
  data: typeof RestaurantReports.prototype.cost_per_package;
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
              <tr key={row.restaurant_id} className="hover:bg-bg-surface2 transition">
                <td className="px-6 py-4">
                  <div className="text-sm font-medium text-text">{row.brand}</div>
                  {row.branch && <div className="text-xs text-text-3 mt-0.5">{row.branch}</div>}
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
}: {
  data: typeof RestaurantReports.prototype.package_growth;
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
            <tr key={row.restaurant_id} className="hover:bg-bg-surface2 transition">
              <td className="px-6 py-4">
                <div className="text-sm font-medium text-text">{row.brand}</div>
                {row.branch && <div className="text-xs text-text-3 mt-0.5">{row.branch}</div>}
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
