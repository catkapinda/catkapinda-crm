'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, ChevronUp, Loader2, Lock, LogOut, User,
} from 'lucide-react';

import {
  changeOwnPassword,
  clearAuthToken,
  readAuthUserCached,
  type AuthUser,
} from '@/lib/api';

export function ProfileDropdownClient() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [open, setOpen] = useState(false);
  const [showChangePwd, setShowChangePwd] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setUser(readAuthUserCached());
  }, []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [open]);

  function handleLogout() {
    clearAuthToken();
    router.push('/login');
  }

  if (!user) return null;

  const displayName = user.full_name || user.email || user.phone || '';
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('') || 'U';

  return (
    <>
      <div ref={ref} className="relative px-2 pt-3 mt-1 border-t border-border/60">
        <button
          onClick={() => setOpen((v) => !v)}
          className="w-full flex items-center gap-2.5 px-2 py-2 rounded-xl hover:bg-bg-surface2 transition group"
        >
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-brand-dark to-brand text-white flex items-center justify-center text-[12px] font-bold shadow-sm flex-shrink-0">
            {initials}
          </div>
          <div className="flex-1 text-left min-w-0">
            <div className="text-[12.5px] font-semibold text-text truncate">
              {user.full_name || user.email?.split('@')[0] || user.phone || 'Kullanıcı'}
            </div>
            <div className="text-[10.5px] text-text-3 truncate">
              {user.email || user.phone || ''}
            </div>
          </div>
          <ChevronUp
            className={`w-3.5 h-3.5 text-text-3 transition-transform ${
              open ? '' : 'rotate-180'
            }`}
            strokeWidth={2.4}
          />
        </button>

        {open && (
          <div className="absolute bottom-full left-2 right-2 mb-2 z-40 bg-white border border-border rounded-xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-150">
            <div className="px-4 py-3 border-b border-border/60 bg-cream-50/60">
              <div className="text-[11px] uppercase tracking-wider font-bold text-text-3 mb-1">
                Profil
              </div>
              <div className="text-[13px] font-semibold text-text">
                {user.full_name || '—'}
              </div>
              <div className="text-[11.5px] text-text-3 font-mono mt-0.5">
                {user.email || user.phone || '—'}
              </div>
              <div className="text-[10px] text-brand uppercase tracking-wider font-bold mt-1.5">
                {user.role}
              </div>
            </div>
            <button
              onClick={() => { setOpen(false); setShowChangePwd(true); }}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-[12.5px] text-text-2 hover:bg-bg-surface2 transition text-left"
            >
              <Lock className="w-3.5 h-3.5" strokeWidth={2.2} />
              Şifre Değiştir
            </button>
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-[12.5px] text-rose-700 hover:bg-rose-50 transition text-left border-t border-border/60"
            >
              <LogOut className="w-3.5 h-3.5" strokeWidth={2.2} />
              Çıkış Yap
            </button>
          </div>
        )}
      </div>

      {showChangePwd && (
        <ChangePasswordModal onClose={() => setShowChangePwd(false)} />
      )}
    </>
  );
}


function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const [current, setCurrent] = useState('');
  const [pwd, setPwd] = useState('');
  const [pwd2, setPwd2] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (pwd.length < 6) { setError('Yeni parola en az 6 karakter'); return; }
    if (pwd !== pwd2) { setError('Parolalar eşleşmiyor'); return; }
    setLoading(true);
    setError(null);
    try {
      await changeOwnPassword(current, pwd);
      setDone(true);
      setTimeout(onClose, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Değiştirilemedi');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          <div className="w-9 h-9 rounded-xl bg-brand-soft text-brand flex items-center justify-center">
            <Lock className="w-4 h-4" strokeWidth={2.4} />
          </div>
          <div>
            <h2 className="font-display text-lg font-bold text-text">Şifre Değiştir</h2>
            <div className="text-[11px] text-text-3">Mevcut parolanızı girin</div>
          </div>
        </div>

        {done ? (
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-emerald-700 text-sm">
            ✓ Parola güncellendi.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <PwdField label="Mevcut Parola" value={current} onChange={setCurrent} autoFocus />
            <PwdField label="Yeni Parola" value={pwd} onChange={setPwd} />
            <PwdField label="Yeni Parola (Tekrar)" value={pwd2} onChange={setPwd2} />

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-2.5 text-red-700 text-[12px] flex items-start gap-2">
                <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2.5 rounded-xl border border-border text-text-2 text-sm font-semibold hover:bg-bg-surface2 transition"
              >
                Vazgeç
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 py-2.5 rounded-xl bg-brand text-white text-sm font-bold hover:bg-brand-dark transition disabled:opacity-60 inline-flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Güncelle'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function PwdField({
  label, value, onChange, autoFocus,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  autoFocus?: boolean;
}) {
  return (
    <div>
      <label className="block text-[11px] font-bold text-text-2 uppercase tracking-wider mb-1">
        {label}
      </label>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoFocus={autoFocus}
        required
        className="w-full px-3 py-2.5 rounded-lg border border-border text-sm focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
      />
    </div>
  );
}
