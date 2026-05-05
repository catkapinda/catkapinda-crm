'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, Download, AlertCircle } from 'lucide-react';
import Link from 'next/link';

type BordroData = {
  personnel_id: number;
  period: string;
  total_brut: number;
  total_deductions: number;
  total_net: number;
  detail?: {
    [key: string]: unknown;
  };
};

function BordroContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const period = searchParams.get('period') || '';
  const [bordro, setBordro] = useState<BordroData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);

  const token = typeof window !== 'undefined' ? localStorage.getItem('courier_token') : null;

  useEffect(() => {
    if (!token) {
      router.push('/kurye');
      return;
    }

    if (!period) {
      setError('Dönem belirtilmedi');
      setIsLoading(false);
      return;
    }

    const fetchBordro = async () => {
      try {
        const res = await fetch(`/api/courier/my-bordro?period=${period}`, {
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
          throw new Error('Bordro yüklenemedi');
        }

        const data: BordroData = await res.json();
        setBordro(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Sunucu hatası');
      } finally {
        setIsLoading(false);
      }
    };

    fetchBordro();
  }, [token, router, period]);

  const handleDownloadPdf = async () => {
    if (!token || !period) return;

    setIsDownloading(true);
    try {
      const res = await fetch(`/api/courier/my-bordro/pdf?period=${period}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        throw new Error('PDF indirilemedi');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bordro-${period}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'PDF indirme hatası');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto">
      {/* Back button */}
      <Link href="/kurye/dashboard" className="flex items-center gap-2 text-brand hover:text-brand-dark mb-6">
        <ArrowLeft className="w-4 h-4" />
        <span className="text-sm">Geri Dön</span>
      </Link>

      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-text mb-1">Bordro</h1>
          <p className="text-text-secondary">{period}</p>
        </div>
        <button
          onClick={handleDownloadPdf}
          disabled={isDownloading || !bordro}
          className="flex items-center gap-2 px-4 py-2 bg-brand text-white rounded-md font-medium hover:bg-brand-dark disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          <Download className="w-4 h-4" />
          {isDownloading ? 'İndiriliyor...' : 'PDF İndir'}
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-8">
          <p className="text-text-secondary">Yükleniyor...</p>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 rounded flex gap-3 items-start">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      ) : !bordro ? (
        <div className="text-center py-8">
          <p className="text-text-secondary">Bordro verisi yüklenemedi</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-cream-200 p-6">
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="text-center">
              <p className="text-sm text-text-secondary mb-1">Toplam Brüt</p>
              <p className="text-2xl font-semibold text-text">
                {(bordro.total_brut || 0).toLocaleString('tr-TR', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })} ₺
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-text-secondary mb-1">Kesintiler</p>
              <p className="text-2xl font-semibold text-red-600">
                {(bordro.total_deductions || 0).toLocaleString('tr-TR', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })} ₺
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-text-secondary mb-1">Net Ödeme</p>
              <p className="text-2xl font-semibold text-brand">
                {(bordro.total_net || 0).toLocaleString('tr-TR', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })} ₺
              </p>
            </div>
          </div>

          <div className="text-sm text-text-secondary text-center">
            <p>Detaylı bilgi için PDF'i indirin</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function BordroPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-text-secondary">Yükleniyor...</p>
      </div>
    }>
      <BordroContent />
    </Suspense>
  );
}
