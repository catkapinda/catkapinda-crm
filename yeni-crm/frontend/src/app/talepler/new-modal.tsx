'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Banknote, Bike, Calculator, Check, Search, X,
} from 'lucide-react';

import {
  type Personnel,
  createCourierRequest,
} from '@/lib/api';

const TYPES = [
  { key: 'Avans', label: 'Avans', Icon: Banknote, accent: 'green' as const, hint: 'Kuryenin maaşından kesilecek geçici nakit avansı.' },
  { key: 'Motor Değişikliği', label: 'Motor Değişikliği', Icon: Bike, accent: 'orange' as const, hint: 'Çat Kapında kiralık/satış motor değişiklik talebi.' },
  { key: 'Muhasebe Değişimi', label: 'Muhasebe Değişimi', Icon: Calculator, accent: 'purple' as const, hint: 'Kendi Muhasebecisi ↔ Çat Kapında Muhasebe geçiş talebi.' },
] as const;

type ReqType = (typeof TYPES)[number]['key'];

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
  const [type, setType] = useState<ReqType>('Avans');
  const [personnelId, setPersonnelId] = useState<number | null>(null);
  const [personnelSearch, setPersonnelSearch] = useState('');
  const [amount, setAmount] = useState<string>('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

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
    return list.slice(0, 30); // İlk 30
  }, [personnel, personnelSearch]);

  const selectedPersonnel = useMemo(
    () => personnel.find((p) => p.id === personnelId) ?? null,
    [personnel, personnelId],
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!personnelId) {
      setError('Lütfen bir kurye seç');
      return;
    }
    if (type === 'Avans') {
      const amt = parseFloat(amount);
      if (isNaN(amt) || amt <= 0) {
        setError('Avans tutarı 0\'dan büyük olmalı');
        return;
      }
    }
    setBusy(true);
    setError(null);
    try {
      await createCourierRequest({
        personnel_id: personnelId,
        request_type: type,
        amount: type === 'Avans' ? parseFloat(amount) : 0,
        reason: reason.trim() || null,
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
      <div
        ref={dialogRef}
        className="bg-white rounded-2xl shadow-xl border border-border w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden"
      >
        {/* HEADER */}
        <div className="flex items-center justify-between p-5 border-b border-border bg-gradient-to-r from-cream-50 to-white">
          <div>
            <div className="font-display text-[20px] font-semibold tracking-tight">
              Yeni Talep Oluştur
            </div>
            <div className="text-[12.5px] text-text-3 mt-0.5">
              Kurye için avans, motor değişikliği veya muhasebe değişimi talebi
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
              <div className="max-h-48 overflow-y-auto">
                {filteredPersonnel.length === 0 ? (
                  <div className="p-4 text-center text-text-3 text-sm">
                    Sonuç yok
                  </div>
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
                        <span className="font-mono text-[10.5px] text-text-3">
                          {p.person_code}
                        </span>
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
              </div>
            )}
          </div>

          {/* 3. AMOUNT (sadece avans) */}
          {type === 'Avans' && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
                3. Avans Tutarı (₺)
              </div>
              <input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                placeholder="0,00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-border text-[15px] font-mono num focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
              />
              <div className="text-[11px] text-text-3 mt-1">
                Onaylandığında kuryenin bordrosundan otomatik kesilir.
              </div>
            </div>
          )}

          {/* 4. REASON */}
          <div>
            <div className="text-[11px] uppercase tracking-wider text-text-3 font-bold mb-2">
              {type === 'Avans' ? '4. Açıklama (opsiyonel)' : '3. Açıklama'}
            </div>
            <textarea
              placeholder={
                type === 'Avans'
                  ? 'Örn. acil sağlık masrafı'
                  : type === 'Motor Değişikliği'
                  ? 'Mevcut motor durumu ve istenen değişiklik...'
                  : 'Mevcut muhasebe + neden değişiklik isteniyor...'
              }
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className="w-full px-3 py-2.5 rounded-xl border border-border text-sm focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition resize-none"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
              {error}
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
