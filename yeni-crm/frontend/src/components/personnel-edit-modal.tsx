'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import {
  type Personnel,
  type PersonnelCreate,
  type PersonnelUpdate,
  type Restaurant,
  createPersonnel,
  getNextPersonCode,
  updatePersonnel,
} from '@/lib/api';

const ROLES = [
  { value: 'Kurye', label: 'Kurye' },
  { value: 'Joker', label: 'Joker' },
  { value: 'Bölge Müdürü', label: 'Bölge Müdürü' },
  { value: 'Kaptan', label: 'Kaptan' },
  { value: 'Restoran Takım Şefi', label: 'Restoran Takım Şefi' },
];

const VEHICLE_TYPES = [
  { value: '', label: '— seç —' },
  { value: 'Kendi motoru', label: 'Kendi motoru' },
  { value: 'Çat Kapında kiralık', label: 'Çat Kapında kiralık' },
  { value: 'Şirket motoru', label: 'Şirket motoru' },
];

const ACCOUNTING_TYPES = [
  { value: '', label: '— seç —' },
  { value: 'Çat Kapında Muhasebe', label: 'Çat Kapında Muhasebe' },
  { value: 'Kendi muhasebesi', label: 'Kendi muhasebesi' },
  { value: 'Şahıs şirketi', label: 'Şahıs şirketi' },
];

type FormState = {
  full_name: string;
  person_code: string;
  role: string;
  status: string;
  phone: string;
  current_plate: string;
  assigned_restaurant_id: number | null;
  start_date: string;
  monthly_fixed_cost: number;
  vehicle_type: string;
  tc_no: string;
  iban: string;
  accounting_type: string;
  address: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  notes: string;
};

const EMPTY_FORM: FormState = {
  full_name: '',
  person_code: '',
  role: 'Kurye',
  status: 'Aktif',
  phone: '',
  current_plate: '',
  assigned_restaurant_id: null,
  start_date: '',
  monthly_fixed_cost: 0,
  vehicle_type: '',
  tc_no: '',
  iban: '',
  accounting_type: '',
  address: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  notes: '',
};

export function PersonnelEditModal({
  personnel,
  restaurants,
  onClose,
  mode,
}: {
  personnel: Personnel | null;
  restaurants: Restaurant[];
  onClose: () => void;
  mode: 'create' | 'edit';
}) {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(() => {
    if (mode === 'edit' && personnel) {
      return {
        full_name: personnel.full_name ?? '',
        person_code: personnel.person_code ?? '',
        role: personnel.role ?? 'Kurye',
        status: personnel.status ?? 'Aktif',
        phone: personnel.phone ?? '',
        current_plate: personnel.current_plate ?? '',
        assigned_restaurant_id: personnel.assigned_restaurant_id ?? null,
        start_date: personnel.start_date ?? '',
        monthly_fixed_cost: personnel.monthly_fixed_cost ?? 0,
        vehicle_type: personnel.vehicle_type ?? '',
        tc_no: personnel.tc_no ?? '',
        iban: personnel.iban ?? '',
        accounting_type: personnel.accounting_type ?? '',
        address: personnel.address ?? '',
        emergency_contact_name: personnel.emergency_contact_name ?? '',
        emergency_contact_phone: personnel.emergency_contact_phone ?? '',
        notes: personnel.notes ?? '',
      };
    }
    return EMPTY_FORM;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Modal davranışı
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

  // Yeni eklerken role değişince person_code önerisi getir
  useEffect(() => {
    if (mode === 'create' && form.role && !form.person_code) {
      getNextPersonCode(form.role)
        .then(({ person_code }) => {
          setForm((p) => ({ ...p, person_code }));
        })
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.role, mode]);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((p) => ({ ...p, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      // Boş stringleri null'a çevir (db'de NULL kalsın)
      const cleaned: PersonnelUpdate & PersonnelCreate = {
        full_name: form.full_name.trim(),
        person_code: form.person_code.trim() || undefined,
        role: form.role,
        status: form.status,
        phone: form.phone.trim() || undefined,
        current_plate: form.current_plate.trim() || undefined,
        assigned_restaurant_id: form.assigned_restaurant_id ?? undefined,
        start_date: form.start_date || undefined,
        monthly_fixed_cost: form.monthly_fixed_cost || undefined,
        vehicle_type: form.vehicle_type || undefined,
        tc_no: form.tc_no.trim() || undefined,
        iban: form.iban.trim() || undefined,
        accounting_type: form.accounting_type || undefined,
        address: form.address.trim() || undefined,
        emergency_contact_name: form.emergency_contact_name.trim() || undefined,
        emergency_contact_phone: form.emergency_contact_phone.trim() || undefined,
        notes: form.notes.trim() || undefined,
      };

      if (mode === 'create') {
        await createPersonnel(cleaned as PersonnelCreate);
      } else if (personnel) {
        await updatePersonnel(personnel.id, cleaned as PersonnelUpdate);
      }
      onClose();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kaydedilemedi');
    } finally {
      setSaving(false);
    }
  }

  const title = mode === 'create' ? 'Yeni Personel Ekle' : 'Personeli Düzenle';
  const subtitle =
    mode === 'edit' && personnel
      ? `${personnel.full_name} · ${personnel.person_code ?? ''}`
      : 'Yeni kayıt';

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-start justify-center p-4 overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-bg-surface rounded-2xl shadow-2xl w-full max-w-2xl my-8 border border-border">
        {/* Header */}
        <div className="bg-gradient-to-r from-brand-dark to-brand text-white px-6 py-5 rounded-t-2xl flex justify-between items-start">
          <div>
            <div className="text-[11px] uppercase tracking-wider opacity-80 font-semibold">
              {title}
            </div>
            <div className="font-display text-xl font-semibold tracking-tight mt-0.5">
              {subtitle}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-white/80 hover:text-white text-2xl leading-none w-8 h-8 flex items-center justify-center rounded-md hover:bg-white/10 transition"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* İsim & Kod */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <Field label="Ad Soyad *">
                <input
                  type="text"
                  required
                  value={form.full_name}
                  onChange={(e) => set('full_name', e.target.value)}
                  className="input"
                  placeholder="örn: Ahmet Yılmaz"
                />
              </Field>
            </div>
            <Field label="Kod">
              <input
                type="text"
                value={form.person_code}
                onChange={(e) => set('person_code', e.target.value)}
                className="input num"
                placeholder="CK-K??"
              />
            </Field>
          </div>

          {/* Rol */}
          <Field label="Rol *">
            <div className="grid grid-cols-3 md:grid-cols-5 gap-1.5">
              {ROLES.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => set('role', r.value)}
                  className={`px-2 py-2 rounded-lg border text-[12.5px] font-medium transition ${
                    form.role === r.value
                      ? 'border-brand bg-brand-soft text-brand'
                      : 'border-border hover:border-brand/50 text-text-2'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </Field>

          {/* Durum + Telefon */}
          <div className="grid grid-cols-3 gap-3">
            <Field label="Durum">
              <select
                value={form.status}
                onChange={(e) => set('status', e.target.value)}
                className="input"
              >
                <option value="Aktif">Aktif</option>
                <option value="Pasif">Pasif</option>
                <option value="Kara Liste">Kara Liste</option>
              </select>
            </Field>
            <div className="col-span-2">
              <Field label="Telefon">
                <input
                  type="tel"
                  value={form.phone}
                  onChange={(e) => set('phone', e.target.value)}
                  className="input"
                  placeholder="0 5XX XXX XX XX"
                />
              </Field>
            </div>
          </div>

          {/* Atanmış restoran + plaka */}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Atanmış Restoran">
              <select
                value={form.assigned_restaurant_id ?? ''}
                onChange={(e) =>
                  set(
                    'assigned_restaurant_id',
                    e.target.value ? parseInt(e.target.value, 10) : null,
                  )
                }
                className="input"
              >
                <option value="">— atanmamış / Joker —</option>
                {restaurants.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.brand} {r.branch ? `· ${r.branch}` : ''}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Plaka">
              <input
                type="text"
                value={form.current_plate}
                onChange={(e) => set('current_plate', e.target.value.toUpperCase())}
                className="input num"
                placeholder="34XXX000"
              />
            </Field>
          </div>

          {/* Aylık sabit + araç tipi */}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Aylık Sabit Hakediş (₺)" hint="Aylık sabit anlaşmalı kuryeler için">
              <input
                type="number"
                step="any"
                value={form.monthly_fixed_cost}
                onChange={(e) =>
                  set('monthly_fixed_cost', parseFloat(e.target.value) || 0)
                }
                className="input num"
              />
            </Field>
            <Field label="Araç Tipi">
              <select
                value={form.vehicle_type}
                onChange={(e) => set('vehicle_type', e.target.value)}
                className="input"
              >
                {VEHICLE_TYPES.map((v) => (
                  <option key={v.value} value={v.value}>
                    {v.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field label="Başlangıç Tarihi">
            <input
              type="date"
              value={form.start_date}
              onChange={(e) => set('start_date', e.target.value)}
              className="input"
            />
          </Field>

          {/* Detaylı bilgiler — collapsible */}
          <div className="border-t border-border pt-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-[12px] font-semibold text-text-2 hover:text-brand transition flex items-center gap-1"
            >
              <span className={`transition-transform ${showAdvanced ? 'rotate-90' : ''}`}>
                ▸
              </span>
              <span>Detaylı bilgiler {showAdvanced ? '(gizle)' : '(göster)'}</span>
            </button>

            {showAdvanced && (
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <Field label="TC Kimlik No">
                    <input
                      type="text"
                      value={form.tc_no}
                      onChange={(e) => set('tc_no', e.target.value)}
                      className="input num"
                      maxLength={11}
                    />
                  </Field>
                  <Field label="IBAN">
                    <input
                      type="text"
                      value={form.iban}
                      onChange={(e) => set('iban', e.target.value.toUpperCase())}
                      className="input num"
                      placeholder="TR..."
                    />
                  </Field>
                </div>

                <Field label="Muhasebe Tipi">
                  <select
                    value={form.accounting_type}
                    onChange={(e) => set('accounting_type', e.target.value)}
                    className="input"
                  >
                    {ACCOUNTING_TYPES.map((a) => (
                      <option key={a.value} value={a.value}>
                        {a.label}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Adres">
                  <textarea
                    value={form.address}
                    onChange={(e) => set('address', e.target.value)}
                    className="input resize-none"
                    rows={2}
                  />
                </Field>

                <div className="grid grid-cols-2 gap-3">
                  <Field label="Acil Durum — Kişi">
                    <input
                      type="text"
                      value={form.emergency_contact_name}
                      onChange={(e) => set('emergency_contact_name', e.target.value)}
                      className="input"
                    />
                  </Field>
                  <Field label="Acil Durum — Telefon">
                    <input
                      type="tel"
                      value={form.emergency_contact_phone}
                      onChange={(e) => set('emergency_contact_phone', e.target.value)}
                      className="input"
                    />
                  </Field>
                </div>

                <Field label="Notlar">
                  <textarea
                    value={form.notes}
                    onChange={(e) => set('notes', e.target.value)}
                    className="input resize-none"
                    rows={2}
                  />
                </Field>
              </div>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
              {error}
            </div>
          )}

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
              disabled={saving || !form.full_name.trim()}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-brand text-white shadow-sm hover:bg-brand-dark transition disabled:opacity-60"
            >
              {saving
                ? 'Kaydediliyor…'
                : mode === 'create'
                ? '+ Personel Ekle'
                : 'Kaydet'}
            </button>
          </div>
        </form>

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
    </div>
  );
}

function Field({
  label, children, hint,
}: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-[11.5px] font-semibold text-text-2">{label}</span>
        {hint && <span className="text-[10.5px] text-text-3 italic">{hint}</span>}
      </div>
      {children}
    </label>
  );
}
