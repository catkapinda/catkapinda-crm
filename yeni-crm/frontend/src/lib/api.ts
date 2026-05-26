/**
 * Backend API ile haberleşme katmanı.
 *
 * Sunucu (Server Component) çağrıları doğrudan API URL'ine gider.
 * İstemci (Client Component) çağrıları Next.js rewrite'ı üzerinden gider.
 */

const SERVER_API = process.env.NEXT_PUBLIC_API_URL
  ? (process.env.NEXT_PUBLIC_API_URL.startsWith('http')
      ? process.env.NEXT_PUBLIC_API_URL
      : `http://${process.env.NEXT_PUBLIC_API_URL}`)
  : 'http://localhost:8000';

/**
 * PDF / dosya indirme gibi durumlar için backend'in tam URL'ini döner.
 * Tarayıcıda relative path Next.js rewrites kullanır; ancak `<a download>`
 * bazı tarayıcılarda rewrites'ı atlayabildiği için tam URL daha güvenli.
 */
export function backendUrl(path: string): string {
  return `${SERVER_API}${path.startsWith('/') ? path : `/${path}`}`;
}

export async function apiGet<T>(
  path: string,
  opts?: { revalidate?: number; cache?: RequestCache },
): Promise<T> {
  // SSR'da NEXT_PUBLIC_API_URL (Render internal hostname) hızlı.
  // Client'ta relative path → Next.js rewrites backend'e proxy'ler.
  // (Internal hostname'e tarayıcı erişemez, mutlaka relative gerek.)
  const isBrowser = typeof window !== 'undefined';
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const url = isBrowser ? cleanPath : `${SERVER_API}${cleanPath}`;
  const revalidate = opts?.revalidate ?? 30;
  // revalidate=0 ise 'no-store' kullan; Next.js Data Cache tamamen by-pass
  const fetchInit: RequestInit & { next?: { revalidate?: number } } = {
    headers: { 'Content-Type': 'application/json' },
  };
  if (opts?.cache) {
    fetchInit.cache = opts.cache;
  } else if (revalidate === 0) {
    fetchInit.cache = 'no-store';
  } else {
    fetchInit.next = { revalidate };
  }
  const res = await fetch(url, fetchInit);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

/**
 * Tarayıcıdan (client) yapılan mutasyon çağrıları — Next.js rewrite üzerinden.
 * SSR'da kullanılmaz; relative path tarayıcı domain'ine bağlanır.
 */
export async function apiMutate<T>(
  path: string,
  body: unknown,
  method: 'POST' | 'PATCH' | 'PUT' | 'DELETE' = 'PATCH'
): Promise<T> {
  const res = await fetch(path.startsWith('/') ? path : `/${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `API ${res.status}`;
    try {
      const err = await res.json();
      msg = err?.detail ?? msg;
    } catch {
      /* sessizce yut */
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export type Personnel = {
  id: number;
  person_code: string | null;
  full_name: string | null;
  role: string | null;
  status: string | null;
  phone: string | null;
  current_plate: string | null;
  assigned_restaurant_id: number | null;
  start_date: string | null;
  exit_date: string | null;
  monthly_fixed_cost?: number | null;
  fixed_monthly_billing?: number | null;
  // Araç
  vehicle_type?: string | null;
  motor_purchase?: string | null;
  motor_purchase_sale_price?: number | null;
  motor_purchase_start_date?: string | null;
  motor_purchase_commitment_months?: number | null;
  motor_purchase_installment_count?: number | null;
  motor_purchase_monthly_amount?: number | null;
  motor_purchase_monthly_deduction?: number | null;
  motor_rental?: string | null;
  motor_rental_monthly_amount?: number | null;
  // Muhasebe
  accounting_type?: string | null;
  accountant_cost?: number | null;
  accounting_revenue?: number | null;
  accounting_effective_date?: string | null;
  // Şirket açılışı
  new_company_setup?: string | null;
  company_setup_cost?: number | null;
  company_setup_revenue?: number | null;
  company_setup_effective_date?: string | null;
  cost_model?: string | null;
  // Kimlik & banka
  tc_no?: string | null;
  iban?: string | null;
  tax_number?: string | null;
  tax_office?: string | null;
  address?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  notes?: string | null;
};

export type PersonnelUpdate = Partial<Omit<Personnel, 'id'>>;

export type PersonnelCreate = {
  full_name: string;
  role: string;
  person_code?: string;
  status?: string;
  phone?: string;
  current_plate?: string;
  assigned_restaurant_id?: number;
  start_date?: string;
  monthly_fixed_cost?: number;
  fixed_monthly_billing?: number;
  vehicle_type?: string;
  tc_no?: string;
  iban?: string;
  accounting_type?: string;
  address?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  notes?: string;
};

export async function listPersonnel(status?: 'Aktif' | 'Pasif'): Promise<Personnel[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiGet<Personnel[]>(`/api/personel${q}`);
}

export async function getPersonnel(id: number): Promise<Personnel> {
  return apiGet<Personnel>(`/api/personel/${id}`);
}

export async function updatePersonnel(
  id: number, fields: PersonnelUpdate,
): Promise<Personnel> {
  return apiMutate<Personnel>(`/api/personel/${id}`, fields, 'PATCH');
}

export async function createPersonnel(fields: PersonnelCreate): Promise<Personnel> {
  return apiMutate<Personnel>(`/api/personel`, fields, 'POST');
}

// Pasife alma / kalıcı silme — backend 422'de dict (code+message+context) döner;
// burada onu kullanıcıya gösterilebilir mesaja çeviriyoruz.
export class PersonnelActionError extends Error {
  code: string;
  context: Record<string, unknown>;
  constructor(message: string, code: string, context: Record<string, unknown> = {}) {
    super(message);
    this.name = 'PersonnelActionError';
    this.code = code;
    this.context = context;
  }
}

async function personnelAction<T>(
  path: string,
  method: 'POST' | 'DELETE',
  body: unknown,
): Promise<T> {
  const res = await fetch(path.startsWith('/') ? path : `/${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `API ${res.status}`;
    let code = 'unknown';
    let context: Record<string, unknown> = {};
    try {
      const err = await res.json();
      const d = err?.detail;
      if (typeof d === 'object' && d !== null) {
        msg = (d.message as string) ?? msg;
        code = (d.code as string) ?? code;
        context = (d.context as Record<string, unknown>) ?? {};
      } else if (typeof d === 'string') {
        msg = d;
      }
    } catch {
      /* sessizce yut */
    }
    throw new PersonnelActionError(msg, code, context);
  }
  return res.json() as Promise<T>;
}

export async function deactivatePersonnel(
  id: number, exitDate: string,
): Promise<Personnel> {
  return personnelAction<Personnel>(
    `/api/personel/${id}/deactivate`, 'POST', { exit_date: exitDate },
  );
}

export async function deletePersonnel(
  id: number, confirmName: string,
): Promise<{ deleted: boolean; id: number; full_name: string | null }> {
  return personnelAction(
    `/api/personel/${id}`, 'DELETE', { confirm_name: confirmName },
  );
}

export async function getNextPersonCode(role: string): Promise<{ person_code: string }> {
  return apiGet<{ person_code: string }>(
    `/api/personel/next-code?role=${encodeURIComponent(role)}`,
    { revalidate: 0 },
  );
}

export type TopPerformer = {
  id: number;
  full_name: string | null;
  person_code: string | null;
  role: string | null;
  brand: string | null;
  branch: string | null;
  total_packages: number;
  total_hours: number;
  working_days: number;
};

export async function getTopPerformers(
  period: string = '2026-03',
  limit: number = 3,
): Promise<TopPerformer[]> {
  return apiGet<TopPerformer[]>(
    `/api/personel/top-performers?period=${period}&limit=${limit}`,
  );
}

export type ManagementMember = {
  id: number;
  full_name: string | null;
  person_code: string | null;
  role: string | null;
  salary: number;
  cover_hours: number;
  cover_packages: number;
  cover_days: number;
};

export async function getManagementSummary(
  period: string = '2026-03',
  opts?: { revalidate?: number },
): Promise<ManagementMember[]> {
  return apiGet<ManagementMember[]>(
    `/api/personel/management?period=${period}`,
    // Default: SSR'da her render'da taze veri (period değişimi anlık yansısın)
    { revalidate: opts?.revalidate ?? 0 },
  );
}

// ─────────────────────────────────────────────────────────────
// Dashboard Analytics — kapsamlı gerçek veri
// ─────────────────────────────────────────────────────────────

export type DeductionBreakdown = {
  deduction_type: string;
  count: number;
  total: number;
};

export type RevenueTrendItem = {
  period: string;
  invoiced: number;
  net_paid: number;
};

export type RestaurantBreakdownItem = {
  id: number;
  brand: string;
  branch: string;
  courier_count: number;
  invoiced: number;
  net_paid: number;
  pricing_model: string;
};

export type PersonnelPerformanceItem = {
  personnel_id: number;
  packages: number;
  hours: number;
  score_0_1: number;
};

export type AIInsight = {
  severity: 'info' | 'warning' | 'alert';
  text: string;
  metric: string;
};

export type DashboardAnalytics = {
  period: string;
  invoiced_kdv_haric: number;
  invoiced_kdv_dahil: number;
  tevkifat_total: number;
  total_courier_net: number;
  total_management_salary: number;
  total_costs: number;
  net_profit: number;
  margin_pct: number;
  revenue_trend: RevenueTrendItem[];
  by_restaurant: RestaurantBreakdownItem[];
  deduction_breakdown: DeductionBreakdown[];
  personnel_performance: PersonnelPerformanceItem[];
  ai_insights: AIInsight[];
};

export async function getDashboardAnalytics(
  period: string = '2026-03',
): Promise<DashboardAnalytics> {
  return apiGet<DashboardAnalytics>(`/api/dashboard/analytics?period=${period}`);
}

export async function getAvailablePeriods(): Promise<string[]> {
  return apiGet<string[]>('/api/dashboard/available-periods');
}

// ─────────────────────────────────────────────────────────────
// Faturalar — restoranlara aylık kesilen faturalar
// ─────────────────────────────────────────────────────────────

export type RestaurantInvoice = {
  id: number | null;
  restaurant_id: number;
  rest_brand: string | null;
  rest_branch: string | null;
  period: string;
  invoice_no: string | null;
  courier_count: number;
  amount_excl_vat: number;
  vat_rate: number;
  vat_amount: number;
  amount_incl_vat: number;
  status: 'Beklemede' | 'Ödendi' | 'Kısmi' | string;
  issued_at: string | null;
  paid_at: string | null;
  paid_amount: number;
  balance: number;
  notes: string | null;
  is_manual_only?: boolean;
};

export type InvoiceSummary = {
  period: string;
  count_total: number;
  count_paid: number;
  count_partial: number;
  count_pending: number;
  sum_excl_vat: number;
  sum_vat: number;
  sum_incl_vat: number;
  sum_paid: number;
  sum_balance: number;
  collection_pct: number;
};

export async function listInvoices(period: string = '2026-03'): Promise<RestaurantInvoice[]> {
  return apiGet<RestaurantInvoice[]>(`/api/invoices?period=${period}`);
}

export async function getInvoiceSummary(period: string = '2026-03'): Promise<InvoiceSummary> {
  return apiGet<InvoiceSummary>(`/api/invoices/summary?period=${period}`);
}

export async function upsertInvoice(
  restaurantId: number,
  period: string,
  fields: Partial<{
    invoice_no: string;
    amount_excl_vat: number;
    vat_amount: number;
    amount_incl_vat: number;
    status: string;
    paid_amount: number;
    notes: string;
  }>,
): Promise<RestaurantInvoice> {
  return apiMutate<RestaurantInvoice>(
    `/api/invoices/${restaurantId}?period=${encodeURIComponent(period)}`,
    fields,
    'PUT',
  );
}

export async function markInvoicePaid(
  restaurantId: number,
  period: string,
  amount?: number,
): Promise<RestaurantInvoice> {
  return apiMutate<RestaurantInvoice>(
    `/api/invoices/${restaurantId}/mark-paid?period=${encodeURIComponent(period)}`,
    amount != null ? { amount } : {},
    'POST',
  );
}

export type ThresholdNear = {
  id: number;
  full_name: string | null;
  person_code: string | null;
  brand: string | null;
  branch: string | null;
  packages: number;
  threshold: number;
  rate_low: number;
  rate_high: number;
};

export type CapacityGap = {
  id: number;
  brand: string | null;
  branch: string | null;
  target: number;
  actual: number;
};

export type PageInsights = {
  threshold_near: ThresholdNear[];
  capacity_gaps: CapacityGap[];
  top_recovery: ManagementMember[];
  pending_actions: number;
};

export async function getPageInsights(
  period: string = '2026-03',
): Promise<PageInsights> {
  return apiGet<PageInsights>(`/api/personel/insights?period=${period}`);
}

// AI Insights — Claude API ile üretilen akıllı içgörü raporu
export type AiInsightCard = {
  key: 'esik_asimi' | 'eksik_kapasite' | 'verimlilik' | 'bekleyen_aksiyon';
  label: string;
  value: string;
  sub: string;
  tone?: 'positive' | 'warning' | 'neutral' | 'info';
};

export type AiInsightAction = {
  title: string;
  detail: string;
  priority?: 'yuksek' | 'orta' | 'dusuk';
};

export type AiInsightsPayload = {
  ai?: {
    headline: string;
    narrative: string;
    cards: AiInsightCard[];
    actions?: AiInsightAction[];
  };
  raw?: PageInsights;
};

export type AiInsightsResponse = {
  stale: boolean;
  generated_at: string;
  model?: string | null;
  payload: AiInsightsPayload;
  error?: string;
};

export async function getAiInsights(
  period: string,
  force: boolean = false,
  opts: { revalidate?: number } = {},
): Promise<AiInsightsResponse | null> {
  const url = `/api/personel/ai-insights?period=${encodeURIComponent(period)}${force ? '&force=true' : ''}`;
  try {
    return await apiGet<AiInsightsResponse>(url, opts);
  } catch {
    // AI servis erişilemiyorsa null dön → frontend deterministik fallback'i kullansın
    return null;
  }
}

// Personel listesi için aylık aggregate stats (paket / saat / gün)
export type PersonnelStats = {
  personnel_id: number;
  total_packages: number;
  total_hours: number;
  working_days: number;
};

export async function getPersonnelStats(
  period: string = '2026-03',
): Promise<PersonnelStats[]> {
  return apiGet<PersonnelStats[]>(`/api/personel/stats?period=${period}`);
}

// ─────────────────────────────────────────────────────────────
// Kesintiler
// ─────────────────────────────────────────────────────────────

export type Deduction = {
  id: number;
  personnel_id: number | null;
  deduction_type: string;
  amount: number;
  deduction_date: string | null;
  notes: string | null;
  equipment_issue_id: number | null;
  personnel_name: string | null;
  person_code: string | null;
  role: string | null;
  equipment_name: string | null;
  equipment_total_installments: number | null;
};

export async function listDeductions(opts?: {
  period?: string;
  personnel_id?: number;
  deduction_type?: string;
}): Promise<Deduction[]> {
  const p = new URLSearchParams();
  if (opts?.period) p.set('period', opts.period);
  if (opts?.personnel_id) p.set('personnel_id', String(opts.personnel_id));
  if (opts?.deduction_type) p.set('deduction_type', opts.deduction_type);
  const qs = p.toString();
  return apiGet<Deduction[]>(`/api/deductions${qs ? '?' + qs : ''}`);
}

export async function getDeductionTypes(): Promise<string[]> {
  return apiGet<string[]>('/api/deductions/types');
}

export type DeductionByType = {
  deduction_type: string;
  count: number;
  total: number;
};

export async function getDeductionSummaryByType(
  period: string = '2026-03',
): Promise<DeductionByType[]> {
  return apiGet<DeductionByType[]>(
    `/api/deductions/summary/by-type?period=${period}`,
  );
}

export async function createDeduction(payload: {
  personnel_id: number;
  deduction_type: string;
  amount: number;
  deduction_date?: string;
  notes?: string;
}): Promise<Deduction> {
  return apiMutate<Deduction>(`/api/deductions`, payload, 'POST');
}

// ─────────────────────────────────────────────────────────────
// Ekipman & Zimmet
// ─────────────────────────────────────────────────────────────

export type EquipmentCatalogItem = {
  name: string;
  category: string;
  default_price: number;
};

export type EquipmentAssignment = {
  id: number;
  personnel_id: number | null;
  item_name: string;
  quantity: number;
  unit_cost: number;
  unit_sale_price: number;
  vat_rate: number;
  sale_type: string | null;
  installment_count: number;
  issue_date: string | null;
  notes: string | null;
  personnel_name: string | null;
  person_code: string | null;
  role: string | null;
  total_amount: number;
  per_installment: number;
  taksit_kesilen: number;
};

export async function getEquipmentCatalog(): Promise<EquipmentCatalogItem[]> {
  return apiGet<EquipmentCatalogItem[]>('/api/equipment/catalog');
}

export async function listEquipmentAssignments(opts?: {
  personnel_id?: number;
  period?: string;
}): Promise<EquipmentAssignment[]> {
  const p = new URLSearchParams();
  if (opts?.personnel_id) p.set('personnel_id', String(opts.personnel_id));
  if (opts?.period) p.set('period', opts.period);
  const qs = p.toString();
  return apiGet<EquipmentAssignment[]>(
    `/api/equipment/assignments${qs ? '?' + qs : ''}`,
  );
}

export async function createEquipmentAssignment(payload: {
  personnel_id: number;
  item_name: string;
  quantity?: number;
  unit_sale_price: number;
  unit_cost?: number;
  vat_rate?: number;
  installment_count?: number;
  issue_date?: string;
  notes?: string;
}): Promise<EquipmentAssignment> {
  return apiMutate<EquipmentAssignment>(
    `/api/equipment/assignments`,
    payload,
    'POST',
  );
}

export type DashboardSummary = {
  period: string;
  active_personnel: number;
  active_restaurants: number;
  kurye_count: number;
  joker_count: number;
  total_deductions: number;
  puantaj_entries: number;
  total_hours: number;
  total_packages: number;
};

export async function getDashboardSummary(period: string = '2026-03'): Promise<DashboardSummary> {
  return apiGet<DashboardSummary>(`/api/dashboard/summary?period=${period}`);
}

export type Restaurant = {
  id: number;
  brand: string | null;
  branch: string | null;
  billing_group: string | null;
  pricing_model: string | null;
  hourly_rate: number | null;
  package_rate: number | null;
  package_threshold: number | null;
  package_rate_low: number | null;
  package_rate_high: number | null;
  fixed_monthly_fee: number | null;
  vat_rate: number | null;
  target_headcount: number | null;
  standard_daily_hours?: number | null;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email?: string | null;
  address?: string | null;
  company_title?: string | null;
  tax_number?: string | null;
  tax_office?: string | null;
  start_date: string | null;
  end_date?: string | null;
  active: number | null;
  notes?: string | null;
};

export type RestaurantUpdate = Partial<Omit<Restaurant, 'id'>>;

export async function listRestaurants(): Promise<Restaurant[]> {
  return apiGet<Restaurant[]>('/api/restaurants');
}

export async function getRestaurant(id: number): Promise<Restaurant> {
  return apiGet<Restaurant>(`/api/restaurants/${id}`);
}

export async function updateRestaurant(
  id: number,
  fields: RestaurantUpdate
): Promise<Restaurant> {
  return apiMutate<Restaurant>(`/api/restaurants/${id}`, fields, 'PATCH');
}

export type RestaurantCreate = Omit<RestaurantUpdate, 'id'> & { brand: string };

export async function createRestaurant(
  fields: RestaurantCreate
): Promise<Restaurant> {
  return apiMutate<Restaurant>(`/api/restaurants`, fields, 'POST');
}

// ─────────────────────────────────────────────────────────────
// Restoran aylık fatura kırılımı (hakediş motoru sonucu)
// ─────────────────────────────────────────────────────────────

export type CourierBillingLine = {
  label: string;
  qty: number;
  rate: number;
  amount: number;
};

export type CourierBilling = {
  personnel_id: number | null;
  full_name: string | null;
  person_code: string | null;
  role: string | null;
  is_support: boolean;
  monthly_fixed_cost: number;
  entries: number;
  working_days: number;
  absences: number;
  total_hours: number;
  total_packages: number;
  billing_excl_vat: number;
  billing_incl_vat: number;
  billing_breakdown: CourierBillingLine[];
};

export type RestaurantMonthly = {
  restaurant: Restaurant;
  period: string;
  couriers: CourierBilling[];
  unassigned_entries?: number;
  unassigned_absences?: number;
  totals: {
    courier_count: number;
    support_count: number;
    total_entries: number;
    total_working_days: number;
    total_absences: number;
    total_hours: number;
    total_packages: number;
    total_billing_excl_vat: number;
    total_billing_incl_vat: number;
    vat_amount: number;
    vat_rate: number;
  };
};

export async function getRestaurantMonthly(
  id: number,
  period: string = '2026-03'
): Promise<RestaurantMonthly> {
  return apiGet<RestaurantMonthly>(
    `/api/restaurants/${id}/monthly?period=${period}`
  );
}

// ─── Tarife değişim geçmişi ────────────────────────────────────────
export type PricingHistoryEntry = {
  id: number;
  effective_from: string;        // 'YYYY-MM-DD'
  pricing_model: string | null;
  hourly_rate: number | null;
  package_rate: number | null;
  package_threshold: number | null;
  package_rate_low: number | null;
  package_rate_high: number | null;
  fixed_monthly_fee: number | null;
  vat_rate: number | null;
  created_at: string;            // ISO timestamp
  note: string | null;
};

export type PricingHistoryResponse = {
  restaurant_id: number;
  history: PricingHistoryEntry[];
  last_change: PricingHistoryEntry | null;
};

export async function getPricingHistory(restaurantId: number): Promise<PricingHistoryResponse> {
  return apiGet<PricingHistoryResponse>(
    `/api/restaurants/${restaurantId}/pricing-history`
  );
}

// ─── Personel Hareketi (çıkış / giriş / destek) ───────────────────
export type PersonnelMovementExit = {
  id: number;
  full_name: string | null;
  person_code: string | null;
  role: string | null;
  exit_date: string;
};
export type PersonnelMovementJoin = {
  id: number;
  full_name: string | null;
  person_code: string | null;
  role: string | null;
  start_date: string;
};
export type PersonnelMovementSupport = {
  id: number;
  full_name: string | null;
  person_code: string | null;
  role: string | null;
  source: 'joker' | 'komşu_şube' | 'yönetim' | 'diğer';
  home_assignment: string;
  working_days: number;
  total_hours: number;
  total_packages: number;
};
export type PersonnelMovementsResponse = {
  restaurant_id: number;
  period: string;
  exits: PersonnelMovementExit[];
  joins: PersonnelMovementJoin[];
  support_workers: PersonnelMovementSupport[];
  active_courier_count: number;
  operation_days: number;
  month_days: number;
  uninterrupted: boolean;
  summary: string;
};

export async function getPersonnelMovements(
  restaurantId: number,
  period: string,
): Promise<PersonnelMovementsResponse> {
  return apiGet<PersonnelMovementsResponse>(
    `/api/restaurants/${restaurantId}/personnel-movements?period=${period}`,
  );
}

// ─── Veri Sağlığı (sistem geneli sanity checks) ───────────────────
export type DataHealthCheck = {
  key: string;
  label: string;
  status: 'green' | 'yellow' | 'red';
  count: number;
  total: number;
  samples: { id: number; name: string | null; detail: string }[];
  suggestion: string;
};

export type DataHealthResponse = {
  period: string;
  checks: DataHealthCheck[];
  summary: {
    green: number;
    yellow: number;
    red: number;
    overall_status: 'green' | 'yellow' | 'red';
    total_checks: number;
  };
};

export async function getDataHealth(period: string): Promise<DataHealthResponse> {
  return apiGet<DataHealthResponse>(`/api/data-health?period=${period}`, {
    revalidate: 0,
  });
}

export type SidebarCounts = {
  personel: number;
  restoranlar: number;
  puantaj_onay: number;
  hakedis_onay: number;
  avans: number;
  talepler: number;
  profil_onay: number;
};

export async function getSidebarCounts(): Promise<SidebarCounts> {
  return apiGet<SidebarCounts>('/api/sidebar/counts');
}

// ─────────────────────────────────────────────────────────────
// Talepler — Avans / Motor Değişikliği / Muhasebe Değişimi
// ─────────────────────────────────────────────────────────────

export type CourierRequest = {
  id: number;
  personnel_id: number;
  personnel_name: string | null;
  person_code: string | null;
  personnel_role: string | null;
  rest_brand: string | null;
  rest_branch: string | null;
  request_type: 'Avans' | 'Motor Değişikliği' | 'Muhasebe Değişimi' | string;
  amount: number;
  reason: string | null;
  status: 'Beklemede' | 'Onaylandı' | 'Reddedildi' | string;
  decision_notes: string | null;
  requested_at: string | null;
  decided_at: string | null;
  decided_by: string | null;
  // Motor Değişikliği detayları
  vehicle_from?: string | null;
  vehicle_to?: string | null;
  vehicle_reason?: string | null;
  plate?: string | null;
  // Muhasebe Değişimi detayları
  accounting_from?: string | null;
  accounting_to?: string | null;
};

export type CourierRequestCounts = {
  Beklemede: number;
  Onaylandı: number;
  Reddedildi: number;
  total: number;
};

export type CourierRequestCreate = {
  personnel_id: number;
  request_type: string;
  amount?: number;
  reason?: string | null;
  // Motor Değişikliği için
  vehicle_from?: string | null;
  vehicle_to?: string | null;
  vehicle_reason?: string | null;
  plate?: string | null;
  // Muhasebe Değişimi için
  accounting_from?: string | null;
  accounting_to?: string | null;
};

export type CourierRequestDecide = {
  status: 'Onaylandı' | 'Reddedildi';
  decided_by?: string | null;
  decision_notes?: string | null;
};

export async function listCourierRequests(filters?: {
  status?: string;
  request_type?: string;
  personnel_id?: number;
}): Promise<CourierRequest[]> {
  const qs = new URLSearchParams();
  if (filters?.status) qs.set('status', filters.status);
  if (filters?.request_type) qs.set('request_type', filters.request_type);
  if (filters?.personnel_id != null) qs.set('personnel_id', String(filters.personnel_id));
  const q = qs.toString();
  return apiGet<CourierRequest[]>(`/api/requests${q ? `?${q}` : ''}`);
}

export async function getCourierRequestCounts(): Promise<CourierRequestCounts> {
  return apiGet<CourierRequestCounts>('/api/requests/counts');
}

export async function getCourierRequestTypes(): Promise<string[]> {
  return apiGet<string[]>('/api/requests/types');
}

export async function createCourierRequest(payload: CourierRequestCreate): Promise<CourierRequest> {
  return apiMutate<CourierRequest>('/api/requests', payload, 'POST');
}

export async function decideCourierRequest(
  id: number,
  payload: CourierRequestDecide,
): Promise<CourierRequest> {
  return apiMutate<CourierRequest>(`/api/requests/${id}/decide`, payload, 'PATCH');
}

export async function deleteCourierRequest(id: number): Promise<{ ok: boolean }> {
  return apiMutate<{ ok: boolean }>(`/api/requests/${id}`, {}, 'DELETE');
}

// ─────────────────────────────────────────────────────────────
// Profil Değişiklik Talepleri
// ─────────────────────────────────────────────────────────────

export type ProfileChangeRequest = {
  id: number;
  personnel_id: number;
  personnel_name: string | null;
  person_code: string | null;
  field: string;
  old_value: string | null;
  new_value: string | null;
  status: 'Beklemede' | 'Onaylandı' | 'Reddedildi' | 'İptal Edildi' | string;
  requested_at: string | null;
  decided_at: string | null;
  decided_by: string | null;
  decision_notes: string | null;
};

export async function listProfileChanges(status?: string): Promise<ProfileChangeRequest[]> {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  return apiGet<ProfileChangeRequest[]>(`/api/profile-changes${params.toString() ? '?' + params.toString() : ''}`);
}

export async function getProfileChangeCounts(): Promise<{ pending: number }> {
  return apiGet<{ pending: number }>('/api/profile-changes/counts');
}

export async function decideProfileChange(
  id: number,
  status: 'Onaylandı' | 'Reddedildi',
  decision_notes?: string,
): Promise<ProfileChangeRequest> {
  return apiMutate<ProfileChangeRequest>(
    `/api/profile-changes/${id}/decide`,
    { status, decided_by: undefined, decision_notes },
    'PATCH'
  );
}

export async function deleteProfileChange(id: number): Promise<{ ok: boolean }> {
  return apiMutate<{ ok: boolean }>(`/api/profile-changes/${id}`, {}, 'DELETE');
}

// ─────────────────────────────────────────────────────────────
// Puantaj
// ─────────────────────────────────────────────────────────────

export type PuantajEntry = {
  id: number;
  entry_date: string;
  restaurant_id: number | null;
  restaurant_brand: string | null;
  restaurant_branch: string | null;
  pricing_model: string | null;
  actual_personnel_id: number | null;
  planned_personnel_id: number | null;
  personnel_name: string | null;
  person_code: string | null;
  personnel_role: string | null;
  worked_hours: number | null;
  package_count: number | null;
  coverage_type: string | null;
  absence_reason: string | null;
  status: string | null;
  notes: string | null;
  monthly_invoice_amount: number | null;
};

export type RestaurantPuantajSummary = {
  restaurant_id: number | null;
  brand: string | null;
  branch: string | null;
  pricing_model: string | null;
  target_headcount: number | null;
  entries: number;
  unique_personnel: number;
  total_hours: number;
  total_packages: number;
  absences: number;
};

export async function listPuantajPeriods(): Promise<string[]> {
  return apiGet<string[]>('/api/puantaj/periods');
}

export async function listPuantajEntries(
  period: string,
  opts?: { restaurantId?: number; personnelId?: number; limit?: number }
): Promise<PuantajEntry[]> {
  const params = new URLSearchParams({ period });
  if (opts?.restaurantId) params.set('restaurant_id', String(opts.restaurantId));
  if (opts?.personnelId) params.set('personnel_id', String(opts.personnelId));
  if (opts?.limit) params.set('limit', String(opts.limit));
  return apiGet<PuantajEntry[]>(`/api/puantaj/entries?${params.toString()}`);
}

export async function getPuantajSummaryByRestaurant(
  period: string
): Promise<RestaurantPuantajSummary[]> {
  return apiGet<RestaurantPuantajSummary[]>(
    `/api/puantaj/summary-by-restaurant?period=${period}`
  );
}

// ─────────────────────────────────────────────────────────────
// Puantaj matrix — kişi × 31 gün grid
// ─────────────────────────────────────────────────────────────

export type MatrixCell = {
  type: 'normal' | 'izin' | 'gelmedi' | 'raporlu' | 'ihbarsiz' | 'empty';
  hours: number;
  packages: number;
  is_support: boolean;
  restaurant_id: number | null;
};

export type MatrixRow = {
  id: number;
  row_key: string;
  full_name: string | null;
  person_code: string | null;
  role: string | null;
  rest_brand: string | null;
  rest_branch: string | null;
  rest_id: number | null;
  is_support_row: boolean;
  cells: MatrixCell[];
  total_hours: number;
  total_packages: number;
  worked_days: number;
  joker_days: number;
};

export type PuantajMatrix = {
  period: string;
  rows: MatrixRow[];
  summary: {
    total_hours: number;
    total_packages: number;
    worked_days: number;
    joker_days: number;
    cell_counts: Record<string, number>;
    personnel_count: number;
    row_count?: number;
  };
};

export async function getPuantajMatrix(
  period: string = '2026-03',
): Promise<PuantajMatrix> {
  return apiGet<PuantajMatrix>(`/api/puantaj/matrix?period=${period}`);
}

export type PuantajCellUpdate = {
  personnel_id: number;
  entry_date: string;
  cell_type: 'normal' | 'izin' | 'gelmedi' | 'raporlu' | 'ihbarsiz' | 'empty';
  worked_hours?: number;
  package_count?: number;
  coverage_type?: string;
  restaurant_id?: number;
  notes?: string;
};

export async function updatePuantajCell(
  payload: PuantajCellUpdate,
): Promise<{ action: string; id: number | null }> {
  return apiMutate(`/api/puantaj/cell`, payload, 'PATCH');
}

export type PuantajBulkFill = {
  period: string;
  pattern: 'weekdays' | 'all' | 'weekend_off' | 'copy_previous';
  hours?: number;
  package_count?: number;
  personnel_ids?: number[];
  restaurant_id?: number;
};

export async function bulkFillPuantaj(
  payload: PuantajBulkFill,
): Promise<{ inserted: number; skipped: number; pattern: string }> {
  return apiMutate(`/api/puantaj/bulk-fill`, payload, 'POST');
}

// ─────────────────────────────────────────────────────────────
// Puantaj Onayları (operasyon → admin onay akışı)
// ─────────────────────────────────────────────────────────────

export type PuantajApprovalNotification = {
  sent?: number;
  skipped_already_sent?: number;
  no_phone?: number;
  not_in_allowlist?: number;
  failed?: number;
  total?: number;
  error?: string;
};

export type PuantajApproval = {
  id: number;
  restaurant_id: number;
  rest_brand: string | null;
  rest_branch: string | null;
  pricing_model: string | null;
  period: string;
  status: 'pending' | 'approved' | 'rejected';
  submitted_by: string | null;
  submitted_at: string | null;
  decided_by: string | null;
  decided_at: string | null;
  decision_notes: string | null;
  entry_count: number;
  total_hours: number;
  total_packages: number;
  // 'approved' decide sonrası backend ekler — SMS bildirim sonucu özeti
  notification?: PuantajApprovalNotification;
};

export type PuantajApprovalSummary = {
  period: string;
  pending: number;
  approved: number;
  rejected: number;
  total_restaurants_active: number;
};

export async function listPuantajApprovals(
  status?: 'pending' | 'approved' | 'rejected',
  period?: string,
): Promise<PuantajApproval[]> {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (period) params.set('period', period);
  const qs = params.toString();
  return apiGet<PuantajApproval[]>(
    `/api/puantaj/approvals${qs ? `?${qs}` : ''}`,
  );
}

export async function getPuantajApprovalsSummary(
  period: string,
): Promise<PuantajApprovalSummary> {
  return apiGet<PuantajApprovalSummary>(
    `/api/puantaj/approvals/summary?period=${period}`,
  );
}

export async function getPuantajApprovalForRestaurant(
  restaurant_id: number,
  period: string,
): Promise<PuantajApproval | Record<string, never>> {
  return apiGet<PuantajApproval | Record<string, never>>(
    `/api/puantaj/approvals/restaurant/${restaurant_id}?period=${period}`,
  );
}

export async function submitPuantajApproval(
  restaurant_id: number,
  period: string,
  submitted_by?: string,
): Promise<PuantajApproval> {
  return apiMutate(
    `/api/puantaj/approvals/submit`,
    { restaurant_id, period, submitted_by },
    'POST',
  );
}

export async function decidePuantajApproval(
  approval_id: number,
  status: 'approved' | 'rejected',
  decided_by?: string,
  decision_notes?: string,
): Promise<PuantajApproval> {
  return apiMutate(
    `/api/puantaj/approvals/${approval_id}/decide`,
    { status, decided_by, decision_notes },
    'PATCH',
  );
}

// ─────────────────────────────────────────────────────────────
// Bordro
// ─────────────────────────────────────────────────────────────

export type PayrollKesintiLine = {
  amount: number;
  notes?: string | null;
  equipment?: string;
  installments?: number;
};

export type PayrollKesintiGroup = {
  type: string;
  count: number;
  total: number;
  lines: PayrollKesintiLine[];
};

export type PayrollDestekLine = {
  restaurant_id: number;
  rest_brand?: string | null;
  rest_branch?: string | null;
  pricing_model?: string | null;
  days: number;
  hours: number;
  packages: number;
  amount: number;
};

export type TevkifatBreakdown = {
  invoice_base_amount: number;
  vat_amount: number;
  tevkifat_amount: number;
  fatura_total?: number;
};

export type PayrollRow = {
  id: number;
  full_name: string | null;
  person_code: string | null;
  role: string | null;
  rest_brand: string | null;
  rest_branch: string | null;
  pricing_model: string | null;
  is_fixed_salary: boolean;
  ana_hours: number;
  ana_packages: number;
  ana_days: number;
  destek_days: number;
  destek_lines: PayrollDestekLine[];
  ana_brut: number;
  ekstra_mesai_brut: number;
  ekstra_mesai_days: number;
  destek_brut: number;
  kaptan_bonus: number;
  toplam_brut: number;
  motor_taksit: number;
  motor_kira: number;
  muhasebe: number;
  sirket_acilis: number;
  kesinti_groups: PayrollKesintiGroup[];
  kesinti_total: number;
  sabit_total: number;
  tevkifat: number;
  tevkifat_breakdown: TevkifatBreakdown;
  is_ck_muhasebe: boolean;
  net: number;
};

export type PayrollResult = {
  period: string;
  rows: PayrollRow[];
  summary: {
    courier_count: number;
    total_brut: number;
    total_kesinti: number;
    total_tevkifat: number;
    total_net: number;
  };
};

export async function getPayroll(
  period: string = '2026-03',
): Promise<PayrollResult> {
  return apiGet<PayrollResult>(`/api/payroll?period=${period}`);
}

export async function getPersonnelPayroll(
  id: number,
  period: string = '2026-03',
): Promise<PayrollRow> {
  return apiGet<PayrollRow>(`/api/payroll/${id}?period=${period}`);
}

// ─────────────────────────────────────────────────────────────
// Restoran Raporları
// ─────────────────────────────────────────────────────────────

export type TurnoverItem = {
  restaurant_id: number;
  brand: string;
  branch: string;
  started_count: number;
  exited_count: number;
  active_count: number;
  turnover_pct: number;
};

export type CourierEfficiencyItem = {
  personnel_id: number;
  full_name: string;
  person_code: string;
  rest_brand: string;
  rest_branch: string;
  packages: number;
  hours: number;
  packages_per_hour: number;
};

export type CostPerPackageRestaurant = {
  restaurant_id: number;
  brand: string;
  branch: string;
  billing_excl_vat: number;
  packages: number;
  cost_per_package: number;
};

export type CostPerPackageCourier = {
  personnel_id: number;
  full_name: string;
  rest_brand: string;
  billing: number;
  packages: number;
  cost_per_package: number;
};

export type PackageGrowthItem = {
  restaurant_id: number;
  brand: string;
  branch: string;
  current_packages: number;
  previous_packages: number;
  growth_pct: number;
  delta: number;
};

export type RestaurantReports = {
  period: string;
  previous_period: string;
  turnover: TurnoverItem[];
  courier_efficiency: CourierEfficiencyItem[];
  cost_per_package: {
    overall: number;
    by_restaurant: CostPerPackageRestaurant[];
    by_courier: CostPerPackageCourier[];
  };
  package_growth: PackageGrowthItem[];
};

export async function getRestaurantReports(
  period: string = '2026-03',
): Promise<RestaurantReports> {
  return apiGet<RestaurantReports>(`/api/restaurant-reports?period=${period}`);
}

// Restoran performans raporu PDF (preview/download için backend URL).
// Tarayıcıda <iframe src={url}> ile render edilir, ya da <a download>.
export function getRestaurantReportPdfUrl(
  restaurantId: number,
  period: string,
  skipAi: boolean = false,
): string {
  const qs = `period=${encodeURIComponent(period)}${skipAi ? '&skip_ai=true' : ''}`;
  // SSR'da NEXT_PUBLIC_API_URL kullan; client'ta rewrite proxy çalışır.
  // iframe src için relative path en güvenlisi.
  return `/api/restaurant-reports/${restaurantId}/pdf?${qs}`;
}

// Restoran raporları için AI içgörü — scope='restoran' ile cache'lenir.
// Cevap şeması AiInsightsResponse ile aynı, kart key'leri farklı:
// turnover_riski / verim_lideri / maliyet_baskisi / buyume_trendi.
export async function getRestaurantsAiInsights(
  period: string,
  force: boolean = false,
  opts: { revalidate?: number } = {},
): Promise<AiInsightsResponse | null> {
  const url = `/api/restaurant-reports/ai-insights?period=${encodeURIComponent(period)}${
    force ? '&force=true' : ''
  }`;
  try {
    return await apiGet<AiInsightsResponse>(url, opts);
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────────────────────
// Hakediş Onayları (imzalanan bordrolar + ödeme takibi)
// ─────────────────────────────────────────────────────────────

export type PayrollSignature = {
  id: number;
  personnel_id: number;
  personnel_name: string | null;
  person_code: string | null;
  role: string | null;
  iban: string | null;
  period: string;
  signed_at: string | null;
  ip_address: string | null;
  paid_at: string | null;
  paid_by: string | null;
  paid_amount: number | null;
};

export async function listPayrollSignatures(
  period: string,
): Promise<PayrollSignature[]> {
  return apiGet<PayrollSignature[]>(
    `/api/payroll/signatures?period=${encodeURIComponent(period)}`,
  );
}

export async function markBordroPaid(
  personnel_id: number,
  period: string,
  paid_amount?: number,
  paid_by?: string,
): Promise<PayrollSignature> {
  const params = new URLSearchParams({ period });
  if (paid_amount != null) params.set('paid_amount', String(paid_amount));
  if (paid_by) params.set('paid_by', paid_by);
  return apiMutate(
    `/api/payroll/signatures/${personnel_id}/mark-paid?${params.toString()}`,
    {},
    'PATCH',
  );
}

export async function unmarkBordroPaid(
  personnel_id: number,
  period: string,
): Promise<{ unmarked: boolean; personnel_id: number; period: string }> {
  return apiMutate(
    `/api/payroll/signatures/${personnel_id}/unmark-paid?period=${encodeURIComponent(period)}`,
    {},
    'PATCH',
  );
}

// ─────────────────────────────────────────────────────────────
// Box Geri Alım — /api/box-returns
// ─────────────────────────────────────────────────────────────
export type BoxReturn = {
  id: number;
  personnel_id: number;
  personnel_name: string;
  person_code: string;
  rest_brand?: string;
  rest_branch?: string;
  item_name: string;
  return_date: string;
  quantity: number;
  condition_status: string;
  payout_amount: number;
  waived: boolean;
  notes: string;
  created_at?: string;
  updated_at?: string;
};

export type BoxReturnsSummary = {
  records_count: number;
  total_quantity: number;
  total_payout: number;
  unique_personnel: number;
  waived_count: number;
};

export type BoxReturnsListResponse = {
  items: BoxReturn[];
  summary: BoxReturnsSummary;
  condition_options: string[];
  item_options: string[];
};

export async function getBoxReturns(params: {
  personnel_id?: number;
  date_from?: string;
  date_to?: string;
  condition?: string;
  search?: string;
} = {}): Promise<BoxReturnsListResponse> {
  const qs = new URLSearchParams();
  if (params.personnel_id) qs.set('personnel_id', String(params.personnel_id));
  if (params.date_from) qs.set('date_from', params.date_from);
  if (params.date_to) qs.set('date_to', params.date_to);
  if (params.condition) qs.set('condition', params.condition);
  if (params.search) qs.set('search', params.search);
  const q = qs.toString();
  return apiGet<BoxReturnsListResponse>(`/api/box-returns${q ? `?${q}` : ''}`);
}

export async function createBoxReturn(payload: Partial<BoxReturn>): Promise<BoxReturn> {
  return apiMutate('/api/box-returns', payload, 'POST');
}

export async function updateBoxReturn(id: number, payload: Partial<BoxReturn>): Promise<BoxReturn> {
  return apiMutate(`/api/box-returns/${id}`, payload, 'PATCH');
}

export async function deleteBoxReturn(id: number): Promise<void> {
  await apiMutate(`/api/box-returns/${id}`, {}, 'DELETE');
}

// ─────────────────────────────────────────────────────────────
// Tahsilat — /api/collections
// ─────────────────────────────────────────────────────────────
export type CollectionItem = {
  id: number | null;
  restaurant_id: number;
  brand: string;
  branch: string;
  collection_month: string | null;
  status: string;
  invoice_amount: number;
  collected_amount: number;
  remaining_amount: number;
  due_date: string | null;
  last_contact_date: string | null;
  responsible_name: string;
  note: string;
  is_overdue: boolean;
  paid_at: string | null;
  invoice_no?: string | null;
  invoice_amount_excl_vat?: number; // KDV hariç tutar (manuel veya auto)
  vat_rate?: number;                // restoranın KDV oranı (örn. 20)
  is_auto_invoice?: boolean;        // puantajdan otomatik hesaplandı mı
  auto_invoice_amount?: number;     // puantaj bazlı tahmini tutar (KDV dahil)
  auto_invoice_excl_vat?: number;   // puantaj bazlı tahmini (KDV hariç)
  auto_vat_rate?: number;
  auto_basis?:
    | 'fixed'              // sadece sabit aylık ücret (SC Petshop)
    | 'hourly'             // saatlik (Doğu Otomotiv)
    | 'package'            // sadece paket × tarife
    | 'hourly+package'     // saat + sabit paket (Quick China: 279 saat + 32 paket)
    | 'hourly+threshold'   // saat + eşikli paket (Fasuli: 273 saat + 390↑/47, ↓/34)
    | 'threshold'          // sadece eşikli paket
    | 'mixed'              // (legacy)
    | 'auto';
  auto_hours?: number;
  auto_packages?: number;
};

export type CollectionsSummary = {
  period: string;
  total_invoice: number;
  total_collected: number;
  total_open: number;
  overdue_amount: number;
  overdue_count: number;
  collected_count: number;
  pending_count: number;
  restaurant_count: number;
  today: string;
  // O ay için daily_entries özet (period sağlık göstergesi)
  entries_total_hours?: number;
  entries_total_packages?: number;
  entries_restaurants?: number;
};

export type CollectionsListResponse = {
  period: string;
  items: CollectionItem[];
  summary: CollectionsSummary;
  status_options: string[];
};

export async function getCollections(params: {
  period: string;
  status?: string;
  search?: string;
}): Promise<CollectionsListResponse> {
  const qs = new URLSearchParams({ period: params.period });
  if (params.status) qs.set('status', params.status);
  if (params.search) qs.set('search', params.search);
  return apiGet<CollectionsListResponse>(`/api/collections?${qs.toString()}`);
}

export type CollectionUpsertPayload = {
  restaurant_id: number;
  collection_month: string;
  invoice_amount?: number;
  collected_amount?: number;
  status?: string;
  due_date?: string | null;
  last_contact_date?: string | null;
  responsible_name?: string;
  note?: string;
  notes?: string;
  paid_at?: string | null;
  payment_date?: string | null;
  invoice_no?: string | null;
};

export async function upsertCollection(payload: CollectionUpsertPayload): Promise<CollectionItem> {
  return apiMutate('/api/collections', payload, 'POST');
}

export async function deleteCollection(id: number): Promise<void> {
  await apiMutate(`/api/collections/${id}`, {}, 'DELETE');
}
