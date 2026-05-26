import { SifreSifirlaView } from './view';

export const dynamic = 'force-dynamic';

export default async function SifreSifirlaPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return <SifreSifirlaView token={token ?? ''} />;
}
