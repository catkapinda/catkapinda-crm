/**
 * Kurye portal API helper'ları — istemci tarafında kullanım için.
 *
 * Tüm çağrılar tarayıcıdan yapılır ve otomatik olarak
 * Authorization header'ına token'ı ekler.
 */

const API_BASE = '/api/courier';

function getAuthHeader(): { Authorization: string } | {} {
  if (typeof window === 'undefined') {
    return {};
  }
  const token = localStorage.getItem('courier_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function courierLogin(
  person_code: string,
  last4_tc: string
): Promise<{
  token: string;
  expires_at: string;
  courier: {
    id: number;
    person_code: string;
    full_name: string;
    role: string;
  };
}> {
  const res = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ person_code, last4_tc }),
    credentials: 'include',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Giriş başarısız');
  }

  return res.json();
}

export async function courierLogout(): Promise<{ ok: boolean }> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
  };

  const res = await fetch(`${API_BASE}/logout`, {
    method: 'POST',
    headers,
    credentials: 'include',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Çıkış başarısız');
  }

  return res.json();
}

export type CourierMe = {
  id: number;
  person_code: string;
  full_name: string;
  role: string;
  status: string;
  phone: string | null;
  current_plate: string | null;
  iban: string | null;
  address: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  vehicle_type: string | null;
  accounting_type: string | null;
  assigned_restaurant_id: number | null;
};

export async function getMyInfo(): Promise<CourierMe> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
  };

  const res = await fetch(`${API_BASE}/me`, { headers });
  if (!res.ok) throw new Error('Bilgiler yüklenemedi');
  return res.json();
}

export async function getMyBordro(period: string): Promise<{
  personnel_id: number;
  period: string;
  total_brut: number;
  total_deductions: number;
  total_net: number;
  [key: string]: unknown;
}> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
  };

  const res = await fetch(`${API_BASE}/my-bordro?period=${period}`, { headers });
  if (!res.ok) throw new Error('Bordro yüklenemedi');
  return res.json();
}

export async function downloadBordroToPdf(period: string): Promise<Blob> {
  const headers = { ...getAuthHeader() };
  const res = await fetch(`${API_BASE}/my-bordro/pdf?period=${period}`, { headers });
  if (!res.ok) throw new Error('PDF indirilemedi');
  return res.blob();
}

export async function listMyRequests(): Promise<
  Array<{
    id: number;
    request_type: string;
    amount: number;
    reason: string | null;
    status: string;
    requested_at: string;
    decided_at: string | null;
    decision_notes: string | null;
  }>
> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
  };

  const res = await fetch(`${API_BASE}/my-requests`, { headers });
  if (!res.ok) throw new Error('Talepler yüklenemedi');
  return res.json();
}

export async function createAvansRequest(
  amount: number,
  reason?: string
): Promise<{
  id: number;
  personnel_id: number;
  request_type: string;
  amount: number;
  status: string;
  requested_at: string;
}> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
  };

  const res = await fetch(`${API_BASE}/my-requests`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ amount, reason: reason || null }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Talep oluşturulamadı');
  }

  return res.json();
}

export async function getMySummary(period: string): Promise<{
  period: string;
  bordro: {
    total_brut: number;
    total_deductions: number;
    total_net: number;
  };
  request_stats: {
    pending_count: number;
    approved_count: number;
    rejected_count: number;
  };
  recent_requests: Array<{
    id: number;
    request_type: string;
    amount: number;
    status: string;
    requested_at: string;
  }>;
}> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
  };

  const res = await fetch(`${API_BASE}/my-summary?period=${period}`, { headers });
  if (!res.ok) throw new Error('Özet yüklenemedi');
  return res.json();
}

export type ProfileChangeRequest = {
  id: number;
  field: string;
  old_value: string | null;
  new_value: string | null;
  status: string;
  requested_at: string;
  decided_at: string | null;
  decision_notes: string | null;
};

export async function listMyProfileChanges(): Promise<ProfileChangeRequest[]> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
  };

  const res = await fetch(`${API_BASE}/my-profile-changes`, { headers });
  if (!res.ok) throw new Error('Profil talepleri yüklenemedi');
  return res.json();
}

export async function submitProfileChange(
  field: string,
  new_value: string | null
): Promise<{
  id: number;
  personnel_id: number;
  field: string;
  old_value: string | null;
  new_value: string | null;
  status: string;
  requested_at: string;
}> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
  };

  const res = await fetch(`${API_BASE}/my-profile-changes`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ field, new_value }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Talep gönderilemedi');
  }

  return res.json();
}
