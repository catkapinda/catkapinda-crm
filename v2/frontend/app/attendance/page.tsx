"use client";

import { useEffect, useState } from "react";

import { AttendanceEntryWorkspace } from "../../components/attendance/attendance-entry-workspace";
import { AttendanceManagementWorkspace } from "../../components/attendance/attendance-management-workspace";
import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type AttendanceDashboard = {
  module: string;
  status: string;
  summary: {
    total_entries: number;
    today_entries: number;
    month_entries: number;
    active_restaurants: number;
  };
  recent_entries: Array<{
    id: number;
    entry_date: string;
    restaurant: string;
    employee_name: string;
    entry_mode: string;
    absence_reason: string;
    coverage_type: string;
    worked_hours: number;
    package_count: number;
    monthly_invoice_amount: number;
    notes: string;
  }>;
};

function metricCard(label: string, value: string) {
  return (
    <article
      key={label}
      style={{
        padding: "18px",
        borderRadius: "20px",
        border: "1px solid var(--line)",
        background: "var(--surface)",
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

export default function AttendancePage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<AttendanceDashboard | null>(null);
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
        const response = await apiFetch("/attendance/dashboard?limit=14");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as AttendanceDashboard;
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
    <AppShell activeItem="Puantaj">
      <section
        style={{
          display: "grid",
          gap: "18px",
        }}
      >
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
            Operasyon Akisi
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 3vw, 2.8rem)",
              lineHeight: 1.05,
            }}
          >
            Gunluk puantaj yeni hatta hazir.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "74ch",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Gunluk puantaj girisi, kayit yonetimi ve son hareketler artik daha akici bir yapida
            tek ekranda ilerliyor. Bu alan pilot acildiginda ofisin Streamlit'e donmeden kullanacagi
            ana operasyon yuzlerinden biri olacak.
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
            Gunluk puantaj verileri yukleniyor...
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
            Puantaj servisine su anda erisilemiyor. Pilot backend ayaga kalktiginda bu ekran
            gunluk puantaj ozetini ve son hareketleri gercek veriden gosterecek.
          </div>
        ) : (
          <>
            <AttendanceEntryWorkspace />
            <AttendanceManagementWorkspace />

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "14px",
              }}
            >
              {metricCard("Toplam Kayit", String(dashboard.summary.total_entries))}
              {metricCard("Bugun", String(dashboard.summary.today_entries))}
              {metricCard("Bu Ay", String(dashboard.summary.month_entries))}
              {metricCard("Aktif Sube", String(dashboard.summary.active_restaurants))}
            </div>

            <div
              style={{
                borderRadius: "24px",
                border: "1px solid var(--line)",
                background: "var(--surface-strong)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "18px 20px",
                  borderBottom: "1px solid var(--line)",
                }}
              >
                <h2
                  style={{
                    margin: 0,
                    fontSize: "1.1rem",
                  }}
                >
                  Son Puantaj Hareketleri
                </h2>
                <p
                  style={{
                    margin: "6px 0 0",
                    color: "var(--muted)",
                  }}
                >
                  Son girilen kayitlari, sube ve calisan akisini tek bakista kontrol et.
                </p>
              </div>

              <div
                style={{
                  overflowX: "auto",
                }}
              >
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                  }}
                >
                  <thead>
                    <tr
                      style={{
                        textAlign: "left",
                        background: "rgba(236, 243, 252, 0.86)",
                      }}
                    >
                      {["Tarih", "Sube", "Calisan", "Akis", "Saat", "Paket"].map((header) => (
                        <th
                          key={header}
                          style={{
                            padding: "14px 16px",
                            fontSize: "0.84rem",
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                            color: "var(--muted)",
                          }}
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.recent_entries.map((entry) => (
                      <tr
                        key={entry.id}
                        style={{
                          borderTop: "1px solid rgba(193, 209, 232, 0.56)",
                        }}
                      >
                        <td style={tableCellStyle}>{entry.entry_date}</td>
                        <td style={tableCellStyle}>{entry.restaurant}</td>
                        <td style={tableCellStyle}>{entry.employee_name || "-"}</td>
                        <td style={tableCellStyle}>{entry.entry_mode}</td>
                        <td style={tableCellStyle}>{entry.worked_hours.toFixed(1)}</td>
                        <td style={tableCellStyle}>{entry.package_count.toFixed(0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </section>
    </AppShell>
  );
}

const tableCellStyle = {
  padding: "14px 16px",
  fontSize: "0.95rem",
  color: "var(--text)",
};
