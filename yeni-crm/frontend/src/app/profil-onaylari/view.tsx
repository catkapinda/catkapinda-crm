'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, Check, Mail, MapPin, Phone, Search, Trash2, User,
  XCircle, type LucideIcon,
} from 'lucide-react';

import {
  type ProfileChangeRequest,
  type SidebarCounts,
  decideProfileChange,
  deleteProfileChange,
} from '@/lib/api';

type StatusKey = 'Beklemede' | 'Onaylandı' | 'Reddedildi';

const FIELD_LABELS: Record<string, { label: string; icon: LucideIcon }> = {
  phone: { label: 'Telefon', icon: Phone },
  iban: { label: 'IBAN', icon: Mail },
  address: { label: 'Adres', icon: MapPin },
  emergency_contact_name: { label: 'Acil Durum İsim', icon: User },
  emergency_contact_phone: { label: 'Acil Durum Telefon', icon: Phone },
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

function statusStyle(status: string): { bg: string; text: string; dot: string } {
  const map: Record<string, { bg: string; text: string; dot: string }> = {
    'Beklemede': { bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-700', dot: 'bg-yellow-500' },
    'Onaylandı': { bg: 'bg-green-50 border-green-200', text: 'text-green-700', dot: 'bg-green-500' },
    'Reddedildi': { bg: 'bg-red-50 border-red-200', text: 'text-red-700', dot: 'bg-red-500' },
    'İptal Edildi': { bg: 'bg-gray-50 border-gray-200', text: 'text-gray-700', dot: 'bg-gray-500' },
  };
  return map[status] || map['Beklemede'];
}

interface ChangeCardProps {
  change: ProfileChangeRequest;
  onApprove: () => Promise<void>;
  onReject: () => Promise<void>;
  onDelete: () => Promise<void>;
  loading?: boolean;
}

function ChangeCard({
  change,
  onApprove,
  onReject,
  onDelete,
  loading,
}: ChangeCardProps) {
  const [actionLoading, setActionLoading] = useState(false);
  const [actionType, setActionType] = useState<'approve' | 'reject' | 'delete' | null>(null);

  const fieldInfo = FIELD_LABELS[change.field];
  const style = statusStyle(change.status);
  const FieldIcon = fieldInfo?.icon || Mail;

  const handleAction = async (type: 'approve' | 'reject' | 'delete') => {
    setActionLoading(true);
    setActionType(type);
    try {
      if (type === 'approve') await onApprove();
      else if (type === 'reject') await onReject();
      else await onDelete();
    } finally {
      setActionLoading(false);
      setActionType(null);
    }
  };

  if (change.status !== 'Beklemede') {
    return (
      <div className={`border rounded-lg p-4 ${style.bg}`}>
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <FieldIcon className="w-4 h-4 text-slate-600" />
              <p className="font-semibold text-slate-900">
                {fieldInfo?.label || change.field}
              </p>
            </div>
            <p className="text-sm text-slate-600">
              {change.personnel_name} ({change.person_code})
            </p>
            <p className="text-xs text-slate-500 mt-1">{relTime(change.requested_at)}</p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${style.dot}`} />
            <span className={`px-2 py-1 text-xs font-medium rounded whitespace-nowrap ${style.text}`}>
              {change.status}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-slate-600">Eski</p>
            <p className="font-mono text-slate-900">{change.old_value || '—'}</p>
          </div>
          <div>
            <p className="text-slate-600">Yeni</p>
            <p className="font-mono text-slate-900">{change.new_value || '—'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`border rounded-lg p-4 ${style.bg} transition hover:shadow-sm`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <FieldIcon className="w-4 h-4 text-slate-600" />
            <p className="font-semibold text-slate-900">
              {fieldInfo?.label || change.field}
            </p>
          </div>
          <p className="text-sm text-slate-600">
            {change.personnel_name} ({change.person_code})
          </p>
          <p className="text-xs text-slate-500 mt-1">{relTime(change.requested_at)}</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${style.dot}`} />
          <span className={`px-2 py-1 text-xs font-medium rounded whitespace-nowrap ${style.text}`}>
            {change.status}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm mb-4 py-3 border-y border-current border-opacity-20">
        <div>
          <p className="text-slate-600">Eski Değer</p>
          <p className="font-mono text-slate-900 font-semibold">{change.old_value || '—'}</p>
        </div>
        <div>
          <p className="text-slate-600">Yeni Değer</p>
          <p className="font-mono text-slate-900 font-semibold">{change.new_value || '—'}</p>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => handleAction('approve')}
          disabled={actionLoading}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-green-600 text-white text-sm font-medium rounded hover:bg-green-700 disabled:opacity-50 transition"
        >
          {actionType === 'approve' && actionLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
            </>
          ) : (
            <>
              <Check className="w-4 h-4" />
              Onayla
            </>
          )}
        </button>
        <button
          onClick={() => handleAction('reject')}
          disabled={actionLoading}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-red-600 text-white text-sm font-medium rounded hover:bg-red-700 disabled:opacity-50 transition"
        >
          {actionType === 'reject' && actionLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
            </>
          ) : (
            <>
              <XCircle className="w-4 h-4" />
              Reddet
            </>
          )}
        </button>
        <button
          onClick={() => handleAction('delete')}
          disabled={actionLoading}
          className="px-3 py-2 text-slate-700 hover:bg-slate-200 rounded text-sm font-medium disabled:opacity-50 transition"
        >
          {actionType === 'delete' && actionLoading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-slate-700 border-t-transparent" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  );
}

export function ProfilOnayView({
  initialChanges,
  initialCounts,
}: {
  initialChanges: ProfileChangeRequest[];
  initialCounts: SidebarCounts;
}) {
  const router = useRouter();
  const [changes, setChanges] = useState(initialChanges);
  const [statusTab, setStatusTab] = useState<StatusKey>('Beklemede');
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    return changes.filter((c) => {
      if (c.status !== statusTab) return false;
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        (c.personnel_name || '').toLowerCase().includes(q)
        || (c.person_code || '').toLowerCase().includes(q)
        || (FIELD_LABELS[c.field]?.label || c.field).toLowerCase().includes(q)
      );
    });
  }, [changes, statusTab, search]);

  const counts = useMemo(() => {
    return {
      'Beklemede': changes.filter((c) => c.status === 'Beklemede').length,
      'Onaylandı': changes.filter((c) => c.status === 'Onaylandı').length,
      'Reddedildi': changes.filter((c) => c.status === 'Reddedildi').length,
      total: changes.length,
    };
  }, [changes]);

  const handleApprove = async (changeId: number) => {
    try {
      await decideProfileChange(changeId, 'Onaylandı');
      setChanges((prev) =>
        prev.map((c) => (c.id === changeId ? { ...c, status: 'Onaylandı', decided_at: new Date().toISOString() } : c))
      );
      router.refresh();
    } catch (err) {
      console.error('Onay hatası:', err);
    }
  };

  const handleReject = async (changeId: number) => {
    try {
      await decideProfileChange(changeId, 'Reddedildi');
      setChanges((prev) =>
        prev.map((c) => (c.id === changeId ? { ...c, status: 'Reddedildi', decided_at: new Date().toISOString() } : c))
      );
      router.refresh();
    } catch (err) {
      console.error('Reddetme hatası:', err);
    }
  };

  const handleDelete = async (changeId: number) => {
    try {
      await deleteProfileChange(changeId);
      setChanges((prev) => prev.filter((c) => c.id !== changeId));
      router.refresh();
    } catch (err) {
      console.error('Silme hatası:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 md:p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 border border-slate-200">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Profil Onayları</h1>
          <p className="text-slate-600">Kurye profil değişiklik taleplerini yönetin</p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Kurye adı, kod veya alan ara..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg bg-white text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Status Tabs */}
        <div className="flex gap-2 bg-white p-1 rounded-lg border border-slate-200 w-fit">
          {(['Beklemede', 'Onaylandı', 'Reddedildi'] as StatusKey[]).map((status) => (
            <button
              key={status}
              onClick={() => setStatusTab(status)}
              className={`px-4 py-2 text-sm font-medium rounded transition ${
                statusTab === status
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-700 hover:bg-slate-100'
              }`}
            >
              {status}
              {counts[status] > 0 && (
                <span className="ml-2 text-xs bg-slate-200 px-2 py-0.5 rounded-full">
                  {counts[status]}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Changes List */}
        <div className="space-y-3">
          {filtered.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
              <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-600">
                {search ? 'Arama sonucu bulunamadı' : `${statusTab} talep yok`}
              </p>
            </div>
          ) : (
            filtered.map((change) => (
              <ChangeCard
                key={change.id}
                change={change}
                onApprove={() => handleApprove(change.id)}
                onReject={() => handleReject(change.id)}
                onDelete={() => handleDelete(change.id)}
              />
            ))
          )}
        </div>

        {/* Summary */}
        {counts.total > 0 && (
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-lg p-4 border border-yellow-200 text-center">
              <p className="text-2xl font-bold text-yellow-700">{counts['Beklemede']}</p>
              <p className="text-xs text-yellow-600">Beklemede</p>
            </div>
            <div className="bg-white rounded-lg p-4 border border-green-200 text-center">
              <p className="text-2xl font-bold text-green-700">{counts['Onaylandı']}</p>
              <p className="text-xs text-green-600">Onaylandı</p>
            </div>
            <div className="bg-white rounded-lg p-4 border border-red-200 text-center">
              <p className="text-2xl font-bold text-red-700">{counts['Reddedildi']}</p>
              <p className="text-xs text-red-600">Reddedildi</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
