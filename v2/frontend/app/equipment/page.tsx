"use client";

import { useEffect, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { EquipmentEntryWorkspace } from "../../components/equipment/equipment-entry-workspace";
import { EquipmentManagementWorkspace } from "../../components/equipment/equipment-management-workspace";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type EquipmentDashboard = {
  module: string;
  status: string;
  summary: {
    total_issues: number;
    this_month_issues: number;
    installment_rows: number;
    total_box_returns: number;
    total_box_payout: number;
    distinct_items: number;
  };
  recent_issues: Array<{
    id: number;
    personnel_label: string;
    issue_date: string;
    item_name: string;
    quantity: number;
    total_sale: number;
    sale_type: string;
    is_auto_record: boolean;
  }>;
  recent_box_returns: Array<{
    id: number;
    personnel_label: string;
    return_date: string;
    quantity: number;
    condition_status: string;
    payout_amount: number;
    waived: boolean;
  }>;
  installment_entries: Array<{
    deduction_date: string;
    personnel_label: string;
    deduction_type: string;
    amount: number;
    notes: string;
  }>;
  sales_profit: Array<{
    item_name: string;
    sold_qty: number;
    total_cost: number;
    total_sale: number;
    gross_profit: number;
  }>;
  purchase_summary: Array<{
    item_name: string;
    purchased_qty: number;
    purchased_total: number;
    weighted_unit_cost: number;
  }>;
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function metricCard(label: string, value: string, tone: "accent" | "soft" = "soft") {
  return (
    <article
      key={label}
      style={{
        padding: "18px",
        borderRadius: "20px",
        border: "1px solid var(--line)",
        background: tone === "accent" ? "rgba(15, 95, 215, 0.06)" : "var(--surface)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.82rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div
        style={{
          marginTop: "10px",
          fontSize: "1.85rem",
          fontWeight: 900,
          letterSpacing: "-0.04em",
        }}
      >
        {value}
      </div>
    </article>
  );
}

function listCard(
  title: string,
  subtitle: string,
  items: Array<{ title: string; meta: string; value: string }>,
) {
  return (
    <section
      style={{
        display: "grid",
        gap: "12px",
        padding: "20px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
        boxShadow: "0 18px 42px rgba(20, 39, 67, 0.06)",
      }}
    >
      <div>
        <h2 style={{ margin: 0, fontSize: "1.08rem" }}>{title}</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>{subtitle}</p>
      </div>
      <div
        style={{
          display: "grid",
          gap: "10px",
          maxHeight: "280px",
          overflow: "auto",
          paddingRight: "4px",
        }}
      >
        {items.length ? (
          items.map((item, index) => (
            <article
              key={`${title}-${index}-${item.title}`}
              style={{
                display: "grid",
                gap: "6px",
                padding: "14px 16px",
                borderRadius: "18px",
                border: "1px solid var(--line)",
                background: "rgba(255, 255, 255, 0.88)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "12px",
                  alignItems: "center",
                }}
              >
                <strong>{item.title}</strong>
                <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>{item.value}</span>
              </div>
              <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>{item.meta}</div>
            </article>
          ))
        ) : (
          <div
            style={{
              padding: "18px",
              borderRadius: "16px",
              border: "1px dashed rgba(15, 95, 215, 0.25)",
              color: "var(--muted)",
              background: "rgba(255, 255, 255, 0.72)",
            }}
          >
            Henuz kayit yok.
          </div>
        )}
      </div>
    </section>
  );
}

export default function EquipmentPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<EquipmentDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);

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
        const response = await apiFetch("/equipment/dashboard?limit=10");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as EquipmentDashboard;
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
  }, [loading, user]);

  return (
    <AppShell activeItem="Ekipman">
      <section style={{ display: "grid", gap: "18px" }}>
        <div
          style={{
            padding: "24px 26px",
            borderRadius: "28px",
            background: "var(--surface-strong)",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
          }}
        >
          <div
            style={{
              display: "inline-flex",
              padding: "7px 12px",
              borderRadius: "999px",
              background: "var(--accent-soft)",
              color: "var(--accent)",
              fontSize: "0.78rem",
              fontWeight: 800,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            Equipment v2
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 3vw, 2.8rem)",
              lineHeight: 1.05,
            }}
          >
            Zimmet, taksit ve box geri alim akislarini yeni shell&apos;e tasiyoruz.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "74ch",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Ekipman operasyonu artik tek ekranda daha hizli kayit, daha kontrollu duzenleme
            ve daha okunur ozetlerle ilerliyor. Bu modulle Streamlit cikisi bir adim daha
            gercek hale geliyor.
          </p>
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
            Ekipman dashboard yukleniyor...
          </div>
        ) : !dashboard ? (
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
            Equipment API su anda erisilebilir degil. Backend ayaga kalktiginda bu ekran
            son zimmetleri, box iadelerini ve taksit akislarini gercek veriden gosterecek.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "14px",
              }}
            >
              {metricCard("Toplam Zimmet", String(dashboard.summary.total_issues), "accent")}
              {metricCard("Bu Ay Zimmet", String(dashboard.summary.this_month_issues))}
              {metricCard("Taksit Satiri", String(dashboard.summary.installment_rows))}
              {metricCard("Box Iadesi", String(dashboard.summary.total_box_returns))}
              {metricCard("Box Odemesi", formatCurrency(dashboard.summary.total_box_payout))}
              {metricCard("Ayrı Kalem", String(dashboard.summary.distinct_items))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "16px",
              }}
            >
              {listCard(
                "Son Zimmetler",
                "Operasyona son girilen ekipman teslimleri.",
                dashboard.recent_issues.map((entry) => ({
                  title: `${entry.item_name} · ${entry.personnel_label}`,
                  meta: `${entry.issue_date} · ${entry.quantity} adet · ${entry.sale_type}${entry.is_auto_record ? " · Otomatik" : ""}`,
                  value: formatCurrency(entry.total_sale),
                })),
              )}
              {listCard(
                "Son Box Iadeleri",
                "Geri alinan box ve varsa personele odeme tutari.",
                dashboard.recent_box_returns.map((entry) => ({
                  title: entry.personnel_label,
                  meta: `${entry.return_date} · ${entry.quantity} adet · ${entry.waived ? "Talep edilmedi" : entry.condition_status}`,
                  value: formatCurrency(entry.payout_amount),
                })),
              )}
              {listCard(
                "Taksit Akisi",
                "Zimmetten otomatik olusan deduction satirlari.",
                dashboard.installment_entries.map((entry) => ({
                  title: entry.personnel_label,
                  meta: `${entry.deduction_date} · ${entry.notes || entry.deduction_type}`,
                  value: formatCurrency(entry.amount),
                })),
              )}
            </div>

            <EquipmentEntryWorkspace />
            <EquipmentManagementWorkspace />
          </>
        )}
      </section>
    </AppShell>
  );
}
