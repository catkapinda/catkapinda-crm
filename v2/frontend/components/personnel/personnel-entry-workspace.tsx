"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type PersonnelFormOptions = {
  restaurants: Array<{
    id: number;
    label: string;
  }>;
  role_options: string[];
  status_options: string[];
  vehicle_mode_options: string[];
  selected_restaurant_id: number | null;
};

const fieldStyle: CSSProperties = {
  width: "100%",
  padding: "13px 14px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.9)",
  color: "var(--text)",
  font: "inherit",
};

export function PersonnelEntryWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<PersonnelFormOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [generatedCode, setGeneratedCode] = useState("");

  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("Kurye");
  const [phone, setPhone] = useState("");
  const [restaurantId, setRestaurantId] = useState<number | "">("");
  const [status, setStatus] = useState("Aktif");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [vehicleMode, setVehicleMode] = useState("Kendi Motoru");
  const [currentPlate, setCurrentPlate] = useState("");
  const [monthlyFixedCost, setMonthlyFixedCost] = useState("0");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    async function loadOptions() {
      setLoadingOptions(true);
      try {
        const response = await apiFetch("/personnel/form-options");
        if (!response.ok) {
          throw new Error("Personel form secenekleri yuklenemedi.");
        }
        const payload = (await response.json()) as PersonnelFormOptions;
        setOptions(payload);
        setRole(payload.role_options[0] ?? "Kurye");
        setStatus(payload.status_options[0] ?? "Aktif");
        setVehicleMode(payload.vehicle_mode_options[0] ?? "Kendi Motoru");
        setRestaurantId(payload.selected_restaurant_id ?? "");
      } catch (error) {
        setSubmitError(
          error instanceof Error ? error.message : "Personel form secenekleri yuklenemedi.",
        );
      } finally {
        setLoadingOptions(false);
      }
    }

    void loadOptions();
  }, []);

  const selectedRestaurantLabel = useMemo(() => {
    if (!options || typeof restaurantId !== "number") {
      return "Atanmadi";
    }
    return options.restaurants.find((restaurant) => restaurant.id === restaurantId)?.label ?? "Atanmadi";
  }, [options, restaurantId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");
    setGeneratedCode("");

    if (!fullName.trim()) {
      setSubmitError("Ad soyad zorunlu.");
      return;
    }

    const response = await apiFetch("/personnel/records", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        full_name: fullName,
        role,
        phone,
        assigned_restaurant_id: typeof restaurantId === "number" ? restaurantId : null,
        status,
        start_date: startDate || null,
        vehicle_mode: vehicleMode,
        current_plate: currentPlate,
        monthly_fixed_cost: Number(monthlyFixedCost || 0),
        notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string; person_code?: string }
      | null;

    if (!response.ok) {
      setSubmitError(payload?.detail || "Personel kaydi olusturulamadi.");
      return;
    }

    setSubmitSuccess(payload?.message || "Personel kaydi olusturuldu.");
    setGeneratedCode(payload?.person_code || "");
    setFullName("");
    setPhone("");
    setCurrentPlate("");
    setMonthlyFixedCost("0");
    setNotes("");
    startTransition(() => {
      router.refresh();
    });
  }

  return (
    <section
      style={{
        display: "grid",
        gap: "16px",
        padding: "22px",
        borderRadius: "24px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
      }}
    >
      <div>
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Personel Kaydi</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Kimlik, rol ve sube atamasini attendance v2 ile ayni hizda parcali ekran mantigina
          tasiyan ilk personel slice.
        </p>
      </div>

      {loadingOptions ? (
        <div
          style={{
            padding: "18px",
            borderRadius: "18px",
            background: "rgba(15, 95, 215, 0.06)",
            color: "var(--muted)",
          }}
        >
          Personel form secenekleri yukleniyor...
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          style={{
            display: "grid",
            gap: "16px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.5fr) minmax(280px, 360px)",
              gap: "16px",
              alignItems: "start",
            }}
          >
            <div
              style={{
                display: "grid",
                gap: "14px",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Ad Soyad</span>
                  <input value={fullName} onChange={(event) => setFullName(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Rol</span>
                  <select value={role} onChange={(event) => setRole(event.target.value)} style={fieldStyle}>
                    {options?.role_options.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Telefon</span>
                  <input value={phone} onChange={(event) => setPhone(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Durum</span>
                  <select value={status} onChange={(event) => setStatus(event.target.value)} style={fieldStyle}>
                    {options?.status_options.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Restoran / Sube</span>
                  <select
                    value={restaurantId}
                    onChange={(event) =>
                      setRestaurantId(event.target.value ? Number(event.target.value) : "")
                    }
                    style={fieldStyle}
                  >
                    <option value="">Atanmadi</option>
                    {options?.restaurants.map((restaurant) => (
                      <option key={restaurant.id} value={restaurant.id}>
                        {restaurant.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Ise Giris</span>
                  <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Arac Modu</span>
                  <select value={vehicleMode} onChange={(event) => setVehicleMode(event.target.value)} style={fieldStyle}>
                    {options?.vehicle_mode_options.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Plaka</span>
                  <input value={currentPlate} onChange={(event) => setCurrentPlate(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Aylik Sabit Tutar</span>
                  <input
                    inputMode="decimal"
                    value={monthlyFixedCost}
                    onChange={(event) => setMonthlyFixedCost(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
              </div>

              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Not</span>
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  rows={3}
                  style={{ ...fieldStyle, resize: "vertical", minHeight: "96px" }}
                />
              </label>

              <button
                type="submit"
                disabled={isPending}
                style={{
                  padding: "14px 18px",
                  borderRadius: "16px",
                  border: "none",
                  background: "var(--accent)",
                  color: "#fff",
                  fontWeight: 800,
                  fontSize: "0.96rem",
                  cursor: "pointer",
                }}
              >
                {isPending ? "Kaydediliyor..." : "Personel Kaydini Olustur"}
              </button>
            </div>

            <aside
              style={{
                display: "grid",
                gap: "12px",
                padding: "16px",
                borderRadius: "20px",
                border: "1px solid var(--line)",
                background: "rgba(244, 248, 255, 0.9)",
              }}
            >
              <h3 style={{ margin: 0, fontSize: "1rem" }}>Kayit Ozeti</h3>
              <SummaryItem label="Rol" value={role} />
              <SummaryItem label="Sube" value={selectedRestaurantLabel} />
              <SummaryItem label="Arac" value={vehicleMode} />
              <SummaryItem label="Durum" value={status} />
              <SummaryItem
                label="Sabit Tutar"
                value={Number(monthlyFixedCost || 0).toLocaleString("tr-TR", {
                  style: "currency",
                  currency: "TRY",
                  maximumFractionDigits: 0,
                })}
              />
              {generatedCode ? <SummaryItem label="Olusan Kod" value={generatedCode} /> : null}
            </aside>
          </div>

          {submitError ? <InlineMessage tone="error" message={submitError} /> : null}
          {submitSuccess ? <InlineMessage tone="success" message={submitSuccess} /> : null}
        </form>
      )}
    </section>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "grid",
        gap: "4px",
        padding: "12px 14px",
        borderRadius: "16px",
        border: "1px solid rgba(193, 209, 232, 0.9)",
        background: "#fff",
      }}
    >
      <span
        style={{
          color: "var(--muted)",
          fontSize: "0.78rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 800,
        }}
      >
        {label}
      </span>
      <span style={{ fontWeight: 800 }}>{value || "-"}</span>
    </div>
  );
}

function InlineMessage({ tone, message }: { tone: "error" | "success"; message: string }) {
  const palette =
    tone === "error"
      ? {
          background: "rgba(222, 66, 66, 0.09)",
          border: "1px solid rgba(222, 66, 66, 0.18)",
          color: "#b53a3a",
        }
      : {
          background: "rgba(38, 167, 107, 0.1)",
          border: "1px solid rgba(38, 167, 107, 0.16)",
          color: "#167f51",
        };
  return (
    <div
      style={{
        padding: "14px 16px",
        borderRadius: "16px",
        ...palette,
      }}
    >
      {message}
    </div>
  );
}
