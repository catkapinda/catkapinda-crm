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

export async function apiGet<T>(path: string, opts?: { revalidate?: number }): Promise<T> {
  const url = `${SERVER_API}${path.startsWith('/') ? path : `/${path}`}`;
  const res = await fetch(url, {
    next: { revalidate: opts?.revalidate ?? 30 },
    headers: { 'Content-Type': 'application/json' },
  });
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
  vehicle_type?: string | null;
  tc_no?: string | null;
  iban?: string | null;
  tax_number?: string | null;
  tax_office?: string | null;
  accounting_type?: string | null;
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

export async function getNextPersonCode(role: string): Promise<{ person_code: string }> {
  return apiGet<{ person_code: string }>(
    `/api/personel/next-code?role=${encodeURIComponent(role)}`,
    { revalidate: 0 },
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

export type SidebarCounts = {
  personel: number;
  restoranlar: number;
  puantaj_onay: number;
  hakedis_onay: number;
  avans: number;
  talepler: number;
};

export async function getSidebarCounts(): Promise<SidebarCounts> {
  return apiGet<SidebarCounts>('/api/sidebar/counts');
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
