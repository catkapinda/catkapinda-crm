'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Check, Clock, X, AlertCircle } from 'lucide-react';
import Link from 'next/link';

type RequestRecord = {
  id: number;
  request_type: string;
  amount: number;
  reason: string | null;
  status: string;
  requested_at: string;
  decided_at: string | null;
  decision_notes: string | null;
};

export default function TalepleriPage() {
  const router = useRouter();
  const [requests, setRequests] = useState<RequestRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const token = typeof window !== 'undefined' ? localStorage.getItem('courier_token') : null;

  useEffect(() => {
    if (!token) {
      router.push('/kurye');
      return;
    }

    const fetchRequests = async () => {
      try {
        const res = await fetch('/api/courier/my-requests', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!res.ok) {
          if (res.status === 401) {
            localStorage.removeItem('courier_token');
            router.push('/kurye');
            return;
          }
          throw new Error('Talepler yüklenemedi');
        }

        const data: RequestRecord[] = await res.json();
        setRequests(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Sunucu hatası');
      } finally {
        setIsLoading(false);
      }
    };

    fetchRequests();
  }, [token, router]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Beklemede':
        return <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-50 text-yellow-700 text-xs font-medium rounded"><Clock className="w-3 h-3" /> Beklemede</span>;
      case 'Onaylandı':
        return <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-50 text-green-700 text-xs font-medium rounded"><Check className="w-3 h-3" /> Onaylandı</span>;
      case 'Reddedildi':
        return <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-50 text-red-700 text-xs font-medium rounded"><X className="w-3 h-3" /> Reddedildi</span>;
      default:
        return <span className="px-2 py-1 bg-gray-50 text-gray-700 text-xs font-medium rounded">{status}</span>;
    }
  };

  const filteredRequests = statusFilter
    ? requests.filter((r) => r.status === statusFilter)
    : requests;

  const statuses = ['Beklemede', 'Onaylandı', 'Reddedildi'];
  const statusCounts = {
    Beklemede: requests.filter((r) => r.status === 'Beklemede').length,
    Onaylandı: requests.filter((r) => r.status === 'Onaylandı').length,
    Reddedildi: requests.filter((r) => r.status === 'Reddedildi').length,
  };

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto">
      {/* Back button */}
      <Link href="/kurye/dashboard" className="flex items-center gap-2 text-brand hover:text-brand-dark mb-6">
        <ArrowLeft className="w-4 h-4" />
        <span className="text-sm">Geri Dön</span>
      </Link>

      <h1 className="text-3xl font-semibold text-text mb-8">Geçmiş Taleplerim</h1>

      {/* Status Filter Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        <button
          onClick={() => setStatusFilter('')}
          className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
            statusFilter === ''
              ? 'bg-brand text-white'
              : 'bg-cream-100 text-text hover:bg-cream-200'
          }`}
        >
          Hepsi ({requests.length})
        </button>
        {statuses.map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
              statusFilter === status
                ? 'bg-brand text-white'
                : 'bg-cream-100 text-text hover:bg-cream-200'
            }`}
          >
            {status} ({statusCounts[status as keyof typeof statusCounts]})
          </button>
        ))}
      </div>

      {/* Requests List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="text-center py-8">
            <p className="text-text-secondary">Yükleniyor...</p>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 border border-red-200 rounded flex gap-3 items-start">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-600">{error}</p>
          </div>
        ) : filteredRequests.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-text-secondary">
              {statusFilter ? `${statusFilter} durumunda talep yok.` : 'Henüz talep oluşturmadınız.'}
            </p>
          </div>
        ) : (
          filteredRequests.map((req) => (
            <div
              key={req.id}
              className="bg-white rounded-lg border border-cream-200 p-6 hover:border-brand-light transition"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-text">{req.request_type}</h3>
                    {getStatusBadge(req.status)}
                  </div>
                  <p className="text-lg font-semibold text-brand">
                    {req.amount.toLocaleString('tr-TR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })} ₺
                  </p>
                </div>
              </div>

              {req.reason && (
                <p className="text-sm text-text-secondary mb-3">{req.reason}</p>
              )}

              <div className="space-y-1 text-xs text-text-secondary">
                <p>Talep Tarihi: {new Date(req.requested_at).toLocaleDateString('tr-TR', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}</p>
                {req.decided_at && (
                  <p>Karar Tarihi: {new Date(req.decided_at).toLocaleDateString('tr-TR', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}</p>
                )}
              </div>

              {req.decision_notes && (
                <div className="mt-3 p-3 bg-cream-50 rounded border border-cream-200">
                  <p className="text-xs font-medium text-text-secondary mb-1">Karar Notu:</p>
                  <p className="text-sm text-text">{req.decision_notes}</p>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
