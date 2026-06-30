"""Veritabanı bağlantı havuzu (Supabase Postgres)."""
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool

from app.core.config import get_settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        # KÜÇÜK AYAK İZİ — Supabase bağlantı limiti dolmasın.
        # Asıl sorun havuz boyutu DEĞİL: Supabase'in toplam bağlantı limiti
        # doluyordu (boşta tutulan bağlantılar + deploy sırasında eski/yeni
        # instance'ların üst üste binmesi). 'couldn't get a connection after
        # Ns' hatası app genelinde (migrations, welcome_sms, forgot_password)
        # görülüyordu — yeni instance startup'ta migration için bile bağlantı
        # alamıyordu. Bu yüzden uygulamanın STANDING bağlantı sayısı düşük
        # tutulur:
        #  - min_size=0: boşta bağlantı TUTMA → Supabase slotlarını işgal etme
        #  - max_size=5: tek instance en fazla 5; iki instance çakışsa bile 10
        #  - max_idle=30: boşta kalan bağlantı 30 sn'de kapanır (slot serbest)
        #  - check: bağlantı verilmeden canlı mı diye doğrulanır (stale önler)
        # KALICI ÇÖZÜM: DATABASE_URL Supabase 'Transaction pooler'a (pgbouncer,
        # port 6543) çevrilmeli — yüzlerce client bağlantısını multipleksler.
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=0,
            max_size=5,
            timeout=10,
            max_idle=30.0,
            max_lifetime=600.0,
            check=ConnectionPool.check_connection,
        )
    return _pool


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Context manager for getting a DB connection from the pool."""
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
