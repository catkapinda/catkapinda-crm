'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ClipboardList, Phone } from 'lucide-react';

import {
  type Restaurant,
  type RestaurantCreate,
  type RestaurantUpdate,
  createRestaurant,
  updateRestaurant,
} from '@/lib/api';

const PRICING_OPTIONS: { value: string; label: string; help: string }[] = [
  { value: 'hourly_only', label: 'Saatlik', help: 'Sadece saat × ücret' },
  { value: 'hourly_plus_package', label: 'Saat + Prim', help: 'Saatlik + paket başına prim' },
  { value: 'threshold_package', label: 'Eşikli (390)', help: '≤390 düşük tarife, >390 yüksek tarife' },
  { value: 'fixed_monthly', label: 'Aylık Sabit', help: 'Aylık tek tutar; saat/paket sayılmaz' },
];

export function RestaurantEditModal({
  restaurant,
  onClose,
  mode = 'edit',
}: {
  restaurant: Restaurant | null;
  onClose: () => void;
  mode?: 'edit' | 'create';
}) {
  const router = useRouter();
  const r = restaurant; // shorthand
  const [form, setForm] = useState<RestaurantUpdate>({
    brand: r?.brand ?? '',
    branch: r?.branch ?? '',
    billing_group: r?.billing_group ?? '',
    pricing_model: r?.pricing_model ?? 'hourly_plus_package',
    hourly_rate: r?.hourly_rate ?? 0,
    package_rate: r?.package_rate ?? 0,
    package_threshold: r?.package_threshold ?? 390,
    package_rate_low: r?.package_rate_low ?? 0,
    package_rate_high: r?.package_rate_high ?? 0,
    fixed_monthly_fee: r?.fixed_monthly_fee ?? 0,
    vat_rate: r?.vat_rate ?? 20,
    target_headcount: r?.target_headcount ?? 1,
    standard_daily_hours: r?.standard_daily_hours ?? 11,
    contact_name: r?.contact_name ?? '',
    contact_phone: r?.contact_phone ?? '',
    contact_email: r?.contact_email ?? '',
    company_title: r?.company_title ?? '',
    tax_office: r?.tax_office ?? '',
    tax_number: r?.tax_number ?? '',
    address: r?.address ?? '',
    notes: r?.notes ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  // ESC ile kapatma + body scroll lock
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  function set<K extends keyof RestaurantUpdate>(key: K, value: RestaurantUpdate[K]) {
    setForm((p) => ({ ...p, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.brand?.trim()) {
      setError('Marka adı zorunludur');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (mode === 'create') {
        await createRestaurant(form as RestaurantCreate);
      } else if (restaurant) {
        await updateRestaurant(restaurant.id, form);
      }
      onClose();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kaydedilemedi');
    } finally {
      setSaving(false);
    }
  }

  const model = form.pricing_model;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-start justify-center p-4 overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className="bg-bg-surface rounded-2xl shadow-2xl w-full max-w-2xl my-8 border border-border"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-brand-dark to-brand text-white px-6 py-5 rounded-t-2xl flex justify-between items-start">
          <div>
            <div className="text-[11px] uppercase tracking-wider opacity-80 font-semibold">
              {mode === 'create' ? 'Yeni Müşteri / Restoran' : 'Restoran Düzenle'}
            </div>
            <div className="font-display text-xl font-semibold tracking-tight mt-0.5">
              {mode === 'create'
                ? form.brand?.trim() || 'Yeni kayıt'
                : restaurant?.brand ?? '—'}
              {mode === 'edit' && restaurant?.branch && (
                <span className="opacity-70 font-normal"> · {restaurant.branch}</span>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-white/80 hover:text-white text-2xl leading-none w-8 h-8 flex items-center justify-center rounded-md hover:bg-white/10 transition"
            aria-label="Kapat"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Marka & Şube */}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Marka">
              <input
                type="text"
                value={form.brand ?? ''}
                onChange={(e) => set('brand', e.target.value)}
                className="input"
              />
            </Field>
            <Field label="Şube">
              <input
                type="text"
                value={form.branch ?? ''}
                onChange={(e) => set('branch', e.target.value)}
                className="input"
              />
            </Field>
          </div>

          {/* Anlaşma tipi */}
          <Field label="Anlaşma Tipi">
            <div className="grid grid-cols-2 gap-2">
              {PRICING_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => set('pricing_model', opt.value)}
                  className={`text-left p-3 rounded-lg border transition ${
                    form.pricing_model === opt.value
                      ? 'border-brand bg-brand-soft text-brand'
                      : 'border-border hover:border-brand/50 text-text-2'
                  }`}
                >
                  <div className="font-semibold text-sm">{opt.label}</div>
                  <div className="text-[11px] text-text-3 mt-0.5">{opt.help}</div>
                </button>
              ))}
            </div>
          </Field>

          {/* Anlaşmaya göre dinamik alanlar */}
          {model === 'hourly_only' && (
            <Field label="Saat Ücreti (₺/saat)">
              <NumberInput value={form.hourly_rate} onChange={(v) => set('hourly_rate', v)} />
            </Field>
          )}

          {model === 'hourly_plus_package' && (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Saat Ücreti (₺/saat)">
                <NumberInput value={form.hourly_rate} onChange={(v) => set('hourly_rate', v)} />
              </Field>
              <Field label="Paket Primi (₺/paket)">
                <NumberInput value={form.package_rate} onChange={(v) => set('package_rate', v)} />
              </Field>
            </div>
          )}

          {model === 'threshold_package' && (
            <>
              <Field label="Saat Ücreti (₺/saat)">
                <NumberInput
                  value={form.hourly_rate}
                  onChange={(v) => set('hourly_rate', v)}
                />
              </Field>
              <div className="grid grid-cols-3 gap-3">
                <Field label="Eşik (paket)">
                  <NumberInput
                    value={form.package_threshold}
                    onChange={(v) => set('package_threshold', Math.round(v ?? 0))}
                  />
                </Field>
                <Field label="≤ Eşik (₺/paket)">
                  <NumberInput
                    value={form.package_rate_low}
                    onChange={(v) => set('package_rate_low', v)}
                  />
                </Field>
                <Field label="> Eşik (₺/paket)">
                  <NumberInput
                    value={form.package_rate_high}
                    onChange={(v) => set('package_rate_high', v)}
                  />
                </Field>
              </div>
            </>
          )}

          {model === 'fixed_monthly' && (
            <Field label="Aylık Sabit Tutar (₺)">
              <NumberInput
                value={form.fixed_monthly_fee}
                onChange={(v) => set('fixed_monthly_fee', v)}
              />
            </Field>
          )}

          <div className="grid grid-cols-3 gap-3">
            <Field label="Hedef Kurye">
              <NumberInput
                value={form.target_headcount}
                onChange={(v) => set('target_headcount', Math.round(v ?? 0))}
              />
            </Field>
            <Field label="Vardiya Saati (gün)">
              <NumberInput
                value={form.standard_daily_hours}
                onChange={(v) => set('standard_daily_hours', Math.round(v ?? 0))}
              />
            </Field>
            <Field label="KDV Oranı (%)">
              <NumberInput value={form.vat_rate} onChange={(v) => set('vat_rate', v)} />
            </Field>
          </div>
          <div className="text-[11px] text-text-3 -mt-1 px-1">
            Vardiya saati ekstra mesai hesabında kullanılır (örn. 10 saatlik vardiyada bayram günü 20 saat çalışırsa +1 gün ekstra mesai).
          </div>

          {/* Resmi Bilgiler */}
          <div className="border-t border-border pt-4">
            <div className="text-[11px] uppercase tracking-wider text-text-3 font-semibold mb-3 flex items-center gap-1.5">
              <ClipboardList className="w-3.5 h-3.5" strokeWidth={2.2} /> Resmi Bilgiler
            </div>
            <Field label="Ticari Ünvan">
              <input
                type="text"
                value={form.company_title ?? ''}
                onChange={(e) => set('company_title', e.target.value)}
                placeholder="Örn. SUSHICO GIDA ANONİM ŞİRKETİ"
                className="input"
              />
            </Field>
            <div className="grid grid-cols-2 gap-3 mt-3">
              <Field label="Vergi Dairesi">
                <input
                  type="text"
                  value={form.tax_office ?? ''}
                  onChange={(e) => set('tax_office', e.target.value)}
                  placeholder="Örn. Sarıgazi VD"
                  className="input"
                />
              </Field>
              <Field label="Vergi Numarası">
                <input
                  type="text"
                  value={form.tax_number ?? ''}
                  onChange={(e) => set('tax_number', e.target.value)}
                  placeholder="10 hane"
                  maxLength={11}
                  className="input num"
                />
              </Field>
            </div>
          </div>

          {/* İletişim */}
          <div className="border-t border-border pt-4">
            <div className="text-[11px] uppercase tracking-wider text-text-3 font-semibold mb-3 flex items-center gap-1.5">
              <Phone className="w-3.5 h-3.5" strokeWidth={2.2} /> İletişim
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Yetkili İsim Soyisim">
                <input
                  type="text"
                  value={form.contact_name ?? ''}
                  onChange={(e) => set('contact_name', e.target.value)}
                  placeholder="Örn. Gökhan Çelik"
                  className="input"
                />
              </Field>
              <Field label="Telefon">
                <input
                  type="tel"
                  value={form.contact_phone ?? ''}
                  onChange={(e) => set('contact_phone', e.target.value)}
                  className="input"
                />
              </Field>
            </div>
            <Field label="E-posta" className="mt-3">
              <input
                type="email"
                value={form.contact_email ?? ''}
                onChange={(e) => set('contact_email', e.target.value)}
                className="input"
              />
            </Field>
            <Field label="Adres" className="mt-3">
              <textarea
                value={form.address ?? ''}
                onChange={(e) => set('address', e.target.value)}
                rows={2}
                className="input resize-none"
              />
            </Field>
          </div>

          {/* Notlar */}
          <Field label="Notlar">
            <textarea
              value={form.notes ?? ''}
              onChange={(e) => set('notes', e.target.value)}
              rows={2}
              className="input resize-none"
            />
          </Field>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Butonlar */}
          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium text-text-2 hover:bg-bg-surface2 transition"
              disabled={saving}
            >
              Vazgeç
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-brand text-white shadow-sm hover:bg-brand-dark transition disabled:opacity-60"
            >
              {saving
                ? 'Kaydediliyor…'
                : mode === 'create'
                ? '+ Müşteri Ekle'
                : 'Kaydet'}
            </button>
          </div>
        </form>
      </div>

      <style jsx>{`
        :global(.input) {
          width: 100%;
          padding: 8px 12px;
          border-radius: 8px;
          border: 1px solid var(--border, #e5e5e5);
          background: var(--bg-surface, #fff);
          font-size: 14px;
          color: var(--text, #111);
          transition: border-color 0.15s, box-shadow 0.15s;
        }
        :global(.input:focus) {
          outline: none;
          border-color: #0f52ba;
          box-shadow: 0 0 0 3px rgba(15, 82, 186, 0.12);
        }
      `}</style>
    </div>
  );
}

function Field({
  label, children, className,
}: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={`block ${className ?? ''}`}>
      <div className="text-[11.5px] font-semibold text-text-2 mb-1.5">{label}</div>
      {children}
    </label>
  );
}

function NumberInput({
  value, onChange,
}: { value: number | null | undefined; onChange: (v: number) => void }) {
  return (
    <input
      type="number"
      value={value ?? 0}
      onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      className="input num"
      step="any"
    />
  );
}
