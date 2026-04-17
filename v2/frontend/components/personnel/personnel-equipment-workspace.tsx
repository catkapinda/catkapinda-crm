"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../auth/auth-provider";
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

type EquipmentIssuesManagementResponse = {
  total_entries: number;
  entries: EquipmentIssueEntry[];
};

type BoxReturnsManagementResponse = {
  total_entries: number;
  entries: BoxReturnEntry[];
};

const fieldStyle: CSSProperties = {
  width: "100%",
  padding: "12px 14px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255,255,255,0.92)",
  color: "var(--text)",
  font: "inherit",
};

const cardStyle: CSSProperties = {
  borderRadius: "24px",
  border: "1px solid var(--line)",
  background: "rgba(255,255,255,0.9)",
  boxShadow: "var(--shadow-soft)",
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function formatDate(value: string) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

function smallPill(label: string, tone: "accent" | "muted" = "muted") {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "6px 10px",
        borderRadius: "999px",
        fontSize: "0.76rem",
        fontWeight: 800,
        background:
          tone === "accent" ? "rgba(185,116,41,0.12)" : "rgba(62,81,107,0.08)",
        color: tone === "accent" ? "var(--accent-strong)" : "var(--muted)",
        border:
          tone === "accent"
            ? "1px solid rgba(185,116,41,0.18)"
            : "1px solid rgba(62,81,107,0.12)",
      }}
    >
      {label}
    </span>
  );
}

export function PersonnelEquipmentWorkspace() {
  const { user } = useAuth();
  const [options, setOptions] = useState<EquipmentFormOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [selectedPersonnelId, setSelectedPersonnelId] = useState<number | "">("");

  const [issueEntries, setIssueEntries] = useState<EquipmentIssueEntry[]>([]);
  const [boxEntries, setBoxEntries] = useState<BoxReturnEntry[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsError, setRecordsError] = useState("");

  const [issueMessage, setIssueMessage] = useState("");
  const [issueError, setIssueError] = useState("");
  const [boxMessage, setBoxMessage] = useState("");
  const [boxError, setBoxError] = useState("");

  const [newIssueDate, setNewIssueDate] = useState(new Date().toISOString().slice(0, 10));
  const [newIssueItem, setNewIssueItem] = useState("");
  const [newIssueQuantity, setNewIssueQuantity] = useState("1");
  const [newIssueUnitCost, setNewIssueUnitCost] = useState("0");
  const [newIssueUnitSalePrice, setNewIssueUnitSalePrice] = useState("0");
  const [newIssueInstallmentCount, setNewIssueInstallmentCount] = useState("1");
  const [newIssueSaleType, setNewIssueSaleType] = useState("Satış");
  const [newIssueNotes, setNewIssueNotes] = useState("");

  const [selectedIssueId, setSelectedIssueId] = useState<number | null>(null);
  const [editIssueDate, setEditIssueDate] = useState("");
  const [editIssueItem, setEditIssueItem] = useState("");
  const [editIssueQuantity, setEditIssueQuantity] = useState("1");
  const [editIssueUnitCost, setEditIssueUnitCost] = useState("0");
  const [editIssueUnitSalePrice, setEditIssueUnitSalePrice] = useState("0");
  const [editIssueInstallmentCount, setEditIssueInstallmentCount] = useState("1");
  const [editIssueSaleType, setEditIssueSaleType] = useState("Satış");
  const [editIssueNotes, setEditIssueNotes] = useState("");
  const [issueBusy, setIssueBusy] = useState(false);

  const [newReturnDate, setNewReturnDate] = useState(new Date().toISOString().slice(0, 10));
  const [newReturnQuantity, setNewReturnQuantity] = useState("1");
  const [newReturnConditionStatus, setNewReturnConditionStatus] = useState("Temiz");
  const [newReturnPayoutAmount, setNewReturnPayoutAmount] = useState("0");
  const [newReturnNotes, setNewReturnNotes] = useState("");

  const [selectedBoxId, setSelectedBoxId] = useState<number | null>(null);
  const [editReturnDate, setEditReturnDate] = useState("");
  const [editReturnQuantity, setEditReturnQuantity] = useState("1");
  const [editReturnConditionStatus, setEditReturnConditionStatus] = useState("Temiz");
  const [editReturnPayoutAmount, setEditReturnPayoutAmount] = useState("0");
  const [editReturnNotes, setEditReturnNotes] = useState("");
  const [boxBusy, setBoxBusy] = useState(false);

  const canViewEquipment = Boolean(user?.allowed_actions.includes("equipment.view"));
  const canCreateEquipment = Boolean(user?.allowed_actions.includes("equipment.create"));
  const canUpdateEquipment = Boolean(user?.allowed_actions.includes("equipment.bulk_update"));
  const canDeleteEquipment = Boolean(user?.allowed_actions.includes("equipment.bulk_delete"));
  const canManageBoxReturn = Boolean(user?.allowed_actions.includes("equipment.box_return"));

  useEffect(() => {
    let active = true;

    async function loadOptions() {
      setLoading(true);
      setLoadError("");
      try {
        const response = await apiFetch("/equipment/form-options");
        if (!response.ok) {
          throw new Error("Personel ekipman referansları yüklenemedi.");
        }
        const payload = (await response.json()) as EquipmentFormOptions;
        if (!active) {
          return;
        }
        setOptions(payload);
        const initialPersonnelId = payload.selected_personnel_id ?? payload.personnel[0]?.id ?? "";
        setSelectedPersonnelId(initialPersonnelId);
        const initialItem = payload.selected_item || payload.issue_items[0] || "";
        setNewIssueItem(initialItem);
        setEditIssueItem(initialItem);
        setNewIssueSaleType(payload.sale_type_options[0] || "Satış");
        setEditIssueSaleType(payload.sale_type_options[0] || "Satış");
        setNewReturnConditionStatus(payload.return_condition_options[0] || "Temiz");
        setEditReturnConditionStatus(payload.return_condition_options[0] || "Temiz");
      } catch (error) {
        if (active) {
          setLoadError(
            error instanceof Error ? error.message : "Personel ekipman referansları yüklenemedi.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    if (canViewEquipment) {
      void loadOptions();
    } else {
      setLoading(false);
    }

    return () => {
      active = false;
    };
  }, [canViewEquipment]);

  useEffect(() => {
    if (!options || !newIssueItem) {
      return;
    }
    const defaults = options.item_defaults[newIssueItem];
    if (!defaults) {
      return;
    }
    setNewIssueUnitCost(String(defaults.default_unit_cost ?? 0));
    setNewIssueUnitSalePrice(String(defaults.default_sale_price ?? 0));
    setNewIssueInstallmentCount(String(defaults.default_installment_count ?? 1));
  }, [newIssueItem, options]);

  useEffect(() => {
    if (!selectedPersonnelId || !options) {
      setIssueEntries([]);
      setBoxEntries([]);
      setSelectedIssueId(null);
      setSelectedBoxId(null);
      return;
    }

    let active = true;

    async function loadRecords() {
      setRecordsLoading(true);
      setRecordsError("");
      try {
        const [issueResponse, boxResponse] = await Promise.all([
          apiFetch(`/equipment/issues?personnel_id=${selectedPersonnelId}&limit=80`),
          apiFetch(`/equipment/box-returns?personnel_id=${selectedPersonnelId}&limit=80`),
        ]);
        if (!issueResponse.ok) {
          throw new Error("Seçili personelin ekipman kayıtları yüklenemedi.");
        }
        if (!boxResponse.ok) {
          throw new Error("Seçili personelin box geri alım kayıtları yüklenemedi.");
        }
        const issuePayload = (await issueResponse.json()) as EquipmentIssuesManagementResponse;
        const boxPayload = (await boxResponse.json()) as BoxReturnsManagementResponse;
        if (!active) {
          return;
        }
        setIssueEntries(issuePayload.entries);
        setBoxEntries(boxPayload.entries);
        setSelectedIssueId((current) => {
          if (!issuePayload.entries.length) {
            return null;
          }
          if (current && issuePayload.entries.some((entry) => entry.id === current)) {
            return current;
          }
          return issuePayload.entries[0].id;
        });
        setSelectedBoxId((current) => {
          if (!boxPayload.entries.length) {
            return null;
          }
          if (current && boxPayload.entries.some((entry) => entry.id === current)) {
            return current;
          }
          return boxPayload.entries[0].id;
        });
      } catch (error) {
        if (active) {
          setRecordsError(
            error instanceof Error ? error.message : "Seçili personelin hareketleri yüklenemedi.",
          );
          setIssueEntries([]);
          setBoxEntries([]);
          setSelectedIssueId(null);
          setSelectedBoxId(null);
        }
      } finally {
        if (active) {
          setRecordsLoading(false);
        }
      }
    }

    void loadRecords();
    return () => {
      active = false;
    };
  }, [options, selectedPersonnelId]);

  const selectedPersonnelLabel =
    options?.personnel.find((entry) => entry.id === selectedPersonnelId)?.label ?? "Personel seç";

  const selectedIssue = useMemo(
    () => issueEntries.find((entry) => entry.id === selectedIssueId) ?? null,
    [issueEntries, selectedIssueId],
  );

  const selectedBoxEntry = useMemo(
    () => boxEntries.find((entry) => entry.id === selectedBoxId) ?? null,
    [boxEntries, selectedBoxId],
  );

  useEffect(() => {
    if (!selectedIssue) {
      setEditIssueDate("");
      setEditIssueItem(options?.selected_item || "");
      setEditIssueQuantity("1");
      setEditIssueUnitCost("0");
      setEditIssueUnitSalePrice("0");
      setEditIssueInstallmentCount("1");
      setEditIssueSaleType(options?.sale_type_options[0] || "Satış");
      setEditIssueNotes("");
      return;
    }
    setEditIssueDate(selectedIssue.issue_date);
    setEditIssueItem(selectedIssue.item_name);
    setEditIssueQuantity(String(selectedIssue.quantity || 1));
    setEditIssueUnitCost(String(selectedIssue.unit_cost || 0));
    setEditIssueUnitSalePrice(String(selectedIssue.unit_sale_price || 0));
    setEditIssueInstallmentCount(String(selectedIssue.installment_count || 1));
    setEditIssueSaleType(selectedIssue.sale_type || "Satış");
    setEditIssueNotes(selectedIssue.notes || "");
  }, [options?.sale_type_options, options?.selected_item, selectedIssue]);

  useEffect(() => {
    if (!selectedBoxEntry) {
      setEditReturnDate("");
      setEditReturnQuantity("1");
      setEditReturnConditionStatus(options?.return_condition_options[0] || "Temiz");
      setEditReturnPayoutAmount("0");
      setEditReturnNotes("");
      return;
    }
    setEditReturnDate(selectedBoxEntry.return_date);
    setEditReturnQuantity(String(selectedBoxEntry.quantity || 1));
    setEditReturnConditionStatus(selectedBoxEntry.condition_status || "Temiz");
    setEditReturnPayoutAmount(String(selectedBoxEntry.payout_amount || 0));
    setEditReturnNotes(selectedBoxEntry.notes || "");
  }, [options?.return_condition_options, selectedBoxEntry]);

  async function refreshRecords() {
    if (!selectedPersonnelId) {
      return;
    }
    setRecordsLoading(true);
    setRecordsError("");
    try {
      const [issueResponse, boxResponse] = await Promise.all([
        apiFetch(`/equipment/issues?personnel_id=${selectedPersonnelId}&limit=80`),
        apiFetch(`/equipment/box-returns?personnel_id=${selectedPersonnelId}&limit=80`),
      ]);
      if (!issueResponse.ok) {
        throw new Error("Seçili personelin ekipman kayıtları yenilenemedi.");
      }
      if (!boxResponse.ok) {
        throw new Error("Seçili personelin box geri alım kayıtları yenilenemedi.");
      }
      const issuePayload = (await issueResponse.json()) as EquipmentIssuesManagementResponse;
      const boxPayload = (await boxResponse.json()) as BoxReturnsManagementResponse;
      setIssueEntries(issuePayload.entries);
      setBoxEntries(boxPayload.entries);
      setSelectedIssueId(issuePayload.entries[0]?.id ?? null);
      setSelectedBoxId(boxPayload.entries[0]?.id ?? null);
    } catch (error) {
      setRecordsError(
        error instanceof Error ? error.message : "Seçili personelin hareketleri yenilenemedi.",
      );
    } finally {
      setRecordsLoading(false);
    }
  }

  async function handleCreateIssue(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPersonnelId) {
      setIssueError("Önce bir personel seçmelisin.");
      return;
    }
    setIssueBusy(true);
    setIssueError("");
    setIssueMessage("");
    try {
      const response = await apiFetch("/equipment/issues", {
        method: "POST",
        body: JSON.stringify({
          personnel_id: selectedPersonnelId,
          issue_date: newIssueDate,
          item_name: newIssueItem,
          quantity: Number(newIssueQuantity),
          unit_cost: Number(newIssueUnitCost),
          unit_sale_price: Number(newIssueUnitSalePrice),
          installment_count: Number(newIssueInstallmentCount),
          sale_type: newIssueSaleType,
          notes: newIssueNotes,
        }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "Zimmet kaydı oluşturulamadı.");
      }
      setIssueMessage(payload?.message || "Zimmet kaydı oluşturuldu.");
      setNewIssueQuantity("1");
      setNewIssueNotes("");
      await refreshRecords();
    } catch (error) {
      setIssueError(error instanceof Error ? error.message : "Zimmet kaydı oluşturulamadı.");
    } finally {
      setIssueBusy(false);
    }
  }

  async function handleUpdateIssue() {
    if (!selectedIssue || !selectedPersonnelId) {
      return;
    }
    setIssueBusy(true);
    setIssueError("");
    setIssueMessage("");
    try {
      const response = await apiFetch(`/equipment/issues/${selectedIssue.id}`, {
        method: "PUT",
        body: JSON.stringify({
          personnel_id: selectedPersonnelId,
          issue_date: editIssueDate,
          item_name: editIssueItem,
          quantity: Number(editIssueQuantity),
          unit_cost: Number(editIssueUnitCost),
          unit_sale_price: Number(editIssueUnitSalePrice),
          installment_count: Number(editIssueInstallmentCount),
          sale_type: editIssueSaleType,
          notes: editIssueNotes,
        }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "Zimmet kaydı güncellenemedi.");
      }
      setIssueMessage(payload?.message || "Zimmet kaydı güncellendi.");
      await refreshRecords();
    } catch (error) {
      setIssueError(error instanceof Error ? error.message : "Zimmet kaydı güncellenemedi.");
    } finally {
      setIssueBusy(false);
    }
  }

  async function handleDeleteIssue() {
    if (!selectedIssue) {
      return;
    }
    setIssueBusy(true);
    setIssueError("");
    setIssueMessage("");
    try {
      const response = await apiFetch(`/equipment/issues/${selectedIssue.id}`, {
        method: "DELETE",
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "Zimmet kaydı silinemedi.");
      }
      setIssueMessage(payload?.message || "Zimmet kaydı silindi.");
      await refreshRecords();
    } catch (error) {
      setIssueError(error instanceof Error ? error.message : "Zimmet kaydı silinemedi.");
    } finally {
      setIssueBusy(false);
    }
  }

  async function handleCreateBoxReturn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPersonnelId) {
      setBoxError("Önce bir personel seçmelisin.");
      return;
    }
    setBoxBusy(true);
    setBoxError("");
    setBoxMessage("");
    try {
      const response = await apiFetch("/equipment/box-returns", {
        method: "POST",
        body: JSON.stringify({
          personnel_id: selectedPersonnelId,
          return_date: newReturnDate,
          quantity: Number(newReturnQuantity),
          condition_status: newReturnConditionStatus,
          payout_amount: Number(newReturnPayoutAmount),
          notes: newReturnNotes,
        }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "Box geri alım kaydı oluşturulamadı.");
      }
      setBoxMessage(payload?.message || "Box geri alım kaydı oluşturuldu.");
      setNewReturnQuantity("1");
      setNewReturnPayoutAmount("0");
      setNewReturnNotes("");
      await refreshRecords();
    } catch (error) {
      setBoxError(
        error instanceof Error ? error.message : "Box geri alım kaydı oluşturulamadı.",
      );
    } finally {
      setBoxBusy(false);
    }
  }

  async function handleUpdateBoxReturn() {
    if (!selectedBoxEntry || !selectedPersonnelId) {
      return;
    }
    setBoxBusy(true);
    setBoxError("");
    setBoxMessage("");
    try {
      const response = await apiFetch(`/equipment/box-returns/${selectedBoxEntry.id}`, {
        method: "PUT",
        body: JSON.stringify({
          personnel_id: selectedPersonnelId,
          return_date: editReturnDate,
          quantity: Number(editReturnQuantity),
          condition_status: editReturnConditionStatus,
          payout_amount: Number(editReturnPayoutAmount),
          notes: editReturnNotes,
        }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "Box geri alım kaydı güncellenemedi.");
      }
      setBoxMessage(payload?.message || "Box geri alım kaydı güncellendi.");
      await refreshRecords();
    } catch (error) {
      setBoxError(
        error instanceof Error ? error.message : "Box geri alım kaydı güncellenemedi.",
      );
    } finally {
      setBoxBusy(false);
    }
  }

  async function handleDeleteBoxReturn() {
    if (!selectedBoxEntry) {
      return;
    }
    setBoxBusy(true);
    setBoxError("");
    setBoxMessage("");
    try {
      const response = await apiFetch(`/equipment/box-returns/${selectedBoxEntry.id}`, {
        method: "DELETE",
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "Box geri alım kaydı silinemedi.");
      }
      setBoxMessage(payload?.message || "Box geri alım kaydı silindi.");
      await refreshRecords();
    } catch (error) {
      setBoxError(error instanceof Error ? error.message : "Box geri alım kaydı silinemedi.");
    } finally {
      setBoxBusy(false);
    }
  }

  if (!canViewEquipment) {
    return (
      <div
        style={{
          ...cardStyle,
          padding: "18px 20px",
          color: "var(--muted)",
          lineHeight: 1.7,
        }}
      >
        Ekipman hattını görmek için ilgili yetki açıldığında, seçili personel kartından zimmet ve
        box geri alım hareketleri burada yönetilecek.
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ ...cardStyle, padding: "18px 20px", color: "var(--muted)" }}>
        Personel ekipman hattı hazırlanıyor...
      </div>
    );
  }

  if (loadError || !options) {
    return (
      <div
        style={{
          ...cardStyle,
          padding: "18px 20px",
          color: "var(--muted)",
          lineHeight: 1.7,
        }}
      >
        {loadError || "Personel ekipman hattı şu anda hazırlanamadı."}
      </div>
    );
  }

  return (
    <section style={{ display: "grid", gap: "18px" }}>
      <article
        style={{
          ...cardStyle,
          padding: "18px",
          display: "grid",
          gap: "14px",
          background:
            "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(248,243,234,0.96))",
        }}
      >
        <div style={{ display: "grid", gap: "8px" }}>
          <div
            style={{
              color: "var(--accent-strong)",
              fontSize: "0.74rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Seçili Personel
          </div>
          <select
            value={selectedPersonnelId}
            onChange={(event) => setSelectedPersonnelId(Number(event.target.value))}
            style={fieldStyle}
          >
            {options.personnel.map((person) => (
              <option key={person.id} value={person.id}>
                {person.label}
              </option>
            ))}
          </select>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            {smallPill(`${issueEntries.length} zimmet hareketi`, "accent")}
            {smallPill(`${boxEntries.length} box geri alım kaydı`)}
            {selectedPersonnelLabel ? smallPill(selectedPersonnelLabel) : null}
          </div>
        </div>
        {recordsError ? (
          <div style={{ color: "#b42318", lineHeight: 1.6 }}>{recordsError}</div>
        ) : null}
        {recordsLoading ? (
          <div style={{ color: "var(--muted)", lineHeight: 1.6 }}>
            Seçili personelin ekipman ve box hareketleri yükleniyor...
          </div>
        ) : null}
      </article>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "18px",
        }}
      >
        <article style={{ ...cardStyle, padding: "20px", display: "grid", gap: "16px" }}>
          <div style={{ display: "grid", gap: "6px" }}>
            <div
              style={{
                color: "var(--accent-strong)",
                fontSize: "0.74rem",
                fontWeight: 800,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Ekipman ve Zimmet
            </div>
            <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
              Seçili personelin zimmet satışlarını personel kartından ekle, düzelt ve bağlı
              taksit hattıyla birlikte izle.
            </div>
          </div>

          <form onSubmit={handleCreateIssue} style={{ display: "grid", gap: "12px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px" }}>
              <input
                type="date"
                value={newIssueDate}
                onChange={(event) => setNewIssueDate(event.target.value)}
                style={fieldStyle}
              />
              <select
                value={newIssueItem}
                onChange={(event) => setNewIssueItem(event.target.value)}
                style={fieldStyle}
              >
                {options.issue_items.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min="1"
                value={newIssueQuantity}
                onChange={(event) => setNewIssueQuantity(event.target.value)}
                style={fieldStyle}
                placeholder="Adet"
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px" }}>
              <input
                type="number"
                min="0"
                step="50"
                value={newIssueUnitCost}
                onChange={(event) => setNewIssueUnitCost(event.target.value)}
                style={fieldStyle}
                placeholder="Birim maliyet"
              />
              <input
                type="number"
                min="0"
                step="50"
                value={newIssueUnitSalePrice}
                onChange={(event) => setNewIssueUnitSalePrice(event.target.value)}
                style={fieldStyle}
                placeholder="Kuryeye satış fiyatı"
              />
              <select
                value={newIssueSaleType}
                onChange={(event) => setNewIssueSaleType(event.target.value)}
                style={fieldStyle}
              >
                {options.sale_type_options.map((saleType) => (
                  <option key={saleType} value={saleType}>
                    {saleType}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 180px) minmax(0, 1fr)", gap: "12px" }}>
              <select
                value={newIssueSaleType === "Satış" ? newIssueInstallmentCount : "1"}
                onChange={(event) => setNewIssueInstallmentCount(event.target.value)}
                style={fieldStyle}
                disabled={newIssueSaleType !== "Satış"}
              >
                {options.installment_count_options.map((count) => (
                  <option key={count} value={count}>
                    {count} taksit
                  </option>
                ))}
              </select>
              <input
                value={newIssueNotes}
                onChange={(event) => setNewIssueNotes(event.target.value)}
                style={fieldStyle}
                placeholder="Not"
              />
            </div>
            {issueError ? <div style={{ color: "#b42318", lineHeight: 1.6 }}>{issueError}</div> : null}
            {issueMessage ? <div style={{ color: "#0f766e", lineHeight: 1.6 }}>{issueMessage}</div> : null}
            <button
              type="submit"
              disabled={!canCreateEquipment || issueBusy}
              style={{
                ...fieldStyle,
                cursor: canCreateEquipment && !issueBusy ? "pointer" : "not-allowed",
                background: "linear-gradient(135deg, var(--accent-strong), #d89a45)",
                color: "#fff7ea",
                border: "none",
                fontWeight: 800,
              }}
            >
              {issueBusy ? "Kaydediliyor..." : "Zimmet hareketini kaydet"}
            </button>
          </form>

          <div style={{ display: "grid", gap: "10px" }}>
            <div style={{ fontWeight: 800 }}>Seçili personelin zimmet geçmişi</div>
            {!issueEntries.length ? (
              <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                Bu personele ait zimmet kaydı henüz yok.
              </div>
            ) : (
              <div style={{ display: "grid", gap: "10px" }}>
                <select
                  value={selectedIssueId ?? ""}
                  onChange={(event) => setSelectedIssueId(Number(event.target.value))}
                  style={fieldStyle}
                >
                  {issueEntries.map((entry) => (
                    <option key={entry.id} value={entry.id}>
                      {`${formatDate(entry.issue_date)} | ${entry.item_name} | ${entry.quantity} adet | #${entry.id}`}
                    </option>
                  ))}
                </select>

                {selectedIssue ? (
                  <div style={{ display: "grid", gap: "12px" }}>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                      {smallPill(selectedIssue.is_auto_record ? "Otomatik kayıt" : "Elle yönetilen kayıt")}
                      {smallPill(
                        `${formatCurrency(selectedIssue.total_sale)} satış`,
                        "accent",
                      )}
                      {smallPill(`${selectedIssue.installment_count} taksit`)}
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px" }}>
                      <input
                        type="date"
                        value={editIssueDate}
                        onChange={(event) => setEditIssueDate(event.target.value)}
                        style={fieldStyle}
                      />
                      <select
                        value={editIssueItem}
                        onChange={(event) => setEditIssueItem(event.target.value)}
                        style={fieldStyle}
                      >
                        {options.issue_items.map((item) => (
                          <option key={item} value={item}>
                            {item}
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        min="1"
                        value={editIssueQuantity}
                        onChange={(event) => setEditIssueQuantity(event.target.value)}
                        style={fieldStyle}
                      />
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px" }}>
                      <input
                        type="number"
                        min="0"
                        step="50"
                        value={editIssueUnitCost}
                        onChange={(event) => setEditIssueUnitCost(event.target.value)}
                        style={fieldStyle}
                      />
                      <input
                        type="number"
                        min="0"
                        step="50"
                        value={editIssueUnitSalePrice}
                        onChange={(event) => setEditIssueUnitSalePrice(event.target.value)}
                        style={fieldStyle}
                      />
                      <select
                        value={editIssueSaleType}
                        onChange={(event) => setEditIssueSaleType(event.target.value)}
                        style={fieldStyle}
                      >
                        {options.sale_type_options.map((saleType) => (
                          <option key={saleType} value={saleType}>
                            {saleType}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 180px) minmax(0, 1fr)", gap: "12px" }}>
                      <select
                        value={editIssueSaleType === "Satış" ? editIssueInstallmentCount : "1"}
                        onChange={(event) => setEditIssueInstallmentCount(event.target.value)}
                        style={fieldStyle}
                        disabled={editIssueSaleType !== "Satış"}
                      >
                        {options.installment_count_options.map((count) => (
                          <option key={count} value={count}>
                            {count} taksit
                          </option>
                        ))}
                      </select>
                      <input
                        value={editIssueNotes}
                        onChange={(event) => setEditIssueNotes(event.target.value)}
                        style={fieldStyle}
                        placeholder="Not"
                      />
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "12px" }}>
                      <button
                        type="button"
                        onClick={() => void handleUpdateIssue()}
                        disabled={!canUpdateEquipment || selectedIssue.is_auto_record || issueBusy}
                        style={{
                          ...fieldStyle,
                          cursor:
                            canUpdateEquipment && !selectedIssue.is_auto_record && !issueBusy
                              ? "pointer"
                              : "not-allowed",
                          background: "rgba(15,95,215,0.1)",
                          color: "#0f5fd7",
                          fontWeight: 800,
                        }}
                      >
                        Kaydı güncelle
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleDeleteIssue()}
                        disabled={!canDeleteEquipment || selectedIssue.is_auto_record || issueBusy}
                        style={{
                          ...fieldStyle,
                          cursor:
                            canDeleteEquipment && !selectedIssue.is_auto_record && !issueBusy
                              ? "pointer"
                              : "not-allowed",
                          background: "rgba(180,35,24,0.08)",
                          color: "#b42318",
                          fontWeight: 800,
                        }}
                      >
                        Kaydı sil
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </article>

        <article style={{ ...cardStyle, padding: "20px", display: "grid", gap: "16px" }}>
          <div style={{ display: "grid", gap: "6px" }}>
            <div
              style={{
                color: "var(--accent-strong)",
                fontSize: "0.74rem",
                fontWeight: 800,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Box Geri Alım
            </div>
            <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
              Aynı personel kartından box dönüşlerini kaydet, ödeme ve durum bilgisini geçmişte
              tek akışta tut.
            </div>
          </div>

          <form onSubmit={handleCreateBoxReturn} style={{ display: "grid", gap: "12px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px" }}>
              <input
                type="date"
                value={newReturnDate}
                onChange={(event) => setNewReturnDate(event.target.value)}
                style={fieldStyle}
              />
              <select
                value={newReturnConditionStatus}
                onChange={(event) => setNewReturnConditionStatus(event.target.value)}
                style={fieldStyle}
              >
                {options.return_condition_options.map((condition) => (
                  <option key={condition} value={condition}>
                    {condition}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min="1"
                value={newReturnQuantity}
                onChange={(event) => setNewReturnQuantity(event.target.value)}
                style={fieldStyle}
                placeholder="Adet"
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 180px) minmax(0, 1fr)", gap: "12px" }}>
              <input
                type="number"
                min="0"
                step="100"
                value={newReturnPayoutAmount}
                onChange={(event) => setNewReturnPayoutAmount(event.target.value)}
                style={fieldStyle}
                placeholder="Ödenen tutar"
              />
              <input
                value={newReturnNotes}
                onChange={(event) => setNewReturnNotes(event.target.value)}
                style={fieldStyle}
                placeholder="İade notu"
              />
            </div>
            {boxError ? <div style={{ color: "#b42318", lineHeight: 1.6 }}>{boxError}</div> : null}
            {boxMessage ? <div style={{ color: "#0f766e", lineHeight: 1.6 }}>{boxMessage}</div> : null}
            <button
              type="submit"
              disabled={!canManageBoxReturn || boxBusy}
              style={{
                ...fieldStyle,
                cursor: canManageBoxReturn && !boxBusy ? "pointer" : "not-allowed",
                background: "linear-gradient(135deg, #1f5f4a, #328167)",
                color: "#f6fff7",
                border: "none",
                fontWeight: 800,
              }}
            >
              {boxBusy ? "Kaydediliyor..." : "Box geri alımını kaydet"}
            </button>
          </form>

          <div style={{ display: "grid", gap: "10px" }}>
            <div style={{ fontWeight: 800 }}>Seçili personelin box geçmişi</div>
            {!boxEntries.length ? (
              <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                Bu personele ait box geri alım kaydı henüz yok.
              </div>
            ) : (
              <div style={{ display: "grid", gap: "10px" }}>
                <select
                  value={selectedBoxId ?? ""}
                  onChange={(event) => setSelectedBoxId(Number(event.target.value))}
                  style={fieldStyle}
                >
                  {boxEntries.map((entry) => (
                    <option key={entry.id} value={entry.id}>
                      {`${formatDate(entry.return_date)} | ${entry.quantity} adet | ${entry.condition_status} | #${entry.id}`}
                    </option>
                  ))}
                </select>

                {selectedBoxEntry ? (
                  <div style={{ display: "grid", gap: "12px" }}>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                      {smallPill(
                        selectedBoxEntry.waived ? "Parasını istemedi" : "Ödemeli dönüş",
                        selectedBoxEntry.waived ? "accent" : "muted",
                      )}
                      {smallPill(formatCurrency(selectedBoxEntry.payout_amount))}
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px" }}>
                      <input
                        type="date"
                        value={editReturnDate}
                        onChange={(event) => setEditReturnDate(event.target.value)}
                        style={fieldStyle}
                      />
                      <select
                        value={editReturnConditionStatus}
                        onChange={(event) => setEditReturnConditionStatus(event.target.value)}
                        style={fieldStyle}
                      >
                        {options.return_condition_options.map((condition) => (
                          <option key={condition} value={condition}>
                            {condition}
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        min="1"
                        value={editReturnQuantity}
                        onChange={(event) => setEditReturnQuantity(event.target.value)}
                        style={fieldStyle}
                      />
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 180px) minmax(0, 1fr)", gap: "12px" }}>
                      <input
                        type="number"
                        min="0"
                        step="100"
                        value={editReturnPayoutAmount}
                        onChange={(event) => setEditReturnPayoutAmount(event.target.value)}
                        style={fieldStyle}
                      />
                      <input
                        value={editReturnNotes}
                        onChange={(event) => setEditReturnNotes(event.target.value)}
                        style={fieldStyle}
                        placeholder="İade notu"
                      />
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "12px" }}>
                      <button
                        type="button"
                        onClick={() => void handleUpdateBoxReturn()}
                        disabled={!canManageBoxReturn || boxBusy}
                        style={{
                          ...fieldStyle,
                          cursor: canManageBoxReturn && !boxBusy ? "pointer" : "not-allowed",
                          background: "rgba(15,95,215,0.1)",
                          color: "#0f5fd7",
                          fontWeight: 800,
                        }}
                      >
                        Kaydı güncelle
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleDeleteBoxReturn()}
                        disabled={!canManageBoxReturn || boxBusy}
                        style={{
                          ...fieldStyle,
                          cursor: canManageBoxReturn && !boxBusy ? "pointer" : "not-allowed",
                          background: "rgba(180,35,24,0.08)",
                          color: "#b42318",
                          fontWeight: 800,
                        }}
                      >
                        Kaydı sil
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </article>
      </div>
    </section>
  );
}
