"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiErrorMessage, apiFetch } from "../../lib/api";

type InvoicesDashboard = {
  month_options: string[];
  selected_month: string | null;
  summary: {
    selected_month: string;
    restaurant_count: number;
    total_hours: number;
    total_packages: number;
    total_revenue: number;
    total_personnel_cost: number;
    gross_profit: number;
    side_income_net: number;
  } | null;
  invoice_entries: Array<{
    restaurant_id: number | null;
    restaurant: string;
    pricing_model: string;
    total_hours: number;
    total_packages: number;
    net_invoice: number;
    gross_invoice: number;
  }>;
  profit_entries: Array<{
    restaurant: string;
    pricing_model: string;
    gross_invoice: number;
    direct_personnel_cost: number;
    gross_profit: number;
    profit_margin_percent: number;
  }>;
  distribution_entries: Array<{
    restaurant: string;
    personnel: string;
    role: string;
    total_hours: number;
    total_packages: number;
    allocated_cost: number;
    allocation_source: string;
  }>;
  invoice_drilldown_entries: Array<{
    restaurant: string;
    personnel: string;
    role: string;
    total_hours: number;
    total_packages: number;
    net_invoice_amount: number;
    gross_invoice_amount: number;
  }>;
  collection_entries: Array<{
    restaurant_id: number;
    restaurant: string;
    pricing_model: string;
    total_hours: number;
    total_packages: number;
    net_invoice: number;
    gross_invoice: number;
    direct_personnel_cost: number;
    gross_profit: number;
    status: string;
    due_date: string | null;
    collected_amount: number;
    remaining_amount: number;
    payment_date: string | null;
    last_contact_date: string | null;
    responsible_name: string;
    note: string;
  }>;
  collection_summary: {
    total_collected_amount: number;
    total_open_amount: number;
    overdue_amount: number;
    tracked_restaurant_count: number;
    collected_restaurant_count: number;
    overdue_restaurant_count: number;
    due_defined_restaurant_count: number;
  };
  collection_status_options: string[];
};

function normalizeInvoicesDashboard(
  payload: Partial<InvoicesDashboard>,
): InvoicesDashboard {
  return {
    month_options: payload.month_options ?? [],
    selected_month: payload.selected_month ?? null,
    summary: payload.summary ?? null,
    invoice_entries: payload.invoice_entries ?? [],
    profit_entries: payload.profit_entries ?? [],
    distribution_entries: payload.distribution_entries ?? [],
    invoice_drilldown_entries: payload.invoice_drilldown_entries ?? [],
    collection_entries: payload.collection_entries ?? [],
    collection_summary: payload.collection_summary ?? {
      total_collected_amount: 0,
      total_open_amount: 0,
      overdue_amount: 0,
      tracked_restaurant_count: 0,
      collected_restaurant_count: 0,
      overdue_restaurant_count: 0,
      due_defined_restaurant_count: 0,
    },
    collection_status_options: payload.collection_status_options ?? [
      "Bekliyor",
      "Planlandı",
      "Kısmi Tahsilat",
      "Tahsil Edildi",
      "Gecikti",
    ],
  };
}

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

const SHARED_SUPPORT_ROLES = new Set(["Joker", "Bölge Müdürü", "Bolge Muduru"]);

function formatMoney(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value || 0);
}

function formatNumber(value: number, decimals = 0) {
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value || 0);
}

function displayPricingModel(value: string) {
  const labels: Record<string, string> = {
    hourly_plus_package: "Saat + Paket",
    threshold_package: "Eşikli Paket",
    hourly_only: "Sadece Saatlik",
    fixed_monthly: "Sabit Aylık Ücret",
  };
  return labels[value] ?? value;
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

function escapeDelimitedCell(value: string) {
  return `"${value.replaceAll('"', '""')}"`;
}

function buildDelimitedText(rows: string[][], delimiter = ";") {
  return rows
    .map((row) => row.map((cell) => escapeDelimitedCell(cell)).join(delimiter))
    .join("\n");
}

function normalizeMoneyInput(value: string) {
  const normalized = value.trim().replace(/\s+/g, "").replace(/\./g, "").replace(",", ".");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function collectionStatusPalette(status: string) {
  switch (status) {
    case "Tahsil Edildi":
      return {
        background: "rgba(34,102,60,0.12)",
        color: "#22663c",
      };
    case "Kısmi Tahsilat":
      return {
        background: "rgba(185,116,41,0.14)",
        color: "var(--accent-strong)",
      };
    case "Gecikti":
      return {
        background: "rgba(158,36,48,0.12)",
        color: "#9e2430",
      };
    default:
      return {
        background: "rgba(24,40,59,0.07)",
        color: "var(--muted)",
      };
  }
}

type CollectionFormState = {
  status: string;
  due_date: string;
  collected_amount: string;
  payment_date: string;
  last_contact_date: string;
  responsible_name: string;
  note: string;
};

function buildCollectionFormState(
  statusOptions: string[],
  entry?: InvoicesDashboard["collection_entries"][number] | null,
): CollectionFormState {
  return {
    status: entry?.status ?? statusOptions[0] ?? "Bekliyor",
    due_date: entry?.due_date ?? "",
    collected_amount:
      entry && entry.collected_amount > 0 ? String(Number(entry.collected_amount.toFixed(2))) : "",
    payment_date: entry?.payment_date ?? "",
    last_contact_date: entry?.last_contact_date ?? "",
    responsible_name: entry?.responsible_name ?? "",
    note: entry?.note ?? "",
  };
}

export default function InvoicesPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<InvoicesDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardRefreshKey, setDashboardRefreshKey] = useState(0);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [invoiceQuery, setInvoiceQuery] = useState("");
  const [selectedRestaurant, setSelectedRestaurant] = useState("");
  const [exportMessage, setExportMessage] = useState("");
  const [exportError, setExportError] = useState("");
  const [collectionForm, setCollectionForm] = useState<CollectionFormState>(
    buildCollectionFormState([]),
  );
  const [collectionSaving, setCollectionSaving] = useState(false);
  const [collectionMessage, setCollectionMessage] = useState("");
  const [collectionError, setCollectionError] = useState("");

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
        const query = selectedMonth ? `?month=${encodeURIComponent(selectedMonth)}` : "";
        const response = await apiFetch(`/invoices/dashboard${query}`);
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = normalizeInvoicesDashboard(
          (await response.json()) as Partial<InvoicesDashboard>,
        );
        if (active) {
          setDashboard(payload);
          if (!selectedMonth && payload.selected_month) {
            setSelectedMonth(payload.selected_month);
          }
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
  }, [dashboardRefreshKey, loading, selectedMonth, user]);

  const filteredInvoiceEntries = useMemo(() => {
    const rows = dashboard?.invoice_entries ?? [];
    const query = invoiceQuery.trim().toLocaleLowerCase("tr-TR");
    if (!query) {
      return rows;
    }
    return rows.filter((row) =>
      `${row.restaurant} ${displayPricingModel(row.pricing_model)}`
        .toLocaleLowerCase("tr-TR")
        .includes(query),
    );
  }, [dashboard?.invoice_entries, invoiceQuery]);

  useEffect(() => {
    if (!filteredInvoiceEntries.length) {
      if (selectedRestaurant) {
        setSelectedRestaurant("");
      }
      return;
    }
    if (filteredInvoiceEntries.some((row) => row.restaurant === selectedRestaurant)) {
      return;
    }
    setSelectedRestaurant(filteredInvoiceEntries[0].restaurant);
  }, [filteredInvoiceEntries, selectedRestaurant]);

  const selectedInvoice = useMemo(() => {
    if (!selectedRestaurant) {
      return null;
    }
    return (
      filteredInvoiceEntries.find((row) => row.restaurant === selectedRestaurant) ??
      dashboard?.invoice_entries.find((row) => row.restaurant === selectedRestaurant) ??
      null
    );
  }, [dashboard?.invoice_entries, filteredInvoiceEntries, selectedRestaurant]);

  const selectedProfit = useMemo(() => {
    if (!selectedInvoice) {
      return null;
    }
    return (
      dashboard?.profit_entries.find((row) => row.restaurant === selectedInvoice.restaurant) ??
      null
    );
  }, [dashboard?.profit_entries, selectedInvoice]);

  const filteredCollectionEntries = useMemo(() => {
    const rows = dashboard?.collection_entries ?? [];
    const query = invoiceQuery.trim().toLocaleLowerCase("tr-TR");
    if (!query) {
      return rows;
    }
    return rows.filter((row) =>
      `${row.restaurant} ${displayPricingModel(row.pricing_model)} ${row.status}`
        .toLocaleLowerCase("tr-TR")
        .includes(query),
    );
  }, [dashboard?.collection_entries, invoiceQuery]);

  const selectedCollection = useMemo(() => {
    if (!selectedRestaurant) {
      return null;
    }
    return (
      filteredCollectionEntries.find((row) => row.restaurant === selectedRestaurant) ??
      dashboard?.collection_entries.find((row) => row.restaurant === selectedRestaurant) ??
      null
    );
  }, [dashboard?.collection_entries, filteredCollectionEntries, selectedRestaurant]);

  const selectedCouriers = useMemo(() => {
    if (!selectedInvoice) {
      return [] as Array<{
        personnel: string;
        role: string;
        total_hours: number;
        total_packages: number;
        net_invoice_amount: number;
        gross_invoice_amount: number;
        allocated_cost: number;
        has_shared_support_cost: boolean;
      }>;
    }
    const grouped = new Map<
      string,
      {
        personnel: string;
        role: string;
        total_hours: number;
        total_packages: number;
        net_invoice_amount: number;
        gross_invoice_amount: number;
        allocated_cost: number;
        has_shared_support_cost: boolean;
      }
    >();
    for (const row of dashboard?.invoice_drilldown_entries ?? []) {
      if (row.restaurant !== selectedInvoice.restaurant) {
        continue;
      }
      const key = `${row.personnel}::${row.role}`;
      const existing = grouped.get(key);
      if (existing) {
        existing.total_hours += row.total_hours;
        existing.total_packages += row.total_packages;
        existing.net_invoice_amount += row.net_invoice_amount;
        existing.gross_invoice_amount += row.gross_invoice_amount;
        continue;
      }
      grouped.set(key, {
        ...row,
        allocated_cost: 0,
        has_shared_support_cost: SHARED_SUPPORT_ROLES.has(row.role),
      });
    }
    for (const row of dashboard?.distribution_entries ?? []) {
      if (row.restaurant !== selectedInvoice.restaurant) {
        continue;
      }
      if (!SHARED_SUPPORT_ROLES.has(row.role)) {
        continue;
      }
      const key = `${row.personnel}::${row.role}`;
      const existing = grouped.get(key);
      if (existing) {
        existing.allocated_cost += row.allocated_cost;
        existing.has_shared_support_cost = true;
      }
    }
    return Array.from(grouped.values()).sort(
      (left, right) => right.net_invoice_amount - left.net_invoice_amount,
    );
  }, [dashboard?.distribution_entries, dashboard?.invoice_drilldown_entries, selectedInvoice]);

  useEffect(() => {
    setCollectionForm(
      buildCollectionFormState(dashboard?.collection_status_options ?? [], selectedCollection),
    );
    setCollectionError("");
    setCollectionMessage("");
  }, [dashboard?.collection_status_options, selectedCollection]);

  const summary = dashboard?.summary;
  const totalGrossInvoice = filteredInvoiceEntries.reduce(
    (total, row) => total + row.gross_invoice,
    0,
  );
  const totalHours = filteredInvoiceEntries.reduce((total, row) => total + row.total_hours, 0);
  const totalPackages = filteredInvoiceEntries.reduce(
    (total, row) => total + row.total_packages,
    0,
  );
  const maxGrossInvoice = Math.max(
    ...filteredInvoiceEntries.map((row) => row.gross_invoice || 0),
    1,
  );
  const directCost = selectedProfit?.direct_personnel_cost ?? 0;
  const maxCourierCost = Math.max(
    ...selectedCouriers.map((row) => row.net_invoice_amount || 0),
    1,
  );
  const todayKey = new Date().toLocaleDateString("sv-SE");
  const totalCollectedAmount = filteredCollectionEntries.reduce(
    (total, row) => total + row.collected_amount,
    0,
  );
  const totalOpenCollectionAmount = filteredCollectionEntries.reduce(
    (total, row) => total + row.remaining_amount,
    0,
  );
  const overdueCollectionEntries = filteredCollectionEntries.filter(
    (row) =>
      row.remaining_amount > 0 &&
      Boolean(row.due_date) &&
      String(row.due_date) < todayKey &&
      row.status !== "Tahsil Edildi",
  );
  const dueDefinedCollectionCount = filteredCollectionEntries.filter((row) => row.due_date).length;
  const topCollectionSummaryItems: Array<[string, string, string]> = [
    ["Açık Tahsilat", formatMoney(totalOpenCollectionAmount), "Kapanmamış bakiye"],
    ["Tahsil Edildi", formatMoney(totalCollectedAmount), "Alınan ödeme"],
    ["Geciken Şube", formatNumber(overdueCollectionEntries.length), "Vadesi geçmiş"],
    ["Vadesi Tanımlı", formatNumber(dueDefinedCollectionCount), "Ödeme günü belli"],
  ];

  async function saveCollectionCard() {
    const restaurantId = selectedCollection?.restaurant_id ?? selectedInvoice?.restaurant_id ?? 0;
    const collectionMonth = dashboard?.selected_month ?? selectedMonth;
    if (!restaurantId || !collectionMonth) {
      setCollectionError("Tahsilat kartını kaydetmek için geçerli şube ve ay seçili olmalı.");
      setCollectionMessage("");
      return;
    }

    setCollectionSaving(true);
    setCollectionError("");
    setCollectionMessage("");
    try {
      const response = await apiFetch("/invoices/collections", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          restaurant_id: restaurantId,
          collection_month: collectionMonth,
          status: collectionForm.status,
          due_date: collectionForm.due_date || null,
          collected_amount: normalizeMoneyInput(collectionForm.collected_amount),
          payment_date: collectionForm.payment_date || null,
          last_contact_date: collectionForm.last_contact_date || null,
          responsible_name: collectionForm.responsible_name.trim(),
          note: collectionForm.note.trim(),
        }),
      });
      if (!response.ok) {
        setCollectionError(
          await apiErrorMessage(response, "Tahsilat kartı kaydedilemedi."),
        );
        return;
      }
      setCollectionMessage("Tahsilat kartı kaydedildi.");
      setDashboardRefreshKey((current) => current + 1);
    } catch {
      setCollectionError("Tahsilat kartı kaydedilirken bağlantı kesildi.");
    } finally {
      setCollectionSaving(false);
    }
  }

  function downloadInvoiceCsv() {
    if (!filteredInvoiceEntries.length) {
      setExportError("Dışa aktarmak için görünür fatura kaydı olmalı.");
      setExportMessage("");
      return;
    }
    const headers = [
      "Şube",
      "Model",
      "Toplam Saat",
      "Toplam Paket",
      "KDV Hariç",
      "KDV Dahil",
      "Tahsilat Durumu",
      "Tahsil Edilen",
      "Kalan Bakiye",
      "Vade Tarihi",
    ];
    const collectionByRestaurant = new Map(
      filteredCollectionEntries.map((entry) => [entry.restaurant, entry]),
    );
    const rows = filteredInvoiceEntries.map((entry) => [
      entry.restaurant,
      displayPricingModel(entry.pricing_model),
      formatNumber(entry.total_hours, 1),
      formatNumber(entry.total_packages, 0),
      formatMoney(entry.net_invoice),
      formatMoney(entry.gross_invoice),
      collectionByRestaurant.get(entry.restaurant)?.status ?? "Bekliyor",
      formatMoney(collectionByRestaurant.get(entry.restaurant)?.collected_amount ?? 0),
      formatMoney(collectionByRestaurant.get(entry.restaurant)?.remaining_amount ?? entry.gross_invoice),
      collectionByRestaurant.get(entry.restaurant)?.due_date ?? "",
    ]);
    const csv = buildDelimitedText([headers, ...rows], ";");
    const month = dashboard?.selected_month || selectedMonth || "faturalar";
    triggerBrowserDownload(
      new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" }),
      `catkapinda_faturalar_${month}.csv`,
    );
    setExportError("");
    setExportMessage("Fatura ve tahsilat tablosu Türkçe finans formatıyla indirildi.");
  }

  return (
    <AppShell activeItem="Faturalar">
      <section style={{ display: "grid", gap: "14px" }}>
        <div
          style={{
            padding: "16px",
            borderRadius: "22px",
            background:
              "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,242,233,0.96))",
            border: "1px solid var(--line)",
            boxShadow: "0 16px 34px rgba(22, 42, 74, 0.06)",
            display: "grid",
            gap: "10px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.25fr) minmax(260px, 0.9fr)",
              gap: "10px",
              alignItems: "start",
            }}
          >
            <div style={{ display: "grid", gap: "10px", alignContent: "start" }}>
              <div
                style={{
                  display: "inline-flex",
                  width: "fit-content",
                  padding: "6px 10px",
                  borderRadius: "999px",
                  background: "var(--accent-soft)",
                  color: "var(--accent)",
                  fontSize: "0.68rem",
                  fontWeight: 800,
                  letterSpacing: "0.04em",
                  textTransform: "uppercase",
                }}
              >
                Fatura Kontrol
              </div>
              <div style={{ display: "grid", gap: "6px", maxWidth: "58ch" }}>
                <h1
                  style={{
                    ...serifStyle,
                    margin: 0,
                    fontSize: "clamp(1.75rem, 2.7vw, 2.55rem)",
                    lineHeight: 0.94,
                    fontWeight: 700,
                  }}
                >
                  Fatura, kurye maliyeti ve tahsilat aynı yüzeyde okunuyor.
                </h1>
                <p
                  style={{
                    margin: 0,
                    maxWidth: "56ch",
                    color: "var(--muted)",
                    fontSize: "0.88rem",
                    lineHeight: 1.55,
                  }}
                >
                  Restoran faturası, dağılan kurye payı ve ödeme takibi burada birlikte akıyor.
                  Alanı açıklama ile değil, doğrudan karar verdiren özetlerle kullanıyoruz.
                </p>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                  gap: "8px",
                }}
              >
                {topCollectionSummaryItems.map(([label, value, note]) => (
                  <article
                    key={label}
                    style={{
                      padding: "12px",
                      borderRadius: "16px",
                      background: "rgba(255,255,255,0.7)",
                      border: "1px solid rgba(219,228,243,0.78)",
                      display: "grid",
                      gap: "4px",
                    }}
                  >
                    <div
                      style={{
                        color: "var(--muted)",
                        fontSize: "0.66rem",
                        fontWeight: 900,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {label}
                    </div>
                    <strong style={{ fontSize: "1rem", letterSpacing: "-0.03em" }}>{value}</strong>
                    <span style={{ color: "var(--muted)", fontSize: "0.76rem", lineHeight: 1.35 }}>
                      {note}
                    </span>
                  </article>
                ))}
              </div>
            </div>

            <div style={{ display: "grid", gap: "10px" }}>
              <article
                style={{
                  padding: "14px 14px 12px",
                  borderRadius: "18px",
                  background:
                    "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
                  color: "#fff7ea",
                  boxShadow: "var(--shadow-deep)",
                  display: "grid",
                  gap: "10px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "12px",
                    alignItems: "start",
                    flexWrap: "wrap",
                  }}
                >
                  <div style={{ display: "grid", gap: "6px" }}>
                    <div
                      style={{
                        color: "rgba(255,247,234,0.62)",
                        fontSize: "0.66rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                      }}
                    >
                      Dönem
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.45rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {(summary?.selected_month ?? selectedMonth) || "Ay seç"}
                    </div>
                  </div>
                  <div
                    style={{
                      display: "inline-flex",
                      padding: "6px 9px",
                      borderRadius: "999px",
                      background: "rgba(255,255,255,0.08)",
                      color: "rgba(255,247,234,0.82)",
                      fontSize: "0.72rem",
                      fontWeight: 800,
                    }}
                  >
                    Faturalar
                  </div>
                </div>
                <select
                  value={selectedMonth}
                  onChange={(event) => setSelectedMonth(event.target.value)}
                  disabled={dashboardLoading || !dashboard?.month_options?.length}
                  style={{
                    padding: "12px 14px",
                    borderRadius: "14px",
                    border: "1px solid rgba(255,255,255,0.1)",
                    background: "rgba(255,255,255,0.06)",
                    color: "#fff7ea",
                    fontWeight: 700,
                  }}
                >
                  {(dashboard?.month_options ?? []).map((month) => (
                    <option key={month} value={month} style={{ color: "#16283b" }}>
                      {month}
                    </option>
                  ))}
                </select>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "8px",
                  }}
                >
                  <div
                    style={{
                      padding: "10px 10px 9px",
                      borderRadius: "14px",
                      background: "rgba(255,255,255,0.06)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.64rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                      }}
                    >
                      Toplam Fatura
                    </div>
                    <div style={{ marginTop: "6px", fontSize: "0.96rem", fontWeight: 900 }}>
                      {formatMoney(summary?.total_revenue ?? 0)}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "10px 10px 9px",
                      borderRadius: "14px",
                      background: "rgba(185,116,41,0.14)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.64rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                      }}
                    >
                      Fatura-Kurye Farkı
                    </div>
                    <div style={{ marginTop: "6px", fontSize: "0.96rem", fontWeight: 900 }}>
                      {formatMoney(summary?.gross_profit ?? 0)}
                    </div>
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "10px",
                    flexWrap: "wrap",
                    marginTop: "2px",
                  }}
                >
                  <span style={{ color: "rgba(255,247,234,0.72)", fontSize: "0.8rem" }}>
                    Filtrelenmiş tabloyu ekip paylaşımı için indir.
                  </span>
                  <button
                    type="button"
                    onClick={downloadInvoiceCsv}
                    disabled={!filteredInvoiceEntries.length}
                    style={{
                      padding: "10px 12px",
                      borderRadius: "12px",
                      border: "1px solid rgba(255,255,255,0.12)",
                      background: "rgba(255,255,255,0.1)",
                      color: "#fff7ea",
                      fontWeight: 800,
                      cursor: filteredInvoiceEntries.length ? "pointer" : "not-allowed",
                      opacity: filteredInvoiceEntries.length ? 1 : 0.6,
                    }}
                  >
                    Fatura tablosunu indir
                  </button>
                </div>
                {exportError ? (
                  <div style={{ color: "#ffd2d7", fontSize: "0.82rem", fontWeight: 700 }}>
                    {exportError}
                  </div>
                ) : null}
                {exportMessage ? (
                  <div style={{ color: "#d8ffe3", fontSize: "0.82rem", fontWeight: 700 }}>
                    {exportMessage}
                  </div>
                ) : null}
              </article>
            </div>
          </div>
        </div>

        {dashboardLoading ? (
          <div
            style={{
              padding: "18px 20px",
              borderRadius: "22px",
              border: "1px solid rgba(15, 95, 215, 0.14)",
              background: "rgba(15, 95, 215, 0.06)",
              color: "var(--muted)",
            }}
          >
            Fatura verileri yükleniyor...
          </div>
        ) : !dashboard || !summary ? (
          <div
            style={{
              padding: "18px 20px",
              borderRadius: "22px",
              border: "1px dashed rgba(15, 95, 215, 0.35)",
              background: "rgba(255, 255, 255, 0.66)",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Fatura verileri şu an alınamadı. Bağlantı toparlandığında restoran faturası ve
            kurye dağılımı otomatik yenilenecek.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "10px",
              }}
            >
              {[
                ["Şube", formatNumber(filteredInvoiceEntries.length), "Filtreye düşen fatura satırı"],
                ["Toplam Fatura", formatMoney(totalGrossInvoice), "KDV dahil restoran faturası"],
                ["Toplam Saat", formatNumber(totalHours, 1), "Şube bazlı toplam çalışma"],
                ["Toplam Paket", formatNumber(totalPackages, 0), "Filtreye göre toplam hacim"],
              ].map(([label, value, note]) => (
                <article
                  key={label}
                  style={{
                    padding: "14px",
                    borderRadius: "18px",
                    border: "1px solid rgba(219, 228, 243, 0.85)",
                    background: "rgba(255,255,255,0.86)",
                    display: "grid",
                    gap: "5px",
                  }}
                >
                  <div
                    style={{
                      color: "var(--muted)",
                      fontSize: "0.66rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      fontWeight: 900,
                    }}
                  >
                    {label}
                  </div>
                  <div style={{ fontSize: "1.18rem", fontWeight: 900, letterSpacing: "-0.04em" }}>
                    {value}
                  </div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem", lineHeight: 1.45 }}>
                    {note}
                  </div>
                </article>
              ))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                gap: "14px",
                alignItems: "start",
              }}
            >
              <section
                style={{
                  borderRadius: "20px",
                  border: "1px solid rgba(219, 228, 243, 0.84)",
                  background: "rgba(255,255,255,0.82)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "14px 16px",
                    borderBottom: "1px solid rgba(219, 228, 243, 0.82)",
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "12px",
                    flexWrap: "wrap",
                  }}
                >
                  <div style={{ display: "grid", gap: "6px" }}>
                    <strong>Şube Fatura Listesi</strong>
                    <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                      En yüksek faturadan aşağı doğru sıralanır.
                    </span>
                  </div>
                  <input
                    value={invoiceQuery}
                    onChange={(event) => setInvoiceQuery(event.target.value)}
                    placeholder="Şube veya model ara"
                    style={{
                      minWidth: "220px",
                      padding: "10px 12px",
                      borderRadius: "12px",
                      border: "1px solid var(--line)",
                      background: "rgba(255,255,255,0.96)",
                      color: "var(--text)",
                      fontSize: "0.84rem",
                    }}
                  />
                </div>

                <div
                  style={{
                    maxHeight: "680px",
                    overflow: "auto",
                    display: "grid",
                    gap: "10px",
                    padding: "12px",
                  }}
                >
                  {filteredInvoiceEntries.map((row) => {
                    const selected = selectedInvoice?.restaurant === row.restaurant;
                    const invoiceWidth = Math.max((row.gross_invoice / maxGrossInvoice) * 100, 6);
                    return (
                      <button
                        key={`${row.restaurant}-${row.pricing_model}`}
                        type="button"
                        onClick={() => setSelectedRestaurant(row.restaurant)}
                        style={{
                          textAlign: "left",
                          padding: "14px",
                          borderRadius: "18px",
                          border: selected
                            ? "1px solid rgba(15,95,215,0.28)"
                            : "1px solid rgba(219, 228, 243, 0.84)",
                          background: selected
                            ? "linear-gradient(180deg, rgba(15,95,215,0.08), rgba(255,255,255,0.96))"
                            : "rgba(255,255,255,0.88)",
                          boxShadow: selected ? "0 16px 28px rgba(15,95,215,0.12)" : "none",
                          display: "grid",
                          gap: "10px",
                          cursor: "pointer",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            gap: "12px",
                            alignItems: "start",
                            flexWrap: "wrap",
                          }}
                        >
                          <div style={{ display: "grid", gap: "6px" }}>
                            <strong style={{ fontSize: "0.98rem" }}>{row.restaurant}</strong>
                            <span
                              style={{
                                display: "inline-flex",
                                width: "fit-content",
                                padding: "6px 9px",
                                borderRadius: "999px",
                                background: "rgba(24,40,59,0.07)",
                                color: "var(--muted)",
                                fontSize: "0.74rem",
                                fontWeight: 800,
                              }}
                            >
                              {displayPricingModel(row.pricing_model)}
                            </span>
                          </div>
                          <div style={{ textAlign: "right", display: "grid", gap: "3px" }}>
                            <strong style={{ fontSize: "1rem" }}>{formatMoney(row.gross_invoice)}</strong>
                            <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>KDV dahil</span>
                          </div>
                        </div>

                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                            gap: "8px",
                          }}
                        >
                          {[
                            ["Saat", formatNumber(row.total_hours, 1)],
                            ["Paket", formatNumber(row.total_packages, 0)],
                            ["KDV Hariç", formatMoney(row.net_invoice)],
                          ].map(([label, value]) => (
                            <div
                              key={label}
                              style={{
                                padding: "9px 10px",
                                borderRadius: "14px",
                                background: "rgba(24,40,59,0.05)",
                                display: "grid",
                                gap: "3px",
                              }}
                            >
                              <span
                                style={{
                                  color: "var(--muted)",
                                  fontSize: "0.68rem",
                                  fontWeight: 900,
                                  textTransform: "uppercase",
                                  letterSpacing: "0.05em",
                                }}
                              >
                                {label}
                              </span>
                              <strong style={{ fontSize: "0.88rem" }}>{value}</strong>
                            </div>
                          ))}
                        </div>

                        <div style={{ display: "grid", gap: "6px" }}>
                          <div
                            style={{
                              height: "10px",
                              borderRadius: "999px",
                              background: "rgba(24,40,59,0.08)",
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                width: `${invoiceWidth}%`,
                                height: "100%",
                                borderRadius: "999px",
                                background: selected
                                  ? "linear-gradient(90deg, rgba(15,95,215,0.98), rgba(80,150,255,0.92))"
                                  : "linear-gradient(90deg, rgba(185,116,41,0.92), rgba(233,184,120,0.88))",
                              }}
                            />
                          </div>
                        </div>
                      </button>
                    );
                  })}

                  {!filteredInvoiceEntries.length ? (
                    <div
                      style={{
                        padding: "16px",
                        borderRadius: "16px",
                        border: "1px dashed rgba(15,95,215,0.24)",
                        color: "var(--muted)",
                        lineHeight: 1.6,
                        fontSize: "0.84rem",
                      }}
                    >
                      Aramana uygun restoran faturası bulunamadı.
                    </div>
                  ) : null}
                </div>
              </section>

              <section style={{ display: "grid", gap: "12px" }}>
                {selectedInvoice ? (
                  <>
                    <article
                      style={{
                        padding: "18px",
                        borderRadius: "22px",
                        background:
                          "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
                        color: "#fff7ea",
                        display: "grid",
                        gap: "14px",
                        boxShadow: "var(--shadow-deep)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "16px",
                          alignItems: "start",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ display: "grid", gap: "6px" }}>
                          <div
                            style={{
                              color: "rgba(255,247,234,0.62)",
                              fontSize: "0.68rem",
                              fontWeight: 900,
                              letterSpacing: "0.08em",
                              textTransform: "uppercase",
                            }}
                          >
                            Seçili Şube
                          </div>
                          <h2
                            style={{
                              ...serifStyle,
                              margin: 0,
                              fontSize: "clamp(1.6rem, 2vw, 2.3rem)",
                              lineHeight: 0.94,
                              fontWeight: 700,
                            }}
                          >
                            {selectedInvoice.restaurant}
                          </h2>
                        </div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                          {[
                            displayPricingModel(selectedInvoice.pricing_model),
                            `${formatNumber(selectedInvoice.total_hours, 1)} saat`,
                            `${formatNumber(selectedInvoice.total_packages, 0)} paket`,
                            `${formatNumber(selectedCouriers.length)} kişi`,
                          ].map((item) => (
                            <span
                              key={item}
                              style={{
                                display: "inline-flex",
                                padding: "7px 10px",
                                borderRadius: "999px",
                                background: "rgba(255,255,255,0.08)",
                                color: "#fff7ea",
                                fontSize: "0.76rem",
                                fontWeight: 800,
                              }}
                            >
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
                          gap: "10px",
                        }}
                      >
                        {[
                          ["KDV Hariç", formatMoney(selectedInvoice.net_invoice), "Net restoran faturası"],
                          ["KDV Dahil", formatMoney(selectedInvoice.gross_invoice), "Kesilen toplam fatura"],
                          ["Şube Kurye Payı", formatMoney(directCost), "Bu şubeye dağılan doğrudan kurye maliyeti"],
                          ["Fatura-Kurye Farkı", formatMoney(selectedProfit?.gross_profit ?? 0), "Şubenin doğrudan farkı"],
                        ].map(([label, value, note]) => (
                          <article
                            key={label}
                            style={{
                              padding: "12px 13px",
                              borderRadius: "16px",
                              background: "rgba(255,255,255,0.08)",
                              display: "grid",
                              gap: "4px",
                            }}
                          >
                            <div
                              style={{
                                color: "rgba(255,247,234,0.62)",
                                fontSize: "0.64rem",
                                fontWeight: 900,
                                letterSpacing: "0.06em",
                                textTransform: "uppercase",
                              }}
                            >
                              {label}
                            </div>
                            <div style={{ fontSize: "1.06rem", fontWeight: 900 }}>{value}</div>
                            <div style={{ color: "rgba(255,247,234,0.68)", fontSize: "0.78rem", lineHeight: 1.45 }}>
                              {note}
                            </div>
                          </article>
                        ))}
                      </div>
                    </article>

                    <section
                      style={{
                        borderRadius: "20px",
                        border: "1px solid rgba(219, 228, 243, 0.84)",
                        background: "rgba(255,255,255,0.9)",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          padding: "14px 16px",
                          borderBottom: "1px solid rgba(219, 228, 243, 0.82)",
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ display: "grid", gap: "4px" }}>
                          <strong>Kurye Bazlı Fatura Katkısı</strong>
                          <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                            Ana tutar, seçilen şubede bu kişinin oluşturduğu KDV hariç fatura katkısıdır.
                            Maliyet payı yalnızca Joker ve Bölge Müdürü desteğinde görünür.
                          </span>
                        </div>
                        <span
                          style={{
                            display: "inline-flex",
                            padding: "7px 10px",
                            borderRadius: "999px",
                            background: "rgba(24,40,59,0.06)",
                            color: "var(--text)",
                            fontSize: "0.78rem",
                            fontWeight: 800,
                          }}
                        >
                          {selectedCouriers.length} kişi
                        </span>
                      </div>

                      {selectedCouriers.length ? (
                        <div style={{ maxHeight: "360px", overflow: "auto", display: "grid", gap: "0" }}>
                          {selectedCouriers.map((row) => (
                            <article
                              key={`${selectedInvoice.restaurant}-${row.personnel}-${row.role}`}
                              style={{
                                padding: "14px 16px",
                                borderTop: "1px solid rgba(219, 228, 243, 0.58)",
                                display: "grid",
                                gap: "8px",
                              }}
                            >
                              <div
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  gap: "12px",
                                  alignItems: "start",
                                  flexWrap: "wrap",
                                }}
                              >
                                <div style={{ display: "grid", gap: "4px" }}>
                                  <strong>{row.personnel}</strong>
                                  <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                                    {row.role} · {formatNumber(row.total_hours, 1)} saat ·{" "}
                                    {formatNumber(row.total_packages, 0)} paket
                                  </span>
                                </div>
                                <div style={{ display: "grid", gap: "4px", textAlign: "right" }}>
                                  <strong style={{ fontSize: "0.98rem" }}>{formatMoney(row.net_invoice_amount)}</strong>
                                  <span style={{ color: "var(--muted)", fontSize: "0.76rem" }}>
                                    KDV dahil {formatMoney(row.gross_invoice_amount)}
                                    {row.has_shared_support_cost && row.allocated_cost > 0
                                      ? ` · Maliyet payı ${formatMoney(row.allocated_cost)}`
                                      : ""}
                                  </span>
                                </div>
                              </div>
                              <div
                                style={{
                                  height: "10px",
                                  borderRadius: "999px",
                                  background: "rgba(24,40,59,0.08)",
                                  overflow: "hidden",
                                }}
                              >
                                <div
                                  style={{
                                    width: `${Math.max((row.net_invoice_amount / maxCourierCost) * 100, 6)}%`,
                                    height: "100%",
                                    borderRadius: "999px",
                                    background:
                                      "linear-gradient(90deg, rgba(15,95,215,0.92), rgba(80,150,255,0.88))",
                                  }}
                                />
                              </div>
                            </article>
                          ))}
                        </div>
                      ) : (
                        <div
                          style={{
                            padding: "16px",
                            color: "var(--muted)",
                            lineHeight: 1.6,
                            fontSize: "0.84rem",
                          }}
                        >
                          Bu şube için seçili ayda dağılım satırı henüz oluşmadı.
                        </div>
                      )}
                    </section>
                  </>
                ) : (
                  <div
                    style={{
                      padding: "24px",
                      borderRadius: "20px",
                      border: "1px dashed rgba(15,95,215,0.3)",
                      background: "rgba(255,255,255,0.84)",
                      color: "var(--muted)",
                      lineHeight: 1.7,
                    }}
                  >
                    Sol taraftan bir şube seçtiğinde restoran faturası ve kurye dağılımı burada açılacak.
                  </div>
                )}
              </section>
            </div>

            <section
              style={{
                borderRadius: "22px",
                border: "1px solid rgba(219, 228, 243, 0.88)",
                background:
                  "linear-gradient(180deg, rgba(255,255,255,0.98), rgba(241,247,255,0.92))",
                boxShadow: "0 16px 34px rgba(22, 42, 74, 0.05)",
                padding: "18px",
                display: "grid",
                gap: "14px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "16px",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                  }}
                >
                  <div style={{ display: "grid", gap: "5px", maxWidth: "58ch" }}>
                    <div
                      style={{
                        color: "#0f5fd7",
                        fontSize: "0.68rem",
                        fontWeight: 900,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                      }}
                    >
                      Tahsilat Masası
                    </div>
                    <h2
                      style={{
                        ...serifStyle,
                        margin: 0,
                        fontSize: "clamp(1.3rem, 1.8vw, 1.8rem)",
                        lineHeight: 0.98,
                        fontWeight: 700,
                      }}
                    >
                      Açık bakiye, vade ve son temas aynı akışta.
                    </h2>
                    <p
                      style={{
                        margin: 0,
                        color: "var(--muted)",
                        fontSize: "0.84rem",
                        lineHeight: 1.55,
                      }}
                    >
                      Seçili restoranın ödeme durumu burada kaydedilir; takip notu, vade ve alınan ödeme tek kartta tutulur.
                    </p>
                  </div>
                </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
                  gap: "10px",
                }}
              >
                {[
                  [
                    "Tahsil Edildi",
                    formatMoney(totalCollectedAmount),
                    "Filtrede görünen şubelerden kapanan ya da kısmi kapanan tahsilat toplamı",
                  ],
                  [
                    "Bekleyen Tahsilat",
                    formatMoney(totalOpenCollectionAmount),
                    "Görünür şubelerde henüz kapanmamış restoran bakiyesi",
                  ],
                  [
                    "Geciken Şube",
                    formatNumber(overdueCollectionEntries.length),
                    "Vadesi geçmiş ve halen açık bakiyesi olan restoran sayısı",
                  ],
                  [
                    "Vadesi Tanımlı",
                    formatNumber(dueDefinedCollectionCount),
                    "Ödeme günü belirlenmiş restoran satırları",
                  ],
                ].map(([label, value, note]) => (
                  <article
                    key={label}
                    style={{
                      padding: "14px",
                      borderRadius: "18px",
                      border: "1px solid rgba(219, 228, 243, 0.84)",
                      background: "rgba(255,255,255,0.88)",
                      display: "grid",
                      gap: "5px",
                    }}
                  >
                    <div
                      style={{
                        color: "var(--muted)",
                        fontSize: "0.66rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        fontWeight: 900,
                      }}
                    >
                      {label}
                    </div>
                    <div style={{ fontSize: "1.08rem", fontWeight: 900, letterSpacing: "-0.03em" }}>
                      {value}
                    </div>
                    <div style={{ color: "var(--muted)", fontSize: "0.8rem", lineHeight: 1.45 }}>
                      {note}
                    </div>
                  </article>
                ))}
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "minmax(0, 1.2fr) minmax(280px, 0.8fr)",
                  gap: "14px",
                  alignItems: "start",
                }}
              >
                <section
                  style={{
                    borderRadius: "20px",
                    border: "1px solid rgba(219, 228, 243, 0.84)",
                    background: "rgba(255,255,255,0.9)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      padding: "14px 16px",
                      borderBottom: "1px solid rgba(219, 228, 243, 0.82)",
                      display: "flex",
                      justifyContent: "space-between",
                      gap: "12px",
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ display: "grid", gap: "4px" }}>
                      <strong>Tahsilat Hattı</strong>
                      <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                        Tahsilat durumu ve açık bakiyesiyle hızlı takip listesi.
                      </span>
                    </div>
                    <span
                      style={{
                        display: "inline-flex",
                        padding: "7px 10px",
                        borderRadius: "999px",
                        background: "rgba(24,40,59,0.06)",
                        color: "var(--text)",
                        fontSize: "0.78rem",
                        fontWeight: 800,
                      }}
                    >
                      {filteredCollectionEntries.length} şube
                    </span>
                  </div>

                  <div style={{ display: "grid", gap: "0", maxHeight: "560px", overflow: "auto" }}>
                    {filteredCollectionEntries.length ? (
                      filteredCollectionEntries.map((entry, index) => {
                        const palette = collectionStatusPalette(entry.status);
                        const selected = selectedCollection?.restaurant === entry.restaurant;
                        return (
                          <button
                          type="button"
                          onClick={() => setSelectedRestaurant(entry.restaurant)}
                          key={`${entry.restaurant}-${entry.pricing_model}-collection`}
                          style={{
                            textAlign: "left",
                            padding: "14px 16px",
                            borderTop: index === 0 ? "none" : "1px solid rgba(219, 228, 243, 0.58)",
                            borderLeft: selected
                              ? "3px solid rgba(15,95,215,0.78)"
                              : "3px solid transparent",
                            background: selected
                              ? "linear-gradient(180deg, rgba(15,95,215,0.06), rgba(255,255,255,0.96))"
                              : "rgba(255,255,255,0.92)",
                            display: "grid",
                            gap: "8px",
                            cursor: "pointer",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              gap: "12px",
                              alignItems: "start",
                              flexWrap: "wrap",
                            }}
                          >
                            <div style={{ display: "grid", gap: "4px" }}>
                              <strong>{entry.restaurant}</strong>
                              <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                                {displayPricingModel(entry.pricing_model)} •{" "}
                                {formatNumber(entry.total_hours, 1)} saat •{" "}
                                {formatNumber(entry.total_packages, 0)} paket
                              </span>
                            </div>
                            <div style={{ textAlign: "right", display: "grid", gap: "4px" }}>
                              <strong style={{ fontSize: "0.96rem" }}>
                                {formatMoney(entry.remaining_amount)}
                              </strong>
                              <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                                Açık bakiye
                              </span>
                            </div>
                          </div>

                          <div
                            style={{
                              display: "flex",
                              flexWrap: "wrap",
                              gap: "8px",
                            }}
                          >
                            <span
                              style={{
                                display: "inline-flex",
                                padding: "6px 9px",
                                borderRadius: "999px",
                                background: palette.background,
                                color: palette.color,
                                fontSize: "0.74rem",
                                fontWeight: 800,
                              }}
                            >
                              {entry.status}
                            </span>
                            <span
                              style={{
                                display: "inline-flex",
                                padding: "6px 9px",
                                borderRadius: "999px",
                                background: "rgba(24,40,59,0.06)",
                                color: "var(--muted)",
                                fontSize: "0.74rem",
                                fontWeight: 800,
                              }}
                            >
                              Tahsil edilen {formatMoney(entry.collected_amount)}
                            </span>
                            {entry.due_date ? (
                              <span
                                style={{
                                  display: "inline-flex",
                                  padding: "6px 9px",
                                  borderRadius: "999px",
                                  background: "rgba(24,40,59,0.06)",
                                  color: "var(--muted)",
                                  fontSize: "0.74rem",
                                  fontWeight: 800,
                                }}
                              >
                                Vade {entry.due_date}
                              </span>
                            ) : null}
                          </div>
                        </button>
                      );
                      })
                    ) : (
                      <div
                        style={{
                          padding: "16px",
                          color: "var(--muted)",
                          lineHeight: 1.6,
                          fontSize: "0.84rem",
                        }}
                      >
                        Filtreye uyan tahsilat satırı görünmüyor.
                      </div>
                    )}
                  </div>
                </section>

                <section
                  style={{
                    borderRadius: "20px",
                    border: "1px solid rgba(219, 228, 243, 0.84)",
                    background: "rgba(255,255,255,0.9)",
                    padding: "16px",
                    display: "grid",
                    gap: "10px",
                  }}
                >
                  <div style={{ display: "grid", gap: "4px" }}>
                    <strong>Tahsilat Kartı</strong>
                    <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                      Seçili restoranın ödeme takibini doğrudan bu karttan güncelle.
                    </span>
                  </div>

                  {selectedCollection ? (
                    <>
                      <div
                        style={{
                          padding: "12px 13px",
                          borderRadius: "16px",
                          background: "rgba(24,40,59,0.05)",
                          display: "grid",
                          gap: "5px",
                        }}
                      >
                        <strong>{selectedCollection.restaurant}</strong>
                        <span style={{ color: "var(--muted)", fontSize: "0.82rem", lineHeight: 1.5 }}>
                          {displayPricingModel(selectedCollection.pricing_model)} •{" "}
                          {formatMoney(selectedCollection.gross_invoice)} fatura •{" "}
                          {formatMoney(selectedCollection.remaining_amount)} açık bakiye
                        </span>
                      </div>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                          gap: "10px",
                        }}
                      >
                        <label style={{ display: "grid", gap: "6px" }}>
                          <span style={{ fontSize: "0.8rem", fontWeight: 800 }}>Tahsilat durumu</span>
                          <select
                            value={collectionForm.status}
                            onChange={(event) =>
                              setCollectionForm((current) => ({
                                ...current,
                                status: event.target.value,
                              }))
                            }
                            style={{
                              padding: "11px 12px",
                              borderRadius: "12px",
                              border: "1px solid var(--line)",
                              background: "rgba(255,255,255,0.96)",
                              color: "var(--text)",
                            }}
                          >
                            {(dashboard?.collection_status_options ?? []).map((item) => (
                              <option key={item} value={item}>
                                {item}
                              </option>
                            ))}
                          </select>
                        </label>

                        <label style={{ display: "grid", gap: "6px" }}>
                          <span style={{ fontSize: "0.8rem", fontWeight: 800 }}>Vade tarihi</span>
                          <input
                            type="date"
                            value={collectionForm.due_date}
                            onChange={(event) =>
                              setCollectionForm((current) => ({
                                ...current,
                                due_date: event.target.value,
                              }))
                            }
                            style={{
                              padding: "11px 12px",
                              borderRadius: "12px",
                              border: "1px solid var(--line)",
                              background: "rgba(255,255,255,0.96)",
                              color: "var(--text)",
                            }}
                          />
                        </label>

                        <label style={{ display: "grid", gap: "6px" }}>
                          <span style={{ fontSize: "0.8rem", fontWeight: 800 }}>Tahsil edilen tutar</span>
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            value={collectionForm.collected_amount}
                            onChange={(event) =>
                              setCollectionForm((current) => ({
                                ...current,
                                collected_amount: event.target.value,
                              }))
                            }
                            placeholder="0"
                            style={{
                              padding: "11px 12px",
                              borderRadius: "12px",
                              border: "1px solid var(--line)",
                              background: "rgba(255,255,255,0.96)",
                              color: "var(--text)",
                            }}
                          />
                        </label>

                        <label style={{ display: "grid", gap: "6px" }}>
                          <span style={{ fontSize: "0.8rem", fontWeight: 800 }}>Ödeme tarihi</span>
                          <input
                            type="date"
                            value={collectionForm.payment_date}
                            onChange={(event) =>
                              setCollectionForm((current) => ({
                                ...current,
                                payment_date: event.target.value,
                              }))
                            }
                            style={{
                              padding: "11px 12px",
                              borderRadius: "12px",
                              border: "1px solid var(--line)",
                              background: "rgba(255,255,255,0.96)",
                              color: "var(--text)",
                            }}
                          />
                        </label>

                        <label style={{ display: "grid", gap: "6px" }}>
                          <span style={{ fontSize: "0.8rem", fontWeight: 800 }}>Son temas</span>
                          <input
                            type="date"
                            value={collectionForm.last_contact_date}
                            onChange={(event) =>
                              setCollectionForm((current) => ({
                                ...current,
                                last_contact_date: event.target.value,
                              }))
                            }
                            style={{
                              padding: "11px 12px",
                              borderRadius: "12px",
                              border: "1px solid var(--line)",
                              background: "rgba(255,255,255,0.96)",
                              color: "var(--text)",
                            }}
                          />
                        </label>

                        <label style={{ display: "grid", gap: "6px" }}>
                          <span style={{ fontSize: "0.8rem", fontWeight: 800 }}>Sorumlu kişi</span>
                          <input
                            value={collectionForm.responsible_name}
                            onChange={(event) =>
                              setCollectionForm((current) => ({
                                ...current,
                                responsible_name: event.target.value,
                              }))
                            }
                            placeholder="Tahsilatı takip eden kişi"
                            style={{
                              padding: "11px 12px",
                              borderRadius: "12px",
                              border: "1px solid var(--line)",
                              background: "rgba(255,255,255,0.96)",
                              color: "var(--text)",
                            }}
                          />
                        </label>
                      </div>

                      <label style={{ display: "grid", gap: "6px" }}>
                        <span style={{ fontSize: "0.8rem", fontWeight: 800 }}>Not</span>
                        <textarea
                          value={collectionForm.note}
                          onChange={(event) =>
                            setCollectionForm((current) => ({
                              ...current,
                              note: event.target.value,
                            }))
                          }
                          placeholder="Ödeme sözü, muhasebe notu veya takip özeti"
                          rows={4}
                          style={{
                            padding: "11px 12px",
                            borderRadius: "12px",
                            border: "1px solid var(--line)",
                            background: "rgba(255,255,255,0.96)",
                            color: "var(--text)",
                            resize: "vertical",
                            fontFamily: "inherit",
                          }}
                        />
                      </label>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                          gap: "10px",
                        }}
                      >
                        <div
                          style={{
                            padding: "11px 12px",
                            borderRadius: "14px",
                            background: "rgba(24,40,59,0.05)",
                            display: "grid",
                            gap: "3px",
                          }}
                        >
                          <span style={{ color: "var(--muted)", fontSize: "0.72rem", fontWeight: 800 }}>
                            Kalan bakiye
                          </span>
                          <strong>{formatMoney(selectedCollection.remaining_amount)}</strong>
                        </div>
                        <div
                          style={{
                            padding: "11px 12px",
                            borderRadius: "14px",
                            background: "rgba(24,40,59,0.05)",
                            display: "grid",
                            gap: "3px",
                          }}
                        >
                          <span style={{ color: "var(--muted)", fontSize: "0.72rem", fontWeight: 800 }}>
                            Şube kurye payı
                          </span>
                          <strong>{formatMoney(selectedCollection.direct_personnel_cost)}</strong>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={saveCollectionCard}
                        disabled={collectionSaving || selectedCollection.restaurant_id <= 0}
                        style={{
                          padding: "12px 14px",
                          borderRadius: "12px",
                          border: "1px solid rgba(15,95,215,0.15)",
                          background: collectionSaving
                            ? "rgba(15,95,215,0.12)"
                            : "linear-gradient(135deg, rgba(15,95,215,0.98), rgba(47,126,255,0.92))",
                          color: collectionSaving ? "#0f5fd7" : "#ffffff",
                          fontWeight: 900,
                          cursor:
                            collectionSaving || selectedCollection.restaurant_id <= 0
                              ? "not-allowed"
                              : "pointer",
                          opacity: collectionSaving || selectedCollection.restaurant_id <= 0 ? 0.7 : 1,
                        }}
                      >
                        {collectionSaving ? "Kaydediliyor..." : "Tahsilat Kartını Kaydet"}
                      </button>

                      {collectionError ? (
                        <div style={{ color: "#9e2430", fontSize: "0.84rem", fontWeight: 700 }}>
                          {collectionError}
                        </div>
                      ) : null}
                      {collectionMessage ? (
                        <div style={{ color: "#22663c", fontSize: "0.84rem", fontWeight: 700 }}>
                          {collectionMessage}
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <div
                      style={{
                        padding: "12px 13px",
                        borderRadius: "16px",
                        background: "rgba(24,40,59,0.05)",
                        color: "var(--muted)",
                        fontSize: "0.84rem",
                        lineHeight: 1.6,
                      }}
                    >
                      Soldaki listeden bir restoran seçildiğinde tahsilat kartı burada açılacak.
                    </div>
                  )}
                </section>
              </div>
            </section>
          </>
        )}
      </section>
    </AppShell>
  );
}
