"use client";

import type { CSSProperties, FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type AttendanceEntry = {
  id: number;
  entry_date: string;
  restaurant_id: number;
  restaurant: string;
  entry_mode: string;
  primary_person_id: number | null;
  primary_person_label: string;
  replacement_person_id: number | null;
  replacement_person_label: string;
  absence_reason: string;
  coverage_type: string;
  worked_hours: number;
  package_count: number;
  monthly_invoice_amount: number;
  notes: string;
};

type AttendanceManagementResponse = {
  total_entries: number;
  entries: AttendanceEntry[];
};

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

type AttendanceEntryDetailResponse = {
  entry: AttendanceEntry;
};

function resolveApiBaseUrl() {
  const configuredBaseUrl =
    process.env.NEXT_PUBLIC_V2_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://127.0.0.1:8000";
  return configuredBaseUrl.endsWith("/api") ? configuredBaseUrl : `${configuredBaseUrl}/api`;
}

function badgeStyle(kind: "accent" | "soft" | "warn" | "muted"): CSSProperties {
  const palette = {
    accent: {
      background: "rgba(15, 95, 215, 0.12)",
      color: "#0f5fd7",
      border: "1px solid rgba(15, 95, 215, 0.18)",
    },
    soft: {
      background: "rgba(20, 39, 67, 0.06)",
      color: "#28476e",
      border: "1px solid rgba(20, 39, 67, 0.08)",
    },
    warn: {
      background: "rgba(230, 140, 55, 0.12)",
      color: "#b96a18",
      border: "1px solid rgba(230, 140, 55, 0.16)",
    },
    muted: {
      background: "rgba(95, 118, 152, 0.1)",
      color: "#5f7698",
      border: "1px solid rgba(95, 118, 152, 0.12)",
    },
  }[kind];
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 10px",
    borderRadius: "999px",
    fontSize: "0.78rem",
    fontWeight: 800,
    ...palette,
  };
}

function formatHours(value: number) {
  return `${value.toFixed(1)} sa`;
}

function formatPackages(value: number) {
  return `${value.toFixed(0)} pkg`;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

export function AttendanceManagementWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const [restaurants, setRestaurants] = useState<AttendanceFormOptions["restaurants"]>([]);
  const [entryModes, setEntryModes] = useState<string[]>([]);
  const [absenceReasons, setAbsenceReasons] = useState<string[]>([]);
  const [editorPeople, setEditorPeople] = useState<AttendanceFormOptions["people"]>([]);

  const [searchInput, setSearchInput] = useState("");
  const deferredSearch = useDeferredValue(searchInput);
  const [filterRestaurantId, setFilterRestaurantId] = useState<number | "">("");

  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [entries, setEntries] = useState<AttendanceEntry[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");

  const [editDate, setEditDate] = useState("");
  const [editRestaurantId, setEditRestaurantId] = useState<number | "">("");
  const [editEntryMode, setEditEntryMode] = useState("Restoran Kuryesi");
  const [editPrimaryPersonId, setEditPrimaryPersonId] = useState<number | "">("");
  const [editReplacementPersonId, setEditReplacementPersonId] = useState<number | "">("");
  const [editAbsenceReason, setEditAbsenceReason] = useState("");
  const [editWorkedHours, setEditWorkedHours] = useState("0");
  const [editPackageCount, setEditPackageCount] = useState("0");
  const [editMonthlyInvoiceAmount, setEditMonthlyInvoiceAmount] = useState("");
  const [editNotes, setEditNotes] = useState("");

  const apiBaseUrl = resolveApiBaseUrl();

  const selectedRestaurant = useMemo(() => {
    if (typeof editRestaurantId !== "number") {
      return null;
    }
    return restaurants.find((restaurant) => restaurant.id === editRestaurantId) ?? null;
  }, [editRestaurantId, restaurants]);

  const isFixedMonthly = selectedRestaurant?.pricing_model === "fixed_monthly";
  const needsReplacement = editEntryMode === "Joker" || editEntryMode === "Destek";
  const needsAbsenceReason = editEntryMode !== "Restoran Kuryesi";

  async function loadReferenceOptions() {
    const response = await fetch(`${apiBaseUrl}/attendance/form-options`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error("Puantaj referans verileri yuklenemedi.");
    }
    const payload = (await response.json()) as AttendanceFormOptions;
    setRestaurants(payload.restaurants);
    setEntryModes(payload.entry_modes);
    setAbsenceReasons(payload.absence_reasons);
  }

  async function loadEntries() {
    setListLoading(true);
    setListError("");
    try {
      const query = new URLSearchParams();
      query.set("limit", "160");
      if (typeof filterRestaurantId === "number") {
        query.set("restaurant_id", String(filterRestaurantId));
      }
      if (deferredSearch.trim()) {
        query.set("search", deferredSearch.trim());
      }
      const response = await fetch(`${apiBaseUrl}/attendance/entries?${query.toString()}`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("Puantaj kayitlari yuklenemedi.");
      }
      const payload = (await response.json()) as AttendanceManagementResponse;
      setEntries(payload.entries);
      setTotalEntries(payload.total_entries);
      setSelectedEntryId((current) => {
        if (!payload.entries.length) {
          return null;
        }
        if (current && payload.entries.some((entry) => entry.id === current)) {
          return current;
        }
        return payload.entries[0].id;
      });
    } catch (error) {
      setListError(error instanceof Error ? error.message : "Puantaj kayitlari yuklenemedi.");
      setEntries([]);
      setTotalEntries(0);
      setSelectedEntryId(null);
    } finally {
      setListLoading(false);
    }
  }

  async function loadPeopleOptions(restaurantId: number) {
    const response = await fetch(
      `${apiBaseUrl}/attendance/form-options?restaurant_id=${encodeURIComponent(String(restaurantId))}`,
      {
        cache: "no-store",
      },
    );
    if (!response.ok) {
      throw new Error("Personel secenekleri yuklenemedi.");
    }
    const payload = (await response.json()) as AttendanceFormOptions;
    setEditorPeople(payload.people);
  }

  async function loadEntryDetail(entryId: number) {
    setDetailLoading(true);
    setDetailError("");
    setSaveError("");
    setSaveSuccess("");
    try {
      const response = await fetch(`${apiBaseUrl}/attendance/entries/${entryId}`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("Kayit detayi yuklenemedi.");
      }
      const payload = (await response.json()) as AttendanceEntryDetailResponse;
      const entry = payload.entry;
      setEditDate(entry.entry_date);
      setEditRestaurantId(entry.restaurant_id);
      setEditEntryMode(entry.entry_mode);
      setEditPrimaryPersonId(entry.primary_person_id ?? "");
      setEditReplacementPersonId(entry.replacement_person_id ?? "");
      setEditAbsenceReason(entry.absence_reason ?? "");
      setEditWorkedHours(String(entry.worked_hours ?? 0));
      setEditPackageCount(String(entry.package_count ?? 0));
      setEditMonthlyInvoiceAmount(
        entry.monthly_invoice_amount ? String(entry.monthly_invoice_amount) : "",
      );
      setEditNotes(entry.notes ?? "");
      await loadPeopleOptions(entry.restaurant_id);
    } catch (error) {
      setDetailError(error instanceof Error ? error.message : "Kayit detayi yuklenemedi.");
      setEditorPeople([]);
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    void loadReferenceOptions().catch((error) => {
      setListError(
        error instanceof Error ? error.message : "Puantaj referans verileri yuklenemedi.",
      );
    });
  }, []);

  useEffect(() => {
    void loadEntries();
  }, [filterRestaurantId, deferredSearch]);

  useEffect(() => {
    if (selectedEntryId) {
      void loadEntryDetail(selectedEntryId);
    }
  }, [selectedEntryId]);

  async function handleEditorRestaurantChange(nextValue: string) {
    const nextRestaurantId = Number(nextValue);
    setEditRestaurantId(nextRestaurantId);
    setEditPrimaryPersonId("");
    setEditReplacementPersonId("");
    setSaveError("");
    await loadPeopleOptions(nextRestaurantId);
    const matchedRestaurant =
      restaurants.find((restaurant) => restaurant.id === nextRestaurantId) ?? null;
    if (matchedRestaurant?.pricing_model === "fixed_monthly") {
      setEditMonthlyInvoiceAmount(
        matchedRestaurant.fixed_monthly_fee ? String(matchedRestaurant.fixed_monthly_fee) : "",
      );
    } else {
      setEditMonthlyInvoiceAmount("");
    }
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEntryId) {
      return;
    }
    if (typeof editRestaurantId !== "number") {
      setSaveError("Lutfen bir sube sec.");
      return;
    }

    setSaveError("");
    setSaveSuccess("");

    const response = await fetch(`${apiBaseUrl}/attendance/entries/${selectedEntryId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        entry_date: editDate,
        restaurant_id: editRestaurantId,
        entry_mode: editEntryMode,
        primary_person_id: typeof editPrimaryPersonId === "number" ? editPrimaryPersonId : null,
        replacement_person_id:
          typeof editReplacementPersonId === "number" ? editReplacementPersonId : null,
        absence_reason: editAbsenceReason,
        worked_hours: Number(editWorkedHours || 0),
        package_count: Number(editPackageCount || 0),
        monthly_invoice_amount: Number(editMonthlyInvoiceAmount || 0),
        notes: editNotes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;

    if (!response.ok) {
      setSaveError(payload?.detail || "Kayit guncellenemedi.");
      return;
    }

    setSaveSuccess(payload?.message || "Kayit guncellendi.");
    await loadEntries();
    await loadEntryDetail(selectedEntryId);
    startTransition(() => {
      router.refresh();
    });
  }

  async function handleDelete() {
    if (!selectedEntryId) {
      return;
    }

    const shouldDelete = window.confirm("Bu puantaj kaydi silinsin mi?");
    if (!shouldDelete) {
      return;
    }

    setSaveError("");
    setSaveSuccess("");

    const response = await fetch(`${apiBaseUrl}/attendance/entries/${selectedEntryId}`, {
      method: "DELETE",
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;

    if (!response.ok) {
      setSaveError(payload?.detail || "Kayit silinemedi.");
      return;
    }

    setSaveSuccess(payload?.message || "Kayit silindi.");
    await loadEntries();
    startTransition(() => {
      router.refresh();
    });
  }

  const summary = useMemo(() => {
    const totalHours = entries.reduce((sum, entry) => sum + Number(entry.worked_hours || 0), 0);
    const totalPackages = entries.reduce((sum, entry) => sum + Number(entry.package_count || 0), 0);
    return {
      visibleEntries: entries.length,
      totalHours,
      totalPackages,
    };
  }, [entries]);

  return (
    <section
      style={{
        display: "grid",
        gap: "18px",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "12px",
        }}
      >
        <MetricCard label="Toplam Kayit" value={String(totalEntries)} hint="Tum filtreler disi genel sayi" />
        <MetricCard
          label="Gorunen Kayit"
          value={String(summary.visibleEntries)}
          hint="Bu listede ekranda gorulen satirlar"
        />
        <MetricCard label="Toplam Saat" value={formatHours(summary.totalHours)} hint="Filtrelenmis toplam" />
        <MetricCard
          label="Toplam Paket"
          value={formatPackages(summary.totalPackages)}
          hint="Filtrelenmis toplam"
        />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.2fr) minmax(340px, 0.9fr)",
          gap: "18px",
          alignItems: "start",
        }}
      >
        <div
          style={{
            borderRadius: "26px",
            border: "1px solid var(--line)",
            background: "var(--surface-strong)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "20px 22px 18px",
              borderBottom: "1px solid var(--line)",
              display: "grid",
              gap: "14px",
            }}
          >
            <div>
              <h2 style={{ margin: 0, fontSize: "1.12rem" }}>Kayit Yonetimi</h2>
              <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>
                Son attendance kayitlarini filtrele, sec ve ayni ekranda guncelle.
              </p>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1fr) minmax(220px, 280px)",
                gap: "12px",
              }}
            >
              <input
                type="search"
                placeholder="Sube, personel veya not ara..."
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                style={fieldStyle}
              />
              <select
                value={filterRestaurantId}
                onChange={(event) => setFilterRestaurantId(Number(event.target.value) || "")}
                style={fieldStyle}
              >
                <option value="">Tum subeler</option>
                {restaurants.map((restaurant) => (
                  <option key={restaurant.id} value={restaurant.id}>
                    {restaurant.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {listError ? (
            <div style={feedbackBox("error")}>{listError}</div>
          ) : listLoading ? (
            <div style={feedbackBox("info")}>Kayit listesi yukleniyor...</div>
          ) : (
            <div
              style={{
                maxHeight: "620px",
                overflow: "auto",
              }}
            >
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                }}
              >
                <thead
                  style={{
                    position: "sticky",
                    top: 0,
                    zIndex: 1,
                    background: "rgba(245, 249, 255, 0.98)",
                    backdropFilter: "blur(12px)",
                  }}
                >
                  <tr>
                    {["Tarih", "Sube", "Akis", "Calisan", "Mesai", "Paket"].map((header) => (
                      <th
                        key={header}
                        style={{
                          padding: "14px 16px",
                          textAlign: "left",
                          fontSize: "0.78rem",
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                          color: "var(--muted)",
                          borderBottom: "1px solid var(--line)",
                        }}
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => {
                    const isSelected = selectedEntryId === entry.id;
                    return (
                      <tr
                        key={entry.id}
                        onClick={() => setSelectedEntryId(entry.id)}
                        style={{
                          cursor: "pointer",
                          background: isSelected ? "rgba(15, 95, 215, 0.06)" : "transparent",
                        }}
                      >
                        <td style={tableCellStyle}>
                          <div style={{ fontWeight: 700 }}>{entry.entry_date}</div>
                        </td>
                        <td style={tableCellStyle}>
                          <div style={{ fontWeight: 700 }}>{entry.restaurant}</div>
                          {entry.notes ? (
                            <div
                              style={{
                                marginTop: "4px",
                                color: "var(--muted)",
                                fontSize: "0.84rem",
                              }}
                            >
                              {entry.notes}
                            </div>
                          ) : null}
                        </td>
                        <td style={tableCellStyle}>
                          <span
                            style={badgeStyle(
                              entry.entry_mode === "Restoran Kuryesi"
                                ? "accent"
                                : entry.entry_mode === "Haftalık İzin"
                                  ? "warn"
                                  : "soft",
                            )}
                          >
                            {entry.entry_mode}
                          </span>
                        </td>
                        <td style={tableCellStyle}>
                          <div style={{ fontWeight: 700 }}>{entry.primary_person_label}</div>
                          {entry.replacement_person_label && entry.replacement_person_label !== "-" ? (
                            <div
                              style={{
                                marginTop: "4px",
                                color: "var(--muted)",
                                fontSize: "0.84rem",
                              }}
                            >
                              Yerine: {entry.replacement_person_label}
                            </div>
                          ) : null}
                        </td>
                        <td style={tableCellStyle}>{formatHours(entry.worked_hours)}</td>
                        <td style={tableCellStyle}>{formatPackages(entry.package_count)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div
          style={{
            display: "grid",
            gap: "14px",
          }}
        >
          <div
            style={{
              borderRadius: "26px",
              border: "1px solid var(--line)",
              background: "linear-gradient(180deg, rgba(15, 95, 215, 0.08), rgba(255, 255, 255, 0.96))",
              padding: "20px 22px",
            }}
          >
            <div
              style={{
                display: "inline-flex",
                padding: "7px 12px",
                borderRadius: "999px",
                background: "rgba(255, 255, 255, 0.8)",
                color: "var(--accent)",
                fontWeight: 800,
                fontSize: "0.74rem",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Secili Kayit
            </div>
            <h3
              style={{
                margin: "14px 0 8px",
                fontSize: "1.2rem",
              }}
            >
              Attendance edit akisi
            </h3>
            <p
              style={{
                margin: 0,
                color: "var(--muted)",
                lineHeight: 1.6,
              }}
            >
              Kaydi sec, personel ve vardiya detaylarini guncelle ya da ayni panelden sil.
            </p>
          </div>

          <div
            style={{
              borderRadius: "26px",
              border: "1px solid var(--line)",
              background: "var(--surface-strong)",
              padding: "20px 22px",
            }}
          >
            {!selectedEntryId ? (
              <div style={feedbackBox("info")}>Duzenlemek icin soldan bir attendance kaydi sec.</div>
            ) : detailLoading ? (
              <div style={feedbackBox("info")}>Secili kayit yukleniyor...</div>
            ) : detailError ? (
              <div style={feedbackBox("error")}>{detailError}</div>
            ) : (
              <form
                onSubmit={handleSave}
                style={{
                  display: "grid",
                  gap: "14px",
                }}
              >
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "12px",
                  }}
                >
                  <label style={{ display: "grid", gap: "7px" }}>
                    <span style={labelStyle}>Tarih</span>
                    <input
                      type="date"
                      value={editDate}
                      onChange={(event) => setEditDate(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "7px" }}>
                    <span style={labelStyle}>Sube</span>
                    <select
                      value={editRestaurantId}
                      onChange={(event) => {
                        void handleEditorRestaurantChange(event.target.value);
                      }}
                      style={fieldStyle}
                    >
                      {restaurants.map((restaurant) => (
                        <option key={restaurant.id} value={restaurant.id}>
                          {restaurant.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "7px" }}>
                    <span style={labelStyle}>Vardiya Akisi</span>
                    <select
                      value={editEntryMode}
                      onChange={(event) => setEditEntryMode(event.target.value)}
                      style={fieldStyle}
                    >
                      {entryModes.map((mode) => (
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
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "12px",
                  }}
                >
                  <label style={{ display: "grid", gap: "7px" }}>
                    <span style={labelStyle}>
                      {needsReplacement ? "Normalde Girecek" : "Calisan Personel"}
                    </span>
                    <select
                      value={editPrimaryPersonId}
                      onChange={(event) => setEditPrimaryPersonId(Number(event.target.value) || "")}
                      style={fieldStyle}
                    >
                      <option value="">Sec</option>
                      {editorPeople.map((person) => (
                        <option key={person.id} value={person.id}>
                          {person.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  {needsReplacement ? (
                    <label style={{ display: "grid", gap: "7px" }}>
                      <span style={labelStyle}>Yerine Giren</span>
                      <select
                        value={editReplacementPersonId}
                        onChange={(event) =>
                          setEditReplacementPersonId(Number(event.target.value) || "")
                        }
                        style={fieldStyle}
                      >
                        <option value="">Sec</option>
                        {editorPeople.map((person) => (
                          <option key={person.id} value={person.id}>
                            {person.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}

                  {needsAbsenceReason ? (
                    <label style={{ display: "grid", gap: "7px" }}>
                      <span style={labelStyle}>Neden Girmedi</span>
                      <select
                        value={editAbsenceReason}
                        onChange={(event) => setEditAbsenceReason(event.target.value)}
                        style={fieldStyle}
                      >
                        <option value="">Sec</option>
                        {absenceReasons.map((reason) => (
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
                    gridTemplateColumns: isFixedMonthly
                      ? "repeat(auto-fit, minmax(160px, 1fr))"
                      : "repeat(auto-fit, minmax(200px, 1fr))",
                    gap: "12px",
                  }}
                >
                  <label style={{ display: "grid", gap: "7px" }}>
                    <span style={labelStyle}>Calisilan Saat</span>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      value={editWorkedHours}
                      onChange={(event) => setEditWorkedHours(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "7px" }}>
                    <span style={labelStyle}>Paket</span>
                    <input
                      type="number"
                      step="1"
                      min="0"
                      value={editPackageCount}
                      onChange={(event) => setEditPackageCount(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                  {isFixedMonthly ? (
                    <label style={{ display: "grid", gap: "7px" }}>
                      <span style={labelStyle}>Aylik Fatura Tutari</span>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={editMonthlyInvoiceAmount}
                        onChange={(event) => setEditMonthlyInvoiceAmount(event.target.value)}
                        style={fieldStyle}
                      />
                    </label>
                  ) : null}
                </div>

                <label style={{ display: "grid", gap: "7px" }}>
                  <span style={labelStyle}>Not</span>
                  <textarea
                    value={editNotes}
                    onChange={(event) => setEditNotes(event.target.value)}
                    rows={4}
                    style={{
                      ...fieldStyle,
                      resize: "vertical",
                    }}
                  />
                </label>

                {saveError ? <div style={feedbackBox("error")}>{saveError}</div> : null}
                {saveSuccess ? <div style={feedbackBox("success")}>{saveSuccess}</div> : null}

                <div
                  style={{
                    display: "flex",
                    gap: "10px",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                  }}
                >
                  <button type="button" onClick={handleDelete} style={secondaryButtonStyle}>
                    Kaydi Sil
                  </button>
                  <button type="submit" disabled={isPending} style={primaryButtonStyle}>
                    {isPending ? "Kaydediliyor..." : "Kaydi Guncelle"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <article
      style={{
        padding: "18px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.78rem",
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
          fontSize: "1.75rem",
          fontWeight: 900,
          letterSpacing: "-0.04em",
        }}
      >
        {value}
      </div>
      <div
        style={{
          marginTop: "8px",
          color: "var(--muted)",
          fontSize: "0.86rem",
          lineHeight: 1.5,
        }}
      >
        {hint}
      </div>
    </article>
  );
}

const fieldStyle: CSSProperties = {
  width: "100%",
  padding: "13px 14px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.92)",
  color: "var(--text)",
  fontSize: "0.98rem",
  outline: "none",
};

const labelStyle: CSSProperties = {
  fontWeight: 800,
  fontSize: "0.88rem",
  color: "var(--muted)",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const tableCellStyle: CSSProperties = {
  padding: "14px 16px",
  borderBottom: "1px solid rgba(188, 205, 230, 0.55)",
  verticalAlign: "top",
  fontSize: "0.94rem",
};

const primaryButtonStyle: CSSProperties = {
  padding: "13px 20px",
  borderRadius: "16px",
  border: "none",
  background: "linear-gradient(135deg, #0f5fd7, #2c86ff)",
  color: "#fff",
  fontWeight: 800,
  cursor: "pointer",
  boxShadow: "0 14px 32px rgba(15, 95, 215, 0.18)",
};

const secondaryButtonStyle: CSSProperties = {
  padding: "13px 20px",
  borderRadius: "16px",
  border: "1px solid rgba(200, 77, 77, 0.18)",
  background: "rgba(255, 245, 245, 0.92)",
  color: "#b54747",
  fontWeight: 800,
  cursor: "pointer",
};

function feedbackBox(kind: "info" | "error" | "success"): CSSProperties {
  const palette = {
    info: {
      background: "rgba(15, 95, 215, 0.08)",
      color: "var(--muted)",
      border: "1px solid rgba(15, 95, 215, 0.12)",
    },
    error: {
      background: "rgba(217, 67, 67, 0.08)",
      color: "#b54747",
      border: "1px solid rgba(217, 67, 67, 0.12)",
    },
    success: {
      background: "rgba(41, 155, 93, 0.08)",
      color: "#21724a",
      border: "1px solid rgba(41, 155, 93, 0.12)",
    },
  }[kind];
  return {
    padding: "14px 16px",
    borderRadius: "16px",
    fontSize: "0.94rem",
    ...palette,
  };
}
