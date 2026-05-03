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
};

export async function listPersonnel(status?: 'Aktif' | 'Pasif'): Promise<Personnel[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiGet<Personnel[]>(`/api/personel${q}`);
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
  start_date: string | null;
  active: number | null;
};

export async function listRestaurants(): Promise<Restaurant[]> {
  return apiGet<Restaurant[]>('/api/restaurants');
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
