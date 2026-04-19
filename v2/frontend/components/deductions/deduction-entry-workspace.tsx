"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type DeductionsFormOptions = {
  personnel: Array<{
    id: number;
    label: string;
  }>;
  deduction_types: string[];
  type_captions: Record<string, string>;
  selected_personnel_id: number | null;
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

export function DeductionEntryWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<DeductionsFormOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [personnelId, setPersonnelId] = useState<number | "">("");
  const [deductionDate, setDeductionDate] = useState(new Date().toISOString().slice(0, 10));
  const [deductionType, setDeductionType] = useState("");
  const [amount, setAmount] = useState("");
  const [notes, setNotes] = useState("");

  async function loadOptions() {
    setLoadingOptions(true);
    try {
      const response = await apiFetch("/deductions/form-options");
      if (!response.ok) {
        throw new Error("Kesinti seçenekleri yüklenemedi.");
      }
      const payload = (await response.json()) as DeductionsFormOptions;
      setOptions(payload);
      setPersonnelId(payload.selected_personnel_id ?? "");
      setDeductionType(payload.deduction_types[0] ?? "");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Kesinti seçenekleri yüklenemedi.");
    } finally {
      setLoadingOptions(false);
    }
  }

  useEffect(() => {
    void loadOptions();
  }, []);

  const selectedCaption = useMemo(() => {
    if (!options || !deductionType) {
      return "";
    }
    return options.type_captions[deductionType] ?? "";
  }, [options, deductionType]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    if (typeof personnelId !== "number") {
      setSubmitError("Lutfen bir personel seç.");
      return;
    }
    if (!deductionType) {
      setSubmitError("Lutfen bir kesinti tipi seç.");
      return;
    }

    const response = await apiFetch("/deductions/records", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personnel_id: personnelId,
        deduction_date: deductionDate,
        deduction_type: deductionType,
        amount: Number(amount || 0),
        notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSubmitError(payload?.detail || "Kesinti kaydı oluşturulamadı.");
      return;
    }

    setSubmitSuccess(payload?.message || "Kesinti kaydı oluşturuldu.");
    setAmount("");
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Kesinti Girisi</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Manuel kesinti kayıtlarını v2 ekraninda hızlı sekilde oluştur.
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
          Kesinti seçenekleri yükleniyor...
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "16px" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "14px",
            }}
          >
            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Personel</span>
              <select
                value={personnelId}
                onChange={(event) => setPersonnelId(Number(event.target.value))}
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
              <span style={{ fontWeight: 700 }}>Tarih</span>
              <input
                type="date"
                value={deductionDate}
                onChange={(event) => setDeductionDate(event.target.value)}
                style={fieldStyle}
              />
            </label>

            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Kesinti Tipi</span>
              <select
                value={deductionType}
                onChange={(event) => setDeductionType(event.target.value)}
                style={fieldStyle}
              >
                {options?.deduction_types.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(220px, 0.8fr) minmax(280px, 1.2fr)",
              gap: "14px",
            }}
          >
            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Tutar</span>
              <input
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0"
                style={fieldStyle}
              />
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
              {selectedCaption || "Seçilen kesinti tipi için açıklama burada görünür."}
            </div>
          </div>

          <label style={{ display: "grid", gap: "8px" }}>
            <span style={{ fontWeight: 700 }}>Not</span>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Kisa operasyon notu"
              rows={3}
              style={{ ...fieldStyle, resize: "vertical" }}
            />
          </label>

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
            {isPending ? "Kaydediliyor..." : "Kesinti Kaydını Oluştur"}
          </button>
        </form>
      )}
    </section>
  );
}
