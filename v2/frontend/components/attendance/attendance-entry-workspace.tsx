"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type AttendanceFormOptions = {
  restaurants: Array<{
    id: number;
    label: string;
    pricing_model: string;
    pricing_model_label: string;
    hourly_rate: number;
    package_rate: number;
    package_threshold: number;
    package_rate_low: number;
    package_rate_high: number;
    fixed_monthly_fee: number;
    vat_rate: number;
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

type AttendanceEntryWorkspaceProps = {
  onDataChange?: () => void;
};

function formatCurrency(value: number) {
  return `${Number(value || 0).toLocaleString("tr-TR", {
    maximumFractionDigits: 0,
  })} TL`;
}

function calculateDraftInvoice(
  restaurant: AttendanceFormOptions["restaurants"][number] | null,
  workedHours: string,
  packageCount: string,
  explicitMonthlyAmount: string,
) {
  const explicitAmount = Number(explicitMonthlyAmount || 0);
  if (explicitAmount > 0) {
    return explicitAmount;
  }
  if (!restaurant) {
    return 0;
  }

  const hours = Number(workedHours || 0);
  const packages = Number(packageCount || 0);
  if (hours <= 0 && packages <= 0) {
    return 0;
  }

  if (restaurant.pricing_model === "hourly_plus_package") {
    return hours * restaurant.hourly_rate + packages * restaurant.package_rate;
  }
  if (restaurant.pricing_model === "threshold_package") {
    const packageRate =
      packages <= restaurant.package_threshold
        ? restaurant.package_rate_low
        : restaurant.package_rate_high;
    return hours * restaurant.hourly_rate + packages * packageRate;
  }
  if (restaurant.pricing_model === "hourly_only") {
    return hours * restaurant.hourly_rate;
  }
  if (restaurant.pricing_model === "fixed_monthly") {
    return restaurant.fixed_monthly_fee;
  }
  return 0;
}

export function AttendanceEntryWorkspace({ onDataChange }: AttendanceEntryWorkspaceProps) {
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
  const [personSearch, setPersonSearch] = useState("");
  const [absenceReason, setAbsenceReason] = useState("");
  const [workedHours, setWorkedHours] = useState("10");
  const [packageCount, setPackageCount] = useState("0");
  const [monthlyInvoiceAmount, setMonthlyInvoiceAmount] = useState("");
  const [notes, setNotes] = useState("");

  async function loadOptions(nextRestaurantId?: number | "") {
    setLoadingOptions(true);
    try {
      const params = new URLSearchParams();
      params.set("include_all_active", "true");
      if (typeof nextRestaurantId === "number") {
        params.set("restaurant_id", String(nextRestaurantId));
      }
      const query = params.size ? `?${params.toString()}` : "";
      const response = await apiFetch(`/attendance/form-options${query}`);
      if (!response.ok) {
        throw new Error("Puantaj seçenekleri alınamadı. Lütfen tekrar dene.");
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
          : "Puantaj seçenekleri alınamadı. Lütfen tekrar dene.",
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
  const draftInvoiceAmount = useMemo(
    () => calculateDraftInvoice(selectedRestaurant, workedHours, packageCount, monthlyInvoiceAmount),
    [selectedRestaurant, workedHours, packageCount, monthlyInvoiceAmount],
  );
  const people = options?.people ?? [];
  const filteredPeople = useMemo(() => {
    const normalizedSearch = personSearch.trim().toLocaleLowerCase("tr-TR");
    const matches = normalizedSearch
      ? people.filter((person) =>
          `${person.label} ${person.role}`.toLocaleLowerCase("tr-TR").includes(normalizedSearch),
        )
      : people;
    const selectedIds = new Set(
      [primaryPersonId, replacementPersonId].filter(
        (personId): personId is number => typeof personId === "number",
      ),
    );
    const pinnedPeople = people.filter(
      (person) => selectedIds.has(person.id) && !matches.some((match) => match.id === person.id),
    );
    return [...pinnedPeople, ...matches];
  }, [people, personSearch, primaryPersonId, replacementPersonId]);

  async function handleRestaurantChange(nextValue: string) {
    const nextRestaurantId = Number(nextValue);
    setRestaurantId(nextRestaurantId);
    setPrimaryPersonId("");
    setReplacementPersonId("");
    setSubmitError("");
    await loadOptions(nextRestaurantId);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    if (typeof restaurantId !== "number") {
      setSubmitError("Lütfen bir şube seç.");
      return;
    }

    const response = await apiFetch("/attendance/entries", {
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
      setSubmitError(payload?.detail || "Kayıt oluşturulamadı.");
      return;
    }

    setSubmitSuccess(payload?.message || "Puantaj kaydedildi.");
    onDataChange?.();
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
          Günlük Puantaj Girişi
        </h2>
        <p
          style={{
            margin: "6px 0 0",
            color: "var(--muted)",
            lineHeight: 1.7,
          }}
        >
          Şubeyi ve çalışanı seç; saat, paket ve durum kaydı aynı anda hakediş ve restoran
          faturası hesaplarına yansır.
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
          Puantaj seçenekleri yükleniyor...
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
              <span style={{ fontWeight: 700 }}>Şube</span>
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
              <span style={{ fontWeight: 700 }}>Vardiya Akışı</span>
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
              <span style={{ fontWeight: 700 }}>Personel Ara</span>
              <input
                type="search"
                value={personSearch}
                onChange={(event) => setPersonSearch(event.target.value)}
                placeholder="Ad, soyad veya rol ara"
                style={fieldStyle}
              />
            </label>
            <div
              style={{
                display: "grid",
                alignContent: "center",
                gap: "4px",
                padding: "12px 14px",
                borderRadius: "16px",
                border: "1px solid rgba(17, 125, 87, 0.16)",
                background: "rgba(17, 125, 87, 0.08)",
              }}
            >
              <span style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 800 }}>
                Aktif Personel
              </span>
              <strong style={{ fontSize: "1.05rem" }}>
                {filteredPeople.length}/{people.length} kişi
              </strong>
            </div>
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
                {needsReplacement ? "Normalde Girecek Personel" : "Çalışan Personel"}
              </span>
              <select
                value={primaryPersonId}
                onChange={(event) => setPrimaryPersonId(Number(event.target.value) || "")}
                style={fieldStyle}
              >
                <option value="">Seç</option>
                {filteredPeople.map((person) => (
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
                  <option value="">Seç</option>
                  {filteredPeople.map((person) => (
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
                  <option value="">Seç</option>
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
              <span style={{ fontWeight: 700 }}>Çalışılan Saat</span>
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
                <span style={{ fontWeight: 700 }}>Aylık Fatura Tutarı</span>
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
                display: "grid",
                gap: "12px",
                padding: "14px 16px",
                borderRadius: "18px",
                background: "rgba(15, 95, 215, 0.06)",
                color: "var(--muted)",
                lineHeight: 1.7,
              }}
            >
              <div>
                <strong style={{ color: "var(--text)" }}>{selectedRestaurant.label}</strong>
                {" "}
                seçili. Fiyat modeli:{" "}
                <strong style={{ color: "var(--text)" }}>
                  {selectedRestaurant.pricing_model_label}
                </strong>
                .
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                  gap: "10px",
                }}
              >
                {[
                  ["Saat", Number(workedHours || 0).toLocaleString("tr-TR")],
                  ["Paket", Number(packageCount || 0).toLocaleString("tr-TR")],
                  ["Tahmini Restoran Faturası", formatCurrency(draftInvoiceAmount)],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    style={{
                      display: "grid",
                      gap: "4px",
                      padding: "12px",
                      borderRadius: "14px",
                      background: "rgba(255, 255, 255, 0.72)",
                      border: "1px solid rgba(15, 95, 215, 0.10)",
                    }}
                  >
                    <span style={{ fontSize: "0.76rem", fontWeight: 800 }}>{label}</span>
                    <strong style={{ color: "var(--text)" }}>{value}</strong>
                  </div>
                ))}
              </div>
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
            {isPending ? "Kayıt yenileniyor..." : "Günlük Puantaj Kaydet"}
          </button>
        </form>
      )}
    </section>
  );
}

const fieldStyle: CSSProperties = {
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.9)",
  color: "var(--text)",
  padding: "12px 14px",
  font: "inherit",
};
