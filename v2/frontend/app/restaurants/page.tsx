import { RestaurantEntryWorkspace } from "../../components/restaurants/restaurant-entry-workspace";
import { RestaurantManagementWorkspace } from "../../components/restaurants/restaurant-management-workspace";
import { AppShell } from "../../components/shell/app-shell";

type RestaurantsDashboard = {
  module: string;
  status: string;
  summary: {
    total_restaurants: number;
    active_restaurants: number;
    passive_restaurants: number;
    fixed_monthly_restaurants: number;
  };
  recent_entries: Array<{
    id: number;
    brand: string;
    branch: string;
    pricing_model: string;
    pricing_model_label: string;
    hourly_rate: number;
    package_rate: number;
    package_threshold: number;
    package_rate_low: number;
    package_rate_high: number;
    fixed_monthly_fee: number;
    vat_rate: number;
    target_headcount: number;
    contact_name: string;
    active: boolean;
  }>;
};

function resolveApiBaseUrl() {
  const configuredBaseUrl =
    process.env.NEXT_PUBLIC_V2_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://127.0.0.1:8000";
  return configuredBaseUrl.endsWith("/api") ? configuredBaseUrl : `${configuredBaseUrl}/api`;
}

async function getRestaurantsDashboard(): Promise<RestaurantsDashboard | null> {
  const apiBaseUrl = resolveApiBaseUrl();
  try {
    const response = await fetch(`${apiBaseUrl}/restaurants/dashboard?limit=10`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as RestaurantsDashboard;
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

export default async function RestaurantsPage() {
  const dashboard = await getRestaurantsDashboard();

  return (
    <AppShell activeItem="Restoranlar">
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
            Restaurants v2
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 3vw, 2.8rem)",
              lineHeight: 1.05,
            }}
          >
            Sube kayitlarini daha hizli ve daha kararlı bir yonetim yuzeyine tasiyoruz.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "74ch",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Marka, fiyat modeli, kadro ve vergi bilgilerini tek akista yonet. Bu slice ile
            restoran operasyonu Streamlit disindaki ana yapiya gecmeye basliyor.
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
            Restaurant API su anda erisilebilir degil. Backend ayaga kalktiginda bu ekran
            restoran ozetini ve yonetim kayitlarini gercek veriden gosterecek.
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
              {metricCard("Toplam Sube", String(dashboard.summary.total_restaurants), "accent")}
              {metricCard("Aktif", String(dashboard.summary.active_restaurants))}
              {metricCard("Pasif", String(dashboard.summary.passive_restaurants))}
              {metricCard("Sabit Aylik", String(dashboard.summary.fixed_monthly_restaurants))}
            </div>

            <RestaurantEntryWorkspace />
            <RestaurantManagementWorkspace />
          </>
        )}
      </section>
    </AppShell>
  );
}
