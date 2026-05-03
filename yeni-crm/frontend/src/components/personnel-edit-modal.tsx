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
  {
    value: 'Çat Kapında Kiralık',
    label: 'Çat Kapında Kiralık',
    sub: 'Aylık kira · ÇK öder bakım',
  },
  {
    value: 'Çat Kapında Satış',
    label: 'Çat Kapında Satış',
    sub: 'Taksit + taahhüt · bakım kuryede',
  },
  {
    value: 'Kendi Motoru',
    label: 'Kendi Motoru',
    sub: 'Bakım kuryede · ÇK kira/taksit yok',
  },
];

const ACCOUNTING_TYPES = [
  { value: '', label: '— seç —' },
  { value: 'Çat Kapında Muhasebe', label: 'Çat Kapında Muhasebe' },
  { value: 'Kendi Muhasebecisi', label: 'Kendi Muhasebecisi' },
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
  fixed_monthly_billing: number;
  // Araç
  vehicle_type: string;
  motor_purchase: string; // 'Evet' / 'Hayır'
  motor_purchase_sale_price: number;
  motor_purchase_monthly_amount: number;
  motor_purchase_installment_count: number;
  motor_purchase_start_date: string;
  motor_rental: string;
  motor_rental_monthly_amount: number;
  // Muhasebe
  accounting_type: string;
  accountant_cost: number;
  accounting_revenue: number;
  accounting_effective_date: string;
  // Şirket açılışı
  new_company_setup: string;
  company_setup_cost: number;
  company_setup_revenue: number;
  company_setup_effective_date: string;
  // Kimlik & banka
  tc_no: string;
  iban: string;
  tax_number: string;
  tax_office: string;
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
  fixed_monthly_billing: 0,
  vehicle_type: '',
  motor_purchase: '',
  motor_purchase_sale_price: 0,
  motor_purchase_monthly_amount: 0,
  motor_purchase_installment_count: 0,
  motor_purchase_start_date: '',
  motor_rental: '',
  motor_rental_monthly_amount: 0,
  accounting_type: '',
  accountant_cost: 0,
  accounting_revenue: 0,
  accounting_effective_date: '',
  new_company_setup: '',
  company_setup_cost: 0,
  company_setup_revenue: 0,
  company_setup_effective_date: '',
  tc_no: '',
  iban: '',
  tax_number: '',
  tax_office: '',
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
        fixed_monthly_billing: personnel.fixed_monthly_billing ?? 0,
        vehicle_type: personnel.vehicle_type ?? '',
        motor_purchase: personnel.motor_purchase ?? '',
        motor_purchase_sale_price: personnel.motor_purchase_sale_price ?? 0,
        motor_purchase_monthly_amount: personnel.motor_purchase_monthly_amount ?? 0,
        motor_purchase_installment_count: personnel.motor_purchase_installment_count ?? 0,
        motor_purchase_start_date: personnel.motor_purchase_start_date ?? '',
        motor_rental: personnel.motor_rental ?? '',
        motor_rental_monthly_amount: personnel.motor_rental_monthly_amount ?? 0,
        accounting_type: personnel.accounting_type ?? '',
        accountant_cost: personnel.accountant_cost ?? 0,
        accounting_revenue: personnel.accounting_revenue ?? 0,
        accounting_effective_date: personnel.accounting_effective_date ?? '',
        new_company_setup: personnel.new_company_setup ?? '',
        company_setup_cost: personnel.company_setup_cost ?? 0,
        company_setup_revenue: personnel.company_setup_revenue ?? 0,
        company_setup_effective_date: personnel.company_setup_effective_date ?? '',
        tc_no: personnel.tc_no ?? '',
        iban: personnel.iban ?? '',
        tax_number: personnel.tax_number ?? '',
        tax_office: personnel.tax_office ?? '',
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
      // Boş stringleri ve 0'ları undefined'a çevir (db'de değişmesin)
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
        fixed_monthly_billing: form.fixed_monthly_billing || undefined,
        vehicle_type: form.vehicle_type || undefined,
        motor_purchase: form.motor_purchase || undefined,
        motor_purchase_sale_price: form.motor_purchase_sale_price || undefined,
        motor_purchase_monthly_amount: form.motor_purchase_monthly_amount || undefined,
        motor_purchase_installment_count: form.motor_purchase_installment_count || undefined,
        motor_purchase_start_date: form.motor_purchase_start_date || undefined,
        motor_rental: form.motor_rental || undefined,
        motor_rental_monthly_amount: form.motor_rental_monthly_amount || undefined,
        accounting_type: form.accounting_type || undefined,
        accountant_cost: form.accountant_cost || undefined,
        accounting_revenue: form.accounting_revenue || undefined,
        accounting_effective_date: form.accounting_effective_date || undefined,
        new_company_setup: form.new_company_setup || undefined,
        company_setup_cost: form.company_setup_cost || undefined,
        company_setup_revenue: form.company_setup_revenue || undefined,
        company_setup_effective_date: form.company_setup_effective_date || undefined,
        tc_no: form.tc_no.trim() || undefined,
        iban: form.iban.trim() || undefined,
        tax_number: form.tax_number.trim() || undefined,
        tax_office: form.tax_office.trim() || undefined,
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

          {/* Görev & Hakediş — Rol bazlı koşullu alanlar */}
          {(() => {
            const role = form.role;
            const needsRestaurant = ['Kurye', 'Kaptan', 'Restoran Takım Şefi'].includes(role);
            const noRestaurant = ['Bölge Müdürü', 'Joker'].includes(role);
            const selectedRest = restaurants.find(
              (r) => r.id === form.assigned_restaurant_id,
            );
            const isFixedMonthlyRestaurant =
              selectedRest?.pricing_model === 'fixed_monthly';
            // Sabit aylık alanı kimler için görünür?
            const showFixedSalary =
              ['Bölge Müdürü', 'Joker', 'Restoran Takım Şefi'].includes(role) ||
              isFixedMonthlyRestaurant;
            // Kaptan bonus banner
            const isKaptan = role === 'Kaptan';

            const modelLabel: Record<string, { label: string; ico: string; color: string }> = {
              hourly_only: { label: 'Sadece Saatlik', ico: '⏱', color: 'bg-blue-50 border-blue-200 text-blue-800' },
              hourly_plus_package: { label: 'Saat + Prim', ico: '+', color: 'bg-orange-50 border-orange-200 text-orange-800' },
              threshold_package: { label: 'Eşikli (390)', ico: '≷', color: 'bg-cream-100 border-yellow-300 text-yellow-900' },
              fixed_monthly: { label: 'Aylık Sabit', ico: '∞', color: 'bg-green-50 border-green-200 text-green-800' },
            };

            return (
              <>
                {/* Atanan Restoran (Kurye/Kaptan/RTŞ) veya bilgi banner (BM/Joker) */}
                {needsRestaurant && (
                  <Field label="Atanan Restoran *">
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
                      <option value="">— Restoran seçin (anlaşma türü açılacak) —</option>
                      {restaurants.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.brand} {r.branch ? `· ${r.branch}` : ''}
                          {r.pricing_model
                            ? ` (${modelLabel[r.pricing_model]?.label ?? r.pricing_model})`
                            : ''}
                        </option>
                      ))}
                    </select>
                  </Field>
                )}

                {noRestaurant && (
                  <div className="flex gap-2.5 items-start bg-cream-100 border border-yellow-200 rounded-xl p-3 text-[12px] text-yellow-900">
                    <span className="text-base leading-none mt-0.5">🌐</span>
                    <div>
                      <strong>Bu rol bir restorana atanmaz.</strong> Tüm
                      restoranlardan sorumludur — sadece sabit aylık tutar
                      tanımlanır.
                    </div>
                  </div>
                )}

                {/* Restoran seçildiyse pricing banner */}
                {needsRestaurant && selectedRest && (
                  <div
                    className={`flex gap-2.5 items-start border rounded-xl p-3 text-[12px] ${
                      modelLabel[selectedRest.pricing_model ?? '']?.color ??
                      'bg-bg-surface2 border-border text-text-2'
                    }`}
                  >
                    <span className="text-lg leading-none mt-0.5 font-bold">
                      {modelLabel[selectedRest.pricing_model ?? '']?.ico ?? '?'}
                    </span>
                    <div className="space-y-1">
                      <div>
                        <strong>
                          {modelLabel[selectedRest.pricing_model ?? '']?.label ??
                            selectedRest.pricing_model}
                        </strong>{' '}
                        anlaşma — restoran tarifesi otomatik uygulanır.
                      </div>
                      <div className="font-mono text-[11.5px] opacity-90">
                        {selectedRest.hourly_rate
                          ? `Saat ${selectedRest.hourly_rate} ₺/sa  ·  `
                          : ''}
                        {selectedRest.package_rate
                          ? `Paket ${selectedRest.package_rate} ₺/pkt`
                          : ''}
                        {selectedRest.pricing_model === 'threshold_package'
                          ? `≤390: ${selectedRest.package_rate_low ?? 0} ₺  ·  >390: ${selectedRest.package_rate_high ?? 0} ₺/pkt`
                          : ''}
                        {selectedRest.pricing_model === 'fixed_monthly'
                          ? `Restoran tarife: ${(selectedRest.fixed_monthly_fee ?? 0).toLocaleString('tr-TR')} ₺/ay`
                          : ''}
                      </div>
                    </div>
                  </div>
                )}

                {/* Kaptan bonusu banner */}
                {isKaptan && (
                  <div className="flex gap-2.5 items-start bg-green-50 border border-green-200 rounded-xl p-3 text-[12px] text-green-900">
                    <span className="text-base leading-none mt-0.5">⭐</span>
                    <div>
                      <strong>Kaptan rolü:</strong> standart kurye gibi saat +
                      paket alır, ek olarak{' '}
                      <strong>her ay otomatik +3.000 ₺ Kaptan Bonusu</strong>{' '}
                      hakedişine eklenir.
                    </div>
                  </div>
                )}

                {/* Sabit Aylık alanları (RTŞ/BM/Joker veya fixed_monthly restoran) */}
                {showFixedSalary && (
                  <div className="bg-brand-soft/40 border border-brand/15 rounded-xl p-3.5">
                    <div className="text-[10.5px] font-semibold text-brand uppercase tracking-wider mb-2.5 flex items-center gap-2">
                      <span>💰 Sabit Aylık Anlaşma</span>
                      <span className="text-text-3 font-normal normal-case">
                        {role === 'Bölge Müdürü' || role === 'Joker'
                          ? '(zorunlu)'
                          : role === 'Restoran Takım Şefi'
                          ? '(Takım Şefi için zorunlu)'
                          : '(Aylık Sabit anlaşma için zorunlu)'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <Field
                        label="Kuryeye Ödenen (₺)"
                        hint="net aylık hakediş"
                      >
                        <input
                          type="number"
                          step="any"
                          value={form.monthly_fixed_cost}
                          onChange={(e) =>
                            set('monthly_fixed_cost', parseFloat(e.target.value) || 0)
                          }
                          className="input num"
                          placeholder="örn 72050"
                        />
                      </Field>
                      <Field
                        label="Restorana Fatura (₺)"
                        hint="KDV hariç, restorana yansıyan"
                      >
                        <input
                          type="number"
                          step="any"
                          value={form.fixed_monthly_billing}
                          onChange={(e) =>
                            set('fixed_monthly_billing', parseFloat(e.target.value) || 0)
                          }
                          className="input num"
                          placeholder="örn 84500"
                        />
                      </Field>
                    </div>
                    {form.fixed_monthly_billing > 0 &&
                      form.monthly_fixed_cost > 0 && (
                        <div className="mt-2 text-[11.5px] text-text-2">
                          <span className="text-text-3">Aylık kar farkı:</span>{' '}
                          <span className="font-semibold text-brand num">
                            {(
                              form.fixed_monthly_billing - form.monthly_fixed_cost
                            ).toLocaleString('tr-TR')}{' '}
                            ₺
                          </span>
                        </div>
                      )}
                  </div>
                )}

                {/* Plaka — sadece restoran atanan rollerde göster */}
                {needsRestaurant && (
                  <Field label="Plaka">
                    <input
                      type="text"
                      value={form.current_plate}
                      onChange={(e) =>
                        set('current_plate', e.target.value.toUpperCase())
                      }
                      className="input num"
                      placeholder="34XXX000"
                    />
                  </Field>
                )}
              </>
            );
          })()}

          {/* Araç tipi — radio cards (3 seçenek) */}
          <Field label="Araç Tipi *">
            <div className="grid grid-cols-3 gap-2">
              {VEHICLE_TYPES.map((v) => {
                const active = form.vehicle_type === v.value;
                return (
                  <button
                    key={v.value}
                    type="button"
                    onClick={() => {
                      set('vehicle_type', v.value);
                      // Eski flag'leri vehicle_type'a göre senkronize et
                      set(
                        'motor_rental',
                        v.value === 'Çat Kapında Kiralık' ? 'Evet' : 'Hayır',
                      );
                      set(
                        'motor_purchase',
                        v.value === 'Çat Kapında Satış' ? 'Evet' : 'Hayır',
                      );
                    }}
                    className={`text-left p-3 rounded-lg border transition ${
                      active
                        ? 'border-brand bg-brand-soft text-brand'
                        : 'border-border hover:border-brand/50 text-text-2'
                    }`}
                  >
                    <div className="font-semibold text-[12.5px]">{v.label}</div>
                    <div className="text-[10.5px] text-text-3 mt-0.5 leading-tight">
                      {v.sub}
                    </div>
                  </button>
                );
              })}
            </div>
          </Field>

          {/* Çat Kapında Kiralık → Aylık kira */}
          {form.vehicle_type === 'Çat Kapında Kiralık' && (
            <div className="bg-orange-50/50 border border-orange-200 rounded-xl p-3.5">
              <div className="text-[10.5px] font-semibold text-orange-800 uppercase tracking-wider mb-2">
                Çat Kapında Kiralık Detayları
              </div>
              <Field label="Aylık Kira (₺)" hint="ÇK gideri · kuryeden düşülmez">
                <input
                  type="number"
                  step="any"
                  value={form.motor_rental_monthly_amount}
                  onChange={(e) =>
                    set(
                      'motor_rental_monthly_amount',
                      parseFloat(e.target.value) || 0,
                    )
                  }
                  className="input num"
                  placeholder="örn 13000"
                />
              </Field>
            </div>
          )}

          {/* Çat Kapında Satış → Taksit + taahhüt */}
          {form.vehicle_type === 'Çat Kapında Satış' && (
            <div className="bg-purple-50/50 border border-purple-200 rounded-xl p-3.5">
              <div className="text-[10.5px] font-semibold text-purple-800 uppercase tracking-wider mb-2">
                Çat Kapında Satış Detayları
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Aylık Taksit (₺)" hint="kuryenin maaşından kesilir">
                  <input
                    type="number"
                    step="any"
                    value={form.motor_purchase_monthly_amount}
                    onChange={(e) =>
                      set(
                        'motor_purchase_monthly_amount',
                        parseFloat(e.target.value) || 0,
                      )
                    }
                    className="input num"
                    placeholder="örn 11250"
                  />
                </Field>
                <Field label="Taahhüt Süresi (ay)">
                  <input
                    type="number"
                    value={form.motor_purchase_installment_count}
                    onChange={(e) =>
                      set(
                        'motor_purchase_installment_count',
                        parseInt(e.target.value) || 0,
                      )
                    }
                    className="input num"
                    placeholder="örn 18"
                  />
                </Field>
                <Field label="Sözleşme Başlangıcı">
                  <input
                    type="date"
                    value={form.motor_purchase_start_date}
                    onChange={(e) =>
                      set('motor_purchase_start_date', e.target.value)
                    }
                    className="input"
                  />
                </Field>
                <Field label="Toplam Satış Bedeli (₺)" hint="bilgi · taksit × süre">
                  <input
                    type="number"
                    step="any"
                    value={form.motor_purchase_sale_price}
                    onChange={(e) =>
                      set('motor_purchase_sale_price', parseFloat(e.target.value) || 0)
                    }
                    className="input num"
                  />
                </Field>
              </div>
            </div>
          )}

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
              <div className="mt-4 space-y-5">
                {/* 📊 MUHASEBE & VERGİ */}
                <SectionTitle icon="📊" label="Muhasebe & Vergi" />
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Muhasebe Tipi *">
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
                  <Field label="Muhasebe Geçiş Tarihi" hint="varsa">
                    <input
                      type="date"
                      value={form.accounting_effective_date}
                      onChange={(e) =>
                        set('accounting_effective_date', e.target.value)
                      }
                      className="input"
                    />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <Field label="Vergi Dairesi">
                    <input
                      type="text"
                      value={form.tax_office}
                      onChange={(e) => set('tax_office', e.target.value)}
                      className="input"
                      placeholder="Örn. Sarıgazi VD"
                    />
                  </Field>
                  <Field label="Vergi Numarası">
                    <input
                      type="text"
                      value={form.tax_number}
                      onChange={(e) => set('tax_number', e.target.value)}
                      className="input num"
                      placeholder="10 hane"
                      maxLength={11}
                    />
                  </Field>
                </div>

                {/* ÇK Muhasebe seçilince → Aylık bedel + Şirket Açılışı toggle */}
                {form.accounting_type === 'Çat Kapında Muhasebe' && (
                  <div className="bg-brand-soft/40 border border-brand/15 rounded-xl p-3.5 space-y-3">
                    <div className="text-[10.5px] font-semibold text-brand uppercase tracking-wider">
                      Çat Kapında Muhasebe Detayları
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <Field
                        label="Aylık Muhasebe Bedeli (₺)"
                        hint="kuryeden alınan"
                      >
                        <input
                          type="number"
                          step="any"
                          value={form.accountant_cost}
                          onChange={(e) =>
                            set('accountant_cost', parseFloat(e.target.value) || 0)
                          }
                          className="input num"
                          placeholder="örn 2000"
                        />
                      </Field>
                      <Field
                        label="Aylık Muhasebe Geliri (₺)"
                        hint="bana kalan"
                      >
                        <input
                          type="number"
                          step="any"
                          value={form.accounting_revenue}
                          onChange={(e) =>
                            set('accounting_revenue', parseFloat(e.target.value) || 0)
                          }
                          className="input num"
                          placeholder="örn 1500"
                        />
                      </Field>
                    </div>

                    {/* Şirket Açılışı toggle */}
                    <label className="flex items-center gap-2.5 cursor-pointer p-2 -mx-2 rounded-lg hover:bg-bg-surface/60 transition">
                      <input
                        type="checkbox"
                        checked={form.new_company_setup === 'Evet'}
                        onChange={(e) =>
                          set(
                            'new_company_setup',
                            e.target.checked ? 'Evet' : 'Hayır',
                          )
                        }
                        className="w-4 h-4 accent-brand"
                      />
                      <div>
                        <div className="text-[12.5px] font-semibold text-text">
                          Şirket açılışı yapılacak / yapıldı
                        </div>
                        <div className="text-[10.5px] text-text-3">
                          Tek seferlik bedel + bilgilerini gir
                        </div>
                      </div>
                    </label>

                    {form.new_company_setup === 'Evet' && (
                      <div className="grid grid-cols-3 gap-3 bg-bg-surface rounded-lg p-3 border border-border">
                        <Field label="Açılış Bedeli (₺)" hint="kuryeden">
                          <input
                            type="number"
                            step="any"
                            value={form.company_setup_cost}
                            onChange={(e) =>
                              set(
                                'company_setup_cost',
                                parseFloat(e.target.value) || 0,
                              )
                            }
                            className="input num"
                            placeholder="örn 1500"
                          />
                        </Field>
                        <Field label="Açılış Geliri (₺)" hint="bana kalan">
                          <input
                            type="number"
                            step="any"
                            value={form.company_setup_revenue}
                            onChange={(e) =>
                              set(
                                'company_setup_revenue',
                                parseFloat(e.target.value) || 0,
                              )
                            }
                            className="input num"
                            placeholder="örn 1000"
                          />
                        </Field>
                        <Field label="Açılış Tarihi">
                          <input
                            type="date"
                            value={form.company_setup_effective_date}
                            onChange={(e) =>
                              set('company_setup_effective_date', e.target.value)
                            }
                            className="input"
                          />
                        </Field>
                      </div>
                    )}
                  </div>
                )}

                {/* 🪪 KİMLİK & BANKA */}
                <SectionTitle icon="🪪" label="Kimlik & Banka" />
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

                {/* 📍 ADRES & ACİL DURUM */}
                <SectionTitle icon="📍" label="Adres & Acil Durum" />
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

function SectionTitle({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="flex items-center gap-2 -mb-1 pt-1">
      <span className="text-base">{icon}</span>
      <h4 className="text-[12.5px] font-semibold text-text-2 uppercase tracking-wider">
        {label}
      </h4>
      <div className="flex-1 border-b border-border" />
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
