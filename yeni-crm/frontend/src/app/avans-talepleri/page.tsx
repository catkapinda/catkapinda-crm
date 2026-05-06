import { Sidebar } from '@/components/sidebar';
import {
  getSidebarCounts,
  listCourierRequests,
  listPersonnel,
  type CourierRequest,
  type Personnel,
  type SidebarCounts,
} from '@/lib/api';

import { AvansTalepleriView } from './view';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Avans Talepleri | CRM',
  description: 'Kuryelerin gönderdiği avans talepleri — onayla / reddet',
};

export default async function AvansTalepleriPage() {
  let requests: CourierRequest[] = [];
  let personnel: Personnel[] = [];
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  try {
    [requests, personnel, counts] = await Promise.all([
      listCourierRequests().catch(() => []),
      listPersonnel('Aktif').catch(() => []),
      getSidebarCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  // Sadece Avans tipi
  const avansRequests = requests.filter((r) => r.request_type === 'Avans');

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="avans-talepleri" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <AvansTalepleriView
            requests={avansRequests}
            personnel={personnel}
          />
        )}
      </main>
    </div>
  );
}
