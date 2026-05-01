"use client";

import type { ComponentType, CSSProperties } from "react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Calendar,
  CalendarCheck,
  ChevronDown,
  Download,
  FileText,
  Home,
  LogOut,
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
} from "lucide-react";

import { useAuth } from "../auth/auth-provider";
import { apiFetch } from "../../lib/api";
import styles from "./PayrollOverviewMock.module.css";

type NavGroup = {
  title: string;
  items: Array<{
    label: string;
    icon: ComponentType<{ className?: string; strokeWidth?: number }>;
    active?: boolean;
  }>;
};

type PayrollDashboard = {
  module: string;
  status: string;
  month_options: string[];
  selected_month: string | null;
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
};

type DeductionRecord = {
  id: number;
  deduction_date: string;
  deduction_type: string;
  type_caption: string;
  amount: number;
};

type DeductionsManagementResponse = {
  entries: DeductionRecord[];
};

type PayrollEntryView = PayrollDashboard["entries"][number];

type MonthlySeriesItem = {
  month: string;
  label: string;
  summary: NonNullable<PayrollDashboard["summary"]>;
  entries: PayrollEntryView[];
};

type DeltaTone = "positive" | "negative" | "neutral";

type DeltaView = {
  label: string;
  tone: DeltaTone;
};

type IconTone = "blue" | "green" | "orange" | "violet";

type KpiItem = {
  label: string;
  value: string;
  delta: DeltaView;
  tone: IconTone;
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
};

type LeaderboardItem = {
  rank: number;
  name: string;
  role: string;
  value: string;
  personnelId: number | null;
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

const COST_MODEL_LABELS: Record<string, string> = {
  hourly_plus_package: "Saatlik",
  threshold_package: "Paket Başı",
  hourly_only: "Günlük",
  fixed_monthly: "Diğer",
};

const DONUT_COLORS = ["#2563EB", "#60A5FA", "#93C5FD", "#DBEAFE"];

function toSafeNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function summarizeEntries(entries: PayrollEntryView[]) {
  return {
    selected_month: "",
    personnel_count: entries.length,
    total_hours: entries.reduce((sum, entry) => sum + entry.total_hours, 0),
    total_packages: entries.reduce((sum, entry) => sum + entry.total_packages, 0),
    gross_payroll: entries.reduce((sum, entry) => sum + entry.gross_pay, 0),
    total_deductions: entries.reduce((sum, entry) => sum + entry.total_deductions, 0),
    total_tevkifat: entries.reduce((sum, entry) => sum + entry.tevkifat_amount, 0),
    net_payment: entries.reduce((sum, entry) => sum + entry.net_payment, 0),
  };
}

function normalizePayrollDashboard(payload: Partial<PayrollDashboard>): PayrollDashboard {
  const normalizedEntries = Array.isArray(payload.entries)
    ? payload.entries.map((entry) => ({
        personnel_id: toSafeNumber(entry.personnel_id),
        personnel: toSafeString(entry.personnel, "—"),
        role: toSafeString(entry.role, "—"),
        status: toSafeString(entry.status, "—"),
        total_hours: toSafeNumber(entry.total_hours),
        total_packages: toSafeNumber(entry.total_packages),
        gross_pay: toSafeNumber(entry.gross_pay),
        total_deductions: toSafeNumber(entry.total_deductions),
        tevkifat_amount: toSafeNumber(entry.tevkifat_amount),
        net_payment: toSafeNumber(entry.net_payment),
        restaurant_count: toSafeNumber(entry.restaurant_count),
        cost_model: toSafeString(entry.cost_model, "—"),
      }))
    : [];

  const fallbackSummary = summarizeEntries(normalizedEntries);
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
      : {
          ...fallbackSummary,
          selected_month: toSafeString(payload.selected_month),
        };

  return {
    module: toSafeString(payload.module, "payroll"),
    status: toSafeString(payload.status, "active"),
    month_options: Array.isArray(payload.month_options)
      ? payload.month_options.map((item) => toSafeString(item)).filter(Boolean)
      : [],
    selected_month: typeof payload.selected_month === "string" ? payload.selected_month : null,
    summary,
    entries: normalizedEntries,
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

function formatMoneyOrDash(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }
  return formatMoney(value);
}

function formatCompactMoney(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }
  if (Math.abs(value) >= 1_000_000) {
    return `${new Intl.NumberFormat("tr-TR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value / 1_000_000)} Mn ₺`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${new Intl.NumberFormat("tr-TR", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value / 1_000)} B ₺`;
  }
  return formatMoney(value);
}

function formatNumber(value: number, decimals = 0) {
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value || 0);
}

function formatNumberOrDash(value: number | null | undefined, decimals = 0) {
  if (value === null || value === undefined) {
    return "—";
  }
  return formatNumber(value, decimals);
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

function monthToLongLabel(month: string | null | undefined) {
  if (!month) {
    return "—";
  }
  const [year, rawMonth] = month.split("-");
  const parsedYear = Number(year);
  const parsedMonth = Number(rawMonth);
  if (!parsedYear || !parsedMonth) {
    return month;
  }
  const label = new Intl.DateTimeFormat("tr-TR", {
    month: "long",
    year: "numeric",
  }).format(new Date(Date.UTC(parsedYear, parsedMonth - 1, 1)));
  return label.charAt(0).toLocaleUpperCase("tr-TR") + label.slice(1);
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
  const safeValue = value.trim();
  if (!safeValue) {
    return "—";
  }
  return safeValue
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase("tr-TR") ?? "")
    .join("");
}

function displayCostModel(value: string) {
  return (COST_MODEL_LABELS[value] ?? value) || "—";
}

function buildDelta(current: number | null | undefined, previous: number | null | undefined, positiveIsGood: boolean): DeltaView {
  if (
    current === null ||
    current === undefined ||
    previous === null ||
    previous === undefined ||
    !Number.isFinite(current) ||
    !Number.isFinite(previous) ||
    previous === 0
  ) {
    return { label: "Kıyas verisi yok", tone: "neutral" };
  }

  const ratio = ((current - previous) / previous) * 100;
  if (Math.abs(ratio) < 0.1) {
    return { label: "Değişim sınırlı", tone: "neutral" };
  }

  const improved = positiveIsGood ? ratio > 0 : ratio < 0;
  return {
    label: `%${formatNumber(Math.abs(ratio), 1)} geçen aya göre`,
    tone: improved ? "positive" : "negative",
  };
}

function buildPath(points: number[], width: number, height: number, padding = 14) {
  if (!points.length) {
    return "";
  }
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  return points
    .map((value, index) => {
      const x = padding + (index * (width - padding * 2)) / Math.max(points.length - 1, 1);
      const y = height - padding - ((value - min) / range) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");
}

function buildTrendGeometry(points: Array<{ label: string; value: number }>) {
  const values = points.length ? points.map((point) => point.value) : [0];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return points.map((point, index) => {
    const x = 36 + (index * (724 - 36)) / Math.max(points.length - 1, 1);
    const normalized = range === 0 ? 0.5 : (point.value - min) / range;
    const y = 188 - normalized * 120;
    return { ...point, x, y };
  });
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
  tone: IconTone;
}) {
  return (
    <span className={`${styles["ck-payroll-icon-badge"]} ${styles[`ck-payroll-icon-${tone}`]}`}>
      <Icon className={styles["ck-payroll-icon"]} strokeWidth={2} />
    </span>
  );
}

export function PayrollOverviewMock() {
  const { user, loading, logout } = useAuth();
  const [dashboard, setDashboard] = useState<PayrollDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [selectedPersonnelId, setSelectedPersonnelId] = useState<number | null>(null);
  const [monthlySeries, setMonthlySeries] = useState<MonthlySeriesItem[]>([]);
  const [deductionEntries, setDeductionEntries] = useState<DeductionRecord[]>([]);
  const [deductionLoading, setDeductionLoading] = useState(false);
  const [documentBusy, setDocumentBusy] = useState(false);
  const deferredSelectedPersonnelId = useDeferredValue(selectedPersonnelId);

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
        const params = new URLSearchParams({ limit: "500" });
        if (selectedMonth) {
          params.set("month", selectedMonth);
        }
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
  }, [loading, selectedMonth, user]);

  const monthWindow = useMemo(() => {
    if (!dashboard?.month_options.length) {
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
            const response = await apiFetch(`/payroll/dashboard?${params.toString()}`);
            if (!response.ok) {
              return null;
            }
            const payload = normalizePayrollDashboard((await response.json()) as Partial<PayrollDashboard>);
            const summary = payload.summary ?? { ...summarizeEntries(payload.entries), selected_month: month };
            return {
              month,
              label: monthToLabel(month),
              summary: {
                ...summary,
                selected_month: summary.selected_month || month,
              },
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
  }, [monthWindow, user]);

  useEffect(() => {
    const entries = dashboard?.entries ?? [];
    if (!entries.length) {
      setSelectedPersonnelId(null);
      return;
    }
    if (!selectedPersonnelId || !entries.some((entry) => entry.personnel_id === selectedPersonnelId)) {
      setSelectedPersonnelId(entries[0].personnel_id);
    }
  }, [dashboard?.entries, selectedPersonnelId]);

  const payrollOverview = useMemo(() => {
    if (dashboard?.summary) {
      return dashboard.summary;
    }
    if (dashboard?.entries.length) {
      return {
        ...summarizeEntries(dashboard.entries),
        selected_month: dashboard.selected_month || selectedMonth || "",
      };
    }
    return null;
  }, [dashboard?.entries, dashboard?.selected_month, dashboard?.summary, selectedMonth]);

  const previousSeries = useMemo(() => {
    const currentMonth = payrollOverview?.selected_month || selectedMonth;
    if (!currentMonth) {
      return null;
    }
    const index = monthlySeries.findIndex((item) => item.month === currentMonth);
    if (index <= 0) {
      return null;
    }
    return monthlySeries[index - 1];
  }, [monthlySeries, payrollOverview?.selected_month, selectedMonth]);

  const trendPoints = useMemo(
    () =>
      monthlySeries.map((item) => ({
        label: item.label,
        value: item.summary.gross_payroll,
      })),
    [monthlySeries],
  );

  const trendGeometry = useMemo(
    () => buildTrendGeometry(trendPoints.length ? trendPoints : [{ label: "—", value: 0 }]),
    [trendPoints],
  );

  const trendPath = useMemo(
    () => buildPath((trendPoints.length ? trendPoints : [{ label: "—", value: 0 }]).map((item) => item.value), 760, 260, 24),
    [trendPoints],
  );

  const costModelItems = useMemo(() => {
    const totals = new Map<string, number>();
    (dashboard?.entries ?? []).forEach((entry) => {
      totals.set(entry.cost_model, (totals.get(entry.cost_model) ?? 0) + entry.gross_pay);
    });
    const total = Array.from(totals.values()).reduce((sum, value) => sum + value, 0);
    return Array.from(totals.entries())
      .map(([costModel, amount], index) => ({
        label: displayCostModel(costModel),
        amount,
        percent: total > 0 ? (amount / total) * 100 : 0,
        color: DONUT_COLORS[index % DONUT_COLORS.length],
      }))
      .sort((left, right) => right.amount - left.amount);
  }, [dashboard?.entries]);

  const donutStyle = useMemo(() => {
    if (!costModelItems.length) {
      return {
        background: "conic-gradient(#DBEAFE 0% 100%)",
      } as CSSProperties;
    }
    return {
      background: `conic-gradient(${costModelItems
        .map((item, index) => {
          const start = costModelItems
            .slice(0, index)
            .reduce((sum, row) => sum + row.percent, 0);
          const end = start + item.percent;
          return `${item.color} ${start}% ${end}%`;
        })
        .join(", ")})`,
    } as CSSProperties;
  }, [costModelItems]);

  const totalDistributionAmount = useMemo(
    () => costModelItems.reduce((sum, item) => sum + item.amount, 0),
    [costModelItems],
  );

  const efficiencySeries = useMemo(() => {
    const packagesPerHour = monthlySeries.map((item) => {
      const hours = item.summary.total_hours;
      return hours > 0 ? item.summary.total_packages / hours : 0;
    });
    return {
      packagesPerHour,
      totalPackages: monthlySeries.map((item) => item.summary.total_packages),
      totalHours: monthlySeries.map((item) => item.summary.total_hours),
    };
  }, [monthlySeries]);

  const currentPackagesPerHour =
    payrollOverview && payrollOverview.total_hours > 0
      ? payrollOverview.total_packages / payrollOverview.total_hours
      : null;

  const previousPackagesPerHour =
    previousSeries && previousSeries.summary.total_hours > 0
      ? previousSeries.summary.total_packages / previousSeries.summary.total_hours
      : null;

  const selectedPersonnel = useMemo(
    () =>
      (dashboard?.entries ?? []).find((entry) => entry.personnel_id === deferredSelectedPersonnelId) ??
      (dashboard?.entries ?? [])[0] ??
      null,
    [dashboard?.entries, deferredSelectedPersonnelId],
  );

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
      return [] as Array<{ label: string; amount: number }>;
    }
    const rows = deductionEntries.map((entry) => ({
      label: entry.type_caption || entry.deduction_type || "Kesinti",
      amount: entry.amount,
    }));
    const hasTevkifat = rows.some((row) => row.label.toLocaleLowerCase("tr-TR").includes("tevkifat"));
    if (!hasTevkifat && selectedPersonnel.tevkifat_amount > 0) {
      rows.push({ label: "Tevkifat", amount: selectedPersonnel.tevkifat_amount });
    }
    const knownTotal = rows.reduce((sum, row) => sum + row.amount, 0);
    const residual = Math.max(selectedPersonnel.total_deductions - knownTotal, 0);
    if (residual > 0.01) {
      rows.push({ label: "Diğer Kesintiler", amount: residual });
    }
    return rows;
  }, [deductionEntries, selectedPersonnel]);

  const kpis = useMemo<KpiItem[]>(
    () => [
      {
        label: "Net Ödenecek Tutar",
        value: formatMoneyOrDash(payrollOverview?.net_payment ?? null),
        delta: buildDelta(payrollOverview?.net_payment, previousSeries?.summary.net_payment, true),
        tone: "blue",
        icon: Wallet,
      },
      {
        label: "Hakediş Tutarı",
        value: formatMoneyOrDash(payrollOverview?.gross_payroll ?? null),
        delta: buildDelta(payrollOverview?.gross_payroll, previousSeries?.summary.gross_payroll, true),
        tone: "green",
        icon: Receipt,
      },
      {
        label: "Toplam Kesinti",
        value: formatMoneyOrDash(payrollOverview?.total_deductions ?? null),
        delta: buildDelta(payrollOverview?.total_deductions, previousSeries?.summary.total_deductions, false),
        tone: "orange",
        icon: CircleMinusIcon,
      },
      {
        label: "Toplam Tevkifat",
        value: formatMoneyOrDash(payrollOverview?.total_tevkifat ?? null),
        delta: buildDelta(payrollOverview?.total_tevkifat, previousSeries?.summary.total_tevkifat, false),
        tone: "violet",
        icon: ShieldCheck,
      },
    ],
    [payrollOverview, previousSeries?.summary.gross_payroll, previousSeries?.summary.net_payment, previousSeries?.summary.total_deductions, previousSeries?.summary.total_tevkifat],
  );

  const efficiencyCards = useMemo(
    () => [
      {
        label: "Ortalama Paket / Saat",
        value:
          currentPackagesPerHour === null
            ? "—"
            : formatNumber(currentPackagesPerHour, 1),
        delta: buildDelta(currentPackagesPerHour, previousPackagesPerHour, true),
        spark: efficiencySeries.packagesPerHour,
      },
      {
        label: "Toplam Paket",
        value: payrollOverview ? formatNumber(payrollOverview.total_packages, 0) : "—",
        delta: buildDelta(payrollOverview?.total_packages, previousSeries?.summary.total_packages, true),
        spark: efficiencySeries.totalPackages,
      },
      {
        label: "Toplam Saat",
        value: payrollOverview ? formatNumber(payrollOverview.total_hours, 0) : "—",
        delta: buildDelta(payrollOverview?.total_hours, previousSeries?.summary.total_hours, true),
        spark: efficiencySeries.totalHours,
      },
    ],
    [currentPackagesPerHour, efficiencySeries.packagesPerHour, efficiencySeries.totalHours, efficiencySeries.totalPackages, payrollOverview, previousPackagesPerHour, previousSeries?.summary.total_hours, previousSeries?.summary.total_packages],
  );

  const highestNetPayment = useMemo<LeaderboardItem[]>(
    () =>
      [...(dashboard?.entries ?? [])]
        .sort((left, right) => right.net_payment - left.net_payment)
        .slice(0, 3)
        .map((entry, index) => ({
          rank: index + 1,
          name: entry.personnel,
          role: entry.role,
          value: formatMoney(entry.net_payment),
          personnelId: entry.personnel_id,
        })),
    [dashboard?.entries],
  );

  const highestDeduction = useMemo<LeaderboardItem[]>(
    () =>
      [...(dashboard?.entries ?? [])]
        .sort((left, right) => right.total_deductions - left.total_deductions)
        .slice(0, 3)
        .map((entry, index) => ({
          rank: index + 1,
          name: entry.personnel,
          role: entry.role,
          value: formatMoney(entry.total_deductions),
          personnelId: entry.personnel_id,
        })),
    [dashboard?.entries],
  );

  const mostEfficient = useMemo<LeaderboardItem[]>(
    () =>
      [...(dashboard?.entries ?? [])]
        .filter((entry) => entry.total_hours > 0)
        .sort(
          (left, right) =>
            right.total_packages / right.total_hours - left.total_packages / left.total_hours,
        )
        .slice(0, 3)
        .map((entry, index) => ({
          rank: index + 1,
          name: entry.personnel,
          role: entry.role,
          value: formatNumber(entry.total_packages / entry.total_hours, 1),
          personnelId: entry.personnel_id,
        })),
    [dashboard?.entries],
  );

  async function handleDocumentDownload() {
    if (!selectedPersonnel) {
      return;
    }
    const month = dashboard?.selected_month || selectedMonth;
    if (!month) {
      return;
    }
    setDocumentBusy(true);
    try {
      const params = new URLSearchParams({
        personnel_id: String(selectedPersonnel.personnel_id),
        month,
      });
      const response = await apiFetch(`/payroll/document?${params.toString()}`);
      if (!response.ok) {
        return;
      }
      const disposition = response.headers.get("Content-Disposition") || "";
      const fileNameMatch = disposition.match(/filename=\"?([^"]+)\"?/i);
      const fileName = fileNameMatch?.[1] || `hakedis_${selectedPersonnel.personnel_id}_${month}.pdf`;
      const blob = await response.blob();
      triggerBrowserDownload(blob, fileName);
    } finally {
      setDocumentBusy(false);
    }
  }

  function handleCsvDownload() {
    const rows = dashboard?.entries ?? [];
    if (!rows.length) {
      return;
    }
    const headers = ["Personel", "Rol", "Durum", "Net Ödeme", "Hakediş Tutarı", "Toplam Kesinti", "Toplam Tevkifat", "Model"];
    const csvRows = rows.map((entry) => [
      entry.personnel,
      entry.role,
      entry.status,
      String(entry.net_payment),
      String(entry.gross_pay),
      String(entry.total_deductions),
      String(entry.tevkifat_amount),
      displayCostModel(entry.cost_model),
    ]);
    const csv = [headers, ...csvRows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const month = dashboard?.selected_month || selectedMonth || "hakedis";
    const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" });
    triggerBrowserDownload(blob, `catkapinda_aylik_hakedis_${month}.csv`);
  }

  const selectedMonthLabel = monthToLongLabel(dashboard?.selected_month || selectedMonth);
  const selectedPersonName = selectedPersonnel?.personnel ?? "—";
  const selectedPersonRole = selectedPersonnel?.role ?? "—";
  const selectedPersonStatus = selectedPersonnel?.status ?? "—";
  const selectedPersonNetPayment = formatMoneyOrDash(selectedPersonnel?.net_payment ?? null);
  const selectedPersonGrossPay = formatMoneyOrDash(selectedPersonnel?.gross_pay ?? null);
  const selectedPersonDeductionsTotal = formatMoneyOrDash(selectedPersonnel?.total_deductions ?? null);
  const selectedPersonTevkifat = formatMoneyOrDash(selectedPersonnel?.tevkifat_amount ?? null);

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
            <div className={styles["ck-payroll-user-avatar"]}>{getInitials(user?.full_name ?? "")}</div>
            <div className={styles["ck-payroll-user-copy"]}>
              <strong>{user?.full_name || "—"}</strong>
              <span>{user?.role_display || "—"}</span>
            </div>
            <ChevronDown className={styles["ck-payroll-user-chevron"]} strokeWidth={2} />
          </button>
          <button type="button" className={styles["ck-payroll-logout"]} onClick={() => void logout()}>
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
                {selectedMonthLabel}
                <ChevronDown className={styles["ck-payroll-inline-chevron"]} strokeWidth={2} />
              </button>
              <button type="button" className={styles["ck-payroll-secondary-button"]} onClick={handleCsvDownload}>
                <Download className={styles["ck-payroll-inline-icon"]} strokeWidth={2} />
                Excel İndir
              </button>
            </div>
          </header>

          <section className={styles["ck-payroll-kpis"]}>
            {kpis.map((kpi) => (
              <article key={kpi.label} className={styles["ck-payroll-kpi-card"]}>
                <div className={styles["ck-payroll-kpi-top"]}>
                  <CardIcon icon={kpi.icon} tone={kpi.tone} />
                  <div className={styles["ck-payroll-kpi-copy"]}>
                    <div className={styles["ck-payroll-kpi-label"]}>{kpi.label}</div>
                    <div className={styles["ck-payroll-kpi-value"]}>{dashboardLoading ? "—" : kpi.value}</div>
                  </div>
                </div>
                <div
                  className={`${styles["ck-payroll-delta"]} ${
                    kpi.delta.tone === "positive"
                      ? styles["ck-payroll-delta-positive"]
                      : kpi.delta.tone === "negative"
                        ? styles["ck-payroll-delta-negative"]
                        : ""
                  }`}
                >
                  {kpi.delta.label}
                </div>
              </article>
            ))}
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
                      {trendGeometry.map((point) => (
                        <g key={point.label}>
                          <circle cx={point.x} cy={point.y} r="5" className={styles["ck-payroll-trend-point"]} />
                          <text x={point.x} y={point.y - 16} textAnchor="middle" className={styles["ck-payroll-trend-value"]}>
                            {formatCompactMoney(point.value)}
                          </text>
                          <text x={point.x} y="238" textAnchor="middle" className={styles["ck-payroll-trend-label"]}>
                            {point.label}
                          </text>
                        </g>
                      ))}
                    </svg>
                  </div>
                  <div className={styles["ck-payroll-insight"]}>
                    <TrendingUp className={styles["ck-payroll-insight-icon"]} strokeWidth={2} />
                    {trendPoints.length > 1
                      ? (() => {
                          const first = trendPoints[0]?.value ?? 0;
                          const last = trendPoints[trendPoints.length - 1]?.value ?? 0;
                          if (first <= 0) {
                            return "Önceki dönem kıyas verisi henüz oluşmadı.";
                          }
                          const ratio = ((last - first) / first) * 100;
                          return `Son 6 ayda hakediş tutarı %${formatNumber(Math.abs(ratio), 1)} ${ratio >= 0 ? "artış" : "daralma"} gösterdi.`;
                        })()
                      : "Trend verisi oluştukça buraya içgörü düşecek."}
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
                        <strong>{formatCompactMoney(totalDistributionAmount)}</strong>
                        <span>Toplam Hakediş</span>
                      </div>
                    </div>
                    <div className={styles["ck-payroll-donut-legend"]}>
                      {costModelItems.length ? (
                        costModelItems.map((item) => (
                          <div key={item.label} className={styles["ck-payroll-donut-legend-item"]}>
                            <span
                              className={styles["ck-payroll-donut-dot"]}
                              style={{ backgroundColor: item.color }}
                            />
                            <span className={styles["ck-payroll-donut-legend-label"]}>{item.label}</span>
                            <strong>{formatMoney(item.amount)}</strong>
                            <small>%{formatNumber(item.percent, 0)}</small>
                          </div>
                        ))
                      ) : (
                        <div className={styles["ck-payroll-empty-compact"]}>—</div>
                      )}
                    </div>
                  </div>
                  <div className={`${styles["ck-payroll-insight"]} ${styles["ck-payroll-insight-success"]}`}>
                    <PieChart className={styles["ck-payroll-insight-icon"]} strokeWidth={2} />
                    {costModelItems[0]
                      ? `Hakedişin %${formatNumber(costModelItems[0].percent, 0)}'si ${costModelItems[0].label.toLocaleLowerCase("tr-TR")} modelden geliyor.`
                      : "Dağılım verisi oluştuğunda baskın model burada görünecek."}
                  </div>
                </article>
              </section>

              <section className={styles["ck-payroll-section"]}>
                <div className={styles["ck-payroll-section-heading"]}>
                  <h2>Verimlilik Özeti</h2>
                  <p>Hız ve hacim tarafında operasyon ritmini aynı alanda okuyun.</p>
                </div>
                <div className={styles["ck-payroll-efficiency"]}>
                  {efficiencyCards.map((item, index) => (
                    <article key={item.label} className={styles["ck-payroll-mini-card"]}>
                      <div className={styles["ck-payroll-mini-label"]}>{item.label}</div>
                      <div className={styles["ck-payroll-mini-value"]}>{item.value}</div>
                      <div
                        className={`${styles["ck-payroll-delta"]} ${
                          item.delta.tone === "positive"
                            ? styles["ck-payroll-delta-positive"]
                            : item.delta.tone === "negative"
                              ? styles["ck-payroll-delta-negative"]
                              : ""
                        }`}
                      >
                        {item.delta.label}
                      </div>
                      <svg viewBox="0 0 120 40" className={styles["ck-payroll-sparkline"]} aria-hidden="true">
                        <path
                          d={buildPath(item.spark.length ? item.spark : [0], 120, 40, 6)}
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
                  {[
                    { title: "En Yüksek Net Ödeme", rows: highestNetPayment },
                    { title: "En Yüksek Kesinti Tutarı", rows: highestDeduction },
                    { title: "En Verimli Kuryeler", rows: mostEfficient },
                  ].map((board) => (
                    <article key={board.title} className={styles["ck-payroll-leaderboard-card"]}>
                      <div className={styles["ck-payroll-leaderboard-head"]}>
                        <h3>{board.title}</h3>
                        <button type="button" className={styles["ck-payroll-link-button"]}>
                          Tümünü Gör
                        </button>
                      </div>
                      <div className={styles["ck-payroll-leaderboard-list"]}>
                        {board.rows.length ? (
                          board.rows.map((row) => (
                            <button
                              key={`${board.title}-${row.rank}-${row.name}`}
                              type="button"
                              className={styles["ck-payroll-leaderboard-row"]}
                              onClick={() => row.personnelId && setSelectedPersonnelId(row.personnelId)}
                            >
                              <span className={styles["ck-payroll-rank-badge"]}>{row.rank}</span>
                              <span className={styles["ck-payroll-avatar-small"]}>{getInitials(row.name)}</span>
                              <div className={styles["ck-payroll-leaderboard-copy"]}>
                                <strong>{row.name}</strong>
                                <span>{row.role}</span>
                              </div>
                              <span className={styles["ck-payroll-leaderboard-value"]}>{row.value}</span>
                            </button>
                          ))
                        ) : (
                          <div className={styles["ck-payroll-empty-compact"]}>—</div>
                        )}
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
                    <span className={styles["ck-payroll-panel-avatar"]}>{getInitials(selectedPersonName)}</span>
                    <div className={styles["ck-payroll-panel-copy"]}>
                      <strong>{selectedPersonName}</strong>
                      <span>{selectedPersonRole}</span>
                    </div>
                  </div>
                  <div className={styles["ck-payroll-panel-actions"]}>
                    <span className={styles["ck-payroll-status-badge"]}>{selectedPersonStatus}</span>
                    <button type="button" className={styles["ck-payroll-kebab"]}>
                      <MoreHorizontal className={styles["ck-payroll-kebab-icon"]} strokeWidth={2} />
                    </button>
                  </div>
                </div>

                <div className={styles["ck-payroll-panel-metrics"]}>
                  <article className={styles["ck-payroll-panel-metric-card"]}>
                    <span>Net Ödeme</span>
                    <strong>{selectedPersonNetPayment}</strong>
                    <small className={styles["ck-payroll-metric-foot-positive"]}>
                      {buildDelta(
                        selectedPersonnel?.net_payment ?? null,
                        previousSeries?.entries.find((entry) => entry.personnel_id === selectedPersonnel?.personnel_id)?.net_payment ?? null,
                        true,
                      ).label}
                    </small>
                  </article>
                  <article className={styles["ck-payroll-panel-metric-card"]}>
                    <span>Hakediş Tutarı</span>
                    <strong>{selectedPersonGrossPay}</strong>
                  </article>
                  <article className={styles["ck-payroll-panel-metric-card"]}>
                    <span>Toplam Kesinti</span>
                    <strong>{selectedPersonDeductionsTotal}</strong>
                    <small>{deductionLoading ? "Yükleniyor…" : `${selectedPersonDeductions.length} kalem`}</small>
                  </article>
                  <article className={styles["ck-payroll-panel-metric-card"]}>
                    <span>Toplam Tevkifat</span>
                    <strong>{selectedPersonTevkifat}</strong>
                    <small>KDV + Tevkifat</small>
                  </article>
                </div>

                <div className={styles["ck-payroll-panel-list"]}>
                  <div className={styles["ck-payroll-panel-list-head"]}>Kesinti Kalemleri</div>
                  {selectedPersonDeductions.length ? (
                    selectedPersonDeductions.map((row) => (
                      <div key={row.label} className={styles["ck-payroll-panel-list-row"]}>
                        <span>{row.label}</span>
                        <strong>{formatMoney(row.amount)}</strong>
                      </div>
                    ))
                  ) : (
                    <div className={styles["ck-payroll-panel-list-row"]}>
                      <span>—</span>
                      <strong>—</strong>
                    </div>
                  )}
                  <div className={styles["ck-payroll-panel-list-total"]}>
                    <span>Toplam Kesinti</span>
                    <strong>{selectedPersonDeductionsTotal}</strong>
                  </div>
                </div>

                <button type="button" className={styles["ck-payroll-primary-button"]} onClick={handleDocumentDownload} disabled={documentBusy}>
                  <Download className={styles["ck-payroll-primary-icon"]} strokeWidth={2} />
                  {documentBusy ? "PDF hazırlanıyor..." : "Hakediş PDF’i İndir"}
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
