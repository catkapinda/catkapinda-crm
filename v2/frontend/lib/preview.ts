type PreviewRestaurantRecord = {
  id: number;
  brand: string;
  branch: string;
  label: string;
  pricing_model: string;
  hourly_rate: number;
  package_rate: number;
  package_threshold: number;
  package_rate_low: number;
  package_rate_high: number;
  fixed_monthly_fee: number;
  vat_rate: number;
  target_headcount: number;
  start_date: string | null;
  end_date: string | null;
  extra_headcount_request: number;
  extra_headcount_request_date: string | null;
  reduce_headcount_request: number;
  reduce_headcount_request_date: string | null;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  company_title: string;
  address: string;
  tax_office: string;
  tax_number: string;
  active: boolean;
  notes: string;
};

type PreviewPersonnelRecord = {
  id: number;
  person_code: string;
  full_name: string;
  role: string;
  status: string;
  phone: string;
  address?: string;
  iban?: string;
  tax_number?: string;
  tax_office?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  accounting_type?: string;
  new_company_setup?: string;
  accounting_revenue?: number;
  accountant_cost?: number;
  company_setup_revenue?: number;
  company_setup_cost?: number;
  restaurant_id: number | null;
  vehicle_mode: string;
  current_plate: string;
  start_date: string | null;
  monthly_fixed_cost: number;
  notes: string;
};

type PreviewAttendanceRecord = {
  id: number;
  entry_date: string;
  restaurant_id: number;
  entry_mode: string;
  primary_person_id: number | null;
  replacement_person_id: number | null;
  absence_reason: string;
  worked_hours: number;
  package_count: number;
  monthly_invoice_amount: number;
  notes: string;
};

type PreviewDeductionRecord = {
  id: number;
  personnel_id: number;
  deduction_date: string;
  deduction_type: string;
  amount: number;
  notes: string;
  auto_source_key: string;
  is_auto_record: boolean;
};

type PreviewSalesRecord = {
  id: number;
  restaurant_name: string;
  city: string;
  district: string;
  address: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  requested_courier_count: number;
  lead_source: string;
  proposed_quote: number;
  pricing_model: string;
  hourly_rate: number;
  package_rate: number;
  package_threshold: number;
  package_rate_low: number;
  package_rate_high: number;
  fixed_monthly_fee: number;
  status: string;
  next_follow_up_date: string | null;
  assigned_owner: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

type PreviewPurchaseRecord = {
  id: number;
  purchase_date: string;
  item_name: string;
  quantity: number;
  total_invoice_amount: number;
  supplier: string;
  invoice_no: string;
  notes: string;
};

type PreviewEquipmentIssueRecord = {
  id: number;
  personnel_id: number;
  issue_date: string;
  item_name: string;
  quantity: number;
  unit_cost: number;
  unit_sale_price: number;
  vat_rate: number;
  installment_count: number;
  sale_type: string;
  notes: string;
  auto_source_key: string;
  is_auto_record: boolean;
};

type PreviewBoxReturnRecord = {
  id: number;
  personnel_id: number;
  return_date: string;
  quantity: number;
  condition_status: string;
  payout_amount: number;
  waived: boolean;
  notes: string;
};

type PreviewAuditRecord = {
  id: number;
  created_at: string;
  actor_username: string;
  actor_full_name: string;
  actor_role: string;
  entity_type: string;
  entity_id: string;
  action_type: string;
  summary: string;
  details_json: string;
};

let previewRestaurants: PreviewRestaurantRecord[] = [
  {
    id: 1,
    brand: "Burger House",
    branch: "Kadikoy Merkez",
    label: "Burger House / Kadikoy Merkez",
    pricing_model: "fixed_monthly",
    hourly_rate: 0,
    package_rate: 0,
    package_threshold: 390,
    package_rate_low: 0,
    package_rate_high: 0,
    fixed_monthly_fee: 185000,
    vat_rate: 20,
    target_headcount: 6,
    start_date: "2025-07-01",
    end_date: null,
    extra_headcount_request: 1,
    extra_headcount_request_date: "2026-04-11",
    reduce_headcount_request: 0,
    reduce_headcount_request_date: null,
    contact_name: "Pelin Aras",
    contact_phone: "02165550001",
    contact_email: "pelin.aras@burgerhouse.com",
    company_title: "Burger House Gida A.S.",
    address: "Kadikoy / Istanbul",
    tax_office: "Goztepe",
    tax_number: "3456789012",
    active: true,
    notes: "Aksam piki için joker gecisi sık kullaniliyor.",
  },
  {
    id: 2,
    brand: "Sushi Fold",
    branch: "Besiktas Hub",
    label: "Sushi Fold / Besiktas Hub",
    pricing_model: "hourly_plus_package",
    hourly_rate: 225,
    package_rate: 74,
    package_threshold: 390,
    package_rate_low: 0,
    package_rate_high: 0,
    fixed_monthly_fee: 0,
    vat_rate: 20,
    target_headcount: 5,
    start_date: "2025-10-15",
    end_date: null,
    extra_headcount_request: 2,
    extra_headcount_request_date: "2026-04-09",
    reduce_headcount_request: 0,
    reduce_headcount_request_date: null,
    contact_name: "Emre Yalcin",
    contact_phone: "02125550002",
    contact_email: "emre.yalcin@sushifold.com",
    company_title: "Sushi Fold Restoran Ltd.",
    address: "Besiktas / Istanbul",
    tax_office: "Levent",
    tax_number: "4567890123",
    active: true,
    notes: "Paket bazli primde hafta sonu verimi yüksek.",
  },
  {
    id: 3,
    brand: "Pide Route",
    branch: "Mecidiyekoy North",
    label: "Pide Route / Mecidiyekoy North",
    pricing_model: "fixed_monthly",
    hourly_rate: 0,
    package_rate: 0,
    package_threshold: 390,
    package_rate_low: 0,
    package_rate_high: 0,
    fixed_monthly_fee: 164000,
    vat_rate: 20,
    target_headcount: 4,
    start_date: "2025-03-04",
    end_date: null,
    extra_headcount_request: 0,
    extra_headcount_request_date: null,
    reduce_headcount_request: 1,
    reduce_headcount_request_date: "2026-03-26",
    contact_name: "Yasemin Colak",
    contact_phone: "02125550003",
    contact_email: "yasemin.colak@pideroute.com",
    company_title: "Pide Route Gida Sanayi",
    address: "Mecidiyekoy / Istanbul",
    tax_office: "Sisli",
    tax_number: "5678901234",
    active: true,
    notes: "Sabit aylık modelde maliyet takibi kritik.",
  },
  {
    id: 4,
    brand: "Wrap Station",
    branch: "Atasehir Line",
    label: "Wrap Station / Atasehir Line",
    pricing_model: "threshold_package",
    hourly_rate: 205,
    package_rate: 0,
    package_threshold: 420,
    package_rate_low: 62,
    package_rate_high: 79,
    fixed_monthly_fee: 0,
    vat_rate: 20,
    target_headcount: 4,
    start_date: "2025-12-10",
    end_date: null,
    extra_headcount_request: 0,
    extra_headcount_request_date: null,
    reduce_headcount_request: 0,
    reduce_headcount_request_date: null,
    contact_name: "Arda Gurel",
    contact_phone: "02165550004",
    contact_email: "arda.gurel@wrapstation.com",
    company_title: "Wrap Station Hizmet A.S.",
    address: "Atasehir / Istanbul",
    tax_office: "Kozyatagi",
    tax_number: "6789012345",
    active: false,
    notes: "Nisan sonunda yeniden aktiflestirme gorusuluyor.",
  },
];

let previewPersonnelRecords: PreviewPersonnelRecord[] = [
  {
    id: 101,
    person_code: "PRS-2401",
    full_name: "Kaan Demir",
    role: "Kurye",
    status: "Aktif",
    phone: "05320000001",
    restaurant_id: 1,
    vehicle_mode: "Kendi Motoru",
    current_plate: "34 KD 101",
    start_date: "2026-01-04",
    monthly_fixed_cost: 0,
    notes: "Sabah vardiyasinda güçlü.",
  },
  {
    id: 102,
    person_code: "PRS-2402",
    full_name: "Ozan Koc",
    role: "Kurye",
    status: "Aktif",
    phone: "05320000002",
    restaurant_id: 2,
    vehicle_mode: "Sirket Motoru",
    current_plate: "34 OK 102",
    start_date: "2025-11-14",
    monthly_fixed_cost: 0,
    notes: "Aksam saatlerinde yoğun kullaniliyor.",
  },
  {
    id: 103,
    person_code: "PRS-2403",
    full_name: "Merve Yildiz",
    role: "Joker",
    status: "Aktif",
    phone: "05320000003",
    restaurant_id: 1,
    vehicle_mode: "Kendi Motoru",
    current_plate: "34 MY 103",
    start_date: "2025-09-02",
    monthly_fixed_cost: 0,
    notes: "İki şube arasinda geçiş yapiyor.",
  },
  {
    id: 104,
    person_code: "PRS-2404",
    full_name: "Baris Akin",
    role: "Saha Lideri",
    status: "Aktif",
    phone: "05320000004",
    restaurant_id: 3,
    vehicle_mode: "Yaya",
    current_plate: "",
    start_date: "2024-08-19",
    monthly_fixed_cost: 42000,
    notes: "Vardiya dağılımını takip ediyor.",
  },
  {
    id: 105,
    person_code: "PRS-2405",
    full_name: "Ece Tan",
    role: "Kurye",
    status: "Pasif",
    phone: "05320000005",
    restaurant_id: 4,
    vehicle_mode: "Sirket Motoru",
    current_plate: "34 ET 105",
    start_date: "2025-06-22",
    monthly_fixed_cost: 0,
    notes: "Geçici pasif durumda.",
  },
  {
    id: 106,
    person_code: "PRS-2406",
    full_name: "Serkan Ince",
    role: "Kurye",
    status: "Aktif",
    phone: "05320000006",
    restaurant_id: 3,
    vehicle_mode: "Kendi Motoru",
    current_plate: "34 SI 106",
    start_date: "2025-12-09",
    monthly_fixed_cost: 0,
    notes: "",
  },
  {
    id: 107,
    person_code: "PRS-2407",
    full_name: "Deniz Ucar",
    role: "Destek",
    status: "Aktif",
    phone: "05320000007",
    restaurant_id: 2,
    vehicle_mode: "Yaya",
    current_plate: "",
    start_date: "2026-02-01",
    monthly_fixed_cost: 18000,
    notes: "Hafta sonu destek ekibi.",
  },
];

let previewAttendanceRecords: PreviewAttendanceRecord[] = [
  {
    id: 501,
    entry_date: "2026-04-15",
    restaurant_id: 1,
    entry_mode: "Restoran Kuryesi",
    primary_person_id: 101,
    replacement_person_id: null,
    absence_reason: "",
    worked_hours: 10,
    package_count: 42,
    monthly_invoice_amount: 0,
    notes: "Aksam pikini rahatlatti.",
  },
  {
    id: 502,
    entry_date: "2026-04-15",
    restaurant_id: 2,
    entry_mode: "Joker",
    primary_person_id: 102,
    replacement_person_id: 103,
    absence_reason: "Izin",
    worked_hours: 9,
    package_count: 36,
    monthly_invoice_amount: 0,
    notes: "Joker kaydirma yapildi.",
  },
  {
    id: 503,
    entry_date: "2026-04-14",
    restaurant_id: 3,
    entry_mode: "Restoran Kuryesi",
    primary_person_id: 106,
    replacement_person_id: null,
    absence_reason: "",
    worked_hours: 11,
    package_count: 39,
    monthly_invoice_amount: 164000,
    notes: "Sabit aylık model.",
  },
  {
    id: 504,
    entry_date: "2026-04-14",
    restaurant_id: 1,
    entry_mode: "Destek",
    primary_person_id: 103,
    replacement_person_id: 101,
    absence_reason: "Rapor",
    worked_hours: 8,
    package_count: 18,
    monthly_invoice_amount: 0,
    notes: "Kisa destek kaydı.",
  },
  {
    id: 505,
    entry_date: "2026-04-13",
    restaurant_id: 4,
    entry_mode: "Restoran Kuryesi",
    primary_person_id: 105,
    replacement_person_id: null,
    absence_reason: "",
    worked_hours: 7,
    package_count: 22,
    monthly_invoice_amount: 0,
    notes: "Pasif karta gecmeden onceki son kayıt.",
  },
  {
    id: 506,
    entry_date: "2026-04-12",
    restaurant_id: 2,
    entry_mode: "Restoran Kuryesi",
    primary_person_id: 102,
    replacement_person_id: null,
    absence_reason: "",
    worked_hours: 10,
    package_count: 40,
    monthly_invoice_amount: 0,
    notes: "",
  },
];

let previewDeductionRecords: PreviewDeductionRecord[] = [
  {
    id: 801,
    personnel_id: 101,
    deduction_date: "2026-04-14",
    deduction_type: "advance_payment",
    amount: 2500,
    notes: "Hafta basi avans kapamasi.",
    auto_source_key: "",
    is_auto_record: false,
  },
  {
    id: 802,
    personnel_id: 102,
    deduction_date: "2026-04-12",
    deduction_type: "traffic_fine",
    amount: 1850,
    notes: "Besiktas hattında park cezasi.",
    auto_source_key: "",
    is_auto_record: false,
  },
  {
    id: 803,
    personnel_id: 104,
    deduction_date: "2026-04-10",
    deduction_type: "missing_equipment",
    amount: 950,
    notes: "Zimmet eksiği otomatik yansidi.",
    auto_source_key: "equipment:loss:104:20260410",
    is_auto_record: true,
  },
  {
    id: 804,
    personnel_id: 106,
    deduction_date: "2026-04-09",
    deduction_type: "cash_gap",
    amount: 620,
    notes: "Gün sonu tahsilat farki.",
    auto_source_key: "",
    is_auto_record: false,
  },
  {
    id: 805,
    personnel_id: 107,
    deduction_date: "2026-04-07",
    deduction_type: "advance_payment",
    amount: 1800,
    notes: "Hafta sonu destek avansi.",
    auto_source_key: "",
    is_auto_record: false,
  },
  {
    id: 806,
    personnel_id: 103,
    deduction_date: "2026-04-03",
    deduction_type: "late_return",
    amount: 430,
    notes: "Motor teslim gecikmesi.",
    auto_source_key: "attendance:late_return:103:20260403",
    is_auto_record: true,
  },
];

let previewSalesRecords: PreviewSalesRecord[] = [
  {
    id: 901,
    restaurant_name: "Kavurma Studio",
    city: "Istanbul",
    district: "Kadikoy",
    address: "Moda Mah. Bahariye Cad. No:18",
    contact_name: "Buse Akpinar",
    contact_phone: "05330000011",
    contact_email: "buse@kavurmastudio.com",
    requested_courier_count: 5,
    lead_source: "Referans",
    proposed_quote: 214000,
    pricing_model: "fixed_monthly",
    hourly_rate: 0,
    package_rate: 0,
    package_threshold: 390,
    package_rate_low: 0,
    package_rate_high: 0,
    fixed_monthly_fee: 214000,
    status: "Teklif Gonderildi",
    next_follow_up_date: "2026-04-18",
    assigned_owner: "Ebru Aslan",
    notes: "Mevcut operasyonu mayis basinda tasimak istiyorlar.",
    created_at: "2026-04-06T10:15:00Z",
    updated_at: "2026-04-14T16:40:00Z",
  },
  {
    id: 902,
    restaurant_name: "Noodle Port",
    city: "Istanbul",
    district: "Sisli",
    address: "Esentepe Mah. Talatpasa Cad. No:44",
    contact_name: "Mert Gungor",
    contact_phone: "05330000012",
    contact_email: "mert@noodleport.com",
    requested_courier_count: 4,
    lead_source: "Mail",
    proposed_quote: 0,
    pricing_model: "hourly_plus_package",
    hourly_rate: 230,
    package_rate: 78,
    package_threshold: 390,
    package_rate_low: 0,
    package_rate_high: 0,
    fixed_monthly_fee: 0,
    status: "Yeni Talep",
    next_follow_up_date: "2026-04-16",
    assigned_owner: "Seda Kurt",
    notes: "Hızlı teklif bekliyorlar, hafta ici demo istenecek.",
    created_at: "2026-04-11T09:20:00Z",
    updated_at: "2026-04-15T08:10:00Z",
  },
  {
    id: 903,
    restaurant_name: "Poke Dock",
    city: "Bursa",
    district: "Nilufer",
    address: "FSM Bulvari No:55",
    contact_name: "Ezgi Tunc",
    contact_phone: "05330000013",
    contact_email: "ezgi@pokedock.com",
    requested_courier_count: 3,
    lead_source: "Saha",
    proposed_quote: 118000,
    pricing_model: "hourly_only",
    hourly_rate: 245,
    package_rate: 0,
    package_threshold: 390,
    package_rate_low: 0,
    package_rate_high: 0,
    fixed_monthly_fee: 0,
    status: "Takipte",
    next_follow_up_date: "2026-04-20",
    assigned_owner: "Onur Celik",
    notes: "Bursa genisleme planina paralel ikinci şube potansiyeli var.",
    created_at: "2026-03-29T14:05:00Z",
    updated_at: "2026-04-13T12:25:00Z",
  },
  {
    id: 904,
    restaurant_name: "Toast Theory",
    city: "Istanbul",
    district: "Besiktas",
    address: "Carsi Cad. No:5",
    contact_name: "Deniz Koray",
    contact_phone: "05330000014",
    contact_email: "deniz@toasttheory.com",
    requested_courier_count: 6,
    lead_source: "Partner",
    proposed_quote: 198000,
    pricing_model: "threshold_package",
    hourly_rate: 215,
    package_rate: 0,
    package_threshold: 430,
    package_rate_low: 64,
    package_rate_high: 81,
    fixed_monthly_fee: 0,
    status: "Kazanildi",
    next_follow_up_date: null,
    assigned_owner: "Ebru Aslan",
    notes: "Mayis ilk haftasi onboarding planlandi.",
    created_at: "2026-03-17T11:50:00Z",
    updated_at: "2026-04-10T18:00:00Z",
  },
];

let previewPurchaseRecords: PreviewPurchaseRecord[] = [
  {
    id: 1001,
    purchase_date: "2026-04-14",
    item_name: "Kuryeye Yelek",
    quantity: 12,
    total_invoice_amount: 14880,
    supplier: "MotoGiyim",
    invoice_no: "MG-240414",
    notes: "Yeni ise baslayan ekip için seri alım.",
  },
  {
    id: 1002,
    purchase_date: "2026-04-12",
    item_name: "Kask",
    quantity: 6,
    total_invoice_amount: 13200,
    supplier: "RideSafe",
    invoice_no: "RS-8821",
    notes: "Eskiyen kasklar yenilendi.",
  },
  {
    id: 1003,
    purchase_date: "2026-04-08",
    item_name: "Telefon Tutucu",
    quantity: 18,
    total_invoice_amount: 5580,
    supplier: "MotoGiyim",
    invoice_no: "MG-240408",
    notes: "Istanbul sahasi için toplu alım.",
  },
  {
    id: 1004,
    purchase_date: "2026-04-03",
    item_name: "Yagmurluk",
    quantity: 10,
    total_invoice_amount: 7200,
    supplier: "SahaTek",
    invoice_no: "ST-240403",
    notes: "Nisan yagmurlari için koruyucu stok.",
  },
];

let previewEquipmentIssueRecords: PreviewEquipmentIssueRecord[] = [
  {
    id: 1101,
    personnel_id: 101,
    issue_date: "2026-04-13",
    item_name: "Kask",
    quantity: 1,
    unit_cost: 2200,
    unit_sale_price: 2750,
    vat_rate: 20,
    installment_count: 2,
    sale_type: "Satış",
    notes: "Yeni ise baslayan personel için standart set.",
    auto_source_key: "",
    is_auto_record: false,
  },
  {
    id: 1102,
    personnel_id: 102,
    issue_date: "2026-04-11",
    item_name: "Telefon Tutucu",
    quantity: 1,
    unit_cost: 280,
    unit_sale_price: 420,
    vat_rate: 20,
    installment_count: 1,
    sale_type: "Zimmet",
    notes: "Araç değişikliği sonrası sabitleme aparatı verildi.",
    auto_source_key: "",
    is_auto_record: false,
  },
  {
    id: 1103,
    personnel_id: 103,
    issue_date: "2026-04-08",
    item_name: "Kuryeye Yelek",
    quantity: 2,
    unit_cost: 620,
    unit_sale_price: 890,
    vat_rate: 20,
    installment_count: 3,
    sale_type: "Satış",
    notes: "Yedek yelek seti eklendi.",
    auto_source_key: "equipment:auto:vest:103:20260408",
    is_auto_record: true,
  },
  {
    id: 1104,
    personnel_id: 106,
    issue_date: "2026-04-04",
    item_name: "Yagmurluk",
    quantity: 1,
    unit_cost: 720,
    unit_sale_price: 960,
    vat_rate: 20,
    installment_count: 2,
    sale_type: "Depozito",
    notes: "Nisan yagmurlari için teslim edildi.",
    auto_source_key: "",
    is_auto_record: false,
  },
];

let previewBoxReturnRecords: PreviewBoxReturnRecord[] = [
  {
    id: 1201,
    personnel_id: 105,
    return_date: "2026-04-14",
    quantity: 2,
    condition_status: "Temiz",
    payout_amount: 1200,
    waived: false,
    notes: "Pasif karta geçiş sonrası tam iade.",
  },
  {
    id: 1202,
    personnel_id: 103,
    return_date: "2026-04-10",
    quantity: 1,
    condition_status: "Hasarli",
    payout_amount: 0,
    waived: true,
    notes: "Hasarli ama operasyonda kayip yazilmadi.",
  },
  {
    id: 1203,
    personnel_id: 107,
    return_date: "2026-04-06",
    quantity: 1,
    condition_status: "Temiz",
    payout_amount: 650,
    waived: false,
    notes: "Hafta sonu destek seti geri alindi.",
  },
];

let previewAuditRecords: PreviewAuditRecord[] = [
  {
    id: 1301,
    created_at: "2026-04-15T09:42:00Z",
    actor_username: "ebru.aslan",
    actor_full_name: "Ebru Aslan",
    actor_role: "admin",
    entity_type: "attendance",
    entity_id: "506",
    action_type: "delete",
    summary: "Nisan ilk hafta puantaj temizligi sirasinda tek kayıt silindi.",
    details_json: '{"entry_id":506,"restaurant":"Sushi Fold / Besiktas Hub","reason":"preview cleanup"}',
  },
  {
    id: 1302,
    created_at: "2026-04-15T08:15:00Z",
    actor_username: "seda.kurt",
    actor_full_name: "Seda Kurt",
    actor_role: "sales_manager",
    entity_type: "sales",
    entity_id: "902",
    action_type: "update",
    summary: "Noodle Port firsatina yeni takip tarihi ve sahibi atandi.",
    details_json: '{"status":"Yeni Talep","next_follow_up_date":"2026-04-16","assigned_owner":"Seda Kurt"}',
  },
  {
    id: 1303,
    created_at: "2026-04-14T17:28:00Z",
    actor_username: "onur.celik",
    actor_full_name: "Onur Celik",
    actor_role: "ops_lead",
    entity_type: "equipment_issue",
    entity_id: "1101",
    action_type: "create",
    summary: "Kaan Demir için kask zimmet kaydı oluşturuldu.",
    details_json: '{"item_name":"Kask","quantity":1,"sale_type":"Satış"}',
  },
  {
    id: 1304,
    created_at: "2026-04-13T13:05:00Z",
    actor_username: "buse.aydin",
    actor_full_name: "Buse Aydin",
    actor_role: "finance",
    entity_type: "purchase",
    entity_id: "1002",
    action_type: "create",
    summary: "RideSafe tedarikcisinden kask alimi kaydedildi.",
    details_json: '{"item_name":"Kask","quantity":6,"total_invoice_amount":13200}',
  },
  {
    id: 1305,
    created_at: "2026-04-12T11:12:00Z",
    actor_username: "ebru.aslan",
    actor_full_name: "Ebru Aslan",
    actor_role: "admin",
    entity_type: "deduction",
    entity_id: "802",
    action_type: "update",
    summary: "Trafik cezasi kesintisinin notu ve tutari güncellendi.",
    details_json: '{"deduction_type":"traffic_fine","amount":1850,"notes":"Besiktas hattında park cezasi."}',
  },
];

const previewRoleOptions = ["Kurye", "Joker", "Destek", "Saha Lideri"];
const previewStatusOptions = ["Aktif", "Pasif"];
const previewVehicleModeOptions = ["Kendi Motoru", "Sirket Motoru", "Yaya"];
const previewEntryModes = ["Restoran Kuryesi", "Joker", "Destek", "Izinli", "Raporlu"];
const previewAbsenceReasons = ["Izin", "Rapor", "Destek Gecisi", "Acil Çıkış"];
const previewDeductionTypeCaptions: Record<string, string> = {
  advance_payment: "Personelin avans talebi nedeniyle manuel olarak kayda dusulur.",
  traffic_fine: "Trafik veya park cezasi nedeniyle oluşan kesinti kalemi.",
  missing_equipment: "Kask, telefon ya da zimmetli ekipman kaybi için otomatik kesinti.",
  cash_gap: "Gün sonu tahsilat veya kasa farki için kullanilir.",
  late_return: "Motor, cihaz veya zimmetin gec teslim edilmesi durumunda kullanilir.",
};
const previewDeductionTypes = Object.keys(previewDeductionTypeCaptions);
const previewRestaurantPricingModels = [
  { value: "hourly_plus_package", label: "Saat + Paket" },
  { value: "threshold_package", label: "Eşikli Paket" },
  { value: "hourly_only", label: "Sadece Saatlik" },
  { value: "fixed_monthly", label: "Sabit Aylık Ücret" },
];
const previewSalesSourceOptions = ["Mail", "Referans", "Saha", "Partner", "Telefon"];
const previewSalesStatusOptions = [
  "Yeni Talep",
  "Takipte",
  "Teklif Gonderildi",
  "Pazarlik",
  "Kazanildi",
  "Kaybedildi",
];
const previewPurchaseItemOptions = [
  "Kask",
  "Kuryeye Yelek",
  "Telefon Tutucu",
  "Yagmurluk",
  "Termal Canta",
];
const previewEquipmentIssueItems = [
  "Kask",
  "Kuryeye Yelek",
  "Telefon Tutucu",
  "Yagmurluk",
  "Termal Canta",
];
const previewEquipmentSaleTypeOptions = ["Satış", "Zimmet", "Depozito"];
const previewEquipmentReturnConditionOptions = ["Temiz", "Hasarli", "Eksik"];
const previewEquipmentInstallmentCountOptions = [1, 2, 3, 4, 5, 6];
const previewEquipmentItemDefaults: Record<
  string,
  {
    default_unit_cost: number;
    default_sale_price: number;
    default_installment_count: number;
    default_vat_rate: number;
  }
> = {
  Kask: { default_unit_cost: 2200, default_sale_price: 2750, default_installment_count: 2, default_vat_rate: 20 },
  "Kuryeye Yelek": {
    default_unit_cost: 620,
    default_sale_price: 890,
    default_installment_count: 3,
    default_vat_rate: 20,
  },
  "Telefon Tutucu": {
    default_unit_cost: 280,
    default_sale_price: 420,
    default_installment_count: 1,
    default_vat_rate: 20,
  },
  Yagmurluk: { default_unit_cost: 720, default_sale_price: 960, default_installment_count: 2, default_vat_rate: 20 },
  "Termal Canta": {
    default_unit_cost: 1600,
    default_sale_price: 2100,
    default_installment_count: 4,
    default_vat_rate: 20,
  },
};

export const PREVIEW_USER = {
  id: 9001,
  identity: "preview@catkapinda.local",
  email: "preview@catkapinda.local",
  phone: "05320009999",
  full_name: "Preview Operator",
  role: "admin",
  role_display: "Tasarım Preview / Yönetici",
  must_change_password: false,
  allowed_actions: [
    "backup.manage",
    "dashboard.view",
    "announcements.view",
    "audit.view",
    "attendance.view",
    "attendance.create",
    "attendance.update",
    "attendance.delete",
    "attendance.bulk_delete",
    "personnel.view",
    "personnel.create",
    "personnel.update",
    "personnel.delete",
    "personnel.status_change",
    "personnel.plate",
    "deduction.view",
    "deduction.create",
    "deduction.update",
    "deduction.delete",
    "deduction.bulk_delete",
    "equipment.view",
    "equipment.bulk_update",
    "equipment.bulk_delete",
    "equipment.box_return",
    "payroll.view",
    "purchase.view",
    "purchase.create",
    "purchase.update",
    "purchase.delete",
    "sales.view",
    "sales.create",
    "sales.update",
    "sales.delete",
    "restaurant.view",
    "restaurant.create",
    "restaurant.update",
    "restaurant.delete",
    "restaurant.status_change",
    "reporting.view",
  ],
  expires_at: "2099-12-31T23:59:59Z",
};

export function isPreviewPathname(pathname: string | null | undefined) {
  return pathname === "/preview" || Boolean(pathname?.startsWith("/preview/"));
}

export function isPreviewModeBrowser() {
  return typeof window !== "undefined" && isPreviewPathname(window.location.pathname);
}

function buildJsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

function readJsonBody(init: RequestInit = {}) {
  if (!init.body || typeof init.body !== "string") {
    return {};
  }
  try {
    return JSON.parse(init.body) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function findRestaurant(restaurantId: number | null | undefined) {
  return previewRestaurants.find((restaurant) => restaurant.id === restaurantId) ?? null;
}

function findPersonnel(personId: number | null | undefined) {
  return previewPersonnelRecords.find((entry) => entry.id === personId) ?? null;
}

function personnelLabel(personId: number | null | undefined) {
  return findPersonnel(personId)?.full_name ?? "";
}

function restaurantLabel(restaurantId: number | null | undefined) {
  return findRestaurant(restaurantId)?.label ?? "";
}

function buildAttendanceCoverageType(entryMode: string, replacementPersonId: number | null) {
  if (entryMode === "Joker" || entryMode === "Destek") {
    return replacementPersonId ? "Yedekli" : "Geçiş";
  }
  if (entryMode === "Izinli" || entryMode === "Raporlu") {
    return "Devamsizlik";
  }
  return "Normal";
}

function buildAttendanceEntry(record: PreviewAttendanceRecord) {
  return {
    id: record.id,
    entry_date: record.entry_date,
    restaurant_id: record.restaurant_id,
    restaurant: restaurantLabel(record.restaurant_id),
    entry_mode: record.entry_mode,
    primary_person_id: record.primary_person_id,
    primary_person_label: personnelLabel(record.primary_person_id) || "-",
    replacement_person_id: record.replacement_person_id,
    replacement_person_label: personnelLabel(record.replacement_person_id) || "-",
    absence_reason: record.absence_reason,
    coverage_type: buildAttendanceCoverageType(record.entry_mode, record.replacement_person_id),
    worked_hours: record.worked_hours,
    package_count: record.package_count,
    monthly_invoice_amount: record.monthly_invoice_amount,
    notes: record.notes,
  };
}

function buildPersonnelEntry(record: PreviewPersonnelRecord) {
  return {
    ...record,
    address: record.address ?? "",
    iban: record.iban ?? "",
    tax_number: record.tax_number ?? "",
    tax_office: record.tax_office ?? "",
    emergency_contact_name: record.emergency_contact_name ?? "",
    emergency_contact_phone: record.emergency_contact_phone ?? "",
    accounting_type: record.accounting_type ?? "Kendi Muhasebecisi",
    new_company_setup: record.new_company_setup ?? "Hayır",
    accounting_revenue: record.accounting_revenue ?? 0,
    accountant_cost: record.accountant_cost ?? 0,
    company_setup_revenue: record.company_setup_revenue ?? 0,
    company_setup_cost: record.company_setup_cost ?? 0,
    motor_rental_monthly_amount: 13000,
    motor_purchase_start_date: null,
    motor_purchase_commitment_months: 0,
    motor_purchase_sale_price: 0,
    motor_purchase_monthly_deduction: 0,
    restaurant_label: restaurantLabel(record.restaurant_id),
  };
}

function buildAttendancePeople(restaurantId: number | null, includeAllActive = false) {
  return previewPersonnelRecords
    .filter((entry) => entry.status === "Aktif")
    .filter((entry) => {
      if (includeAllActive) {
        return true;
      }
      return restaurantId ? entry.restaurant_id === restaurantId : true;
    })
    .map((entry) => ({
      id: entry.id,
      label: `${entry.full_name} (${entry.role})`,
      role: entry.role,
    }));
}

function buildAttendanceFormOptions(restaurantId: number | null, includeAllActive = false) {
  const defaultRestaurantId = restaurantId ?? previewRestaurants[0]?.id ?? null;
  const selectedRestaurant = findRestaurant(defaultRestaurantId);
  return {
    restaurants: previewRestaurants.map((restaurant) => ({
      id: restaurant.id,
      label: restaurant.label,
      pricing_model: restaurant.pricing_model,
      fixed_monthly_fee: restaurant.fixed_monthly_fee,
    })),
    people: buildAttendancePeople(defaultRestaurantId, includeAllActive),
    entry_modes: previewEntryModes,
    absence_reasons: previewAbsenceReasons,
    bulk_statuses: ["Normal", "Joker", "İzin", "Raporlu", "İhbarsız Çıkış", "Gelmedi", "Çıkış yaptı", "Şef"],
    selected_restaurant_id: defaultRestaurantId,
    selected_pricing_model: selectedRestaurant?.pricing_model ?? null,
    selected_fixed_monthly_fee: selectedRestaurant?.fixed_monthly_fee ?? 0,
  };
}

function buildPersonnelFormOptions() {
  return {
    restaurants: previewRestaurants.map((restaurant) => ({
      id: restaurant.id,
      label: restaurant.label,
    })),
    role_options: previewRoleOptions,
    status_options: previewStatusOptions,
    vehicle_mode_options: previewVehicleModeOptions,
    accounting_type_options: ["Çat Kapında Muhasebe", "Kendi Muhasebecisi"],
    company_setup_options: ["Hayır", "Evet"],
    selected_restaurant_id: previewRestaurants[0]?.id ?? null,
  };
}

function pricingModelLabel(pricingModel: string) {
  return (
    previewRestaurantPricingModels.find((item) => item.value === pricingModel)?.label ?? pricingModel
  );
}

function deductionCaption(deductionType: string) {
  return previewDeductionTypeCaptions[deductionType] ?? deductionType;
}

function buildDeductionEntry(record: PreviewDeductionRecord) {
  return {
    id: record.id,
    personnel_id: record.personnel_id,
    personnel_label: personnelLabel(record.personnel_id) || "-",
    deduction_date: record.deduction_date,
    deduction_type: record.deduction_type,
    type_caption: deductionCaption(record.deduction_type),
    amount: record.amount,
    notes: record.notes,
    auto_source_key: record.auto_source_key,
    is_auto_record: record.is_auto_record,
  };
}

function buildDeductionFormOptions() {
  return {
    personnel: previewPersonnelRecords
      .filter((entry) => entry.status === "Aktif")
      .map((entry) => ({
        id: entry.id,
        label: `${entry.full_name} · ${restaurantLabel(entry.restaurant_id) || "Atanmadı"}`,
      })),
    deduction_types: previewDeductionTypes,
    type_captions: previewDeductionTypeCaptions,
    selected_personnel_id: previewPersonnelRecords.find((entry) => entry.status === "Aktif")?.id ?? null,
  };
}

function buildRestaurantFormOptions() {
  return {
    pricing_models: previewRestaurantPricingModels,
    status_options: previewStatusOptions,
    selected_pricing_model: previewRestaurantPricingModels[0]?.value ?? "hourly_plus_package",
  };
}

function buildRestaurantEntry(record: PreviewRestaurantRecord) {
  return {
    id: record.id,
    brand: record.brand,
    branch: record.branch,
    pricing_model: record.pricing_model,
    pricing_model_label: pricingModelLabel(record.pricing_model),
    hourly_rate: record.hourly_rate,
    package_rate: record.package_rate,
    package_threshold: record.package_threshold,
    package_rate_low: record.package_rate_low,
    package_rate_high: record.package_rate_high,
    fixed_monthly_fee: record.fixed_monthly_fee,
    vat_rate: record.vat_rate,
    target_headcount: record.target_headcount,
    start_date: record.start_date,
    end_date: record.end_date,
    extra_headcount_request: record.extra_headcount_request,
    extra_headcount_request_date: record.extra_headcount_request_date,
    reduce_headcount_request: record.reduce_headcount_request,
    reduce_headcount_request_date: record.reduce_headcount_request_date,
    contact_name: record.contact_name,
    contact_phone: record.contact_phone,
    contact_email: record.contact_email,
    company_title: record.company_title,
    address: record.address,
    tax_office: record.tax_office,
    tax_number: record.tax_number,
    active: record.active,
    notes: record.notes,
  };
}

function salesPricingHint(record: {
  pricing_model: string;
  hourly_rate: number;
  package_rate: number;
  package_threshold: number;
  package_rate_low: number;
  package_rate_high: number;
  fixed_monthly_fee: number;
}) {
  const toMoney = (value: number) =>
    new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: "TRY",
      maximumFractionDigits: 0,
    }).format(value || 0);

  if (record.pricing_model === "threshold_package") {
    return `${toMoney(record.hourly_rate)}/saat | ${record.package_threshold} altı ${toMoney(record.package_rate_low)} | üstü ${toMoney(record.package_rate_high)}`;
  }
  if (record.pricing_model === "hourly_plus_package") {
    return `${toMoney(record.hourly_rate)}/saat + ${toMoney(record.package_rate)}/paket`;
  }
  if (record.pricing_model === "hourly_only") {
    return `${toMoney(record.hourly_rate)}/saat`;
  }
  if (record.pricing_model === "fixed_monthly") {
    return `${toMoney(record.fixed_monthly_fee)}/ay`;
  }
  return "-";
}

function buildSalesEntry(record: PreviewSalesRecord) {
  return {
    ...record,
    pricing_model_label: pricingModelLabel(record.pricing_model),
    pricing_model_hint: salesPricingHint(record),
  };
}

function buildSalesFormOptions() {
  return {
    pricing_models: previewRestaurantPricingModels,
    source_options: previewSalesSourceOptions,
    status_options: previewSalesStatusOptions,
    selected_pricing_model: previewRestaurantPricingModels[0]?.value ?? "hourly_plus_package",
  };
}

function buildPurchaseEntry(record: PreviewPurchaseRecord) {
  return {
    ...record,
    unit_cost: record.quantity > 0 ? record.total_invoice_amount / record.quantity : 0,
  };
}

function buildPurchaseFormOptions() {
  return {
    item_options: previewPurchaseItemOptions,
    selected_item: previewPurchaseItemOptions[0] ?? "",
  };
}

function buildEquipmentIssueEntry(record: PreviewEquipmentIssueRecord) {
  const totalCost = record.quantity * record.unit_cost;
  const totalSale = record.quantity * record.unit_sale_price;
  return {
    id: record.id,
    personnel_id: record.personnel_id,
    personnel_label: personnelLabel(record.personnel_id) || "-",
    issue_date: record.issue_date,
    item_name: record.item_name,
    quantity: record.quantity,
    unit_cost: record.unit_cost,
    unit_sale_price: record.unit_sale_price,
    vat_rate: record.vat_rate,
    total_cost: totalCost,
    total_sale: totalSale,
    gross_profit: totalSale - totalCost,
    installment_count: record.installment_count,
    sale_type: record.sale_type,
    notes: record.notes,
    auto_source_key: record.auto_source_key,
    is_auto_record: record.is_auto_record,
  };
}

function buildBoxReturnEntry(record: PreviewBoxReturnRecord) {
  return {
    ...record,
    personnel_label: personnelLabel(record.personnel_id) || "-",
  };
}

function buildEquipmentFormOptions() {
  return {
    personnel: previewPersonnelRecords
      .filter((entry) => entry.status === "Aktif" || entry.status === "Pasif")
      .map((entry) => ({
        id: entry.id,
        label: `${entry.full_name} · ${restaurantLabel(entry.restaurant_id) || "Atanmadı"}`,
      })),
    issue_items: previewEquipmentIssueItems,
    sale_type_options: previewEquipmentSaleTypeOptions,
    return_condition_options: previewEquipmentReturnConditionOptions,
    installment_count_options: previewEquipmentInstallmentCountOptions,
    item_defaults: previewEquipmentItemDefaults,
    selected_personnel_id: previewPersonnelRecords[0]?.id ?? null,
    selected_item: previewEquipmentIssueItems[0] ?? "",
  };
}

function buildAuditEntry(record: PreviewAuditRecord) {
  return { ...record };
}

function filterAttendanceEntries(searchParams: URLSearchParams) {
  const restaurantId = Number(searchParams.get("restaurant_id") || "");
  const search = (searchParams.get("search") || "").trim().toLocaleLowerCase("tr-TR");
  const dateFrom = searchParams.get("date_from") || "";
  const dateTo = searchParams.get("date_to") || "";

  return previewAttendanceRecords
    .filter((record) => (Number.isFinite(restaurantId) ? record.restaurant_id === restaurantId : true))
    .filter((record) => (!dateFrom ? true : record.entry_date >= dateFrom))
    .filter((record) => (!dateTo ? true : record.entry_date <= dateTo))
    .filter((record) => {
      if (!search) {
        return true;
      }
      const haystack = [
        restaurantLabel(record.restaurant_id),
        personnelLabel(record.primary_person_id),
        personnelLabel(record.replacement_person_id),
        record.entry_mode,
        record.notes,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    })
    .sort((left, right) => `${right.entry_date}-${right.id}`.localeCompare(`${left.entry_date}-${left.id}`));
}

function filterPersonnelEntries(searchParams: URLSearchParams) {
  const restaurantId = Number(searchParams.get("restaurant_id") || "");
  const role = (searchParams.get("role") || "").trim();
  const search = (searchParams.get("search") || "").trim().toLocaleLowerCase("tr-TR");

  return previewPersonnelRecords
    .filter((record) => (Number.isFinite(restaurantId) ? record.restaurant_id === restaurantId : true))
    .filter((record) => (!role ? true : record.role === role))
    .filter((record) => {
      if (!search) {
        return true;
      }
      const haystack = [
        record.person_code,
        record.full_name,
        record.phone,
        record.iban,
        record.tax_number,
        record.tax_office,
        record.emergency_contact_name,
        record.emergency_contact_phone,
        record.accounting_type,
        record.new_company_setup,
        restaurantLabel(record.restaurant_id),
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    })
    .sort((left, right) => right.id - left.id);
}

function filterDeductionEntries(searchParams: URLSearchParams) {
  const personnelId = Number(searchParams.get("personnel_id") || "");
  const deductionType = (searchParams.get("deduction_type") || "").trim();
  const search = (searchParams.get("search") || "").trim().toLocaleLowerCase("tr-TR");

  return previewDeductionRecords
    .filter((record) => (Number.isFinite(personnelId) ? record.personnel_id === personnelId : true))
    .filter((record) => (!deductionType ? true : record.deduction_type === deductionType))
    .filter((record) => {
      if (!search) {
        return true;
      }
      const haystack = [
        personnelLabel(record.personnel_id),
        record.deduction_type,
        deductionCaption(record.deduction_type),
        record.notes,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    })
    .sort((left, right) => `${right.deduction_date}-${right.id}`.localeCompare(`${left.deduction_date}-${left.id}`));
}

function filterRestaurantEntries(searchParams: URLSearchParams) {
  const pricingModel = (searchParams.get("pricing_model") || "").trim();
  const active = searchParams.get("active");
  const search = (searchParams.get("search") || "").trim().toLocaleLowerCase("tr-TR");

  return previewRestaurants
    .filter((record) => (!pricingModel ? true : record.pricing_model === pricingModel))
    .filter((record) => {
      if (active === "true") {
        return record.active;
      }
      if (active === "false") {
        return !record.active;
      }
      return true;
    })
    .filter((record) => {
      if (!search) {
        return true;
      }
      const haystack = [
        record.brand,
        record.branch,
        record.contact_name,
        record.company_title,
        record.notes,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    })
    .sort((left, right) => right.id - left.id);
}

function filterSalesEntries(searchParams: URLSearchParams) {
  const status = (searchParams.get("status") || "").trim();
  const search = (searchParams.get("search") || "").trim().toLocaleLowerCase("tr-TR");

  return previewSalesRecords
    .filter((record) => (!status ? true : record.status === status))
    .filter((record) => {
      if (!search) {
        return true;
      }
      const haystack = [
        record.restaurant_name,
        record.city,
        record.district,
        record.contact_name,
        record.assigned_owner,
        record.notes,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    })
    .sort((left, right) => `${right.updated_at}-${right.id}`.localeCompare(`${left.updated_at}-${left.id}`));
}

function filterPurchaseEntries(searchParams: URLSearchParams) {
  const itemName = (searchParams.get("item_name") || "").trim();
  const search = (searchParams.get("search") || "").trim().toLocaleLowerCase("tr-TR");

  return previewPurchaseRecords
    .filter((record) => (!itemName ? true : record.item_name === itemName))
    .filter((record) => {
      if (!search) {
        return true;
      }
      const haystack = [record.item_name, record.supplier, record.invoice_no, record.notes]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    })
    .sort((left, right) => `${right.purchase_date}-${right.id}`.localeCompare(`${left.purchase_date}-${left.id}`));
}

function filterEquipmentIssueEntries(searchParams: URLSearchParams) {
  const personnelId = Number(searchParams.get("personnel_id") || "");
  const itemName = (searchParams.get("item_name") || "").trim();
  const search = (searchParams.get("search") || "").trim().toLocaleLowerCase("tr-TR");

  return previewEquipmentIssueRecords
    .filter((record) => (Number.isFinite(personnelId) ? record.personnel_id === personnelId : true))
    .filter((record) => (!itemName ? true : record.item_name === itemName))
    .filter((record) => {
      if (!search) {
        return true;
      }
      const haystack = [
        personnelLabel(record.personnel_id),
        record.item_name,
        record.sale_type,
        record.notes,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    })
    .sort((left, right) => `${right.issue_date}-${right.id}`.localeCompare(`${left.issue_date}-${left.id}`));
}

function filterBoxReturnEntries(searchParams: URLSearchParams) {
  const personnelId = Number(searchParams.get("personnel_id") || "");
  const search = (searchParams.get("search") || "").trim().toLocaleLowerCase("tr-TR");

  return previewBoxReturnRecords
    .filter((record) => (Number.isFinite(personnelId) ? record.personnel_id === personnelId : true))
    .filter((record) => {
      if (!search) {
        return true;
      }
      const haystack = [
        personnelLabel(record.personnel_id),
        record.condition_status,
        record.notes,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    })
    .sort((left, right) => `${right.return_date}-${right.id}`.localeCompare(`${left.return_date}-${left.id}`));
}

function filterAuditEntries(searchParams: URLSearchParams) {
  const actionType = (searchParams.get("action_type") || "").trim();
  const entityType = (searchParams.get("entity_type") || "").trim();
  const actorName = (searchParams.get("actor_name") || "").trim();
  const search = (searchParams.get("search") || "").trim().toLocaleLowerCase("tr-TR");

  return previewAuditRecords
    .filter((record) => (!actionType ? true : record.action_type === actionType))
    .filter((record) => (!entityType ? true : record.entity_type === entityType))
    .filter((record) => (!actorName ? true : record.actor_full_name === actorName))
    .filter((record) => {
      if (!search) {
        return true;
      }
      const haystack = [
        record.summary,
        record.details_json,
        record.entity_type,
        record.actor_full_name,
        record.actor_username,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    })
    .sort((left, right) => `${right.created_at}-${right.id}`.localeCompare(`${left.created_at}-${left.id}`));
}

function buildOverviewDashboard() {
  const activeRestaurants = new Set(
    previewPersonnelRecords.filter((entry) => entry.status === "Aktif" && entry.restaurant_id).map((entry) => entry.restaurant_id),
  ).size;
  const activePersonnel = previewPersonnelRecords.filter((entry) => entry.status === "Aktif").length;
  const currentMonthPrefix = "2026-04";
  const monthAttendanceEntries = previewAttendanceRecords.filter((entry) => entry.entry_date.startsWith(currentMonthPrefix)).length;
  const monthDeductionEntries = previewDeductionRecords.filter((entry) =>
    entry.deduction_date.startsWith(currentMonthPrefix),
  ).length;
  const openSalesPipeline = previewSalesRecords.filter((entry) =>
    ["Yeni Talep", "Takipte", "Teklif Gonderildi", "Pazarlik"].includes(entry.status),
  ).length;
  const monthPurchasesTotal = previewPurchaseRecords
    .filter((entry) => entry.purchase_date.startsWith(currentMonthPrefix))
    .reduce((sum, entry) => sum + entry.total_invoice_amount, 0);
  const monthPayrollNet = previewPersonnelRecords
    .filter((entry) => entry.status === "Aktif")
    .reduce((sum, entry) => {
      const attendanceTotal = previewAttendanceRecords
        .filter(
          (row) =>
            row.entry_date.startsWith(currentMonthPrefix) &&
            (row.primary_person_id === entry.id || row.replacement_person_id === entry.id),
        )
        .reduce((rowSum, row) => rowSum + row.worked_hours * 220, 0);
      const deductionsTotal = previewDeductionRecords
        .filter((row) => row.personnel_id === entry.id && row.deduction_date.startsWith(currentMonthPrefix))
        .reduce((rowSum, row) => rowSum + row.amount, 0);
      return sum + Math.max(attendanceTotal + entry.monthly_fixed_cost - deductionsTotal, 0);
    }, 0);
  const equipmentIssuesThisMonth = previewEquipmentIssueRecords.filter((entry) =>
    entry.issue_date.startsWith(currentMonthPrefix),
  ).length;
  const auditThisWeek = previewAuditRecords.filter(
    (entry) => entry.created_at >= "2026-04-08T00:00:00Z",
  ).length;

  const activityEntries = [
    ...previewAttendanceRecords.slice(0, 3).map((entry) => ({
      module_key: "attendance",
      module_label: "Puantaj",
      title: `${restaurantLabel(entry.restaurant_id)} puantaji güncel`,
      subtitle: `${personnelLabel(entry.primary_person_id) || "Atama"} / ${entry.entry_mode}`,
      meta: `${entry.worked_hours} saat · ${entry.package_count} paket`,
      entry_date: entry.entry_date,
      href: "/preview/attendance",
    })),
    ...previewPersonnelRecords.slice(0, 3).map((entry) => ({
      module_key: "personnel",
      module_label: "Personel",
      title: `${entry.full_name} kartı hazır`,
      subtitle: `${entry.role} · ${restaurantLabel(entry.restaurant_id) || "Atanmadı"}`,
      meta: entry.status,
      entry_date: entry.start_date,
      href: "/preview/personnel",
    })),
    ...previewDeductionRecords.slice(0, 2).map((entry) => ({
      module_key: "deductions",
      module_label: "Kesintiler",
      title: `${personnelLabel(entry.personnel_id) || "Personel"} için kesinti kaydı hazır`,
      subtitle: deductionCaption(entry.deduction_type),
      meta: new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        maximumFractionDigits: 0,
      }).format(entry.amount),
      entry_date: entry.deduction_date,
      href: "/preview/deductions",
    })),
    ...previewRestaurants.slice(0, 2).map((entry) => ({
      module_key: "restaurants",
      module_label: "Restoranlar",
      title: `${entry.brand} / ${entry.branch} kartı hazır`,
      subtitle: `${pricingModelLabel(entry.pricing_model)} · ${entry.active ? "Aktif" : "Pasif"}`,
      meta: `${entry.target_headcount} hedef kadro`,
      entry_date: entry.start_date,
      href: "/preview/restaurants",
    })),
    ...previewSalesRecords.slice(0, 2).map((entry) => ({
      module_key: "sales",
      module_label: "Satış",
      title: `${entry.restaurant_name} fırsatı pipeline'da`,
      subtitle: `${entry.status} · ${entry.assigned_owner || "Sahip bekliyor"}`,
      meta: new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        maximumFractionDigits: 0,
      }).format(entry.proposed_quote),
      entry_date: entry.updated_at,
      href: "/preview/sales",
    })),
    ...previewPurchaseRecords.slice(0, 2).map((entry) => ({
      module_key: "purchases",
      module_label: "Satın Alma",
      title: `${entry.item_name} faturası kayıtlı`,
      subtitle: `${entry.supplier || "Tedarikçi yok"} · ${entry.quantity} adet`,
      meta: new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        maximumFractionDigits: 0,
      }).format(entry.total_invoice_amount),
      entry_date: entry.purchase_date,
      href: "/preview/purchases",
    })),
    ...previewEquipmentIssueRecords.slice(0, 2).map((entry) => ({
      module_key: "equipment",
      module_label: "Ekipman",
      title: `${personnelLabel(entry.personnel_id) || "Personel"} için ${entry.item_name} zimmeti`,
      subtitle: `${entry.sale_type} · ${entry.quantity} adet`,
      meta: new Intl.NumberFormat("tr-TR", {
        style: "currency",
        currency: "TRY",
        maximumFractionDigits: 0,
      }).format(entry.quantity * entry.unit_sale_price),
      entry_date: entry.issue_date,
      href: "/preview/equipment",
    })),
    ...previewAuditRecords.slice(0, 2).map((entry) => ({
      module_key: "audit",
      module_label: "Sistem Kayıtları",
      title: entry.summary,
      subtitle: `${entry.actor_full_name} · ${entry.action_type} · ${entry.entity_type}`,
      meta: entry.entity_id,
      entry_date: entry.created_at,
      href: "/preview/audit",
    })),
  ]
    .slice()
    .sort((left, right) => `${right.entry_date || ""}`.localeCompare(`${left.entry_date || ""}`))
    .slice(0, 12);

  return {
    module: "overview",
    status: "preview",
    hero: {
      active_restaurants: activeRestaurants,
      active_personnel: activePersonnel,
      month_attendance_entries: monthAttendanceEntries,
      month_deduction_entries: monthDeductionEntries,
    },
    modules: [
      {
        key: "attendance",
        title: "Puantaj",
        description: "Günlük attendance girisi, kayıt yönetimi ve aylık silme akışlarını aynı yerde toplar.",
        href: "/preview/attendance",
        primary_label: "Aylık Kayıt",
        primary_value: String(monthAttendanceEntries),
        secondary_label: "Aktif Şube",
        secondary_value: String(activeRestaurants),
      },
      {
        key: "personnel",
        title: "Personel",
        description: "Kart açma, durum değiştirme ve saha dağılımını operasyon diliyle gösterir.",
        href: "/preview/personnel",
        primary_label: "Aktif Kadro",
        primary_value: String(activePersonnel),
        secondary_label: "Pasif Kart",
        secondary_value: String(previewPersonnelRecords.filter((entry) => entry.status !== "Aktif").length),
      },
      {
        key: "reports",
        title: "Raporlar",
        description: "Aylık hakediş ve fatura resmini editorial komuta paneli gibi okur.",
        href: "/preview/reports",
        primary_label: "Toplam Ciro",
        primary_value: "TRY 1.24M",
        secondary_label: "Kurye Maliyeti",
        secondary_value: "TRY 742K",
      },
      {
        key: "deductions",
        title: "Kesintiler",
        description: "Manuel ve otomatik kesinti akışını tek panelde izler, günceller ve temizler.",
        href: "/preview/deductions",
        primary_label: "Bu Ay Kayıt",
        primary_value: String(monthDeductionEntries),
        secondary_label: "Otomatik Kayıt",
        secondary_value: String(previewDeductionRecords.filter((entry) => entry.is_auto_record).length),
      },
      {
        key: "restaurants",
        title: "Restoranlar",
        description: "Şube, fiyat modeli ve kadro dengesini daha kararli bir ekrana tasir.",
        href: "/preview/restaurants",
        primary_label: "Aktif Şube",
        primary_value: String(previewRestaurants.filter((entry) => entry.active).length),
        secondary_label: "Sabit Aylık",
        secondary_value: String(
          previewRestaurants.filter((entry) => entry.pricing_model === "fixed_monthly").length,
        ),
      },
      {
        key: "sales",
        title: "Satış",
        description: "Fırsat havuzu, teklif durumu ve takip aksiyonları yeni ticari panelde toplanir.",
        href: "/preview/sales",
        primary_label: "Açık Fırsat Hattı",
        primary_value: String(openSalesPipeline),
        secondary_label: "Kazanılan",
        secondary_value: String(
          previewSalesRecords.filter((entry) => entry.status === "Kazanildi").length,
        ),
      },
      {
        key: "purchases",
        title: "Satın Alma",
        description: "Fatura, tedarikçi ve birim maliyet hareketleri daha temiz bir backoffice yüzeye taşınır.",
        href: "/preview/purchases",
        primary_label: "Bu Ay Fatura",
        primary_value: new Intl.NumberFormat("tr-TR", {
          style: "currency",
          currency: "TRY",
          maximumFractionDigits: 0,
        }).format(monthPurchasesTotal),
        secondary_label: "Tedarikçi",
        secondary_value: String(new Set(previewPurchaseRecords.map((entry) => entry.supplier)).size),
      },
      {
        key: "payroll",
        title: "Aylık Hakediş",
        description: "Saat, paket, kesinti ve net ödeme görünümünü tek bordro yüzeyinde toplar.",
        href: "/preview/payroll",
        primary_label: "Nisan Net",
        primary_value: new Intl.NumberFormat("tr-TR", {
          style: "currency",
          currency: "TRY",
          maximumFractionDigits: 0,
        }).format(monthPayrollNet),
        secondary_label: "Aktif Kadro",
        secondary_value: String(activePersonnel),
      },
      {
        key: "equipment",
        title: "Ekipman",
        description: "Zimmet, satış, depozito ve box geri alım akışını tek panelde izler.",
        href: "/preview/equipment",
        primary_label: "Bu Ay Zimmet",
        primary_value: String(equipmentIssuesThisMonth),
        secondary_label: "Box İade",
        secondary_value: String(previewBoxReturnRecords.length),
      },
      {
        key: "audit",
        title: "Sistem Kayıtları",
        description: "Kim, hangi kayıt üzerinde ne yaptı sorusunu daha okunur bir admin katmanına taşır.",
        href: "/preview/audit",
        primary_label: "Son 7 Gün",
        primary_value: String(auditThisWeek),
        secondary_label: "Toplam Log",
        secondary_value: String(previewAuditRecords.length),
      },
    ],
    recent_activity: activityEntries,
  };
}

function buildAttendanceDashboard() {
  const today = "2026-04-15";
  const monthPrefix = "2026-04";
  return {
    module: "attendance",
    status: "preview",
    summary: {
      total_entries: previewAttendanceRecords.length,
      today_entries: previewAttendanceRecords.filter((entry) => entry.entry_date === today).length,
      month_entries: previewAttendanceRecords.filter((entry) => entry.entry_date.startsWith(monthPrefix)).length,
      active_restaurants: new Set(previewAttendanceRecords.map((entry) => entry.restaurant_id)).size,
    },
    recent_entries: previewAttendanceRecords
      .slice()
      .sort((left, right) => `${right.entry_date}-${right.id}`.localeCompare(`${left.entry_date}-${left.id}`))
      .slice(0, 14)
      .map((entry) => ({
        id: entry.id,
        entry_date: entry.entry_date,
        restaurant: restaurantLabel(entry.restaurant_id),
        employee_name: personnelLabel(entry.primary_person_id) || "-",
        entry_mode: entry.entry_mode,
        absence_reason: entry.absence_reason,
        coverage_type: buildAttendanceCoverageType(entry.entry_mode, entry.replacement_person_id),
        worked_hours: entry.worked_hours,
        package_count: entry.package_count,
        monthly_invoice_amount: entry.monthly_invoice_amount,
        notes: entry.notes,
      })),
  };
}

function buildPersonnelDashboard() {
  return {
    module: "personnel",
    status: "preview",
    summary: {
      total_personnel: previewPersonnelRecords.length,
      active_personnel: previewPersonnelRecords.filter((entry) => entry.status === "Aktif").length,
      passive_personnel: previewPersonnelRecords.filter((entry) => entry.status !== "Aktif").length,
      assigned_restaurants: previewPersonnelRecords.filter((entry) => entry.restaurant_id !== null).length,
    },
    recent_entries: previewPersonnelRecords
      .slice()
      .sort((left, right) => right.id - left.id)
      .slice(0, 12)
      .map((entry) => ({
        ...buildPersonnelEntry(entry),
      })),
  };
}

function buildDeductionsDashboard() {
  const monthPrefix = "2026-04";
  return {
    module: "deductions",
    status: "preview",
    summary: {
      total_entries: previewDeductionRecords.length,
      this_month_entries: previewDeductionRecords.filter((entry) =>
        entry.deduction_date.startsWith(monthPrefix),
      ).length,
      manual_entries: previewDeductionRecords.filter((entry) => !entry.is_auto_record).length,
      auto_entries: previewDeductionRecords.filter((entry) => entry.is_auto_record).length,
    },
    recent_entries: previewDeductionRecords
      .slice()
      .sort((left, right) =>
        `${right.deduction_date}-${right.id}`.localeCompare(`${left.deduction_date}-${left.id}`),
      )
      .slice(0, 12)
      .map((entry) => buildDeductionEntry(entry)),
  };
}

function buildRestaurantsDashboard() {
  return {
    module: "restaurants",
    status: "preview",
    summary: {
      total_restaurants: previewRestaurants.length,
      active_restaurants: previewRestaurants.filter((entry) => entry.active).length,
      passive_restaurants: previewRestaurants.filter((entry) => !entry.active).length,
      fixed_monthly_restaurants: previewRestaurants.filter(
        (entry) => entry.pricing_model === "fixed_monthly",
      ).length,
    },
    recent_entries: previewRestaurants
      .slice()
      .sort((left, right) => right.id - left.id)
      .slice(0, 10)
      .map((entry) => buildRestaurantEntry(entry)),
  };
}

function buildSalesDashboard() {
  return {
    module: "sales",
    status: "preview",
    summary: {
      total_entries: previewSalesRecords.length,
      open_follow_up: previewSalesRecords.filter((entry) =>
        ["Yeni Talep", "Takipte", "Teklif Gonderildi", "Pazarlik"].includes(entry.status),
      ).length,
      proposal_stage: previewSalesRecords.filter((entry) =>
        ["Teklif Gonderildi", "Pazarlik"].includes(entry.status),
      ).length,
      won_count: previewSalesRecords.filter((entry) => entry.status === "Kazanildi").length,
    },
    recent_entries: previewSalesRecords
      .slice()
      .sort((left, right) => `${right.updated_at}-${right.id}`.localeCompare(`${left.updated_at}-${left.id}`))
      .slice(0, 12)
      .map((entry) => ({
        id: entry.id,
        restaurant_name: entry.restaurant_name,
        city: entry.city,
        district: entry.district,
        contact_name: entry.contact_name,
        lead_source: entry.lead_source,
        proposed_quote: entry.proposed_quote,
        pricing_model_label: pricingModelLabel(entry.pricing_model),
        status: entry.status,
        assigned_owner: entry.assigned_owner,
        updated_at: entry.updated_at,
      })),
  };
}

function buildPurchasesDashboard() {
  const monthPrefix = "2026-04";
  return {
    module: "purchases",
    status: "preview",
    summary: {
      total_entries: previewPurchaseRecords.length,
      this_month_entries: previewPurchaseRecords.filter((entry) =>
        entry.purchase_date.startsWith(monthPrefix),
      ).length,
      this_month_total_invoice: previewPurchaseRecords
        .filter((entry) => entry.purchase_date.startsWith(monthPrefix))
        .reduce((sum, entry) => sum + entry.total_invoice_amount, 0),
      distinct_suppliers: new Set(previewPurchaseRecords.map((entry) => entry.supplier)).size,
    },
    recent_entries: previewPurchaseRecords
      .slice()
      .sort((left, right) => `${right.purchase_date}-${right.id}`.localeCompare(`${left.purchase_date}-${left.id}`))
      .slice(0, 12)
      .map((entry) => buildPurchaseEntry(entry)),
  };
}

function buildPayrollDashboard(
  month: string | null,
  role: string | null,
  restaurant: string | null,
) {
  const selectedMonth = month || "2026-04";
  const roleOptions = ["Tümü", ...new Set(previewPersonnelRecords.map((entry) => entry.role))];
  const restaurantOptions = ["Tümü", ...previewRestaurants.filter((entry) => entry.active).map((entry) => entry.label)];
  const selectedRole = role && role !== "Tümü" ? role : "Tümü";
  const selectedRestaurant = restaurant && restaurant !== "Tümü" ? restaurant : "Tümü";

  const entries = previewPersonnelRecords
    .filter((entry) => entry.status === "Aktif")
    .filter((entry) => (selectedRole === "Tümü" ? true : entry.role === selectedRole))
    .filter((entry) =>
      selectedRestaurant === "Tümü" ? true : restaurantLabel(entry.restaurant_id) === selectedRestaurant,
    )
    .map((entry) => {
      const attendanceRows = previewAttendanceRecords.filter(
        (row) =>
          row.entry_date.startsWith(selectedMonth) &&
          (row.primary_person_id === entry.id || row.replacement_person_id === entry.id),
      );
      const deductions = previewDeductionRecords
        .filter(
          (row) => row.personnel_id === entry.id && row.deduction_date.startsWith(selectedMonth),
        )
        .reduce((sum, row) => sum + row.amount, 0);
      const totalHours = attendanceRows.reduce((sum, row) => sum + row.worked_hours, 0);
      const totalPackages = attendanceRows.reduce((sum, row) => sum + row.package_count, 0);
      const grossPay = Math.round(totalHours * 220 + entry.monthly_fixed_cost);
      const restaurantCount = new Set(
        attendanceRows.map((row) => restaurantLabel(row.restaurant_id)).filter(Boolean),
      ).size;
      const costModel = entry.monthly_fixed_cost > 0 ? "Sabit + Saat" : "Saat Bazlı";
      return {
        personnel_id: entry.id,
        personnel: entry.full_name,
        role: entry.role,
        status: entry.status,
        total_hours: totalHours,
        total_packages: totalPackages,
        gross_pay: grossPay,
        total_deductions: deductions,
        net_payment: Math.max(grossPay - deductions, 0),
        restaurant_count: restaurantCount,
        cost_model: costModel,
      };
    })
    .sort((left, right) => right.net_payment - left.net_payment);

  const summary = entries.length
    ? {
        selected_month: selectedMonth,
        personnel_count: entries.length,
        total_hours: entries.reduce((sum, entry) => sum + entry.total_hours, 0),
        total_packages: entries.reduce((sum, entry) => sum + entry.total_packages, 0),
        gross_payroll: entries.reduce((sum, entry) => sum + entry.gross_pay, 0),
        total_deductions: entries.reduce((sum, entry) => sum + entry.total_deductions, 0),
        net_payment: entries.reduce((sum, entry) => sum + entry.net_payment, 0),
      }
    : null;

  const costModelBreakdown = entries.reduce<
    Array<{
      cost_model: string;
      personnel_count: number;
      total_hours: number;
      total_packages: number;
      net_payment: number;
    }>
  >((accumulator, entry) => {
    const existing = accumulator.find((item) => item.cost_model === entry.cost_model);
    if (existing) {
      existing.personnel_count += 1;
      existing.total_hours += entry.total_hours;
      existing.total_packages += entry.total_packages;
      existing.net_payment += entry.net_payment;
    } else {
      accumulator.push({
        cost_model: entry.cost_model,
        personnel_count: 1,
        total_hours: entry.total_hours,
        total_packages: entry.total_packages,
        net_payment: entry.net_payment,
      });
    }
    return accumulator;
  }, []);

  const roleBreakdown = entries.reduce<
    Array<{
      role: string;
      personnel_count: number;
      total_hours: number;
      total_packages: number;
      net_payment: number;
    }>
  >((accumulator, entry) => {
    const existing = accumulator.find((item) => item.role === entry.role);
    if (existing) {
      existing.personnel_count += 1;
      existing.total_hours += entry.total_hours;
      existing.total_packages += entry.total_packages;
      existing.net_payment += entry.net_payment;
    } else {
      accumulator.push({
        role: entry.role,
        personnel_count: 1,
        total_hours: entry.total_hours,
        total_packages: entry.total_packages,
        net_payment: entry.net_payment,
      });
    }
    return accumulator;
  }, []);

  return {
    module: "payroll",
    status: "preview",
    month_options: ["2026-04", "2026-03", "2026-02"],
    selected_month: selectedMonth,
    role_options: roleOptions,
    restaurant_options: restaurantOptions,
    selected_role: selectedRole,
    selected_restaurant: selectedRestaurant,
    summary,
    entries,
    cost_model_breakdown: costModelBreakdown,
    role_breakdown: roleBreakdown,
    top_personnel: entries.slice(0, 5),
  };
}

function buildEquipmentDashboard() {
  const monthPrefix = "2026-04";
  const issueEntries = previewEquipmentIssueRecords.map((entry) => buildEquipmentIssueEntry(entry));
  const boxEntries = previewBoxReturnRecords.map((entry) => buildBoxReturnEntry(entry));
  const installmentEntries = issueEntries
    .filter((entry) => entry.installment_count > 1)
    .map((entry) => ({
      deduction_date: entry.issue_date,
      personnel_label: entry.personnel_label,
      deduction_type: "equipment_installment",
      amount: entry.total_sale / entry.installment_count,
      notes: `${entry.item_name} · ${entry.installment_count} taksit`,
    }));

  const salesProfit = previewEquipmentIssueItems.map((itemName) => {
    const rows = issueEntries.filter((entry) => entry.item_name === itemName);
    return {
      item_name: itemName,
      sold_qty: rows.reduce((sum, entry) => sum + entry.quantity, 0),
      total_cost: rows.reduce((sum, entry) => sum + entry.total_cost, 0),
      total_sale: rows.reduce((sum, entry) => sum + entry.total_sale, 0),
      gross_profit: rows.reduce((sum, entry) => sum + entry.gross_profit, 0),
    };
  }).filter((entry) => entry.sold_qty > 0);

  const purchaseSummary = previewEquipmentIssueItems.map((itemName) => {
    const rows = previewPurchaseRecords.filter((entry) => entry.item_name === itemName);
    const purchasedQty = rows.reduce((sum, entry) => sum + entry.quantity, 0);
    const purchasedTotal = rows.reduce((sum, entry) => sum + entry.total_invoice_amount, 0);
    return {
      item_name: itemName,
      purchased_qty: purchasedQty,
      purchased_total: purchasedTotal,
      weighted_unit_cost: purchasedQty > 0 ? purchasedTotal / purchasedQty : 0,
    };
  }).filter((entry) => entry.purchased_qty > 0);

  return {
    module: "equipment",
    status: "preview",
    summary: {
      total_issues: issueEntries.length,
      this_month_issues: issueEntries.filter((entry) => entry.issue_date.startsWith(monthPrefix)).length,
      installment_rows: installmentEntries.length,
      total_box_returns: boxEntries.reduce((sum, entry) => sum + entry.quantity, 0),
      total_box_payout: boxEntries.reduce((sum, entry) => sum + entry.payout_amount, 0),
      distinct_items: new Set(issueEntries.map((entry) => entry.item_name)).size,
    },
    recent_issues: issueEntries.slice().sort((a, b) => `${b.issue_date}-${b.id}`.localeCompare(`${a.issue_date}-${a.id}`)).slice(0, 10),
    recent_box_returns: boxEntries.slice().sort((a, b) => `${b.return_date}-${b.id}`.localeCompare(`${a.return_date}-${a.id}`)).slice(0, 10),
    installment_entries: installmentEntries.slice(0, 10),
    sales_profit: salesProfit,
    purchase_summary: purchaseSummary,
  };
}

function buildAuditDashboard() {
  const records = previewAuditRecords.slice().sort((a, b) => `${b.created_at}-${b.id}`.localeCompare(`${a.created_at}-${a.id}`));
  return {
    module: "audit",
    status: "preview",
    summary: {
      total_entries: records.length,
      last_7_days: records.filter((entry) => entry.created_at >= "2026-04-08T00:00:00Z").length,
      unique_actors: new Set(records.map((entry) => entry.actor_username)).size,
      unique_entities: new Set(records.map((entry) => `${entry.entity_type}:${entry.entity_id}`)).size,
    },
    recent_entries: records.slice(0, 12).map((entry) => buildAuditEntry(entry)),
    action_options: [...new Set(records.map((entry) => entry.action_type))],
    entity_options: [...new Set(records.map((entry) => entry.entity_type))],
    actor_options: [...new Set(records.map((entry) => entry.actor_full_name))],
  };
}

function buildReportsDashboard(month: string | null) {
  const selectedMonth = month || "2026-04";
  const attendanceRows = previewAttendanceRecords.filter((entry) => entry.entry_date.startsWith(selectedMonth));
  const activePersonnelIds = new Set(attendanceRows.map((entry) => entry.primary_person_id).filter(Boolean));
  const restaurantIds = new Set(attendanceRows.map((entry) => entry.restaurant_id));
  const activeRestaurants = previewRestaurants.filter((entry) => entry.active);

  const invoiceEntries = previewRestaurants.map((restaurant) => {
    const rows = attendanceRows.filter((entry) => entry.restaurant_id === restaurant.id);
    const totalHours = rows.reduce((sum, row) => sum + row.worked_hours, 0);
    const totalPackages = rows.reduce((sum, row) => sum + row.package_count, 0);
    const grossInvoice =
      restaurant.pricing_model === "fixed_monthly"
        ? restaurant.fixed_monthly_fee || totalHours * 420
        : totalPackages * 72;
    const netInvoice = grossInvoice / 1.2;
    return {
      restaurant: restaurant.label,
      pricing_model: restaurant.pricing_model === "fixed_monthly" ? "Sabit Aylık" : "Paket Bazlı",
      total_hours: totalHours,
      total_packages: totalPackages,
      net_invoice: Math.round(netInvoice),
      gross_invoice: Math.round(grossInvoice),
    };
  }).sort((left, right) => right.gross_invoice - left.gross_invoice);

  const costEntries = previewPersonnelRecords
    .filter((entry) => activePersonnelIds.has(entry.id))
    .map((entry) => {
      const rows = attendanceRows.filter(
        (attendance) =>
          attendance.primary_person_id === entry.id || attendance.replacement_person_id === entry.id,
      );
      const totalHours = rows.reduce((sum, row) => sum + row.worked_hours, 0);
      const totalPackages = rows.reduce((sum, row) => sum + row.package_count, 0);
      const totalDeductions = previewDeductionRecords
        .filter(
          (deduction) =>
            deduction.personnel_id === entry.id && deduction.deduction_date.startsWith(selectedMonth),
        )
        .reduce((sum, deduction) => sum + deduction.amount, 0);
      const netCost = Math.round(totalHours * 220 + totalDeductions + entry.monthly_fixed_cost);
      return {
        personnel: entry.full_name,
        role: entry.role,
        total_hours: totalHours,
        total_packages: totalPackages,
        total_deductions: totalDeductions,
        net_cost: netCost,
        cost_model: entry.monthly_fixed_cost > 0 ? "Sabit + Saat" : "Saat Bazlı",
      };
    })
    .sort((left, right) => right.net_cost - left.net_cost);

  const totalRevenue = invoiceEntries.reduce((sum, row) => sum + row.gross_invoice, 0);
  const totalPersonnelCost = costEntries.reduce((sum, row) => sum + row.net_cost, 0);
  const totalHours = invoiceEntries.reduce((sum, row) => sum + row.total_hours, 0);
  const totalPackages = invoiceEntries.reduce((sum, row) => sum + row.total_packages, 0);
  const grossProfit = totalRevenue - totalPersonnelCost;
  const sideIncomeNet = Math.round(totalRevenue * 0.045);
  const fuelReflectionAmount = Math.round(totalPackages * 18);
  const companyFuelReflectionAmount = Math.round(fuelReflectionAmount * 0.42);
  const uttsFuelDiscountAmount = Math.round(companyFuelReflectionAmount * 0.07);
  const partnerCardDiscountAmount = Math.max(sideIncomeNet - uttsFuelDiscountAmount, 0);

  const modelBreakdown = invoiceEntries.reduce<
    Array<{
      pricing_model: string;
      restaurant_count: number;
      total_hours: number;
      total_packages: number;
      gross_invoice: number;
    }>
  >((accumulator, entry) => {
    const current = accumulator.find((item) => item.pricing_model === entry.pricing_model);
    if (current) {
      current.restaurant_count += 1;
      current.total_hours += entry.total_hours;
      current.total_packages += entry.total_packages;
      current.gross_invoice += entry.gross_invoice;
    } else {
      accumulator.push({
        pricing_model: entry.pricing_model,
        restaurant_count: 1,
        total_hours: entry.total_hours,
        total_packages: entry.total_packages,
        gross_invoice: entry.gross_invoice,
      });
    }
    return accumulator;
  }, []);

  const sharedOverheadEntries = previewPersonnelRecords
    .filter(
      (entry) =>
        entry.status === "Aktif" &&
        ["Joker", "Bölge Müdürü"].includes(entry.role) &&
        entry.monthly_fixed_cost > 0,
    )
    .map((entry) => ({
      personnel: entry.full_name,
      role: entry.role,
      gross_cost: entry.monthly_fixed_cost,
      total_deductions: 0,
      net_cost: entry.monthly_fixed_cost,
      allocated_restaurant_count: activeRestaurants.length,
      share_per_restaurant:
        activeRestaurants.length > 0 ? entry.monthly_fixed_cost / activeRestaurants.length : 0,
    }));

  const distributionEntries = attendanceRows
    .map((entry) => {
      const personnel = previewPersonnelRecords.find((item) => item.id === entry.primary_person_id);
      const restaurant = previewRestaurants.find((item) => item.id === entry.restaurant_id);
      if (!personnel || !restaurant) {
        return null;
      }
      const personnelCost = costEntries.find((item) => item.personnel === personnel.full_name);
      return {
        restaurant: restaurant.label,
        personnel: personnel.full_name,
        role: personnel.role,
        total_hours: entry.worked_hours,
        total_packages: entry.package_count,
        allocated_cost: personnelCost ? Math.round(personnelCost.net_cost / Math.max(attendanceRows.length, 1)) : 0,
        allocation_source:
          personnel.monthly_fixed_cost > 0 && entry.worked_hours <= 0
            ? "Sabit maliyet payı"
            : "Değişken maliyet",
      };
    })
    .filter(Boolean)
    .slice(0, 18);

  const sideIncomeEntries = [
    {
      item: "UTTS Yakıt İndirimi",
      revenue: uttsFuelDiscountAmount,
      cost: 0,
      net_profit: uttsFuelDiscountAmount,
    },
    {
      item: "Partner Kart İndirimi",
      revenue: partnerCardDiscountAmount,
      cost: 0,
      net_profit: partnerCardDiscountAmount,
    },
  ];
  const sharedOverheadPerRestaurant = sharedOverheadEntries.reduce(
    (total, entry) => total + entry.share_per_restaurant,
    0,
  );
  const profitEntries = invoiceEntries.map((entry) => {
    const directPersonnelCost = distributionEntries
      .filter((item) => item?.restaurant === entry.restaurant)
      .reduce((total, item) => total + (item?.allocated_cost ?? 0), 0);
    const totalPersonnelCostForRestaurant = directPersonnelCost + sharedOverheadPerRestaurant;
    const grossProfitForRestaurant = entry.gross_invoice - totalPersonnelCostForRestaurant;
    return {
      restaurant: entry.restaurant,
      pricing_model: entry.pricing_model,
      total_hours: entry.total_hours,
      total_packages: entry.total_packages,
      net_invoice: entry.net_invoice,
      gross_invoice: entry.gross_invoice,
      direct_personnel_cost: directPersonnelCost,
      shared_overhead_cost: sharedOverheadPerRestaurant,
      total_personnel_cost: totalPersonnelCostForRestaurant,
      gross_profit: grossProfitForRestaurant,
      profit_margin_percent:
        entry.gross_invoice > 0 ? (grossProfitForRestaurant / entry.gross_invoice) * 100 : 0,
    };
  });

  return {
    module: "reports",
    status: "preview",
    month_options: ["2026-04", "2026-03", "2026-02"],
    selected_month: selectedMonth,
    summary: {
      selected_month: selectedMonth,
      restaurant_count: restaurantIds.size,
      courier_count: activePersonnelIds.size,
      total_hours: totalHours,
      total_packages: totalPackages,
      total_revenue: totalRevenue,
      total_personnel_cost: totalPersonnelCost,
      gross_profit: grossProfit,
      side_income_net: sideIncomeNet,
    },
    invoice_entries: invoiceEntries,
    cost_entries: costEntries,
    profit_entries: profitEntries,
    model_breakdown: modelBreakdown,
    top_restaurants: [...invoiceEntries].slice(0, 5)
      .map((entry) => ({
        restaurant: entry.restaurant,
        pricing_model: entry.pricing_model,
        total_hours: entry.total_hours,
        total_packages: entry.total_packages,
        gross_invoice: entry.gross_invoice,
      })),
    top_couriers: [...costEntries].slice(0, 5)
      .map((entry) => ({
        personnel: entry.personnel,
        role: entry.role,
        total_hours: entry.total_hours,
        total_deductions: entry.total_deductions,
        net_cost: entry.net_cost,
        cost_model: entry.cost_model,
      })),
    coverage: {
      covered_restaurant_count: restaurantIds.size,
      operational_restaurant_count: activeRestaurants.length,
    },
    shared_overhead_entries: sharedOverheadEntries,
    distribution_entries: distributionEntries,
    side_income_entries: sideIncomeEntries,
    side_income_snapshot: {
      fuel_reflection_amount: fuelReflectionAmount,
      company_fuel_reflection_amount: companyFuelReflectionAmount,
      utts_fuel_discount_amount: uttsFuelDiscountAmount,
      partner_card_discount_amount: partnerCardDiscountAmount,
    },
  };
}

function nextPersonnelCode() {
  const maxNumeric = previewPersonnelRecords.reduce((maxValue, entry) => {
    const numeric = Number(entry.person_code.replace(/\D/g, "")) || 0;
    return Math.max(maxValue, numeric);
  }, 2400);
  return `PRS-${String(maxNumeric + 1).padStart(4, "0")}`;
}

function nextPersonnelId() {
  return previewPersonnelRecords.reduce((maxValue, entry) => Math.max(maxValue, entry.id), 100) + 1;
}

function nextAttendanceId() {
  return previewAttendanceRecords.reduce((maxValue, entry) => Math.max(maxValue, entry.id), 500) + 1;
}

function nextDeductionId() {
  return previewDeductionRecords.reduce((maxValue, entry) => Math.max(maxValue, entry.id), 800) + 1;
}

function nextRestaurantId() {
  return previewRestaurants.reduce((maxValue, entry) => Math.max(maxValue, entry.id), 4) + 1;
}

function nextSalesId() {
  return previewSalesRecords.reduce((maxValue, entry) => Math.max(maxValue, entry.id), 900) + 1;
}

function nextPurchaseId() {
  return previewPurchaseRecords.reduce((maxValue, entry) => Math.max(maxValue, entry.id), 1000) + 1;
}

function nextEquipmentIssueId() {
  return previewEquipmentIssueRecords.reduce((maxValue, entry) => Math.max(maxValue, entry.id), 1100) + 1;
}

function nextBoxReturnId() {
  return previewBoxReturnRecords.reduce((maxValue, entry) => Math.max(maxValue, entry.id), 1200) + 1;
}

export function buildPreviewResponse(path: string, init: RequestInit = {}) {
  const method = (init.method || "GET").toUpperCase();
  const url = new URL(path, "http://preview.local");
  const pathname = url.pathname;
  const body = readJsonBody(init);

  if (pathname === "/auth/me" && method === "GET") {
    return buildJsonResponse(PREVIEW_USER);
  }

  if (pathname === "/auth/logout" && method === "POST") {
    return buildJsonResponse({ ok: true });
  }

  if (pathname === "/overview/dashboard" && method === "GET") {
    return buildJsonResponse(buildOverviewDashboard());
  }

  if (pathname === "/attendance/dashboard" && method === "GET") {
    return buildJsonResponse(buildAttendanceDashboard());
  }

  if (pathname === "/deductions/dashboard" && method === "GET") {
    return buildJsonResponse(buildDeductionsDashboard());
  }

  if (pathname === "/restaurants/dashboard" && method === "GET") {
    return buildJsonResponse(buildRestaurantsDashboard());
  }

  if (pathname === "/sales/dashboard" && method === "GET") {
    return buildJsonResponse(buildSalesDashboard());
  }

  if (pathname === "/purchases/dashboard" && method === "GET") {
    return buildJsonResponse(buildPurchasesDashboard());
  }

  if (pathname === "/payroll/dashboard" && method === "GET") {
    return buildJsonResponse(
      buildPayrollDashboard(
        url.searchParams.get("month"),
        url.searchParams.get("role"),
        url.searchParams.get("restaurant"),
      ),
    );
  }

  if (pathname === "/payroll/document" && method === "GET") {
    const personnelId = url.searchParams.get("personnel_id") || "personel";
    const month = url.searchParams.get("month") || "2026-04";
    const fileName = `hakedis_${personnelId}_${month}.pdf`;
    const pdfStub = `%PDF-1.4\n% Preview payroll document\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF`;
    return new Response(pdfStub, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${fileName}"`,
      },
    });
  }

  if (pathname === "/equipment/dashboard" && method === "GET") {
    return buildJsonResponse(buildEquipmentDashboard());
  }

  if (pathname === "/audit/dashboard" && method === "GET") {
    return buildJsonResponse(buildAuditDashboard());
  }

  if (pathname === "/attendance/form-options" && method === "GET") {
    const restaurantId = Number(url.searchParams.get("restaurant_id") || "");
    const includeAllActive = url.searchParams.get("include_all_active") === "true";
    return buildJsonResponse(
      buildAttendanceFormOptions(Number.isFinite(restaurantId) ? restaurantId : null, includeAllActive),
    );
  }

  if (pathname === "/deductions/form-options" && method === "GET") {
    return buildJsonResponse(buildDeductionFormOptions());
  }

  if (pathname === "/restaurants/form-options" && method === "GET") {
    return buildJsonResponse(buildRestaurantFormOptions());
  }

  if (pathname === "/sales/form-options" && method === "GET") {
    return buildJsonResponse(buildSalesFormOptions());
  }

  if (pathname === "/purchases/form-options" && method === "GET") {
    return buildJsonResponse(buildPurchaseFormOptions());
  }

  if (pathname === "/equipment/form-options" && method === "GET") {
    return buildJsonResponse(buildEquipmentFormOptions());
  }

  if (pathname === "/attendance/entries" && method === "GET") {
    const entries = filterAttendanceEntries(url.searchParams).map(buildAttendanceEntry);
    return buildJsonResponse({
      total_entries: entries.length,
      entries,
    });
  }

  if (pathname === "/attendance/entries" && method === "POST") {
    const nextRecord: PreviewAttendanceRecord = {
      id: nextAttendanceId(),
      entry_date: String(body.entry_date || "2026-04-15"),
      restaurant_id: Number(body.restaurant_id || previewRestaurants[0]?.id || 1),
      entry_mode: String(body.entry_mode || "Restoran Kuryesi"),
      primary_person_id: body.primary_person_id ? Number(body.primary_person_id) : null,
      replacement_person_id: body.replacement_person_id ? Number(body.replacement_person_id) : null,
      absence_reason: String(body.absence_reason || ""),
      worked_hours: Number(body.worked_hours || 0),
      package_count: Number(body.package_count || 0),
      monthly_invoice_amount: Number(body.monthly_invoice_amount || 0),
      notes: String(body.notes || ""),
    };
    previewAttendanceRecords = [nextRecord, ...previewAttendanceRecords];
    return buildJsonResponse({
      message: "Preview kaydı oluşturuldu.",
      entry_id: nextRecord.id,
    });
  }

  if (pathname === "/attendance/entries/bulk" && method === "POST") {
    const rows = Array.isArray(body.rows) ? body.rows : [];
    const createdIds: number[] = [];
    rows.forEach((row) => {
      const personId = Number(row?.person_id || 0);
      const workedHours = Number(row?.worked_hours || 0);
      const packageCount = Number(row?.package_count || 0);
      const entryStatus = String(row?.entry_status || "Normal");
      const notes = String(row?.notes || "");
      if (!personId) {
        return;
      }
      if (workedHours === 0 && packageCount === 0 && entryStatus === "Normal") {
        return;
      }
      const recordId = nextAttendanceId();
      previewAttendanceRecords = [
        {
          id: recordId,
          entry_date: String(body.entry_date || "2026-04-15"),
          restaurant_id: Number(body.restaurant_id || previewRestaurants[0]?.id || 1),
          entry_mode: "Restoran Kuryesi",
          primary_person_id: personId,
          replacement_person_id: personId,
          absence_reason: "",
          worked_hours: workedHours,
          package_count: packageCount,
          monthly_invoice_amount: 0,
          notes: notes ? `${notes} | Kaynak: Toplu Puantaj` : "Kaynak: Toplu Puantaj",
        },
        ...previewAttendanceRecords,
      ];
      createdIds.push(recordId);
    });
    return buildJsonResponse(
      {
        entry_ids: createdIds,
        created_count: createdIds.length,
        message: `${createdIds.length} toplu puantaj kaydı oluşturuldu.`,
      },
      createdIds.length ? 201 : 422,
    );
  }

  if (pathname === "/attendance/entries" && method === "DELETE") {
    const entryIds = Array.isArray(body.entry_ids)
      ? body.entry_ids.map((value) => Number(value)).filter((value) => Number.isFinite(value))
      : [];
    previewAttendanceRecords = previewAttendanceRecords.filter((entry) => !entryIds.includes(entry.id));
    return buildJsonResponse({
      entry_ids: entryIds,
      deleted_count: entryIds.length,
      message: "Preview seçili kayıtları silindi.",
    });
  }

  if (pathname === "/attendance/entries/filter" && method === "DELETE") {
    const dateFrom = String(body.date_from || "");
    const dateTo = String(body.date_to || "");
    const restaurantId = body.restaurant_id ? Number(body.restaurant_id) : null;
    const search = String(body.search || "").trim().toLocaleLowerCase("tr-TR");
    const deletable = previewAttendanceRecords.filter((entry) => {
      if (dateFrom && entry.entry_date < dateFrom) {
        return false;
      }
      if (dateTo && entry.entry_date > dateTo) {
        return false;
      }
      if (restaurantId && entry.restaurant_id !== restaurantId) {
        return false;
      }
      if (!search) {
        return true;
      }
      const haystack = [
        restaurantLabel(entry.restaurant_id),
        personnelLabel(entry.primary_person_id),
        entry.entry_mode,
        entry.notes,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");
      return haystack.includes(search);
    });
    const deleteIds = new Set(deletable.map((entry) => entry.id));
    previewAttendanceRecords = previewAttendanceRecords.filter((entry) => !deleteIds.has(entry.id));
    return buildJsonResponse({
      deleted_count: deletable.length,
      date_from: dateFrom,
      date_to: dateTo,
      restaurant_id: restaurantId,
      search,
      message: "Preview filtredeki puantaj kayıtları silindi.",
    });
  }

  if (pathname.startsWith("/attendance/entries/")) {
    const entryId = Number(pathname.split("/").pop());
    const index = previewAttendanceRecords.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Kayıt bulunamadı." }, 404);
    }

    if (method === "GET") {
      return buildJsonResponse({
        entry: buildAttendanceEntry(previewAttendanceRecords[index]),
      });
    }

    if (method === "PUT") {
      previewAttendanceRecords[index] = {
        ...previewAttendanceRecords[index],
        entry_date: String(body.entry_date || previewAttendanceRecords[index].entry_date),
        restaurant_id: Number(body.restaurant_id || previewAttendanceRecords[index].restaurant_id),
        entry_mode: String(body.entry_mode || previewAttendanceRecords[index].entry_mode),
        primary_person_id: body.primary_person_id ? Number(body.primary_person_id) : null,
        replacement_person_id: body.replacement_person_id ? Number(body.replacement_person_id) : null,
        absence_reason: String(body.absence_reason || ""),
        worked_hours: Number(body.worked_hours || 0),
        package_count: Number(body.package_count || 0),
        monthly_invoice_amount: Number(body.monthly_invoice_amount || 0),
        notes: String(body.notes || ""),
      };
      return buildJsonResponse({ message: "Preview puantaj kaydı güncellendi." });
    }

    if (method === "DELETE") {
      previewAttendanceRecords = previewAttendanceRecords.filter((entry) => entry.id !== entryId);
      return buildJsonResponse({ message: "Preview puantaj kaydı silindi." });
    }
  }

  if (pathname === "/personnel/dashboard" && method === "GET") {
    return buildJsonResponse(buildPersonnelDashboard());
  }

  if (pathname === "/reports/dashboard" && method === "GET") {
    const month = url.searchParams.get("month");
    return buildJsonResponse(buildReportsDashboard(month));
  }

  if (pathname === "/personnel/form-options" && method === "GET") {
    return buildJsonResponse(buildPersonnelFormOptions());
  }

  if (pathname === "/auth/change-password" && method === "POST") {
    return buildJsonResponse({
      message: "Preview modunda şifre güncellendi.",
      user: {
        ...PREVIEW_USER,
        must_change_password: false,
      },
    });
  }

  if (pathname === "/personnel/records" && method === "GET") {
    const entries = filterPersonnelEntries(url.searchParams).map(buildPersonnelEntry);
    return buildJsonResponse({
      total_entries: entries.length,
      entries,
    });
  }

  if (pathname === "/deductions/records" && method === "GET") {
    const entries = filterDeductionEntries(url.searchParams).map(buildDeductionEntry);
    return buildJsonResponse({
      total_entries: entries.length,
      entries,
    });
  }

  if (pathname === "/deductions/records" && method === "DELETE") {
    const deductionIds = Array.isArray(body.deduction_ids)
      ? body.deduction_ids.map((value) => Number(value)).filter((value) => Number.isInteger(value) && value > 0)
      : [];
    if (!deductionIds.length) {
      return buildJsonResponse({ detail: "Önce en az bir manuel kesinti kaydı seçmelisin." }, 422);
    }
    const blockedEntries = previewDeductionRecords.filter(
      (entry) => deductionIds.includes(entry.id) && entry.is_auto_record,
    );
    if (blockedEntries.length) {
      return buildJsonResponse(
        { detail: "Otomatik oluşan kesinti kayıtları preview modunda toplu silinemez." },
        422,
      );
    }
    const existingIds = new Set(previewDeductionRecords.map((entry) => entry.id));
    const missingIds = deductionIds.filter((deductionId) => !existingIds.has(deductionId));
    if (missingIds.length) {
      return buildJsonResponse(
        { detail: `Seçilen kesinti kayıtları bulunamadı: ${missingIds.join(", ")}.` },
        404,
      );
    }
    previewDeductionRecords = previewDeductionRecords.filter(
      (entry) => !deductionIds.includes(entry.id),
    );
    return buildJsonResponse({
      deduction_ids: deductionIds,
      deleted_count: deductionIds.length,
      message: `${deductionIds.length} kesinti kaydı silindi.`,
    });
  }

  if (pathname === "/deductions/records" && method === "POST") {
    const nextRecord: PreviewDeductionRecord = {
      id: nextDeductionId(),
      personnel_id: Number(body.personnel_id || previewPersonnelRecords[0]?.id || 101),
      deduction_date: String(body.deduction_date || "2026-04-15"),
      deduction_type: String(body.deduction_type || previewDeductionTypes[0]),
      amount: Number(body.amount || 0),
      notes: String(body.notes || ""),
      auto_source_key: "",
      is_auto_record: false,
    };
    previewDeductionRecords = [nextRecord, ...previewDeductionRecords];
    return buildJsonResponse({
      message: "Preview kesinti kaydı oluşturuldu.",
      entry_id: nextRecord.id,
    });
  }

  if (pathname.startsWith("/deductions/records/")) {
    const entryId = Number(pathname.split("/").pop());
    const index = previewDeductionRecords.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Kesinti bulunamadı." }, 404);
    }

    if (method === "GET") {
      return buildJsonResponse({
        entry: buildDeductionEntry(previewDeductionRecords[index]),
      });
    }

    if (previewDeductionRecords[index].is_auto_record && (method === "PUT" || method === "DELETE")) {
      return buildJsonResponse(
        { detail: "Otomatik oluşan kesinti kayıtları preview modunda düzenlenemez." },
        400,
      );
    }

    if (method === "PUT") {
      previewDeductionRecords[index] = {
        ...previewDeductionRecords[index],
        personnel_id: Number(body.personnel_id || previewDeductionRecords[index].personnel_id),
        deduction_date: String(body.deduction_date || previewDeductionRecords[index].deduction_date),
        deduction_type: String(body.deduction_type || previewDeductionRecords[index].deduction_type),
        amount: Number(body.amount || 0),
        notes: String(body.notes || ""),
      };
      return buildJsonResponse({ message: "Preview kesinti kaydı güncellendi." });
    }

    if (method === "DELETE") {
      previewDeductionRecords = previewDeductionRecords.filter((entry) => entry.id !== entryId);
      return buildJsonResponse({ message: "Preview kesinti kaydı silindi." });
    }
  }

  if (pathname === "/restaurants/records" && method === "GET") {
    const entries = filterRestaurantEntries(url.searchParams).map(buildRestaurantEntry);
    return buildJsonResponse({
      total_entries: entries.length,
      entries,
    });
  }

  if (pathname === "/restaurants/records" && method === "POST") {
    const brand = String(body.brand || "Preview Marka");
    const branch = String(body.branch || "Yeni Şube");
    const nextRecord: PreviewRestaurantRecord = {
      id: nextRestaurantId(),
      brand,
      branch,
      label: `${brand} / ${branch}`,
      pricing_model: String(body.pricing_model || previewRestaurantPricingModels[0]?.value || "hourly_plus_package"),
      hourly_rate: Number(body.hourly_rate || 0),
      package_rate: Number(body.package_rate || 0),
      package_threshold: Number(body.package_threshold || 390),
      package_rate_low: Number(body.package_rate_low || 0),
      package_rate_high: Number(body.package_rate_high || 0),
      fixed_monthly_fee: Number(body.fixed_monthly_fee || 0),
      vat_rate: Number(body.vat_rate || 20),
      target_headcount: Number(body.target_headcount || 1),
      start_date: body.start_date ? String(body.start_date) : "2026-04-15",
      end_date: body.end_date ? String(body.end_date) : null,
      extra_headcount_request: Number(body.extra_headcount_request || 0),
      extra_headcount_request_date: body.extra_headcount_request_date
        ? String(body.extra_headcount_request_date)
        : null,
      reduce_headcount_request: Number(body.reduce_headcount_request || 0),
      reduce_headcount_request_date: body.reduce_headcount_request_date
        ? String(body.reduce_headcount_request_date)
        : null,
      contact_name: String(body.contact_name || ""),
      contact_phone: String(body.contact_phone || ""),
      contact_email: String(body.contact_email || ""),
      company_title: String(body.company_title || ""),
      address: String(body.address || ""),
      tax_office: String(body.tax_office || ""),
      tax_number: String(body.tax_number || ""),
      active: String(body.status || "Aktif") !== "Pasif",
      notes: String(body.notes || ""),
    };
    previewRestaurants = [nextRecord, ...previewRestaurants];
    return buildJsonResponse({
      message: "Preview restoran kaydı oluşturuldu.",
      entry_id: nextRecord.id,
    });
  }

  if (pathname === "/sales/records" && method === "GET") {
    const entries = filterSalesEntries(url.searchParams).map(buildSalesEntry);
    return buildJsonResponse({
      total_entries: entries.length,
      entries,
    });
  }

  if (pathname === "/sales/records" && method === "POST") {
    const timestamp = "2026-04-15T10:30:00Z";
    const nextRecord: PreviewSalesRecord = {
      id: nextSalesId(),
      restaurant_name: String(body.restaurant_name || "Preview Fırsat"),
      city: String(body.city || "Istanbul"),
      district: String(body.district || "Kadikoy"),
      address: String(body.address || ""),
      contact_name: String(body.contact_name || ""),
      contact_phone: String(body.contact_phone || ""),
      contact_email: String(body.contact_email || ""),
      requested_courier_count: Number(body.requested_courier_count || 1),
      lead_source: String(body.lead_source || previewSalesSourceOptions[0]),
      proposed_quote: Number(body.proposed_quote || 0),
      pricing_model: String(body.pricing_model || previewRestaurantPricingModels[0]?.value || "hourly_plus_package"),
      hourly_rate: Number(body.hourly_rate || 0),
      package_rate: Number(body.package_rate || 0),
      package_threshold: Number(body.package_threshold || 390),
      package_rate_low: Number(body.package_rate_low || 0),
      package_rate_high: Number(body.package_rate_high || 0),
      fixed_monthly_fee: Number(body.fixed_monthly_fee || 0),
      status: String(body.status || previewSalesStatusOptions[0]),
      next_follow_up_date: body.next_follow_up_date ? String(body.next_follow_up_date) : null,
      assigned_owner: String(body.assigned_owner || ""),
      notes: String(body.notes || ""),
      created_at: timestamp,
      updated_at: timestamp,
    };
    previewSalesRecords = [nextRecord, ...previewSalesRecords];
    return buildJsonResponse({
      message: "Preview satış fırsatı oluşturuldu.",
      entry_id: nextRecord.id,
    });
  }

  if (pathname === "/purchases/records" && method === "GET") {
    const entries = filterPurchaseEntries(url.searchParams).map(buildPurchaseEntry);
    return buildJsonResponse({
      total_entries: entries.length,
      entries,
    });
  }

  if (pathname === "/purchases/records" && method === "POST") {
    const nextRecord: PreviewPurchaseRecord = {
      id: nextPurchaseId(),
      purchase_date: String(body.purchase_date || "2026-04-15"),
      item_name: String(body.item_name || previewPurchaseItemOptions[0] || "Ekipman"),
      quantity: Number(body.quantity || 1),
      total_invoice_amount: Number(body.total_invoice_amount || 0),
      supplier: String(body.supplier || ""),
      invoice_no: String(body.invoice_no || ""),
      notes: String(body.notes || ""),
    };
    previewPurchaseRecords = [nextRecord, ...previewPurchaseRecords];
    return buildJsonResponse({
      message: "Preview satın alma kaydı oluşturuldu.",
      entry_id: nextRecord.id,
    });
  }

  if (pathname === "/equipment/issues" && method === "GET") {
    const entries = filterEquipmentIssueEntries(url.searchParams).map(buildEquipmentIssueEntry);
    return buildJsonResponse({
      total_entries: entries.length,
      entries,
    });
  }

  if (pathname === "/equipment/issues" && method === "POST") {
    const nextRecord: PreviewEquipmentIssueRecord = {
      id: nextEquipmentIssueId(),
      personnel_id: Number(body.personnel_id || previewPersonnelRecords[0]?.id || 101),
      issue_date: String(body.issue_date || "2026-04-15"),
      item_name: String(body.item_name || previewEquipmentIssueItems[0] || "Kask"),
      quantity: Number(body.quantity || 1),
      unit_cost: Number(body.unit_cost || 0),
      unit_sale_price: Number(body.unit_sale_price || 0),
      vat_rate: Number(
        previewEquipmentItemDefaults[String(body.item_name || previewEquipmentIssueItems[0] || "Kask")]
          ?.default_vat_rate || 20,
      ),
      installment_count: Number(body.installment_count || 1),
      sale_type: String(body.sale_type || previewEquipmentSaleTypeOptions[0]),
      notes: String(body.notes || ""),
      auto_source_key: "",
      is_auto_record: false,
    };
    previewEquipmentIssueRecords = [nextRecord, ...previewEquipmentIssueRecords];
    return buildJsonResponse({
      message: "Preview zimmet kaydı oluşturuldu.",
      entry_id: nextRecord.id,
    });
  }

  if (pathname === "/equipment/issues/bulk-update" && method === "POST") {
    const issueIds = Array.isArray(body.issue_ids)
      ? body.issue_ids.map((value) => Number(value)).filter((value) => Number.isFinite(value))
      : [];
    if (!issueIds.length) {
      return buildJsonResponse({ detail: "Önce en az bir zimmet kaydı seçmelisin." }, 422);
    }
    const blockedEntries = previewEquipmentIssueRecords.filter(
      (entry) => issueIds.includes(entry.id) && entry.is_auto_record,
    );
    if (blockedEntries.length) {
      return buildJsonResponse(
        {
          detail: `Otomatik oluşan zimmet kayıtları preview modunda toplu güncellenemez: ${blockedEntries
            .map((entry) => `${entry.issue_date} | ${personnelLabel(entry.personnel_id) || "Personel"} | ${entry.item_name}`)
            .join(", ")}.`,
        },
        422,
      );
    }
    previewEquipmentIssueRecords = previewEquipmentIssueRecords.map((entry) => {
      if (!issueIds.includes(entry.id)) {
        return entry;
      }
      const nextNotes = String(body.note_append_text || "").trim();
      return {
        ...entry,
        issue_date: body.issue_date ? String(body.issue_date) : entry.issue_date,
        unit_cost:
          body.unit_cost !== null && body.unit_cost !== undefined ? Number(body.unit_cost || 0) : entry.unit_cost,
        unit_sale_price:
          body.unit_sale_price !== null && body.unit_sale_price !== undefined
            ? Number(body.unit_sale_price || 0)
            : entry.unit_sale_price,
        vat_rate:
          body.vat_rate !== null && body.vat_rate !== undefined ? Number(body.vat_rate || 0) : entry.vat_rate,
        installment_count:
          body.installment_count !== null && body.installment_count !== undefined
            ? Number(body.installment_count || 1)
            : entry.installment_count,
        sale_type: body.sale_type ? String(body.sale_type) : entry.sale_type,
        notes: nextNotes ? [entry.notes, nextNotes].filter(Boolean).join("\n") : entry.notes,
      };
    });
    return buildJsonResponse({
      updated_count: issueIds.length,
      message: `${issueIds.length} zimmet kaydı güncellendi.`,
    });
  }

  if (pathname === "/equipment/issues/bulk-delete" && method === "POST") {
    const issueIds = Array.isArray(body.issue_ids)
      ? body.issue_ids.map((value) => Number(value)).filter((value) => Number.isFinite(value))
      : [];
    if (!issueIds.length) {
      return buildJsonResponse({ detail: "Önce en az bir zimmet kaydı seçmelisin." }, 422);
    }
    const blockedEntries = previewEquipmentIssueRecords.filter(
      (entry) => issueIds.includes(entry.id) && entry.is_auto_record,
    );
    if (blockedEntries.length) {
      return buildJsonResponse(
        {
          detail: `Otomatik oluşan zimmet kayıtları preview modunda toplu silinemez: ${blockedEntries
            .map((entry) => `${entry.issue_date} | ${personnelLabel(entry.personnel_id) || "Personel"} | ${entry.item_name}`)
            .join(", ")}.`,
        },
        422,
      );
    }
    previewEquipmentIssueRecords = previewEquipmentIssueRecords.filter((entry) => !issueIds.includes(entry.id));
    return buildJsonResponse({
      deleted_count: issueIds.length,
      message: `${issueIds.length} zimmet kaydı ve bağlı taksitler silindi.`,
    });
  }

  if (pathname === "/equipment/box-returns" && method === "GET") {
    const entries = filterBoxReturnEntries(url.searchParams).map(buildBoxReturnEntry);
    return buildJsonResponse({
      total_entries: entries.length,
      entries,
    });
  }

  if (pathname === "/equipment/box-returns" && method === "POST") {
    const nextRecord: PreviewBoxReturnRecord = {
      id: nextBoxReturnId(),
      personnel_id: Number(body.personnel_id || previewPersonnelRecords[0]?.id || 101),
      return_date: String(body.return_date || "2026-04-15"),
      quantity: Number(body.quantity || 1),
      condition_status: String(body.condition_status || previewEquipmentReturnConditionOptions[0]),
      payout_amount: Number(body.payout_amount || 0),
      waived: Number(body.payout_amount || 0) <= 0,
      notes: String(body.notes || ""),
    };
    previewBoxReturnRecords = [nextRecord, ...previewBoxReturnRecords];
    return buildJsonResponse({
      message: "Preview box geri alım kaydı oluşturuldu.",
      entry_id: nextRecord.id,
    });
  }

  if (pathname === "/audit/records" && method === "GET") {
    const entries = filterAuditEntries(url.searchParams).map(buildAuditEntry);
    return buildJsonResponse({
      total_entries: entries.length,
      entries,
      action_options: [...new Set(previewAuditRecords.map((entry) => entry.action_type))],
      entity_options: [...new Set(previewAuditRecords.map((entry) => entry.entity_type))],
      actor_options: [...new Set(previewAuditRecords.map((entry) => entry.actor_full_name))],
    });
  }

  if (
    pathname.startsWith("/restaurants/records/") &&
    pathname.endsWith("/toggle-status") &&
    method === "POST"
  ) {
    const entryId = Number(pathname.split("/")[3]);
    const index = previewRestaurants.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Restoran bulunamadı." }, 404);
    }
    previewRestaurants[index] = {
      ...previewRestaurants[index],
      active: !previewRestaurants[index].active,
    };
    return buildJsonResponse({ message: "Preview restoran durumu güncellendi." });
  }

  if (pathname.startsWith("/restaurants/records/")) {
    const entryId = Number(pathname.split("/").pop());
    const index = previewRestaurants.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Restoran bulunamadı." }, 404);
    }

    if (method === "GET") {
      return buildJsonResponse({
        entry: buildRestaurantEntry(previewRestaurants[index]),
      });
    }

    if (method === "PUT") {
      const brand = String(body.brand || previewRestaurants[index].brand);
      const branch = String(body.branch || previewRestaurants[index].branch);
      previewRestaurants[index] = {
        ...previewRestaurants[index],
        brand,
        branch,
        label: `${brand} / ${branch}`,
        pricing_model: String(body.pricing_model || previewRestaurants[index].pricing_model),
        hourly_rate: Number(body.hourly_rate || 0),
        package_rate: Number(body.package_rate || 0),
        package_threshold: Number(body.package_threshold || 390),
        package_rate_low: Number(body.package_rate_low || 0),
        package_rate_high: Number(body.package_rate_high || 0),
        fixed_monthly_fee: Number(body.fixed_monthly_fee || 0),
        vat_rate: Number(body.vat_rate || 20),
        target_headcount: Number(body.target_headcount || 0),
        start_date: body.start_date ? String(body.start_date) : null,
        end_date: body.end_date ? String(body.end_date) : null,
        extra_headcount_request: Number(body.extra_headcount_request || 0),
        extra_headcount_request_date: body.extra_headcount_request_date
          ? String(body.extra_headcount_request_date)
          : null,
        reduce_headcount_request: Number(body.reduce_headcount_request || 0),
        reduce_headcount_request_date: body.reduce_headcount_request_date
          ? String(body.reduce_headcount_request_date)
          : null,
        contact_name: String(body.contact_name || ""),
        contact_phone: String(body.contact_phone || ""),
        contact_email: String(body.contact_email || ""),
        company_title: String(body.company_title || ""),
        address: String(body.address || ""),
        tax_office: String(body.tax_office || ""),
        tax_number: String(body.tax_number || ""),
        active: String(body.status || "Aktif") !== "Pasif",
        notes: String(body.notes || ""),
      };
      return buildJsonResponse({ message: "Preview restoran kaydı güncellendi." });
    }

    if (method === "DELETE") {
      previewRestaurants = previewRestaurants.filter((entry) => entry.id !== entryId);
      return buildJsonResponse({ message: "Preview restoran kaydı silindi." });
    }
  }

  if (pathname.startsWith("/sales/records/")) {
    const entryId = Number(pathname.split("/").pop());
    const index = previewSalesRecords.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Satış fırsatı bulunamadı." }, 404);
    }

    if (method === "GET") {
      return buildJsonResponse({
        entry: buildSalesEntry(previewSalesRecords[index]),
      });
    }

    if (method === "PUT") {
      previewSalesRecords[index] = {
        ...previewSalesRecords[index],
        restaurant_name: String(body.restaurant_name || previewSalesRecords[index].restaurant_name),
        city: String(body.city || previewSalesRecords[index].city),
        district: String(body.district || previewSalesRecords[index].district),
        address: String(body.address || previewSalesRecords[index].address),
        contact_name: String(body.contact_name || previewSalesRecords[index].contact_name),
        contact_phone: String(body.contact_phone || previewSalesRecords[index].contact_phone),
        contact_email: String(body.contact_email || previewSalesRecords[index].contact_email),
        requested_courier_count: Number(
          body.requested_courier_count || previewSalesRecords[index].requested_courier_count,
        ),
        lead_source: String(body.lead_source || previewSalesRecords[index].lead_source),
        proposed_quote: Number(body.proposed_quote || 0),
        pricing_model: String(body.pricing_model || previewSalesRecords[index].pricing_model),
        hourly_rate: Number(body.hourly_rate || 0),
        package_rate: Number(body.package_rate || 0),
        package_threshold: Number(body.package_threshold || 390),
        package_rate_low: Number(body.package_rate_low || 0),
        package_rate_high: Number(body.package_rate_high || 0),
        fixed_monthly_fee: Number(body.fixed_monthly_fee || 0),
        status: String(body.status || previewSalesRecords[index].status),
        next_follow_up_date: body.next_follow_up_date ? String(body.next_follow_up_date) : null,
        assigned_owner: String(body.assigned_owner || previewSalesRecords[index].assigned_owner),
        notes: String(body.notes || previewSalesRecords[index].notes),
        updated_at: "2026-04-15T11:45:00Z",
      };
      return buildJsonResponse({ message: "Preview satış kaydı güncellendi." });
    }

    if (method === "DELETE") {
      previewSalesRecords = previewSalesRecords.filter((entry) => entry.id !== entryId);
      return buildJsonResponse({ message: "Preview satış kaydı silindi." });
    }
  }

  if (pathname.startsWith("/purchases/records/")) {
    const entryId = Number(pathname.split("/").pop());
    const index = previewPurchaseRecords.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Satın alma kaydı bulunamadı." }, 404);
    }

    if (method === "GET") {
      return buildJsonResponse({
        entry: buildPurchaseEntry(previewPurchaseRecords[index]),
      });
    }

    if (method === "PUT") {
      previewPurchaseRecords[index] = {
        ...previewPurchaseRecords[index],
        purchase_date: String(body.purchase_date || previewPurchaseRecords[index].purchase_date),
        item_name: String(body.item_name || previewPurchaseRecords[index].item_name),
        quantity: Number(body.quantity || previewPurchaseRecords[index].quantity),
        total_invoice_amount: Number(body.total_invoice_amount || 0),
        supplier: String(body.supplier || previewPurchaseRecords[index].supplier),
        invoice_no: String(body.invoice_no || previewPurchaseRecords[index].invoice_no),
        notes: String(body.notes || previewPurchaseRecords[index].notes),
      };
      return buildJsonResponse({ message: "Preview satın alma kaydı güncellendi." });
    }

    if (method === "DELETE") {
      previewPurchaseRecords = previewPurchaseRecords.filter((entry) => entry.id !== entryId);
      return buildJsonResponse({ message: "Preview satın alma kaydı silindi." });
    }
  }

  if (pathname.startsWith("/equipment/issues/")) {
    const entryId = Number(pathname.split("/").pop());
    const index = previewEquipmentIssueRecords.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Zimmet kaydı bulunamadı." }, 404);
    }

    if (method === "GET") {
      return buildJsonResponse({
        entry: buildEquipmentIssueEntry(previewEquipmentIssueRecords[index]),
      });
    }

    if (previewEquipmentIssueRecords[index].is_auto_record && (method === "PUT" || method === "DELETE")) {
      return buildJsonResponse(
        { detail: "Otomatik oluşan zimmet kayıtları preview modunda düzenlenemez." },
        400,
      );
    }

    if (method === "PUT") {
      previewEquipmentIssueRecords[index] = {
        ...previewEquipmentIssueRecords[index],
        personnel_id: Number(body.personnel_id || previewEquipmentIssueRecords[index].personnel_id),
        issue_date: String(body.issue_date || previewEquipmentIssueRecords[index].issue_date),
        item_name: String(body.item_name || previewEquipmentIssueRecords[index].item_name),
        quantity: Number(body.quantity || previewEquipmentIssueRecords[index].quantity),
        unit_cost: Number(body.unit_cost || 0),
        unit_sale_price: Number(body.unit_sale_price || 0),
        installment_count: Number(body.installment_count || 1),
        sale_type: String(body.sale_type || previewEquipmentIssueRecords[index].sale_type),
        notes: String(body.notes || previewEquipmentIssueRecords[index].notes),
      };
      return buildJsonResponse({ message: "Preview zimmet kaydı güncellendi." });
    }

    if (method === "DELETE") {
      previewEquipmentIssueRecords = previewEquipmentIssueRecords.filter((entry) => entry.id !== entryId);
      return buildJsonResponse({ message: "Preview zimmet kaydı silindi." });
    }
  }

  if (pathname.startsWith("/equipment/box-returns/")) {
    const entryId = Number(pathname.split("/").pop());
    const index = previewBoxReturnRecords.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Box geri alım kaydı bulunamadı." }, 404);
    }

    if (method === "GET") {
      return buildJsonResponse({
        entry: buildBoxReturnEntry(previewBoxReturnRecords[index]),
      });
    }

    if (method === "PUT") {
      previewBoxReturnRecords[index] = {
        ...previewBoxReturnRecords[index],
        personnel_id: Number(body.personnel_id || previewBoxReturnRecords[index].personnel_id),
        return_date: String(body.return_date || previewBoxReturnRecords[index].return_date),
        quantity: Number(body.quantity || previewBoxReturnRecords[index].quantity),
        condition_status: String(body.condition_status || previewBoxReturnRecords[index].condition_status),
        payout_amount: Number(body.payout_amount || 0),
        waived: Number(body.payout_amount || 0) <= 0,
        notes: String(body.notes || previewBoxReturnRecords[index].notes),
      };
      return buildJsonResponse({ message: "Preview box geri alım kaydı güncellendi." });
    }

    if (method === "DELETE") {
      previewBoxReturnRecords = previewBoxReturnRecords.filter((entry) => entry.id !== entryId);
      return buildJsonResponse({ message: "Preview box geri alım kaydı silindi." });
    }
  }

  if (pathname === "/personnel/records" && method === "POST") {
    const nextRecord: PreviewPersonnelRecord = {
      id: nextPersonnelId(),
      person_code: nextPersonnelCode(),
      full_name: String(body.full_name || "Preview Personel"),
      role: String(body.role || previewRoleOptions[0]),
      status: String(body.status || previewStatusOptions[0]),
      phone: String(body.phone || ""),
      address: String(body.address || ""),
      iban: String(body.iban || ""),
      tax_number: String(body.tax_number || ""),
      tax_office: String(body.tax_office || ""),
      emergency_contact_name: String(body.emergency_contact_name || ""),
      emergency_contact_phone: String(body.emergency_contact_phone || ""),
      accounting_type: String(body.accounting_type || "Kendi Muhasebecisi"),
      new_company_setup: String(body.new_company_setup || "Hayır"),
      accounting_revenue: Number(body.accounting_revenue || 0),
      accountant_cost: Number(body.accountant_cost || 0),
      company_setup_revenue: Number(body.company_setup_revenue || 0),
      company_setup_cost: Number(body.company_setup_cost || 0),
      restaurant_id: body.assigned_restaurant_id ? Number(body.assigned_restaurant_id) : null,
      vehicle_mode: String(body.vehicle_mode || previewVehicleModeOptions[0]),
      current_plate: String(body.current_plate || ""),
      start_date: String(body.start_date || "2026-04-15"),
      monthly_fixed_cost: Number(body.monthly_fixed_cost || 0),
      notes: String(body.notes || ""),
    };
    previewPersonnelRecords = [nextRecord, ...previewPersonnelRecords];
    return buildJsonResponse({
      message: "Preview personel kaydı oluşturuldu.",
      person_code: nextRecord.person_code,
    });
  }

  if (pathname.startsWith("/personnel/records/") && pathname.endsWith("/toggle-status") && method === "POST") {
    const entryId = Number(pathname.split("/")[3]);
    const index = previewPersonnelRecords.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Personel bulunamadı." }, 404);
    }
    previewPersonnelRecords[index] = {
      ...previewPersonnelRecords[index],
      status: previewPersonnelRecords[index].status === "Aktif" ? "Pasif" : "Aktif",
    };
    return buildJsonResponse({
      message: "Preview personel durumu güncellendi.",
    });
  }

  if (pathname.startsWith("/personnel/records/")) {
    const entryId = Number(pathname.split("/").pop());
    const index = previewPersonnelRecords.findIndex((entry) => entry.id === entryId);
    if (index < 0) {
      return buildJsonResponse({ detail: "Personel bulunamadı." }, 404);
    }

    if (method === "GET") {
      return buildJsonResponse({
        entry: buildPersonnelEntry(previewPersonnelRecords[index]),
      });
    }

    if (method === "PUT") {
      previewPersonnelRecords[index] = {
        ...previewPersonnelRecords[index],
        full_name: String(body.full_name || previewPersonnelRecords[index].full_name),
        role: String(body.role || previewPersonnelRecords[index].role),
        phone: String(body.phone || previewPersonnelRecords[index].phone),
        address: String(body.address || previewPersonnelRecords[index].address || ""),
        iban: String(body.iban || previewPersonnelRecords[index].iban || ""),
        tax_number: String(body.tax_number || previewPersonnelRecords[index].tax_number || ""),
        tax_office: String(body.tax_office || previewPersonnelRecords[index].tax_office || ""),
        emergency_contact_name: String(
          body.emergency_contact_name || previewPersonnelRecords[index].emergency_contact_name || "",
        ),
        emergency_contact_phone: String(
          body.emergency_contact_phone || previewPersonnelRecords[index].emergency_contact_phone || "",
        ),
        accounting_type: String(body.accounting_type || previewPersonnelRecords[index].accounting_type || "Kendi Muhasebecisi"),
        new_company_setup: String(body.new_company_setup || previewPersonnelRecords[index].new_company_setup || "Hayır"),
        accounting_revenue: Number(body.accounting_revenue || previewPersonnelRecords[index].accounting_revenue || 0),
        accountant_cost: Number(body.accountant_cost || previewPersonnelRecords[index].accountant_cost || 0),
        company_setup_revenue: Number(body.company_setup_revenue || previewPersonnelRecords[index].company_setup_revenue || 0),
        company_setup_cost: Number(body.company_setup_cost || previewPersonnelRecords[index].company_setup_cost || 0),
        restaurant_id: body.assigned_restaurant_id ? Number(body.assigned_restaurant_id) : null,
        status: String(body.status || previewPersonnelRecords[index].status),
        start_date: String(body.start_date || previewPersonnelRecords[index].start_date || ""),
        vehicle_mode: String(body.vehicle_mode || previewPersonnelRecords[index].vehicle_mode),
        current_plate: String(body.current_plate || ""),
        monthly_fixed_cost: Number(body.monthly_fixed_cost || 0),
        notes: String(body.notes || ""),
      };
      return buildJsonResponse({
        message: "Preview personel kaydı güncellendi.",
        person_code: previewPersonnelRecords[index].person_code,
      });
    }

    if (method === "DELETE") {
      previewPersonnelRecords = previewPersonnelRecords.filter((entry) => entry.id !== entryId);
      return buildJsonResponse({
        message: "Preview personel kaydı silindi.",
      });
    }
  }

  return null;
}
