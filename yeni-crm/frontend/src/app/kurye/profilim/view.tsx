'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle, Camera, Check, ChevronLeft, Clock, Edit3, Mail,
  MapPin, Phone, Shield, ShieldCheck, Trash2, User, UserCircle2, Zap,
} from 'lucide-react';
import Link from 'next/link';

import {
  directUpdateProfile,
  getMyInfo,
  listMyDirectChangeLog,
  listMyProfileChanges,
  submitProfileChange,
  uploadProfilePhoto,
  type CourierMe,
  type DirectChangeLog,
  type ProfileChangeRequest,
} from '@/lib/courier-api';

const FIELD_META: Record<
  string,
  {
    label: string;
    icon: typeof Phone;
    type: 'text' | 'tel' | 'date' | 'select';
    placeholder?: string;
    options?: string[];
    category: 'critical' | 'direct';
    helper?: string;
  }
> = {
  phone: {
    label: 'Telefon',
    icon: Phone,
    type: 'tel',
    placeholder: '0555 555 55 55',
    category: 'critical',
    helper: 'Değişiklik admin onayı sonrası geçerli olur',
  },
  iban: {
    label: 'IBAN',
    icon: Mail,
    type: 'text',
    placeholder: 'TR00 0000 0000 0000 0000 0000 00',
    category: 'critical',
    helper: 'Maaşınız buraya yatar — onay gerekiyor',
  },
  address: {
    label: 'Adres',
    icon: MapPin,
    type: 'text',
    placeholder: 'Açık adresiniz',
    category: 'critical',
    helper: 'Değişiklik admin onayı sonrası geçerli olur',
  },
  emergency_contact_name: {
    label: 'Acil Durum İsim',
    icon: User,
    type: 'text',
    placeholder: 'Yakınınızın adı',
    category: 'direct',
    helper: 'Anında güncellenir',
  },
  emergency_contact_phone: {
    label: 'Acil Durum Telefon',
    icon: Phone,
    type: 'tel',
    placeholder: '0555 000 00 00',
    category: 'direct',
    helper: 'Anında güncellenir',
  },
  birth_date: {
    label: 'Doğum Tarihi',
    icon: Clock,
    type: 'date',
    category: 'direct',
    helper: 'Anında güncellenir',
  },
  tshirt_size: {
    label: 'Tişört Bedeni',
    icon: Edit3,
    type: 'select',
    options: ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'],
    category: 'direct',
    helper: 'Anında güncellenir',
  },
};

const CRITICAL_FIELDS = ['phone', 'iban', 'address'] as const;
const DIRECT_FIELDS = [
  'emergency_contact_name',
  'emergency_contact_phone',
  'birth_date',
  'tshirt_size',
] as const;

function relTime(iso: string | null): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  const diff = Date.now() - t;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return 'az önce';
  if (min < 60) return `${min} dk önce`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} saat önce`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} gün önce`;
  return new Date(iso).toLocaleDateString('tr-TR');
}

function formatValue(field: string, value: string | null): string {
  if (!value) return '—';
  if (field === 'birth_date') {
    try {
      return new Date(value).toLocaleDateString('tr-TR');
    } catch {
      return value;
    }
  }
  return value;
}

export function ProfilimView() {
  const [info, setInfo] = useState<CourierMe | null>(null);
  const [changes, setChanges] = useState<ProfileChangeRequest[]>([]);
  const [directLog, setDirectLog] = useState<DirectChangeLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'edit' | 'history'>('edit');
  const [photoBusy, setPhotoBusy] = useState(false);
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadAll = useCallback(async () => {
    try {
      setError(null);
      const [me, ch, log] = await Promise.all([
        getMyInfo(),
        listMyProfileChanges().catch(() => []),
        listMyDirectChangeLog().catch(() => []),
      ]);
      setInfo(me);
      setChanges(ch);
      setDirectLog(log);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const showToast = (kind: 'ok' | 'err', text: string) => {
    setToast({ kind, text });
    setTimeout(() => setToast(null), 3500);
  };

  const handleSubmitCritical = async (field: string, value: string | null) => {
    await submitProfileChange(field, value);
    showToast('ok', 'Talebiniz admin onayına gönderildi');
    setEditingField(null);
    loadAll();
  };

  const handleSubmitDirect = async (field: string, value: string | null) => {
    await directUpdateProfile(field, value);
    showToast('ok', 'Anında güncellendi');
    setEditingField(null);
    loadAll();
  };

  const handlePhotoChange = async (file: File | null) => {
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) {
      showToast('err', 'Fotoğraf çok büyük (max 4MB)');
      return;
    }
    setPhotoBusy(true);
    try {
      // Resize + compress to ~max 600x600 JPEG
      const dataUrl = await resizeImageToDataUrl(file, 600, 0.85);
      await uploadProfilePhoto(dataUrl);
      showToast('ok', 'Fotoğraf güncellendi');
      loadAll();
    } catch (err) {
      showToast('err', err instanceof Error ? err.message : 'Yüklenemedi');
    } finally {
      setPhotoBusy(false);
    }
  };

  const handlePhotoRemove = async () => {
    if (!confirm('Profil fotoğrafını silmek istediğinize emin misiniz?')) return;
    setPhotoBusy(true);
    try {
      await uploadProfilePhoto(null);
      showToast('ok', 'Fotoğraf silindi');
      loadAll();
    } catch (err) {
      showToast('err', err instanceof Error ? err.message : 'Silinemedi');
    } finally {
      setPhotoBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-slate-200 border-t-blue-600 mb-3" />
          <p className="text-slate-600 text-sm">Profilin yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !info) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-6">
        <div className="max-w-sm rounded-2xl bg-white shadow-lg p-6 text-center border border-red-100">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-2" />
          <h3 className="font-semibold text-slate-900 mb-1">Profil yüklenemedi</h3>
          <p className="text-sm text-slate-600 mb-4">{error || 'Bir hata oluştu'}</p>
          <button
            onClick={() => {
              setLoading(true);
              loadAll();
            }}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Yeniden Dene
          </button>
        </div>
      </div>
    );
  }

  const initials = info.full_name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');

  const pendingCount = changes.filter((c) => c.status === 'Beklemede').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      {/* HEADER bar */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link
            href="/kurye/dashboard"
            className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 transition"
          >
            <ChevronLeft className="w-4 h-4" /> Pano
          </Link>
          <h1 className="font-semibold text-slate-900">Profilim</h1>
          <div className="w-12" /> {/* spacer */}
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">
        {/* HERO — avatar + isim */}
        <div className="bg-gradient-to-br from-blue-600 via-blue-500 to-blue-700 rounded-3xl p-6 text-white shadow-xl relative overflow-hidden">
          {/* Decorative pattern */}
          <div
            className="absolute inset-0 opacity-10"
            style={{
              backgroundImage:
                'radial-gradient(circle at 20% 80%, white 1px, transparent 1px), radial-gradient(circle at 80% 20%, white 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />
          <div className="relative flex items-center gap-4">
            {/* Avatar */}
            <div className="relative flex-shrink-0">
              <div className="w-20 h-20 rounded-2xl overflow-hidden bg-white/15 ring-4 ring-white/30 shadow-lg flex items-center justify-center">
                {info.profile_photo_data ? (
                  <img
                    src={info.profile_photo_data}
                    alt={info.full_name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-2xl font-bold text-white">{initials}</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={photoBusy}
                className="absolute -bottom-1.5 -right-1.5 w-8 h-8 bg-white text-blue-600 rounded-full shadow-lg flex items-center justify-center hover:scale-105 transition disabled:opacity-50"
                title="Fotoğraf yükle"
              >
                <Camera className="w-4 h-4" strokeWidth={2.4} />
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => handlePhotoChange(e.target.files?.[0] ?? null)}
              />
            </div>

            <div className="flex-1 min-w-0">
              <h2 className="font-bold text-2xl truncate">{info.full_name}</h2>
              <p className="text-blue-100 text-sm font-mono">
                {info.person_code} · {info.role}
              </p>
              {info.profile_photo_data && (
                <button
                  onClick={handlePhotoRemove}
                  disabled={photoBusy}
                  className="mt-2 inline-flex items-center gap-1 text-xs text-blue-100 hover:text-white transition disabled:opacity-50"
                >
                  <Trash2 className="w-3 h-3" /> Fotoğrafı sil
                </button>
              )}
            </div>
          </div>

          {/* Status pills */}
          <div className="relative mt-4 flex gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1 bg-white/20 backdrop-blur-sm px-2.5 py-1 rounded-full text-xs font-medium">
              <ShieldCheck className="w-3 h-3" /> {info.status}
            </span>
            {pendingCount > 0 && (
              <span className="inline-flex items-center gap-1 bg-yellow-400 text-yellow-900 px-2.5 py-1 rounded-full text-xs font-bold">
                <Clock className="w-3 h-3" /> {pendingCount} bekleyen talep
              </span>
            )}
          </div>
        </div>

        {/* TABS */}
        <div className="flex gap-1 bg-white rounded-xl p-1 border border-slate-200 shadow-sm">
          <button
            onClick={() => setActiveTab('edit')}
            className={`flex-1 px-4 py-2 rounded-lg text-sm font-semibold transition ${
              activeTab === 'edit'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            Bilgilerim
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 px-4 py-2 rounded-lg text-sm font-semibold transition ${
              activeTab === 'history'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            Geçmiş
            {pendingCount > 0 && (
              <span className="ml-1.5 px-1.5 py-px rounded-full bg-yellow-400 text-yellow-900 text-[10px] font-bold">
                {pendingCount}
              </span>
            )}
          </button>
        </div>

        {activeTab === 'edit' && (
          <>
            {/* DIRECT (anında değişen) */}
            <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100 bg-gradient-to-r from-emerald-50 to-white flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <Zap className="w-4 h-4" strokeWidth={2.4} />
                </div>
                <div>
                  <h2 className="font-semibold text-slate-900">Hızlı Düzenle</h2>
                  <p className="text-xs text-slate-500">Bu alanlar onay gerektirmez — anında kaydedilir</p>
                </div>
              </div>
              <div className="divide-y divide-slate-100">
                {DIRECT_FIELDS.map((key) => (
                  <FieldRow
                    key={key}
                    field={key}
                    value={info[key as keyof CourierMe] as string | null}
                    isEditing={editingField === key}
                    onEdit={() => setEditingField(key)}
                    onCancel={() => setEditingField(null)}
                    onSubmit={(v) => handleSubmitDirect(key, v)}
                  />
                ))}
              </div>
            </section>

            {/* CRITICAL (onay isteyen) */}
            <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100 bg-gradient-to-r from-amber-50 to-white flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
                  <Shield className="w-4 h-4" strokeWidth={2.4} />
                </div>
                <div>
                  <h2 className="font-semibold text-slate-900">Onay Gerektiren</h2>
                  <p className="text-xs text-slate-500">Maaş ve iletişim güvenliği için admin onayından geçer</p>
                </div>
              </div>
              <div className="divide-y divide-slate-100">
                {CRITICAL_FIELDS.map((key) => {
                  const pendingForField = changes.find(
                    (c) => c.field === key && c.status === 'Beklemede',
                  );
                  return (
                    <FieldRow
                      key={key}
                      field={key}
                      value={info[key as keyof CourierMe] as string | null}
                      isEditing={editingField === key}
                      pendingValue={pendingForField?.new_value ?? null}
                      onEdit={() => setEditingField(key)}
                      onCancel={() => setEditingField(null)}
                      onSubmit={(v) => handleSubmitCritical(key, v)}
                    />
                  );
                })}
              </div>
            </section>

            {/* Read-only info */}
            <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center">
                  <UserCircle2 className="w-4 h-4" strokeWidth={2.4} />
                </div>
                <h2 className="font-semibold text-slate-900">Sistem Bilgileri</h2>
              </div>
              <div className="px-5 py-3 grid grid-cols-2 gap-3 text-sm">
                <ReadOnly label="Plaka" value={info.current_plate} />
                <ReadOnly label="Araç" value={info.vehicle_type} />
                <ReadOnly label="Muhasebe" value={info.accounting_type} />
                <ReadOnly
                  label="İşe Başlama"
                  value={info.start_date ? new Date(info.start_date).toLocaleDateString('tr-TR') : null}
                />
              </div>
            </section>
          </>
        )}

        {activeTab === 'history' && (
          <HistoryView changes={changes} directLog={directLog} />
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
          <div
            className={`px-4 py-3 rounded-xl shadow-lg text-sm font-medium flex items-center gap-2 ${
              toast.kind === 'ok'
                ? 'bg-emerald-600 text-white'
                : 'bg-red-600 text-white'
            }`}
          >
            {toast.kind === 'ok' ? (
              <Check className="w-4 h-4" strokeWidth={2.5} />
            ) : (
              <AlertCircle className="w-4 h-4" />
            )}
            {toast.text}
          </div>
        </div>
      )}

      {photoBusy && (
        <div className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-white rounded-2xl p-6 shadow-2xl flex items-center gap-3">
            <div className="animate-spin rounded-full h-6 w-6 border-3 border-slate-200 border-t-blue-600" />
            <span className="text-sm text-slate-700 font-medium">Fotoğraf işleniyor...</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ───────────────────────────────────────────────────────────
// FieldRow — düzenlenebilir alan satırı
// ───────────────────────────────────────────────────────────
function FieldRow({
  field, value, pendingValue, isEditing, onEdit, onCancel, onSubmit,
}: {
  field: string;
  value: string | null;
  pendingValue?: string | null;
  isEditing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSubmit: (newValue: string | null) => Promise<void>;
}) {
  const meta = FIELD_META[field];
  const Icon = meta?.icon ?? User;
  const [draft, setDraft] = useState<string>(value ?? '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (isEditing) {
      setDraft(value ?? '');
      setErr(null);
    }
  }, [isEditing, value]);

  const submit = async () => {
    const trimmed = draft.trim();
    if (trimmed === (value ?? '').trim()) {
      onCancel();
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await onSubmit(trimmed || null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Hata');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="px-5 py-3.5">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center flex-shrink-0">
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-0.5">
            {meta?.label ?? field}
          </div>

          {!isEditing ? (
            <div className="flex items-center gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-slate-900 font-medium truncate">
                  {formatValue(field, value)}
                </div>
                {pendingValue && (
                  <div className="text-xs text-amber-700 mt-0.5 truncate">
                    Onay bekliyor: <span className="font-mono">{formatValue(field, pendingValue)}</span>
                  </div>
                )}
              </div>
              <button
                onClick={onEdit}
                className="text-xs text-blue-600 hover:text-blue-700 font-semibold px-3 py-1.5 rounded-lg hover:bg-blue-50 transition"
              >
                Düzenle
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {meta?.type === 'select' ? (
                <select
                  value={draft}
                  onChange={(e) => {
                    setDraft(e.target.value);
                    setErr(null);
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                >
                  <option value="">— seçiniz —</option>
                  {meta.options?.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={meta?.type ?? 'text'}
                  value={draft}
                  onChange={(e) => {
                    setDraft(e.target.value);
                    setErr(null);
                  }}
                  placeholder={meta?.placeholder}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  autoFocus
                />
              )}
              {meta?.helper && (
                <div
                  className={`text-xs ${
                    meta.category === 'critical' ? 'text-amber-700' : 'text-emerald-700'
                  }`}
                >
                  {meta.category === 'critical' ? '⚠ ' : '⚡ '}
                  {meta.helper}
                </div>
              )}
              {err && (
                <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                  {err}
                </div>
              )}
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={onCancel}
                  disabled={busy}
                  className="px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 rounded-lg disabled:opacity-50"
                >
                  İptal
                </button>
                <button
                  type="button"
                  onClick={submit}
                  disabled={busy}
                  className={`px-4 py-1.5 text-sm font-semibold text-white rounded-lg disabled:opacity-60 ${
                    meta?.category === 'critical'
                      ? 'bg-amber-600 hover:bg-amber-700'
                      : 'bg-emerald-600 hover:bg-emerald-700'
                  }`}
                >
                  {busy
                    ? 'Kaydediliyor...'
                    : meta?.category === 'critical'
                    ? 'Onaya Gönder'
                    : 'Kaydet'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ReadOnly({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <div className="text-xs text-slate-500 mb-0.5">{label}</div>
      <div className="font-medium text-slate-900 truncate">{value ?? '—'}</div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────
// Geçmiş tab
// ───────────────────────────────────────────────────────────
function HistoryView({
  changes, directLog,
}: {
  changes: ProfileChangeRequest[];
  directLog: DirectChangeLog[];
}) {
  // Birleşik timeline
  type Item = {
    id: string;
    when: string;
    field: string;
    oldVal: string | null;
    newVal: string | null;
    kind: 'critical' | 'direct';
    status?: string;
    notes?: string | null;
  };

  const items: Item[] = [
    ...changes.map<Item>((c) => ({
      id: `c-${c.id}`,
      when: c.requested_at,
      field: c.field,
      oldVal: c.old_value,
      newVal: c.new_value,
      kind: 'critical',
      status: c.status,
      notes: c.decision_notes,
    })),
    ...directLog.map<Item>((d) => ({
      id: `d-${d.id}`,
      when: d.changed_at,
      field: d.field,
      oldVal: d.old_value,
      newVal: d.new_value,
      kind: 'direct',
      status: 'Uygulandı',
    })),
  ].sort((a, b) => (b.when || '').localeCompare(a.when || ''));

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-12 text-center">
        <Clock className="w-10 h-10 text-slate-300 mx-auto mb-3" />
        <p className="text-slate-600 font-medium">Henüz değişiklik yok</p>
        <p className="text-sm text-slate-500 mt-1">
          Profil bilgilerinizi düzenlediğinizde burada görünecek
        </p>
      </div>
    );
  }

  const STATUS_STYLE: Record<string, { bg: string; text: string }> = {
    Beklemede: { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-700' },
    Onaylandı: { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700' },
    Reddedildi: { bg: 'bg-red-50 border-red-200', text: 'text-red-700' },
    'İptal Edildi': { bg: 'bg-slate-50 border-slate-200', text: 'text-slate-600' },
    Uygulandı: { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700' },
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100">
        <h2 className="font-semibold text-slate-900">Değişiklik Geçmişi</h2>
        <p className="text-xs text-slate-500">{items.length} kayıt</p>
      </div>
      <div className="divide-y divide-slate-100">
        {items.map((it) => {
          const meta = FIELD_META[it.field];
          const Icon = meta?.icon ?? Edit3;
          const style = STATUS_STYLE[it.status ?? ''] ?? STATUS_STYLE.Uygulandı;
          return (
            <div key={it.id} className="px-5 py-4">
              <div className="flex items-start gap-3">
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    it.kind === 'direct'
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'bg-amber-50 text-amber-700'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="font-semibold text-slate-900 text-sm">
                      {meta?.label ?? it.field}
                      {it.kind === 'direct' && (
                        <span className="ml-2 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-px rounded">
                          ⚡ Anında
                        </span>
                      )}
                    </div>
                    {it.status && (
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${style.bg} ${style.text}`}
                      >
                        {it.status}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {relTime(it.when)}
                  </div>
                  <div className="mt-2 text-sm flex items-center gap-2 flex-wrap">
                    <span className="text-slate-500 line-through font-mono text-xs">
                      {it.oldVal || '—'}
                    </span>
                    <span className="text-slate-400">→</span>
                    <span className="text-slate-900 font-mono text-xs font-semibold">
                      {it.newVal || '—'}
                    </span>
                  </div>
                  {it.notes && (
                    <div className="mt-2 text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-600">
                      <strong>Not:</strong> {it.notes}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────
// Helper: image resize + compress to dataUrl
// ───────────────────────────────────────────────────────────
async function resizeImageToDataUrl(
  file: File,
  maxSize: number,
  quality: number,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Dosya okunamadı'));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('Görüntü işlenemedi'));
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let { width, height } = img;
        if (width > height) {
          if (width > maxSize) {
            height = Math.round((height * maxSize) / width);
            width = maxSize;
          }
        } else {
          if (height > maxSize) {
            width = Math.round((width * maxSize) / height);
            height = maxSize;
          }
        }
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new Error('Canvas oluşturulamadı'));
          return;
        }
        ctx.drawImage(img, 0, 0, width, height);
        const dataUrl = canvas.toDataURL('image/jpeg', quality);
        resolve(dataUrl);
      };
      img.src = String(reader.result || '');
    };
    reader.readAsDataURL(file);
  });
}
