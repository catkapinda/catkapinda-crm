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

// ─────────────────────────────────────────────────────────────────
// SMS OTP login (Sprint 2)
// ─────────────────────────────────────────────────────────────────

export type OtpRequestResult = {
  sent: boolean;
  masked_phone: string;
  expires_in_seconds: number;
  cooldown_seconds: number;
};

export async function requestLoginOtp(phone: string): Promise<OtpRequestResult> {
  const res = await fetch(`${API_BASE}/login/request-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Kod gönderilemedi');
  }
  return res.json();
}

export async function verifyLoginOtp(
  phone: string,
  code: string,
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
  const res = await fetch(`${API_BASE}/login/verify-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Kod doğrulanamadı');
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
  profile_photo_data: string | null;
  birth_date: string | null;
  tshirt_size: string | null;
  start_date: string | null;
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

// ─────────────────────────────────────────────────────────────────
// Sprint 2: doğrudan güncelleme + fotoğraf
// ─────────────────────────────────────────────────────────────────

export async function directUpdateProfile(
  field: string,
  new_value: string | null,
): Promise<{ field: string; old_value: string | null; new_value: string | null; changed: boolean }> {
  const headers = { 'Content-Type': 'application/json', ...getAuthHeader() };
  const res = await fetch(`${API_BASE}/my-profile/direct-update`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ field, new_value }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Güncellenemedi');
  }
  return res.json();
}

export async function uploadProfilePhoto(
  photoDataUrl: string | null,
): Promise<{ has_photo: boolean }> {
  const headers = { 'Content-Type': 'application/json', ...getAuthHeader() };
  const res = await fetch(`${API_BASE}/my-profile/photo`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ photo_data_url: photoDataUrl }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Fotoğraf kaydedilemedi');
  }
  return res.json();
}

export type EditableFieldsConfig = {
  critical: string[];
  direct: string[];
};

export async function getEditableFields(): Promise<EditableFieldsConfig> {
  const headers = { 'Content-Type': 'application/json', ...getAuthHeader() };
  const res = await fetch(`${API_BASE}/my-profile/editable-fields`, { headers });
  if (!res.ok) throw new Error('Alan konfigürasyonu yüklenemedi');
  return res.json();
}

export type DirectChangeLog = {
  id: number;
  field: string;
  old_value: string | null;
  new_value: string | null;
  changed_at: string;
};

export async function listMyDirectChangeLog(): Promise<DirectChangeLog[]> {
  const headers = { 'Content-Type': 'application/json', ...getAuthHeader() };
  const res = await fetch(`${API_BASE}/my-profile/direct-log`, { headers });
  if (!res.ok) throw new Error('Değişim logu yüklenemedi');
  return res.json();
}

// ─────────────────────────────────────────────────────────────────
// E-imza
// ─────────────────────────────────────────────────────────────────

export type BordroSignature = {
  is_signed: boolean;
  period: string;
  id?: number;
  personnel_id?: number;
  signed_at?: string;
  ip_address?: string | null;
};

export async function getMyBordroSignature(period: string): Promise<BordroSignature> {
  const headers = { 'Content-Type': 'application/json', ...getAuthHeader() };
  const res = await fetch(`${API_BASE}/my-bordro/${encodeURIComponent(period)}/signature`, {
    headers,
  });
  if (!res.ok) throw new Error('İmza durumu alınamadı');
  return res.json();
}

export async function signMyBordro(
  period: string,
  signature_data: string,
): Promise<BordroSignature> {
  const headers = { 'Content-Type': 'application/json', ...getAuthHeader() };
  const res = await fetch(`${API_BASE}/my-bordro/${encodeURIComponent(period)}/sign`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ signature_data }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'İmza kaydedilemedi');
  }
  return res.json();
}
