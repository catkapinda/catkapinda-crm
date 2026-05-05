import { Sidebar } from '@/components/sidebar';
import {
  getSidebarCounts,
  listProfileChanges,
  type ProfileChangeRequest,
  type SidebarCounts,
} from '@/lib/api';

import { ProfilOnayView } from './view';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Profil Onayları | CRM',
  description: 'Kurye profil değişikliklerini onayla veya reddet',
};

export default async function ProfilOnayPage() {
  let changes: ProfileChangeRequest[] = [];
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  try {
    [changes, counts] = await Promise.all([
      listProfileChanges().catch(() => []),
      getSidebarCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="profil-onay" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <ProfilOnayView
            initialChanges={changes}
            initialCounts={counts ?? ({} as SidebarCounts)}
          />
        )}
      </main>
    </div>
  );
}
