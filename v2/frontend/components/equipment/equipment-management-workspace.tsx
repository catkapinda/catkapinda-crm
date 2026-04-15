"use client";

import type { CSSProperties, FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type EquipmentIssueEntry = {
  id: number;
  personnel_id: number;
  personnel_label: string;
  issue_date: string;
  item_name: string;
  quantity: number;
  unit_cost: number;
  unit_sale_price: number;
  vat_rate: number;
  total_cost: number;
  total_sale: number;
  gross_profit: number;
  installment_count: number;
  sale_type: string;
  notes: string;
  auto_source_key: string;
  is_auto_record: boolean;
};

type EquipmentIssueDetailResponse = {
  entry: EquipmentIssueEntry;
};

type EquipmentIssuesManagementResponse = {
  total_entries: number;
  entries: EquipmentIssueEntry[];
};

type BoxReturnEntry = {
  id: number;
  personnel_id: number;
  personnel_label: string;
  return_date: string;
  quantity: number;
  condition_status: string;
  payout_amount: number;
  waived: boolean;
  notes: string;
};

type BoxReturnDetailResponse = {
  entry: BoxReturnEntry;
};

type BoxReturnsManagementResponse = {
  total_entries: number;
  entries: BoxReturnEntry[];
};

type EquipmentFormOptions = {
  personnel: Array<{ id: number; label: string }>;
  issue_items: string[];
  sale_type_options: string[];
  return_condition_options: string[];
  installment_count_options: number[];
  item_defaults: Record<
    string,
    {
      default_unit_cost: number;
      default_sale_price: number;
      default_installment_count: number;
      default_vat_rate: number;
    }
  >;
  selected_personnel_id: number | null;
  selected_item: string;
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

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

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

export function EquipmentManagementWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<EquipmentFormOptions | null>(null);

  const [issueEntries, setIssueEntries] = useState<EquipmentIssueEntry[]>([]);
  const [issueTotalEntries, setIssueTotalEntries] = useState(0);
  const [issueListLoading, setIssueListLoading] = useState(true);
  const [issueListError, setIssueListError] = useState("");
  const [issueSaveError, setIssueSaveError] = useState("");
  const [issueSaveSuccess, setIssueSaveSuccess] = useState("");
  const [issueSearchInput, setIssueSearchInput] = useState("");
  const deferredIssueSearch = useDeferredValue(issueSearchInput);
  const [issueFilterPersonnelId, setIssueFilterPersonnelId] = useState<number | "">("");
  const [issueFilterItemName, setIssueFilterItemName] = useState("");
  const [selectedIssueId, setSelectedIssueId] = useState<number | null>(null);
  const [issueDetailLoading, setIssueDetailLoading] = useState(false);

  const [editIssuePersonnelId, setEditIssuePersonnelId] = useState<number | "">("");
  const [editIssueDate, setEditIssueDate] = useState("");
  const [editItemName, setEditItemName] = useState("");
  const [editQuantity, setEditQuantity] = useState("1");
  const [editUnitCost, setEditUnitCost] = useState("0");
  const [editUnitSalePrice, setEditUnitSalePrice] = useState("0");
  const [editInstallmentCount, setEditInstallmentCount] = useState("1");
  const [editSaleType, setEditSaleType] = useState("Satış");
  const [editIssueNotes, setEditIssueNotes] = useState("");
  const [editIssueIsAuto, setEditIssueIsAuto] = useState(false);

  const [boxEntries, setBoxEntries] = useState<BoxReturnEntry[]>([]);
  const [boxTotalEntries, setBoxTotalEntries] = useState(0);
  const [boxListLoading, setBoxListLoading] = useState(true);
  const [boxListError, setBoxListError] = useState("");
  const [boxSaveError, setBoxSaveError] = useState("");
  const [boxSaveSuccess, setBoxSaveSuccess] = useState("");
  const [boxSearchInput, setBoxSearchInput] = useState("");
  const deferredBoxSearch = useDeferredValue(boxSearchInput);
  const [boxFilterPersonnelId, setBoxFilterPersonnelId] = useState<number | "">("");
  const [selectedBoxId, setSelectedBoxId] = useState<number | null>(null);
  const [boxDetailLoading, setBoxDetailLoading] = useState(false);

  const [editBoxPersonnelId, setEditBoxPersonnelId] = useState<number | "">("");
  const [editReturnDate, setEditReturnDate] = useState("");
  const [editReturnQuantity, setEditReturnQuantity] = useState("1");
  const [editConditionStatus, setEditConditionStatus] = useState("Temiz");
  const [editPayoutAmount, setEditPayoutAmount] = useState("0");
  const [editBoxNotes, setEditBoxNotes] = useState("");

  async function loadOptions() {
    const response = await apiFetch("/equipment/form-options");
    if (!response.ok) {
      throw new Error("Ekipman referans verileri yuklenemedi.");
    }
    const payload = (await response.json()) as EquipmentFormOptions;
    setOptions(payload);
    if (!issueFilterPersonnelId && payload.selected_personnel_id) {
      setIssueFilterPersonnelId(payload.selected_personnel_id);
    }
    if (!boxFilterPersonnelId && payload.selected_personnel_id) {
      setBoxFilterPersonnelId(payload.selected_personnel_id);
    }
  }

  async function loadIssueEntries() {
    setIssueListLoading(true);
    setIssueListError("");
    try {
      const query = new URLSearchParams();
      query.set("limit", "180");
      if (typeof issueFilterPersonnelId === "number") {
        query.set("personnel_id", String(issueFilterPersonnelId));
      }
      if (issueFilterItemName) {
        query.set("item_name", issueFilterItemName);
      }
      if (deferredIssueSearch.trim()) {
        query.set("search", deferredIssueSearch.trim());
      }
      const response = await apiFetch(`/equipment/issues?${query.toString()}`);
      if (!response.ok) {
        throw new Error("Ekipman zimmet listesi yuklenemedi.");
      }
      const payload = (await response.json()) as EquipmentIssuesManagementResponse;
      setIssueEntries(payload.entries);
      setIssueTotalEntries(payload.total_entries);
      setSelectedIssueId((current) => {
        if (!payload.entries.length) {
          return null;
        }
        if (current && payload.entries.some((entry) => entry.id === current)) {
          return current;
        }
        return payload.entries[0].id;
      });
    } catch (error) {
      setIssueListError(
        error instanceof Error ? error.message : "Ekipman zimmet listesi yuklenemedi.",
      );
      setIssueEntries([]);
      setIssueTotalEntries(0);
      setSelectedIssueId(null);
    } finally {
      setIssueListLoading(false);
    }
  }

  async function loadIssueDetail(entryId: number) {
    setIssueDetailLoading(true);
    setIssueSaveError("");
    setIssueSaveSuccess("");
    try {
      const response = await apiFetch(`/equipment/issues/${entryId}`);
      if (!response.ok) {
        throw new Error("Zimmet detayi yuklenemedi.");
      }
      const payload = (await response.json()) as EquipmentIssueDetailResponse;
      const entry = payload.entry;
      setEditIssuePersonnelId(entry.personnel_id);
      setEditIssueDate(entry.issue_date);
      setEditItemName(entry.item_name);
      setEditQuantity(String(entry.quantity ?? 1));
      setEditUnitCost(String(entry.unit_cost ?? 0));
      setEditUnitSalePrice(String(entry.unit_sale_price ?? 0));
      setEditInstallmentCount(String(entry.installment_count ?? 1));
      setEditSaleType(entry.sale_type);
      setEditIssueNotes(entry.notes ?? "");
      setEditIssueIsAuto(entry.is_auto_record);
    } catch (error) {
      setIssueSaveError(error instanceof Error ? error.message : "Zimmet detayi yuklenemedi.");
    } finally {
      setIssueDetailLoading(false);
    }
  }

  async function loadBoxEntries() {
    setBoxListLoading(true);
    setBoxListError("");
    try {
      const query = new URLSearchParams();
      query.set("limit", "180");
      if (typeof boxFilterPersonnelId === "number") {
        query.set("personnel_id", String(boxFilterPersonnelId));
      }
      if (deferredBoxSearch.trim()) {
        query.set("search", deferredBoxSearch.trim());
      }
      const response = await apiFetch(`/equipment/box-returns?${query.toString()}`);
      if (!response.ok) {
        throw new Error("Box geri alım listesi yuklenemedi.");
      }
      const payload = (await response.json()) as BoxReturnsManagementResponse;
      setBoxEntries(payload.entries);
      setBoxTotalEntries(payload.total_entries);
      setSelectedBoxId((current) => {
        if (!payload.entries.length) {
          return null;
        }
        if (current && payload.entries.some((entry) => entry.id === current)) {
          return current;
        }
        return payload.entries[0].id;
      });
    } catch (error) {
      setBoxListError(
        error instanceof Error ? error.message : "Box geri alım listesi yuklenemedi.",
      );
      setBoxEntries([]);
      setBoxTotalEntries(0);
      setSelectedBoxId(null);
    } finally {
      setBoxListLoading(false);
    }
  }

  async function loadBoxDetail(entryId: number) {
    setBoxDetailLoading(true);
    setBoxSaveError("");
    setBoxSaveSuccess("");
    try {
      const response = await apiFetch(`/equipment/box-returns/${entryId}`);
      if (!response.ok) {
        throw new Error("Box geri alım detayi yuklenemedi.");
      }
      const payload = (await response.json()) as BoxReturnDetailResponse;
      const entry = payload.entry;
      setEditBoxPersonnelId(entry.personnel_id);
      setEditReturnDate(entry.return_date);
      setEditReturnQuantity(String(entry.quantity ?? 1));
      setEditConditionStatus(entry.condition_status);
      setEditPayoutAmount(String(entry.payout_amount ?? 0));
      setEditBoxNotes(entry.notes ?? "");
    } catch (error) {
      setBoxSaveError(
        error instanceof Error ? error.message : "Box geri alım detayi yuklenemedi.",
      );
    } finally {
      setBoxDetailLoading(false);
    }
  }

  useEffect(() => {
    void loadOptions();
  }, []);

  useEffect(() => {
    if (!options) {
      return;
    }
    void loadIssueEntries();
  }, [options, deferredIssueSearch, issueFilterItemName, issueFilterPersonnelId]);

  useEffect(() => {
    if (!options) {
      return;
    }
    void loadBoxEntries();
  }, [options, deferredBoxSearch, boxFilterPersonnelId]);

  useEffect(() => {
    if (selectedIssueId == null) {
      return;
    }
    void loadIssueDetail(selectedIssueId);
  }, [selectedIssueId]);

  useEffect(() => {
    if (selectedBoxId == null) {
      return;
    }
    void loadBoxDetail(selectedBoxId);
  }, [selectedBoxId]);

  const selectedIssue = useMemo(
    () => issueEntries.find((entry) => entry.id === selectedIssueId) ?? null,
    [issueEntries, selectedIssueId],
  );

  const selectedBox = useMemo(
    () => boxEntries.find((entry) => entry.id === selectedBoxId) ?? null,
    [boxEntries, selectedBoxId],
  );

  async function handleIssueSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedIssueId || typeof editIssuePersonnelId !== "number") {
      setIssueSaveError("Duzenlenecek zimmet kaydini seç.");
      return;
    }
    setIssueSaveError("");
    setIssueSaveSuccess("");
    const response = await apiFetch(`/equipment/issues/${selectedIssueId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personnel_id: editIssuePersonnelId,
        issue_date: editIssueDate,
        item_name: editItemName,
        quantity: Number(editQuantity || 0),
        unit_cost: Number(editUnitCost || 0),
        unit_sale_price: Number(editUnitSalePrice || 0),
        installment_count: Number(editInstallmentCount || 1),
        sale_type: editSaleType,
        notes: editIssueNotes,
      }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setIssueSaveError(payload?.detail || "Zimmet kaydı güncellenemedi.");
      return;
    }
    setIssueSaveSuccess(payload?.message || "Zimmet kaydı güncellendi.");
    startTransition(() => {
      router.refresh();
    });
    await loadIssueEntries();
    await loadIssueDetail(selectedIssueId);
  }

  async function handleIssueDelete() {
    if (!selectedIssueId) {
      setIssueSaveError("Silinecek zimmet kaydini seç.");
      return;
    }
    setIssueSaveError("");
    setIssueSaveSuccess("");
    const response = await apiFetch(`/equipment/issues/${selectedIssueId}`, {
      method: "DELETE",
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setIssueSaveError(payload?.detail || "Zimmet kaydı silinemedi.");
      return;
    }
    setIssueSaveSuccess(payload?.message || "Zimmet kaydı silindi.");
    startTransition(() => {
      router.refresh();
    });
    await loadIssueEntries();
  }

  async function handleBoxSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedBoxId || typeof editBoxPersonnelId !== "number") {
      setBoxSaveError("Duzenlenecek box kaydini seç.");
      return;
    }
    setBoxSaveError("");
    setBoxSaveSuccess("");
    const response = await apiFetch(`/equipment/box-returns/${selectedBoxId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personnel_id: editBoxPersonnelId,
        return_date: editReturnDate,
        quantity: Number(editReturnQuantity || 0),
        condition_status: editConditionStatus,
        payout_amount: Number(editPayoutAmount || 0),
        notes: editBoxNotes,
      }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setBoxSaveError(payload?.detail || "Box geri alım kaydı güncellenemedi.");
      return;
    }
    setBoxSaveSuccess(payload?.message || "Box geri alım kaydı güncellendi.");
    startTransition(() => {
      router.refresh();
    });
    await loadBoxEntries();
    await loadBoxDetail(selectedBoxId);
  }

  async function handleBoxDelete() {
    if (!selectedBoxId) {
      setBoxSaveError("Silinecek box kaydini seç.");
      return;
    }
    setBoxSaveError("");
    setBoxSaveSuccess("");
    const response = await apiFetch(`/equipment/box-returns/${selectedBoxId}`, {
      method: "DELETE",
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setBoxSaveError(payload?.detail || "Box geri alım kaydı silinemedi.");
      return;
    }
    setBoxSaveSuccess(payload?.message || "Box geri alım kaydı silindi.");
    startTransition(() => {
      router.refresh();
    });
    await loadBoxEntries();
  }

  return (
    <div style={{ display: "grid", gap: "16px" }}>
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
          <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Zimmet Yonetimi</h2>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
            Zimmet kayıtlarını filtrele, seç, güncelle ve bağlı taksitleriyle temizle.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(320px, 1.05fr) minmax(320px, 0.95fr)",
            gap: "16px",
            alignItems: "start",
          }}
        >
          <div style={{ display: "grid", gap: "14px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(180px, 0.9fr) minmax(180px, 0.9fr) minmax(220px, 1.2fr)",
                gap: "12px",
              }}
            >
              <select
                value={issueFilterPersonnelId}
                onChange={(event) => {
                  const value = event.target.value;
                  setIssueFilterPersonnelId(value ? Number(value) : "");
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
                value={issueFilterItemName}
                onChange={(event) => setIssueFilterItemName(event.target.value)}
                style={fieldStyle}
              >
                <option value="">Tüm kalemler</option>
                {options?.issue_items.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
              <input
                value={issueSearchInput}
                onChange={(event) => setIssueSearchInput(event.target.value)}
                placeholder="Personel, kalem veya not ara"
                style={fieldStyle}
              />
            </div>

            <div
              style={{
                padding: "14px 16px",
                borderRadius: "18px",
                border: "1px solid var(--line)",
                background: "rgba(255, 255, 255, 0.86)",
                color: "var(--muted)",
                fontWeight: 700,
              }}
            >
              Toplam eslesen zimmet: {issueTotalEntries}
            </div>

            {issueListLoading ? (
              <div
                style={{
                  padding: "18px",
                  borderRadius: "18px",
                  background: "rgba(15, 95, 215, 0.06)",
                  color: "var(--muted)",
                }}
              >
                Zimmet listesi yükleniyor...
              </div>
            ) : issueListError ? (
              <div
                style={{
                  padding: "18px",
                  borderRadius: "18px",
                  border: "1px solid rgba(205, 70, 66, 0.18)",
                  background: "rgba(205, 70, 66, 0.08)",
                  color: "#b53632",
                }}
              >
                {issueListError}
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gap: "10px",
                  maxHeight: "360px",
                  overflow: "auto",
                  paddingRight: "4px",
                }}
              >
                {issueEntries.map((entry) => {
                  const selected = entry.id === selectedIssueId;
                  return (
                    <button
                      key={entry.id}
                      type="button"
                      onClick={() => setSelectedIssueId(entry.id)}
                      style={{
                        textAlign: "left",
                        display: "grid",
                        gap: "8px",
                        padding: "16px",
                        borderRadius: "18px",
                        border: selected
                          ? "1px solid rgba(15, 95, 215, 0.35)"
                          : "1px solid var(--line)",
                        background: selected
                          ? "rgba(15, 95, 215, 0.08)"
                          : "rgba(255, 255, 255, 0.88)",
                        cursor: "pointer",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          alignItems: "center",
                        }}
                      >
                        <strong>{entry.item_name}</strong>
                        <span style={pill(entry.is_auto_record ? "warn" : "accent")}>
                          {entry.is_auto_record ? "Otomatik" : entry.sale_type}
                        </span>
                      </div>
                      <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
                        {entry.personnel_label}
                      </div>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          color: "var(--muted)",
                          fontSize: "0.9rem",
                        }}
                      >
                        <span>{entry.issue_date}</span>
                        <span>{entry.quantity} adet</span>
                        <span>{formatCurrency(entry.total_sale)}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <form onSubmit={handleIssueSubmit} style={{ display: "grid", gap: "14px" }}>
            {selectedIssue ? (
              <div
                style={{
                  display: "grid",
                  gap: "14px",
                  padding: "18px",
                  borderRadius: "20px",
                  border: "1px solid var(--line)",
                  background: "rgba(255, 255, 255, 0.9)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "12px",
                  }}
                >
                  <div>
                    <div
                      style={{
                        color: "var(--muted)",
                        fontSize: "0.78rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        fontWeight: 800,
                      }}
                    >
                      Seçili Zimmet
                    </div>
                    <h3 style={{ margin: "6px 0 0" }}>{selectedIssue.item_name}</h3>
                  </div>
                  <span style={pill(selectedIssue.is_auto_record ? "warn" : "muted")}>
                    {selectedIssue.is_auto_record ? "Otomatik kayıt" : "Manuel kayıt"}
                  </span>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                    gap: "12px",
                  }}
                >
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Personel</span>
                    <select
                      value={editIssuePersonnelId}
                      onChange={(event) => setEditIssuePersonnelId(Number(event.target.value))}
                      style={fieldStyle}
                      disabled={editIssueIsAuto}
                    >
                      {options?.personnel.map((person) => (
                        <option key={person.id} value={person.id}>
                          {person.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Tarih</span>
                    <input
                      type="date"
                      value={editIssueDate}
                      onChange={(event) => setEditIssueDate(event.target.value)}
                      style={fieldStyle}
                      disabled={editIssueIsAuto}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Kalem</span>
                    <select
                      value={editItemName}
                      onChange={(event) => setEditItemName(event.target.value)}
                      style={fieldStyle}
                      disabled={editIssueIsAuto}
                    >
                      {options?.issue_items.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Satış Tipi</span>
                    <select
                      value={editSaleType}
                      onChange={(event) => setEditSaleType(event.target.value)}
                      style={fieldStyle}
                      disabled={editIssueIsAuto}
                    >
                      {options?.sale_type_options.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Adet</span>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      value={editQuantity}
                      onChange={(event) => setEditQuantity(event.target.value)}
                      style={fieldStyle}
                      disabled={editIssueIsAuto}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Birim Maliyet</span>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={editUnitCost}
                      onChange={(event) => setEditUnitCost(event.target.value)}
                      style={fieldStyle}
                      disabled={editIssueIsAuto}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Birim Satış</span>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={editUnitSalePrice}
                      onChange={(event) => setEditUnitSalePrice(event.target.value)}
                      style={fieldStyle}
                      disabled={editIssueIsAuto}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Taksit</span>
                    <select
                      value={editInstallmentCount}
                      onChange={(event) => setEditInstallmentCount(event.target.value)}
                      style={fieldStyle}
                      disabled={editIssueIsAuto || editSaleType !== "Satış"}
                    >
                      {options?.installment_count_options.map((count) => (
                        <option key={count} value={count}>
                          {count}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Not</span>
                  <textarea
                    value={editIssueNotes}
                    onChange={(event) => setEditIssueNotes(event.target.value)}
                    rows={3}
                    style={{ ...fieldStyle, resize: "vertical" }}
                    disabled={editIssueIsAuto}
                  />
                </label>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                    gap: "12px",
                    color: "var(--muted)",
                    fontSize: "0.92rem",
                  }}
                >
                  <div>
                    <div>Toplam Maliyet</div>
                    <strong style={{ color: "var(--text)" }}>{formatCurrency(selectedIssue.total_cost)}</strong>
                  </div>
                  <div>
                    <div>Toplam Satış</div>
                    <strong style={{ color: "var(--text)" }}>{formatCurrency(selectedIssue.total_sale)}</strong>
                  </div>
                  <div>
                    <div>Brut Kar</div>
                    <strong style={{ color: "var(--text)" }}>{formatCurrency(selectedIssue.gross_profit)}</strong>
                  </div>
                  <div>
                    <div>KDV</div>
                    <strong style={{ color: "var(--text)" }}>%{selectedIssue.vat_rate}</strong>
                  </div>
                </div>

                {(issueSaveError || issueSaveSuccess) && (
                  <div
                    style={{
                      padding: "14px 16px",
                      borderRadius: "16px",
                      border: issueSaveError
                        ? "1px solid rgba(205, 70, 66, 0.18)"
                        : "1px solid rgba(35, 148, 94, 0.18)",
                      background: issueSaveError
                        ? "rgba(205, 70, 66, 0.08)"
                        : "rgba(35, 148, 94, 0.08)",
                      color: issueSaveError ? "#b53632" : "#1d7b4d",
                      fontWeight: 700,
                    }}
                  >
                    {issueSaveError || issueSaveSuccess}
                  </div>
                )}

                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  <button
                    type="submit"
                    disabled={isPending || editIssueIsAuto || issueDetailLoading}
                    style={{
                      border: "none",
                      borderRadius: "16px",
                      padding: "14px 16px",
                      background: "linear-gradient(135deg, #0f5fd7, #1a73e8)",
                      color: "white",
                      fontWeight: 800,
                      cursor: "pointer",
                    }}
                  >
                    {isPending ? "Kaydediliyor..." : "Zimmeti Güncelle"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleIssueDelete()}
                    disabled={isPending || editIssueIsAuto}
                    style={{
                      borderRadius: "16px",
                      padding: "14px 16px",
                      border: "1px solid rgba(205, 70, 66, 0.18)",
                      background: "rgba(205, 70, 66, 0.08)",
                      color: "#b53632",
                      fontWeight: 800,
                      cursor: "pointer",
                    }}
                  >
                    Zimmeti Sil
                  </button>
                </div>
              </div>
            ) : (
              <div
                style={{
                  padding: "24px",
                  borderRadius: "20px",
                  border: "1px dashed rgba(15, 95, 215, 0.22)",
                  color: "var(--muted)",
                  background: "rgba(255, 255, 255, 0.76)",
                }}
              >
                Düzenlemek için sol taraftan bir zimmet kaydı seç.
              </div>
            )}
          </form>
        </div>
      </section>

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
          <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Box Geri Alım Yonetimi</h2>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
            İade kayıtlarını filtrele, seç, güncelle ve ödeme durumuyla takip et.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(320px, 1.05fr) minmax(320px, 0.95fr)",
            gap: "16px",
            alignItems: "start",
          }}
        >
          <div style={{ display: "grid", gap: "14px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(180px, 0.95fr) minmax(220px, 1.25fr)",
                gap: "12px",
              }}
            >
              <select
                value={boxFilterPersonnelId}
                onChange={(event) => {
                  const value = event.target.value;
                  setBoxFilterPersonnelId(value ? Number(value) : "");
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
              <input
                value={boxSearchInput}
                onChange={(event) => setBoxSearchInput(event.target.value)}
                placeholder="Personel, durum veya not ara"
                style={fieldStyle}
              />
            </div>

            <div
              style={{
                padding: "14px 16px",
                borderRadius: "18px",
                border: "1px solid var(--line)",
                background: "rgba(255, 255, 255, 0.86)",
                color: "var(--muted)",
                fontWeight: 700,
              }}
            >
              Toplam eslesen box iadesi: {boxTotalEntries}
            </div>

            {boxListLoading ? (
              <div
                style={{
                  padding: "18px",
                  borderRadius: "18px",
                  background: "rgba(15, 95, 215, 0.06)",
                  color: "var(--muted)",
                }}
              >
                Box geri alım listesi yükleniyor...
              </div>
            ) : boxListError ? (
              <div
                style={{
                  padding: "18px",
                  borderRadius: "18px",
                  border: "1px solid rgba(205, 70, 66, 0.18)",
                  background: "rgba(205, 70, 66, 0.08)",
                  color: "#b53632",
                }}
              >
                {boxListError}
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gap: "10px",
                  maxHeight: "320px",
                  overflow: "auto",
                  paddingRight: "4px",
                }}
              >
                {boxEntries.map((entry) => {
                  const selected = entry.id === selectedBoxId;
                  return (
                    <button
                      key={entry.id}
                      type="button"
                      onClick={() => setSelectedBoxId(entry.id)}
                      style={{
                        textAlign: "left",
                        display: "grid",
                        gap: "8px",
                        padding: "16px",
                        borderRadius: "18px",
                        border: selected
                          ? "1px solid rgba(15, 95, 215, 0.35)"
                          : "1px solid var(--line)",
                        background: selected
                          ? "rgba(15, 95, 215, 0.08)"
                          : "rgba(255, 255, 255, 0.88)",
                        cursor: "pointer",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: "12px",
                        }}
                      >
                        <strong>{entry.personnel_label}</strong>
                        <span style={pill(entry.waived ? "muted" : "accent")}>
                          {entry.waived ? "Talep edilmedi" : entry.condition_status}
                        </span>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          color: "var(--muted)",
                          fontSize: "0.9rem",
                        }}
                      >
                        <span>{entry.return_date}</span>
                        <span>{entry.quantity} adet</span>
                        <span>{formatCurrency(entry.payout_amount)}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <form onSubmit={handleBoxSubmit} style={{ display: "grid", gap: "14px" }}>
            {selectedBox ? (
              <div
                style={{
                  display: "grid",
                  gap: "14px",
                  padding: "18px",
                  borderRadius: "20px",
                  border: "1px solid var(--line)",
                  background: "rgba(255, 255, 255, 0.9)",
                }}
              >
                <div>
                  <div
                    style={{
                      color: "var(--muted)",
                      fontSize: "0.78rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      fontWeight: 800,
                    }}
                  >
                    Seçili Box Iadesi
                  </div>
                  <h3 style={{ margin: "6px 0 0" }}>{selectedBox.personnel_label}</h3>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                    gap: "12px",
                  }}
                >
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Personel</span>
                    <select
                      value={editBoxPersonnelId}
                      onChange={(event) => setEditBoxPersonnelId(Number(event.target.value))}
                      style={fieldStyle}
                    >
                      {options?.personnel.map((person) => (
                        <option key={person.id} value={person.id}>
                          {person.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>İade Tarihi</span>
                    <input
                      type="date"
                      value={editReturnDate}
                      onChange={(event) => setEditReturnDate(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Adet</span>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      value={editReturnQuantity}
                      onChange={(event) => setEditReturnQuantity(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Durum</span>
                    <select
                      value={editConditionStatus}
                      onChange={(event) => setEditConditionStatus(event.target.value)}
                      style={fieldStyle}
                    >
                      {options?.return_condition_options.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Ödeme Tutarı</span>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={editPayoutAmount}
                      onChange={(event) => setEditPayoutAmount(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                </div>

                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Not</span>
                  <textarea
                    value={editBoxNotes}
                    onChange={(event) => setEditBoxNotes(event.target.value)}
                    rows={3}
                    style={{ ...fieldStyle, resize: "vertical" }}
                  />
                </label>

                {(boxSaveError || boxSaveSuccess) && (
                  <div
                    style={{
                      padding: "14px 16px",
                      borderRadius: "16px",
                      border: boxSaveError
                        ? "1px solid rgba(205, 70, 66, 0.18)"
                        : "1px solid rgba(35, 148, 94, 0.18)",
                      background: boxSaveError
                        ? "rgba(205, 70, 66, 0.08)"
                        : "rgba(35, 148, 94, 0.08)",
                      color: boxSaveError ? "#b53632" : "#1d7b4d",
                      fontWeight: 700,
                    }}
                  >
                    {boxSaveError || boxSaveSuccess}
                  </div>
                )}

                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  <button
                    type="submit"
                    disabled={isPending || boxDetailLoading}
                    style={{
                      border: "none",
                      borderRadius: "16px",
                      padding: "14px 16px",
                      background: "linear-gradient(135deg, #10203c, #1d315b)",
                      color: "white",
                      fontWeight: 800,
                      cursor: "pointer",
                    }}
                  >
                    {isPending ? "Kaydediliyor..." : "Box Kaydini Güncelle"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleBoxDelete()}
                    disabled={isPending}
                    style={{
                      borderRadius: "16px",
                      padding: "14px 16px",
                      border: "1px solid rgba(205, 70, 66, 0.18)",
                      background: "rgba(205, 70, 66, 0.08)",
                      color: "#b53632",
                      fontWeight: 800,
                      cursor: "pointer",
                    }}
                  >
                    Box Kaydini Sil
                  </button>
                </div>
              </div>
            ) : (
              <div
                style={{
                  padding: "24px",
                  borderRadius: "20px",
                  border: "1px dashed rgba(15, 95, 215, 0.22)",
                  color: "var(--muted)",
                  background: "rgba(255, 255, 255, 0.76)",
                }}
              >
                Düzenlemek için sol taraftan bir box geri alım kaydı seç.
              </div>
            )}
          </form>
        </div>
      </section>
    </div>
  );
}
