import { AppShell } from "../../components/shell/app-shell";
import { AttendanceEntryWorkspace } from "../../components/attendance/attendance-entry-workspace";

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

function resolveApiBaseUrl() {
  const configuredBaseUrl =
    process.env.NEXT_PUBLIC_V2_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://127.0.0.1:8000";
  return configuredBaseUrl.endsWith("/api") ? configuredBaseUrl : `${configuredBaseUrl}/api`;
}

async function getAttendanceDashboard(): Promise<AttendanceDashboard | null> {
  const apiBaseUrl = resolveApiBaseUrl();
  try {
    const response = await fetch(`${apiBaseUrl}/attendance/dashboard?limit=14`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as AttendanceDashboard;
  } catch {
    return null;
  }
}

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

export default async function AttendancePage() {
  const dashboard = await getAttendanceDashboard();

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
            Attendance v2
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 3vw, 2.8rem)",
              lineHeight: 1.05,
            }}
          >
            Gunluk Puantaj icin hizli ve parcali ekran hazirligi.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "74ch",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Bu ilk v2 slice, attendance tarafinda tam sayfa rerun yerine parcali veri yukleme
            mantigina gecis icin summary ve son kayitlar panelini ayaga kaldiriyor.
          </p>
        </div>

        {!dashboard ? (
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
            Attendance API su anda erisilebilir degil. V2 backend ayaga kalktiginda bu ekran
            gunluk puantaj ozetini ve son kayitlari gercek veriden gosterecek.
          </div>
        ) : (
          <>
            <AttendanceEntryWorkspace />

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
                  Son Puantaj Kayitlari
                </h2>
                <p
                  style={{
                    margin: "6px 0 0",
                    color: "var(--muted)",
                  }}
                >
                  Attendance v2 ilk slice icin read-only operasyon panosu.
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
                      {["Tarih", "Sube", "Calisan", "Akis", "Saat", "Paket", "Not"].map((header) => (
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
                          borderTop: "1px solid rgba(222, 231, 244, 0.92)",
                        }}
                      >
                        <td style={{ padding: "14px 16px", fontWeight: 700 }}>{entry.entry_date}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.restaurant}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.employee_name}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.entry_mode}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.worked_hours}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.package_count}</td>
                        <td style={{ padding: "14px 16px", color: "var(--muted)" }}>
                          {entry.notes || "-"}
                        </td>
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
