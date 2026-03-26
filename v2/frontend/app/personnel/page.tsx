import { AppShell } from "../../components/shell/app-shell";
import { PersonnelEntryWorkspace } from "../../components/personnel/personnel-entry-workspace";
import { PersonnelManagementWorkspace } from "../../components/personnel/personnel-management-workspace";

type PersonnelDashboard = {
  module: string;
  status: string;
  summary: {
    total_personnel: number;
    active_personnel: number;
    passive_personnel: number;
    assigned_restaurants: number;
  };
  recent_entries: Array<{
    id: number;
    person_code: string;
    full_name: string;
    role: string;
    status: string;
    phone: string;
    restaurant_id: number | null;
    restaurant_label: string;
    vehicle_mode: string;
    current_plate: string;
    start_date: string | null;
    monthly_fixed_cost: number;
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

async function getPersonnelDashboard(): Promise<PersonnelDashboard | null> {
  try {
    const response = await fetch(`${resolveApiBaseUrl()}/personnel/dashboard?limit=12`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as PersonnelDashboard;
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

export default async function PersonnelPage() {
  const dashboard = await getPersonnelDashboard();

  return (
    <AppShell activeItem="Personel">
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
            Personnel v2
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 3vw, 2.8rem)",
              lineHeight: 1.05,
            }}
          >
            Personel kayitlarini parcali veri akisi ve daha kontrollu yonetim kartlariyla tasiyoruz.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "74ch",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Attendance sonrasinda ikinci gercek v2 dikey dilim personel oldu. Burada amac, Streamlit
            rerun yerine liste, form ve detay akisini birbirinden ayirmak.
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
            Personnel API su anda erisilebilir degil. V2 backend ayaga kalktiginda burada personel
            ozeti ve son kayitlar gercek veriden calisacak.
          </div>
        ) : (
          <>
            <PersonnelEntryWorkspace />
            <PersonnelManagementWorkspace />

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "14px",
              }}
            >
              {metricCard("Toplam Personel", String(dashboard.summary.total_personnel))}
              {metricCard("Aktif", String(dashboard.summary.active_personnel))}
              {metricCard("Pasif", String(dashboard.summary.passive_personnel))}
              {metricCard("Atanmis Sube", String(dashboard.summary.assigned_restaurants))}
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
                <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Son Personel Kayitlari</h2>
                <p style={{ margin: "6px 0 0", color: "var(--muted)" }}>
                  Personel slice icin read-only hizli ozet panosu.
                </p>
              </div>
              <div style={{ overflowX: "auto" }}>
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
                      {["Kod", "Ad Soyad", "Rol", "Durum", "Sube", "Arac", "Telefon"].map((header) => (
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
                        <td style={{ padding: "14px 16px", fontWeight: 700 }}>{entry.person_code}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.full_name}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.role}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.status}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.restaurant_label}</td>
                        <td style={{ padding: "14px 16px" }}>{entry.vehicle_mode}</td>
                        <td style={{ padding: "14px 16px", color: "var(--muted)" }}>{entry.phone || "-"}</td>
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
