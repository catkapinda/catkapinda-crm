from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException
import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


def get_db() -> Generator[psycopg.Connection, None, None]:
    if not settings.database_url:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL tanimli olmadigi icin v2 backend veritabanina baglanamiyor.",
        )
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()
