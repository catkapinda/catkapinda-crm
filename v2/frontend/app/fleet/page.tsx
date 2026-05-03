"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import FleetMotorWorkbench, {
  type FleetMotorRecord,
} from "../../components/fleet/FleetMotorWorkbench";
import { AppShell } from "../../components/shell/app-shell";
import { apiErrorMessage, apiFetch } from "../../lib/api";

type PersonnelVehicleCandidateEntry = {
  id: number;
  person_code: string;
  full_name: string;
  role: string;
  status: string;
  restaurant_label: string;
  vehicle_mode: string;
  current_plate: string;
  motor_rental_monthly_amount: number;
  motor_purchase_start_date: string | null;
  motor_purchase_commitment_months: number;
  motor_purchase_sale_price: number;
  motor_purchase_monthly_deduction: number;
  vehicle_history_count: number;
};

type PersonnelVehicleHistoryEntry = {
  id: number;
  personnel_id: number;
  person_code: string;
  full_name: string;
  role: string;
  status: string;
  restaurant_label: string;
  vehicle_mode: string;
  current_plate: string;
  motor_rental_monthly_amount: number;
  motor_purchase_start_date: string | null;
  motor_purchase_commitment_months: number;
  motor_purchase_sale_price: number;
  motor_purchase_monthly_deduction: number;
  effective_date: string | null;
  notes: string;
};

type PersonnelVehicleWorkspaceResponse = {
  summary: {
    total_history_records: number;
    active_catkapinda_vehicle_personnel: number;
    rental_cards: number;
    sale_cards: number;
  };
  people: PersonnelVehicleCandidateEntry[];
  history: PersonnelVehicleHistoryEntry[];
};

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

type FleetOwnershipType = FleetMotorRecord["ownershipType"];
type FleetStatus = FleetMotorRecord["status"];
type FleetMaintenanceSummary = NonNullable<FleetMotorRecord["maintenanceSummary"]>;
type FleetMaintenanceRecord = NonNullable<FleetMotorRecord["maintenanceRecords"]>[number];
type FleetPaymentSummary = NonNullable<FleetMotorRecord["paymentSummary"]>;
type FleetPaymentRecord = NonNullable<FleetMotorRecord["paymentRecords"]>[number];

const pageSectionStyle = {
  display: "grid",
  gap: "18px",
} as const;

const noticeStyle = {
  padding: "18px 20px",
  borderRadius: "22px",
  border: "1px solid rgba(15, 95, 215, 0.14)",
  background: "rgba(15, 95, 215, 0.06)",
  color: "var(--muted)",
  lineHeight: 1.7,
} as const;

function normalizeText(value: string | null | undefined) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[ıİ]/g, "i")
    .toLowerCase()
    .trim();
}

function toOwnershipType(value: string): FleetOwnershipType {
  const normalized = normalizeText(value);
  if (normalized.includes("satis")) {
    return "Çat Kapında Satılık";
  }
  if (normalized.includes("kira")) {
    return "Çat Kapında Kiralık";
  }
  return "Kendi Motoru";
}

function toMotorStatus(person: PersonnelVehicleCandidateEntry, ownershipType: FleetOwnershipType): FleetStatus {
  const normalizedStatus = normalizeText(person.status);
  if (normalizedStatus === "pasif") {
    return ownershipType === "Çat Kapında Satılık" ? "Satıldı" : "Pasif";
  }
  return "Aktif";
}

function buildMotorCode(person: PersonnelVehicleCandidateEntry) {
  return `MTR-${String(person.id).padStart(5, "0")}`;
}

function formatDateLabel(value: string | null | undefined) {
  if (!value) {
    return "—";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(parsed);
}

function formatMoneyLabel(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }
  return `${new Intl.NumberFormat("tr-TR", {
    maximumFractionDigits: value % 1 === 0 ? 0 : 2,
  }).format(value)} ₺`;
}

function computeMonthlyAmount(
  person: PersonnelVehicleCandidateEntry,
  ownershipType: FleetOwnershipType,
): number | null {
  if (ownershipType === "Kendi Motoru") {
    return 0;
  }
  if (ownershipType === "Çat Kapında Kiralık") {
    return person.motor_rental_monthly_amount > 0 ? person.motor_rental_monthly_amount : null;
  }
  if (person.motor_purchase_monthly_deduction > 0) {
    return person.motor_purchase_monthly_deduction;
  }
  if (person.motor_purchase_sale_price > 0 && person.motor_purchase_commitment_months > 0) {
    return Number(
      (person.motor_purchase_sale_price / person.motor_purchase_commitment_months).toFixed(2),
    );
  }
  return null;
}

function computeStartDate(
  person: PersonnelVehicleCandidateEntry,
  ownershipType: FleetOwnershipType,
  historyRows: PersonnelVehicleHistoryEntry[],
): string | null {
  if (ownershipType === "Çat Kapında Satılık" && person.motor_purchase_start_date) {
    return person.motor_purchase_start_date;
  }

  const matchingRow = historyRows.find(
    (row) => toOwnershipType(row.vehicle_mode) === ownershipType && row.effective_date,
  );
  if (matchingRow?.effective_date) {
    return matchingRow.effective_date;
  }

  if (ownershipType === "Çat Kapında Satılık") {
    return person.motor_purchase_start_date;
  }

  return null;
}

function computeNextPaymentDate(startDate: string | null, monthlyAmount: number | null) {
  if (!startDate || !monthlyAmount || monthlyAmount <= 0) {
    return null;
  }

  const parsed = new Date(startDate);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  const today = new Date();
  const dueDay = parsed.getDate();

  const nextCandidate = new Date(today.getFullYear(), today.getMonth(), dueDay);
  if (nextCandidate <= today) {
    nextCandidate.setMonth(nextCandidate.getMonth() + 1);
  }

  if (Number.isNaN(nextCandidate.getTime())) {
    return null;
  }

  return nextCandidate.toISOString().slice(0, 10);
}

function buildPaidInstallmentsLabel(
  person: PersonnelVehicleCandidateEntry,
  ownershipType: FleetOwnershipType,
  monthlyAmount: number | null,
) {
  if (ownershipType === "Kendi Motoru") {
    return "Kira yok";
  }
  if (ownershipType === "Çat Kapında Satılık" && person.motor_purchase_commitment_months > 0) {
    return `${person.motor_purchase_commitment_months} ay taahhüt`;
  }
  if (monthlyAmount && monthlyAmount > 0) {
    return `${formatMoneyLabel(monthlyAmount)} aylık plan`;
  }
  return "Kayıtlı plan yok";
}

function isMaintenanceDeductionType(value: string) {
  const normalized = normalizeText(value);
  return normalized.includes("motor servis") || normalized.includes("motor hasar");
}

function isMotorPaymentDeductionType(value: string) {
  const normalized = normalizeText(value);
  return normalized.includes("motor kiras") || normalized.includes("motor satis");
}

function formatMaintenanceItemLabel(value: string | null | undefined) {
  const raw = String(value || "").trim();
  const normalized = normalizeText(raw);

  if (!raw) {
    return "Bakım Masrafı";
  }
  if (normalized.includes("motor servis")) {
    return "Periyodik Bakım";
  }
  if (normalized.includes("motor hasar")) {
    return "Hasar / Onarım";
  }
  return raw;
}

function formatMaintenanceDescription(entry: DeductionEntry) {
  const note = entry.notes?.trim();
  if (note) {
    return note;
  }
  const caption = String(entry.type_caption || "").trim();
  if (caption) {
    return caption;
  }
  return `${formatMaintenanceItemLabel(entry.deduction_type)} kaydı`;
}

function buildMaintenanceData(
  person: PersonnelVehicleCandidateEntry,
  deductions: DeductionEntry[],
) {
  const relevant = deductions
    .filter((entry) => entry.personnel_id === person.id && isMaintenanceDeductionType(entry.deduction_type))
    .sort((left, right) => {
      const leftTime = left.deduction_date ? new Date(left.deduction_date).getTime() : 0;
      const rightTime = right.deduction_date ? new Date(right.deduction_date).getTime() : 0;
      return rightTime - leftTime;
    });

  if (!relevant.length) {
    return {
      summary: {
        totalCost: "—",
        lastServiceDate: "—",
        nextServiceDate: "—",
        averageMonthlyCost: "—",
      } satisfies FleetMaintenanceSummary,
      records: [] as FleetMaintenanceRecord[],
      items: [
        { label: "Bakım Kayıtları", value: "—" },
        { label: "Toplam Bakım Masrafı", value: "—" },
        { label: "Son Kayıt", value: "—" },
        { label: "Not", value: "Kayıtlı bakım / masraf bulunmuyor." },
      ],
    };
  }

  const totalAmount = relevant.reduce((sum, entry) => sum + Number(entry.amount || 0), 0);
  const latest = relevant[0];
  const monthCount = new Set(
    relevant.map((entry) => String(entry.deduction_date || "").slice(0, 7)).filter(Boolean),
  ).size;
  const items = relevant.slice(0, 3).map((entry) => ({
    label: `${formatDateLabel(entry.deduction_date)} • ${formatMaintenanceItemLabel(entry.deduction_type)}`,
    value: `${formatMoneyLabel(entry.amount)}${entry.notes ? ` • ${entry.notes}` : ""}`,
  }));

  return {
    summary: {
      totalCost: formatMoneyLabel(totalAmount),
      lastServiceDate: formatDateLabel(latest.deduction_date),
      nextServiceDate: "—",
      averageMonthlyCost: formatMoneyLabel(monthCount > 0 ? totalAmount / monthCount : 0),
    } satisfies FleetMaintenanceSummary,
    records: relevant.map((entry) => ({
      date: formatDateLabel(entry.deduction_date),
      item: formatMaintenanceItemLabel(entry.deduction_type),
      description: formatMaintenanceDescription(entry),
      amount: formatMoneyLabel(entry.amount),
    })) satisfies FleetMaintenanceRecord[],
    items: [
      { label: "Toplam Bakım Masrafı", value: formatMoneyLabel(totalAmount) },
      {
        label: "Son Kayıt",
        value: `${formatDateLabel(latest.deduction_date)} • ${formatMaintenanceItemLabel(latest.deduction_type)}`,
      },
      ...items,
    ],
  };
}

function buildPaymentData(
  person: PersonnelVehicleCandidateEntry,
  ownershipType: FleetOwnershipType,
  deductions: DeductionEntry[],
  startDate: string | null,
  monthlyAmount: number | null,
) {
  const relevant = deductions
    .filter((entry) => entry.personnel_id === person.id && isMotorPaymentDeductionType(entry.deduction_type))
    .sort((left, right) => {
      const leftTime = left.deduction_date ? new Date(left.deduction_date).getTime() : 0;
      const rightTime = right.deduction_date ? new Date(right.deduction_date).getTime() : 0;
      return rightTime - leftTime;
    });

  const totalPaidRaw = relevant.reduce((sum, entry) => sum + Number(entry.amount || 0), 0);
  const latest = relevant[0];
  const remainingRaw =
    ownershipType === "Çat Kapında Satılık" && person.motor_purchase_sale_price > 0
      ? Math.max(person.motor_purchase_sale_price - totalPaidRaw, 0)
      : null;

  const records: FleetPaymentRecord[] = [];
  if (startDate) {
    records.push({
      date: formatDateLabel(startDate),
      label: ownershipType,
      amount: formatMoneyLabel(monthlyAmount),
    });
  }
  relevant.slice(0, 8).forEach((entry) => {
    records.push({
      date: formatDateLabel(entry.deduction_date),
      label: entry.deduction_type || entry.type_caption || "Ödeme kaydı",
      amount: formatMoneyLabel(entry.amount),
    });
  });

  return {
    totalPaidRaw,
    summary: {
      monthlyAmount: formatMoneyLabel(monthlyAmount),
      startDate: formatDateLabel(startDate),
      totalPaid: relevant.length ? formatMoneyLabel(totalPaidRaw) : "—",
      remainingPayment: remainingRaw !== null ? formatMoneyLabel(remainingRaw) : "—",
      lastPayment: latest ? formatDateLabel(latest.deduction_date) : "—",
      nextPayment: formatDateLabel(computeNextPaymentDate(startDate, monthlyAmount)),
    } satisfies FleetPaymentSummary,
    records,
  };
}

function mapVehicleWorkspaceToMotors(
  workspace: PersonnelVehicleWorkspaceResponse | null,
  deductions: DeductionEntry[],
): FleetMotorRecord[] {
  if (!workspace) {
    return [];
  }

  const historyByPerson = workspace.history.reduce<Record<number, PersonnelVehicleHistoryEntry[]>>(
    (accumulator, row) => {
      const bucket = accumulator[row.personnel_id] ?? [];
      bucket.push(row);
      accumulator[row.personnel_id] = bucket;
      return accumulator;
    },
    {},
  );

  return workspace.people
    .map((person) => {
      const ownershipType = toOwnershipType(person.vehicle_mode);
      const personHistory = [...(historyByPerson[person.id] ?? [])].sort((left, right) => {
        const leftTime = left.effective_date ? new Date(left.effective_date).getTime() : 0;
        const rightTime = right.effective_date ? new Date(right.effective_date).getTime() : 0;
        return rightTime - leftTime;
      });
      const monthlyAmount = computeMonthlyAmount(person, ownershipType);
      const startDate = computeStartDate(person, ownershipType, personHistory);
      const latestNote = personHistory.find((entry) => entry.notes?.trim())?.notes?.trim() ?? "";
      const status = toMotorStatus(person, ownershipType);
      const maintenanceData = buildMaintenanceData(person, deductions);
      const paymentData = buildPaymentData(person, ownershipType, deductions, startDate, monthlyAmount);

      return {
        id: `fleet-${person.id}`,
        code: buildMotorCode(person),
        plate: person.current_plate?.trim() || "—",
        model: person.current_plate?.trim() || ownershipType,
        type: ownershipType,
        ownershipType,
        status,
        assigneeName: person.full_name?.trim() || null,
        assigneeRole: person.role?.trim() || null,
        monthlyAmount,
        startDate,
        nextPaymentDate: computeNextPaymentDate(startDate, monthlyAmount),
        totalPaid: paymentData.totalPaidRaw || null,
        paidInstallmentsLabel: buildPaidInstallmentsLabel(person, ownershipType, monthlyAmount),
        notes: latestNote || (person.restaurant_label?.trim() && person.restaurant_label !== "-" ? `${person.restaurant_label} ataması` : "—"),
        modelYear: "—",
        color: "—",
        chassisNo: "—",
        engineNo: "—",
        branchLabel: person.restaurant_label?.trim() && person.restaurant_label !== "-" ? person.restaurant_label : null,
        maintenanceSummary: maintenanceData.summary,
        maintenanceRecords: maintenanceData.records,
        paymentSummary: paymentData.summary,
        paymentRecords: paymentData.records,
        rentalHistory:
          ownershipType === "Çat Kapında Satılık"
            ? [
                { label: "Satış Başlangıcı", value: formatDateLabel(startDate) },
                { label: "Aylık Taksit", value: formatMoneyLabel(monthlyAmount) },
                {
                  label: "Toplam Satış Bedeli",
                  value: formatMoneyLabel(person.motor_purchase_sale_price || null),
                },
                {
                  label: "Taahhüt Süresi",
                  value:
                    person.motor_purchase_commitment_months > 0
                      ? `${person.motor_purchase_commitment_months} ay`
                      : "—",
                },
              ]
            : ownershipType === "Çat Kapında Kiralık"
              ? [
                  { label: "Kira Başlangıcı", value: formatDateLabel(startDate) },
                  { label: "Aylık Kira", value: formatMoneyLabel(monthlyAmount) },
                  { label: "Şube / Restoran", value: person.restaurant_label || "—" },
                  { label: "Plaka", value: person.current_plate?.trim() || "—" },
                ]
              : [
                  { label: "Kayıt Tipi", value: "Kendi Motoru" },
                  { label: "Güncel Plaka", value: person.current_plate?.trim() || "—" },
                  { label: "Şube / Restoran", value: person.restaurant_label || "—" },
                  { label: "Son Geçiş", value: formatDateLabel(personHistory[0]?.effective_date ?? null) },
                ],
        maintenanceItems: maintenanceData.items,
        ownershipHistory:
          personHistory.length > 0
            ? personHistory.map((entry) => ({
                label: formatDateLabel(entry.effective_date),
                value: [entry.vehicle_mode || "—", entry.notes || ""].filter(Boolean).join(" • "),
              }))
            : [{ label: "—", value: "Geçiş kaydı bulunmuyor." }],
        documents: [],
        movements:
          personHistory.length > 0
            ? personHistory.map((entry) => ({
                title: entry.vehicle_mode || "Motor geçiş kaydı",
                meta: formatDateLabel(entry.effective_date),
                actor: "Sistem",
                tone:
                  toOwnershipType(entry.vehicle_mode) === "Çat Kapında Satılık"
                    ? "warning"
                    : toOwnershipType(entry.vehicle_mode) === "Çat Kapında Kiralık"
                      ? "positive"
                      : "neutral",
              }))
            : [
                {
                  title: `${ownershipType} kaydı aktif.`,
                  meta: person.restaurant_label || "Kayıtlı şube yok",
                  actor: "Sistem",
                  tone: ownershipType === "Kendi Motoru" ? "neutral" : "positive",
                },
              ],
      } satisfies FleetMotorRecord;
    })
    .sort((left, right) => {
      const statusWeight = (value: FleetStatus) =>
        value === "Aktif" ? 0 : value === "Bakımda" ? 1 : value === "Pasif" ? 2 : 3;
      const statusDelta = statusWeight(left.status) - statusWeight(right.status);
      if (statusDelta !== 0) {
        return statusDelta;
      }
      return left.code.localeCompare(right.code, "tr");
    });
}

export default function FleetPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [workspace, setWorkspace] = useState<PersonnelVehicleWorkspaceResponse | null>(null);
  const [deductions, setDeductions] = useState<DeductionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadWorkspace() {
      if (authLoading) {
        return;
      }
      if (!user) {
        if (active) {
          setWorkspace(null);
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      setError("");
      try {
        const [workspaceResponse, deductionsResponse] = await Promise.all([
          apiFetch("/personnel/vehicle-workspace?limit=500"),
          user.allowed_actions?.includes("deduction.view")
            ? apiFetch("/deductions/records?limit=400")
            : Promise.resolve(null),
        ]);

        if (!workspaceResponse.ok) {
          throw new Error(
            await apiErrorMessage(workspaceResponse, "Motor yönetimi verileri yüklenemedi."),
          );
        }
        const payload = (await workspaceResponse.json()) as PersonnelVehicleWorkspaceResponse;
        if (active) {
          setWorkspace(payload);
          if (deductionsResponse && deductionsResponse.ok) {
            const deductionsPayload = (await deductionsResponse.json()) as DeductionsManagementResponse;
            setDeductions(deductionsPayload.entries ?? []);
          } else {
            setDeductions([]);
          }
        }
      } catch (nextError) {
        if (active) {
          setWorkspace(null);
          setDeductions([]);
          setError(
            nextError instanceof Error ? nextError.message : "Motor yönetimi verileri yüklenemedi.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadWorkspace();
    return () => {
      active = false;
    };
  }, [authLoading, user]);

  const mappedMotors = useMemo(
    () => mapVehicleWorkspaceToMotors(workspace, deductions),
    [workspace, deductions],
  );

  return (
    <AppShell activeItem="Filo">
      <section style={pageSectionStyle}>
        {loading ? (
          <div style={noticeStyle}>Motor yönetimi verileri yükleniyor...</div>
        ) : null}
        {!loading && error ? <div style={noticeStyle}>{error}</div> : null}
        {!loading && !error ? (
          <FleetMotorWorkbench
            motors={mappedMotors}
            onCreateMotor={() => router.push("/personnel#personnel-vehicle")}
            onOpenAssignee={() => router.push("/personnel")}
          />
        ) : null}
      </section>
    </AppShell>
  );
}
