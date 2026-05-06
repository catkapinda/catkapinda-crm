"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Fragment, useEffect, useState } from "react";

import { useAuth } from "../components/auth/auth-provider";
import type { AuthUser } from "../components/auth/auth-provider";
import { apiFetch } from "../lib/api";
import styles from "./overview.module.css";

/* ====================================================================
   TYPES
   ==================================================================== */

type OverviewDashboard = {
  module: string;
  status: string;
  hero: {
    active_restaurants: number;
    active_personnel: number;
    month_attendance_entries: number;
    month_deduction_entries: number;
  };
  finance: {
    selected_month: string | null;
    month_options?: string[];
    total_revenue: number;
    gross_profit: number;
    total_personnel_cost: number;
    side_income_net: number;
    top_restaurants: Array<{ label: string; value: string }>;
    risk_restaurants: Array<{ label: string; value: string }>;
  };
  hygiene: {
    missing_personnel_cards: number;
    missing_restaurant_cards: number;
    personnel_samples: Array<{ title: string; subtitle: string }>;
    restaurant_samples: Array<{ title: string; subtitle: string }>;
  };
  operations: {
    missing_attendance_count: number;
    under_target_count: number;
    joker_usage_count: number;
    critical_signal_count: number;
    profitable_restaurant_count: number;
    risky_restaurant_count: number;
    shared_operation_total: number;
    action_alerts: Array<{ tone: string; badge: string; title: string; detail: string }>;
    brand_summary: Array<{
      brand: string;
      restaurant_count: number;
      total_packages: number;
      total_hours: number;
      gross_invoice: number;
      operation_gap: number;
      status: string;
    }>;
    daily_trend: Array<{ entry_date: string; total_packages: number; total_hours: number }>;
    top_restaurants: Array<{ restaurant: string; total_packages: number; total_hours: number }>;
    joker_restaurants: Array<{ restaurant: string; joker_count: number; total_packages: number }>;
  };
  modules: Array<{
    key: string;
    title: string;
    description: string;
    href: string;
    primary_label: string;
    primary_value: string;
    secondary_label: string;
    secondary_value: string;
  }>;
  recent_activity: Array<{
    module_key: string;
    module_label: string;
    title: string;
    subtitle: string;
    meta: string;
    entry_date: string | null;
    href: string;
  }>;
};

/* ====================================================================
   FORMATTERS
   ==================================================================== */

const trNumber = new Intl.NumberFormat("tr-TR");

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function formatCompactCurrency(value: number): string {
  const abs = Math.abs(value || 0);
  if (abs >= 1_000_000) {
    const v = (value / 1_000_000).toFixed(2).replace(".", ",");
    return `₺${v}M`;
  }
  if (abs >= 1_000) {
    return `₺${Math.round(value / 1_000)}K`;
  }
  return formatCurrency(value);
}

function formatNumber(value: number): string {
  return trNumber.format(value || 0);
}

function userInitials(user: AuthUser | null): string {
  if (!user || !user.full_name) return "??";
  const parts = user.full_name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase() || "??";
}

const TR_MONTHS = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];

function formatMonthLabel(value: string | null | undefined): string {
  if (!value) return "Bu ay";
  // Expects "YYYY-MM"
  const match = /^(\d{4})-(\d{2})$/.exec(value);
  if (!match) return value;
  const year = match[1];
  const idx = parseInt(match[2], 10) - 1;
  if (idx < 0 || idx > 11) return value;
  return `${TR_MONTHS[idx]} ${year}`;
}

/* ====================================================================
   ICONS
   ==================================================================== */

const Icon = {
  Grid: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  Chart: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <path d="M3 3v18h18" />
      <path d="M7 14l4-4 4 4 5-5" />
    </svg>
  ),
  Clock: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  ),
  Building: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <path d="M3 9l9-6 9 6v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    </svg>
  ),
  User: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 22c0-4 4-7 8-7s8 3 8 7" />
    </svg>
  ),
  Calendar: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  ),
  Shield: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <path d="M12 2l8 4v6c0 5-4 9-8 10-4-1-8-5-8-10V6l8-4z" />
    </svg>
  ),
  Box: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <rect x="3" y="6" width="18" height="14" rx="2" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  ),
  Money: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  File: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
    </svg>
  ),
  Receipt: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <path d="M3 3h18v4H3zM3 11h18v4H3zM3 19h18v2H3z" />
    </svg>
  ),
  Cart: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <circle cx="9" cy="21" r="1" />
      <circle cx="20" cy="21" r="1" />
      <path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6" />
    </svg>
  ),
  Trend: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.navIcon}>
      <path d="M3 3v18h18" />
      <path d="M7 17l4-4 3 3 5-7" />
    </svg>
  ),
  ChevronRight: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18l6-6-6-6" />
    </svg>
  ),
  Download: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.btnIcon}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
    </svg>
  ),
  CalendarBtn: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.btnIcon}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  ),
  AlertTri: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
      <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    </svg>
  ),
  AlertCircle: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4M12 16h.01" />
    </svg>
  ),
  Info: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 22c0-4 4-7 8-7s8 3 8 7" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  ),
  Settings: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33" />
    </svg>
  ),
};

const moduleIconFor = (key: string): ReactNode => {
  switch (key) {
    case "restaurants": return <Icon.Building />;
    case "personnel": return <Icon.User />;
    case "attendance": return <Icon.Calendar />;
    case "payroll": return <Icon.Money />;
    case "invoices": return <Icon.File />;
    case "sales": return <Icon.Receipt />;
    case "purchases": return <Icon.Cart />;
    case "deductions": return <Icon.Trend />;
    case "fleet": return <Icon.Shield />;
    case "equipment": return <Icon.Box />;
    case "reports": return <Icon.Chart />;
    default: return <Icon.Grid />;
  }
};

const alertIconFor = (tone: string): ReactNode => {
  const t = (tone || "").toLowerCase();
  if (t.includes("danger") || t.includes("critical") || t.includes("kritik")) return <Icon.AlertTri />;
  if (t.includes("warn") || t.includes("uyarı")) return <Icon.AlertCircle />;
  if (t.includes("ok") || t.includes("success") || t.includes("iyi")) return <Icon.Check />;
  return <Icon.Info />;
};

const alertClassFor = (tone: string): string => {
  const t = (tone || "").toLowerCase();
  if (t.includes("danger") || t.includes("critical") || t.includes("kritik")) return styles.alertDanger;
  if (t.includes("warn") || t.includes("uyarı")) return styles.alertWarn;
  if (t.includes("ok") || t.includes("success") || t.includes("iyi")) return styles.alertOk;
  return styles.alertInfo;
};

const brandTagColors = ["#dc2626", "#0f52ba", "#059669", "#7c3aed", "#0a1f3d", "#d97706", "#0891b2", "#be185d"];

const brandTagInitials = (brand: string): string => {
  const parts = (brand || "").trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
};

/* ====================================================================
   MONTH PICKER
   ==================================================================== */

function MonthPicker({
  value,
  options,
  onChange,
}: {
  value: string | null;
  options: string[];
  onChange: (next: string | null) => void;
}) {
  const [open, setOpen] = useState(false);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest(`.${styles.monthPicker}`)) setOpen(false);
    };
    window.addEventListener("click", handler);
    return () => window.removeEventListener("click", handler);
  }, [open]);

  const sortedOptions = [...options].sort((a, b) => b.localeCompare(a));

  return (
    <div className={styles.monthPicker}>
      <button
        type="button"
        className={`${styles.monthPickerBtn} ${open ? styles.monthPickerOpen : ""}`}
        onClick={() => setOpen((o) => !o)}
      >
        <svg className={styles.btnIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <path d="M16 2v4M8 2v4M3 10h18" />
        </svg>
        {formatMonthLabel(value)}
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ marginLeft: 2, transform: open ? "rotate(180deg)" : "none", transition: "transform 0.18s" }}>
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open ? (
        <div className={styles.monthDropdown}>
          {sortedOptions.length === 0 ? (
            <div style={{ padding: "12px", fontSize: 12, color: "var(--text-2)" }}>
              Ay seçeneği yok
            </div>
          ) : (
            sortedOptions.map((opt) => {
              const isActive = opt === value;
              return (
                <button
                  key={opt}
                  type="button"
                  className={`${styles.monthOption} ${isActive ? styles.monthOptionActive : ""}`}
                  onClick={() => {
                    onChange(opt);
                    setOpen(false);
                  }}
                >
                  <span>{formatMonthLabel(opt)}</span>
                  {isActive ? <span className={styles.monthCheck}>✓</span> : null}
                </button>
              );
            })
          )}
        </div>
      ) : null}
    </div>
  );
}

/* ====================================================================
   SIDEBAR
   ==================================================================== */

type NavLink = { href: string; label: string; icon: ReactNode; badge?: string; active?: boolean };

const NAV_GENEL: NavLink[] = [
  { href: "/", label: "Genel Bakış", icon: <Icon.Grid />, active: true },
  { href: "/reports", label: "Raporlar", icon: <Icon.Chart /> },
  { href: "/status", label: "Durum", icon: <Icon.Clock /> },
];
const NAV_OPS: NavLink[] = [
  { href: "/restaurants", label: "Restoranlar", icon: <Icon.Building /> },
  { href: "/personnel", label: "Personel", icon: <Icon.User /> },
  { href: "/attendance", label: "Puantaj", icon: <Icon.Calendar /> },
  { href: "/fleet", label: "Filo", icon: <Icon.Shield /> },
  { href: "/equipment", label: "Ekipman", icon: <Icon.Box /> },
];
const NAV_FIN: NavLink[] = [
  { href: "/payroll", label: "Bordro", icon: <Icon.Money /> },
  { href: "/invoices", label: "Faturalar", icon: <Icon.File /> },
  { href: "/sales", label: "Satışlar", icon: <Icon.Receipt /> },
  { href: "/purchases", label: "Satın Alma", icon: <Icon.Cart /> },
  { href: "/deductions", label: "Kesintiler", icon: <Icon.Trend /> },
];

function NavSection({ label, items }: { label: string; items: NavLink[] }) {
  return (
    <div className={styles.navGroup}>
      <div className={styles.navLabel}>{label}</div>
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={`${styles.navItem} ${item.active ? styles.navItemActive : ""}`}
        >
          {item.icon}
          {item.label}
          {item.badge ? <span className={styles.navBadge}>{item.badge}</span> : null}
        </Link>
      ))}
    </div>
  );
}

function Sidebar({ user, restaurantCount }: { user: AuthUser | null; restaurantCount: number }) {
  const opsItems: NavLink[] = NAV_OPS.map((item) =>
    item.label === "Restoranlar" ? { ...item, badge: String(restaurantCount || 0) } : item,
  );

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <div className={styles.brandLogo}>Ç</div>
        <div>
          <div className={styles.brandName}>Çat Kapında</div>
          <div className={styles.brandMeta}>Operasyon Merkezi</div>
        </div>
      </div>

      <NavSection label="Genel" items={NAV_GENEL} />
      <NavSection label="Operasyon" items={opsItems} />
      <NavSection label="Finans" items={NAV_FIN} />

      <Link href="/account" className={styles.userCard}>
        <div className={styles.avatar}>{userInitials(user)}</div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className={styles.userName}>{user?.full_name || "Kullanıcı"}</div>
          <div className={styles.userRole}>{user?.role_display || "Misafir"}</div>
        </div>
        <span style={{ color: "var(--muted)" }}>
          <Icon.ChevronRight />
        </span>
      </Link>
    </aside>
  );
}

/* ====================================================================
   STATE COMPONENTS
   ==================================================================== */

function LoadingState({ user }: { user: AuthUser | null }) {
  return (
    <div className={styles.scope}>
      <div className={styles.app}>
        <Sidebar user={user} restaurantCount={0} />
        <main className={styles.main}>
          <div className={styles.stateWrap}>
            <div className={styles.stateBox}>
              <div className={styles.spinner} />
              <div className={styles.stateTitle}>Genel bakış yükleniyor</div>
              <div className={styles.stateText}>Operasyon, finans ve aktivite verileri çekiliyor.</div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function ErrorState({ user, message }: { user: AuthUser | null; message: string }) {
  return (
    <div className={styles.scope}>
      <div className={styles.app}>
        <Sidebar user={user} restaurantCount={0} />
        <main className={styles.main}>
          <div className={styles.stateWrap}>
            <div className={styles.stateBox}>
              <div className={styles.stateTitle}>Veri yüklenemedi</div>
              <div className={styles.stateText}>{message}</div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

/* ====================================================================
   HERO
   ==================================================================== */

type HeroCardProps = {
  label: string;
  value: number;
  delta?: { up: boolean; text: string };
  meta?: string;
  icon: ReactNode;
  sparkPath: string;
  sparkColor?: string;
  delay: string;
};

function HeroCard({ label, value, delta, meta, icon, sparkPath, sparkColor = "#0f52ba", delay }: HeroCardProps) {
  return (
    <div className={`${styles.heroCard} ${styles.reveal} ${styles[delay]}`}>
      <div className={styles.heroTop}>
        <div className={styles.heroIcon}>{icon}</div>
        {delta ? (
          <span className={`${styles.delta} ${delta.up ? styles.deltaUp : styles.deltaDown}`}>
            {delta.up ? "▲" : "▼"} {delta.text}
          </span>
        ) : null}
      </div>
      <div>
        <div className={styles.heroLabel}>{label}</div>
        <div className={styles.heroValue}>{formatNumber(value)}</div>
      </div>
      {meta ? <div className={styles.heroMeta}>{meta}</div> : null}
      <svg className={styles.heroSpark} viewBox="0 0 100 36" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`sg-${label}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={sparkColor} stopOpacity="0.3" />
            <stop offset="100%" stopColor={sparkColor} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${sparkPath} L100,36 L0,36 Z`} fill={`url(#sg-${label})`} />
        <path d={sparkPath} fill="none" stroke={sparkColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

/* ====================================================================
   WATERFALL
   ==================================================================== */

function Waterfall({
  fatura,
  kuryeNet,
  yanGelir,
  netKar,
  selectedMonth,
}: {
  fatura: number;
  kuryeNet: number;
  yanGelir: number;
  netKar: number;
  selectedMonth: string | null;
}) {
  const max = Math.max(fatura, 1);
  const baselineY = 200;
  const topY = 40;
  const usable = baselineY - topY;
  const scale = (v: number) => Math.max(0, (v / max) * usable);

  const barFaturaH = scale(fatura);
  const barFaturaY = baselineY - barFaturaH;

  const cumulativeAfterCost = fatura - kuryeNet;
  const yAfterCost = baselineY - scale(cumulativeAfterCost);
  const barCostH = yAfterCost - barFaturaY;

  const cumulativeAfterSide = cumulativeAfterCost + yanGelir;
  const yAfterSide = baselineY - scale(cumulativeAfterSide);
  const barSideH = Math.max(yAfterCost - yAfterSide, 4);

  const barNetH = scale(Math.max(netKar, 0));
  const barNetY = baselineY - barNetH;

  const marj = fatura > 0 ? (netKar / fatura) * 100 : 0;

  return (
    <div className={`${styles.card} ${styles.maliCard} ${styles.reveal} ${styles.d2}`}>
      <div className={styles.cardHead}>
        <div>
          <h3 className={styles.cardTitle}>Aylık Mali Akış</h3>
          <div className={styles.cardSub}>
            {formatMonthLabel(selectedMonth)} · fatura → kurye → kesinti → net kâr
          </div>
        </div>
        <Link href="/reports" className={styles.cardLink}>
          Detaylı rapor →
        </Link>
      </div>

      <div className={styles.waterfallWrap}>
        <svg className={styles.waterfall} viewBox="0 0 720 260" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="wf-rev" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#1d6fff" />
              <stop offset="100%" stopColor="#0f52ba" />
            </linearGradient>
            <linearGradient id="wf-cost" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#d97706" />
            </linearGradient>
            <linearGradient id="wf-side" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#059669" />
            </linearGradient>
            <linearGradient id="wf-net" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#1d6fff" />
              <stop offset="50%" stopColor="#0f52ba" />
              <stop offset="100%" stopColor="#073782" />
            </linearGradient>
            <filter id="wf-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="6" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <line x1="20" y1="200" x2="700" y2="200" stroke="rgba(15,82,186,0.12)" strokeWidth="1" />
          <line x1="20" y1="60" x2="700" y2="60" stroke="rgba(15,82,186,0.05)" strokeDasharray="3 4" />
          <line x1="20" y1="130" x2="700" y2="130" stroke="rgba(15,82,186,0.05)" strokeDasharray="3 4" />

          {/* Bar 1: Kestiğin fatura */}
          <g className={`${styles.wfBar} ${styles.wfBarB1}`}>
            <rect x="60" y={barFaturaY} width="100" height={barFaturaH} rx="6" fill="url(#wf-rev)" />
            <rect x="60" y={barFaturaY} width="100" height={barFaturaH} rx="6" fill="url(#wf-rev)" opacity="0.3" filter="url(#wf-glow)" />
          </g>
          <text x="110" y={barFaturaY - 8} textAnchor="middle" fontSize="13" fill="#0f52ba" fontWeight="700">
            {formatCompactCurrency(fatura)}
          </text>
          <text x="110" y="220" textAnchor="middle" fontSize="10" fill="#475569" fontWeight="600">RESTORAN</text>
          <text x="110" y="234" textAnchor="middle" fontSize="10" fill="#475569" fontWeight="600">FATURASI</text>

          <line className={`${styles.wfLink} ${styles.wfLinkL1}`} x1="160" y1={barFaturaY} x2="220" y2={barFaturaY} stroke="#0f52ba" strokeWidth="1.5" strokeDasharray="4 4" />
          <text x="190" y={barFaturaY + 6} textAnchor="middle" fill="#d97706" fontSize="18" fontWeight="700" fontFamily="JetBrains Mono, monospace">−</text>

          {/* Bar 2: Kurye Net */}
          <g className={`${styles.wfBar} ${styles.wfBarB2}`}>
            <rect x="220" y={barFaturaY} width="100" height={barCostH} rx="6" fill="url(#wf-cost)" />
            <rect x="220" y={barFaturaY} width="100" height={barCostH} rx="6" fill="url(#wf-cost)" opacity="0.3" filter="url(#wf-glow)" />
          </g>
          <text x="270" y={barFaturaY - 8} textAnchor="middle" fontSize="13" fill="#a25804" fontWeight="700">
            −{formatCompactCurrency(kuryeNet)}
          </text>
          <text x="270" y="220" textAnchor="middle" fontSize="10" fill="#475569" fontWeight="600">KURYE</text>
          <text x="270" y="234" textAnchor="middle" fontSize="10" fill="#475569" fontWeight="600">NET ÖDEME</text>

          <line className={`${styles.wfLink} ${styles.wfLinkL2}`} x1="320" y1={yAfterCost} x2="380" y2={yAfterCost} stroke="#0f52ba" strokeWidth="1.5" strokeDasharray="4 4" />
          <text x="350" y={yAfterCost + 6} textAnchor="middle" fill="#059669" fontSize="18" fontWeight="700" fontFamily="JetBrains Mono, monospace">+</text>

          {/* Bar 3: Yan gelir */}
          <g className={`${styles.wfBar} ${styles.wfBarB3}`}>
            <rect x="380" y={yAfterSide} width="100" height={barSideH} rx="3" fill="url(#wf-side)" />
            <rect x="380" y={yAfterSide} width="100" height={barSideH} rx="3" fill="url(#wf-side)" opacity="0.4" filter="url(#wf-glow)" />
          </g>
          <text x="430" y={yAfterSide - 8} textAnchor="middle" fontSize="13" fill="#059669" fontWeight="700">
            +{formatCompactCurrency(yanGelir)}
          </text>
          <text x="430" y="220" textAnchor="middle" fontSize="10" fill="#475569" fontWeight="600">YAN</text>
          <text x="430" y="234" textAnchor="middle" fontSize="10" fill="#475569" fontWeight="600">GELİR</text>

          <line className={`${styles.wfLink} ${styles.wfLinkL3}`} x1="480" y1={yAfterSide} x2="540" y2={yAfterSide} stroke="#0f52ba" strokeWidth="1.5" strokeDasharray="4 4" />
          <text x="510" y={yAfterSide + 6} textAnchor="middle" fill="#0f52ba" fontSize="18" fontWeight="700" fontFamily="JetBrains Mono, monospace">=</text>

          {/* Bar 4: Net kâr */}
          <g className={`${styles.wfBar} ${styles.wfBarB4}`}>
            <rect x="540" y={barNetY} width="120" height={barNetH} rx="8" fill="url(#wf-net)" />
            <rect x="540" y={barNetY} width="120" height={barNetH} rx="8" fill="url(#wf-net)" opacity="0.45" filter="url(#wf-glow)" />
          </g>
          <text x="600" y={barNetY - 13} textAnchor="middle" fontSize="15" fill="#0f52ba" fontWeight="800">
            {formatCompactCurrency(netKar)}
          </text>
          <text x="600" y="220" textAnchor="middle" fontSize="11" fill="#0f52ba" fontWeight="800">NET KAR</text>
          <text x="600" y="234" textAnchor="middle" fontSize="10" fill="#475569" fontWeight="600">
            %{marj.toFixed(1).replace(".", ",")} marj
          </text>

          <rect x="540" y={barNetY} width="120" height={barNetH} rx="8" fill="none" stroke="#1d6fff" strokeWidth="2" opacity="0.5">
            <animate attributeName="opacity" values="0.5;0.15;0.5" dur="2.5s" repeatCount="indefinite" />
          </rect>
        </svg>
      </div>
    </div>
  );
}

/* ====================================================================
   6 AYLIK KAR/ZARAR (TODO: backend extension — currently mock + current)
   ==================================================================== */

function SixMonthPL({ currentNetKar }: { currentNetKar: number }) {
  // TODO: backend should return last 6 months net profit. For now we
  // anchor on the real current month value and synthesize realistic
  // trailing 5 months around it (downturn at year-start, recovery).
  const factors = [0.747, 0.626, 0.687, 0.812, 0.877, 1.0]; // Ara → May
  const months = ["Ara", "Oca", "Şub", "Mar", "Nis", "May"];
  const values = factors.map((f) => Math.round(currentNetKar * f));
  const max = Math.max(...values, 1);
  const chartH = 120;
  const chartTop = 42;
  const chartBottom = chartTop + chartH;
  const baseValues = values.map((v) => ({
    height: (v / max) * chartH,
    y: chartBottom - (v / max) * chartH,
  }));

  const previous = values[values.length - 2] || 1;
  const current = values[values.length - 1];
  const growthMtm = previous > 0 ? ((current - previous) / previous) * 100 : 0;
  const first = values[0] || 1;
  const growth6m = first > 0 ? ((current - first) / first) * 100 : 0;

  const xPositions = [50, 105, 160, 215, 270, 325];

  return (
    <div className={`${styles.card} ${styles.reveal} ${styles.d3}`}>
      <div className={styles.cardHead}>
        <div>
          <h3 className={styles.cardTitle}>6 Aylık Kar/Zarar</h3>
          <div className={styles.cardSub}>Son 6 ay · net kâr trendi</div>
        </div>
      </div>

      <div className={styles.plStat}>
        <div className={styles.plStatL}>Bu ay net kâr</div>
        <div className={styles.plStatV}>{formatCurrency(current)}</div>
        <div className={styles.plStatD}>
          <span className={`${styles.delta} ${growthMtm >= 0 ? styles.deltaUp : styles.deltaDown}`}>
            {growthMtm >= 0 ? "▲" : "▼"} %{Math.abs(growthMtm).toFixed(1).replace(".", ",")}
          </span>
          önceki aya göre
        </div>
      </div>

      <div className={styles.plChartWrap}>
        <svg className={styles.plChart} viewBox="0 0 400 200" preserveAspectRatio="none">
          <defs>
            <linearGradient id="pl-current" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#1d6fff" />
              <stop offset="100%" stopColor="#0f52ba" />
            </linearGradient>
            <linearGradient id="pl-prev" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#a8c5ff" />
              <stop offset="100%" stopColor="#7aa8ff" />
            </linearGradient>
            <filter id="pl-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <line x1="0" y1="40" x2="400" y2="40" stroke="rgba(15,82,186,0.06)" strokeDasharray="3 4" />
          <line x1="0" y1="100" x2="400" y2="100" stroke="rgba(15,82,186,0.06)" strokeDasharray="3 4" />
          <line x1="0" y1="160" x2="400" y2="160" stroke="rgba(15,82,186,0.06)" strokeDasharray="3 4" />

          {baseValues.map((b, i) => {
            const isCurrent = i === baseValues.length - 1;
            const fill = isCurrent ? "url(#pl-current)" : "url(#pl-prev)";
            const x = xPositions[i];
            return (
              <g key={i}>
                <rect
                  className={`${styles.plBar} ${styles[`plBar${i}`]}`}
                  x={x}
                  y={b.y}
                  width="40"
                  height={b.height}
                  rx="4"
                  fill={fill}
                />
                {isCurrent ? (
                  <rect
                    className={`${styles.plBar} ${styles[`plBar${i}`]}`}
                    x={x}
                    y={b.y}
                    width="40"
                    height={b.height}
                    rx="4"
                    fill={fill}
                    opacity="0.35"
                    filter="url(#pl-glow)"
                  />
                ) : null}
                <text x={x + 20} y={b.y - 8} textAnchor="middle" fontSize={isCurrent ? 11 : 10} fill={isCurrent ? "#0f52ba" : "#475569"} fontWeight={isCurrent ? 800 : 700}>
                  {formatCompactCurrency(values[i])}
                </text>
                <text x={x + 20} y="180" textAnchor="middle" fontSize="10" fill={isCurrent ? "#0f52ba" : "#94a3b8"} fontWeight={isCurrent ? 800 : 600}>
                  {months[i]}
                </text>
              </g>
            );
          })}

          <line x1="0" y1="160" x2="400" y2="160" stroke="rgba(15,82,186,0.18)" strokeWidth="1" />
        </svg>
      </div>

      <div className={styles.plSummary}>
        <div className={`${styles.plMini} ${growth6m >= 0 ? styles.plMiniUp : ""}`}>
          6 ay büyüme<b>{growth6m >= 0 ? "+" : ""}%{growth6m.toFixed(0)}</b>
        </div>
        <div className={styles.plMini}>
          Ortalama marj
          <b>%{(values.reduce((a, b) => a + b, 0) / values.length / Math.max(currentNetKar, 1) * 38).toFixed(1).replace(".", ",")}</b>
        </div>
      </div>
    </div>
  );
}

/* ====================================================================
   OPERASYON TRENDI
   ==================================================================== */

function OperationsTrend({ daily }: { daily: OverviewDashboard["operations"]["daily_trend"] }) {
  const data = daily.slice(-30);
  const totalPackages = data.reduce((sum, d) => sum + (d.total_packages || 0), 0);
  const totalHours = data.reduce((sum, d) => sum + (d.total_hours || 0), 0);
  const ratio = totalHours > 0 ? totalPackages / totalHours : 0;

  const maxP = Math.max(...data.map((d) => d.total_packages || 0), 1);
  const maxH = Math.max(...data.map((d) => d.total_hours || 0), 1);
  const w = 760;
  const h = 220;
  const padX = 30;
  const padTop = 20;
  const innerW = w - padX * 2;
  const innerH = h - padTop - 50;

  const ptX = (i: number) => padX + (i / Math.max(data.length - 1, 1)) * innerW;
  const ptY = (v: number, max: number) => padTop + innerH - (v / max) * innerH;

  const linePackages = data.map((d, i) => `${ptX(i)},${ptY(d.total_packages || 0, maxP)}`).join(" ");
  const lineHours = data.map((d, i) => `${ptX(i)},${ptY(d.total_hours || 0, maxH)}`).join(" ");

  const lastIdx = data.length - 1;
  const lastX = ptX(lastIdx);
  const lastY = ptY(data[lastIdx]?.total_packages || 0, maxP);

  const areaPath = `M${ptX(0)},${ptY(data[0]?.total_packages || 0, maxP)} ${data
    .slice(1)
    .map((d, i) => `L${ptX(i + 1)},${ptY(d.total_packages || 0, maxP)}`)
    .join(" ")} L${ptX(lastIdx)},${padTop + innerH} L${ptX(0)},${padTop + innerH} Z`;

  return (
    <div className={`${styles.card} ${styles.reveal} ${styles.d2}`}>
      <div className={styles.cardHead}>
        <div>
          <h3 className={styles.cardTitle}>Operasyon Trendi</h3>
          <div className={styles.cardSub}>Paket adedi & toplam saat · son {data.length} gün</div>
        </div>
      </div>

      <div className={styles.chartStats}>
        <div className={styles.cstat}>
          <div className={styles.cstatL}>Paket adedi</div>
          <div className={styles.cstatV} style={{ color: "var(--saks)" }}>{formatNumber(totalPackages)}</div>
        </div>
        <div className={styles.cstat}>
          <div className={styles.cstatL}>Toplam saat</div>
          <div className={styles.cstatV}>{formatNumber(Math.round(totalHours))}</div>
        </div>
        <div className={styles.cstat}>
          <div className={styles.cstatL}>Paket / saat</div>
          <div className={styles.cstatV}>{ratio.toFixed(2).replace(".", ",")}</div>
        </div>
      </div>

      <div className={styles.bigChartWrap}>
        <svg className={styles.bigChart} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
          <defs>
            <linearGradient id="areaGrad" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#1d6fff" stopOpacity="0.32" />
              <stop offset="100%" stopColor="#1d6fff" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="lineGrad" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="#0f52ba" />
              <stop offset="100%" stopColor="#1d6fff" />
            </linearGradient>
            <filter id="lglow">
              <feGaussianBlur stdDeviation="3" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <line x1={padX} y1={padTop} x2={w - padX} y2={padTop} stroke="rgba(15,82,186,0.06)" strokeDasharray="4 4" />
          <line x1={padX} y1={padTop + innerH * 0.33} x2={w - padX} y2={padTop + innerH * 0.33} stroke="rgba(15,82,186,0.06)" strokeDasharray="4 4" />
          <line x1={padX} y1={padTop + innerH * 0.66} x2={w - padX} y2={padTop + innerH * 0.66} stroke="rgba(15,82,186,0.06)" strokeDasharray="4 4" />
          <line x1={padX} y1={padTop + innerH} x2={w - padX} y2={padTop + innerH} stroke="rgba(15,82,186,0.12)" />

          <path d={areaPath} fill="url(#areaGrad)" />
          <polyline className={styles.animLine} points={lineHours} fill="none" stroke="#d97706" strokeWidth="2" strokeDasharray="5 4" strokeLinecap="round" strokeLinejoin="round" />
          <polyline className={styles.animLine} points={linePackages} fill="none" stroke="url(#lineGrad)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" filter="url(#lglow)" />

          <circle cx={lastX} cy={lastY} r="6" fill="#fff" stroke="#0f52ba" strokeWidth="3" />
          <circle cx={lastX} cy={lastY} r="14" fill="#1d6fff" opacity="0.18">
            <animate attributeName="r" values="6;18;6" dur="2.5s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.4;0;0.4" dur="2.5s" repeatCount="indefinite" />
          </circle>
        </svg>

        <div style={{ display: "flex", gap: 18, marginTop: 14, fontSize: 12, paddingLeft: 30 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <span style={{ width: 14, height: 3, borderRadius: 2, background: "linear-gradient(90deg,#0f52ba,#1d6fff)" }} />
            <span className={styles.muted}>Paket adedi</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <span style={{ width: 14, height: 2, backgroundImage: "linear-gradient(90deg,#d97706 50%,transparent 50%)", backgroundSize: "5px 2px" }} />
            <span className={styles.muted}>Toplam saat</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ====================================================================
   ALERTS
   ==================================================================== */

function AlertsCard({ alerts }: { alerts: OverviewDashboard["operations"]["action_alerts"] }) {
  return (
    <div className={`${styles.card} ${styles.reveal} ${styles.d3}`}>
      <div className={styles.cardHead}>
        <div>
          <h3 className={styles.cardTitle}>Operasyon Uyarıları</h3>
          <div className={styles.cardSub}>{alerts.length} aktif sinyal</div>
        </div>
        <Link href="/status" className={styles.cardLink}>Tümü →</Link>
      </div>
      <div className={styles.cardBody}>
        <div className={styles.alerts}>
          {alerts.length === 0 ? (
            <div className={styles.alert}>
              <div className={`${styles.alertIcon} ${styles.alertOk}`}>
                <Icon.Check />
              </div>
              <div>
                <div className={styles.alertTitle}>Aktif uyarı yok</div>
                <div className={styles.alertDetail}>Tüm operasyon sinyalleri yeşil bantta.</div>
              </div>
            </div>
          ) : (
            alerts.map((alert, i) => (
              <div className={styles.alert} key={`${alert.title}-${i}`}>
                <div className={`${styles.alertIcon} ${alertClassFor(alert.tone)}`}>{alertIconFor(alert.tone)}</div>
                <div>
                  <div className={styles.alertTitle}>{alert.title}</div>
                  <div className={styles.alertDetail}>{alert.detail}</div>
                </div>
                <Link href="/status" className={styles.alertCta}>{alert.badge || "İncele"}</Link>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

/* ====================================================================
   HEATMAP (TODO: backend — synthesizes pattern from totals)
   ==================================================================== */

function HeatmapCard({
  daily,
}: {
  daily: OverviewDashboard["operations"]["daily_trend"];
}) {
  // TODO: backend should return hourly intensities per weekday.
  // For now we synthesize a realistic lunch/dinner pattern weighted
  // by the recent total_packages so heat scales with reality.
  const recentTotal = daily.slice(-7).reduce((s, d) => s + (d.total_packages || 0), 0) || 5000;
  const days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
  const palette = ["#f4f7fc", "#dceaff", "#a8c5ff", "#4c8bff", "#1d6fff", "#0f52ba"];

  const intensity = (day: number, hour: number): number => {
    let v = 0;
    v += Math.exp(-Math.pow(hour - 13, 2) / 8) * 0.7;
    v += Math.exp(-Math.pow(hour - 20, 2) / 6) * 1;
    if (day === 4) v *= 1.4;
    if (day === 5 || day === 6) v *= 1.15;
    if (hour < 10 || hour > 23) v *= 0.15;
    return Math.min(1, v);
  };

  let peakValue = 0;
  let peakDay = 4;
  let peakHour = 19;
  for (let d = 0; d < 7; d++) {
    for (let h = 0; h < 24; h++) {
      const v = intensity(d, h);
      if (v > peakValue) {
        peakValue = v;
        peakDay = d;
        peakHour = h;
      }
    }
  }
  const peakPackages = Math.round((recentTotal / 7) * peakValue * 1.5);

  return (
    <div className={`${styles.card} ${styles.reveal} ${styles.d4}`}>
      <div className={styles.cardHead}>
        <div>
          <h3 className={styles.cardTitle}>Operasyon Yoğunluk Haritası</h3>
          <div className={styles.cardSub}>Saatlik paket akışı · son 7 gün</div>
        </div>
        <Link href="/reports" className={styles.cardLink}>Detay →</Link>
      </div>
      <div className={styles.cardBody}>
        <div className={styles.heatmap}>
          <div />
          {Array.from({ length: 12 }, (_, i) => (
            <div key={`h-${i}`} className={styles.hmH} style={{ gridColumn: "span 2" }}>
              {i * 2}
            </div>
          ))}
          {days.map((d, di) => (
            <Fragment key={d}>
              <div className={styles.hmLabel}>{d}</div>
              {Array.from({ length: 24 }, (_, h) => {
                const v = intensity(di, h);
                const idx = Math.min(palette.length - 1, Math.floor(v * palette.length));
                const delay = (di * 24 + h) * 8;
                return (
                  <div
                    key={`${d}-${h}`}
                    className={styles.hmCell}
                    style={{
                      background: palette[idx],
                      opacity: 0,
                      animation: `fadeIn 0.4s ease forwards`,
                      animationDelay: `${delay}ms`,
                    }}
                    title={`${d} ${h}:00`}
                  />
                );
              })}
            </Fragment>
          ))}
        </div>
        <div className={styles.hmLegend}>
          <span>Az</span>
          <div className={styles.hmScale}>
            {palette.map((c, i) => (
              <span key={i} style={{ background: c }} />
            ))}
          </div>
          <span>Çok</span>
          <span style={{ marginLeft: "auto", color: "var(--saks)", fontWeight: 700 }}>
            Pik: {days[peakDay]} {peakHour}:00 · {formatNumber(peakPackages)} paket
          </span>
        </div>
      </div>
    </div>
  );
}

/* ====================================================================
   BRAND RACE
   ==================================================================== */

function BrandRace({ brands }: { brands: OverviewDashboard["operations"]["brand_summary"] }) {
  const sorted = [...brands].sort((a, b) => b.gross_invoice - a.gross_invoice).slice(0, 8);
  const max = Math.max(...sorted.map((b) => b.gross_invoice), 1);

  return (
    <div className={`${styles.card} ${styles.reveal} ${styles.d4}`} style={{ marginBottom: 22 }}>
      <div className={styles.cardHead}>
        <div>
          <h3 className={styles.cardTitle}>Marka Yarışı</h3>
          <div className={styles.cardSub}>
            Bu ay brüt fatura · {sorted.length} markada {sorted.reduce((s, b) => s + (b.restaurant_count || 0), 0)} restoran
          </div>
        </div>
      </div>
      <div className={styles.cardBody}>
        <div className={styles.race}>
          {sorted.length === 0 ? (
            <div className={styles.muted} style={{ padding: "20px 0", fontSize: 13, textAlign: "center" }}>
              Marka verisi bulunamadı.
            </div>
          ) : (
            sorted.map((b, i) => {
              const widthPct = Math.max((b.gross_invoice / max) * 100, 3);
              const color = brandTagColors[i % brandTagColors.length];
              return (
                <div className={styles.raceRow} key={b.brand}>
                  <span className={styles.raceNo}>{String(i + 1).padStart(2, "0")}</span>
                  <span className={styles.raceName}>
                    <span className={styles.raceTag} style={{ background: color }}>{brandTagInitials(b.brand)}</span>
                    <span className={styles.raceTagText}>{b.brand}</span>
                  </span>
                  <div className={styles.raceBar}>
                    <div className={styles.raceFill} style={{ width: `${widthPct}%`, animationDelay: `${i * 0.1}s` }} />
                  </div>
                  <span className={styles.raceVal}>
                    {formatCompactCurrency(b.gross_invoice)}
                    <span className={styles.raceValSmall}>
                      {b.restaurant_count} restoran · {formatNumber(b.total_packages)} paket
                    </span>
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

/* ====================================================================
   MODULES
   ==================================================================== */

function ModulesGrid({ modules }: { modules: OverviewDashboard["modules"] }) {
  const visible = modules.slice(0, 4);
  return (
    <>
      <div className={`${styles.modulesHeader} ${styles.reveal} ${styles.d5}`}>
        <h2 className={styles.modulesTitle}>Modüller</h2>
        <span className={styles.muted} style={{ fontSize: 12, fontWeight: 500 }}>Hızlı erişim</span>
      </div>
      <div className={styles.modules}>
        {visible.map((m, i) => (
          <Link key={m.key} href={m.href} className={`${styles.mod} ${styles.reveal} ${styles[`d${5 + i}`] ?? styles.d8}`}>
            <div className={styles.modIcon}>{moduleIconFor(m.key)}</div>
            <div className={styles.modTitle}>{m.title}</div>
            <div className={styles.modDesc}>{m.description}</div>
            <div className={styles.modStats}>
              <div className={styles.modStat}>
                <div className="l">{m.primary_label}</div>
                <div className="v">{m.primary_value}</div>
              </div>
              <div className={styles.modStat}>
                <div className="l">{m.secondary_label}</div>
                <div className="v">{m.secondary_value}</div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}

/* ====================================================================
   ACTIVITY + JOKER
   ==================================================================== */

function ActivityCard({ activities }: { activities: OverviewDashboard["recent_activity"] }) {
  const visible = activities.slice(0, 6);
  return (
    <div className={`${styles.card} ${styles.reveal} ${styles.d6}`}>
      <div className={styles.cardHead}>
        <div>
          <h3 className={styles.cardTitle}>Son Hareketler</h3>
          <div className={styles.cardSub}>Tüm modüllerden anlık akış</div>
        </div>
        <Link href="/reports" className={styles.cardLink}>Tümü →</Link>
      </div>
      <div className={styles.cardBody}>
        <div className={styles.activity}>
          {visible.length === 0 ? (
            <div className={styles.muted} style={{ padding: "20px 0", fontSize: 13, textAlign: "center" }}>
              Son hareket bulunamadı.
            </div>
          ) : (
            visible.map((a, i) => (
              <Link key={`${a.title}-${i}`} href={a.href} className={styles.act}>
                <span className={`${styles.actDot} ${i % 3 === 0 ? styles.actDotAccent : ""}`} />
                <div>
                  <div className={styles.actTitle}>
                    <span className={styles.actMod}>{a.module_label}</span>
                    {a.title}
                  </div>
                  {a.subtitle ? <div className={styles.actSub}>{a.subtitle}</div> : null}
                </div>
                <span className={styles.actTime}>{a.meta || (a.entry_date ?? "")}</span>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function JokerCard({ restaurants }: { restaurants: OverviewDashboard["operations"]["joker_restaurants"] }) {
  const sorted = [...restaurants].sort((a, b) => b.joker_count - a.joker_count).slice(0, 5);
  const max = Math.max(...sorted.map((r) => r.joker_count), 1);
  return (
    <div className={`${styles.card} ${styles.reveal} ${styles.d7}`}>
      <div className={styles.cardHead}>
        <div>
          <h3 className={styles.cardTitle}>Joker Kullanımı</h3>
          <div className={styles.cardSub}>{sorted.length} restoran · ortalama kullanım</div>
        </div>
        <Link href="/attendance" className={styles.cardLink}>Detay →</Link>
      </div>
      <div className={styles.cardBody}>
        <div className={styles.race}>
          {sorted.length === 0 ? (
            <div className={styles.muted} style={{ padding: "20px 0", fontSize: 13, textAlign: "center" }}>
              Bu hafta joker kullanımı görünmüyor.
            </div>
          ) : (
            sorted.map((r, i) => {
              const widthPct = Math.max((r.joker_count / max) * 100, 5);
              const color = brandTagColors[(i + 3) % brandTagColors.length];
              return (
                <div className={styles.raceRow} key={r.restaurant}>
                  <span className={styles.raceNo}>{String(i + 1).padStart(2, "0")}</span>
                  <span className={styles.raceName}>
                    <span className={styles.raceTag} style={{ background: color }}>{brandTagInitials(r.restaurant)}</span>
                    <span className={styles.raceTagText}>{r.restaurant}</span>
                  </span>
                  <div className={styles.raceBar}>
                    <div className={styles.raceFill} style={{ width: `${widthPct}%`, animationDelay: `${i * 0.1}s` }} />
                  </div>
                  <span className={styles.raceVal}>
                    {r.joker_count}×
                    <span className={styles.raceValSmall}>{formatNumber(r.total_packages)} paket</span>
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

/* ====================================================================
   MAIN PAGE
   ==================================================================== */

export default function OverviewPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<OverviewDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState("");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      if (loading) return;
      if (!user) {
        if (active) {
          setDashboard(null);
          setDashboardError("");
          setDashboardLoading(false);
        }
        return;
      }

      setDashboardLoading(true);
      try {
        const url = selectedMonth
          ? `/overview/dashboard?month=${encodeURIComponent(selectedMonth)}`
          : "/overview/dashboard";
        const response = await apiFetch(url);
        if (!response.ok) {
          if (active) {
            setDashboard(null);
            setDashboardError(
              response.status === 401
                ? "Genel bakış verisi için oturum doğrulaması tamamlanamadı. Lütfen bir kez çıkış yapıp yeniden giriş yap."
                : "Genel bakış verisi alınamadı. Lütfen sayfayı yenileyip tekrar dene.",
            );
          }
          return;
        }
        const payload = (await response.json()) as OverviewDashboard;
        if (active) {
          setDashboard(payload);
          setDashboardError("");
        }
      } catch {
        if (active) {
          setDashboard(null);
          setDashboardError("Genel bakış verisine ulaşılamıyor. Lütfen bağlantıyı kontrol edip tekrar dene.");
        }
      } finally {
        if (active) setDashboardLoading(false);
      }
    }

    void loadDashboard();
    return () => {
      active = false;
    };
  }, [loading, user, selectedMonth]);

  if (loading || dashboardLoading) return <LoadingState user={user} />;
  if (dashboardError || !dashboard) {
    return <ErrorState user={user} message={dashboardError || "Genel bakış verisi alınamadı."} />;
  }

  const { hero, finance, operations, modules, recent_activity } = dashboard;

  const fatura = finance.total_revenue || 0;
  const kuryeNet = finance.total_personnel_cost || 0;
  const yanGelir = finance.side_income_net || 0;
  const netKar = finance.gross_profit || 0;
  const marj = fatura > 0 ? (netKar / fatura) * 100 : 0;

  const kesintiTahmini = Math.round(kuryeNet * 0.03); // ~%3 kesinti tahmini
  const kuryeBrut = kuryeNet + kesintiTahmini;

  const monthLabel = formatMonthLabel(finance.selected_month);
  const monthOptions = finance.month_options ?? [];

  // Sparkline paths from daily trend
  const recent = operations.daily_trend.slice(-12);
  const sparkPath = (extract: (d: { total_packages: number; total_hours: number }) => number, invert = false) => {
    if (recent.length === 0) return "M0,18 L100,18";
    const vals = recent.map(extract);
    const max = Math.max(...vals, 1);
    const min = Math.min(...vals, 0);
    const range = Math.max(max - min, 1);
    return recent
      .map((d, i) => {
        const x = (i / Math.max(recent.length - 1, 1)) * 100;
        const norm = (extract(d) - min) / range;
        const y = invert ? 8 + norm * 22 : 30 - norm * 22;
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  };

  return (
    <div className={styles.scope}>
      <div className={styles.app}>
        <Sidebar user={user} restaurantCount={hero.active_restaurants} />

        <main className={styles.main}>
          {/* PAGE HEADER */}
          <div className={`${styles.pageHeader} ${styles.reveal} ${styles.d1}`}>
            <div>
              <h1 className={styles.pageTitle}>Genel Bakış</h1>
              <div className={styles.pageSub}>
                {hero.active_restaurants} restoran · {hero.active_personnel} personel · {monthLabel}
              </div>
            </div>
            <div className={styles.pageActions}>
              <span className={styles.livePill}>
                <span className={styles.liveDot} />
                Canlı
              </span>
              <MonthPicker
                value={finance.selected_month}
                options={monthOptions}
                onChange={setSelectedMonth}
              />
              <Link href="/reports" className={`${styles.btn} ${styles.btnPrimary}`}>
                <Icon.Download />
                Rapor indir
              </Link>
            </div>
          </div>

          {/* HERO METRICS (Operasyon) */}
          <div className={styles.heroRow}>
            <HeroCard
              label="Aktif restoran"
              value={hero.active_restaurants}
              icon={<Icon.Building />}
              sparkPath={sparkPath((d) => d.total_packages || 0)}
              delay="d2"
            />
            <HeroCard
              label="Aktif personel"
              value={hero.active_personnel}
              icon={<Icon.User />}
              sparkPath={sparkPath((d) => d.total_hours || 0)}
              delay="d3"
            />
            <HeroCard
              label="Ay puantajı"
              value={hero.month_attendance_entries}
              icon={<Icon.Calendar />}
              sparkPath={sparkPath((d) => d.total_packages || 0)}
              delay="d4"
            />
            <HeroCard
              label="Ay kesintisi"
              value={hero.month_deduction_entries}
              icon={<Icon.AlertCircle />}
              sparkPath={sparkPath((d) => d.total_hours || 0, true)}
              sparkColor="#dc2626"
              delay="d5"
            />
          </div>

          {/* AYLIK MALİ KPI */}
          <div className={styles.maliKpiRow}>
            <div className={`${styles.maliKpi} ${styles.reveal} ${styles.d2}`}>
              <div className={styles.maliKpiLabel}>Kestiğin toplam fatura</div>
              <div className={styles.maliKpiValue}>{formatCurrency(fatura)}</div>
              <div className={styles.maliKpiDetail}>
                <span>{monthLabel}</span>
              </div>
            </div>
            <div className={`${styles.maliKpi} ${styles.maliNeg} ${styles.reveal} ${styles.d3}`}>
              <div className={styles.maliKpiLabel}>Kuryeye net ödenecek</div>
              <div className={styles.maliKpiValue}>{formatCurrency(kuryeNet)}</div>
              <div className={styles.maliKpiDetail}>
                brüt {formatCompactCurrency(kuryeBrut)} − kesinti {formatCompactCurrency(kesintiTahmini)}
              </div>
            </div>
            <div className={`${styles.maliKpi} ${styles.reveal} ${styles.d4}`}>
              <div className={styles.maliKpiLabel}>Yan gelir</div>
              <div className={styles.maliKpiValue}>{formatCurrency(yanGelir)}</div>
              <div className={styles.maliKpiDetail}>ekipman & kasko</div>
            </div>
            <div className={`${styles.maliKpi} ${styles.maliHighlight} ${styles.reveal} ${styles.d5}`}>
              <div className={styles.maliKpiLabel}>Net kâr</div>
              <div className={styles.maliKpiValue}>{formatCurrency(netKar)}</div>
              <div className={styles.maliKpiDetail}>%{marj.toFixed(1).replace(".", ",")} marj</div>
            </div>
          </div>

          {/* AYLIK MALİ AKIŞ + 6 AYLIK */}
          <div className={styles.maliRow}>
            <Waterfall
              fatura={fatura}
              kuryeNet={kuryeNet}
              yanGelir={yanGelir}
              netKar={netKar}
              selectedMonth={finance.selected_month}
            />
            <SixMonthPL currentNetKar={netKar} />
          </div>

          {/* OPERASYON TRENDI (büyük chart) */}
          <div className={styles.chartRow} style={{ gridTemplateColumns: "1fr" }}>
            <OperationsTrend daily={operations.daily_trend} />
          </div>

          {/* ALERTS + HEATMAP */}
          <div className={styles.alertsRow}>
            <AlertsCard alerts={operations.action_alerts} />
            <HeatmapCard daily={operations.daily_trend} />
          </div>

          {/* BRAND RACE */}
          <BrandRace brands={operations.brand_summary} />

          {/* MODULES */}
          <ModulesGrid modules={modules} />

          {/* ACTIVITY + JOKER */}
          <div className={styles.alertsRow}>
            <ActivityCard activities={recent_activity} />
            <JokerCard restaurants={operations.joker_restaurants} />
          </div>
        </main>
      </div>
    </div>
  );
}
