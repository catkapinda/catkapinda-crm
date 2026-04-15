"use client";

import { useEffect, useMemo, useState } from "react";

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

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function formatDate(value: string) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function metricCard(label: string, value: string, note: string, tone: "accent" | "soft" = "soft") {
  return (
    <article
      key={label}
      style={{
        padding: "18px 18px 16px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background:
          tone === "accent"
            ? "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(246,239,228,0.96))"
            : "var(--surface-strong)",
        boxShadow: "0 18px 42px rgba(20, 39, 67, 0.06)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.78rem",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div
        style={{
          ...serifStyle,
          marginTop: "10px",
          fontSize: "2rem",
          lineHeight: 0.95,
          fontWeight: 700,
        }}
      >
        {value}
      </div>
      <div
        style={{
          marginTop: "8px",
          color: "var(--muted)",
          lineHeight: 1.6,
          fontSize: "0.92rem",
        }}
      >
        {note}
      </div>
    </article>
  );
}

function narrativeCard({
  eyebrow,
  title,
  body,
  tone = "paper",
}: {
  eyebrow: string;
  title: string;
  body: string;
  tone?: "paper" | "ink" | "accent";
}) {
  const palette =
    tone === "ink"
      ? {
          background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
          border: "1px solid rgba(255,255,255,0.08)",
          title: "#fff7ea",
          body: "rgba(255,247,234,0.72)",
          eyebrow: "rgba(255,247,234,0.62)",
        }
      : tone === "accent"
        ? {
            background: "linear-gradient(180deg, rgba(185,116,41,0.12), rgba(255,248,236,0.98))",
            border: "1px solid rgba(185,116,41,0.18)",
            title: "var(--text)",
            body: "var(--muted)",
            eyebrow: "var(--accent-strong)",
          }
        : {
            background: "rgba(255,255,255,0.84)",
            border: "1px solid var(--line)",
            title: "var(--text)",
            body: "var(--muted)",
            eyebrow: "var(--muted)",
          };

  return (
    <article
      style={{
        padding: "18px 18px 16px",
        borderRadius: "22px",
        background: palette.background,
        border: palette.border,
        boxShadow: tone === "ink" ? "var(--shadow-deep)" : "var(--shadow-soft)",
        display: "grid",
        gap: "10px",
      }}
    >
      <div
        style={{
          color: palette.eyebrow,
          fontSize: "0.74rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {eyebrow}
      </div>
      <div
        style={{
          ...serifStyle,
          color: palette.title,
          fontSize: "1.45rem",
          lineHeight: 0.98,
          fontWeight: 700,
        }}
      >
        {title}
      </div>
      <div
        style={{
          color: palette.body,
          fontSize: "0.93rem",
          lineHeight: 1.65,
        }}
      >
        {body}
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

  const decisionDeck = useMemo(() => {
    if (!dashboard) {
      return [];
    }

    const topEntry = dashboard.recent_entries[0] ?? null;
    const supplierTotals = new Map<string, { count: number; total: number }>();
    dashboard.recent_entries.forEach((entry) => {
      const current = supplierTotals.get(entry.supplier) ?? { count: 0, total: 0 };
      current.count += 1;
      current.total += entry.total_invoice_amount;
      supplierTotals.set(entry.supplier, current);
    });
    const dominantSupplier = [...supplierTotals.entries()].sort(
      (left, right) => right[1].total - left[1].total || right[1].count - left[1].count,
    )[0] ?? null;
    const averageInvoice =
      dashboard.summary.this_month_entries > 0
        ? dashboard.summary.this_month_total_invoice / dashboard.summary.this_month_entries
        : 0;
    const invoicePressure =
      dashboard.summary.this_month_total_invoice >= Math.max(50000, averageInvoice * 4);

    return [
      {
        eyebrow: "Fatura Nabzi",
        title: invoicePressure ? "Bu ay alis hacmi sertlesiyor." : "Alis ritmi kontrollu gorunuyor.",
        body: `${dashboard.summary.this_month_entries} kayit ile ${formatCurrency(dashboard.summary.this_month_total_invoice)} aylik fatura akisi tasiniyor. Bu oran stok ve maliyet yukunun ne kadar hizli buyudugunu anlatir.`,
        tone: invoicePressure ? "ink" : "paper",
      },
      {
        eyebrow: "En Sicak Alim",
        title: topEntry ? `${topEntry.item_name} / ${topEntry.supplier}` : "Alim sinyali henuz yok.",
        body: topEntry
          ? `${formatDate(topEntry.purchase_date)} tarihli ${topEntry.quantity} adet alim, ${formatCurrency(topEntry.total_invoice_amount)} fatura tasiyor. Birim maliyet ${formatCurrency(topEntry.unit_cost)} ile bu kalem ayni anda stok ve maliyet sinyali veriyor.`
          : "Yeni satin alma hareketleri geldikce burada ilk dikkat isteyen alim kaydi one cikarilacak.",
        tone: "paper",
      },
      {
        eyebrow: "Tedarikci Baskisi",
        title: dominantSupplier ? `${dominantSupplier[0]} onde gidiyor.` : "Tedarikci sinyali henuz yok.",
        body: dominantSupplier
          ? `${dominantSupplier[1].count} kayit ve ${formatCurrency(dominantSupplier[1].total)} toplam fatura ile alis akisinin agirlik merkezi burada toplaniyor. Tedarik riski ve fiyat pazarligi icin yakin takip edilmeli.`
          : "Tedarikci dagilimi geldikce burada hangi kanal agirlik kazaniyor daha net gorunecek.",
        tone: dominantSupplier && dominantSupplier[1].count >= 2 ? "accent" : "paper",
      },
    ] as const;
  }, [dashboard]);

  const supplierInsights = useMemo(() => {
    if (!dashboard) {
      return [];
    }
    const totals = new Map<string, { count: number; total: number }>();
    dashboard.recent_entries.forEach((entry) => {
      const current = totals.get(entry.supplier) ?? { count: 0, total: 0 };
      current.count += 1;
      current.total += entry.total_invoice_amount;
      totals.set(entry.supplier, current);
    });
    return [...totals.entries()]
      .sort((left, right) => right[1].total - left[1].total || right[1].count - left[1].count)
      .slice(0, 6)
      .map(([supplier, value]) => ({
        title: supplier,
        meta: `${value.count} alim kaydi`,
        value: formatCurrency(value.total),
      }));
  }, [dashboard]);

  const unitCostSignals = useMemo(() => {
    if (!dashboard) {
      return [];
    }
    return [...dashboard.recent_entries]
      .sort((left, right) => right.unit_cost - left.unit_cost)
      .slice(0, 6)
      .map((entry) => ({
        title: entry.item_name,
        meta: `${entry.supplier} · ${entry.quantity} adet · ${formatDate(entry.purchase_date)}`,
        value: formatCurrency(entry.unit_cost),
      }));
  }, [dashboard]);

  return (
    <AppShell activeItem="Satın Alma">
      <section style={{ display: "grid", gap: "18px" }}>
        <div
          style={{
            padding: "28px",
            borderRadius: "30px",
            background: "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,242,233,0.96))",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
            display: "grid",
            gap: "18px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.35fr) minmax(280px, 0.9fr)",
              gap: "18px",
              alignItems: "stretch",
            }}
          >
            <div
              style={{
                display: "grid",
                gap: "16px",
                alignContent: "start",
              }}
            >
              <div
                style={{
                  display: "inline-flex",
                  width: "fit-content",
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
                Satin Alma Room
              </div>
              <div style={{ display: "grid", gap: "10px", maxWidth: "72ch" }}>
                <h1
                  style={{
                    ...serifStyle,
                    margin: 0,
                    fontSize: "clamp(2.2rem, 4vw, 3.6rem)",
                    lineHeight: 0.96,
                    fontWeight: 700,
                  }}
                >
                  Satin alma akisini artik sadece kayit degil, maliyet ve tedarik baskisi olarak okuyoruz.
                </h1>
                <p
                  style={{
                    margin: 0,
                    maxWidth: "74ch",
                    color: "var(--muted)",
                    lineHeight: 1.76,
                    fontSize: "1.02rem",
                  }}
                >
                  Fatura hacmi, birim maliyet, tedarikci yogunlugu ve son alim hareketlerini ayni
                  karar katmaninda topluyoruz. Hedefimiz, alis tarafini sadece veri giris yeri degil;
                  stok ve maliyet nabzini okutan bir kontrol masasi haline getirmek.
                </p>
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(15,95,215,0.08)",
                    color: "#0f5fd7",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Fatura ve tedarik ayni hatta
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(185,116,41,0.1)",
                    color: "var(--accent-strong)",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Maliyet baskisi erken gorunur
                </span>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gap: "12px",
              }}
            >
              <article
                style={{
                  padding: "18px 18px 16px",
                  borderRadius: "24px",
                  background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
                  color: "#fff7ea",
                  boxShadow: "var(--shadow-deep)",
                  display: "grid",
                  gap: "14px",
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
                        fontSize: "0.74rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Satin Alma Nabzi
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.8rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {dashboard?.summary.this_month_entries ?? 0} aylik alim
                    </div>
                  </div>
                  <div
                    style={{
                      display: "inline-flex",
                      padding: "7px 10px",
                      borderRadius: "999px",
                      background: "rgba(255,255,255,0.08)",
                      color: "rgba(255,247,234,0.82)",
                      fontSize: "0.8rem",
                      fontWeight: 800,
                    }}
                  >
                    Purchase Desk
                  </div>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "10px",
                  }}
                >
                  <div
                    style={{
                      padding: "12px 12px 10px",
                      borderRadius: "16px",
                      background: "rgba(255,255,255,0.06)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.72rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Aylik Fatura
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {formatCurrency(dashboard?.summary.this_month_total_invoice ?? 0)}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "12px 12px 10px",
                      borderRadius: "16px",
                      background: "rgba(185,116,41,0.14)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.72rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Tedarikci
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.distinct_suppliers ?? 0}
                    </div>
                  </div>
                </div>
              </article>

              <article
                style={{
                  padding: "16px 18px",
                  borderRadius: "22px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.78)",
                  display: "grid",
                  gap: "8px",
                }}
              >
                <div
                  style={{
                    color: "var(--muted)",
                    fontSize: "0.74rem",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  Okuma Notu
                </div>
                <div
                  style={{
                    color: "var(--text)",
                    fontSize: "0.95rem",
                    lineHeight: 1.7,
                  }}
                >
                  Bu ekranda once aylik fatura hacmine, sonra tedarikci yogunluguna ve en son
                  birim maliyet sinyaline bakmak en saglikli satin alma okumasini verir.
                </div>
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
            Satin alma verileri yukleniyor...
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
            Satin alma servisine su anda erisilemiyor. Backend hazir oldugunda bu ekran faturayi,
            tedarikcileri ve maliyet sinyallerini gercek veriden gosterecek.
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
              {metricCard("Toplam Kayit", String(dashboard.summary.total_entries), "Tum alim zinciri", "accent")}
              {metricCard("Bu Ay", String(dashboard.summary.this_month_entries), "Aylik alim hareketi")}
              {metricCard("Bu Ay Fatura", formatCurrency(dashboard.summary.this_month_total_invoice), "Giren toplam alim faturasi")}
              {metricCard("Tedarikci", String(dashboard.summary.distinct_suppliers), "Aktif alim kaynagi sayisi")}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                gap: "14px",
              }}
            >
              {decisionDeck.map((item) => (
                <div key={`${item.eyebrow}-${item.title}`}>{narrativeCard(item)}</div>
              ))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "16px",
              }}
            >
              {listCard(
                "Son Alim Sinyalleri",
                "Fatura, kalem ve tedarikci bilgisini ayni kartta oku.",
                dashboard.recent_entries.map((entry) => ({
                  title: `${entry.item_name} · ${entry.supplier}`,
                  meta: `${formatDate(entry.purchase_date)} · ${entry.quantity} adet${entry.invoice_no ? ` · Fatura ${entry.invoice_no}` : ""}${entry.notes ? ` · ${entry.notes}` : ""}`,
                  value: formatCurrency(entry.total_invoice_amount),
                })),
              )}
              {listCard(
                "Tedarikci Nabzi",
                "Son alislar icinde hangi tedarikci daha agirlikli ilerliyor bak.",
                supplierInsights,
              )}
              {listCard(
                "Birim Maliyet Sinyali",
                "Birim maliyeti yuksek kalemleri daha erken fark et.",
                unitCostSignals,
              )}
            </div>

            <PurchaseEntryWorkspace />
            <PurchaseManagementWorkspace />
          </>
        )}
      </section>
    </AppShell>
  );
}
