"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type AttendanceFormOptions = {
  restaurants: Array<{
    id: number;
    label: string;
    pricing_model: string;
    fixed_monthly_fee: number;
  }>;
  people: Array<{
    id: number;
    label: string;
    role: string;
  }>;
  entry_modes: string[];
  absence_reasons: string[];
  selected_restaurant_id: number | null;
  selected_pricing_model: string | null;
  selected_fixed_monthly_fee: number;
};

function resolveApiBaseUrl() {
  const configuredBaseUrl =
    process.env.NEXT_PUBLIC_V2_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://127.0.0.1:8000";
  return configuredBaseUrl.endsWith("/api") ? configuredBaseUrl : `${configuredBaseUrl}/api`;
}

export function AttendanceEntryWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<AttendanceFormOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [entryDate, setEntryDate] = useState(new Date().toISOString().slice(0, 10));
  const [restaurantId, setRestaurantId] = useState<number | "">("");
  const [entryMode, setEntryMode] = useState("Restoran Kuryesi");
  const [primaryPersonId, setPrimaryPersonId] = useState<number | "">("");
  const [replacementPersonId, setReplacementPersonId] = useState<number | "">("");
  const [absenceReason, setAbsenceReason] = useState("");
  const [workedHours, setWorkedHours] = useState("10");
  const [packageCount, setPackageCount] = useState("0");
  const [monthlyInvoiceAmount, setMonthlyInvoiceAmount] = useState("");
  const [notes, setNotes] = useState("");

  async function loadOptions(nextRestaurantId?: number | "") {
    setLoadingOptions(true);
    try {
      const apiBaseUrl = resolveApiBaseUrl();
      const query =
        typeof nextRestaurantId === "number"
          ? `?restaurant_id=${encodeURIComponent(String(nextRestaurantId))}`
          : "";
      const response = await fetch(`${apiBaseUrl}/attendance/form-options${query}`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("Attendance form options could not be loaded.");
      }
      const payload = (await response.json()) as AttendanceFormOptions;
      setOptions(payload);
      const selectedRestaurantId = payload.selected_restaurant_id ?? "";
      setRestaurantId(selectedRestaurantId);
      if (payload.selected_pricing_model === "fixed_monthly" && !monthlyInvoiceAmount) {
        setMonthlyInvoiceAmount(
          payload.selected_fixed_monthly_fee ? String(payload.selected_fixed_monthly_fee) : "",
        );
      }
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : "Attendance form options could not be loaded.",
      );
    } finally {
      setLoadingOptions(false);
    }
  }

  useEffect(() => {
    void loadOptions();
  }, []);

  const selectedRestaurant = useMemo(() => {
    if (!options || typeof restaurantId !== "number") {
      return null;
    }
    return options.restaurants.find((item) => item.id === restaurantId) ?? null;
  }, [options, restaurantId]);

  const isFixedMonthly = selectedRestaurant?.pricing_model === "fixed_monthly";
  const needsReplacement = entryMode === "Joker" || entryMode === "Destek";
  const needsAbsenceReason = entryMode !== "Restoran Kuryesi";

  async function handleRestaurantChange(nextValue: string) {
    const nextRestaurantId = Number(nextValue);
    setRestaurantId(nextRestaurantId);
    setPrimaryPersonId("");
    setReplacementPersonId("");
    setSubmitError("");
    await loadOptions(nextRestaurantId);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    if (typeof restaurantId !== "number") {
      setSubmitError("Lutfen bir sube sec.");
      return;
    }

    const apiBaseUrl = resolveApiBaseUrl();
    const response = await fetch(`${apiBaseUrl}/attendance/entries`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        entry_date: entryDate,
        restaurant_id: restaurantId,
        entry_mode: entryMode,
        primary_person_id: typeof primaryPersonId === "number" ? primaryPersonId : null,
        replacement_person_id:
          typeof replacementPersonId === "number" ? replacementPersonId : null,
        absence_reason: absenceReason,
        worked_hours: Number(workedHours || 0),
        package_count: Number(packageCount || 0),
        monthly_invoice_amount: Number(monthlyInvoiceAmount || 0),
        notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;

    if (!response.ok) {
      setSubmitError(payload?.detail || "Kayit olusturulamadi.");
      return;
    }

    setSubmitSuccess(payload?.message || "Kayit olusturuldu.");
    setEntryMode("Restoran Kuryesi");
    setPrimaryPersonId("");
    setReplacementPersonId("");
    setAbsenceReason("");
    setWorkedHours("10");
    setPackageCount("0");
    setNotes("");
    if (isFixedMonthly) {
      setMonthlyInvoiceAmount(
        selectedRestaurant?.fixed_monthly_fee ? String(selectedRestaurant.fixed_monthly_fee) : "",
      );
    } else {
      setMonthlyInvoiceAmount("");
    }
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
        <h2
          style={{
            margin: 0,
            fontSize: "1.2rem",
          }}
        >
          Gunluk Puantaj Girisi
        </h2>
        <p
          style={{
            margin: "6px 0 0",
            color: "var(--muted)",
            lineHeight: 1.7,
          }}
        >
          Bu ilk yazilabilir v2 formu, sube ve personel secimini gercek attendance API ile
          baglar.
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
          Attendance form secenekleri yukleniyor...
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
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "14px",
            }}
          >
            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Tarih</span>
              <input
                type="date"
                value={entryDate}
                onChange={(event) => setEntryDate(event.target.value)}
                style={fieldStyle}
              />
            </label>

            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Sube</span>
              <select
                value={restaurantId}
                onChange={(event) => {
                  void handleRestaurantChange(event.target.value);
                }}
                style={fieldStyle}
              >
                {options?.restaurants.map((restaurant) => (
                  <option key={restaurant.id} value={restaurant.id}>
                    {restaurant.label}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Vardiya Akisi</span>
              <select
                value={entryMode}
                onChange={(event) => setEntryMode(event.target.value)}
                style={fieldStyle}
              >
                {options?.entry_modes.map((mode) => (
                  <option key={mode} value={mode}>
                    {mode}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "14px",
            }}
          >
            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>
                {needsReplacement ? "Normalde Girecek Personel" : "Calisan Personel"}
              </span>
              <select
                value={primaryPersonId}
                onChange={(event) => setPrimaryPersonId(Number(event.target.value) || "")}
                style={fieldStyle}
              >
                <option value="">Sec</option>
                {options?.people.map((person) => (
                  <option key={person.id} value={person.id}>
                    {person.label}
                  </option>
                ))}
              </select>
            </label>

            {needsReplacement ? (
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Yerine Giren Personel</span>
                <select
                  value={replacementPersonId}
                  onChange={(event) => setReplacementPersonId(Number(event.target.value) || "")}
                  style={fieldStyle}
                >
                  <option value="">Sec</option>
                  {options?.people.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            {needsAbsenceReason ? (
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Neden Girmedi</span>
                <select
                  value={absenceReason}
                  onChange={(event) => setAbsenceReason(event.target.value)}
                  style={fieldStyle}
                >
                  <option value="">Sec</option>
                  {options?.absence_reasons.map((reason) => (
                    <option key={reason} value={reason}>
                      {reason}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "14px",
            }}
          >
            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Calisilan Saat</span>
              <input
                type="number"
                step="0.5"
                min="0"
                value={workedHours}
                onChange={(event) => setWorkedHours(event.target.value)}
                style={fieldStyle}
              />
            </label>

            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Paket</span>
              <input
                type="number"
                step="1"
                min="0"
                value={packageCount}
                onChange={(event) => setPackageCount(event.target.value)}
                style={fieldStyle}
              />
            </label>

            {isFixedMonthly ? (
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Aylik Fatura Tutari</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={monthlyInvoiceAmount}
                  onChange={(event) => setMonthlyInvoiceAmount(event.target.value)}
                  style={fieldStyle}
                />
              </label>
            ) : null}
          </div>

          <label style={{ display: "grid", gap: "8px" }}>
            <span style={{ fontWeight: 700 }}>Not</span>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
              style={{
                ...fieldStyle,
                resize: "vertical",
                minHeight: "96px",
              }}
            />
          </label>

          {selectedRestaurant ? (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "18px",
                background: "rgba(15, 95, 215, 0.06)",
                color: "var(--muted)",
                lineHeight: 1.7,
              }}
            >
              <strong style={{ color: "var(--text)" }}>{selectedRestaurant.label}</strong>
              {" "}
              secili.
              {isFixedMonthly ? (
                <>
                  {" "}
                  Bu sube sabit aylik ucret modeliyle calisiyor. Kayit icin varsayilan sabit
                  rakam:{" "}
                  <strong style={{ color: "var(--text)" }}>
                    {selectedRestaurant.fixed_monthly_fee.toLocaleString("tr-TR")} TL
                  </strong>
                  .
                </>
              ) : null}
            </div>
          ) : null}

          {submitError ? (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "16px",
                background: "rgba(196, 53, 53, 0.08)",
                color: "#9e2430",
              }}
            >
              {submitError}
            </div>
          ) : null}

          {submitSuccess ? (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "16px",
                background: "rgba(17, 125, 87, 0.10)",
                color: "#0c6b4b",
              }}
            >
              {submitSuccess}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isPending || loadingOptions}
            style={{
              border: 0,
              borderRadius: "18px",
              padding: "15px 18px",
              fontWeight: 900,
              fontSize: "1rem",
              background: "var(--accent)",
              color: "#fff",
              cursor: "pointer",
              opacity: isPending ? 0.72 : 1,
            }}
          >
            {isPending ? "Kayit yenileniyor..." : "Gunluk Puantaj Kaydet"}
          </button>
        </form>
      )}
    </section>
  );
}

const fieldStyle: React.CSSProperties = {
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.9)",
  color: "var(--text)",
  padding: "12px 14px",
  font: "inherit",
};
