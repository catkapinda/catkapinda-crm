import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Çat Kapında · Kurye Paneli',
  description: 'Kurye self-service bordro ve talep yönetimi',
};

// NOT: Next.js App Router'da <html>/<body> SADECE root layout'ta olmalı.
// Buradaki nested <html>/<body> tag'leri root layout'takiyle çakışıp
// hydration mismatch (React #418) tetikliyordu — kaldırıldı. Fontlar root
// layout'ta zaten yüklü, kurye sayfaları kendi içlerinde min-h-screen
// kullanıyor.
export default function CourierLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
