"use client";

import type { CSSProperties, FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiErrorMessage, apiFetch } from "../../lib/api";
import {
  dangerGradientButtonStyle as dangerButtonStyle,
  feedbackBoxStyle as feedbackBox,
  managementFieldStyle,
  softDangerButtonStyle as secondaryButtonStyle,
} from "../shared/compact-ui";

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

type AttendanceBulkDeleteResponse = {
  entry_ids: number[];
  deleted_count: number;
  message: string;
};

type AttendanceFilteredDeleteResponse = {
  deleted_count: number;
  date_from: string;
  date_to: string;
  restaurant_id: number | null;
  search: string;
  message: string;
};

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

function resolveMonthWindow(monthValue: string) {
  if (!monthValue) {
    return null;
  }
  const [yearText, monthText] = monthValue.split("-");
  const year = Number(yearText);
  const month = Number(monthText);
  if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) {
    return null;
  }
  const dateFrom = `${yearText}-${monthText}-01`;
  const dateTo = new Date(Date.UTC(year, month, 0)).toISOString().slice(0, 10);
  return { dateFrom, dateTo };
}

function formatMonthLabel(monthValue: string) {
  const windowValue = resolveMonthWindow(monthValue);
  if (!windowValue) {
    return "";
  }
  return new Intl.DateTimeFormat("tr-TR", {
    month: "long",
    year: "numeric",
  }).format(new Date(`${windowValue.dateFrom}T12:00:00`));
}

type AttendanceManagementWorkspaceProps = {
  onDataChange?: () => void;
};

export function AttendanceManagementWorkspace({ onDataChange }: AttendanceManagementWorkspaceProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const [restaurants, setRestaurants] = useState<AttendanceFormOptions["restaurants"]>([]);
  const [entryModes, setEntryModes] = useState<string[]>([]);
  const [absenceReasons, setAbsenceReasons] = useState<string[]>([]);
  const [editorPeople, setEditorPeople] = useState<AttendanceFormOptions["people"]>([]);

  const [searchInput, setSearchInput] = useState("");
  const deferredSearch = useDeferredValue(searchInput);
  const [filterRestaurantId, setFilterRestaurantId] = useState<number | "">("");
  const [filterMonth, setFilterMonth] = useState("");

  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [entries, setEntries] = useState<AttendanceEntry[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  const [selectedEntryIds, setSelectedEntryIds] = useState<number[]>([]);

  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");
  const [deletePending, setDeletePending] = useState(false);
  const [bulkDeletePending, setBulkDeletePending] = useState(false);
  const [filteredDeletePending, setFilteredDeletePending] = useState(false);

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

  const selectedRestaurant = useMemo(() => {
    if (typeof editRestaurantId !== "number") {
      return null;
    }
    return restaurants.find((restaurant) => restaurant.id === editRestaurantId) ?? null;
  }, [editRestaurantId, restaurants]);

  const isFixedMonthly = selectedRestaurant?.pricing_model === "fixed_monthly";
  const needsReplacement = editEntryMode === "Joker" || editEntryMode === "Destek";
  const needsAbsenceReason = editEntryMode !== "Restoran Kuryesi";
  const selectedEntryIdSet = useMemo(() => new Set(selectedEntryIds), [selectedEntryIds]);
  const activeMonthWindow = useMemo(() => resolveMonthWindow(filterMonth), [filterMonth]);
  const activeMonthLabel = useMemo(() => formatMonthLabel(filterMonth), [filterMonth]);
  const allVisibleSelected =
    entries.length > 0 && entries.every((entry) => selectedEntryIdSet.has(entry.id));
  const selectedVisibleCount = entries.filter((entry) => selectedEntryIdSet.has(entry.id)).length;
  const hasSelectedEntry = Boolean(selectedEntryId);
  const isAnyMutationPending =
    isPending || deletePending || bulkDeletePending || filteredDeletePending;

  async function loadReferenceOptions() {
    const response = await apiFetch("/attendance/form-options");
    if (!response.ok) {
      throw new Error(await apiErrorMessage(response, "Puantaj seçenekleri alınamadı. Lütfen tekrar dene."));
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
      query.set("limit", "500");
      if (typeof filterRestaurantId === "number") {
        query.set("restaurant_id", String(filterRestaurantId));
      }
      if (activeMonthWindow) {
        query.set("date_from", activeMonthWindow.dateFrom);
        query.set("date_to", activeMonthWindow.dateTo);
      }
      if (deferredSearch.trim()) {
        query.set("search", deferredSearch.trim());
      }
      const response = await apiFetch(`/attendance/entries?${query.toString()}`);
      if (!response.ok) {
        throw new Error(await apiErrorMessage(response, "Puantaj kayıtları alınamadı. Lütfen tekrar dene."));
      }
      const payload = (await response.json()) as AttendanceManagementResponse;
      const visibleEntryIdSet = new Set(payload.entries.map((entry) => entry.id));
      setEntries(payload.entries);
      setTotalEntries(payload.total_entries);
      setSelectedEntryIds((current) => current.filter((entryId) => visibleEntryIdSet.has(entryId)));
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
      setListError(error instanceof Error ? error.message : "Puantaj kayıtları alınamadı. Lütfen tekrar dene.");
      setEntries([]);
      setTotalEntries(0);
      setSelectedEntryId(null);
    } finally {
      setListLoading(false);
    }
  }

  function toggleEntrySelection(entryId: number, checked: boolean) {
    setSelectedEntryIds((current) => {
      if (checked) {
        if (current.includes(entryId)) {
          return current;
        }
        return [...current, entryId];
      }
      return current.filter((currentEntryId) => currentEntryId !== entryId);
    });
  }

  function toggleVisibleEntries(checked: boolean) {
    const visibleEntryIds = entries.map((entry) => entry.id);
    const visibleEntryIdSet = new Set(visibleEntryIds);
    setSelectedEntryIds((current) => {
      if (checked) {
        return Array.from(new Set([...current, ...visibleEntryIds]));
      }
      return current.filter((entryId) => !visibleEntryIdSet.has(entryId));
    });
  }

  async function loadPeopleOptions(restaurantId: number) {
    const response = await apiFetch(
      `/attendance/form-options?restaurant_id=${encodeURIComponent(String(restaurantId))}&include_all_active=true`,
    );
    if (!response.ok) {
      throw new Error(await apiErrorMessage(response, "Personel seçenekleri alınamadı. Lütfen tekrar dene."));
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
      const response = await apiFetch(`/attendance/entries/${entryId}`);
      if (!response.ok) {
        throw new Error(await apiErrorMessage(response, "Kayıt detayı alınamadı. Lütfen tekrar dene."));
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
      setDetailError(error instanceof Error ? error.message : "Kayıt detayı alınamadı. Lütfen tekrar dene.");
      setEditorPeople([]);
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    void loadReferenceOptions().catch((error) => {
      setListError(
        error instanceof Error ? error.message : "Puantaj seçenekleri alınamadı. Lütfen tekrar dene.",
      );
    });
  }, []);

  useEffect(() => {
    void loadEntries();
  }, [filterRestaurantId, deferredSearch, activeMonthWindow]);

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
      setSaveError("Lütfen bir şube seç.");
      return;
    }

    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/attendance/entries/${selectedEntryId}`, {
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
      setSaveError(payload?.detail || "Kayıt güncellenemedi.");
      return;
    }

    setSaveSuccess(payload?.message || "Kayıt güncellendi.");
    await loadEntries();
    await loadEntryDetail(selectedEntryId);
    onDataChange?.();
    startTransition(() => {
      router.refresh();
    });
  }

  async function handleDelete() {
    if (!selectedEntryId) {
      return;
    }

    const shouldDelete = window.confirm("Bu puantaj kaydı silinsin mi?");
    if (!shouldDelete) {
      return;
    }

    setSaveError("");
    setSaveSuccess("");
    setDeletePending(true);

    try {
      const response = await apiFetch(`/attendance/entries/${selectedEntryId}`, {
        method: "DELETE",
      });
      const payload = (await response.json().catch(() => null)) as
        | { detail?: string; message?: string }
        | null;

      if (!response.ok) {
        setSaveError(payload?.detail || "Kayıt silinemedi.");
        return;
      }

      setSelectedEntryIds((current) =>
        current.filter((entryId) => entryId !== selectedEntryId),
      );
      setSaveSuccess(payload?.message || "Kayıt silindi.");
      await loadEntries();
      onDataChange?.();
      startTransition(() => {
        router.refresh();
      });
    } finally {
      setDeletePending(false);
    }
  }

  async function handleBulkDelete() {
    if (!selectedEntryIds.length) {
      return;
    }

    const shouldDelete = window.confirm(
      `Seçili ${selectedEntryIds.length} puantaj kaydı silinsin mi?`,
    );
    if (!shouldDelete) {
      return;
    }

    setSaveError("");
    setSaveSuccess("");
    setBulkDeletePending(true);

    try {
      const response = await apiFetch("/attendance/entries", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          entry_ids: selectedEntryIds,
        }),
      });
      const payload = (await response.json().catch(() => null)) as
        | ({ detail?: string } & Partial<AttendanceBulkDeleteResponse>)
        | null;

      if (!response.ok) {
        setSaveError(payload?.detail || "Seçili puantaj kayıtları silinemedi.");
        return;
      }

      const deletedEntryIds = Array.isArray(payload?.entry_ids) ? payload.entry_ids : selectedEntryIds;
      const deletedEntryIdSet = new Set(deletedEntryIds);
      setSelectedEntryIds((current) =>
        current.filter((entryId) => !deletedEntryIdSet.has(entryId)),
      );
      setSelectedEntryId((current) =>
        current !== null && deletedEntryIdSet.has(current) ? null : current,
      );
      setSaveSuccess(payload?.message || "Seçili puantaj kayıtları silindi.");
      await loadEntries();
      onDataChange?.();
      startTransition(() => {
        router.refresh();
      });
    } finally {
      setBulkDeletePending(false);
    }
  }

  async function handleFilteredDelete() {
    if (!activeMonthWindow || totalEntries <= 0) {
      return;
    }

    const monthLabel = activeMonthLabel || "seçilen ay";
    const restaurantLabel =
      typeof filterRestaurantId === "number"
        ? restaurants.find((restaurant) => restaurant.id === filterRestaurantId)?.label ?? ""
        : "";
    const searchLabel = deferredSearch.trim();
    const extraNotes = [
      restaurantLabel ? `Şube: ${restaurantLabel}` : "",
      searchLabel ? `Arama: ${searchLabel}` : "",
    ].filter(Boolean);
    const shouldDelete = window.confirm(
      [
        `${monthLabel} icindeki ${totalEntries} puantaj kaydı silinsin mi?`,
        extraNotes.length ? extraNotes.join("\n") : "",
        "Bu islem seçili aya uyan tüm kayıtları kalıcı olarak siler.",
      ]
        .filter(Boolean)
        .join("\n\n"),
    );
    if (!shouldDelete) {
      return;
    }

    setSaveError("");
    setSaveSuccess("");
    setFilteredDeletePending(true);

    try {
      const response = await apiFetch("/attendance/entries/filter", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          date_from: activeMonthWindow.dateFrom,
          date_to: activeMonthWindow.dateTo,
          restaurant_id: typeof filterRestaurantId === "number" ? filterRestaurantId : null,
          search: searchLabel,
        }),
      });
      const payload = (await response.json().catch(() => null)) as
        | ({ detail?: string } & Partial<AttendanceFilteredDeleteResponse>)
        | null;

      if (!response.ok) {
        setSaveError(payload?.detail || "Filtredeki puantaj kayıtları silinemedi.");
        return;
      }

      setSelectedEntryIds([]);
      setSelectedEntryId(null);
      setSaveSuccess(payload?.message || "Filtredeki puantaj kayıtları silindi.");
      await loadEntries();
      onDataChange?.();
      startTransition(() => {
        router.refresh();
      });
    } finally {
      setFilteredDeletePending(false);
    }
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
        <MetricCard label="Toplam Kayıt" value={String(totalEntries)} hint="Tüm filtreler disi genel sayi" />
        <MetricCard
          label="Gorunen Kayıt"
          value={String(summary.visibleEntries)}
          hint="Bu listede ekranda gorulen satırlar"
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
          gridTemplateColumns: hasSelectedEntry
            ? "minmax(0, 1.2fr) minmax(340px, 0.9fr)"
            : "minmax(0, 1fr)",
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
              <h2 style={{ margin: 0, fontSize: "1.12rem" }}>Kayıt Yonetimi</h2>
              <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>
                Son attendance kayıtlarını filtrele, seç, ay bazinda toplu sil veya aynı ekranda
                güncelle.
              </p>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "12px",
              }}
            >
              <input
                type="search"
                placeholder="Şube, personel veya not ara..."
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                style={fieldStyle}
              />
              <select
                value={filterRestaurantId}
                onChange={(event) => setFilterRestaurantId(Number(event.target.value) || "")}
                style={fieldStyle}
              >
                <option value="">Tüm şubeler</option>
                {restaurants.map((restaurant) => (
                  <option key={restaurant.id} value={restaurant.id}>
                    {restaurant.label}
                  </option>
                ))}
              </select>
              <input
                type="month"
                value={filterMonth}
                onChange={(event) => setFilterMonth(event.target.value)}
                style={fieldStyle}
              />
            </div>

            <div
              style={{
                display: "flex",
                gap: "10px",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <span
                style={badgeStyle(selectedEntryIds.length ? "accent" : "muted")}
              >
                {selectedEntryIds.length
                  ? `${selectedEntryIds.length} kayıt seçili${
                      selectedVisibleCount ? ` • ${selectedVisibleCount} görünüyor` : ""
                    }`
                  : activeMonthLabel
                    ? `${activeMonthLabel} filtresi aktif`
                    : "Toplu silme için kayıt seç"}
              </span>
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  flexWrap: "wrap",
                  justifyContent: "flex-end",
                }}
              >
                {selectedEntryIds.length ? (
                  <button
                    type="button"
                    onClick={() => setSelectedEntryIds([])}
                    disabled={isAnyMutationPending}
                    style={tertiaryButtonStyle}
                  >
                    Seçimi Temizle
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => setFilterMonth("")}
                  disabled={!filterMonth || isAnyMutationPending}
                  style={tertiaryButtonStyle}
                >
                  Ay Filtresini Temizle
                </button>
                <button
                  type="button"
                  onClick={handleFilteredDelete}
                  disabled={!activeMonthWindow || totalEntries <= 0 || isAnyMutationPending}
                  style={dangerButtonStyle}
                >
                  {filteredDeletePending
                    ? "Filtredeki Ay Siliniyor..."
                    : activeMonthLabel
                      ? `${activeMonthLabel} Kayıtlarını Sil`
                      : "Ayı Toplu Sil"}
                </button>
                <button
                  type="button"
                  onClick={handleBulkDelete}
                  disabled={!selectedEntryIds.length || isAnyMutationPending}
                  style={dangerButtonStyle}
                >
                  {bulkDeletePending ? "Seçilenler Siliniyor..." : "Seçilenleri Sil"}
                </button>
              </div>
            </div>

            {activeMonthLabel ? (
              <div style={feedbackBox("info")}>
                {activeMonthLabel} için toplam {totalEntries} kayıt bulundu.
                {totalEntries > entries.length
                  ? ` Listede ilk ${entries.length} kayıt gösteriliyor; ay silme işlemi tüm ${totalEntries} kaydı kapsar.`
                  : ""}
              </div>
            ) : null}
          </div>

          {listError ? (
            <div style={feedbackBox("error")}>{listError}</div>
          ) : listLoading ? (
            <div style={feedbackBox("info")}>Kayıt listesi yükleniyor...</div>
          ) : !entries.length ? (
            <div style={feedbackBox("info")}>Filtreye uygun puantaj kaydı bulunamadı.</div>
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
                    <th
                      style={{
                        ...tableHeaderCellStyle,
                        width: "54px",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={allVisibleSelected}
                        aria-label="Tüm görünen puantaj kayıtlarını seç"
                        onChange={(event) => toggleVisibleEntries(event.target.checked)}
                      />
                    </th>
                    {["Tarih", "Şube", "Akış", "Çalışan", "Mesai", "Paket"].map((header) => (
                      <th key={header} style={tableHeaderCellStyle}>
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => {
                    const isSelected = selectedEntryId === entry.id;
                    const isChecked = selectedEntryIdSet.has(entry.id);
                    return (
                      <tr
                        key={entry.id}
                        onClick={() => setSelectedEntryId(entry.id)}
                        style={{
                          cursor: "pointer",
                          background: isSelected
                            ? "rgba(15, 95, 215, 0.06)"
                            : isChecked
                              ? "rgba(15, 95, 215, 0.03)"
                              : "transparent",
                        }}
                      >
                        <td
                          style={{
                            ...tableCellStyle,
                            width: "54px",
                            textAlign: "center",
                          }}
                          onClick={(event) => event.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            aria-label={`${entry.restaurant} puantaj kaydini seç`}
                            onChange={(event) =>
                              toggleEntrySelection(entry.id, event.target.checked)
                            }
                          />
                        </td>
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

        {hasSelectedEntry ? (
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
                background:
                  "linear-gradient(180deg, rgba(15, 95, 215, 0.08), rgba(255, 255, 255, 0.96))",
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
                Seçili Kayıt
              </div>
              <h3
                style={{
                  margin: "14px 0 8px",
                  fontSize: "1.2rem",
                }}
              >
                Attendance düzenleme akışı
              </h3>
              <p
                style={{
                  margin: 0,
                  color: "var(--muted)",
                  lineHeight: 1.6,
                }}
              >
                Kaydı seç, personel ve vardiya detaylarını güncelle; istersen soldan birden fazla
                kaydı toplu silebilirsin.
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
              {detailLoading ? (
                <div style={feedbackBox("info")}>Seçili kayıt yükleniyor...</div>
              ) : detailError ? (
                <div style={feedbackBox("error")}>{detailError}</div>
            ) : (
              <form
                onSubmit={handleSave}
                style={{
                  display: "grid",
                  gap: "10px",
                }}
              >
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
                    gap: "10px",
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
                    <span style={labelStyle}>Şube</span>
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
                    <span style={labelStyle}>Vardiya Akışı</span>
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
                    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
                    gap: "10px",
                  }}
                >
                  <label style={{ display: "grid", gap: "7px" }}>
                    <span style={labelStyle}>
                      {needsReplacement ? "Normalde Girecek" : "Çalışan Personel"}
                    </span>
                    <select
                      value={editPrimaryPersonId}
                      onChange={(event) => setEditPrimaryPersonId(Number(event.target.value) || "")}
                      style={fieldStyle}
                    >
                      <option value="">Seç</option>
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
                        <option value="">Seç</option>
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
                        <option value="">Seç</option>
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
                      ? "repeat(auto-fit, minmax(150px, 1fr))"
                      : "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "10px",
                  }}
                >
                  <label style={{ display: "grid", gap: "7px" }}>
                    <span style={labelStyle}>Çalışılan Saat</span>
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
                      <span style={labelStyle}>Aylık Fatura Tutarı</span>
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
                    rows={3}
                    style={{
                      ...fieldStyle,
                      resize: "vertical",
                      minHeight: "60px",
                    }}
                  />
                </label>

                {saveError ? <div style={feedbackBox("error")}>{saveError}</div> : null}
                {saveSuccess ? <div style={feedbackBox("success")}>{saveSuccess}</div> : null}

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                    gap: "8px",
                  }}
                >
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={isAnyMutationPending}
                    style={secondaryButtonStyle}
                  >
                    {deletePending ? "Kayıt Siliniyor..." : "Kaydı Sil"}
                  </button>
                  <button type="submit" disabled={isAnyMutationPending} style={primaryButtonStyle}>
                    {isPending ? "Kaydediliyor..." : "Kaydı Güncelle"}
                  </button>
                </div>
              </form>
              )}
            </div>
          </div>
        ) : null}
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

const fieldStyle: CSSProperties = managementFieldStyle({
  density: "roomy",
  backgroundAlpha: 0.92,
  fontSize: "0.98rem",
  outline: "none",
});

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

const tableHeaderCellStyle: CSSProperties = {
  padding: "14px 16px",
  textAlign: "left",
  fontSize: "0.78rem",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  color: "var(--muted)",
  borderBottom: "1px solid var(--line)",
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

const tertiaryButtonStyle: CSSProperties = {
  padding: "13px 18px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.92)",
  color: "var(--muted)",
  fontWeight: 800,
  cursor: "pointer",
};
