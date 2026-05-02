"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import PayrollPersonnelWorkbench from "../../components/payroll/PayrollPersonnelWorkbench";
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
    deduction_items?: Array<{
      label: string;
      amount: number;
    }>;
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
const EFFICIENCY_PACKAGE_MODELS = new Set(["hourly_plus_package", "threshold_package"]);

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
      label: "",
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
  if (!delta.label) {
    return null;
  }

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

function hasValidPackageData(entry: PayrollEntryView) {
  return entry.total_packages > 0 || EFFICIENCY_PACKAGE_MODELS.has(entry.cost_model);
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
  const [selectedPersonnelId, setSelectedPersonnelId] = useState<number | null>(null);
  const [monthlySeries, setMonthlySeries] = useState<MonthlySeriesItem[]>([]);
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

  useEffect(() => {
    if (!filteredEntries.length) {
      setSelectedPersonnelId(null);
      return;
    }

    if (selectedPersonnelId && !filteredEntries.some((entry) => entry.personnel_id === selectedPersonnelId)) {
      setSelectedPersonnelId(null);
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

  const efficiencyEntries = useMemo(
    () => filteredEntries.filter((entry) => hasValidPackageData(entry)),
    [filteredEntries],
  );

  const efficiencySummary = useMemo(() => {
    const totalPackages = efficiencyEntries.reduce((sum, entry) => sum + entry.total_packages, 0);
    const totalHours = efficiencyEntries.reduce((sum, entry) => sum + entry.total_hours, 0);
    const hasData = efficiencyEntries.length > 0 && totalHours > 0;

    return {
      hasData,
      totalPackages,
      totalHours,
      packagesPerHour: hasData ? totalPackages / totalHours : 0,
    };
  }, [efficiencyEntries]);

  const efficiencyMonthlySeries = useMemo(
    () =>
      monthlySeries.map((item) => {
        const validEntries = item.entries.filter((entry) => hasValidPackageData(entry));
        const totalPackages = validEntries.reduce((sum, entry) => sum + entry.total_packages, 0);
        const totalHours = validEntries.reduce((sum, entry) => sum + entry.total_hours, 0);
        const hasData = validEntries.length > 0 && totalHours > 0;

        return {
          month: item.month,
          label: item.label,
          hasData,
          totalPackages,
          totalHours,
          packagesPerHour: hasData ? totalPackages / totalHours : 0,
        };
      }),
    [monthlySeries],
  );

  const productivitySeries = useMemo(
    () => ({
      packagesPerHour: efficiencyMonthlySeries
        .filter((item) => item.hasData)
        .map((item) => item.packagesPerHour),
      totalPackages: efficiencyMonthlySeries.filter((item) => item.hasData).map((item) => item.totalPackages),
      totalHours: efficiencyMonthlySeries.filter((item) => item.hasData).map((item) => item.totalHours),
    }),
    [efficiencyMonthlySeries],
  );

  const previousEfficiencySeries = useMemo(() => {
    if (!payrollOverview.selectedMonth) {
      return null;
    }
    const index = efficiencyMonthlySeries.findIndex((item) => item.month === payrollOverview.selectedMonth);
    if (index <= 0) {
      return null;
    }
    return efficiencyMonthlySeries[index - 1];
  }, [efficiencyMonthlySeries, payrollOverview.selectedMonth]);

  const packagesPerHourDelta = buildDelta(
    efficiencySummary.packagesPerHour,
    previousEfficiencySeries?.packagesPerHour ?? 0,
    true,
  );
  const totalPackagesDelta = buildDelta(
    efficiencySummary.totalPackages,
    previousEfficiencySeries?.totalPackages ?? 0,
    true,
  );
  const totalHoursDelta = buildDelta(
    efficiencySummary.totalHours,
    previousEfficiencySeries?.totalHours ?? 0,
    true,
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

  async function handleDownloadPayrollPdf(person?: {
    id?: number | null;
    name?: string | null;
  }) {
    const personnelId = person?.id;
    const month = dashboard?.selected_month || selectedMonth;
    if (!personnelId || !month) {
      return;
    }

    try {
      const params = new URLSearchParams({
        personnel_id: String(personnelId),
        month,
      });
      const response = await apiFetch(`/payroll/document?${params.toString()}`);
      if (!response.ok) {
        throw new Error("Hakediş PDF'i indirilemedi.");
      }
      const disposition = response.headers.get("Content-Disposition") || "";
      const encodedFileNameMatch = disposition.match(/filename\*\=UTF-8''([^;]+)/i);
      const fileNameMatch = disposition.match(/filename=\"?([^"]+)\"?/i);
      const fileName =
        (encodedFileNameMatch?.[1]
          ? decodeURIComponent(encodedFileNameMatch[1])
          : undefined) ||
        fileNameMatch?.[1] ||
        `hakedis_${personnelId}_${month}.pdf`;
      const blob = await response.blob();
      triggerBrowserDownload(blob, fileName);
    } catch (error) {
      console.error("Hakediş PDF'i indirilemedi", error);
    }
  }

  function handleCsvDownload() {
    if (!filteredEntries.length) {
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

  const mappedPayrollPeople = useMemo(
    () =>
      filteredEntries.map((entry) => {
        const deductions =
          entry.deduction_items && entry.deduction_items.length
            ? entry.deduction_items
                .filter((item) => Number.isFinite(item.amount) && Math.abs(item.amount) > 0.01)
                .map((item) => ({
                  label: item.label || "Kesinti",
                  amount: Number(item.amount),
                }))
            : (() => {
                const residualDeduction = Math.max(entry.total_deductions - entry.tevkifat_amount, 0);
                const fallbackItems = [] as Array<{ label: string; amount: number }>;
                if (residualDeduction > 0.01) {
                  fallbackItems.push({ label: "Diğer Kesintiler", amount: residualDeduction });
                }
                if (entry.tevkifat_amount > 0.01) {
                  fallbackItems.push({
                    label: "Tevkifat (Yasal yükümlülük kesintisi)",
                    amount: entry.tevkifat_amount,
                  });
                }
                return fallbackItems;
              })();

        return {
          id: entry.personnel_id,
          name: entry.personnel || "—",
          role: entry.role || "—",
          status: entry.status || "—",
          netPayment: Number.isFinite(entry.net_payment) ? entry.net_payment : null,
          earning: Number.isFinite(entry.gross_pay) ? entry.gross_pay : null,
          deduction: Number.isFinite(entry.total_deductions) ? entry.total_deductions : null,
          withholding: Number.isFinite(entry.tevkifat_amount) ? entry.tevkifat_amount : null,
          model: displayCostModel(entry.cost_model),
          totalHours: Number.isFinite(entry.total_hours) ? entry.total_hours : null,
          totalPackages: Number.isFinite(entry.total_packages) ? entry.total_packages : null,
          operationsLabel:
            entry.restaurant_count > 0 ? `${formatNumber(entry.restaurant_count, 0)} şube` : "—",
          deductions,
        };
      }),
    [filteredEntries],
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

      <section className={styles.payintOverviewLayout}>
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
                  {efficiencySummary.hasData ? <DeltaBadge delta={packagesPerHourDelta} /> : null}
                </div>
                <strong>
                  {efficiencySummary.hasData ? formatNumber(efficiencySummary.packagesPerHour, 1) : "—"}
                </strong>
                {efficiencySummary.hasData ? (
                  <Sparkline
                    values={productivitySeries.packagesPerHour}
                    strokeClassName={styles.payintSparkBlue}
                  />
                ) : (
                  <small className={styles.payintMiniMetricNote}>Yeterli veri yok</small>
                )}
              </article>

              <article className={styles.payintMiniMetricCard}>
                <div className={styles.payintMiniMetricHead}>
                  <span>Toplam Paket</span>
                  {efficiencySummary.hasData ? <DeltaBadge delta={totalPackagesDelta} /> : null}
                </div>
                <strong>{efficiencySummary.hasData ? formatNumber(efficiencySummary.totalPackages, 0) : "—"}</strong>
                {efficiencySummary.hasData ? (
                  <Sparkline
                    values={productivitySeries.totalPackages}
                    strokeClassName={styles.payintSparkGreen}
                  />
                ) : (
                  <small className={styles.payintMiniMetricNote}>Yeterli veri yok</small>
                )}
              </article>

              <article className={styles.payintMiniMetricCard}>
                <div className={styles.payintMiniMetricHead}>
                  <span>Toplam Saat</span>
                  {efficiencySummary.hasData ? <DeltaBadge delta={totalHoursDelta} /> : null}
                </div>
                <strong>{efficiencySummary.hasData ? formatNumber(efficiencySummary.totalHours, 1) : "—"}</strong>
                {efficiencySummary.hasData ? (
                  <Sparkline
                    values={productivitySeries.totalHours}
                    strokeClassName={styles.payintSparkBlue}
                  />
                ) : (
                  <small className={styles.payintMiniMetricNote}>Yeterli veri yok</small>
                )}
              </article>
            </div>
            {efficiencySummary.hasData ? (
              <p className={styles.payintEfficiencyNote}>
                Sadece paket verisi olan kuryeler üzerinden hesaplandı
              </p>
            ) : null}
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
      </section>
    </>
  );

  const listView = (
    <PayrollPersonnelWorkbench
      people={mappedPayrollPeople}
      onDownloadPdf={handleDownloadPayrollPdf}
    />
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
