import type { Metadata } from "next";

import { AuthProvider } from "../components/auth/auth-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cat Kapinda CRM v2",
  description: "Operational control panel rebuild for Cat Kapinda",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
