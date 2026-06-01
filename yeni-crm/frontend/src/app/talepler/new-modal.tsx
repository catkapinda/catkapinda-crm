'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle, Bike, Calculator, Check, Search, X,
  type LucideIcon,
} from 'lucide-react';

import {
  type Personnel,
  createCourierRequest,
} from '@/lib/api';

// Avans talepleri artık kuryeler tarafından kurye portalı üzerinden
// gönderiliyor (/avans-talepleri sayfasında ayrı listeleniyor).
// Bu modal sadece Motor + Muhasebe Değişikliği için kullanılır.
const TYPES: { key: ReqType; label: string; Icon: LucideIcon; accent: 'orange' | 'purple'; hint: string }[] = [
  { key: 'Motor Değişikliği', label: 'Motor Değişikliği', Icon: Bike, accent: 'orange', hint: 'ÇK Kiralık ↔ Kendi Motoru ↔ ÇK Satış geçişleri (kaza/arıza vb.).' },
  { key: 'Muhasebe Değişimi', label: 'Muhasebe Değişimi', Icon: Calculator, accent: 'purple', hint: 'Kendi Muhasebecisi ↔ Çat Kapında Muhasebe geçişi.' },
];

type ReqType = 'Motor Değişikliği' | 'Muhasebe Değişimi';

const VEHICLE_OPTIONS = [
  'Çat Kapında Kiralık',
  'Çat Kapında Satış',
  'Kendi Motoru',
] as const;

const VEHICLE_REASONS = [
  'Kaza',
  'Arıza',
  'Bakım',
  'Eskime / Yıpranma',
  'Kişisel Talep',
  'Diğer',
] as const;

const ACCOUNTING_OPTIONS = [
  'Çat Kapında Muhasebe',
  'Kendi Muhasebecisi',
] as const;

const ACCENT_STYLES: Record<string, { ring: string; bg: string; iconBg: string; iconText: string }> = {
  green: {
    ring: 'border-green-500 ring-2 ring-green-200',
    bg: 'bg-green-50',
    iconBg: 'bg-green-100',
    iconText: 'text-green-700',
  },
  orange: {
    ring: 'border-orange-500 ring-2 ring-orange-200',
    bg: 'bg-orange-50',
    iconBg: 'bg-orange-100',
    iconText: 'text-orange-700',
  },
  purple: {
    ring: 'border-purple-500 ring-2 ring-purple-200',
    bg: 'bg-purple-50',
    iconBg: 'bg-purple-100',
    iconText: 'text-purple-700',
  },
};

export function NewRequestModal({
  personnel, onClose, onCreated,
}: {
  personnel: Personnel[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [type, setType] = useState<ReqType>('Motor Değişikliği');
  const [personnelId, setPersonnelId] = useState<number | null>(null);
  const [personnelSearch, setPersonnelSearch] = useState('');
  // Genel
  const [reason, setReason] = useState('');
  // Motor
  const [vehicleFrom, setVehicleFrom] = useState<string>('');
  const [vehicleTo, setVehicleTo] = useState<string>('');
  const [vehicleReason, setVehicleReason] = useState<string>('');
  const [plate, setPlate] = useState<string>('');
  // Muhasebe
  const [accountingFrom, setAccountingFrom] = useState<string>('');
  const [accountingTo, setAccountingTo] = useState<string>('');
  // Geçerlilik tarihi (motor/muhasebe yürürlük — bordro orantısı için)
  const [effectiveDate, setEffectiveDate] = useState<string>(
    () => new Date().toISOString().slice(0, 10),
  );

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ESC ile kapat + body scroll lock
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

  const filteredPersonnel = useMemo(() => {
    const q = personnelSearch.trim().toLocaleLowerCase('tr-TR');
    let list = [...personnel];
    if (q) {
      list = list.filter((p) => {
        const hay = `${p.full_name ?? ''} ${p.person_code ?? ''} ${p.role ?? ''}`
          .toLocaleLowerCase('tr-TR');
        return hay.includes(q);
      });
    }
    return list.slice(0, 30);
  }, [personnel, personnelSearch]);

  const selectedPersonnel = useMemo(
    () => personnel.find((p) => p.id === personnelId) ?? null,
    [personnel, personnelId],
  );

  // Personel seçilince motor/muhasebe için "from" alanlarını otomatik doldur
  useEffect(() => {
    if (!selectedPersonnel) return;
    if (type === 'Motor Değişikliği' && !vehicleFrom && selectedPersonnel.vehicle_type) {
      setVehicleFrom(selectedPersonnel.vehicle_type);
    }
    if (type === 'Motor Değişikliği' && !plate && selectedPersonnel.current_plate) {
      setPlate(selectedPersonnel.current_plate);
    }
    if (type === 'Muhasebe Değişimi' && !accountingFrom && selectedPersonnel.accounting_type) {
      setAccountingFrom(selectedPersonnel.accounting_type);
    }
  }, [selectedPersonnel, type, vehicleFrom, plate, accountingFrom]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!personnelId) {
      setError('Lütfen bir kurye seç');
      return;
    }
    if (type === 'Motor Değişikliği') {
      if (!vehicleFrom || !vehicleTo) {
        setError('Mevcut ve yeni araç tipini seç');
        return;
      }
      if (vehicleFrom === vehicleTo) {
        setError('Mevcut ve yeni araç tipi farklı olmalı (aynı tip seçildi). Kiralık → kiralık değişimi için neden "Kaza/Arıza" girilebilir.');
      }
      if (!vehicleReason) {
        setError('Değişiklik nedenini seç');
        return;
      }
    }
    if (type === 'Muhasebe Değişimi') {
      if (!accountingFrom || !accountingTo) {
        setError('Mevcut ve yeni muhasebe tipini seç');
        return;
      }
      if (accountingFrom === accountingTo) {
        setError('Mevcut ve yeni muhasebe tipi aynı olamaz');
        return;
      }
    }
    if (!effectiveDate) {
      setError('Geçerlilik tarihini gir (bordro hesabı bu tarihten itibaren yapılır)');
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await createCourierRequest({
        personnel_id: personnelId,
        request_type: type,
        amount: 0,
        reason: reason.trim() || null,
        effective_date: effectiveDate || null,
        ...(type === 'Motor Değişikliği' && {
          vehicle_from: vehicleFrom,
          vehicle_to: vehicleTo,
          vehicle_reason: vehicleReason,
          plate: plate.trim().toUpperCase() || null,
        }),
        ...(type === 'Muhasebe Değişimi' && {
          accounting_from: accountingFrom,
          accounting_to: accountingTo,
        }),
      });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Talep oluşturulamadı');
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-text/40 backdrop-blur-sm flex items-start justify-center pt-12 pb-8 px-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-2xl shadow-xl border border-border w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* HEADER */}
        <div className="flex items-center justify-between p-5 border-b border-border bg-gradient-to-r from-cream-50 to-white">
          <div>
            <div className="font-display text-[20px] font-semibold tracking-tight">
              Yeni Talep Oluştur
            </div>
            <div className="text-[12.5px] text-text-3 mt-0.5">
              {type === 'Motor Değişikliği' && 'Araç tipi değişikliği (kiralık ↔ kendi ↔ satış)'}
              {type === 'Muhasebe Değişimi' && 'Muhasebe sağlayıcı değişikliği'}
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-bg-surface2 transition flex items-center justify-center text-text-3 hover:text-text"
          >
            <X className="w-5 h-5" strokeWidth={2.2} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* 1. TIP SEÇIMI */}
          <div>
            <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
              1. Talep Tipi
            </div>
            <div className="grid grid-cols-3 gap-2">
              {TYPES.map((t) => {
                const active = type === t.key;
                const s = ACCENT_STYLES[t.accent];
                return (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setType(t.key)}
                    className={`p-3 rounded-xl border-2 text-left transition ${
                      active
                        ? `${s.ring} ${s.bg}`
                        : 'border-border bg-white hover:border-border-strong'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${s.iconBg} ${s.iconText}`}>
                      <t.Icon className="w-4 h-4" strokeWidth={2.2} />
                    </div>
                    <div className="font-semibold text-[13px] text-text">{t.label}</div>
                    <div className="text-[11px] text-text-3 mt-0.5 leading-snug">{t.hint}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. KURYE SEÇİMİ */}
          <div>
            <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
              2. Kurye Seç
            </div>
            <div className="border border-border rounded-xl bg-white overflow-hidden">
              <div className="relative flex items-center border-b border-border">
                <Search className="w-4 h-4 absolute left-3 text-text-3" strokeWidth={2.2} />
                <input
                  type="search"
                  placeholder="Ad, kod ya da role göre ara…"
                  value={personnelSearch}
                  onChange={(e) => setPersonnelSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-2.5 text-sm focus:outline-none"
                />
              </div>
              <div className="max-h-44 overflow-y-auto">
                {filteredPersonnel.length === 0 ? (
                  <div className="p-4 text-center text-text-3 text-sm">Sonuç yok</div>
                ) : (
                  filteredPersonnel.map((p) => {
                    const active = personnelId === p.id;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setPersonnelId(p.id)}
                        className={`w-full px-3 py-2 text-left text-[13px] flex items-center gap-2 border-b border-border last:border-b-0 transition ${
                          active ? 'bg-brand-soft text-brand' : 'hover:bg-cream-50'
                        }`}
                      >
                        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                          active ? 'border-brand bg-brand' : 'border-border'
                        }`}>
                          {active && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
                        </div>
                        <span className="font-mono text-[10.5px] text-text-3">{p.person_code}</span>
                        <span className="font-medium truncate flex-1">{p.full_name}</span>
                        <span className="text-[10.5px] text-text-3 truncate">{p.role}</span>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
            {selectedPersonnel && (
              <div className="text-[11.5px] text-brand mt-1.5 font-medium">
                Seçili: <strong>{selectedPersonnel.full_name}</strong> ({selectedPersonnel.person_code})
                {type === 'Motor Değişikliği' && selectedPersonnel.vehicle_type && (
                  <span className="text-text-3 ml-2">
                    · mevcut: <strong>{selectedPersonnel.vehicle_type}</strong>
                    {selectedPersonnel.current_plate && ` · ${selectedPersonnel.current_plate}`}
                  </span>
                )}
                {type === 'Muhasebe Değişimi' && selectedPersonnel.accounting_type && (
                  <span className="text-text-3 ml-2">
                    · mevcut: <strong>{selectedPersonnel.accounting_type}</strong>
                  </span>
                )}
              </div>
            )}
          </div>

          {/* 3. TIPE ÖZEL FIELDS */}
          {type === 'Motor Değişikliği' && (
            <div className="space-y-3">
              <div>
                <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
                  3. Araç Geçişi
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <SelectField
                    label="Mevcut Araç"
                    value={vehicleFrom}
                    onChange={setVehicleFrom}
                    options={VEHICLE_OPTIONS}
                  />
                  <SelectField
                    label="Yeni Araç"
                    value={vehicleTo}
                    onChange={setVehicleTo}
                    options={VEHICLE_OPTIONS}
                  />
                </div>
              </div>

              <div>
                <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
                  4. Değişiklik Nedeni
                </div>
                <div className="grid grid-cols-3 gap-1.5">
                  {VEHICLE_REASONS.map((r) => {
                    const active = vehicleReason === r;
                    return (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setVehicleReason(r)}
                        className={`px-3 py-2 rounded-lg border-[1.5px] text-[12px] font-semibold transition ${
                          active
                            ? 'border-orange-500 bg-orange-50 text-orange-700'
                            : 'border-border bg-white text-text-2 hover:border-border-strong'
                        }`}
                      >
                        {r}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
                  5. Plaka
                </div>
                <input
                  type="text"
                  placeholder="34 ABC 123"
                  value={plate}
                  onChange={(e) => setPlate(e.target.value.toUpperCase())}
                  maxLength={20}
                  className="w-full px-3 py-2.5 rounded-xl border border-border text-[14px] font-mono focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition uppercase"
                />
                <div className="text-[11px] text-text-3 mt-1">
                  Mevcut motorun plakası (otomatik dolduruldu — gerekirse değiştir).
                </div>
              </div>
            </div>
          )}

          {type === 'Muhasebe Değişimi' && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
                3. Muhasebe Geçişi
              </div>
              <div className="grid grid-cols-2 gap-2">
                <SelectField
                  label="Mevcut Muhasebe"
                  value={accountingFrom}
                  onChange={setAccountingFrom}
                  options={ACCOUNTING_OPTIONS}
                />
                <SelectField
                  label="Yeni Muhasebe"
                  value={accountingTo}
                  onChange={setAccountingTo}
                  options={ACCOUNTING_OPTIONS}
                />
              </div>
              {accountingFrom && accountingTo && accountingFrom !== accountingTo && (
                <div className="text-[11.5px] text-purple-700 mt-2 font-medium bg-purple-50 border border-purple-200 rounded-lg px-3 py-2">
                  <strong>{accountingFrom}</strong> → <strong>{accountingTo}</strong> geçişi.
                  {accountingTo === 'Çat Kapında Muhasebe' && ' Aylık muhasebe bedeli kuryeden kesilmeye başlar.'}
                  {accountingTo === 'Kendi Muhasebecisi' && ' ÇK Muhasebe bedeli kesilmez; kurye kendi mali müşaviriyle çalışır.'}
                </div>
              )}
            </div>
          )}

          {/* GEÇERLİLİK TARİHİ */}
          <div>
            <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
              {type === 'Motor Değişikliği' ? '6. Geçerlilik Tarihi' : '4. Geçerlilik Tarihi'}
            </div>
            <input
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-border text-[14px] focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
            />
            <div className="text-[11px] text-text-3 mt-1 leading-snug">
              {type === 'Motor Değişikliği' ? (
                <>
                  Değişikliğin yürürlük günü. Onaylanınca bordro bu tarihten
                  itibaren hesaplanır:{' '}
                  {vehicleTo === 'Kendi Motoru'
                    ? 'mevcut kira/satış bu güne kadar gün bazlı kesilir (motor bitiş tarihi).'
                    : vehicleTo === 'Çat Kapında Kiralık'
                    ? 'kira bu tarihten itibaren gün bazlı başlar.'
                    : vehicleTo === 'Çat Kapında Satış'
                    ? 'satış taksiti bu tarihten itibaren başlar.'
                    : 'yeni araç tipini seçince ne olacağı burada görünür.'}
                </>
              ) : (
                'Muhasebe geçişinin yürürlük günü. Onaylanınca bu tarihten itibaren geçerli olur.'
              )}
            </div>
          </div>

          {/* GENEL AÇIKLAMA */}
          <div>
            <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
              {type === 'Motor Değişikliği' ? '7. Ek Not (opsiyonel)' : '5. Açıklama (opsiyonel)'}
            </div>
            <textarea
              placeholder={
                type === 'Motor Değişikliği'
                  ? 'Hasar detayı, atölye notu, vs.'
                  : 'Geçiş gerekçesi, talep eden kişi notu, vs.'
              }
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              className="w-full px-3 py-2.5 rounded-xl border border-border text-sm focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition resize-none"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" strokeWidth={2.2} />
              <span>{error}</span>
            </div>
          )}
        </form>

        {/* FOOTER */}
        <div className="border-t border-border p-4 flex justify-end gap-2 bg-cream-50">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="px-4 py-2 rounded-xl bg-white border border-border text-text-2 text-[13px] font-medium hover:border-border-strong transition disabled:opacity-50"
          >
            İptal
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={busy || !personnelId}
            className="px-5 py-2 rounded-xl bg-brand text-white text-[13px] font-semibold shadow-sm hover:bg-brand-dark transition disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            <Check className="w-4 h-4" strokeWidth={2.4} />
            {busy ? 'Oluşturuluyor…' : 'Talep Oluştur'}
          </button>
        </div>
      </div>
    </div>
  );
}

function SelectField({
  label, value, onChange, options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
}) {
  return (
    <label className="block">
      <div className="text-[10.5px] text-text-3 font-semibold uppercase tracking-wider mb-1">
        {label}
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2.5 rounded-xl border border-border text-[13px] focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
      >
        <option value="">— seçin —</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </label>
  );
}
