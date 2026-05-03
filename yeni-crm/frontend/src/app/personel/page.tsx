import { Sidebar } from '@/components/sidebar';
import {
  listPersonnel,
  listRestaurants,
  getSidebarCounts,
  type Personnel,
  type Restaurant,
  type SidebarCounts,
} from '@/lib/api';
import { PersonnelView } from './view';

export const dynamic = 'force-dynamic';

export default async function PersonelPage() {
  let allPersonnel: Personnel[] = [];
  let restaurants: Restaurant[] = [];
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  try {
    // Tüm statüsleri çek; filtrelemeyi client'ta yap
    [allPersonnel, restaurants, counts] = await Promise.all([
      listPersonnel(),
      listRestaurants().catch(() => []),
      getSidebarCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="personel" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <PersonnelView personnel={allPersonnel} restaurants={restaurants} />
        )}
      </main>
    </div>
  );
}
