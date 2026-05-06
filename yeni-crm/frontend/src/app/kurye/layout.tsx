import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Çat Kapında · Kurye Paneli',
  description: 'Kurye self-service bordro ve talep yönetimi',
};

export default function CourierLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700&family=Inter+Tight:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased text-slate-900 font-sans min-h-screen">
        {children}
      </body>
    </html>
  );
}
