'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileText, Plus, Clock, Download, LogOut, AlertCircle } from 'lucide-react';
import Link from 'next/link';

type CourierSummary = {
  period: string;
  bordro: {
    total_brut: number;
    total_deductions: number;
    total_net: number;
  };
  request_stats: {
    pending_count: number;
    approved_count: number;
    rejected_count: number;
  };
};

export default function CourierDashboard() {
  const router = useRouter();
  const [data, setData] = useState<CourierSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('courier_token');
      if (!token) {
        router.push('/kurye');
        return;
      }

      try {
        const now = new Date();
        const period = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

        const res = await fetch(`/api/courier/my-summary?period=${period}`, {
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
          throw new Error('Veriler yüklenemedi');
        }

        const summary: CourierSummary = await res.json();
        setData(summary);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Sunucu hatası');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [router]);

  const handleLogout = async () => {
    const token = localStorage.getItem('courier_token');
    if (token) {
      try {
        await fetch('/api/courier/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
      } catch {
        /* sessizce yut */
      }
    }
    localStorage.removeItem('courier_token');
    router.push('/kurye');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-text-secondary">Yükleniyor...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-4 md:p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex gap-3 items-start">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-600">{error || 'Veri yüklenemedi'}</p>
        </div>
      </div>
    );
  }

  const { bordro, request_stats } = data;

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto">
      {/* Header with Logout */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-text mb-2">Hoşgeldiniz</h1>
          <p className="text-text-secondary">
            {data.period} döneminde bordronuzu görebilir ve avans talep oluşturabilirsiniz.
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="p-2 text-text-secondary hover:text-text hover:bg-cream-100 rounded-md transition"
          title="Çıkış Yap"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </div>

      {/* Bordro Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-cream-200 p-6">
          <p className="text-sm text-text-secondary mb-1">Toplam Brüt</p>
          <p className="text-2xl font-semibold text-text">
            {(bordro.total_brut || 0).toLocaleString('tr-TR', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })} ₺
          </p>
        </div>

        <div className="bg-white rounded-lg border border-cream-200 p-6">
          <p className="text-sm text-text-secondary mb-1">Kesintiler</p>
          <p className="text-2xl font-semibold text-red-600">
            {(bordro.total_deductions || 0).toLocaleString('tr-TR', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })} ₺
          </p>
        </div>

        <div className="bg-white rounded-lg border border-cream-200 p-6">
          <p className="text-sm text-text-secondary mb-1">Net Ödeme</p>
          <p className="text-2xl font-semibold text-brand">
            {(bordro.total_net || 0).toLocaleString('tr-TR', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })} ₺
          </p>
        </div>
      </div>

      {/* Quick Action Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Link
          href={`/kurye/bordro?period=${data.period}`}
          className="flex items-center gap-3 p-4 bg-white rounded-lg border border-cream-200 hover:border-brand-light hover:bg-cream-50 transition"
        >
          <Download className="w-5 h-5 text-brand flex-shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-text">Bordromu İndir</p>
            <p className="text-xs text-text-secondary">PDF olarak indir</p>
          </div>
        </Link>

        <Link
          href="/kurye/avans"
          className="flex items-center gap-3 p-4 bg-white rounded-lg border border-cream-200 hover:border-brand-light hover:bg-cream-50 transition"
        >
          <Plus className="w-5 h-5 text-brand flex-shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-text">Avans Talep Et</p>
            <p className="text-xs text-text-secondary">Yeni talep oluştur</p>
          </div>
        </Link>

        <Link
          href="/kurye/talepler"
          className="flex items-center gap-3 p-4 bg-white rounded-lg border border-cream-200 hover:border-brand-light hover:bg-cream-50 transition"
        >
          <Clock className="w-5 h-5 text-brand flex-shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-text">Geçmiş Taleplerim</p>
            <p className="text-xs text-text-secondary">
              {request_stats.pending_count} beklemede
            </p>
          </div>
        </Link>
      </div>

      {/* Request Stats Card */}
      <div className="bg-white rounded-lg border border-cream-200 p-6">
        <h2 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-brand" />
          Talep Durumu
        </h2>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-text-secondary mb-1">Beklemede</p>
            <p className="text-2xl font-semibold text-yellow-600">
              {request_stats.pending_count}
            </p>
          </div>
          <div>
            <p className="text-text-secondary mb-1">Onaylandı</p>
            <p className="text-2xl font-semibold text-green-600">
              {request_stats.approved_count}
            </p>
          </div>
          <div>
            <p className="text-text-secondary mb-1">Reddedildi</p>
            <p className="text-2xl font-semibold text-red-600">
              {request_stats.rejected_count}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
