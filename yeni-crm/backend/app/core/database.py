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
        # Havuz büyütüldü + dayanıklılık eklendi:
        #  - max_size 10→20: Genel Bakış tek seferde 5+ paralel sorgu açıyor;
        #    eşzamanlı yükte 10 bağlantı tükenip "couldn't get a connection
        #    after 10s" hatasına (ör. forgot_password e-posta gönderememe)
        #    yol açıyordu.
        #  - check: bir bağlantı havuzdan verilmeden önce canlı mı diye
        #    doğrulanır → Supabase boşta kalan bağlantıları düşürdüğünde
        #    ölü bağlantı verilmesini önler.
        #  - max_idle / max_lifetime: bağlantılar periyodik geri dönüştürülür.
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=20,
            timeout=15,
            max_idle=300.0,       # 5 dk boşta kalan fazlalık bağlantı kapanır
            max_lifetime=1800.0,  # her bağlantı en fazla 30 dk yaşar
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
