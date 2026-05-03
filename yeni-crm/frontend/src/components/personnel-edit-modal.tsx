'use client';

import { useEffect, useMemo, useState } from 'react';
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
  { value: 'Kaptan', label: 'Kaptan' },
  { value: 'Restoran Takım Şefi', label: 'Restoran Takım Şefi' },
  { value: 'Bölge Müdürü', label: 'Bölge Müdürü' },
  { value: 'Joker', label: 'Joker' },
];

const STEPS = [
  { num: 1, label: 'Kimlik' },
  { num: 2, label: 'Görev & Hakediş' },
  { num: 3, label: 'Araç' },
  { num: 4, label: 'Muhasebe' },
];

type FormState = {
  // 1. Kimlik
  full_name: string;
  person_code: string;
  tc_no: string;
  phone: string;
  address: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  iban: string;
  // 2. Görev & Hakediş
  role: string;
  status: string;
  start_date: string;
  assigned_restaurant_id: number | null;
  monthly_fixed_cost: number;
  fixed_monthly_billing: number;
  // 3. Araç
  vehicle_type: string;
  current_plate: string;
  motor_rental_monthly_amount: number;
  motor_purchase_monthly_amount: number;
  motor_purchase_installment_count: number;
  motor_purchase_start_date: string;
  motor_purchase_sale_price: number;
  // 4. Muhasebe
  accounting_type: string;
  accounting_effective_date: string;
  tax_office: string;
  tax_number: string;
  accountant_cost: number;
  accounting_revenue: number;
  new_company_setup: string;
  company_setup_cost: number;
  company_setup_revenue: number;
  company_setup_effective_date: string;
  notes: string;
};

const todayISO = () => new Date().toISOString().slice(0, 10);

const EMPTY_FORM: FormState = {
  full_name: '',
  person_code: '',
  tc_no: '',
  phone: '',
  address: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  iban: '',
  role: 'Kurye',
  status: 'Aktif',
  start_date: todayISO(),
  assigned_restaurant_id: null,
  monthly_fixed_cost: 0,
  fixed_monthly_billing: 0,
  vehicle_type: 'Çat Kapında Kiralık',
  current_plate: '',
  motor_rental_monthly_amount: 13000,
  motor_purchase_monthly_amount: 0,
  motor_purchase_installment_count: 18,
  motor_purchase_start_date: '',
  motor_purchase_sale_price: 0,
  accounting_type: 'Çat Kapında Muhasebe',
  accounting_effective_date: '',
  tax_office: '',
  tax_number: '',
  accountant_cost: 2000,
  accounting_revenue: 0,
  new_company_setup: 'Hayır',
  company_setup_cost: 1500,
  company_setup_revenue: 0,
  company_setup_effective_date: '',
  notes: '',
};

const PRICING_LABELS: Record<string, string> = {
  hourly_only: 'Sadece Saatlik',
  hourly_plus_package: 'Saat + Prim',
  threshold_package: 'Eşikli (390)',
  fixed_monthly: 'Aylık Sabit',
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
  const [activeStep, setActiveStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const [form, setForm] = useState<FormState>(() => {
    if (mode === 'edit' && personnel) {
      return {
        full_name: personnel.full_name ?? '',
        person_code: personnel.person_code ?? '',
        tc_no: personnel.tc_no ?? '',
        phone: personnel.phone ?? '',
        address: personnel.address ?? '',
        emergency_contact_name: personnel.emergency_contact_name ?? '',
        emergency_contact_phone: personnel.emergency_contact_phone ?? '',
        iban: personnel.iban ?? '',
        role: personnel.role ?? 'Kurye',
        status: personnel.status ?? 'Aktif',
        start_date: personnel.start_date ?? todayISO(),
        assigned_restaurant_id: personnel.assigned_restaurant_id ?? null,
        monthly_fixed_cost: personnel.monthly_fixed_cost ?? 0,
        fixed_monthly_billing: personnel.fixed_monthly_billing ?? 0,
        vehicle_type: personnel.vehicle_type ?? 'Çat Kapında Kiralık',
        current_plate: personnel.current_plate ?? '',
        motor_rental_monthly_amount: personnel.motor_rental_monthly_amount ?? 0,
        motor_purchase_monthly_amount: personnel.motor_purchase_monthly_amount ?? 0,
        motor_purchase_installment_count: personnel.motor_purchase_installment_count ?? 0,
        motor_purchase_start_date: personnel.motor_purchase_start_date ?? '',
        motor_purchase_sale_price: personnel.motor_purchase_sale_price ?? 0,
        accounting_type: personnel.accounting_type ?? 'Çat Kapında Muhasebe',
        accounting_effective_date: personnel.accounting_effective_date ?? '',
        tax_office: personnel.tax_office ?? '',
        tax_number: personnel.tax_number ?? '',
        accountant_cost: personnel.accountant_cost ?? 0,
        accounting_revenue: personnel.accounting_revenue ?? 0,
        new_company_setup: personnel.new_company_setup ?? 'Hayır',
        company_setup_cost: personnel.company_setup_cost ?? 0,
        company_setup_revenue: personnel.company_setup_revenue ?? 0,
        company_setup_effective_date: personnel.company_setup_effective_date ?? '',
        notes: personnel.notes ?? '',
      };
    }
    return EMPTY_FORM;
  });

  // Açılış animasyonu + ESC + body scroll lock
  useEffect(() => {
    const id = requestAnimationFrame(() => setOpen(true));
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      cancelAnimationFrame(id);
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Yeni kayıtta role değişince otomatik kod öner
  useEffect(() => {
    if (mode === 'create' && form.role && !form.person_code) {
      getNextPersonCode(form.role)
        .then(({ person_code }) => set('person_code', person_code))
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.role, mode]);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((p) => ({ ...p, [key]: value }));
  }

  function handleClose() {
    setOpen(false);
    setTimeout(onClose, 320);
  }

  async function handleSubmit() {
    if (!form.full_name.trim()) {
      setError('Ad Soyad zorunludur');
      setActiveStep(1);
      return;
    }
    setSaving(true);
    setError(null);
    try {
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
        motor_rental:
          form.vehicle_type === 'Çat Kapında Kiralık' ? 'Evet' : 'Hayır',
        motor_purchase:
          form.vehicle_type === 'Çat Kapında Satış' ? 'Evet' : 'Hayır',
        motor_rental_monthly_amount:
          form.motor_rental_monthly_amount || undefined,
        motor_purchase_monthly_amount:
          form.motor_purchase_monthly_amount || undefined,
        motor_purchase_installment_count:
          form.motor_purchase_installment_count || undefined,
        motor_purchase_start_date: form.motor_purchase_start_date || undefined,
        motor_purchase_sale_price: form.motor_purchase_sale_price || undefined,
        accounting_type: form.accounting_type || undefined,
        accountant_cost: form.accountant_cost || undefined,
        accounting_revenue: form.accounting_revenue || undefined,
        accounting_effective_date: form.accounting_effective_date || undefined,
        new_company_setup: form.new_company_setup || undefined,
        company_setup_cost: form.company_setup_cost || undefined,
        company_setup_revenue: form.company_setup_revenue || undefined,
        company_setup_effective_date:
          form.company_setup_effective_date || undefined,
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
      handleClose();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kaydedilemedi');
    } finally {
      setSaving(false);
    }
  }

  // Seçili restoran
  const selectedRest = useMemo(
    () => restaurants.find((r) => r.id === form.assigned_restaurant_id) ?? null,
    [restaurants, form.assigned_restaurant_id],
  );

  // Tahmini hakediş — 180 saat / 350 paket varsayımıyla
  const liveCalc = useMemo(() => {
    const hours = 180;
    const pkts = 350;
    const role = form.role;
    const isFixedRole = ['Bölge Müdürü', 'Joker', 'Restoran Takım Şefi'].includes(role);
    let dealLabel = '— rol seçin —';
    let gross = 0;

    if (isFixedRole) {
      dealLabel = 'Sabit aylık';
      gross = form.monthly_fixed_cost;
    } else if (selectedRest) {
      const pm = selectedRest.pricing_model ?? '';
      const hr = selectedRest.hourly_rate ?? 0;
      const pr = selectedRest.package_rate ?? 0;
      const lo = selectedRest.package_rate_low ?? 0;
      const hi = selectedRest.package_rate_high ?? 0;
      const fee = selectedRest.fixed_monthly_fee ?? 0;
      dealLabel = PRICING_LABELS[pm] ?? pm;
      if (pm === 'hourly_only') gross = hours * hr;
      else if (pm === 'hourly_plus_package') gross = hours * hr + pkts * pr;
      else if (pm === 'threshold_package')
        gross = hours * hr + pkts * (pkts > 390 ? hi : lo);
      else if (pm === 'fixed_monthly') gross = fee;
    }

    const kaptanBonus = role === 'Kaptan' ? 3000 : 0;
    const motorDed =
      form.vehicle_type === 'Çat Kapında Satış'
        ? form.motor_purchase_monthly_amount
        : 0;
    const accDed =
      form.accounting_type === 'Çat Kapında Muhasebe'
        ? form.accountant_cost
        : 0;
    const setupDed =
      form.accounting_type === 'Çat Kapında Muhasebe' &&
      form.new_company_setup === 'Evet'
        ? form.company_setup_cost
        : 0;
    const net = gross + kaptanBonus - motorDed - accDed - setupDed;

    return {
      dealLabel,
      gross,
      kaptanBonus,
      motorDed,
      accDed,
      setupDed,
      net,
    };
  }, [form, selectedRest]);

  const initials = (form.full_name || 'YP')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');

  // Step bölümlerine scroll için ref'siz: id ile
  function jumpToStep(n: number) {
    setActiveStep(n);
    const el = document.getElementById(`pp-step-${n}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <>
      {/* Overlay */}
      <div
        className={`fixed inset-0 z-50 bg-black/40 backdrop-blur-sm transition-opacity duration-300 ${
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={handleClose}
      />
      {/* Slide panel */}
      <div
        className={`fixed top-0 right-0 bottom-0 z-50 w-full max-w-[760px] bg-bg-surface shadow-2xl flex flex-col transition-transform duration-[400ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* HEAD */}
        <div className="px-7 pt-6 pb-4 border-b border-border flex justify-between items-start">
          <div>
            <div className="font-display text-[22px] font-semibold tracking-tight">
              {mode === 'create' ? 'Yeni Personel' : `Düzenle · ${personnel?.full_name}`}
            </div>
            <div className="text-[13px] text-text-3 mt-1 font-medium">
              {mode === 'create'
                ? 'Restoran seçince fiyatlandırma alanları otomatik açılır · IBAN dışında her şey zorunlu'
                : `${personnel?.person_code ?? ''} · ${personnel?.role ?? ''}`}
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="text-text-3 hover:text-text text-xl leading-none w-8 h-8 flex items-center justify-center rounded-md hover:bg-bg-surface2 transition"
          >
            ×
          </button>
        </div>

        {/* STEP NAV */}
        <div className="flex gap-2 px-7 py-4 bg-bg-surface border-b border-border">
          {STEPS.map((s) => {
            const active = activeStep === s.num;
            return (
              <button
                key={s.num}
                type="button"
                onClick={() => jumpToStep(s.num)}
                className={`flex-1 flex items-center gap-2 p-2 rounded-md text-[12px] font-semibold transition ${
                  active
                    ? 'bg-brand-soft text-brand'
                    : 'bg-bg-surface2 text-text-3 hover:text-text-2'
                }`}
              >
                <span
                  className={`w-[22px] h-[22px] rounded-full flex items-center justify-center text-[11px] font-bold ${
                    active ? 'bg-brand text-white' : 'bg-bg-surface text-text-3'
                  }`}
                >
                  {s.num}
                </span>
                <span>{s.label}</span>
              </button>
            );
          })}
        </div>

        {/* INNER */}
        <div className="grid grid-cols-[1fr_240px] flex-1 overflow-hidden">
          {/* FORM */}
          <div className="overflow-y-auto px-7 pt-4 pb-6 space-y-6">
            {/* 1. KİMLİK */}
            <Section id="pp-step-1" icon="👤" title="Kimlik Bilgileri">
              <Row>
                <Field label="Ad Soyad" required>
                  <input
                    value={form.full_name}
                    onChange={(e) => set('full_name', e.target.value)}
                    placeholder="Örn. Ahmet Yılmaz"
                    className="input"
                    required
                    onFocus={() => setActiveStep(1)}
                  />
                </Field>
                <Field label="Personel Kodu" hint="Otomatik atandı">
                  <input
                    value={form.person_code}
                    onChange={(e) => set('person_code', e.target.value)}
                    className="input num"
                    placeholder="CK-K??"
                  />
                </Field>
              </Row>
              <Row>
                <Field label="TC Kimlik No" required>
                  <input
                    value={form.tc_no}
                    onChange={(e) => set('tc_no', e.target.value)}
                    placeholder="11 hane"
                    maxLength={11}
                    className="input num"
                  />
                </Field>
                <Field label="Telefon" required>
                  <input
                    type="tel"
                    value={form.phone}
                    onChange={(e) => set('phone', e.target.value)}
                    placeholder="0 5xx xxx xx xx"
                    className="input"
                  />
                </Field>
              </Row>
              <Field label="Adres" required>
                <input
                  value={form.address}
                  onChange={(e) => set('address', e.target.value)}
                  placeholder="Mah, sokak, no, ilçe/il"
                  className="input"
                />
              </Field>
              <Row>
                <Field label="Acil İletişim Adı" optional>
                  <input
                    value={form.emergency_contact_name}
                    onChange={(e) => set('emergency_contact_name', e.target.value)}
                    className="input"
                  />
                </Field>
                <Field label="Acil Telefon" optional>
                  <input
                    type="tel"
                    value={form.emergency_contact_phone}
                    onChange={(e) =>
                      set('emergency_contact_phone', e.target.value)
                    }
                    placeholder="0 5xx …"
                    className="input"
                  />
                </Field>
              </Row>
              <Field label="IBAN" optional>
                <input
                  value={form.iban}
                  onChange={(e) => set('iban', e.target.value.toUpperCase())}
                  placeholder="TR00 0000 0000 0000 0000 0000 00"
                  className="input num"
                />
              </Field>
            </Section>

            {/* 2. GÖREV */}
            <Section id="pp-step-2" icon="🍽" title="Görev & Hakediş">
              <Row>
                <Field label="Rol" required>
                  <select
                    value={form.role}
                    onChange={(e) => {
                      set('role', e.target.value);
                      setActiveStep(2);
                    }}
                    className="input"
                  >
                    {ROLES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Başlangıç Tarihi" required>
                  <input
                    type="date"
                    value={form.start_date}
                    onChange={(e) => set('start_date', e.target.value)}
                    className="input"
                  />
                </Field>
              </Row>

              <GorevHakedis
                form={form}
                set={set}
                restaurants={restaurants}
                selectedRest={selectedRest}
              />
            </Section>

            {/* 3. ARAÇ */}
            <Section id="pp-step-3" icon="🛵" title="Araç Bilgisi">
              <ArayCard
                value={form.vehicle_type}
                onChange={(v) => {
                  set('vehicle_type', v);
                  setActiveStep(3);
                }}
              />

              <Field label="Plaka" required>
                <input
                  value={form.current_plate}
                  onChange={(e) =>
                    set('current_plate', e.target.value.toUpperCase())
                  }
                  placeholder="34 NFE 437"
                  className="input num"
                />
              </Field>

              {form.vehicle_type === 'Çat Kapında Kiralık' && (
                <>
                  <Banner color="brand" icon="i">
                    Kira <strong>işe giriş tarihinden itibaren</strong> başlar —
                    ayrıca tarih girmeniz gerekmez. Bakım maliyetlerini Çat
                    Kapında karşılar.
                  </Banner>
                  <Field label="Aylık Kira" optional hint="bilgi amaçlı · şirket maliyeti">
                    <NumberSuffix
                      value={form.motor_rental_monthly_amount}
                      onChange={(v) => set('motor_rental_monthly_amount', v)}
                      suffix="₺/ay"
                    />
                  </Field>
                </>
              )}

              {form.vehicle_type === 'Çat Kapında Satış' && (
                <>
                  <Banner color="cream" icon="📜">
                    <strong>Taahhüt:</strong> kurye sözleşme süresince aylık
                    taksiti ödemekle yükümlü. PDF hakedişte "Motor Satış Taksidi
                    18/2" gibi gösterilir.
                  </Banner>
                  <Row>
                    <Field label="Aylık Taksit" required>
                      <NumberSuffix
                        value={form.motor_purchase_monthly_amount}
                        onChange={(v) => set('motor_purchase_monthly_amount', v)}
                        suffix="₺/ay"
                      />
                    </Field>
                    <Field label="Taahhüt Süresi" required>
                      <NumberSuffix
                        value={form.motor_purchase_installment_count}
                        onChange={(v) =>
                          set('motor_purchase_installment_count', Math.round(v))
                        }
                        suffix="ay"
                      />
                    </Field>
                  </Row>
                  <Row>
                    <Field label="Sözleşme Başlangıcı" required>
                      <input
                        type="date"
                        value={form.motor_purchase_start_date}
                        onChange={(e) =>
                          set('motor_purchase_start_date', e.target.value)
                        }
                        className="input"
                      />
                    </Field>
                    <Field label="Toplam Satış Bedeli" hint="Bilgi · taksit × süre">
                      <NumberSuffix
                        value={form.motor_purchase_sale_price}
                        onChange={(v) => set('motor_purchase_sale_price', v)}
                        suffix="₺"
                      />
                    </Field>
                  </Row>
                </>
              )}

              {form.vehicle_type === 'Kendi Motoru' && (
                <Banner color="gray" icon="i">
                  Kendi motoruyla çalışan kurye — bakım kuryeye aittir, ÇK
                  kira/taksit kesmez.
                </Banner>
              )}
            </Section>

            {/* 4. MUHASEBE */}
            <Section id="pp-step-4" icon="📋" title="Muhasebe & Vergi">
              <Row>
                <Field label="Muhasebe Tipi" required>
                  <select
                    value={form.accounting_type}
                    onChange={(e) => {
                      set('accounting_type', e.target.value);
                      setActiveStep(4);
                    }}
                    className="input"
                  >
                    <option value="Çat Kapında Muhasebe">Çat Kapında Muhasebe</option>
                    <option value="Kendi Muhasebecisi">Kendi Muhasebecisi</option>
                  </select>
                </Field>
                <Field label="Muhasebe Geçiş Tarihi" optional hint="Önceki muhasebeciden geçtiyse">
                  <input
                    type="date"
                    value={form.accounting_effective_date}
                    onChange={(e) =>
                      set('accounting_effective_date', e.target.value)
                    }
                    className="input"
                  />
                </Field>
              </Row>
              <Row>
                <Field label="Vergi Dairesi" required>
                  <input
                    value={form.tax_office}
                    onChange={(e) => set('tax_office', e.target.value)}
                    placeholder="Örn. Sarıgazi VD"
                    className="input"
                  />
                </Field>
                <Field label="Vergi Numarası" required>
                  <input
                    value={form.tax_number}
                    onChange={(e) => set('tax_number', e.target.value)}
                    placeholder="10 hane"
                    className="input num"
                  />
                </Field>
              </Row>

              {form.accounting_type === 'Çat Kapında Muhasebe' && (
                <>
                  <Field
                    label="Aylık Muhasebe Bedeli"
                    optional
                    hint="kuryeye yansıyan · her ay otomatik düşer"
                  >
                    <NumberSuffix
                      value={form.accountant_cost}
                      onChange={(v) => set('accountant_cost', v)}
                      suffix="₺/ay"
                    />
                  </Field>
                  <Field
                    label="Aylık Muhasebe Geliri"
                    optional
                    hint="bana kalan kar"
                  >
                    <NumberSuffix
                      value={form.accounting_revenue}
                      onChange={(v) => set('accounting_revenue', v)}
                      suffix="₺/ay"
                    />
                  </Field>

                  <ToggleCard
                    on={form.new_company_setup === 'Evet'}
                    onChange={(on) =>
                      set('new_company_setup', on ? 'Evet' : 'Hayır')
                    }
                    title="Şirket açılışı yapılacak / yapıldı"
                    sub="Tek seferlik bedel kuryenin hakedişinden düşülür"
                  />

                  {form.new_company_setup === 'Evet' && (
                    <div className="bg-bg-surface2/50 border border-border rounded-xl p-3 space-y-3">
                      <Row>
                        <Field
                          label="Şirket Açılış Bedeli"
                          hint="kuryeden alınan"
                        >
                          <NumberSuffix
                            value={form.company_setup_cost}
                            onChange={(v) => set('company_setup_cost', v)}
                            suffix="₺"
                          />
                        </Field>
                        <Field label="Şirket Açılış Geliri" hint="bana kalan">
                          <NumberSuffix
                            value={form.company_setup_revenue}
                            onChange={(v) => set('company_setup_revenue', v)}
                            suffix="₺"
                          />
                        </Field>
                      </Row>
                      <Field label="Şirket Açılış Tarihi">
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
                </>
              )}
            </Section>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
                {error}
              </div>
            )}
          </div>

          {/* SIDE — Canlı Hesap */}
          <aside className="bg-cream-50 border-l border-border p-5 overflow-y-auto">
            <div className="text-[10.5px] font-semibold text-text-3 uppercase tracking-wider mb-3">
              📊 Canlı Hesap
            </div>

            {/* Avatar preview */}
            <div className="flex items-center gap-2.5 p-3 bg-bg-surface border border-border rounded-md mb-4">
              <div className="w-11 h-11 rounded-full bg-gradient-to-br from-brand-dark to-brand text-white font-bold flex items-center justify-center text-base">
                {initials || 'YP'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-semibold text-text truncate">
                  {form.full_name || 'Yeni Personel'}
                </div>
                <div className="text-[11px] text-text-3 truncate">
                  {form.person_code || '—'} · {form.role}
                </div>
              </div>
            </div>

            {/* Net donut */}
            <Donut
              value={liveCalc.net}
              label="Tahmini Net"
            />

            {/* Live summary */}
            <div className="space-y-0">
              <SummaryRow label="Tip" small>
                {liveCalc.dealLabel}
              </SummaryRow>
              <SummaryRow label="Tahmini brüt" plus>
                {tr(liveCalc.gross)} ₺
              </SummaryRow>
              {liveCalc.kaptanBonus > 0 && (
                <SummaryRow label="+ Kaptan bonusu" plus>
                  +{tr(liveCalc.kaptanBonus)} ₺
                </SummaryRow>
              )}
              {liveCalc.motorDed > 0 && (
                <SummaryRow label="− Motor" minus>
                  −{tr(liveCalc.motorDed)} ₺
                </SummaryRow>
              )}
              {liveCalc.accDed > 0 && (
                <SummaryRow label="− Muhasebe" minus>
                  −{tr(liveCalc.accDed)} ₺
                </SummaryRow>
              )}
              {liveCalc.setupDed > 0 && (
                <SummaryRow label="− Şirket açılışı (1×)" minus>
                  −{tr(liveCalc.setupDed)} ₺
                </SummaryRow>
              )}
              <div className="flex justify-between pt-3 mt-1 border-t-2 border-text font-display font-bold text-brand">
                <span className="text-[13px]">Net Aylık</span>
                <span className="text-[14px] num">{tr(liveCalc.net)} ₺</span>
              </div>
            </div>

            <div className="bg-brand-soft/60 border border-brand/15 rounded-lg p-2.5 mt-4 text-[11px] text-text-2 leading-relaxed">
              <strong className="text-brand">ⓘ</strong> 180 saat · 350 paket
              varsayımıyla. Yakıt, bakım, avans gibi değişken kesintiler aya
              göre değişir.
            </div>
          </aside>
        </div>

        {/* FOOT */}
        <div className="px-7 py-3.5 border-t border-border flex justify-end gap-2 bg-cream-50">
          <button
            type="button"
            onClick={handleClose}
            className="px-3.5 py-2 rounded-lg text-sm font-medium text-text-2 border border-border bg-bg-surface hover:bg-bg-surface2 transition"
            disabled={saving}
          >
            İptal
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving || !form.full_name.trim()}
            className="px-4 py-2 rounded-lg text-sm font-semibold bg-brand text-white shadow-sm hover:bg-brand-dark transition disabled:opacity-60"
          >
            {saving
              ? 'Kaydediliyor…'
              : mode === 'create'
              ? 'Personeli Kaydet'
              : 'Değişiklikleri Kaydet'}
          </button>
        </div>
      </div>

      <style jsx>{`
        :global(.input) {
          width: 100%;
          padding: 9px 12px;
          border-radius: 10px;
          border: 1px solid var(--border, #E2E5EC);
          background: var(--bg-surface, #FFFFFF);
          font-size: 13.5px;
          color: var(--text, #0B0D17);
          font-family: inherit;
          transition: border-color 0.15s, box-shadow 0.15s;
        }
        :global(.input:focus) {
          outline: none;
          border-color: #0F52BA;
          box-shadow: 0 0 0 3px rgba(15, 82, 186, 0.12);
        }
      `}</style>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────
// Görev & Hakediş bölümü (rol/restoran bazlı)
// ─────────────────────────────────────────────────────────────────

function GorevHakedis({
  form, set, restaurants, selectedRest,
}: {
  form: FormState;
  set: <K extends keyof FormState>(k: K, v: FormState[K]) => void;
  restaurants: Restaurant[];
  selectedRest: Restaurant | null;
}) {
  const role = form.role;
  const needsRestaurant = ['Kurye', 'Kaptan', 'Restoran Takım Şefi'].includes(role);
  const noRestaurant = ['Bölge Müdürü', 'Joker'].includes(role);
  const isFixedRole = ['Bölge Müdürü', 'Joker', 'Restoran Takım Şefi'].includes(role);
  const isKaptan = role === 'Kaptan';
  const restPM = selectedRest?.pricing_model ?? '';

  return (
    <div className="space-y-3.5">
      {/* Sabit aylık alanı — RTŞ/BM/Joker zorunlu */}
      {isFixedRole && (
        <>
          <Banner color="brand" icon="₺">
            <strong>Sabit aylık maaş</strong> — bu rol için manuel maaş tutarı
            girin.
          </Banner>
          <Row>
            <Field label="Kuryeye Ödenen" required hint="net aylık hakediş">
              <NumberSuffix
                value={form.monthly_fixed_cost}
                onChange={(v) => set('monthly_fixed_cost', v)}
                suffix="₺/ay"
                placeholder="örn 72050"
              />
            </Field>
            <Field
              label="Restorana Fatura"
              hint="KDV hariç · +%20 ile kesilir"
              optional={role !== 'Restoran Takım Şefi'}
              required={role === 'Restoran Takım Şefi'}
            >
              <NumberSuffix
                value={form.fixed_monthly_billing}
                onChange={(v) => set('fixed_monthly_billing', v)}
                suffix="₺/ay"
                placeholder="örn 84500"
              />
            </Field>
          </Row>

          {/* Canlı KDV dahil + kar göstergesi */}
          {form.fixed_monthly_billing > 0 && (
            <div className="flex flex-wrap gap-2 -mt-1">
              <span className="px-2.5 py-1 rounded-md text-[11.5px] font-semibold bg-brand text-white">
                KDV dahil kesilen fatura ={' '}
                {Math.round(form.fixed_monthly_billing * 1.2).toLocaleString(
                  'tr-TR',
                )}{' '}
                ₺
              </span>
              {form.monthly_fixed_cost > 0 && (
                <span className="px-2.5 py-1 rounded-md text-[11.5px] font-semibold bg-green-50 text-green-700 border border-green-200">
                  Aylık kar ={' '}
                  {Math.round(
                    form.fixed_monthly_billing - form.monthly_fixed_cost,
                  ).toLocaleString('tr-TR')}{' '}
                  ₺
                </span>
              )}
            </div>
          )}
        </>
      )}

      {/* Kaptan bonusu */}
      {isKaptan && (
        <Banner color="success" icon="⭐">
          <strong>Kaptan rolü:</strong> standart kurye gibi saat + paket alır,
          ek olarak <strong>her ay otomatik +3.000 ₺ Kaptan Bonusu</strong>{' '}
          hakedişine eklenir.
        </Banner>
      )}

      {/* Atanan restoran */}
      {needsRestaurant && (
        <Field label="Atanan Restoran" required>
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
            <option value="">— Restoran seçin —</option>
            {restaurants.map((r) => (
              <option key={r.id} value={r.id}>
                {r.brand}
                {r.branch ? ` · ${r.branch}` : ''}
                {r.pricing_model
                  ? ` (${PRICING_LABELS[r.pricing_model] ?? r.pricing_model})`
                  : ''}
              </option>
            ))}
          </select>
        </Field>
      )}

      {/* BM/Joker için bilgi banner */}
      {noRestaurant && (
        <Banner color="cream" icon="🌐">
          <strong>Bu rol bir restorana atanmaz.</strong> Tüm restoranlardan
          sorumludur.
        </Banner>
      )}

      {/* Restoran seçildiyse pricing banner */}
      {needsRestaurant && selectedRest && (
        <>
          {restPM === 'hourly_only' && (
            <Banner color="info" icon="⏱">
              <strong>Sadece Saatlik</strong> anlaşma — restoran tarifesi:{' '}
              <strong>{tr(selectedRest.hourly_rate ?? 0)} ₺/sa</strong> ·
              kuryeye otomatik uygulanır.
            </Banner>
          )}
          {restPM === 'hourly_plus_package' && (
            <Banner color="amber" icon="+">
              <strong>Saat + Prim</strong> anlaşma — saatlik{' '}
              <strong>{tr(selectedRest.hourly_rate ?? 0)} ₺/sa</strong> + paket{' '}
              <strong>{tr(selectedRest.package_rate ?? 0)} ₺/pkt</strong> ·
              kuryeye otomatik uygulanır.
            </Banner>
          )}
          {restPM === 'threshold_package' && (
            <Banner color="terra" icon="≷">
              <strong>Eşikli (390 paket)</strong> — saat{' '}
              <strong>{tr(selectedRest.hourly_rate ?? 0)} ₺/sa</strong>; ≤390{' '}
              <strong>{tr(selectedRest.package_rate_low ?? 0)} ₺/pkt</strong> ·
              &gt;390{' '}
              <strong>{tr(selectedRest.package_rate_high ?? 0)} ₺/pkt</strong>{' '}
              tüm paketlere uygulanır.
            </Banner>
          )}
          {restPM === 'fixed_monthly' && (
            <Banner color="success" icon="∞">
              <strong>Aylık Sabit</strong> anlaşma — restoran tutar:{' '}
              <strong>{tr(selectedRest.fixed_monthly_fee ?? 0)} ₺/ay</strong>.
              Kuryenin sabit aylık tutarını aşağıdan girin.
            </Banner>
          )}

          {/* Aylık sabit anlaşmalı restoranda kurye için sabit tutar */}
          {restPM === 'fixed_monthly' && !isFixedRole && (
            <Field
              label="Kuryeye Ödenen Aylık"
              required
              hint="restoran sabit anlaşmalı · kurye net aylık"
            >
              <NumberSuffix
                value={form.monthly_fixed_cost}
                onChange={(v) => set('monthly_fixed_cost', v)}
                suffix="₺/ay"
                placeholder="örn 73600"
              />
            </Field>
          )}
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Yardımcı bileşenler
// ─────────────────────────────────────────────────────────────────

function Section({
  id, icon, title, children,
}: {
  id?: string;
  icon: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="space-y-3 scroll-mt-2">
      <div className="text-[12px] font-bold text-text-3 uppercase tracking-[0.06em] flex items-center gap-2">
        <span className="text-base">{icon}</span>
        <span>{title}</span>
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-3">{children}</div>;
}

function Field({
  label, required, optional, hint, children,
}: {
  label: string;
  required?: boolean;
  optional?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[12px] font-semibold text-text-2">{label}</span>
        {required && <span className="text-red-500 text-[11px]">*</span>}
        {optional && (
          <span className="text-text-3 text-[11px] font-medium">opsiyonel</span>
        )}
      </div>
      {children}
      {hint && (
        <div className="text-[11px] text-text-3 mt-1">{hint}</div>
      )}
    </label>
  );
}

function NumberSuffix({
  value, onChange, suffix, placeholder,
}: {
  value: number;
  onChange: (v: number) => void;
  suffix: string;
  placeholder?: string;
}) {
  return (
    <div className="relative">
      <input
        type="number"
        step="any"
        value={value || ''}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        placeholder={placeholder ?? '0'}
        className="input num"
        style={{ paddingRight: 44 }}
      />
      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-text-3 text-[12px] font-semibold pointer-events-none num">
        {suffix}
      </span>
    </div>
  );
}

const BANNER_STYLES: Record<
  string,
  { bg: string; border: string; iconBg: string; iconColor: string }
> = {
  brand: {
    bg: 'bg-brand-soft/60',
    border: 'border-brand/20',
    iconBg: 'bg-brand',
    iconColor: 'text-white',
  },
  amber: {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    iconBg: 'bg-orange-600',
    iconColor: 'text-white',
  },
  terra: {
    bg: 'bg-cream-100',
    border: 'border-yellow-300',
    iconBg: 'bg-yellow-700',
    iconColor: 'text-white',
  },
  cream: {
    bg: 'bg-cream-100',
    border: 'border-yellow-200',
    iconBg: 'bg-yellow-600',
    iconColor: 'text-white',
  },
  success: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    iconBg: 'bg-green-600',
    iconColor: 'text-white',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    iconBg: 'bg-blue-500',
    iconColor: 'text-white',
  },
  gray: {
    bg: 'bg-bg-surface2',
    border: 'border-border',
    iconBg: 'bg-text-3',
    iconColor: 'text-white',
  },
};

function Banner({
  color = 'brand', icon, children,
}: {
  color?: keyof typeof BANNER_STYLES;
  icon: string;
  children: React.ReactNode;
}) {
  const s = BANNER_STYLES[color] ?? BANNER_STYLES.brand;
  return (
    <div
      className={`flex gap-2.5 items-start ${s.bg} border ${s.border} rounded-xl p-3 text-[12.5px] text-text-2 leading-relaxed`}
    >
      <div
        className={`w-7 h-7 ${s.iconBg} ${s.iconColor} rounded-md flex items-center justify-center flex-shrink-0 font-bold text-[13px]`}
      >
        {icon}
      </div>
      <div>{children}</div>
    </div>
  );
}

function ArayCard({
  value, onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const items = [
    {
      v: 'Çat Kapında Kiralık',
      title: 'Çat Kapında Kiralık',
      sub: 'Aylık kira · ÇK öder bakım · plaka bizden',
    },
    {
      v: 'Çat Kapında Satış',
      title: 'Çat Kapında Satış',
      sub: 'Taksit + taahhüt · bakım kuryede',
    },
    {
      v: 'Kendi Motoru',
      title: 'Kendi Motoru',
      sub: 'Bakım kuryede',
    },
  ];
  return (
    <div className="grid grid-cols-3 gap-2">
      {items.map((it) => {
        const active = value === it.v;
        return (
          <button
            key={it.v}
            type="button"
            onClick={() => onChange(it.v)}
            className={`text-left p-3 rounded-md border-[1.5px] transition ${
              active
                ? 'border-brand bg-brand-soft shadow-[0_0_0_3px_rgba(15,82,186,0.1)]'
                : 'border-border hover:border-brand/40 bg-bg-surface'
            }`}
          >
            <div className="font-semibold text-[12.5px] text-text">
              {it.title}
            </div>
            <div className="text-[11px] text-text-3 mt-0.5 leading-tight">
              {it.sub}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function ToggleCard({
  on, onChange, title, sub,
}: {
  on: boolean;
  onChange: (on: boolean) => void;
  title: string;
  sub: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!on)}
      className={`w-full text-left flex gap-2.5 items-start p-3 rounded-md border-[1.5px] transition ${
        on
          ? 'border-brand bg-brand-soft'
          : 'border-border bg-bg-surface hover:border-border'
      }`}
    >
      <div
        className={`w-9 h-[22px] rounded-full transition relative flex-shrink-0 mt-0.5 ${
          on ? 'bg-brand' : 'bg-bg-surface2'
        }`}
      >
        <div
          className={`absolute top-0.5 w-[18px] h-[18px] bg-white rounded-full shadow-sm transition-transform ${
            on ? 'translate-x-[16px]' : 'translate-x-0.5'
          }`}
        />
      </div>
      <div>
        <div className="text-[13px] font-semibold text-text">{title}</div>
        <div className="text-[11.5px] text-text-3 mt-0.5">{sub}</div>
      </div>
    </button>
  );
}

function Donut({ value, label }: { value: number; label: string }) {
  // SVG donut — net pozitifse mavi, negatifse kırmızı
  const positive = value >= 0;
  const r = 60;
  const circumference = 2 * Math.PI * r;
  const fillRatio = Math.min(Math.abs(value) / 100000, 1);
  const offset = circumference * (1 - fillRatio);

  return (
    <div className="relative h-[160px] mb-4 flex items-center justify-center">
      <svg width="160" height="160" viewBox="0 0 160 160">
        <circle
          cx="80"
          cy="80"
          r={r}
          fill="none"
          stroke="rgba(15,82,186,0.08)"
          strokeWidth="14"
        />
        <circle
          cx="80"
          cy="80"
          r={r}
          fill="none"
          stroke={positive ? '#0F52BA' : '#EF4444'}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 80 80)"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-[10px] text-text-3 uppercase tracking-wider font-semibold">
          {label}
        </div>
        <div
          className={`font-display text-[18px] font-bold mt-1 num ${
            positive ? 'text-brand' : 'text-red-500'
          }`}
        >
          {tr(value)}
        </div>
        <div className="text-[10px] text-text-3">₺/ay</div>
      </div>
    </div>
  );
}

function SummaryRow({
  label, children, plus, minus, small,
}: {
  label: string;
  children: React.ReactNode;
  plus?: boolean;
  minus?: boolean;
  small?: boolean;
}) {
  return (
    <div className="flex justify-between py-2 border-b border-dashed border-border last:border-b-0 text-[12.5px] text-text-2">
      <span>{label}</span>
      <span
        className={`num font-semibold ${
          plus ? 'text-green-700' : minus ? 'text-red-500' : 'text-text'
        } ${small ? 'text-[11px] font-medium' : ''}`}
      >
        {children}
      </span>
    </div>
  );
}

function tr(value: number): string {
  if (!value && value !== 0) return '—';
  return Math.round(value).toLocaleString('tr-TR');
}
