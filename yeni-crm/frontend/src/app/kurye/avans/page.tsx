'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Plus, Check, Clock, X, AlertCircle } from 'lucide-react';
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

export default function AvansPage() {
  const router = useRouter();
  const [requests, setRequests] = useState<RequestRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const [success, setSuccess] = useState('');

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setSuccess('');
    setIsSubmitting(true);

    if (!amount || parseFloat(amount) <= 0) {
      setFormError('Tutar sıfırdan büyük olmalı');
      setIsSubmitting(false);
      return;
    }

    try {
      const res = await fetch('/api/courier/my-requests', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount: parseFloat(amount),
          reason: reason || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        setFormError(data.detail || 'Talep oluşturulamadı');
        setIsSubmitting(false);
        return;
      }

      const newRequest: RequestRecord = await res.json();
      setRequests([newRequest, ...requests]);
      setAmount('');
      setReason('');
      setSuccess('Avans talebiniz başarıyla oluşturuldu');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Sunucu hatası');
    } finally {
      setIsSubmitting(false);
    }
  };

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

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto">
      {/* Back button */}
      <Link href="/kurye/dashboard" className="flex items-center gap-2 text-brand hover:text-brand-dark mb-6">
        <ArrowLeft className="w-4 h-4" />
        <span className="text-sm">Geri Dön</span>
      </Link>

      <h1 className="text-3xl font-semibold text-text mb-8">Avans Talep Et</h1>

      {/* Form Section */}
      <div className="bg-white rounded-lg border border-cream-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
          <Plus className="w-5 h-5 text-brand" />
          Yeni Talep Oluştur
        </h2>

        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded flex gap-2 items-start">
            <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-green-600">{success}</p>
          </div>
        )}

        {formError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded flex gap-2 items-start">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-600">{formError}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Amount */}
          <div>
            <label htmlFor="amount" className="block text-sm font-medium text-text mb-1">
              Talep Tutar (₺)
            </label>
            <input
              id="amount"
              type="number"
              inputMode="decimal"
              placeholder="5000"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-cream-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent disabled:opacity-50"
              required
            />
          </div>

          {/* Reason */}
          <div>
            <label htmlFor="reason" className="block text-sm font-medium text-text mb-1">
              Neden (Opsiyonel)
            </label>
            <textarea
              id="reason"
              placeholder="Avans nedenini yazın (örn: Acil kişisel masraf)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={isSubmitting}
              rows={3}
              className="w-full px-3 py-2 border border-cream-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent disabled:opacity-50 resize-none"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting || !amount}
            className="w-full py-2 px-4 bg-brand text-white rounded-md font-medium hover:bg-brand-dark disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isSubmitting ? 'Gönderiliyor...' : 'Talep Oluştur'}
          </button>
        </form>
      </div>

      {/* Requests History */}
      <div className="bg-white rounded-lg border border-cream-200 p-6">
        <h2 className="text-lg font-semibold text-text mb-4">Talep Geçmişi</h2>

        {isLoading ? (
          <p className="text-sm text-text-secondary">Yükleniyor...</p>
        ) : error ? (
          <div className="p-3 bg-red-50 border border-red-200 rounded flex gap-2 items-start">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-600">{error}</p>
          </div>
        ) : requests.length === 0 ? (
          <p className="text-sm text-text-secondary">Henüz talep oluşturmadınız.</p>
        ) : (
          <div className="space-y-3">
            {requests.map((req) => (
              <div
                key={req.id}
                className="border border-cream-200 rounded-lg p-4 hover:bg-cream-50 transition"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-medium text-text">{req.request_type}</p>
                      {getStatusBadge(req.status)}
                    </div>
                    <p className="text-sm text-text-secondary mb-2">
                      {req.amount.toLocaleString('tr-TR', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })} ₺
                    </p>
                    {req.reason && (
                      <p className="text-sm text-text-secondary mb-2">{req.reason}</p>
                    )}
                    <p className="text-xs text-text-secondary">
                      Talep: {new Date(req.requested_at).toLocaleDateString('tr-TR')}
                      {req.decided_at && (
                        <>
                          {' · Karar: '}
                          {new Date(req.decided_at).toLocaleDateString('tr-TR')}
                        </>
                      )}
                    </p>
                    {req.decision_notes && (
                      <p className="text-xs text-text-secondary mt-2 italic">{req.decision_notes}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
