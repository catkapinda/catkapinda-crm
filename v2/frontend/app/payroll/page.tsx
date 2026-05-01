"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";
import styles from "./payroll-intelligence.module.css";

type PayrollDashboard = {
  module: string;
  status: string;
  month_options: string[];
  selected_month: string | null;
  role_options: string[];
  restaurant_options: string[];
  selected_role: string;
  selected_restaurant: string;
  summary: {
    selected_month: string;
    personnel_count: number;
    total_hours: number;
    total_packages: number;
    gross_payroll: number;
    total_deductions: number;
    total_tevkifat: number;
    net_payment: number;
  } | null;
  entries: Array<{
    personnel_id: number;
    personnel: string;
    role: string;
    status: string;
    total_hours: number;
    total_packages: number;
    gross_pay: number;
    total_deductions: number;
    tevkifat_amount: number;
    net_payment: number;
    restaurant_count: number;
    cost_model: string;
  }>;
  cost_model_breakdown: Array<{
    cost_model: string;
    personnel_count: number;
    total_hours: number;
    total_packages: number;
    net_payment: number;
  }>;
};

type DeductionRecord = {
  id: number;
  personnel_id: number;
  personnel_label: string;
  deduction_date: string;
  deduction_type: string;
  type_caption: string;
  amount: number;
  notes: string;
};

type DeductionsManagementResponse = {
  total_entries: number;
  entries: DeductionRecord[];
};

type PayrollDeltaTone = "positive" | "negative" | "neutral";
type PayrollTab = "finance" | "operations" | "trend" | "pdf";
type PayrollViewMode = "overview" | "list";

type PayrollEntryView = PayrollDashboard["entries"][number];

type MonthlySeriesItem = {
  month: string;
  label: string;
  summary: NonNullable<PayrollDashboard["summary"]> | null;
  entries: PayrollDashboard["entries"];
};

type DeductionListItem = {
  key: number | string;
  label: string;
  amount: number;
};

type DeltaView = {
  label: string;
  tone: PayrollDeltaTone;
};

type IconName =
  | "wallet"
  | "receipt"
  | "minus-circle"
  | "shield"
  | "calendar"
  | "download"
  | "trend"
  | "pie"
  | "activity";

const COST_MODEL_LABELS: Record<string, string> = {
  hourly_plus_package: "Saatlik",
  threshold_package: "Paket Başı",
  hourly_only: "Günlük",
  fixed_monthly: "Diğer",
};

const DONUT_COLORS = ["#2563EB", "#5B8CFF", "#8EB5FF", "#D7E5FF"];

function IconGlyph({
  name,
  className,
}: {
  name: IconName;
  className?: string;
}) {
  switch (name) {
    case "wallet":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
          <path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H18a2 2 0 0 1 2 2v1.5H8.5A2.5 2.5 0 0 0 6 11v2a2.5 2.5 0 0 0 2.5 2.5H20V17a2 2 0 0 1-2 2H5.5A2.5 2.5 0 0 1 3 16.5z" />
          <path d="M20 8.5h-11A2.5 2.5 0 0 0 6.5 11v2A2.5 2.5 0 0 0 9 15.5h11A1.5 1.5 0 0 0 21.5 14V10A1.5 1.5 0 0 0 20 8.5Z" />
          <circle cx="16.5" cy="12" r="1" fill="currentColor" stroke="none" />
        </svg>
      );
    case "receipt":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
          <path d="M6 3.5h12v17l-2.25-1.5L13.5 20l-2.25-1.5L9 20l-3-1.5z" />
          <path d="M9 8h6" />
          <path d="M9 12h6" />
          <path d="M9 16h4" />
        </svg>
      );
    case "minus-circle":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
          <circle cx="12" cy="12" r="8.5" />
          <path d="M8.5 12h7" />
        </svg>
      );
    case "shield":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
          <path d="M12 3.5 18.5 6v5c0 4.1-2.45 7.45-6.5 9-4.05-1.55-6.5-4.9-6.5-9V6z" />
          <path d="m9.25 12 1.75 1.75L15 9.75" />
        </svg>
      );
    case "calendar":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
          <rect x="4" y="5" width="16" height="15" rx="3" />
          <path d="M8 3.5v3" />
          <path d="M16 3.5v3" />
          <path d="M4 9.5h16" />
        </svg>
      );
    case "download":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
          <path d="M12 4.5v10" />
          <path d="m8.5 11.5 3.5 3.5 3.5-3.5" />
          <path d="M5 18.5h14" />
        </svg>
      );
    case "trend":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
          <path d="m4.5 15.5 5-5 4 4 6-7" />
          <path d="M15.5 7.5h4v4" />
        </svg>
      );
    case "pie":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
          <path d="M12 3.5a8.5 8.5 0 1 0 8.5 8.5H12z" />
          <path d="M12 3.5a8.5 8.5 0 0 1 8.5 8.5H12z" />
        </svg>
      );
    case "activity":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
          <path d="M4 12h3l2.5-5 5 10 2.5-5H20" />
        </svg>
      );
      default:
        return null;
  }
}

function toSafeNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function normalizePayrollDashboard(payload: Partial<PayrollDashboard>): PayrollDashboard {
  const summary =
    payload.summary && typeof payload.summary === "object"
      ? {
          selected_month: toSafeString(payload.summary.selected_month),
          personnel_count: toSafeNumber(payload.summary.personnel_count),
          total_hours: toSafeNumber(payload.summary.total_hours),
          total_packages: toSafeNumber(payload.summary.total_packages),
          gross_payroll: toSafeNumber(payload.summary.gross_payroll),
          total_deductions: toSafeNumber(payload.summary.total_deductions),
          total_tevkifat: toSafeNumber(payload.summary.total_tevkifat),
          net_payment: toSafeNumber(payload.summary.net_payment),
        }
      : null;

  return {
    module: toSafeString(payload.module, "payroll"),
    status: toSafeString(payload.status, "active"),
    month_options: Array.isArray(payload.month_options)
      ? payload.month_options.map((item) => toSafeString(item)).filter(Boolean)
      : [],
    selected_month: typeof payload.selected_month === "string" ? payload.selected_month : null,
    role_options: Array.isArray(payload.role_options)
      ? payload.role_options.map((item) => toSafeString(item)).filter(Boolean)
      : [],
    restaurant_options: Array.isArray(payload.restaurant_options)
      ? payload.restaurant_options.map((item) => toSafeString(item)).filter(Boolean)
      : [],
    selected_role: toSafeString(payload.selected_role, "Tümü"),
    selected_restaurant: toSafeString(payload.selected_restaurant, "Tümü"),
    summary,
    entries: Array.isArray(payload.entries)
      ? payload.entries.map((entry) => ({
          personnel_id: toSafeNumber(entry.personnel_id),
          personnel: toSafeString(entry.personnel, "-"),
          role: toSafeString(entry.role, "-"),
          status: toSafeString(entry.status, "-"),
          total_hours: toSafeNumber(entry.total_hours),
          total_packages: toSafeNumber(entry.total_packages),
          gross_pay: toSafeNumber(entry.gross_pay),
          total_deductions: toSafeNumber(entry.total_deductions),
          tevkifat_amount: toSafeNumber(entry.tevkifat_amount),
          net_payment: toSafeNumber(entry.net_payment),
          restaurant_count: toSafeNumber(entry.restaurant_count),
          cost_model: toSafeString(entry.cost_model, "-"),
        }))
      : [],
    cost_model_breakdown: Array.isArray(payload.cost_model_breakdown)
      ? payload.cost_model_breakdown.map((row) => ({
          cost_model: toSafeString(row.cost_model, "-"),
          personnel_count: toSafeNumber(row.personnel_count),
          total_hours: toSafeNumber(row.total_hours),
          total_packages: toSafeNumber(row.total_packages),
          net_payment: toSafeNumber(row.net_payment),
        }))
      : [],
  };
}

function formatMoney(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  })
    .format(value || 0)
    .replace("₺", "")
    .trim()
    .concat(" ₺");
}

function formatNumber(value: number, decimals = 0) {
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value || 0);
}

function monthToLabel(month: string) {
  const [year, rawMonth] = month.split("-");
  const parsedYear = Number(year);
  const parsedMonth = Number(rawMonth);
  if (!parsedYear || !parsedMonth) {
    return month;
  }
  return new Intl.DateTimeFormat("tr-TR", {
    month: "short",
    year: "2-digit",
  })
    .format(new Date(Date.UTC(parsedYear, parsedMonth - 1, 1)))
    .replace(".", "");
}

function triggerBrowserDownload(blob: Blob, fileName: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function getInitials(value: string) {
  return value
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase("tr-TR") ?? "")
    .join("");
}

function displayCostModel(value: string) {
  return COST_MODEL_LABELS[value] ?? value;
}

function buildDelta(current: number, previous: number, positiveIsGood: boolean): DeltaView {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) {
    return {
      label: "Kıyas verisi yok",
      tone: "neutral",
    };
  }

  const ratio = ((current - previous) / previous) * 100;
  if (Math.abs(ratio) < 0.1) {
    return {
      label: "Değişim sınırlı",
      tone: "neutral",
    };
  }

  const improved = positiveIsGood ? ratio > 0 : ratio < 0;
  return {
    label: `${ratio > 0 ? "+" : ""}${formatNumber(ratio, 1)}% geçen aya göre`,
    tone: improved ? "positive" : "negative",
  };
}

function buildLinePath(values: number[], width: number, height: number, padding = 20) {
  if (!values.length) {
    return { path: "", points: [] as Array<{ x: number; y: number; value: number }> };
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;
  const points = values.map((value, index) => {
    const x =
      padding + (values.length === 1 ? chartWidth / 2 : (chartWidth / (values.length - 1)) * index);
    const y = padding + chartHeight - ((value - min) / range) * chartHeight;
    return { x, y, value };
  });
  const path = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ");
  return { path, points, min, max };
}

function buildAreaPath(points: Array<{ x: number; y: number }>, height: number, padding = 20) {
  if (!points.length) {
    return "";
  }
  const bottom = height - padding;
  return `${points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ")} L ${points[points.length - 1].x.toFixed(2)} ${bottom.toFixed(2)} L ${points[0].x.toFixed(2)} ${bottom.toFixed(2)} Z`;
}

function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLocaleLowerCase("tr-TR");
  const tone = normalized.includes("aktif")
    ? styles.payintStatusActive
    : normalized.includes("pasif")
      ? styles.payintStatusMuted
      : styles.payintStatusInfo;
  return <span className={`${styles.payintStatusBadge} ${tone}`}>{value || "—"}</span>;
}

function DeltaBadge({ delta }: { delta: DeltaView }) {
  return (
    <span
      className={`${styles.payintDeltaBadge} ${
        delta.tone === "positive"
          ? styles.payintDeltaPositive
          : delta.tone === "negative"
            ? styles.payintDeltaNegative
            : styles.payintDeltaNeutral
      }`}
    >
      {delta.label}
    </span>
  );
}

function KpiCard({
  title,
  value,
  delta,
  tone,
  icon,
}: {
  title: string;
  value: string;
  delta: DeltaView;
  tone: "blue" | "green" | "orange" | "violet";
  icon: IconName;
}) {
  return (
    <article className={styles.payintKpiCard}>
      <div className={styles.payintKpiHeader}>
        <span className={`${styles.payintKpiIconBadge} ${styles[`payintKpiDot${tone}`]}`}>
          <IconGlyph name={icon} className={styles.payintKpiIcon} />
        </span>
        <span className={styles.payintKpiLabel}>{title}</span>
      </div>
      <div className={styles.payintKpiValue}>{value}</div>
      <DeltaBadge delta={delta} />
    </article>
  );
}

function TrendChart({ items }: { items: Array<{ label: string; value: number }> }) {
  const width = 760;
  const height = 260;
  const { path, points, min, max } = buildLinePath(
    items.length ? items.map((item) => item.value) : [0],
    width,
    height,
    26,
  );
  const safeMin = min ?? 0;
  const safeMax = max ?? safeMin;
  const areaPath = buildAreaPath(points, height, 26);
  const ticks = Array.from({ length: 4 }, (_, index) =>
    safeMin + (((safeMax - safeMin) || 1) / 3) * index,
  ).reverse();

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={styles.payintTrendChart} role="img" aria-label="Hakediş trendi">
      <defs>
        <linearGradient id="payintTrendFill" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="rgba(37, 99, 235, 0.18)" />
          <stop offset="100%" stopColor="rgba(37, 99, 235, 0)" />
        </linearGradient>
      </defs>
      {ticks.map((tick, index) => {
        const y = 26 + ((height - 52) / 3) * index;
        return (
          <g key={`tick-${tick}-${index}`}>
            <line x1="26" x2={width - 26} y1={y} y2={y} className={styles.payintTrendGridLine} />
            <text x="0" y={y + 4} className={styles.payintTrendAxisLabel}>
              {formatMoney(tick)}
            </text>
          </g>
        );
      })}
      {areaPath ? <path d={areaPath} fill="url(#payintTrendFill)" /> : null}
      {path ? <path d={path} className={styles.payintTrendLine} /> : null}
      {points.map((point, index) => (
        <g key={`point-${items[index]?.label ?? index}`}>
          <circle cx={point.x} cy={point.y} r="4.5" className={styles.payintTrendPoint} />
          <text x={point.x} y={point.y - 14} textAnchor="middle" className={styles.payintTrendValue}>
            {formatMoney(point.value)}
          </text>
          <text x={point.x} y={height - 4} textAnchor="middle" className={styles.payintTrendMonth}>
            {items[index]?.label ?? ""}
          </text>
        </g>
      ))}
    </svg>
  );
}

function Sparkline({
  values,
  strokeClassName,
}: {
  values: number[];
  strokeClassName: string;
}) {
  const width = 120;
  const height = 40;
  const { path } = buildLinePath(values.length ? values : [0], width, height, 6);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={styles.payintSparkline} role="img" aria-hidden="true">
      <path d={path} className={strokeClassName} />
    </svg>
  );
}

function DonutChart({
  items,
  total,
}: {
  items: Array<{ label: string; value: number; color: string; percentage: number }>;
  total: number;
}) {
  const radius = 54;
  const strokeWidth = 16;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div className={styles.payintDonutShell}>
      <svg viewBox="0 0 160 160" className={styles.payintDonutChart} role="img" aria-label="Maliyet modeli dağılımı">
        <circle
          cx="80"
          cy="80"
          r={radius}
          fill="none"
          stroke="rgba(148, 163, 184, 0.18)"
          strokeWidth={strokeWidth}
        />
        {items.map((item) => {
          const ratio = total > 0 ? item.value / total : 0;
          const dash = circumference * ratio;
          const strokeDasharray = `${dash} ${circumference - dash}`;
          const currentOffset = offset;
          offset += dash;
          return (
            <circle
              key={item.label}
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke={item.color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={strokeDasharray}
              strokeDashoffset={-currentOffset}
              transform="rotate(-90 80 80)"
            />
          );
        })}
      </svg>
      <div className={styles.payintDonutTotal}>
        <strong>{formatMoney(total)}</strong>
        <span>Toplam hakediş</span>
      </div>
    </div>
  );
}

function LeaderboardCard({
  title,
  items,
  valueFormatter,
  onSelect,
  onViewAll,
  selectedPersonnelId,
}: {
  title: string;
  items: Array<{
    id: number;
    name: string;
    role: string;
    value: number;
    subValue?: string;
  }>;
  valueFormatter: (value: number) => string;
  onSelect: (id: number) => void;
  onViewAll: () => void;
  selectedPersonnelId: number | null;
}) {
  return (
    <section className={styles.payintLeaderboardCard}>
      <div className={styles.payintSectionHeaderCompact}>
        <h3>{title}</h3>
        <button type="button" className={styles.payintTextLinkButton} onClick={onViewAll}>
          Tümünü Gör
        </button>
      </div>
      <div className={styles.payintLeaderboardList}>
        {items.length ? (
          items.map((item, index) => (
            <button
              key={`${title}-${item.id}`}
              type="button"
              className={`${styles.payintLeaderboardItem} ${
                selectedPersonnelId === item.id ? styles.payintLeaderboardItemSelected : ""
              }`}
              onClick={() => onSelect(item.id)}
            >
              <span className={styles.payintLeaderboardRank}>{index + 1}</span>
              <span className={styles.payintLeaderboardAvatar}>{getInitials(item.name)}</span>
              <span className={styles.payintLeaderboardCopy}>
                <strong>{item.name}</strong>
                <small>
                  {item.role}
                  {item.subValue ? ` • ${item.subValue}` : ""}
                </small>
              </span>
              <span className={styles.payintLeaderboardValue}>{valueFormatter(item.value)}</span>
            </button>
          ))
        ) : (
          <div className={styles.payintEmptyCompact}>Seçili filtrede sıralama oluşmadı.</div>
        )}
      </div>
    </section>
  );
}

export default function PayrollPage() {
  const { user, loading } = useAuth();
  const [viewMode, setViewMode] = useState<PayrollViewMode>("overview");
  const [dashboard, setDashboard] = useState<PayrollDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [selectedRole, setSelectedRole] = useState("Tümü");
  const [selectedRestaurant, setSelectedRestaurant] = useState("Tümü");
  const [personnelQuery, setPersonnelQuery] = useState("");
  const [sortMode, setSortMode] = useState("net-desc");
  const [selectedPersonnelId, setSelectedPersonnelId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<PayrollTab>("finance");
  const [documentBusy, setDocumentBusy] = useState(false);
  const [documentError, setDocumentError] = useState("");
  const [documentMessage, setDocumentMessage] = useState("");
  const [monthlySeries, setMonthlySeries] = useState<MonthlySeriesItem[]>([]);
  const [deductionEntries, setDeductionEntries] = useState<DeductionRecord[]>([]);
  const [deductionLoading, setDeductionLoading] = useState(false);
  const deferredPersonnelQuery = useDeferredValue(personnelQuery);

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      if (loading) {
        return;
      }
      if (!user) {
        if (active) {
          setDashboard(null);
          setDashboardLoading(false);
        }
        return;
      }

      setDashboardLoading(true);
      try {
        const params = new URLSearchParams();
        if (selectedMonth) {
          params.set("month", selectedMonth);
        }
        if (selectedRole && selectedRole !== "Tümü") {
          params.set("role", selectedRole);
        }
        if (selectedRestaurant && selectedRestaurant !== "Tümü") {
          params.set("restaurant", selectedRestaurant);
        }
        params.set("limit", "500");

        const response = await apiFetch(`/payroll/dashboard?${params.toString()}`);
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }

        const payload = normalizePayrollDashboard((await response.json()) as Partial<PayrollDashboard>);
        if (!selectedMonth && payload.selected_month) {
          setSelectedMonth(payload.selected_month);
        }
        if (active) {
          setDashboard(payload);
        }
      } catch {
        if (active) {
          setDashboard(null);
        }
      } finally {
        if (active) {
          setDashboardLoading(false);
        }
      }
    }

    void loadDashboard();
    return () => {
      active = false;
    };
  }, [loading, selectedMonth, selectedRestaurant, selectedRole, user]);

  const monthWindow = useMemo(() => {
    if (!dashboard?.month_options?.length) {
      return [];
    }
    const targetMonth = dashboard.selected_month || selectedMonth || dashboard.month_options[0];
    const index = dashboard.month_options.indexOf(targetMonth);
    const startIndex = index === -1 ? 0 : index;
    return dashboard.month_options.slice(startIndex, startIndex + 6).reverse();
  }, [dashboard?.month_options, dashboard?.selected_month, selectedMonth]);

  useEffect(() => {
    let active = true;

    async function loadMonthlySeries() {
      if (!user || !monthWindow.length) {
        if (active) {
          setMonthlySeries([]);
        }
        return;
      }

      try {
        const snapshots = await Promise.all(
          monthWindow.map(async (month) => {
            const params = new URLSearchParams({ month, limit: "500" });
            if (selectedRole && selectedRole !== "Tümü") {
              params.set("role", selectedRole);
            }
            if (selectedRestaurant && selectedRestaurant !== "Tümü") {
              params.set("restaurant", selectedRestaurant);
            }
            const response = await apiFetch(`/payroll/dashboard?${params.toString()}`);
            if (!response.ok) {
              return null;
            }
            const payload = normalizePayrollDashboard(
              (await response.json()) as Partial<PayrollDashboard>,
            );
            return {
              month,
              label: monthToLabel(month),
              summary: payload.summary,
              entries: payload.entries,
            } satisfies MonthlySeriesItem;
          }),
        );
        if (active) {
          setMonthlySeries(snapshots.filter(Boolean) as MonthlySeriesItem[]);
        }
      } catch {
        if (active) {
          setMonthlySeries([]);
        }
      }
    }

    void loadMonthlySeries();
    return () => {
      active = false;
    };
  }, [monthWindow, selectedRestaurant, selectedRole, user]);

  const filteredEntries = useMemo(() => {
    const rows = dashboard?.entries ?? [];
    const query = deferredPersonnelQuery.trim().toLocaleLowerCase("tr-TR");
    if (!query) {
      return rows;
    }
    return rows.filter((row) =>
      `${row.personnel} ${row.role} ${row.cost_model}`.toLocaleLowerCase("tr-TR").includes(query),
    );
  }, [dashboard?.entries, deferredPersonnelQuery]);

  const listEntries = useMemo(() => {
    const rows = [...filteredEntries];
    switch (sortMode) {
      case "name-asc":
        return rows.sort((left, right) => left.personnel.localeCompare(right.personnel, "tr"));
      case "gross-desc":
        return rows.sort((left, right) => right.gross_pay - left.gross_pay);
      case "deduction-desc":
        return rows.sort((left, right) => right.total_deductions - left.total_deductions);
      case "tevkifat-desc":
        return rows.sort((left, right) => right.tevkifat_amount - left.tevkifat_amount);
      case "net-desc":
      default:
        return rows.sort((left, right) => right.net_payment - left.net_payment);
    }
  }, [filteredEntries, sortMode]);

  useEffect(() => {
    if (!filteredEntries.length) {
      setSelectedPersonnelId(null);
      return;
    }

    if (!selectedPersonnelId || !filteredEntries.some((entry) => entry.personnel_id === selectedPersonnelId)) {
      setSelectedPersonnelId(filteredEntries[0].personnel_id);
    }
  }, [filteredEntries, selectedPersonnelId]);

  const payrollOverview = useMemo(() => {
    const summary = dashboard?.summary;
    return {
      selectedMonth: summary?.selected_month ?? selectedMonth,
      personnelCount: summary?.personnel_count ?? 0,
      totalHours: summary?.total_hours ?? 0,
      totalPackages: summary?.total_packages ?? 0,
      grossPayroll: summary?.gross_payroll ?? 0,
      totalDeductions: summary?.total_deductions ?? 0,
      totalTevkifat: summary?.total_tevkifat ?? 0,
      netPayment: summary?.net_payment ?? 0,
    };
  }, [dashboard?.summary, selectedMonth]);

  const previousSeries = useMemo(() => {
    if (!payrollOverview.selectedMonth) {
      return null;
    }
    const index = monthlySeries.findIndex((item) => item.month === payrollOverview.selectedMonth);
    if (index <= 0) {
      return null;
    }
    return monthlySeries[index - 1];
  }, [monthlySeries, payrollOverview.selectedMonth]);

  const trendSeries = useMemo(
    () =>
      monthlySeries.map((item) => ({
        label: item.label,
        value: item.summary?.gross_payroll ?? 0,
      })),
    [monthlySeries],
  );

  const trendInsight = useMemo(() => {
    if (trendSeries.length < 2) {
      return "Kıyas verisi geldikçe trend içgörüsü burada görünecek.";
    }
    const first = trendSeries[0]?.value ?? 0;
    const last = trendSeries[trendSeries.length - 1]?.value ?? 0;
    if (first <= 0) {
      return "Önceki dönem baz verisi oluşmadı.";
    }
    const ratio = ((last - first) / first) * 100;
    return `Son ${trendSeries.length} ayda hakediş tutarı ${formatNumber(
      Math.abs(ratio),
      1,
    )}% ${ratio >= 0 ? "artış" : "daralma"} gösterdi.`;
  }, [trendSeries]);

  const costModelItems = useMemo(() => {
    const totals = new Map<string, number>();
    filteredEntries.forEach((entry) => {
      totals.set(entry.cost_model, (totals.get(entry.cost_model) ?? 0) + entry.gross_pay);
    });
    const total = Array.from(totals.values()).reduce((sum, value) => sum + value, 0);
    return Array.from(totals.entries())
      .map(([costModel, value], index) => ({
        label: displayCostModel(costModel),
        value,
        color: DONUT_COLORS[index % DONUT_COLORS.length],
        percentage: total > 0 ? (value / total) * 100 : 0,
      }))
      .sort((left, right) => right.value - left.value);
  }, [filteredEntries]);

  const dominantCostModelInsight = useMemo(() => {
    const top = costModelItems[0];
    if (!top) {
      return "Model dağılımı oluştuğunda baskın hakediş yapısı burada okunacak.";
    }
    return `Hakedişin ${formatNumber(top.percentage, 0)}%'si ${top.label.toLocaleLowerCase(
      "tr-TR",
    )} modelden geliyor.`;
  }, [costModelItems]);

  const totalGrossByModel = useMemo(
    () => costModelItems.reduce((sum, item) => sum + item.value, 0),
    [costModelItems],
  );

  const productivitySeries = useMemo(() => {
    return {
      packagesPerHour: monthlySeries.map((item) => {
        const hours = item.summary?.total_hours ?? 0;
        const packages = item.summary?.total_packages ?? 0;
        return hours > 0 ? packages / hours : 0;
      }),
      totalPackages: monthlySeries.map((item) => item.summary?.total_packages ?? 0),
      totalHours: monthlySeries.map((item) => item.summary?.total_hours ?? 0),
    };
  }, [monthlySeries]);

  const currentPackagesPerHour =
    payrollOverview.totalHours > 0 ? payrollOverview.totalPackages / payrollOverview.totalHours : 0;

  const previousPackagesPerHour =
    (previousSeries?.summary?.total_hours ?? 0) > 0
      ? (previousSeries?.summary?.total_packages ?? 0) /
        (previousSeries?.summary?.total_hours ?? 1)
      : 0;

  const packagesPerHourDelta = buildDelta(currentPackagesPerHour, previousPackagesPerHour, true);
  const totalPackagesDelta = buildDelta(
    payrollOverview.totalPackages,
    previousSeries?.summary?.total_packages ?? 0,
    true,
  );
  const totalHoursDelta = buildDelta(
    payrollOverview.totalHours,
    previousSeries?.summary?.total_hours ?? 0,
    true,
  );

  const selectedPersonnel = useMemo(
    () => filteredEntries.find((entry) => entry.personnel_id === selectedPersonnelId) ?? null,
    [filteredEntries, selectedPersonnelId],
  );

  const highestNetPayment = useMemo(
    () =>
      [...filteredEntries]
        .sort((left, right) => right.net_payment - left.net_payment)
        .slice(0, 3)
        .map((entry) => ({
          id: entry.personnel_id,
          name: entry.personnel,
          role: entry.role,
          value: entry.net_payment,
        })),
    [filteredEntries],
  );

  const highestDeduction = useMemo(
    () =>
      [...filteredEntries]
        .sort((left, right) => right.total_deductions - left.total_deductions)
        .slice(0, 3)
        .map((entry) => ({
          id: entry.personnel_id,
          name: entry.personnel,
          role: entry.role,
          value: entry.total_deductions,
        })),
    [filteredEntries],
  );

  const mostEfficient = useMemo(
    () =>
      [...filteredEntries]
        .filter((entry) => entry.total_hours > 0)
        .sort(
          (left, right) =>
            right.total_packages / right.total_hours - left.total_packages / left.total_hours,
        )
        .slice(0, 3)
        .map((entry) => ({
          id: entry.personnel_id,
          name: entry.personnel,
          role: entry.role,
          value: entry.total_packages / entry.total_hours,
        })),
    [filteredEntries],
  );

  const personTrendSeries = useMemo(() => {
    if (!selectedPersonnelId) {
      return [];
    }
    return monthlySeries.map((item) => {
      const personEntry = item.entries.find((entry) => entry.personnel_id === selectedPersonnelId);
      return {
        label: item.label,
        value: personEntry?.net_payment ?? 0,
      };
    });
  }, [monthlySeries, selectedPersonnelId]);

  const personTrendInsight = useMemo(() => {
    if (personTrendSeries.length < 2) {
      return "Seçili personelin aylık trendi oluştukça burada içgörü görünecek.";
    }
    const first = personTrendSeries[0]?.value ?? 0;
    const last = personTrendSeries[personTrendSeries.length - 1]?.value ?? 0;
    if (first <= 0) {
      return "Bu kişi için önceki dönem kıyası oluşmadı.";
    }
    const ratio = ((last - first) / first) * 100;
    return `Seçili personelin net ödemesi ${personTrendSeries.length} aylık hatta ${formatNumber(
      Math.abs(ratio),
      1,
    )}% ${ratio >= 0 ? "artış" : "gerileme"} gösteriyor.`;
  }, [personTrendSeries]);

  useEffect(() => {
    let active = true;

    async function loadDeductions() {
      if (!user || !selectedPersonnel) {
        if (active) {
          setDeductionEntries([]);
          setDeductionLoading(false);
        }
        return;
      }

      setDeductionLoading(true);
      try {
        const params = new URLSearchParams({
          personnel_id: String(selectedPersonnel.personnel_id),
          limit: "60",
        });
        const response = await apiFetch(`/deductions/records?${params.toString()}`);
        if (!response.ok) {
          if (active) {
            setDeductionEntries([]);
          }
          return;
        }
        const payload = (await response.json()) as DeductionsManagementResponse;
        const monthPrefix = (dashboard?.selected_month || selectedMonth || "").trim();
        const rows = (payload.entries ?? []).filter((entry) =>
          monthPrefix ? String(entry.deduction_date).startsWith(monthPrefix) : true,
        );
        if (active) {
          setDeductionEntries(rows);
        }
      } catch {
        if (active) {
          setDeductionEntries([]);
        }
      } finally {
        if (active) {
          setDeductionLoading(false);
        }
      }
    }

    void loadDeductions();
    return () => {
      active = false;
    };
  }, [dashboard?.selected_month, selectedMonth, selectedPersonnel, user]);

  const selectedPersonDeductions = useMemo(() => {
    if (!selectedPersonnel) {
      return [] as DeductionListItem[];
    }

    const rows: DeductionListItem[] = deductionEntries.map((entry) => ({
      key: entry.id,
      label: entry.type_caption || entry.deduction_type || "Kesinti",
      amount: entry.amount,
    }));
    const hasTevkifat = rows.some((row) =>
      row.label.toLocaleLowerCase("tr-TR").includes("tevkifat"),
    );
    if (!hasTevkifat && selectedPersonnel.tevkifat_amount > 0) {
      rows.push({
        key: "tevkifat",
        label: "Tevkifat",
        amount: selectedPersonnel.tevkifat_amount,
      });
    }
    const knownTotal = rows.reduce((sum, row) => sum + row.amount, 0);
    const residual = Math.max(selectedPersonnel.total_deductions - knownTotal, 0);
    if (residual > 0.01) {
      rows.push({
        key: "other",
        label: "Diğer Kesintiler",
        amount: residual,
      });
    }
    return rows;
  }, [deductionEntries, selectedPersonnel]);

  async function handleDocumentDownload() {
    if (!selectedPersonnel) {
      setDocumentError("PDF indirmek için önce personel seçmelisin.");
      setDocumentMessage("");
      return;
    }

    const month = dashboard?.selected_month || selectedMonth;
    if (!month) {
      setDocumentError("PDF indirmek için önce dönem seçmelisin.");
      setDocumentMessage("");
      return;
    }

    setDocumentBusy(true);
    setDocumentError("");
    setDocumentMessage("");
    try {
      const params = new URLSearchParams({
        personnel_id: String(selectedPersonnel.personnel_id),
        month,
      });
      const response = await apiFetch(`/payroll/document?${params.toString()}`);
      if (!response.ok) {
        let detail = "Hakediş PDF'i indirilemedi.";
        try {
          const payload = (await response.json()) as { detail?: string };
          if (payload?.detail) {
            detail = payload.detail;
          }
        } catch {}
        throw new Error(detail);
      }
      const disposition = response.headers.get("Content-Disposition") || "";
      const fileNameMatch = disposition.match(/filename=\"?([^"]+)\"?/i);
      const fileName =
        fileNameMatch?.[1] ||
        `hakedis_${selectedPersonnel.personnel_id}_${month}.pdf`;
      const blob = await response.blob();
      triggerBrowserDownload(blob, fileName);
      setDocumentMessage("Hakediş PDF'i indirildi.");
    } catch (nextError) {
      setDocumentError(
        nextError instanceof Error ? nextError.message : "Hakediş PDF'i indirilemedi.",
      );
    } finally {
      setDocumentBusy(false);
    }
  }

  function handleCsvDownload() {
    if (!filteredEntries.length) {
      setDocumentError("Excel indirmek için görünür kayıt oluşmalı.");
      setDocumentMessage("");
      return;
    }
    const headers = [
      "Personel",
      "Rol",
      "Durum",
      "Net Ödeme",
      "Hakediş Tutarı",
      "Toplam Kesinti",
      "Toplam Tevkifat",
      "Model",
    ];
    const rows = filteredEntries.map((entry) => [
      entry.personnel,
      entry.role,
      entry.status,
      String(entry.net_payment),
      String(entry.gross_pay),
      String(entry.total_deductions),
      String(entry.tevkifat_amount),
      displayCostModel(entry.cost_model),
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const month = dashboard?.selected_month || selectedMonth || "hakedis";
    const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" });
    triggerBrowserDownload(blob, `catkapinda_aylik_hakedis_${month}.csv`);
    setDocumentError("");
    setDocumentMessage("Excel indirildi.");
  }

  const kpis = [
    {
      title: "Net Ödenecek Tutar",
      value: formatMoney(payrollOverview.netPayment),
      delta: buildDelta(
        payrollOverview.netPayment,
        previousSeries?.summary?.net_payment ?? 0,
        true,
      ),
      tone: "blue" as const,
      icon: "wallet" as const,
    },
    {
      title: "Hakediş Tutarı",
      value: formatMoney(payrollOverview.grossPayroll),
      delta: buildDelta(
        payrollOverview.grossPayroll,
        previousSeries?.summary?.gross_payroll ?? 0,
        true,
      ),
      tone: "green" as const,
      icon: "receipt" as const,
    },
    {
      title: "Toplam Kesinti",
      value: formatMoney(payrollOverview.totalDeductions),
      delta: buildDelta(
        payrollOverview.totalDeductions,
        previousSeries?.summary?.total_deductions ?? 0,
        false,
      ),
      tone: "orange" as const,
      icon: "minus-circle" as const,
    },
    {
      title: "Toplam Tevkifat",
      value: formatMoney(payrollOverview.totalTevkifat),
      delta: buildDelta(
        payrollOverview.totalTevkifat,
        previousSeries?.summary?.total_tevkifat ?? 0,
        false,
      ),
      tone: "violet" as const,
      icon: "shield" as const,
    },
  ];

  const detailTabs = [
    { id: "finance", label: "Finans Özeti" },
    { id: "operations", label: "Operasyon Özeti" },
    { id: "trend", label: "Trend" },
    { id: "pdf", label: "PDF" },
  ] satisfies Array<{ id: PayrollTab; label: string }>;

  const detailPanel = (
    <section className={styles.payintDetailPanel}>
      {selectedPersonnel ? (
        <>
          <div className={styles.payintDetailHeader}>
            <div className={styles.payintDetailProfile}>
              <div className={styles.payintDetailAvatar}>{getInitials(selectedPersonnel.personnel)}</div>
              <div className={styles.payintDetailCopy}>
                <h3>{selectedPersonnel.personnel}</h3>
                <p>{selectedPersonnel.role}</p>
              </div>
            </div>
            <div className={styles.payintDetailStatusRow}>
              <StatusBadge value={selectedPersonnel.status} />
              <button type="button" className={styles.payintKebabButton} aria-label="Detay menüsü">
                <span />
                <span />
                <span />
              </button>
            </div>
          </div>
          <div className={styles.payintTabStrip} role="tablist" aria-label="Personel detay sekmeleri">
            {detailTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`${styles.payintTabButton} ${
                  activeTab === tab.id ? styles.payintTabButtonActive : ""
                }`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === "finance" ? (
            <div className={styles.payintDetailBody}>
              <div className={styles.payintDetailMetricGrid}>
                <article className={styles.payintDetailMetricCard}>
                  <span>Net Ödeme</span>
                  <strong>{formatMoney(selectedPersonnel.net_payment)}</strong>
                </article>
                <article className={styles.payintDetailMetricCard}>
                  <span>Hakediş Tutarı</span>
                  <strong>{formatMoney(selectedPersonnel.gross_pay)}</strong>
                </article>
                <article className={styles.payintDetailMetricCard}>
                  <span>Toplam Kesinti</span>
                  <strong>{formatMoney(selectedPersonnel.total_deductions)}</strong>
                </article>
                <article className={styles.payintDetailMetricCard}>
                  <span>Toplam Tevkifat</span>
                  <strong>{formatMoney(selectedPersonnel.tevkifat_amount)}</strong>
                </article>
              </div>

              <div className={styles.payintDetailListCard}>
                <div className={styles.payintDetailListHead}>
                  <h4>Kesinti Kalemleri</h4>
                  {deductionLoading ? <span>Yükleniyor…</span> : null}
                </div>
                <div className={styles.payintDetailListRows}>
                  {selectedPersonDeductions.length ? (
                    selectedPersonDeductions.map((row) => (
                      <div key={String(row.key)} className={styles.payintDetailListRow}>
                        <span>{row.label}</span>
                        <strong className={styles.payintNegativeText}>{formatMoney(row.amount)}</strong>
                      </div>
                    ))
                  ) : (
                    <div className={styles.payintEmptyCompact}>Bu kişi için seçili ayda kesinti oluşmadı.</div>
                  )}
                </div>
                <div className={styles.payintDetailListTotal}>
                  <span>Toplam Kesinti</span>
                  <strong>{formatMoney(selectedPersonnel.total_deductions)}</strong>
                </div>
              </div>
            </div>
          ) : null}

          {activeTab === "operations" ? (
            <div className={styles.payintDetailBody}>
              <div className={styles.payintDetailMetricGrid}>
                <article className={styles.payintDetailMetricCard}>
                  <span>Toplam Saat</span>
                  <strong>{formatNumber(selectedPersonnel.total_hours, 1)}</strong>
                </article>
                <article className={styles.payintDetailMetricCard}>
                  <span>Toplam Paket</span>
                  <strong>{formatNumber(selectedPersonnel.total_packages, 0)}</strong>
                </article>
                <article className={styles.payintDetailMetricCard}>
                  <span>Toplam Şube</span>
                  <strong>{formatNumber(selectedPersonnel.restaurant_count, 0)}</strong>
                </article>
                <article className={styles.payintDetailMetricCard}>
                  <span>Paket / Saat</span>
                  <strong>
                    {selectedPersonnel.total_hours > 0
                      ? formatNumber(selectedPersonnel.total_packages / selectedPersonnel.total_hours, 1)
                      : "0,0"}
                  </strong>
                </article>
              </div>
            </div>
          ) : null}

          {activeTab === "trend" ? (
            <div className={styles.payintDetailBody}>
              <div className={styles.payintDetailTrendCard}>
                <TrendChart
                  items={personTrendSeries.length ? personTrendSeries : [{ label: "—", value: 0 }]}
                />
              </div>
              <div className={styles.payintInsightCard}>{personTrendInsight}</div>
            </div>
          ) : null}

          {activeTab === "pdf" ? (
            <div className={styles.payintDetailBody}>
              <button
                type="button"
                className={styles.payintPrimaryButton}
                onClick={handleDocumentDownload}
                disabled={documentBusy}
              >
                {documentBusy ? "PDF hazırlanıyor..." : "Hakediş PDF’i İndir"}
              </button>
              {documentError ? (
                <div className={`${styles.payintFeedback} ${styles.payintFeedbackError}`}>{documentError}</div>
              ) : null}
              {documentMessage ? (
                <div className={`${styles.payintFeedback} ${styles.payintFeedbackSuccess}`}>{documentMessage}</div>
              ) : null}
            </div>
          ) : null}
        </>
      ) : (
        <div className={styles.payintEmptyPanel}>Sağ paneli doldurmak için listeden bir personel seçin.</div>
      )}
    </section>
  );

  const overviewView = (
    <>
      <section className={styles.payintKpiStrip}>
        {kpis.map((kpi) => (
          <KpiCard
            key={kpi.title}
            title={kpi.title}
            value={kpi.value}
            delta={kpi.delta}
            tone={kpi.tone}
            icon={kpi.icon}
          />
        ))}
      </section>

      <section className={styles.payintOverviewGrid}>
        <div className={styles.payintMainColumn}>
          <section className={styles.payintAnalyticsGrid}>
            <article className={`${styles.payintCard} ${styles.payintTrendCard}`}>
              <div className={styles.payintSectionHeader}>
                <div>
                  <h3>Hakediş Trendi</h3>
                  <p>Son 6 ayda toplam hakediş akışı.</p>
                </div>
                <button type="button" className={styles.payintCardFilter}>
                  Toplam Hakediş
                </button>
              </div>
              <TrendChart items={trendSeries.length ? trendSeries : [{ label: "—", value: 0 }]} />
              <div className={styles.payintInsightCard}>{trendInsight}</div>
            </article>

            <article className={`${styles.payintCard} ${styles.payintDistributionCard}`}>
              <div className={styles.payintSectionHeader}>
                <div>
                  <h3>Maliyet Modeli Dağılımı</h3>
                  <p>Model bazlı hakediş payını hızlıca gör.</p>
                </div>
              </div>
              <div className={styles.payintDonutRow}>
                <DonutChart items={costModelItems} total={totalGrossByModel} />
                <div className={styles.payintLegendList}>
                  {costModelItems.length ? (
                    costModelItems.map((item) => (
                      <div key={item.label} className={styles.payintLegendItem}>
                        <span
                          className={styles.payintLegendDot}
                          style={{ backgroundColor: item.color }}
                        />
                        <span className={styles.payintLegendLabel}>{item.label}</span>
                        <strong>{formatMoney(item.value)}</strong>
                        <small>%{formatNumber(item.percentage, 0)}</small>
                      </div>
                    ))
                  ) : (
                    <div className={styles.payintEmptyCompact}>Dağılım verisi yok.</div>
                  )}
                </div>
              </div>
              <div className={`${styles.payintInsightCard} ${styles.payintInsightSuccess}`}>
                {dominantCostModelInsight}
              </div>
            </article>
          </section>

          <section className={styles.payintEfficiencySection}>
            <div className={styles.payintSectionHeader}>
              <div>
                <h3>Verimlilik Özeti</h3>
                <p>Hız ve hacim tarafında operasyon ritmini aynı alanda okuyun.</p>
              </div>
            </div>
            <div className={styles.payintEfficiencyGrid}>
              <article className={styles.payintMiniMetricCard}>
                <div className={styles.payintMiniMetricHead}>
                  <span>Ortalama Paket / Saat</span>
                  {packagesPerHourDelta.label !== "Kıyas verisi yok" ? (
                    <DeltaBadge delta={packagesPerHourDelta} />
                  ) : null}
                </div>
                <strong>{formatNumber(currentPackagesPerHour, 1)}</strong>
                <Sparkline
                  values={productivitySeries.packagesPerHour}
                  strokeClassName={styles.payintSparkBlue}
                />
              </article>

              <article className={styles.payintMiniMetricCard}>
                <div className={styles.payintMiniMetricHead}>
                  <span>Toplam Paket</span>
                  {totalPackagesDelta.label !== "Kıyas verisi yok" ? (
                    <DeltaBadge delta={totalPackagesDelta} />
                  ) : null}
                </div>
                <strong>{formatNumber(payrollOverview.totalPackages, 0)}</strong>
                <Sparkline
                  values={productivitySeries.totalPackages}
                  strokeClassName={styles.payintSparkGreen}
                />
              </article>

              <article className={styles.payintMiniMetricCard}>
                <div className={styles.payintMiniMetricHead}>
                  <span>Toplam Saat</span>
                  {totalHoursDelta.label !== "Kıyas verisi yok" ? (
                    <DeltaBadge delta={totalHoursDelta} />
                  ) : null}
                </div>
                <strong>{formatNumber(payrollOverview.totalHours, 1)}</strong>
                <Sparkline
                  values={productivitySeries.totalHours}
                  strokeClassName={styles.payintSparkBlue}
                />
              </article>
            </div>
          </section>

          <section className={styles.payintLeaderboardSection}>
            <div className={styles.payintSectionHeader}>
              <div>
                <h3>Kurye Performans Sıralamaları</h3>
                <p>Net ödeme, kesinti ve verimlilik tarafında öne çıkanları hızlıca görün.</p>
              </div>
            </div>
            <div className={styles.payintLeaderboardGrid}>
              <LeaderboardCard
                title="En Yüksek Net Ödeme"
                items={highestNetPayment}
                valueFormatter={formatMoney}
                onSelect={setSelectedPersonnelId}
                onViewAll={() => setViewMode("list")}
                selectedPersonnelId={selectedPersonnelId}
              />
              <LeaderboardCard
                title="En Yüksek Kesinti Tutarı"
                items={highestDeduction}
                valueFormatter={formatMoney}
                onSelect={setSelectedPersonnelId}
                onViewAll={() => setViewMode("list")}
                selectedPersonnelId={selectedPersonnelId}
              />
              <LeaderboardCard
                title="En Verimli Kuryeler"
                items={mostEfficient}
                valueFormatter={(value) => formatNumber(value, 1)}
                onSelect={setSelectedPersonnelId}
                onViewAll={() => setViewMode("list")}
                selectedPersonnelId={selectedPersonnelId}
              />
            </div>
          </section>
        </div>

        <aside className={styles.payintSideColumn}>{detailPanel}</aside>
      </section>
    </>
  );

  const listView = (
    <section className={styles.payintListViewGrid}>
      <div className={styles.payintMainColumn}>
        <section className={`${styles.payintCard} ${styles.payintListCard}`}>
          <div className={styles.payintSectionHeader}>
            <div>
              <h3>Personel Listesi</h3>
              <p>Seçili dönemde hakediş havuzuna giren personeli filtreleyip detay panelini açın.</p>
            </div>
            <div className={styles.payintListMeta}>
              <span className={styles.payintCountBadge}>{formatNumber(listEntries.length, 0)} kişi</span>
            </div>
          </div>

          <div className={styles.payintListToolbar}>
            <label className={styles.payintField}>
              <span>Rol</span>
              <select value={selectedRole} onChange={(event) => setSelectedRole(event.target.value)}>
                <option value="Tümü">Tümü</option>
                {(dashboard?.role_options ?? []).map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.payintField}>
              <span>Restoran / Şube</span>
              <select
                value={selectedRestaurant}
                onChange={(event) => setSelectedRestaurant(event.target.value)}
              >
                <option value="Tümü">Tümü</option>
                {(dashboard?.restaurant_options ?? []).map((restaurant) => (
                  <option key={restaurant} value={restaurant}>
                    {restaurant}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.payintField}>
              <span>Sırala</span>
              <select value={sortMode} onChange={(event) => setSortMode(event.target.value)}>
                <option value="net-desc">Net Ödeme</option>
                <option value="gross-desc">Hakediş Tutarı</option>
                <option value="deduction-desc">Kesinti</option>
                <option value="tevkifat-desc">Tevkifat</option>
                <option value="name-asc">Ada Göre</option>
              </select>
            </label>

            <label className={`${styles.payintField} ${styles.payintSearchField}`}>
              <span>Personel ara</span>
              <input
                value={personnelQuery}
                onChange={(event) => setPersonnelQuery(event.target.value)}
                placeholder="Ad, rol veya model ara"
              />
            </label>
          </div>

          <div className={styles.payintListBody}>
            <div className={styles.payintTableDesktop}>
              <div className={styles.payintTableHeader}>
                <span>Personel</span>
                <span>Rol</span>
                <span>Durum</span>
                <span>Net Ödeme</span>
                <span>Hakediş</span>
                <span>Kesinti</span>
                <span>Tevkifat</span>
                <span>Model</span>
              </div>
              {listEntries.map((entry) => (
                <button
                  key={entry.personnel_id}
                  type="button"
                  className={`${styles.payintTableRow} ${
                    selectedPersonnelId === entry.personnel_id ? styles.payintTableRowSelected : ""
                  }`}
                  onClick={() => setSelectedPersonnelId(entry.personnel_id)}
                >
                  <span className={styles.payintPersonCell}>
                    <strong>{entry.personnel}</strong>
                  </span>
                  <span>{entry.role}</span>
                  <span>
                    <StatusBadge value={entry.status} />
                  </span>
                  <span className={styles.payintNumericCell}>{formatMoney(entry.net_payment)}</span>
                  <span className={styles.payintNumericCell}>{formatMoney(entry.gross_pay)}</span>
                  <span className={`${styles.payintNumericCell} ${styles.payintNegativeText}`}>
                    {formatMoney(entry.total_deductions)}
                  </span>
                  <span className={styles.payintNumericCell}>
                    {formatMoney(entry.tevkifat_amount)}
                  </span>
                  <span className={styles.payintModelCell}>{displayCostModel(entry.cost_model)}</span>
                </button>
              ))}
            </div>

            <div className={styles.payintTableMobile}>
              {listEntries.map((entry) => (
                <button
                  key={`mobile-${entry.personnel_id}`}
                  type="button"
                  className={`${styles.payintPersonCard} ${
                    selectedPersonnelId === entry.personnel_id ? styles.payintPersonCardSelected : ""
                  }`}
                  onClick={() => setSelectedPersonnelId(entry.personnel_id)}
                >
                  <div className={styles.payintPersonCardHead}>
                    <div className={styles.payintPersonCardCopy}>
                      <strong>{entry.personnel}</strong>
                      <span>{entry.role}</span>
                    </div>
                    <StatusBadge value={entry.status} />
                  </div>
                  <div className={styles.payintPersonCardGrid}>
                    <div>
                      <small>Net Ödeme</small>
                      <strong>{formatMoney(entry.net_payment)}</strong>
                    </div>
                    <div>
                      <small>Hakediş</small>
                      <strong>{formatMoney(entry.gross_pay)}</strong>
                    </div>
                    <div>
                      <small>Kesinti</small>
                      <strong className={styles.payintNegativeText}>
                        {formatMoney(entry.total_deductions)}
                      </strong>
                    </div>
                    <div>
                      <small>Tevkifat</small>
                      <strong>{formatMoney(entry.tevkifat_amount)}</strong>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </section>
      </div>

      <aside className={styles.payintSideColumn}>{detailPanel}</aside>
    </section>
  );

  return (
    <AppShell activeItem="Aylık Hakediş">
      <div className={styles.payintPage}>
        <div className={styles.payintContainer}>
          <header className={styles.payintHeader}>
            <div className={styles.payintHeaderCopy}>
              <h1>Aylık Hakediş</h1>
              <p>Kurye ödemelerini, kesintileri ve performansı tek ekranda yönetin.</p>
            </div>
            <div className={styles.payintHeaderActions}>
              <label className={styles.payintField}>
                <span>Dönem</span>
                <div className={styles.payintFieldControl}>
                  <IconGlyph name="calendar" className={styles.payintFieldIcon} />
                  <select
                    value={selectedMonth}
                    onChange={(event) => setSelectedMonth(event.target.value)}
                    disabled={dashboardLoading || !dashboard?.month_options?.length}
                  >
                    {(dashboard?.month_options ?? []).map((month) => (
                      <option key={month} value={month}>
                        {month}
                      </option>
                    ))}
                  </select>
                </div>
              </label>
              <button type="button" className={styles.payintGhostButton} onClick={handleCsvDownload}>
                <IconGlyph name="download" className={styles.payintButtonIcon} />
                Excel İndir
              </button>
            </div>
          </header>

          <div className={styles.payintViewSwitch} role="tablist" aria-label="Hakediş görünüm modu">
            <button
              type="button"
              className={`${styles.payintViewButton} ${
                viewMode === "overview" ? styles.payintViewButtonActive : ""
              }`}
              onClick={() => setViewMode("overview")}
            >
              Genel Bakış
            </button>
            <button
              type="button"
              className={`${styles.payintViewButton} ${
                viewMode === "list" ? styles.payintViewButtonActive : ""
              }`}
              onClick={() => setViewMode("list")}
            >
              Personel Listesi
            </button>
          </div>

          {dashboardLoading ? (
            <section className={styles.payintLoadingCard}>Hakediş verileri yükleniyor...</section>
          ) : !dashboard || !dashboard.summary ? (
            <section className={styles.payintLoadingCard}>
              Hakediş verileri şu an alınamadı. Bağlantı toparlandığında panel otomatik yenilenecek.
            </section>
          ) : (
            viewMode === "overview" ? overviewView : listView
          )}
        </div>
      </div>
    </AppShell>
  );
}
