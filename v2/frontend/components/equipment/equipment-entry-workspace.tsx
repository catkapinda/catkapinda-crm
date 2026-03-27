"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type EquipmentPersonnelOption = {
  id: number;
  label: string;
};

type EquipmentItemDefault = {
  default_unit_cost: number;
  default_sale_price: number;
  default_installment_count: number;
  default_vat_rate: number;
};

type EquipmentFormOptions = {
  personnel: EquipmentPersonnelOption[];
  issue_items: string[];
  sale_type_options: string[];
  return_condition_options: string[];
  installment_count_options: number[];
  item_defaults: Record<string, EquipmentItemDefault>;
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

export function EquipmentEntryWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<EquipmentFormOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [issueError, setIssueError] = useState("");
  const [issueSuccess, setIssueSuccess] = useState("");
  const [boxError, setBoxError] = useState("");
  const [boxSuccess, setBoxSuccess] = useState("");

  const today = new Date().toISOString().slice(0, 10);
  const [issuePersonnelId, setIssuePersonnelId] = useState<number | "">("");
  const [issueDate, setIssueDate] = useState(today);
  const [itemName, setItemName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unitCost, setUnitCost] = useState("0");
  const [unitSalePrice, setUnitSalePrice] = useState("0");
  const [installmentCount, setInstallmentCount] = useState("2");
  const [saleType, setSaleType] = useState("Satış");
  const [issueNotes, setIssueNotes] = useState("");

  const [boxPersonnelId, setBoxPersonnelId] = useState<number | "">("");
  const [returnDate, setReturnDate] = useState(today);
  const [returnQuantity, setReturnQuantity] = useState("1");
  const [conditionStatus, setConditionStatus] = useState("Temiz");
  const [payoutAmount, setPayoutAmount] = useState("0");
  const [boxNotes, setBoxNotes] = useState("");

  async function loadOptions() {
    setLoadingOptions(true);
    try {
      const response = await apiFetch("/equipment/form-options");
      if (!response.ok) {
        throw new Error("Ekipman secenekleri yuklenemedi.");
      }
      const payload = (await response.json()) as EquipmentFormOptions;
      setOptions(payload);
      setIssuePersonnelId(payload.selected_personnel_id ?? "");
      setBoxPersonnelId(payload.selected_personnel_id ?? "");
      setItemName(payload.selected_item);
      setSaleType(payload.sale_type_options[0] ?? "Satış");
      setConditionStatus(payload.return_condition_options[0] ?? "Temiz");
      const defaults = payload.item_defaults[payload.selected_item];
      if (defaults) {
        setUnitCost(String(defaults.default_unit_cost ?? 0));
        setUnitSalePrice(String(defaults.default_sale_price ?? 0));
        setInstallmentCount(String(defaults.default_installment_count ?? 2));
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Ekipman secenekleri yuklenemedi.";
      setIssueError(message);
      setBoxError(message);
    } finally {
      setLoadingOptions(false);
    }
  }

  useEffect(() => {
    void loadOptions();
  }, []);

  useEffect(() => {
    if (!options || !itemName) {
      return;
    }
    const defaults = options.item_defaults[itemName];
    if (!defaults) {
      return;
    }
    setUnitCost(String(defaults.default_unit_cost ?? 0));
    setUnitSalePrice(String(defaults.default_sale_price ?? 0));
    setInstallmentCount(String(defaults.default_installment_count ?? 2));
  }, [itemName, options]);

  const issueSummary = useMemo(() => {
    const qty = Number(quantity || 0);
    const cost = Number(unitCost || 0) * qty;
    const sale = Number(unitSalePrice || 0) * qty;
    return {
      totalCost: cost,
      totalSale: sale,
      installmentAmount:
        saleType === "Satış" && Number(installmentCount || 0) > 0
          ? sale / Number(installmentCount || 1)
          : 0,
    };
  }, [installmentCount, quantity, saleType, unitCost, unitSalePrice]);

  async function handleIssueSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIssueError("");
    setIssueSuccess("");
    if (typeof issuePersonnelId !== "number") {
      setIssueError("Lutfen bir personel sec.");
      return;
    }

    const response = await apiFetch("/equipment/issues", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personnel_id: issuePersonnelId,
        issue_date: issueDate,
        item_name: itemName,
        quantity: Number(quantity || 0),
        unit_cost: Number(unitCost || 0),
        unit_sale_price: Number(unitSalePrice || 0),
        installment_count: Number(installmentCount || 1),
        sale_type: saleType,
        notes: issueNotes,
      }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setIssueError(payload?.detail || "Zimmet kaydi olusturulamadi.");
      return;
    }

    setIssueSuccess(payload?.message || "Zimmet kaydi olusturuldu.");
    setQuantity("1");
    setIssueNotes("");
    startTransition(() => {
      router.refresh();
    });
  }

  async function handleBoxSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBoxError("");
    setBoxSuccess("");
    if (typeof boxPersonnelId !== "number") {
      setBoxError("Lutfen bir personel sec.");
      return;
    }

    const response = await apiFetch("/equipment/box-returns", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personnel_id: boxPersonnelId,
        return_date: returnDate,
        quantity: Number(returnQuantity || 0),
        condition_status: conditionStatus,
        payout_amount: Number(payoutAmount || 0),
        notes: boxNotes,
      }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setBoxError(payload?.detail || "Box geri alim kaydi olusturulamadi.");
      return;
    }

    setBoxSuccess(payload?.message || "Box geri alim kaydi olusturuldu.");
    setReturnQuantity("1");
    setPayoutAmount("0");
    setBoxNotes("");
    startTransition(() => {
      router.refresh();
    });
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
        gap: "16px",
      }}
    >
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
          <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Yeni Zimmet Kaydi</h2>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
            Ekipman teslim, satis ve depozit kayitlarini ayni yuzeyden olustur.
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
            Ekipman secenekleri yukleniyor...
          </div>
        ) : (
          <form onSubmit={handleIssueSubmit} style={{ display: "grid", gap: "16px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "14px",
              }}
            >
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Personel</span>
                <select
                  value={issuePersonnelId}
                  onChange={(event) => setIssuePersonnelId(Number(event.target.value))}
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
                <span style={{ fontWeight: 700 }}>Zimmet Tarihi</span>
                <input
                  type="date"
                  value={issueDate}
                  onChange={(event) => setIssueDate(event.target.value)}
                  style={fieldStyle}
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Kalem</span>
                <select value={itemName} onChange={(event) => setItemName(event.target.value)} style={fieldStyle}>
                  {options?.issue_items.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Satis Tipi</span>
                <select value={saleType} onChange={(event) => setSaleType(event.target.value)} style={fieldStyle}>
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
                  value={quantity}
                  onChange={(event) => setQuantity(event.target.value)}
                  style={fieldStyle}
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Birim Maliyet</span>
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.01"
                  value={unitCost}
                  onChange={(event) => setUnitCost(event.target.value)}
                  style={fieldStyle}
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Birim Satis</span>
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.01"
                  value={unitSalePrice}
                  onChange={(event) => setUnitSalePrice(event.target.value)}
                  style={fieldStyle}
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Taksit</span>
                <select
                  value={installmentCount}
                  onChange={(event) => setInstallmentCount(event.target.value)}
                  style={fieldStyle}
                  disabled={saleType !== "Satış"}
                >
                  {options?.installment_count_options.map((count) => (
                    <option key={count} value={count}>
                      {count}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.2fr) minmax(260px, 0.8fr)",
                gap: "14px",
                alignItems: "start",
              }}
            >
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Not</span>
                <textarea
                  value={issueNotes}
                  onChange={(event) => setIssueNotes(event.target.value)}
                  rows={3}
                  placeholder="Kisa ekipman notu"
                  style={{ ...fieldStyle, resize: "vertical" }}
                />
              </label>

              <div
                style={{
                  display: "grid",
                  gap: "10px",
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
                  Zimmet Ozeti
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.82rem" }}>Toplam Maliyet</div>
                  <div style={{ fontWeight: 800 }}>{formatCurrency(issueSummary.totalCost)}</div>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.82rem" }}>Toplam Satis</div>
                  <div style={{ fontWeight: 800 }}>{formatCurrency(issueSummary.totalSale)}</div>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.82rem" }}>Taksit Basi</div>
                  <div style={{ fontWeight: 900, fontSize: "1.1rem" }}>
                    {saleType === "Satış"
                      ? formatCurrency(issueSummary.installmentAmount)
                      : "Taksit yok"}
                  </div>
                </div>
              </div>
            </div>

            {(issueError || issueSuccess) && (
              <div
                style={{
                  padding: "14px 16px",
                  borderRadius: "16px",
                  border: issueError
                    ? "1px solid rgba(205, 70, 66, 0.18)"
                    : "1px solid rgba(35, 148, 94, 0.18)",
                  background: issueError
                    ? "rgba(205, 70, 66, 0.08)"
                    : "rgba(35, 148, 94, 0.08)",
                  color: issueError ? "#b53632" : "#1d7b4d",
                  fontWeight: 700,
                }}
              >
                {issueError || issueSuccess}
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
              {isPending ? "Kaydediliyor..." : "Zimmet Kaydini Olustur"}
            </button>
          </form>
        )}
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
          <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Box Geri Alim</h2>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
            Iade alinmis box adetlerini ve varsa odeme tutarini operasyon kaydina bagla.
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
            Box geri alim secenekleri yukleniyor...
          </div>
        ) : (
          <form onSubmit={handleBoxSubmit} style={{ display: "grid", gap: "16px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "14px",
              }}
            >
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Personel</span>
                <select
                  value={boxPersonnelId}
                  onChange={(event) => setBoxPersonnelId(Number(event.target.value))}
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
                <span style={{ fontWeight: 700 }}>Iade Tarihi</span>
                <input
                  type="date"
                  value={returnDate}
                  onChange={(event) => setReturnDate(event.target.value)}
                  style={fieldStyle}
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Adet</span>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={returnQuantity}
                  onChange={(event) => setReturnQuantity(event.target.value)}
                  style={fieldStyle}
                />
              </label>
              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Durum</span>
                <select
                  value={conditionStatus}
                  onChange={(event) => setConditionStatus(event.target.value)}
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
                <span style={{ fontWeight: 700 }}>Odeme Tutarı</span>
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.01"
                  value={payoutAmount}
                  onChange={(event) => setPayoutAmount(event.target.value)}
                  style={fieldStyle}
                />
              </label>
            </div>

            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Not</span>
              <textarea
                value={boxNotes}
                onChange={(event) => setBoxNotes(event.target.value)}
                rows={3}
                placeholder="Kisa iade notu"
                style={{ ...fieldStyle, resize: "vertical" }}
              />
            </label>

            {(boxError || boxSuccess) && (
              <div
                style={{
                  padding: "14px 16px",
                  borderRadius: "16px",
                  border: boxError
                    ? "1px solid rgba(205, 70, 66, 0.18)"
                    : "1px solid rgba(35, 148, 94, 0.18)",
                  background: boxError
                    ? "rgba(205, 70, 66, 0.08)"
                    : "rgba(35, 148, 94, 0.08)",
                  color: boxError ? "#b53632" : "#1d7b4d",
                  fontWeight: 700,
                }}
              >
                {boxError || boxSuccess}
              </div>
            )}

            <button
              type="submit"
              disabled={isPending}
              style={{
                border: "none",
                borderRadius: "18px",
                padding: "15px 18px",
                background: "linear-gradient(135deg, #10203c, #1d315b)",
                color: "white",
                fontWeight: 800,
                fontSize: "0.98rem",
                cursor: "pointer",
                boxShadow: "0 16px 28px rgba(16, 32, 60, 0.2)",
              }}
            >
              {isPending ? "Kaydediliyor..." : "Box Geri Alim Kaydini Olustur"}
            </button>
          </form>
        )}
      </section>
    </div>
  );
}
