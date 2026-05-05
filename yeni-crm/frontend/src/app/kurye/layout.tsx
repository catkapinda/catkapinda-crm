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
      <body className="antialiased bg-cream-50 text-text font-sans min-h-screen">
        <div className="flex flex-col min-h-screen">
          {/* Brand Bar */}
          <div className="border-b border-cream-200 bg-white px-4 py-3 md:px-6">
            <p className="text-sm font-medium text-text">çatkapında · kurye paneli</p>
          </div>
          {/* Content */}
          <div className="flex-1">{children}</div>
        </div>
      </body>
    </html>
  );
}
