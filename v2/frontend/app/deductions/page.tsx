import { DeductionEntryWorkspace } from "../../components/deductions/deduction-entry-workspace";
import { DeductionManagementWorkspace } from "../../components/deductions/deduction-management-workspace";
import { AppShell } from "../../components/shell/app-shell";

type DeductionsDashboard = {
  module: string;
  status: string;
  summary: {
    total_entries: number;
    this_month_entries: number;
    manual_entries: number;
    auto_entries: number;
  };
  recent_entries: Array<{
    id: number;
    personnel_id: number;
    personnel_label: string;
    deduction_date: string;
    deduction_type: string;
    type_caption: string;
    amount: number;
    notes: string;
    auto_source_key: string;
    is_auto_record: boolean;
  }>;
};

function resolveApiBaseUrl() {
  const configuredBaseUrl =
    process.env.NEXT_PUBLIC_V2_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://127.0.0.1:8000";
  return configuredBaseUrl.endsWith("/api") ? configuredBaseUrl : `${configuredBaseUrl}/api`;
}

async function getDeductionsDashboard(): Promise<DeductionsDashboard | null> {
  const apiBaseUrl = resolveApiBaseUrl();
  try {
    const response = await fetch(`${apiBaseUrl}/deductions/dashboard?limit=12`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as DeductionsDashboard;
  } catch {
    return null;
  }
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

export default async function DeductionsPage() {
  const dashboard = await getDeductionsDashboard();

  return (
    <AppShell activeItem="Kesintiler">
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
            Deductions v2
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 3vw, 2.8rem)",
              lineHeight: 1.05,
            }}
          >
            Kesinti kayitlari icin parcali ve daha hizli operasyon akisi.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "74ch",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Bu slice ile manual deductions girisi ve kayit yonetimi Streamlit disina
            alinmaya basliyor. Amacimiz kesinti operasyonunu daha hizli ve daha stabil hale
            getirmek.
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
            Deductions API su anda erisilebilir degil. Backend ayaga kalktiginda bu ekran
            kesinti ozetini ve son kayitlari gercek veriden gosterecek.
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
              {metricCard("Toplam Kayit", String(dashboard.summary.total_entries), "accent")}
              {metricCard("Bu Ay", String(dashboard.summary.this_month_entries))}
              {metricCard("Manuel", String(dashboard.summary.manual_entries))}
              {metricCard("Otomatik", String(dashboard.summary.auto_entries))}
            </div>

            <DeductionEntryWorkspace />
            <DeductionManagementWorkspace />
          </>
        )}
      </section>
    </AppShell>
  );
}
