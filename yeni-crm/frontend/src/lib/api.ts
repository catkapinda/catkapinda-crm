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
  active: boolean | null;
};

export async function listRestaurants(): Promise<Restaurant[]> {
  return apiGet<Restaurant[]>('/api/restaurants');
}
