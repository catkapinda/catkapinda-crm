"use client";

import type { CSSProperties, FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type DeductionEntry = {
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
};

type DeductionsManagementResponse = {
  total_entries: number;
  entries: DeductionEntry[];
};

type DeductionsFormOptions = {
  personnel: Array<{
    id: number;
    label: string;
  }>;
  deduction_types: string[];
  type_captions: Record<string, string>;
  selected_personnel_id: number | null;
};

type DeductionDetailResponse = {
  entry: DeductionEntry;
};

function pill(kind: "accent" | "muted" | "warn"): CSSProperties {
  const palette = {
    accent: {
      background: "rgba(15, 95, 215, 0.1)",
      color: "#0f5fd7",
      border: "1px solid rgba(15, 95, 215, 0.14)",
    },
    muted: {
      background: "rgba(95, 118, 152, 0.1)",
      color: "#5f7698",
      border: "1px solid rgba(95, 118, 152, 0.12)",
    },
    warn: {
      background: "rgba(230, 140, 55, 0.12)",
      color: "#b96a18",
      border: "1px solid rgba(230, 140, 55, 0.16)",
    },
  }[kind];
  return {
    display: "inline-flex",
    alignItems: "center",
    padding: "6px 10px",
    borderRadius: "999px",
    fontSize: "0.76rem",
    fontWeight: 800,
    ...palette,
  };
}

const fieldStyle: CSSProperties = {
  width: "100%",
  padding: "13px 14px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.9)",
  color: "var(--text)",
  font: "inherit",
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

export function DeductionManagementWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const [options, setOptions] = useState<DeductionsFormOptions | null>(null);
  const [entries, setEntries] = useState<DeductionEntry[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const deferredSearch = useDeferredValue(searchInput);
  const [filterPersonnelId, setFilterPersonnelId] = useState<number | "">("");
  const [filterDeductionType, setFilterDeductionType] = useState("");
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

  const [editPersonnelId, setEditPersonnelId] = useState<number | "">("");
  const [editDeductionDate, setEditDeductionDate] = useState("");
  const [editDeductionType, setEditDeductionType] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editIsAuto, setEditIsAuto] = useState(false);

  async function loadOptions() {
    const response = await apiFetch("/deductions/form-options");
    if (!response.ok) {
      throw new Error("Kesinti referans verileri yuklenemedi.");
    }
    const payload = (await response.json()) as DeductionsFormOptions;
    setOptions(payload);
    if (!filterPersonnelId && payload.selected_personnel_id) {
      setFilterPersonnelId(payload.selected_personnel_id);
    }
  }

  async function loadEntries() {
    setListLoading(true);
    setListError("");
    try {
      const query = new URLSearchParams();
      query.set("limit", "180");
      if (typeof filterPersonnelId === "number") {
        query.set("personnel_id", String(filterPersonnelId));
      }
      if (filterDeductionType) {
        query.set("deduction_type", filterDeductionType);
      }
      if (deferredSearch.trim()) {
        query.set("search", deferredSearch.trim());
      }
      const response = await apiFetch(`/deductions/records?${query.toString()}`);
      if (!response.ok) {
        throw new Error("Kesinti listesi yuklenemedi.");
      }
      const payload = (await response.json()) as DeductionsManagementResponse;
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
      setListError(error instanceof Error ? error.message : "Kesinti listesi yuklenemedi.");
      setEntries([]);
      setTotalEntries(0);
      setSelectedEntryId(null);
    } finally {
      setListLoading(false);
    }
  }

  async function loadEntryDetail(entryId: number) {
    setDetailLoading(true);
    setSaveError("");
    setSaveSuccess("");
    try {
      const response = await apiFetch(`/deductions/records/${entryId}`);
      if (!response.ok) {
        throw new Error("Kesinti detayi yuklenemedi.");
      }
      const payload = (await response.json()) as DeductionDetailResponse;
      const entry = payload.entry;
      setEditPersonnelId(entry.personnel_id);
      setEditDeductionDate(entry.deduction_date);
      setEditDeductionType(entry.deduction_type);
      setEditAmount(String(entry.amount));
      setEditNotes(entry.notes ?? "");
      setEditIsAuto(entry.is_auto_record);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Kesinti detayi yuklenemedi.");
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    void loadOptions();
  }, []);

  useEffect(() => {
    if (!options) {
      return;
    }
    void loadEntries();
  }, [options, deferredSearch, filterPersonnelId, filterDeductionType]);

  useEffect(() => {
    if (selectedEntryId == null) {
      return;
    }
    void loadEntryDetail(selectedEntryId);
  }, [selectedEntryId]);

  const selectedEntry = useMemo(
    () => entries.find((entry) => entry.id === selectedEntryId) ?? null,
    [entries, selectedEntryId],
  );

  const selectedCaption = useMemo(() => {
    if (!options || !editDeductionType) {
      return "";
    }
    return options.type_captions[editDeductionType] ?? "";
  }, [options, editDeductionType]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEntryId || typeof editPersonnelId !== "number") {
      setSaveError("Duzenlenecek kesinti seç.");
      return;
    }

    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/deductions/records/${selectedEntryId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personnel_id: editPersonnelId,
        deduction_date: editDeductionDate,
        deduction_type: editDeductionType,
        amount: Number(editAmount || 0),
        notes: editNotes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSaveError(payload?.detail || "Kesinti kaydı güncellenemedi.");
      return;
    }

    setSaveSuccess(payload?.message || "Kesinti kaydı güncellendi.");
    startTransition(() => {
      router.refresh();
    });
    await loadEntries();
    await loadEntryDetail(selectedEntryId);
  }

  async function handleDelete() {
    if (!selectedEntryId) {
      setSaveError("Silinecek kesinti seç.");
      return;
    }
    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/deductions/records/${selectedEntryId}`, {
      method: "DELETE",
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSaveError(payload?.detail || "Kesinti kaydı silinemedi.");
      return;
    }
    setSaveSuccess(payload?.message || "Kesinti kaydı silindi.");
    startTransition(() => {
      router.refresh();
    });
    await loadEntries();
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Kesinti Kayıt Yönetimi</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Kayıtları filtrele, seç, güncelle ve sil. Otomatik oluşan satırlar salt okunur tutulur.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(320px, 1.1fr) minmax(280px, 0.9fr)",
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
              gridTemplateColumns: "minmax(180px, 1fr) minmax(180px, 1fr) minmax(180px, 1.2fr)",
              gap: "12px",
            }}
          >
            <select
              value={filterPersonnelId}
              onChange={(event) => {
                const value = event.target.value;
                setFilterPersonnelId(value ? Number(value) : "");
              }}
              style={fieldStyle}
            >
              <option value="">Tüm personel</option>
              {options?.personnel.map((person) => (
                <option key={person.id} value={person.id}>
                  {person.label}
                </option>
              ))}
            </select>

            <select
              value={filterDeductionType}
              onChange={(event) => setFilterDeductionType(event.target.value)}
              style={fieldStyle}
            >
              <option value="">Tüm tipler</option>
              {options?.deduction_types.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>

            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Personel, tip veya not ara"
              style={fieldStyle}
            />
          </div>

          <div
            style={{
              borderRadius: "20px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.86)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "14px 16px",
                borderBottom: "1px solid var(--line)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <strong>{totalEntries} kayıt</strong>
              <span style={pill("muted")}>{entries.length} gosteriliyor</span>
            </div>

            <div
              style={{
                maxHeight: "440px",
                overflowY: "auto",
              }}
            >
              {listLoading ? (
                <div style={{ padding: "18px 16px", color: "var(--muted)" }}>Kayitlar yükleniyor...</div>
              ) : entries.length === 0 ? (
                <div style={{ padding: "18px 16px", color: "var(--muted)" }}>Eslesen kesinti kaydı yok.</div>
              ) : (
                entries.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    onClick={() => setSelectedEntryId(entry.id)}
                    style={{
                      width: "100%",
                      border: "none",
                      background: entry.id === selectedEntryId ? "rgba(15, 95, 215, 0.08)" : "transparent",
                      padding: "14px 16px",
                      textAlign: "left",
                      borderBottom: "1px solid rgba(193, 209, 232, 0.5)",
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center" }}>
                      <div style={{ fontWeight: 800 }}>{entry.personnel_label}</div>
                      <span style={entry.is_auto_record ? pill("warn") : pill("accent")}>
                        {entry.is_auto_record ? "Otomatik" : "Manuel"}
                      </span>
                    </div>
                    <div style={{ marginTop: "6px", color: "var(--muted)", fontSize: "0.9rem" }}>
                      {entry.deduction_type} · {entry.deduction_date}
                    </div>
                    <div style={{ marginTop: "10px", display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center" }}>
                      <span style={{ color: "var(--text)", fontWeight: 800 }}>{formatCurrency(entry.amount)}</span>
                      <span style={pill("muted")}>#{entry.id}</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
          {listError && (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "16px",
                border: "1px solid rgba(205, 70, 66, 0.18)",
                background: "rgba(205, 70, 66, 0.08)",
                color: "#b53632",
                fontWeight: 700,
              }}
            >
              {listError}
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
              padding: "16px",
              borderRadius: "20px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.86)",
              display: "grid",
              gap: "10px",
            }}
          >
            <div style={{ fontWeight: 900 }}>Seçili Kayıt</div>
            {selectedEntry ? (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                  <span style={{ color: "var(--muted)" }}>Personel</span>
                  <strong>{selectedEntry.personnel_label}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                  <span style={{ color: "var(--muted)" }}>Tip</span>
                  <strong>{selectedEntry.deduction_type}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                  <span style={{ color: "var(--muted)" }}>Tutar</span>
                  <strong>{formatCurrency(selectedEntry.amount)}</strong>
                </div>
                <div>{selectedEntry.type_caption}</div>
              </>
            ) : (
              <div style={{ color: "var(--muted)" }}>Düzenlemek için soldan bir kayıt seç.</div>
            )}
          </div>

          <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Personel</span>
              <select
                value={editPersonnelId}
                onChange={(event) => setEditPersonnelId(Number(event.target.value))}
                style={fieldStyle}
                disabled={detailLoading || editIsAuto}
              >
                {options?.personnel.map((person) => (
                  <option key={person.id} value={person.id}>
                    {person.label}
                  </option>
                ))}
              </select>
            </label>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "12px",
              }}
            >
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Tarih</span>
                <input
                  type="date"
                  value={editDeductionDate}
                  onChange={(event) => setEditDeductionDate(event.target.value)}
                  style={fieldStyle}
                  disabled={detailLoading || editIsAuto}
                />
              </label>

              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Tutar</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={editAmount}
                  onChange={(event) => setEditAmount(event.target.value)}
                  style={fieldStyle}
                  disabled={detailLoading || editIsAuto}
                />
              </label>
            </div>

            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Kesinti Tipi</span>
              <select
                value={editDeductionType}
                onChange={(event) => setEditDeductionType(event.target.value)}
                style={fieldStyle}
                disabled={detailLoading || editIsAuto}
              >
                {options?.deduction_types.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>

            <div
              style={{
                borderRadius: "18px",
                border: "1px solid var(--line)",
                background: "rgba(255, 255, 255, 0.85)",
                padding: "14px 16px",
                color: "var(--muted)",
                lineHeight: 1.7,
              }}
            >
              <div style={{ fontWeight: 800, color: "var(--text)", marginBottom: "4px" }}>
                Tip Aciklamasi
              </div>
              {selectedCaption || "Seçilen kesinti tipinin açıklaması burada görünür."}
            </div>

            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Not</span>
              <textarea
                value={editNotes}
                onChange={(event) => setEditNotes(event.target.value)}
                rows={3}
                style={{ ...fieldStyle, resize: "vertical" }}
                disabled={detailLoading || editIsAuto}
              />
            </label>

            {editIsAuto && (
              <div
                style={{
                  padding: "14px 16px",
                  borderRadius: "16px",
                  border: "1px solid rgba(230, 140, 55, 0.16)",
                  background: "rgba(230, 140, 55, 0.08)",
                  color: "#b96a18",
                  fontWeight: 700,
                }}
              >
                Bu satir otomatik olustugu için v2 ekraninda düzenlenemez veya silinemez.
              </div>
            )}

            {(saveError || saveSuccess) && (
              <div
                style={{
                  padding: "14px 16px",
                  borderRadius: "16px",
                  border: saveError ? "1px solid rgba(205, 70, 66, 0.18)" : "1px solid rgba(35, 148, 94, 0.18)",
                  background: saveError ? "rgba(205, 70, 66, 0.08)" : "rgba(35, 148, 94, 0.08)",
                  color: saveError ? "#b53632" : "#1d7b4d",
                  fontWeight: 700,
                }}
              >
                {saveError || saveSuccess}
              </div>
            )}

            <div style={{ display: "flex", gap: "12px" }}>
              <button
                type="submit"
                disabled={isPending || detailLoading || editIsAuto || !selectedEntryId}
                style={{
                  flex: 1,
                  border: "none",
                  borderRadius: "18px",
                  padding: "15px 18px",
                  background: "linear-gradient(135deg, #0f5fd7, #1a73e8)",
                  color: "white",
                  fontWeight: 800,
                  fontSize: "0.96rem",
                  cursor: "pointer",
                }}
              >
                {isPending ? "Kaydediliyor..." : "Kaydı Güncelle"}
              </button>
              <button
                type="button"
                onClick={() => {
                  void handleDelete();
                }}
                disabled={isPending || detailLoading || editIsAuto || !selectedEntryId}
                style={{
                  flex: 1,
                  borderRadius: "18px",
                  padding: "15px 18px",
                  background: "rgba(205, 70, 66, 0.08)",
                  color: "#b53632",
                  border: "1px solid rgba(205, 70, 66, 0.18)",
                  fontWeight: 800,
                  fontSize: "0.96rem",
                  cursor: "pointer",
                }}
              >
                Kaydı Sil
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}
