"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

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
  } | null;
  invoice_entries: Array<{
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
  };
}

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

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

export default function InvoicesPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<InvoicesDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [invoiceQuery, setInvoiceQuery] = useState("");
  const [selectedRestaurant, setSelectedRestaurant] = useState("");
  const [exportMessage, setExportMessage] = useState("");
  const [exportError, setExportError] = useState("");

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
        const response = await apiFetch(`/reports/dashboard${query}`);
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
  }, [loading, selectedMonth, user]);

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

  const selectedCouriers = useMemo(() => {
    if (!selectedInvoice) {
      return [] as Array<{
        personnel: string;
        role: string;
        total_hours: number;
        total_packages: number;
        allocated_cost: number;
        allocation_source: string;
      }>;
    }
    const grouped = new Map<
      string,
      {
        personnel: string;
        role: string;
        total_hours: number;
        total_packages: number;
        allocated_cost: number;
        allocation_source: string;
      }
    >();
    for (const row of dashboard?.distribution_entries ?? []) {
      if (row.restaurant !== selectedInvoice.restaurant) {
        continue;
      }
      const key = `${row.personnel}::${row.role}`;
      const existing = grouped.get(key);
      if (existing) {
        existing.total_hours += row.total_hours;
        existing.total_packages += row.total_packages;
        existing.allocated_cost += row.allocated_cost;
        continue;
      }
      grouped.set(key, { ...row });
    }
    return Array.from(grouped.values()).sort(
      (left, right) => right.allocated_cost - left.allocated_cost,
    );
  }, [dashboard?.distribution_entries, selectedInvoice]);

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
  const selectedHourlyInvoice =
    selectedInvoice && selectedInvoice.total_hours > 0
      ? selectedInvoice.gross_invoice / selectedInvoice.total_hours
      : 0;
  const selectedPackageInvoice =
    selectedInvoice && selectedInvoice.total_packages > 0
      ? selectedInvoice.gross_invoice / selectedInvoice.total_packages
      : 0;
  const selectedCourierAverage =
    selectedCouriers.length > 0 ? directCost / selectedCouriers.length : 0;
  const selectedMarginPercent =
    selectedProfit?.profit_margin_percent ??
    (selectedInvoice && selectedInvoice.gross_invoice > 0 && selectedProfit
      ? (selectedProfit.gross_profit / selectedInvoice.gross_invoice) * 100
      : 0);
  const maxCourierCost = Math.max(
    ...selectedCouriers.map((row) => row.allocated_cost || 0),
    1,
  );
  const pendingCollectionAmount = totalGrossInvoice;
  const plannedCollectionCount = filteredInvoiceEntries.length;
  const collectionFocusEntries = filteredInvoiceEntries.slice(0, 6);

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
    ];
    const rows = filteredInvoiceEntries.map((entry) => [
      entry.restaurant,
      displayPricingModel(entry.pricing_model),
      formatNumber(entry.total_hours, 1),
      formatNumber(entry.total_packages, 0),
      formatMoney(entry.net_invoice),
      formatMoney(entry.gross_invoice),
    ]);
    const csv = buildDelimitedText([headers, ...rows], ";");
    const month = dashboard?.selected_month || selectedMonth || "faturalar";
    triggerBrowserDownload(
      new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8;" }),
      `catkapinda_faturalar_${month}.csv`,
    );
    setExportError("");
    setExportMessage("Fatura tablosu Türkçe finans formatıyla indirildi.");
  }

  return (
    <AppShell activeItem="Faturalar">
      <section style={{ display: "grid", gap: "14px" }}>
        <div
          style={{
            padding: "18px",
            borderRadius: "22px",
            background:
              "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,242,233,0.96))",
            border: "1px solid var(--line)",
            boxShadow: "0 16px 34px rgba(22, 42, 74, 0.06)",
            display: "grid",
            gap: "12px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.25fr) minmax(260px, 0.9fr)",
              gap: "12px",
              alignItems: "stretch",
            }}
          >
            <div style={{ display: "grid", gap: "12px", alignContent: "start" }}>
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
                Fatura Masası
              </div>
              <div style={{ display: "grid", gap: "8px", maxWidth: "64ch" }}>
                <h1
                  style={{
                    ...serifStyle,
                    margin: 0,
                    fontSize: "clamp(1.8rem, 3vw, 2.8rem)",
                    lineHeight: 0.94,
                    fontWeight: 700,
                  }}
                >
                  Restoran faturası ve kurye dağılımı tek sekmede.
                </h1>
                <p
                  style={{
                    margin: 0,
                    maxWidth: "62ch",
                    color: "var(--muted)",
                    fontSize: "0.9rem",
                    lineHeight: 1.6,
                  }}
                >
                  Bu yüzey restoran faturası okumak için kuruldu. Bir sonraki adımda tahsilat,
                  vade, ödeme durumu ve not takibini de aynı sekmeye ekleyebiliriz.
                </p>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {[
                  "Fatura ve dağılım aynı yerde",
                  "Tahsilat alanı hazır",
                  "Şube bazlı karar yüzeyi",
                ].map((item) => (
                  <span
                    key={item}
                    style={{
                      display: "inline-flex",
                      padding: "6px 10px",
                      borderRadius: "999px",
                      background: "rgba(15,95,215,0.08)",
                      color: "#0f5fd7",
                      fontSize: "0.74rem",
                      fontWeight: 800,
                    }}
                  >
                    {item}
                  </span>
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
                        fontSize: "1.5rem",
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
              </article>

              <article
                style={{
                  padding: "14px 14px 12px",
                  borderRadius: "18px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.78)",
                  display: "grid",
                  gap: "8px",
                }}
              >
                <div
                  style={{
                    color: "var(--muted)",
                    fontSize: "0.66rem",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Yaklaşan Katmanlar
                </div>
                {[
                  "Tahsilat durumu",
                  "Vade tarihi",
                  "Ödendi / bekliyor durumu",
                ].map((item) => (
                  <div
                    key={item}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "12px",
                      paddingBottom: "7px",
                      borderBottom: "1px solid rgba(24,40,59,0.08)",
                      fontSize: "0.84rem",
                    }}
                  >
                    <span style={{ color: "var(--muted)", fontWeight: 800 }}>{item}</span>
                    <strong>Hazır alan</strong>
                  </div>
                ))}
              </article>
            </div>
          </div>

          <section
            style={{
              borderRadius: "18px",
              border: "1px solid var(--line)",
              background: "rgba(255,255,255,0.78)",
              padding: "14px 16px",
              display: "flex",
              justifyContent: "space-between",
              gap: "16px",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <div style={{ display: "grid", gap: "4px" }}>
              <strong>Excel ve ekip paylaşımı için hazır</strong>
              <span style={{ color: "var(--muted)", fontSize: "0.84rem" }}>
                Filtrelenmiş şube faturasını tek tıkla dışa aktar.
              </span>
            </div>
            <button
              type="button"
              onClick={downloadInvoiceCsv}
              disabled={!filteredInvoiceEntries.length}
              style={{
                padding: "10px 12px",
                borderRadius: "12px",
                border: "1px solid rgba(15,95,215,0.15)",
                background: "rgba(15,95,215,0.08)",
                color: "#0f5fd7",
                fontWeight: 800,
                cursor: filteredInvoiceEntries.length ? "pointer" : "not-allowed",
                opacity: filteredInvoiceEntries.length ? 1 : 0.6,
              }}
            >
              Fatura tablosunu indir
            </button>
            {exportError ? (
              <div style={{ color: "#9e2430", fontSize: "0.84rem", fontWeight: 700 }}>
                {exportError}
              </div>
            ) : null}
            {exportMessage ? (
              <div style={{ color: "#22663c", fontSize: "0.84rem", fontWeight: 700 }}>
                {exportMessage}
              </div>
            ) : null}
          </section>
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

                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                        gap: "10px",
                      }}
                    >
                      {[
                        ["Saat Başına Fatura", formatMoney(selectedHourlyInvoice)],
                        ["Paket Başına Fatura", formatMoney(selectedPackageInvoice)],
                        ["Kurye Başına Ortalama", formatMoney(selectedCourierAverage)],
                        ["Doğrudan Marj", `%${formatNumber(selectedMarginPercent, 1)}`],
                      ].map(([label, value]) => (
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
                          <div style={{ fontSize: "1rem", fontWeight: 900 }}>{value}</div>
                        </article>
                      ))}
                    </div>

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
                          <strong>Kurye Dağılımı</strong>
                          <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                            Buradaki tutar, kuryenin toplam ay hakedişi değil; seçilen şubeye düşen payıdır.
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
                        <div style={{ maxHeight: "470px", overflow: "auto", display: "grid", gap: "0" }}>
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
                                <strong style={{ fontSize: "0.98rem" }}>{formatMoney(row.allocated_cost)}</strong>
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
                                    width: `${Math.max((row.allocated_cost / maxCourierCost) * 100, 6)}%`,
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
                <div style={{ display: "grid", gap: "6px", maxWidth: "68ch" }}>
                  <div
                    style={{
                      color: "#0f5fd7",
                      fontSize: "0.68rem",
                      fontWeight: 900,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    Tahsilat Tasarımı
                  </div>
                  <h2
                    style={{
                      ...serifStyle,
                      margin: 0,
                      fontSize: "clamp(1.45rem, 2vw, 2.05rem)",
                      lineHeight: 0.96,
                      fontWeight: 700,
                    }}
                  >
                    Faturadan sonra takip edeceğimiz tahsilat hattı hazır.
                  </h2>
                  <p
                    style={{
                      margin: 0,
                      color: "var(--muted)",
                      fontSize: "0.88rem",
                      lineHeight: 1.6,
                    }}
                  >
                    Burayı ödeme takibi için kurguladım. Şimdilik tasarım ve çalışma mantığı hazır;
                    vade, tahsilat tarihi, ödeme notu ve cari durum verisi bağlandığında aynı alan
                    canlı tahsilat masasına dönecek.
                  </p>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {["Tahsil edildi", "Bekliyor", "Vade", "Not"].map((item) => (
                    <span
                      key={item}
                      style={{
                        display: "inline-flex",
                        padding: "7px 10px",
                        borderRadius: "999px",
                        background: "rgba(15,95,215,0.08)",
                        color: "#0f5fd7",
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
                  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
                  gap: "10px",
                }}
              >
                {[
                  ["Tahsil Edildi", formatMoney(0), "Canlı ödeme akışı bağlandığında dolacak"],
                  [
                    "Bekleyen Tahsilat",
                    formatMoney(pendingCollectionAmount),
                    "Şu an fatura toplamı kadar açık tahsilat kabul ediyoruz",
                  ],
                  [
                    "Takipteki Şube",
                    formatNumber(plannedCollectionCount),
                    "Tahsilat planına girecek restoran satırı",
                  ],
                  ["Ortalama Vade", "Tanımsız", "Vade tarihi alanı sonraki adımda bağlanacak"],
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
                        İlk etapta hangi şubelerin ödeme planına alınacağını bu listede tutacağız.
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
                      MVP tasarım
                    </span>
                  </div>

                  <div style={{ display: "grid", gap: "0" }}>
                    {collectionFocusEntries.length ? (
                      collectionFocusEntries.map((entry, index) => (
                        <article
                          key={`${entry.restaurant}-${entry.pricing_model}-collection`}
                          style={{
                            padding: "14px 16px",
                            borderTop: index === 0 ? "none" : "1px solid rgba(219, 228, 243, 0.58)",
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
                              <strong>{entry.restaurant}</strong>
                              <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                                {displayPricingModel(entry.pricing_model)} •{" "}
                                {formatNumber(entry.total_hours, 1)} saat •{" "}
                                {formatNumber(entry.total_packages, 0)} paket
                              </span>
                            </div>
                            <strong style={{ fontSize: "0.96rem" }}>
                              {formatMoney(entry.gross_invoice)}
                            </strong>
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
                                background: "rgba(185,116,41,0.12)",
                                color: "var(--accent-strong)",
                                fontSize: "0.74rem",
                                fontWeight: 800,
                              }}
                            >
                              Tahsilat planlanacak
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
                              Vade bekleniyor
                            </span>
                          </div>
                        </article>
                      ))
                    ) : (
                      <div
                        style={{
                          padding: "16px",
                          color: "var(--muted)",
                          lineHeight: 1.6,
                          fontSize: "0.84rem",
                        }}
                      >
                        Tahsilat hattına düşecek fatura satırı görünmüyor.
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
                    <strong>Tahsilat Kartında Olacak Alanlar</strong>
                    <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                      Backend bağlanınca bu alanları gerçek veriye çevireceğiz.
                    </span>
                  </div>

                  {[
                    "Tahsilat durumu: Tahsil edildi / Bekliyor / Gecikti",
                    "Vade tarihi ve planlanan ödeme günü",
                    "Tahsil edilen tutar ve kalan bakiye",
                    "Restoran notu ve muhasebe açıklaması",
                    "Sorumlu kişi ve son takip zamanı",
                  ].map((item) => (
                    <div
                      key={item}
                      style={{
                        padding: "10px 12px",
                        borderRadius: "14px",
                        background: "rgba(24,40,59,0.05)",
                        color: "var(--text)",
                        fontSize: "0.84rem",
                        lineHeight: 1.5,
                      }}
                    >
                      {item}
                    </div>
                  ))}
                </section>
              </div>
            </section>
          </>
        )}
      </section>
    </AppShell>
  );
}
