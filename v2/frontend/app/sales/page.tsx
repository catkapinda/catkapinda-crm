"use client";

import { useEffect, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { SalesEntryWorkspace } from "../../components/sales/sales-entry-workspace";
import { SalesManagementWorkspace } from "../../components/sales/sales-management-workspace";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type SalesDashboard = {
  module: string;
  status: string;
  summary: {
    total_entries: number;
    open_follow_up: number;
    proposal_stage: number;
    won_count: number;
  };
  recent_entries: Array<{
    id: number;
    restaurant_name: string;
    city: string;
    district: string;
    contact_name: string;
    lead_source: string;
    proposed_quote: number;
    pricing_model_label: string;
    status: string;
    assigned_owner: string;
    updated_at: string;
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

export default function SalesPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<SalesDashboard | null>(null);
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
        const response = await apiFetch("/sales/dashboard?limit=12");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as SalesDashboard;
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
    <AppShell activeItem="Satış">
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
            Sales v2
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 3vw, 2.8rem)",
              lineHeight: 1.05,
            }}
          >
            Ticari takip ve teklif akisi yeni shell'e tasiniyor.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "74ch",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Firsat havuzu, teklif modeli ve takip aksiyonlari artik parcali ve daha hizli
            bir arayuzde yonetilecek.
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
            Sales dashboard yukleniyor...
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
            Sales API su anda erisilebilir degil. Backend ayaga kalktiginda bu ekran
            canli firsat ozetini gosterecek.
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
              {metricCard("Toplam Firsat", String(dashboard.summary.total_entries), "accent")}
              {metricCard("Acik Takip", String(dashboard.summary.open_follow_up))}
              {metricCard("Teklif Asamasi", String(dashboard.summary.proposal_stage))}
              {metricCard("Kazanilan", String(dashboard.summary.won_count))}
            </div>

            <SalesEntryWorkspace />
            <SalesManagementWorkspace />
          </>
        )}
      </section>
    </AppShell>
  );
}
