"use client";

import type { ComponentType, CSSProperties } from "react";
import {
  Activity,
  BarChart3,
  Bell,
  Building2,
  Calendar,
  CalendarCheck,
  ChevronDown,
  CreditCard,
  Download,
  FileText,
  Home,
  MoreHorizontal,
  Package,
  Percent,
  PieChart,
  Receipt,
  Search,
  ShieldCheck,
  ShoppingCart,
  Store,
  TrendingUp,
  User,
  Users,
  Wallet,
  LogOut,
} from "lucide-react";

import styles from "./PayrollOverviewMock.module.css";

type NavGroup = {
  title: string;
  items: Array<{
    label: string;
    icon: ComponentType<{ className?: string; strokeWidth?: number }>;
    active?: boolean;
  }>;
};

const navGroups: NavGroup[] = [
  {
    title: "Ana Menü",
    items: [
      { label: "Genel Bakış", icon: Home },
      { label: "Puantaj", icon: CalendarCheck },
      { label: "Personel", icon: Users },
      { label: "Aylık Hakediş", icon: Wallet, active: true },
    ],
  },
  {
    title: "Operasyon",
    items: [
      { label: "Kesintiler", icon: Percent },
      { label: "Ekipman", icon: Package },
      { label: "Restoranlar", icon: Store },
    ],
  },
  {
    title: "Finans",
    items: [
      { label: "Faturalar", icon: FileText },
      { label: "Satın Alma", icon: ShoppingCart },
      { label: "Satış", icon: TrendingUp },
    ],
  },
  {
    title: "Analiz",
    items: [{ label: "Raporlar", icon: BarChart3 }],
  },
  {
    title: "Hesap",
    items: [{ label: "Profil", icon: User }],
  },
];

const kpis = [
  {
    label: "Net Ödenecek Tutar",
    value: 2_116_597,
    delta: "%8,4 geçen aya göre",
    tone: "positive",
    icon: Wallet,
  },
  {
    label: "Hakediş Tutarı",
    value: 4_178_323,
    delta: "%7,2 geçen aya göre",
    tone: "positive",
    icon: Receipt,
  },
  {
    label: "Toplam Kesinti",
    value: 2_565_752,
    delta: "%5,6 geçen aya göre",
    tone: "negative",
    icon: CircleMinusIcon,
  },
  {
    label: "Toplam Tevkifat",
    value: 114_488,
    delta: "%3,1 geçen aya göre",
    tone: "negative",
    icon: ShieldCheck,
  },
] as const;

const trendPoints = [
  { month: "Eki 25", value: 1.62 },
  { month: "Kas 25", value: 1.83 },
  { month: "Ara 25", value: 2.11 },
  { month: "Oca 26", value: 2.28 },
  { month: "Şub 26", value: 2.4 },
  { month: "Mar 26", value: 2.56 },
];

const distribution = [
  { label: "Saatlik", amount: 1_847_146, percent: 72, color: "#2563EB" },
  { label: "Paket Başı", amount: 498_912, percent: 19, color: "#60A5FA" },
  { label: "Günlük", amount: 153_694, percent: 6, color: "#93C5FD" },
  { label: "Diğer", amount: 65_000, percent: 3, color: "#DBEAFE" },
];

const efficiency = [
  {
    label: "Ortalama Paket / Saat",
    value: "4.8",
    delta: "%6,2",
    tone: "positive",
    spark: [18, 15, 10, 8, 14, 21, 19, 17, 22, 28, 25, 24],
  },
  {
    label: "Toplam Paket",
    value: "122.540",
    delta: "%9,1",
    tone: "positive",
    spark: [8, 9, 14, 12, 18, 23, 19, 20, 17, 26, 22, 21],
  },
  {
    label: "Toplam Saat",
    value: "25.540",
    delta: "%2,4",
    tone: "positive",
    spark: [16, 14, 10, 11, 15, 20, 25, 22, 19, 24, 20, 16],
  },
];

const leaderboards = [
  {
    title: "En Yüksek Net Ödeme",
    rows: [
      { rank: 1, name: "Yaşar Tunç Beratoğlu", role: "Bölge Müdürü", value: "82.696 ₺" },
      { rank: 2, name: "Cihan Can Çimen", role: "Bölge Müdürü", value: "64.295 ₺" },
      { rank: 3, name: "Evren Karapınar", role: "Kurye", value: "62.685 ₺" },
    ],
  },
  {
    title: "En Yüksek Kesinti Tutarı",
    rows: [
      { rank: 1, name: "Faruk Yeşilkeklik", role: "Kurye", value: "28.965 ₺" },
      { rank: 2, name: "Necirvan Bulgan", role: "Kurye", value: "27.119 ₺" },
      { rank: 3, name: "İlham Ardıç", role: "Kurye", value: "25.842 ₺" },
    ],
  },
  {
    title: "En Verimli Kuryeler",
    rows: [
      { rank: 1, name: "Evrem Karapınar", role: "Kurye", value: "6.2" },
      { rank: 2, name: "Cihan Can Çimen", role: "Bölge Müdürü", value: "5.6" },
      { rank: 3, name: "Yaşar Tunç Beratoğlu", role: "Bölge Müdürü", value: "5.1" },
    ],
  },
];

const deductions = [
  { label: "Yakıt Desteği Kesintisi", amount: 9_250 },
  { label: "Avans Kesintisi", amount: 6_500 },
  { label: "Ekipman Kesintisi", amount: 3_750 },
  { label: "Diğer Kesintiler", amount: 4_348 },
];

function formatMoney(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    maximumFractionDigits: 0,
  }).format(value) + " ₺";
}

function getInitials(value: string) {
  return value
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0))
    .join("")
    .toUpperCase();
}

function buildPath(points: number[], width: number, height: number, padding = 14) {
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  return points
    .map((value, index) => {
      const x = padding + (index * (width - padding * 2)) / (points.length - 1);
      const y = height - padding - ((value - min) / range) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");
}

function buildTrendPath() {
  return buildPath(
    trendPoints.map((point) => point.value),
    760,
    260,
    24,
  );
}

function CircleMinusIcon({
  className,
  strokeWidth = 2,
}: {
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.5 12h7" />
    </svg>
  );
}

function CardIcon({
  icon: Icon,
  tone,
}: {
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
  tone: "blue" | "green" | "orange" | "violet";
}) {
  return (
    <span className={`${styles["ck-payroll-icon-badge"]} ${styles[`ck-payroll-icon-${tone}`]}`}>
      <Icon className={styles["ck-payroll-icon"]} strokeWidth={2} />
    </span>
  );
}

export function PayrollOverviewMock() {
  const trendPath = buildTrendPath();
  const donutStyle = {
    background: `conic-gradient(${distribution
      .map((item, index) => {
        const start = distribution
          .slice(0, index)
          .reduce((sum, row) => sum + row.percent, 0);
        const end = start + item.percent;
        return `${item.color} ${start}% ${end}%`;
      })
      .join(", ")})`,
  } as CSSProperties;

  return (
    <div className={styles["ck-payroll-shell"]}>
      <aside className={styles["ck-payroll-sidebar"]}>
        <div className={styles["ck-payroll-sidebar-top"]}>
          <div className={styles["ck-payroll-brand"]}>
            <div className={styles["ck-payroll-brand-mark"]} aria-hidden="true">
              <span className={styles["ck-payroll-brand-cube-outer"]} />
              <span className={styles["ck-payroll-brand-cube-inner"]} />
            </div>
            <div className={styles["ck-payroll-brand-copy"]}>
              <strong>ÇAT KAPINDA</strong>
              <span>CRM</span>
            </div>
          </div>

          <button type="button" className={styles["ck-payroll-search"]}>
            <Search className={styles["ck-payroll-search-icon"]} strokeWidth={2} />
            <span>Ara...</span>
            <small>⌘K</small>
          </button>

          <div className={styles["ck-payroll-nav-groups"]}>
            {navGroups.map((group) => (
              <section key={group.title} className={styles["ck-payroll-nav-group"]}>
                <div className={styles["ck-payroll-nav-label"]}>{group.title}</div>
                <div className={styles["ck-payroll-nav-list"]}>
                  {group.items.map((item) => {
                    const ItemIcon = item.icon;
                    return (
                      <button
                        key={item.label}
                        type="button"
                        className={`${styles["ck-payroll-nav-item"]} ${
                          item.active ? styles["ck-payroll-nav-item-active"] : ""
                        }`}
                      >
                        <span className={styles["ck-payroll-nav-accent"]} />
                        <ItemIcon className={styles["ck-payroll-nav-icon"]} strokeWidth={2} />
                        <span className={styles["ck-payroll-nav-text"]}>{item.label}</span>
                        {item.active ? <span className={styles["ck-payroll-nav-dot"]} /> : null}
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        </div>

        <div className={styles["ck-payroll-sidebar-bottom"]}>
          <button type="button" className={styles["ck-payroll-user-card"]}>
            <div className={styles["ck-payroll-user-avatar"]}>EA</div>
            <div className={styles["ck-payroll-user-copy"]}>
              <strong>Ebru Aslan</strong>
              <span>Yönetici</span>
            </div>
            <ChevronDown className={styles["ck-payroll-user-chevron"]} strokeWidth={2} />
          </button>
          <button type="button" className={styles["ck-payroll-logout"]}>
            <LogOut className={styles["ck-payroll-logout-icon"]} strokeWidth={2} />
            Oturumu Kapat
          </button>
        </div>
      </aside>

      <main className={styles["ck-payroll-main"]}>
        <div className={styles["ck-payroll-container"]}>
          <header className={styles["ck-payroll-header"]}>
            <div className={styles["ck-payroll-header-copy"]}>
              <h1>Aylık Hakediş</h1>
              <p>Kurye ödemelerini, kesintileri ve performansı tek ekranda yönetin.</p>
            </div>

            <div className={styles["ck-payroll-header-actions"]}>
              <button type="button" className={styles["ck-payroll-select"]}>
                <Calendar className={styles["ck-payroll-inline-icon"]} strokeWidth={2} />
                Mart 2026
                <ChevronDown className={styles["ck-payroll-inline-chevron"]} strokeWidth={2} />
              </button>
              <button type="button" className={styles["ck-payroll-secondary-button"]}>
                <Download className={styles["ck-payroll-inline-icon"]} strokeWidth={2} />
                Excel İndir
              </button>
            </div>
          </header>

          <section className={styles["ck-payroll-kpis"]}>
            {kpis.map((kpi) => {
              const KpiIcon = kpi.icon;
              return (
                <article key={kpi.label} className={styles["ck-payroll-kpi-card"]}>
                  <div className={styles["ck-payroll-kpi-top"]}>
                    <CardIcon
                      icon={KpiIcon}
                      tone={
                        kpi.label === "Net Ödenecek Tutar"
                          ? "blue"
                          : kpi.label === "Hakediş Tutarı"
                            ? "green"
                            : kpi.label === "Toplam Kesinti"
                              ? "orange"
                              : "violet"
                      }
                    />
                    <div className={styles["ck-payroll-kpi-copy"]}>
                      <div className={styles["ck-payroll-kpi-label"]}>{kpi.label}</div>
                      <div className={styles["ck-payroll-kpi-value"]}>{formatMoney(kpi.value)}</div>
                    </div>
                  </div>
                  <div
                    className={`${styles["ck-payroll-delta"]} ${
                      kpi.tone === "positive"
                        ? styles["ck-payroll-delta-positive"]
                        : styles["ck-payroll-delta-negative"]
                    }`}
                  >
                    {kpi.delta}
                  </div>
                </article>
              );
            })}
          </section>

          <section className={styles["ck-payroll-dashboard"]}>
            <div className={styles["ck-payroll-left-column"]}>
              <section className={styles["ck-payroll-analytics"]}>
                <article className={styles["ck-payroll-card"]}>
                  <div className={styles["ck-payroll-card-header"]}>
                    <div>
                      <h3>Hakediş Trendi</h3>
                      <p>Son 6 ayda toplam hakediş akışı.</p>
                    </div>
                    <button type="button" className={styles["ck-payroll-mini-select"]}>
                      Toplam Hakediş
                      <ChevronDown className={styles["ck-payroll-mini-chevron"]} strokeWidth={2} />
                    </button>
                  </div>
                  <div className={styles["ck-payroll-trend-chart-wrap"]}>
                    <svg viewBox="0 0 760 260" className={styles["ck-payroll-trend-chart"]} aria-hidden="true">
                      {[0, 1, 2, 3].map((tick) => {
                        const y = 36 + tick * 52;
                        return (
                          <line
                            key={tick}
                            x1="36"
                            y1={y}
                            x2="724"
                            y2={y}
                            className={styles["ck-payroll-trend-gridline"]}
                          />
                        );
                      })}
                      <path d={trendPath} className={styles["ck-payroll-trend-line"]} />
                      {trendPoints.map((point, index) => {
                        const x = 36 + (index * (724 - 36)) / (trendPoints.length - 1);
                        const y = 188 - ((point.value - 1.5) / 1.1) * 120;
                        return (
                          <g key={point.month}>
                            <circle cx={x} cy={y} r="5" className={styles["ck-payroll-trend-point"]} />
                            <text x={x} y={y - 16} textAnchor="middle" className={styles["ck-payroll-trend-value"]}>
                              ₺{point.value.toFixed(2)}M
                            </text>
                            <text x={x} y="238" textAnchor="middle" className={styles["ck-payroll-trend-label"]}>
                              {point.month}
                            </text>
                          </g>
                        );
                      })}
                    </svg>
                  </div>
                  <div className={styles["ck-payroll-insight"]}>
                    <TrendingUp className={styles["ck-payroll-insight-icon"]} strokeWidth={2} />
                    Son 6 ayda hakediş tutarı %57 artış gösterdi.
                  </div>
                </article>

                <article className={styles["ck-payroll-card"]}>
                  <div className={styles["ck-payroll-card-header"]}>
                    <div>
                      <h3>Maliyet Modeli Dağılımı</h3>
                      <p>Model bazlı hakediş payını hızlıca gör.</p>
                    </div>
                  </div>
                  <div className={styles["ck-payroll-donut-layout"]}>
                    <div className={styles["ck-payroll-donut-shell"]}>
                      <div className={styles["ck-payroll-donut"]} style={donutStyle} />
                      <div className={styles["ck-payroll-donut-center"]}>
                        <strong>₺2.57M</strong>
                        <span>Toplam Hakediş</span>
                      </div>
                    </div>
                    <div className={styles["ck-payroll-donut-legend"]}>
                      {distribution.map((item) => (
                        <div key={item.label} className={styles["ck-payroll-donut-legend-item"]}>
                          <span
                            className={styles["ck-payroll-donut-dot"]}
                            style={{ backgroundColor: item.color }}
                          />
                          <span className={styles["ck-payroll-donut-legend-label"]}>{item.label}</span>
                          <strong>{formatMoney(item.amount)}</strong>
                          <small>%{item.percent}</small>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className={`${styles["ck-payroll-insight"]} ${styles["ck-payroll-insight-success"]}`}>
                    <PieChart className={styles["ck-payroll-insight-icon"]} strokeWidth={2} />
                    Hakedişin %72’si saatlik modelden geliyor.
                  </div>
                </article>
              </section>

              <section className={styles["ck-payroll-section"]}>
                <div className={styles["ck-payroll-section-heading"]}>
                  <h2>Verimlilik Özeti</h2>
                  <p>Hız ve hacim tarafında operasyon ritmini aynı alanda okuyun.</p>
                </div>
                <div className={styles["ck-payroll-efficiency"]}>
                  {efficiency.map((item, index) => (
                    <article key={item.label} className={styles["ck-payroll-mini-card"]}>
                      <div className={styles["ck-payroll-mini-label"]}>{item.label}</div>
                      <div className={styles["ck-payroll-mini-value"]}>{item.value}</div>
                      <div
                        className={`${styles["ck-payroll-delta"]} ${styles["ck-payroll-delta-positive"]}`}
                      >
                        {item.delta} geçen aya göre
                      </div>
                      <svg viewBox="0 0 120 40" className={styles["ck-payroll-sparkline"]} aria-hidden="true">
                        <path
                          d={buildPath(item.spark, 120, 40, 6)}
                          className={
                            index === 1
                              ? styles["ck-payroll-sparkline-green"]
                              : styles["ck-payroll-sparkline-blue"]
                          }
                        />
                      </svg>
                    </article>
                  ))}
                </div>
              </section>

              <section className={styles["ck-payroll-section"]}>
                <div className={styles["ck-payroll-section-heading"]}>
                  <h2>Kurye Performans Sıralamaları</h2>
                </div>
                <div className={styles["ck-payroll-leaderboards"]}>
                  {leaderboards.map((board) => (
                    <article key={board.title} className={styles["ck-payroll-leaderboard-card"]}>
                      <div className={styles["ck-payroll-leaderboard-head"]}>
                        <h3>{board.title}</h3>
                        <button type="button" className={styles["ck-payroll-link-button"]}>
                          Tümünü Gör
                        </button>
                      </div>
                      <div className={styles["ck-payroll-leaderboard-list"]}>
                        {board.rows.map((row) => (
                          <div key={`${board.title}-${row.rank}`} className={styles["ck-payroll-leaderboard-row"]}>
                            <span className={styles["ck-payroll-rank-badge"]}>{row.rank}</span>
                            <span className={styles["ck-payroll-avatar-small"]}>{getInitials(row.name)}</span>
                            <div className={styles["ck-payroll-leaderboard-copy"]}>
                              <strong>{row.name}</strong>
                              <span>{row.role}</span>
                            </div>
                            <span className={styles["ck-payroll-leaderboard-value"]}>{row.value}</span>
                          </div>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            </div>

            <aside className={styles["ck-payroll-right-panel"]}>
              <div className={styles["ck-payroll-panel-card"]}>
                <div className={styles["ck-payroll-panel-head"]}>
                  <div className={styles["ck-payroll-panel-person"]}>
                    <span className={styles["ck-payroll-panel-avatar"]}>YT</span>
                    <div className={styles["ck-payroll-panel-copy"]}>
                      <strong>Yaşar Tunç Beratoğlu</strong>
                      <span>Kurye • Bölge Müdürlüğü</span>
                    </div>
                  </div>
                  <div className={styles["ck-payroll-panel-actions"]}>
                    <span className={styles["ck-payroll-status-badge"]}>Aktif</span>
                    <button type="button" className={styles["ck-payroll-kebab"]}>
                      <MoreHorizontal className={styles["ck-payroll-kebab-icon"]} strokeWidth={2} />
                    </button>
                  </div>
                </div>

                <div className={styles["ck-payroll-tabs"]}>
                  {["Finans Özeti", "Operasyon Özeti", "Trend", "PDF"].map((tab, index) => (
                    <button
                      key={tab}
                      type="button"
                      className={`${styles["ck-payroll-tab"]} ${
                        index === 0 ? styles["ck-payroll-tab-active"] : ""
                      }`}
                    >
                      {tab}
                    </button>
                  ))}
                </div>

                <div className={styles["ck-payroll-panel-metrics"]}>
                  <article className={styles["ck-payroll-panel-metric-card"]}>
                    <span>Net Ödeme</span>
                    <strong>82.696 ₺</strong>
                    <small className={styles["ck-payroll-metric-foot-positive"]}>%8,4 geçen aya göre</small>
                  </article>
                  <article className={styles["ck-payroll-panel-metric-card"]}>
                    <span>Hakediş Tutarı</span>
                    <strong>106.544 ₺</strong>
                  </article>
                  <article className={styles["ck-payroll-panel-metric-card"]}>
                    <span>Toplam Kesinti</span>
                    <strong>23.848 ₺</strong>
                    <small>12 kalem</small>
                  </article>
                  <article className={styles["ck-payroll-panel-metric-card"]}>
                    <span>Toplam Tevkifat</span>
                    <strong>5.612 ₺</strong>
                    <small>KDV + Tevkifat</small>
                  </article>
                </div>

                <div className={styles["ck-payroll-panel-list"]}>
                  <div className={styles["ck-payroll-panel-list-head"]}>Kesinti Kalemleri</div>
                  {deductions.map((row) => (
                    <div key={row.label} className={styles["ck-payroll-panel-list-row"]}>
                      <span>{row.label}</span>
                      <strong>{formatMoney(row.amount)}</strong>
                    </div>
                  ))}
                  <div className={styles["ck-payroll-panel-list-total"]}>
                    <span>Toplam Kesinti</span>
                    <strong>23.848 ₺</strong>
                  </div>
                </div>

                <button type="button" className={styles["ck-payroll-primary-button"]}>
                  <Download className={styles["ck-payroll-primary-icon"]} strokeWidth={2} />
                  Hakediş PDF’i İndir
                </button>
              </div>
            </aside>
          </section>
        </div>
      </main>
    </div>
  );
}

export default PayrollOverviewMock;
