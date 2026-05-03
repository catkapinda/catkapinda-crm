"use client";

import { useMemo, useState, type ReactNode } from "react";
import {
  Bike,
  Calendar,
  ChevronRight,
  Download,
  FileText,
  FilterX,
  MoreHorizontal,
  Plus,
  Search,
  ShieldCheck,
  UserRound,
  Wallet,
  Wrench,
} from "lucide-react";

import styles from "./FleetMotorWorkbench.module.css";

type FleetOwnershipType = "Kendi Motoru" | "Çat Kapında Kiralık" | "Çat Kapında Satılık";
type FleetStatus = "Aktif" | "Bakımda" | "Pasif" | "Satıldı";

type FleetMovement = {
  title: string;
  meta: string;
  actor: string;
  tone?: "positive" | "neutral" | "warning";
};

type FleetDocument = {
  label: string;
  description: string;
};

type FleetMotorRecord = {
  id: string;
  code: string;
  plate: string;
  model: string;
  type: string;
  ownershipType: FleetOwnershipType;
  status: FleetStatus;
  assigneeName: string | null;
  assigneeRole: string | null;
  monthlyAmount: number | null;
  startDate: string | null;
  nextPaymentDate: string | null;
  totalPaid: number | null;
  paidInstallmentsLabel: string;
  notes: string;
  modelYear: string;
  color: string;
  chassisNo: string;
  engineNo: string;
  branchLabel: string | null;
  rentalHistory: Array<{
    label: string;
    value: string;
  }>;
  maintenanceItems: Array<{
    label: string;
    value: string;
  }>;
  ownershipHistory: Array<{
    label: string;
    value: string;
  }>;
  documents: FleetDocument[];
  movements: FleetMovement[];
};

type FleetMotorWorkbenchProps = {
  motors?: FleetMotorRecord[];
  onCreateMotor?: () => void;
  onDownloadHistoryPdf?: (motor: FleetMotorRecord) => void | Promise<void>;
  onOpenAssignee?: (motor: FleetMotorRecord) => void | Promise<void>;
};

const MOCK_MOTORS: FleetMotorRecord[] = [
  {
    id: "mtr-23",
    code: "MTR-00023",
    plate: "34 KPK 123",
    model: "Honda Dio",
    type: "Honda Dio",
    ownershipType: "Çat Kapında Kiralık",
    status: "Aktif",
    assigneeName: "Ahmet Yılmaz",
    assigneeRole: "Motorlu Kurye",
    monthlyAmount: 2500,
    startDate: "2025-02-01",
    nextPaymentDate: "2025-06-01",
    totalPaid: 7500,
    paidInstallmentsLabel: "3 ay / 3 ödeme",
    notes:
      "Motor yeni kiralanmıştır. İlk 3 ay kira ₺2.500, 4. aydan itibaren ₺2.800 olacaktır.",
    modelYear: "2023",
    color: "Siyah",
    chassisNo: "DIO-2023-00023",
    engineNo: "ENG-2023-00023",
    branchLabel: "Merkez Operasyon",
    rentalHistory: [
      { label: "Kira Başlangıcı", value: "01.02.2025" },
      { label: "Son Ödeme", value: "01.05.2025" },
      { label: "Bir Sonraki Ödeme", value: "01.06.2025" },
      { label: "Aylık Kira", value: "₺2.500" },
    ],
    maintenanceItems: [
      { label: "Son Servis", value: "12.05.2025 • Yağ bakımı" },
      { label: "Açık Masraf", value: "Yok" },
      { label: "Lastik Durumu", value: "İyi" },
      { label: "Sigorta", value: "31.12.2025" },
    ],
    ownershipHistory: [
      { label: "01.02.2025", value: "Çat Kapında Kiralık olarak filoya eklendi" },
      { label: "01.02.2025", value: "Ahmet Yılmaz kişisine zimmetlendi" },
      { label: "01.05.2025", value: "3. kira ödemesi işlendi" },
    ],
    documents: [
      { label: "Kira Sözleşmesi", description: "PDF • 01.02.2025" },
      { label: "Servis Fişi", description: "PDF • 12.05.2025" },
    ],
    movements: [
      {
        title: "Motor kiralama sözleşmesi oluşturuldu.",
        meta: "01.02.2025 11:30",
        actor: "Yönetici",
        tone: "positive",
      },
      {
        title: "Ahmet Yılmaz kişisine zimmetlendi.",
        meta: "01.02.2025 11:32",
        actor: "Yönetici",
      },
      {
        title: "Aylık kira ₺2.500 olarak belirlendi.",
        meta: "01.02.2025 11:33",
        actor: "Sistem",
      },
    ],
  },
  {
    id: "mtr-24",
    code: "MTR-00024",
    plate: "34 KPT 148",
    model: "Honda PCX",
    type: "Honda PCX",
    ownershipType: "Çat Kapında Kiralık",
    status: "Aktif",
    assigneeName: "Mehmet Demir",
    assigneeRole: "Kurye",
    monthlyAmount: 2500,
    startDate: "2025-02-18",
    nextPaymentDate: "2025-06-18",
    totalPaid: 7500,
    paidInstallmentsLabel: "3 ay / 3 ödeme",
    notes: "Mayıs sonu genel bakım planlandı.",
    modelYear: "2024",
    color: "Beyaz",
    chassisNo: "PCX-2024-00024",
    engineNo: "ENG-2024-00024",
    branchLabel: "Avrupa Yakası",
    rentalHistory: [
      { label: "Kira Başlangıcı", value: "18.02.2025" },
      { label: "Son Ödeme", value: "18.05.2025" },
      { label: "Bir Sonraki Ödeme", value: "18.06.2025" },
      { label: "Aylık Kira", value: "₺2.500" },
    ],
    maintenanceItems: [
      { label: "Son Servis", value: "03.05.2025 • Fren kontrolü" },
      { label: "Açık Masraf", value: "₺0" },
      { label: "Lastik Durumu", value: "İyi" },
      { label: "Sigorta", value: "31.12.2025" },
    ],
    ownershipHistory: [{ label: "18.02.2025", value: "Mehmet Demir kişisine zimmetlendi" }],
    documents: [{ label: "Kira Sözleşmesi", description: "PDF • 18.02.2025" }],
    movements: [
      {
        title: "Mehmet Demir için kira kaydı açıldı.",
        meta: "18.02.2025 09:12",
        actor: "Sistem",
      },
    ],
  },
  {
    id: "mtr-25",
    code: "MTR-00025",
    plate: "34 KDY 902",
    model: "Honda Dio",
    type: "Honda Dio",
    ownershipType: "Kendi Motoru",
    status: "Aktif",
    assigneeName: "Burak Şahin",
    assigneeRole: "Kurye",
    monthlyAmount: 0,
    startDate: "2025-01-05",
    nextPaymentDate: null,
    totalPaid: 0,
    paidInstallmentsLabel: "Kira yok",
    notes: "Şahsi motor. Filoda sadece takip amaçlı görünür.",
    modelYear: "2022",
    color: "Mavi",
    chassisNo: "DIO-2022-00025",
    engineNo: "ENG-2022-00025",
    branchLabel: "Anadolu Yakası",
    rentalHistory: [
      { label: "Kayıt Tipi", value: "Şahsi motor" },
      { label: "Aylık Kira", value: "₺0" },
      { label: "Son Güncelleme", value: "05.01.2025" },
      { label: "Atama", value: "Burak Şahin" },
    ],
    maintenanceItems: [
      { label: "Son Servis", value: "Takip edilmiyor" },
      { label: "Açık Masraf", value: "Yok" },
      { label: "Lastik Durumu", value: "—" },
      { label: "Sigorta", value: "—" },
    ],
    ownershipHistory: [{ label: "05.01.2025", value: "Şahsi motor olarak kaydedildi" }],
    documents: [],
    movements: [
      {
        title: "Şahsi motor kaydı oluşturuldu.",
        meta: "05.01.2025 08:40",
        actor: "Yönetici",
      },
    ],
  },
  {
    id: "mtr-26",
    code: "MTR-00026",
    plate: "34 KSA 311",
    model: "Honda PCX",
    type: "Honda PCX",
    ownershipType: "Çat Kapında Satılık",
    status: "Satıldı",
    assigneeName: null,
    assigneeRole: null,
    monthlyAmount: 0,
    startDate: "2024-11-01",
    nextPaymentDate: null,
    totalPaid: 22500,
    paidInstallmentsLabel: "Satış tamamlandı",
    notes: "Motor satış süreci kapandı, aktif listede gizlenir.",
    modelYear: "2023",
    color: "Gri",
    chassisNo: "PCX-2023-00026",
    engineNo: "ENG-2023-00026",
    branchLabel: null,
    rentalHistory: [
      { label: "Satış Başlangıcı", value: "01.11.2024" },
      { label: "Son Tahsilat", value: "01.04.2025" },
      { label: "Aylık Taksit", value: "₺7.500" },
      { label: "Durum", value: "Satıldı" },
    ],
    maintenanceItems: [
      { label: "Son Servis", value: "Yok" },
      { label: "Açık Masraf", value: "Yok" },
      { label: "Lastik Durumu", value: "—" },
      { label: "Sigorta", value: "—" },
    ],
    ownershipHistory: [
      { label: "01.11.2024", value: "Çat Kapında Satılık olarak çıkarıldı" },
      { label: "01.04.2025", value: "Satış kapandı" },
    ],
    documents: [{ label: "Satış Sözleşmesi", description: "PDF • 01.11.2024" }],
    movements: [
      {
        title: "Satış süreci tamamlandı.",
        meta: "01.04.2025 16:25",
        actor: "Finans",
        tone: "warning",
      },
    ],
  },
  {
    id: "mtr-27",
    code: "MTR-00027",
    plate: "34 KRM 882",
    model: "Honda Dio",
    type: "Honda Dio",
    ownershipType: "Çat Kapında Kiralık",
    status: "Bakımda",
    assigneeName: "Ali Can",
    assigneeRole: "Kurye",
    monthlyAmount: 2500,
    startDate: "2025-03-01",
    nextPaymentDate: "2025-06-01",
    totalPaid: 5000,
    paidInstallmentsLabel: "2 ay / 2 ödeme",
    notes: "Ön fren disk değişimi bekleniyor.",
    modelYear: "2024",
    color: "Beyaz",
    chassisNo: "DIO-2024-00027",
    engineNo: "ENG-2024-00027",
    branchLabel: "Beşiktaş Hub",
    rentalHistory: [
      { label: "Kira Başlangıcı", value: "01.03.2025" },
      { label: "Son Ödeme", value: "01.05.2025" },
      { label: "Bir Sonraki Ödeme", value: "01.06.2025" },
      { label: "Aylık Kira", value: "₺2.500" },
    ],
    maintenanceItems: [
      { label: "Açık Masraf", value: "₺1.850 • Fren disk" },
      { label: "Servis Tarihi", value: "06.05.2025" },
      { label: "Servis Noktası", value: "Çekmeköy Yetkili Servis" },
      { label: "Durum", value: "Parça bekleniyor" },
    ],
    ownershipHistory: [{ label: "06.05.2025", value: "Bakım statüsüne alındı" }],
    documents: [{ label: "Servis Teklifi", description: "PDF • 06.05.2025" }],
    movements: [
      {
        title: "Bakım kaydı açıldı.",
        meta: "06.05.2025 10:08",
        actor: "Filo",
        tone: "warning",
      },
    ],
  },
  {
    id: "mtr-28",
    code: "MTR-00028",
    plate: "34 KAN 542",
    model: "Honda Dio",
    type: "Honda Dio",
    ownershipType: "Çat Kapında Kiralık",
    status: "Aktif",
    assigneeName: "Emre Kaya",
    assigneeRole: "Kurye",
    monthlyAmount: 2500,
    startDate: "2025-04-11",
    nextPaymentDate: "2025-06-11",
    totalPaid: 2500,
    paidInstallmentsLabel: "1 ay / 1 ödeme",
    notes: "İlk kira ödemesi işlendi.",
    modelYear: "2024",
    color: "Kırmızı",
    chassisNo: "DIO-2024-00028",
    engineNo: "ENG-2024-00028",
    branchLabel: "Merkez Operasyon",
    rentalHistory: [
      { label: "Kira Başlangıcı", value: "11.04.2025" },
      { label: "Son Ödeme", value: "11.05.2025" },
      { label: "Bir Sonraki Ödeme", value: "11.06.2025" },
      { label: "Aylık Kira", value: "₺2.500" },
    ],
    maintenanceItems: [
      { label: "Son Servis", value: "Yok" },
      { label: "Açık Masraf", value: "Yok" },
      { label: "Lastik Durumu", value: "Yeni" },
      { label: "Sigorta", value: "31.12.2025" },
    ],
    ownershipHistory: [{ label: "11.04.2025", value: "Emre Kaya kişisine atandı" }],
    documents: [{ label: "Kira Sözleşmesi", description: "PDF • 11.04.2025" }],
    movements: [
      {
        title: "Yeni atama tamamlandı.",
        meta: "11.04.2025 13:22",
        actor: "Yönetici",
        tone: "positive",
      },
    ],
  },
  {
    id: "mtr-29",
    code: "MTR-00029",
    plate: "34 KGD 775",
    model: "Honda Dio",
    type: "Honda Dio",
    ownershipType: "Çat Kapında Kiralık",
    status: "Pasif",
    assigneeName: "Atanmamış",
    assigneeRole: null,
    monthlyAmount: 0,
    startDate: null,
    nextPaymentDate: null,
    totalPaid: 0,
    paidInstallmentsLabel: "Atama bekliyor",
    notes: "Depoda bekleyen yedek araç.",
    modelYear: "2023",
    color: "Siyah",
    chassisNo: "DIO-2023-00029",
    engineNo: "ENG-2023-00029",
    branchLabel: "Depo",
    rentalHistory: [
      { label: "Durum", value: "Atanmamış" },
      { label: "Aylık Kira", value: "₺0" },
      { label: "Son Güncelleme", value: "02.05.2025" },
      { label: "Not", value: "Depoda bekliyor" },
    ],
    maintenanceItems: [
      { label: "Son Servis", value: "20.04.2025 • Genel kontrol" },
      { label: "Açık Masraf", value: "Yok" },
      { label: "Lastik Durumu", value: "İyi" },
      { label: "Sigorta", value: "31.12.2025" },
    ],
    ownershipHistory: [{ label: "02.05.2025", value: "Atama boşa çıkarıldı" }],
    documents: [],
    movements: [
      {
        title: "Araç ataması kaldırıldı.",
        meta: "02.05.2025 17:10",
        actor: "Operasyon",
      },
    ],
  },
  {
    id: "mtr-30",
    code: "MTR-00030",
    plate: "34 KFY 661",
    model: "Honda PCX",
    type: "Honda PCX",
    ownershipType: "Çat Kapında Kiralık",
    status: "Aktif",
    assigneeName: "Fatih Ünal",
    assigneeRole: "Motorlu Kurye",
    monthlyAmount: 2500,
    startDate: "2025-05-01",
    nextPaymentDate: "2025-06-01",
    totalPaid: 0,
    paidInstallmentsLabel: "İlk ödeme bekleniyor",
    notes: "Yeni dönem için ayrıldı.",
    modelYear: "2024",
    color: "Lacivert",
    chassisNo: "PCX-2024-00030",
    engineNo: "ENG-2024-00030",
    branchLabel: "Kadıköy",
    rentalHistory: [
      { label: "Kira Başlangıcı", value: "01.05.2025" },
      { label: "Son Ödeme", value: "—" },
      { label: "Bir Sonraki Ödeme", value: "01.06.2025" },
      { label: "Aylık Kira", value: "₺2.500" },
    ],
    maintenanceItems: [
      { label: "Son Servis", value: "Araç yeni" },
      { label: "Açık Masraf", value: "Yok" },
      { label: "Lastik Durumu", value: "Yeni" },
      { label: "Sigorta", value: "31.12.2025" },
    ],
    ownershipHistory: [{ label: "01.05.2025", value: "Fatih Ünal kişisine zimmetlendi" }],
    documents: [{ label: "Kira Sözleşmesi", description: "PDF • 01.05.2025" }],
    movements: [
      {
        title: "İlk kira planı oluşturuldu.",
        meta: "01.05.2025 09:20",
        actor: "Sistem",
        tone: "positive",
      },
    ],
  },
];

const formatMoney = (value: number | null | undefined) => {
  if (value === null || value === undefined) return "—";
  return `${new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 }).format(value)} ₺`;
};

const formatDateLabel = (value: string | null | undefined) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
};

const getInitials = (value: string | null | undefined) => {
  if (!value) return "—";
  return value
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((item) => item[0])
    .join("")
    .toUpperCase();
};

const ownershipLabel = (value: FleetOwnershipType) => {
  if (value === "Çat Kapında Kiralık") return "Kiralık";
  if (value === "Çat Kapında Satılık") return "Satılık";
  return "Kendi Motoru";
};

const ownershipShortLabel = (value: FleetOwnershipType) => {
  if (value === "Çat Kapında Kiralık") return "Kiralık";
  if (value === "Çat Kapında Satılık") return "Satılık";
  return "Kendi";
};

export default function FleetMotorWorkbench({
  motors = MOCK_MOTORS,
  onCreateMotor,
  onDownloadHistoryPdf,
  onOpenAssignee,
}: FleetMotorWorkbenchProps) {
  const [selectedMotorId, setSelectedMotorId] = useState<string | null>(motors[0]?.id ?? null);
  const [statusFilter, setStatusFilter] = useState("Tümü");
  const [typeFilter, setTypeFilter] = useState("Tümü");
  const [ownershipFilter, setOwnershipFilter] = useState("Tümü");
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState("general");

  const statusOptions = useMemo(
    () => ["Tümü", "Aktif", "Bakımda", "Pasif", "Satıldı"],
    [],
  );
  const typeOptions = useMemo(
    () => ["Tümü", ...Array.from(new Set(motors.map((motor) => motor.type))).sort()],
    [motors],
  );
  const ownershipOptions = useMemo(
    () => ["Tümü", "Kendi Motoru", "Çat Kapında Kiralık", "Çat Kapında Satılık"],
    [],
  );

  const filteredMotors = useMemo(() => {
    const query = search.trim().toLowerCase();
    return motors.filter((motor) => {
      if (statusFilter !== "Tümü" && motor.status !== statusFilter) return false;
      if (typeFilter !== "Tümü" && motor.type !== typeFilter) return false;
      if (ownershipFilter !== "Tümü" && motor.ownershipType !== ownershipFilter) return false;
      if (!query) return true;
      const haystack = [
        motor.code,
        motor.plate,
        motor.model,
        motor.type,
        motor.assigneeName ?? "Atanmamış",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [motors, ownershipFilter, search, statusFilter, typeFilter]);

  const selectedMotor =
    filteredMotors.find((motor) => motor.id === selectedMotorId) ??
    motors.find((motor) => motor.id === selectedMotorId) ??
    filteredMotors[0] ??
    null;

  const resetFilters = () => {
    setStatusFilter("Tümü");
    setTypeFilter("Tümü");
    setOwnershipFilter("Tümü");
    setSearch("");
  };

  return (
    <section className={styles["ck-fm-workbench"]}>
      <header className={styles["ck-fm-header"]}>
        <div className={styles["ck-fm-heading"]}>
          <div className={styles["ck-fm-breadcrumbs"]}>
            <span>Filo</span>
            <ChevronRight size={16} />
            <span className={styles["ck-fm-breadcrumb-current"]}>Motor Yönetimi</span>
          </div>
          <h1>Motor Yönetimi</h1>
          <p>Motor kirası, motor satışı ve kendi motoru geçişlerini yönetin.</p>
        </div>

        <div className={styles["ck-fm-header-actions"]}>
          <label className={styles["ck-fm-search"]}>
            <Search size={18} />
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Motor ID, plaka veya kullanıcı ara..."
            />
            <span className={styles["ck-fm-shortcut"]}>⌘ K</span>
          </label>

          <button
            type="button"
            className={styles["ck-fm-primary-btn"]}
            onClick={() => onCreateMotor?.()}
          >
            <Plus size={18} />
            Yeni Motor Ekle
          </button>
        </div>
      </header>

      <section className={styles["ck-fm-filter-bar"]}>
        <label className={styles["ck-fm-filter-field"]}>
          <span>Durum</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label className={styles["ck-fm-filter-field"]}>
          <span>Tip</span>
          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            {typeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label className={styles["ck-fm-filter-field"]}>
          <span>Sahiplik</span>
          <select value={ownershipFilter} onChange={(event) => setOwnershipFilter(event.target.value)}>
            {ownershipOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <button type="button" className={styles["ck-fm-ghost-btn"]} onClick={resetFilters}>
          <FilterX size={16} />
          Filtreleri Temizle
        </button>
      </section>

      <div className={styles["ck-fm-main-grid"]}>
        <article className={styles["ck-fm-list-card"]}>
          <div className={styles["ck-fm-list-head"]}>
            <div className={styles["ck-fm-list-title"]}>
              <h2>Motorlar</h2>
              <span>{filteredMotors.length}</span>
            </div>
            <button type="button" className={styles["ck-fm-icon-btn"]} aria-label="Sıralamayı düzenle">
              <MoreHorizontal size={18} />
            </button>
          </div>

          <div className={styles["ck-fm-list"]}>
            {filteredMotors.map((motor) => {
              const selected = selectedMotor?.id === motor.id;
              return (
                <button
                  key={motor.id}
                  type="button"
                  className={`${styles["ck-fm-row"]} ${selected ? styles["is-selected"] : ""}`}
                  onClick={() => setSelectedMotorId(motor.id)}
                >
                  <div className={styles["ck-fm-row-main"]}>
                    <strong>{motor.code}</strong>
                    <span>{ownershipShortLabel(motor.ownershipType)}</span>
                  </div>

                  <div className={styles["ck-fm-row-plate"]}>
                    <strong>{motor.plate || "—"}</strong>
                  </div>

                  <span
                    className={`${styles["ck-fm-badge"]} ${
                      styles[`status-${motor.status.toLowerCase().replace(/ı/g, "i")}`] ?? ""
                    }`}
                  >
                    {motor.status}
                  </span>

                  <div className={styles["ck-fm-row-owner"]}>
                    <span>{motor.assigneeName || "Atanmamış"}</span>
                  </div>

                  <div className={styles["ck-fm-row-cost"]}>
                    <strong>{formatMoney(motor.monthlyAmount)}</strong>
                  </div>
                </button>
              );
            })}
          </div>

          <div className={styles["ck-fm-pagination"]}>
            <button type="button">‹</button>
            <button type="button" className={styles["is-current-page"]}>
              1
            </button>
            <button type="button">2</button>
            <button type="button">3</button>
            <span>…</span>
            <button type="button">4</button>
            <button type="button">›</button>
          </div>
        </article>

        <aside className={styles["ck-fm-detail-card"]}>
          {!selectedMotor ? (
            <div className={styles["ck-fm-empty"]}>
              <div className={styles["ck-fm-empty-icon"]}>
                <Bike size={28} />
              </div>
              <h3>Motor seçin</h3>
              <p>Detayları görmek için soldaki listeden bir motor seçin.</p>
            </div>
          ) : (
            <>
              <div className={styles["ck-fm-detail-head"]}>
                <div className={styles["ck-fm-detail-head-main"]}>
                  <div className={styles["ck-fm-headline-row"]}>
                    <span
                      className={`${styles["ck-fm-badge"]} ${
                        styles[`status-${selectedMotor.status.toLowerCase().replace(/ı/g, "i")}`] ?? ""
                      }`}
                    >
                      {selectedMotor.status}
                    </span>
                    <h2>{selectedMotor.code}</h2>
                  </div>
                  <div className={styles["ck-fm-detail-model"]}>{selectedMotor.model}</div>
                </div>

                <div className={styles["ck-fm-detail-actions"]}>
                  <button
                    type="button"
                    className={styles["ck-fm-secondary-btn"]}
                    onClick={() => onDownloadHistoryPdf?.(selectedMotor)}
                  >
                    <Download size={16} />
                    Geçmiş PDF İndir
                  </button>
                  <button type="button" className={styles["ck-fm-icon-btn"]} aria-label="Diğer işlemler">
                    <MoreHorizontal size={18} />
                  </button>
                </div>
              </div>

              <div className={styles["ck-fm-summary-grid"]}>
                <div className={styles["ck-fm-summary-item"]}>
                  <span>Plaka</span>
                  <strong>{selectedMotor.plate}</strong>
                </div>
                <div className={styles["ck-fm-summary-item"]}>
                  <span>Motor Tipi</span>
                  <strong>{selectedMotor.type}</strong>
                </div>
                <div className={styles["ck-fm-summary-item"]}>
                  <span>Sahiplik</span>
                  <strong>{ownershipLabel(selectedMotor.ownershipType)}</strong>
                </div>
                <div className={styles["ck-fm-summary-item"]}>
                  <span>Kişi</span>
                  <strong>{selectedMotor.assigneeName || "Atanmamış"}</strong>
                </div>
              </div>

              <div className={styles["ck-fm-metrics"]}>
                <MetricCard
                  icon={<Wallet size={18} />}
                  label={selectedMotor.ownershipType === "Çat Kapında Satılık" ? "Aylık Taksit" : "Aylık Kira"}
                  value={formatMoney(selectedMotor.monthlyAmount)}
                  helper={selectedMotor.ownershipType === "Çat Kapında Satılık" ? "KDV hariç" : "KDV dahil"}
                />
                <MetricCard
                  icon={<Calendar size={18} />}
                  label={selectedMotor.ownershipType === "Çat Kapında Satılık" ? "Satış Başlangıcı" : "Kira Başlangıcı"}
                  value={formatDateLabel(selectedMotor.startDate)}
                  helper="Kayıt tarihi"
                />
                <MetricCard
                  icon={<Calendar size={18} />}
                  label="Bir Sonraki Ödeme"
                  value={formatDateLabel(selectedMotor.nextPaymentDate)}
                  helper={selectedMotor.nextPaymentDate ? "Takvimde kayıtlı" : "Planlı ödeme yok"}
                />
                <MetricCard
                  icon={<ShieldCheck size={18} />}
                  label="Toplam Ödeme"
                  value={formatMoney(selectedMotor.totalPaid)}
                  helper={selectedMotor.paidInstallmentsLabel}
                />
              </div>

              <div className={styles["ck-fm-tabs"]}>
                <button
                  type="button"
                  className={activeTab === "general" ? styles["is-active-tab"] : ""}
                  onClick={() => setActiveTab("general")}
                >
                  Genel Bilgiler
                </button>
                <button
                  type="button"
                  className={activeTab === "rental" ? styles["is-active-tab"] : ""}
                  onClick={() => setActiveTab("rental")}
                >
                  Kira &amp; Geçmiş
                </button>
                <button
                  type="button"
                  className={activeTab === "maintenance" ? styles["is-active-tab"] : ""}
                  onClick={() => setActiveTab("maintenance")}
                >
                  Bakım &amp; Masraf
                </button>
                <button
                  type="button"
                  className={activeTab === "ownership" ? styles["is-active-tab"] : ""}
                  onClick={() => setActiveTab("ownership")}
                >
                  Sahiplik Geçmişi
                </button>
                <button
                  type="button"
                  className={activeTab === "documents" ? styles["is-active-tab"] : ""}
                  onClick={() => setActiveTab("documents")}
                >
                  Belgeler
                </button>
              </div>

              {activeTab === "general" ? (
                <>
                  <div className={styles["ck-fm-detail-grid"]}>
                    <InfoCard title="Motor Bilgileri">
                      <InfoRow label="Motor ID" value={selectedMotor.code} />
                      <InfoRow label="Plaka" value={selectedMotor.plate} />
                      <InfoRow label="Motor Tipi" value={selectedMotor.type} />
                      <InfoRow label="Model Yılı" value={selectedMotor.modelYear} />
                      <InfoRow label="Renk" value={selectedMotor.color} />
                      <InfoRow label="Şasi No" value={selectedMotor.chassisNo} />
                      <InfoRow label="Motor No" value={selectedMotor.engineNo} />
                      <InfoRow label="Not" value={selectedMotor.notes || "—"} />
                    </InfoCard>

                    <InfoCard title="Mevcut Kullanıcı">
                      <div className={styles["ck-fm-user-card"]}>
                        <div className={styles["ck-fm-user-avatar"]}>
                          {getInitials(selectedMotor.assigneeName)}
                        </div>
                        <div className={styles["ck-fm-user-copy"]}>
                          <strong>{selectedMotor.assigneeName || "Atanmamış"}</strong>
                          <span>{selectedMotor.assigneeRole || "Aktif kullanıcı yok"}</span>
                        </div>
                      </div>
                      <InfoRow label="Şube" value={selectedMotor.branchLabel || "Atanmamış"} />
                      <InfoRow
                        label="Sahiplik"
                        value={ownershipLabel(selectedMotor.ownershipType)}
                      />
                      <button
                        type="button"
                        className={styles["ck-fm-link-btn"]}
                        onClick={() => onOpenAssignee?.(selectedMotor)}
                      >
                        Kişi Detayına Git
                        <ChevronRight size={16} />
                      </button>
                    </InfoCard>

                    <InfoCard title="Kısa Notlar">
                      <p className={styles["ck-fm-note-copy"]}>{selectedMotor.notes}</p>
                      <div className={styles["ck-fm-note-meta"]}>Notu ekleyen: Yönetici</div>
                    </InfoCard>
                  </div>

                  <InfoCard title="Son Hareketler" className={styles["ck-fm-timeline-card"]}>
                    <div className={styles["ck-fm-timeline"]}>
                      {selectedMotor.movements.map((movement) => (
                        <div key={`${movement.title}-${movement.meta}`} className={styles["ck-fm-timeline-row"]}>
                          <span
                            className={`${styles["ck-fm-timeline-dot"]} ${
                              movement.tone ? styles[`tone-${movement.tone}`] : ""
                            }`}
                          />
                          <div className={styles["ck-fm-timeline-copy"]}>
                            <strong>{movement.title}</strong>
                            <span>
                              {movement.meta} • {movement.actor}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </InfoCard>
                </>
              ) : null}

              {activeTab === "rental" ? (
                <div className={styles["ck-fm-detail-grid-single"]}>
                  <InfoCard title="Kira & Geçmiş">
                    {selectedMotor.rentalHistory.map((item) => (
                      <InfoRow key={`${item.label}-${item.value}`} label={item.label} value={item.value} />
                    ))}
                  </InfoCard>
                </div>
              ) : null}

              {activeTab === "maintenance" ? (
                <div className={styles["ck-fm-detail-grid-single"]}>
                  <InfoCard title="Bakım & Masraf">
                    {selectedMotor.maintenanceItems.map((item) => (
                      <InfoRow key={`${item.label}-${item.value}`} label={item.label} value={item.value} />
                    ))}
                  </InfoCard>
                </div>
              ) : null}

              {activeTab === "ownership" ? (
                <div className={styles["ck-fm-detail-grid-single"]}>
                  <InfoCard title="Sahiplik Geçmişi">
                    <div className={styles["ck-fm-history-list"]}>
                      {selectedMotor.ownershipHistory.map((item) => (
                        <div key={`${item.label}-${item.value}`} className={styles["ck-fm-history-row"]}>
                          <strong>{item.label}</strong>
                          <span>{item.value}</span>
                        </div>
                      ))}
                    </div>
                  </InfoCard>
                </div>
              ) : null}

              {activeTab === "documents" ? (
                <div className={styles["ck-fm-detail-grid-single"]}>
                  <InfoCard title="Belgeler">
                    {selectedMotor.documents.length ? (
                      <div className={styles["ck-fm-documents"]}>
                        {selectedMotor.documents.map((item) => (
                          <div key={`${item.label}-${item.description}`} className={styles["ck-fm-document-row"]}>
                            <div className={styles["ck-fm-document-icon"]}>
                              <FileText size={18} />
                            </div>
                            <div className={styles["ck-fm-document-copy"]}>
                              <strong>{item.label}</strong>
                              <span>{item.description}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className={styles["ck-fm-empty-substate"]}>
                        Bu motora bağlı belge bulunmuyor.
                      </div>
                    )}
                  </InfoCard>
                </div>
              ) : null}
            </>
          )}
        </aside>
      </div>
    </section>
  );
}

function MetricCard({
  icon,
  label,
  value,
  helper,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className={styles["ck-fm-metric-card"]}>
      <div className={styles["ck-fm-metric-icon"]}>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </div>
  );
}

function InfoCard({
  title,
  className,
  children,
}: {
  title: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`${styles["ck-fm-info-card"]} ${className ?? ""}`.trim()}>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles["ck-fm-info-row"]}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export type { FleetMotorRecord, FleetMotorWorkbenchProps };
