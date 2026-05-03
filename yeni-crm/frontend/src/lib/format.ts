/**
 * Format yardımcıları — Türkçe karakter normalizasyonu, sayı, tarih.
 *
 * V2'den taşınan eski kayıtlarda Türkçe karakterler eksik (örn 'Yakit', 'Idari ceza').
 * Bu helper UI'da görüntülerken doğru Türkçe karakterleri yerine koyar.
 */

const TR_NORMALIZE_MAP: Record<string, string> = {
  // Kesinti tipleri (deductions)
  Yakit: 'Yakıt',
  'Idari ceza': 'İdari Ceza',
  'Idari Ceza': 'İdari Ceza',
  'Trafik cezasi': 'Trafik Cezası',
  'Fatura Edilmeyen Tutar': 'Fatura Edilmeyen Tutar',
  Bakim: 'Bakım',
  'Agir Bakim': 'Ağır Bakım',
  'Motor Servis Bakım': 'Motor Servis Bakım',
  'Motor Hasar': 'Motor Hasarı',
  // Ekipman/Zimmet
  'Korumali Mont': 'Korumalı Mont',
  Yagmurluk: 'Yağmurluk',
  Tshirt: 'T-shirt',
  'Gogus Cantasi': 'Göğüs Çantası',
  'Telefon Tutacagi': 'Telefon Tutacağı',
  Elcik: 'Elcik',
  Kask: 'Kask',
};

/**
 * Eski kayıtlarda Türkçe karakter eksikse normalize et.
 */
export function normalizeTr(text: string | null | undefined): string {
  if (text == null) return '';
  const trimmed = text.trim();
  return TR_NORMALIZE_MAP[trimmed] ?? trimmed;
}

/**
 * Sayıyı Türkçe formatta göster (1.234,56)
 */
export function fmtNumber(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/**
 * Para tutarı formatla (KISA)
 */
export function fmtMoney(value: number | null | undefined, withSuffix = true): string {
  if (value == null) return '—';
  const v = Math.round(value).toLocaleString('tr-TR');
  return withSuffix ? `${v} ₺` : v;
}

/**
 * Tarih: YYYY-MM-DD → 14.03.26
 */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return iso;
  return `${m[3]}.${m[2]}.${m[1].slice(2)}`;
}

/**
 * Period (YYYY-MM) → "Mart 2026"
 */
export function fmtPeriod(period: string): string {
  const months = [
    'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
    'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
  ];
  const [y, m] = period.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return period;
  return `${months[m - 1]} ${y}`;
}
