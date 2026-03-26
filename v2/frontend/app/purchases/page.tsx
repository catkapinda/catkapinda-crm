"use client";

import { useEffect, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { PurchaseEntryWorkspace } from "../../components/purchases/purchase-entry-workspace";
import { PurchaseManagementWorkspace } from "../../components/purchases/purchase-management-workspace";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type PurchasesDashboard = {
  module: string;
  status: string;
  summary: {
    total_entries: number;
    this_month_entries: number;
    this_month_total_invoice: number;
    distinct_suppliers: number;
  };
  recent_entries: Array<{
    id: number;
    purchase_date: string;
    item_name: string;
    quantity: number;
    total_invoice_amount: number;
    unit_cost: number;
    supplier: string;
    invoice_no: string;
    notes: string;
  }>;
};

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

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

export default function PurchasesPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<PurchasesDashboard | null>(null);
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
        const response = await apiFetch("/purchases/dashboard?limit=12");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as PurchasesDashboard;
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
    <AppShell activeItem="Satın Alma">
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
            Purchases v2
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 3vw, 2.8rem)",
              lineHeight: 1.05,
            }}
          >
            Fatura girişi ve birim maliyet takibi yeni shell&apos;e taşınıyor.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "74ch",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Ekipman ve filo satın alma kayıtları artık daha hızlı ve daha kontrollü bir
            operasyon ekranında tutulacak.
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
            Satın alma dashboard yükleniyor...
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
            Purchases API şu anda erişilebilir değil. Backend ayakta olduğunda bu ekran
            satın alma özetini ve son kayıtları gösterecek.
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
              {metricCard("Toplam Kayıt", String(dashboard.summary.total_entries), "accent")}
              {metricCard("Bu Ay", String(dashboard.summary.this_month_entries))}
              {metricCard("Bu Ay Fatura", formatCurrency(dashboard.summary.this_month_total_invoice))}
              {metricCard("Tedarikçi", String(dashboard.summary.distinct_suppliers))}
            </div>

            <PurchaseEntryWorkspace />
            <PurchaseManagementWorkspace />
          </>
        )}
      </section>
    </AppShell>
  );
}
