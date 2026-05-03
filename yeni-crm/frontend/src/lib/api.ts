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
};

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiGet<DashboardSummary>('/api/dashboard/summary');
}
