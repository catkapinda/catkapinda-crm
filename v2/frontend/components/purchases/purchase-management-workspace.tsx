"use client";

import type { CSSProperties, FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type PurchaseEntry = {
  id: number;
  purchase_date: string;
  item_name: string;
  quantity: number;
  total_invoice_amount: number;
  unit_cost: number;
  supplier: string;
  invoice_no: string;
  notes: string;
};

type PurchasesManagementResponse = {
  total_entries: number;
  entries: PurchaseEntry[];
};

type PurchaseDetailResponse = {
  entry: PurchaseEntry;
};

type PurchasesFormOptions = {
  item_options: string[];
  selected_item: string;
};

const fieldStyle: CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: "12px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.9)",
  color: "var(--text)",
  font: "inherit",
  fontSize: "0.92rem",
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

export function PurchaseManagementWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<PurchasesFormOptions | null>(null);
  const [entries, setEntries] = useState<PurchaseEntry[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const deferredSearch = useDeferredValue(searchInput);
  const [filterItemName, setFilterItemName] = useState("");
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

  const [editPurchaseDate, setEditPurchaseDate] = useState("");
  const [editItemName, setEditItemName] = useState("");
  const [editQuantity, setEditQuantity] = useState("1");
  const [editTotalInvoiceAmount, setEditTotalInvoiceAmount] = useState("");
  const [editSupplier, setEditSupplier] = useState("");
  const [editInvoiceNo, setEditInvoiceNo] = useState("");
  const [editNotes, setEditNotes] = useState("");

  async function loadOptions() {
    const response = await apiFetch("/purchases/form-options");
    if (!response.ok) {
      throw new Error("Satın alma referans verileri yüklenemedi.");
    }
    const payload = (await response.json()) as PurchasesFormOptions;
    setOptions(payload);
  }

  async function loadEntries() {
    setListLoading(true);
    setListError("");
    try {
      const query = new URLSearchParams();
      query.set("limit", "180");
      if (filterItemName) {
        query.set("item_name", filterItemName);
      }
      if (deferredSearch.trim()) {
        query.set("search", deferredSearch.trim());
      }
      const response = await apiFetch(`/purchases/records?${query.toString()}`);
      if (!response.ok) {
        throw new Error("Satın alma listesi yüklenemedi.");
      }
      const payload = (await response.json()) as PurchasesManagementResponse;
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
      setListError(error instanceof Error ? error.message : "Satın alma listesi yüklenemedi.");
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
      const response = await apiFetch(`/purchases/records/${entryId}`);
      if (!response.ok) {
        throw new Error("Satın alma detayı yüklenemedi.");
      }
      const payload = (await response.json()) as PurchaseDetailResponse;
      const entry = payload.entry;
      setEditPurchaseDate(entry.purchase_date);
      setEditItemName(entry.item_name);
      setEditQuantity(String(entry.quantity ?? 1));
      setEditTotalInvoiceAmount(String(entry.total_invoice_amount ?? 0));
      setEditSupplier(entry.supplier ?? "");
      setEditInvoiceNo(entry.invoice_no ?? "");
      setEditNotes(entry.notes ?? "");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Satın alma detayı yüklenemedi.");
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
  }, [options, deferredSearch, filterItemName]);

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
  const hasSelectedEntry = Boolean(selectedEntry);

  const unitCostPreview = useMemo(() => {
    const qty = Number(editQuantity || 0);
    const total = Number(editTotalInvoiceAmount || 0);
    if (qty <= 0 || total <= 0) {
      return formatCurrency(0);
    }
    return formatCurrency(total / qty);
  }, [editQuantity, editTotalInvoiceAmount]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEntryId) {
      setSaveError("Düzenlenecek satın alma kaydını seç.");
      return;
    }

    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/purchases/records/${selectedEntryId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        purchase_date: editPurchaseDate,
        item_name: editItemName,
        quantity: Number(editQuantity || 0),
        total_invoice_amount: Number(editTotalInvoiceAmount || 0),
        supplier: editSupplier,
        invoice_no: editInvoiceNo,
        notes: editNotes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSaveError(payload?.detail || "Satın alma kaydı güncellenemedi.");
      return;
    }

    setSaveSuccess(payload?.message || "Satın alma kaydı güncellendi.");
    startTransition(() => {
      router.refresh();
    });
    await loadEntries();
    await loadEntryDetail(selectedEntryId);
  }

  async function handleDelete() {
    if (!selectedEntryId) {
      setSaveError("Silinecek satın alma kaydını seç.");
      return;
    }
    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/purchases/records/${selectedEntryId}`, {
      method: "DELETE",
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSaveError(payload?.detail || "Satın alma kaydı silinemedi.");
      return;
    }
    setSaveSuccess(payload?.message || "Satın alma kaydı silindi.");
    startTransition(() => {
      router.refresh();
    });
    await loadEntries();
  }

  return (
    <section
      style={{
        display: "grid",
        gap: "12px",
        padding: "18px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
      }}
    >
      <div>
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Satın Alma Kayıt Yönetimi</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Fatura kayıtlarını filtrele, seç, güncelle ve aynı panelden temizle.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: hasSelectedEntry
            ? "minmax(320px, 1.05fr) minmax(320px, 0.95fr)"
            : "minmax(0, 1fr)",
          gap: "12px",
          alignItems: "start",
        }}
      >
        <div style={{ display: "grid", gap: "10px" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "12px",
            }}
          >
            <select value={filterItemName} onChange={(event) => setFilterItemName(event.target.value)} style={fieldStyle}>
              <option value="">Tüm Ürünler</option>
              {options?.item_options.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Ürün, tedarikçi, fatura no veya not ara"
              style={fieldStyle}
            />
          </div>

          <div
            style={{
              padding: "10px 12px",
              borderRadius: "14px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.86)",
              color: "var(--muted)",
              fontWeight: 700,
              fontSize: "0.9rem",
            }}
          >
            Toplam eşleşen fatura: {totalEntries}
          </div>

          {listLoading ? (
            <div
              style={{
                padding: "12px 14px",
                borderRadius: "14px",
                background: "rgba(15, 95, 215, 0.06)",
                color: "var(--muted)",
                fontSize: "0.9rem",
              }}
            >
              Satın alma listesi yükleniyor...
            </div>
          ) : listError ? (
            <div
              style={{
                padding: "12px 14px",
                borderRadius: "14px",
                border: "1px solid rgba(205, 70, 66, 0.14)",
                background: "rgba(205, 70, 66, 0.08)",
                color: "#b53632",
                fontWeight: 700,
                fontSize: "0.9rem",
              }}
            >
              {listError}
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gap: "8px",
                maxHeight: "560px",
                overflowY: "auto",
                paddingRight: "4px",
              }}
            >
              {entries.map((entry) => {
                const isActive = entry.id === selectedEntryId;
                return (
                  <button
                    key={entry.id}
                    type="button"
                    onClick={() => setSelectedEntryId(entry.id)}
                    style={{
                      textAlign: "left",
                      padding: "10px 12px",
                      borderRadius: "14px",
                      border: isActive ? "1px solid rgba(15, 95, 215, 0.22)" : "1px solid var(--line)",
                      background: isActive ? "rgba(15, 95, 215, 0.08)" : "rgba(255, 255, 255, 0.88)",
                      cursor: "pointer",
                      display: "grid",
                      gap: "6px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                      <strong
                        style={{
                          fontSize: "0.92rem",
                          lineHeight: 1.3,
                          display: "-webkit-box",
                          WebkitLineClamp: 1,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                          minWidth: 0,
                        }}
                      >
                        {entry.item_name}
                      </strong>
                      <span style={{ color: "var(--muted)", fontWeight: 700, fontSize: "0.78rem", whiteSpace: "nowrap" }}>
                        {entry.purchase_date}
                      </span>
                    </div>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                        gap: "8px",
                        color: "var(--muted)",
                        fontSize: "0.8rem",
                      }}
                    >
                      <span>{entry.quantity} adet</span>
                      <span>{formatCurrency(entry.total_invoice_amount)}</span>
                      <span
                        style={{
                          display: "-webkit-box",
                          WebkitLineClamp: 1,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {entry.supplier || "Tedarikçi yok"}
                      </span>
                    </div>
                  </button>
                );
              })}

              {!entries.length && (
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: "14px",
                    border: "1px dashed rgba(15, 95, 215, 0.25)",
                    background: "rgba(255, 255, 255, 0.7)",
                    color: "var(--muted)",
                    fontSize: "0.9rem",
                  }}
                >
                  Bu filtrede satın alma kaydı yok.
                </div>
              )}
            </div>
          )}
        </div>

        {selectedEntry ? (
          <form
            onSubmit={handleSubmit}
            style={{
              display: "grid",
              gap: "10px",
              padding: "14px",
              borderRadius: "18px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.86)",
            }}
          >
          <div>
            <h3 style={{ margin: 0, fontSize: "1.05rem" }}>Seçili Kayıt</h3>
            <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>
              Satın alma tarihini, fatura tutarını ve tedarikçi bilgisini burada güncelle.
            </p>
          </div>

          {selectedEntry && !detailLoading ? (
            <div
              style={{
                padding: "12px 14px",
                borderRadius: "14px",
                border: "1px solid var(--line)",
                background: "rgba(15, 95, 215, 0.04)",
                display: "grid",
                gap: "8px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                <strong style={{ fontSize: "0.95rem", lineHeight: 1.3 }}>{selectedEntry.item_name}</strong>
                <span style={{ color: "var(--muted)", fontWeight: 700, fontSize: "0.88rem" }}>{selectedEntry.purchase_date}</span>
              </div>
              <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "8px",
                  }}
                >
                <div>
                  <div style={{ fontSize: "0.76rem", color: "var(--muted)" }}>Adet</div>
                  <div style={{ marginTop: "4px", fontWeight: 700 }}>{selectedEntry.quantity} adet</div>
                </div>
                <div>
                  <div style={{ fontSize: "0.76rem", color: "var(--muted)" }}>Toplam Fatura</div>
                  <div style={{ marginTop: "4px", fontWeight: 700 }}>
                    {formatCurrency(selectedEntry.total_invoice_amount)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "0.76rem", color: "var(--muted)" }}>Tedarikçi</div>
                  <div style={{ marginTop: "4px", fontWeight: 700 }}>
                    {selectedEntry.supplier || "Tedarikçi yok"}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "0.76rem", color: "var(--muted)" }}>Fatura No</div>
                  <div style={{ marginTop: "4px", fontWeight: 700 }}>
                    {selectedEntry.invoice_no || "-"}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {detailLoading ? (
            <div
              style={{
                padding: "10px 12px",
                borderRadius: "12px",
                background: "rgba(15, 95, 215, 0.06)",
                color: "var(--muted)",
                fontSize: "0.9rem",
              }}
            >
              Satın alma detayı yükleniyor...
            </div>
          ) : selectedEntry ? (
            <>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "12px",
                }}
              >
                <label style={{ display: "grid", gap: "6px" }}>
                  <span style={{ fontWeight: 700 }}>Fatura Tarihi</span>
                  <input type="date" value={editPurchaseDate} onChange={(event) => setEditPurchaseDate(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "6px" }}>
                  <span style={{ fontWeight: 700 }}>Ürün</span>
                  <select value={editItemName} onChange={(event) => setEditItemName(event.target.value)} style={fieldStyle}>
                    {options?.item_options.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "6px" }}>
                  <span style={{ fontWeight: 700 }}>Adet</span>
                  <input type="number" min="1" step="1" value={editQuantity} onChange={(event) => setEditQuantity(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "6px" }}>
                  <span style={{ fontWeight: 700 }}>Toplam Fatura</span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min="0"
                    step="0.01"
                    value={editTotalInvoiceAmount}
                    onChange={(event) => setEditTotalInvoiceAmount(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "6px" }}>
                  <span style={{ fontWeight: 700 }}>Tedarikçi</span>
                  <input value={editSupplier} onChange={(event) => setEditSupplier(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "6px" }}>
                  <span style={{ fontWeight: 700 }}>Fatura No</span>
                  <input value={editInvoiceNo} onChange={(event) => setEditInvoiceNo(event.target.value)} style={fieldStyle} />
                </label>
              </div>

              <div
                style={{
                  padding: "10px 12px",
                  borderRadius: "14px",
                  border: "1px solid var(--line)",
                  background: "rgba(15, 95, 215, 0.05)",
                  color: "var(--muted)",
                  fontSize: "0.9rem",
                }}
              >
                <div style={{ fontWeight: 800, color: "var(--text)", marginBottom: "4px" }}>Birim Maliyet</div>
                {unitCostPreview}
              </div>

              <label style={{ display: "grid", gap: "6px" }}>
                <span style={{ fontWeight: 700 }}>Not</span>
                <textarea
                  value={editNotes}
                  onChange={(event) => setEditNotes(event.target.value)}
                  rows={2}
                  style={{ ...fieldStyle, resize: "vertical", minHeight: "72px" }}
                />
              </label>
            </>
          ) : (
            <div
              style={{
                padding: "10px 12px",
                borderRadius: "12px",
                border: "1px dashed rgba(15, 95, 215, 0.25)",
                background: "rgba(255, 255, 255, 0.7)",
                color: "var(--muted)",
                fontSize: "0.9rem",
              }}
            >
              Düzenleme için soldan bir satın alma kaydı seç.
            </div>
          )}

          {(saveError || saveSuccess) && (
            <div
              style={{
                padding: "10px 12px",
                borderRadius: "12px",
                border: saveError ? "1px solid rgba(205, 70, 66, 0.18)" : "1px solid rgba(35, 148, 94, 0.18)",
                background: saveError ? "rgba(205, 70, 66, 0.08)" : "rgba(35, 148, 94, 0.08)",
                color: saveError ? "#b53632" : "#1d7b4d",
                fontWeight: 700,
                fontSize: "0.9rem",
              }}
            >
              {saveError || saveSuccess}
            </div>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "10px",
            }}
          >
            <button
              type="submit"
              disabled={isPending || !selectedEntry}
              style={{
                border: "none",
                borderRadius: "12px",
                padding: "10px 14px",
                background: "linear-gradient(135deg, #0f5fd7, #1a73e8)",
                color: "white",
                fontWeight: 800,
                fontSize: "0.9rem",
                cursor: "pointer",
                boxShadow: "0 12px 22px rgba(15, 95, 215, 0.18)",
              }}
            >
              {isPending ? "Kaydediliyor..." : "Kaydı Güncelle"}
            </button>
            <button
              type="button"
              onClick={() => void handleDelete()}
              disabled={isPending || !selectedEntry}
              style={{
                border: "1px solid rgba(205, 70, 66, 0.18)",
                borderRadius: "12px",
                padding: "10px 14px",
                background: "rgba(205, 70, 66, 0.08)",
                color: "#b53632",
                fontWeight: 800,
                fontSize: "0.9rem",
                cursor: "pointer",
              }}
            >
              Kaydı Sil
            </button>
          </div>
          </form>
        ) : null}
      </div>
    </section>
  );
}
