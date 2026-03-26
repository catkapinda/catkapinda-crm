"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type PurchasesFormOptions = {
  item_options: string[];
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
    maximumFractionDigits: 2,
  }).format(value || 0);
}

export function PurchaseEntryWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<PurchasesFormOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [itemName, setItemName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [totalInvoiceAmount, setTotalInvoiceAmount] = useState("");
  const [supplier, setSupplier] = useState("");
  const [invoiceNo, setInvoiceNo] = useState("");
  const [notes, setNotes] = useState("");

  async function loadOptions() {
    setLoadingOptions(true);
    try {
      const response = await apiFetch("/purchases/form-options");
      if (!response.ok) {
        throw new Error("Satın alma seçenekleri yüklenemedi.");
      }
      const payload = (await response.json()) as PurchasesFormOptions;
      setOptions(payload);
      setItemName(payload.selected_item);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Satın alma seçenekleri yüklenemedi.");
    } finally {
      setLoadingOptions(false);
    }
  }

  useEffect(() => {
    void loadOptions();
  }, []);

  const unitCostPreview = useMemo(() => {
    const qty = Number(quantity || 0);
    const total = Number(totalInvoiceAmount || 0);
    if (qty <= 0 || total <= 0) {
      return formatCurrency(0);
    }
    return formatCurrency(total / qty);
  }, [quantity, totalInvoiceAmount]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    const response = await apiFetch("/purchases/records", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        purchase_date: purchaseDate,
        item_name: itemName,
        quantity: Number(quantity || 0),
        total_invoice_amount: Number(totalInvoiceAmount || 0),
        supplier,
        invoice_no: invoiceNo,
        notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSubmitError(payload?.detail || "Satın alma kaydı oluşturulamadı.");
      return;
    }

    setSubmitSuccess(payload?.message || "Satın alma kaydı oluşturuldu.");
    setQuantity("1");
    setTotalInvoiceAmount("");
    setSupplier("");
    setInvoiceNo("");
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Yeni Satın Alma Kaydı</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Fatura tarihini, ürünü ve toplam tutarı gir; sistem birim maliyeti otomatik
          hesaplasın.
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
          Satın alma seçenekleri yükleniyor...
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "16px" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.3fr) minmax(280px, 0.7fr)",
              gap: "16px",
              alignItems: "start",
            }}
          >
            <div style={{ display: "grid", gap: "14px" }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Fatura Tarihi</span>
                  <input type="date" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Ürün</span>
                  <select value={itemName} onChange={(event) => setItemName(event.target.value)} style={fieldStyle}>
                    {options?.item_options.map((item) => (
                      <option key={item} value={item}>
                        {item}
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
                    value={quantity}
                    onChange={(event) => setQuantity(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Toplam Fatura Tutarı</span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min="0"
                    step="0.01"
                    value={totalInvoiceAmount}
                    onChange={(event) => setTotalInvoiceAmount(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Tedarikçi</span>
                  <input value={supplier} onChange={(event) => setSupplier(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Fatura No</span>
                  <input value={invoiceNo} onChange={(event) => setInvoiceNo(event.target.value)} style={fieldStyle} />
                </label>
              </div>

              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Not</span>
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Kısa satın alma notu"
                  rows={3}
                  style={{ ...fieldStyle, resize: "vertical" }}
                />
              </label>
            </div>

            <div
              style={{
                display: "grid",
                gap: "12px",
                padding: "16px",
                borderRadius: "20px",
                border: "1px solid var(--line)",
                background: "rgba(255, 255, 255, 0.86)",
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
                Kayıt Özeti
              </div>
              <div style={{ display: "grid", gap: "10px" }}>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.82rem" }}>Ürün</div>
                  <div style={{ fontWeight: 800 }}>{itemName || "-"}</div>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.82rem" }}>Adet</div>
                  <div style={{ fontWeight: 800 }}>{quantity || "0"}</div>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.82rem" }}>Toplam Fatura</div>
                  <div style={{ fontWeight: 800 }}>{formatCurrency(Number(totalInvoiceAmount || 0))}</div>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.82rem" }}>Birim Maliyet</div>
                  <div style={{ fontWeight: 900, fontSize: "1.15rem" }}>{unitCostPreview}</div>
                </div>
              </div>
            </div>
          </div>

          {(submitError || submitSuccess) && (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "16px",
                border: submitError ? "1px solid rgba(205, 70, 66, 0.18)" : "1px solid rgba(35, 148, 94, 0.18)",
                background: submitError ? "rgba(205, 70, 66, 0.08)" : "rgba(35, 148, 94, 0.08)",
                color: submitError ? "#b53632" : "#1d7b4d",
                fontWeight: 700,
              }}
            >
              {submitError || submitSuccess}
            </div>
          )}

          <button
            type="submit"
            disabled={isPending}
            style={{
              border: "none",
              borderRadius: "18px",
              padding: "15px 18px",
              background: "linear-gradient(135deg, #0f5fd7, #1a73e8)",
              color: "white",
              fontWeight: 800,
              fontSize: "0.98rem",
              cursor: "pointer",
              boxShadow: "0 16px 28px rgba(15, 95, 215, 0.2)",
            }}
          >
            {isPending ? "Kaydediliyor..." : "Satın Alma Kaydını Oluştur"}
          </button>
        </form>
      )}
    </section>
  );
}
