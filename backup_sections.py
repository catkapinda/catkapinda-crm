from __future__ import annotations

import tempfile
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import streamlit as st


_FETCH_DF: Callable[[Any, str, tuple], Any] | None = None
_TABLE_EXPORT_ORDER: list[str] = []
_DB_PATH: Path | None = None
_DATABASE_HAS_OPERATIONAL_DATA: Callable[[Any], bool] | None = None
_IMPORT_SQLITE_INTO_CURRENT_DB: Callable[[Any, Path], bool] | None = None


def configure_backup_sections(
    *,
    fetch_df_fn: Callable[[Any, str, tuple], Any],
    table_export_order: list[str],
    db_path: Path,
    database_has_operational_data_fn: Callable[[Any], bool],
    import_sqlite_into_current_db_fn: Callable[[Any, Path], bool],
) -> None:
    global _FETCH_DF
    global _TABLE_EXPORT_ORDER
    global _DB_PATH
    global _DATABASE_HAS_OPERATIONAL_DATA
    global _IMPORT_SQLITE_INTO_CURRENT_DB

    _FETCH_DF = fetch_df_fn
    _TABLE_EXPORT_ORDER = list(table_export_order)
    _DB_PATH = db_path
    _DATABASE_HAS_OPERATIONAL_DATA = database_has_operational_data_fn
    _IMPORT_SQLITE_INTO_CURRENT_DB = import_sqlite_into_current_db_fn


def build_table_backup_zip(conn: Any) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for table in _TABLE_EXPORT_ORDER:
            df = _FETCH_DF(conn, f"SELECT * FROM {table}")
            archive.writestr(f"{table}.csv", df.to_csv(index=False).encode("utf-8-sig"))
    buffer.seek(0)
    return buffer.getvalue()


def render_backup_tools_content(conn: Any) -> None:
    backend_text = "Harici veritabanı" if conn.backend == "postgres" else "Yerel veritabanı"
    st.caption(f"Aktif kayıt altyapısı: {backend_text}")

    backup_zip = build_table_backup_zip(conn)
    st.download_button(
        "Tüm tabloları yedek olarak indir",
        data=backup_zip,
        file_name=f"catkapinda_tam_yedek_{date.today().isoformat()}.zip",
        mime="application/zip",
        use_container_width=True,
    )

    if conn.backend == "sqlite" and _DB_PATH and _DB_PATH.exists():
        st.download_button(
            "SQLite veritabanı dosyasını indir",
            data=_DB_PATH.read_bytes(),
            file_name=f"catkapinda_crm_{date.today().isoformat()}.db",
            mime="application/octet-stream",
            use_container_width=True,
        )
        st.info("Harici veritabanına geçmeden önce bu dosyayı indirmen en güvenli adım olur.")

    if conn.backend == "postgres" and not _DATABASE_HAS_OPERATIONAL_DATA(conn):
        st.markdown("#### SQLite yedeğini içe aktar")
        upload = st.file_uploader("Daha önce indirdiğin `.db` yedeğini seç", type=["db"], key="sqlite_backup_import")
        if st.button("Yedeği içe aktar", key="sqlite_backup_import_btn", use_container_width=True, disabled=upload is None):
            if upload is None:
                st.warning("Önce bir `.db` dosyası seçmelisin.")
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_db:
                    temp_db.write(upload.getvalue())
                    temp_path = Path(temp_db.name)
                try:
                    imported = _IMPORT_SQLITE_INTO_CURRENT_DB(conn, temp_path)
                    if imported:
                        st.success("SQLite yedeği başarıyla harici veritabanına aktarıldı.")
                        st.rerun()
                    st.info("Yedek dosyasında aktarılacak veri bulunamadı.")
                finally:
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass
