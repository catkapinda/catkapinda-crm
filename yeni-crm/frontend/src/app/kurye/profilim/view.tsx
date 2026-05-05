'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, Edit2, Mail, MapPin, Phone, User,
} from 'lucide-react';

import {
  getMyInfo,
  listMyProfileChanges,
  submitProfileChange,
  type ProfileChangeRequest,
} from '@/lib/courier-api';

type PersonnelInfo = {
  id: number;
  person_code: string;
  full_name: string;
  phone: string | null;
  iban: string | null;
  address: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  [key: string]: unknown;
};

const EDITABLE_FIELDS = [
  { key: 'phone', label: 'Telefon', icon: Phone, type: 'tel' },
  { key: 'iban', label: 'IBAN', icon: Mail, type: 'text' },
  { key: 'address', label: 'Adres', icon: MapPin, type: 'text' },
  { key: 'emergency_contact_name', label: 'Acil Durum İsim', icon: User, type: 'text' },
  { key: 'emergency_contact_phone', label: 'Acil Durum Telefon', icon: Phone, type: 'tel' },
];

const FIELD_LABELS: Record<string, string> = {
  phone: 'Telefon',
  iban: 'IBAN',
  address: 'Adres',
  emergency_contact_name: 'Acil Durum İsim',
  emergency_contact_phone: 'Acil Durum Telefon',
};

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

function statusBadge(status: string) {
  const map: Record<string, { bg: string; text: string }> = {
    'Beklemede': { bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-700' },
    'Onaylandı': { bg: 'bg-green-50 border-green-200', text: 'text-green-700' },
    'Reddedildi': { bg: 'bg-red-50 border-red-200', text: 'text-red-700' },
    'İptal Edildi': { bg: 'bg-gray-50 border-gray-200', text: 'text-gray-700' },
  };
  const style = map[status] || map['Beklemede'];
  return { ...style, label: status };
}

interface EditFieldProps {
  field: string;
  label: string;
  current: string | null;
  onSubmit: (newValue: string | null) => Promise<void>;
  disabled?: boolean;
}

function EditField({ field, label, current, onSubmit, disabled }: EditFieldProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [value, setValue] = useState(current || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (value.trim() === (current || '')) {
      setIsOpen(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await onSubmit(value.trim() || null);
      setIsOpen(false);
      setValue('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <div className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-lg hover:border-slate-300 transition">
        <span className="text-slate-700">{current || '—'}</span>
        <button
          onClick={() => {
            setValue(current || '');
            setIsOpen(true);
          }}
          disabled={disabled}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
        >
          Değiştir
        </button>
      </div>
    );
  }

  return (
    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-2">
      <input
        type="text"
        value={value}
        onChange={(e) => {
          setError(null);
          setValue(e.target.value);
        }}
        placeholder="Yeni değer girin"
        className="w-full px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2 justify-end">
        <button
          onClick={() => setIsOpen(false)}
          disabled={loading}
          className="px-3 py-1 text-sm text-slate-700 hover:bg-slate-100 rounded disabled:opacity-50"
        >
          İptal
        </button>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="px-3 py-1 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded disabled:opacity-50"
        >
          {loading ? 'Gönderiliyor...' : 'Talep Gönder'}
        </button>
      </div>
    </div>
  );
}

export function ProfilimView() {
  const router = useRouter();
  const [info, setInfo] = useState<PersonnelInfo | null>(null);
  const [changes, setChanges] = useState<ProfileChangeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [myInfo, myChanges] = await Promise.all([
        getMyInfo(),
        listMyProfileChanges(),
      ]);
      setInfo(myInfo as PersonnelInfo);
      setChanges(myChanges as ProfileChangeRequest[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Veriler yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFieldChange = async (fieldKey: string, newValue: string | null) => {
    try {
      await submitProfileChange(fieldKey, newValue);
      setChanges((prev) => [
        {
          id: Math.max(0, ...prev.map((c) => c.id)) + 1,
          field: fieldKey,
          old_value: (info?.[fieldKey] as string | null) || null,
          new_value: newValue,
          status: 'Beklemede',
          requested_at: new Date().toISOString(),
          decided_at: null,
          decision_notes: null,
        },
        ...prev,
      ]);
    } catch (err) {
      throw err;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-300 border-t-blue-600 mb-3" />
          <p className="text-slate-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !info) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="max-w-sm rounded-lg bg-white shadow-lg p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-2" />
          <h3 className="font-semibold text-slate-900 mb-1">Hata</h3>
          <p className="text-sm text-slate-600">{error || 'Profil yüklenemedi'}</p>
          <button
            onClick={() => {
              setLoading(true);
              loadData();
            }}
            className="mt-4 px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Yeniden Dene
          </button>
        </div>
      </div>
    );
  }

  const pendingCount = changes.filter((c) => c.status === 'Beklemede').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 md:p-8">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 border border-slate-200">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{info.full_name}</h1>
              <p className="text-sm text-slate-500 mt-1">Kod: {info.person_code}</p>
            </div>
            <div className="flex items-center gap-2 bg-blue-50 px-3 py-2 rounded-lg border border-blue-200">
              <Edit2 className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-600">
                {pendingCount} talep beklemede
              </span>
            </div>
          </div>
        </div>

        {/* Editable Fields */}
        <div className="bg-white rounded-lg shadow-sm p-6 border border-slate-200 space-y-4">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Kişisel Bilgilerim</h2>
          {EDITABLE_FIELDS.map(({ key, label }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                {label}
              </label>
              <EditField
                field={key}
                label={label}
                current={(info[key] as string | null) || null}
                onSubmit={(newValue) => handleFieldChange(key, newValue)}
              />
            </div>
          ))}
        </div>

        {/* Pending Requests */}
        {changes.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6 border border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Bekleyen Taleplerim</h2>
            <div className="space-y-3">
              {changes.map((change) => {
                const style = statusBadge(change.status);
                return (
                  <div
                    key={change.id}
                    className={`p-4 rounded-lg border ${style.bg}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <p className="font-medium text-slate-900">
                          {FIELD_LABELS[change.field] || change.field}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {relTime(change.requested_at)}
                        </p>
                      </div>
                      <span className={`px-2 py-1 text-xs font-medium rounded ${style.text}`}>
                        {style.label}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                      <div>
                        <p className="text-slate-600">Eski Değer</p>
                        <p className="font-mono text-slate-900">
                          {change.old_value || '—'}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-600">Yeni Değer</p>
                        <p className="font-mono text-slate-900">
                          {change.new_value || '—'}
                        </p>
                      </div>
                    </div>
                    {change.decision_notes && (
                      <div className="text-xs bg-slate-50 p-2 rounded border border-slate-200">
                        <p className="text-slate-600">Not: {change.decision_notes}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
