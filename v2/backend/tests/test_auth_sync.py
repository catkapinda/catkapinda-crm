from app.core.auth_sync import sync_mobile_auth_user_for_personnel, sync_mobile_auth_users
from app.core.security import build_mobile_auth_email


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class FakeConnection:
    def __init__(self, *, personnel_rows=None, auth_users=None):
        self.personnel_rows = personnel_rows or {}
        self.auth_users = auth_users or []
        self.deleted_sessions: list[str] = []
        self.deleted_phone_codes: list[int] = []
        self.next_auth_user_id = (
            max((int(row.get("id") or 0) for row in self.auth_users), default=0) + 1
        )

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split())

        if "FROM personnel WHERE id = %s LIMIT 1" in normalized:
            row = self.personnel_rows.get(int(params[0]))
            return FakeResult([dict(row)] if row else [])

        if "FROM personnel WHERE role IN %s" in normalized:
            roles = {str(value) for value in params[0]}
            rows = [
                dict(row)
                for row in self.personnel_rows.values()
                if str(row.get("role") or "") in roles
            ]
            return FakeResult(rows)

        if "FROM auth_users WHERE lower(COALESCE(email, '')) = lower(%s) LIMIT 1" in normalized:
            target = str(params[0]).lower()
            row = next(
                (candidate for candidate in self.auth_users if str(candidate.get("email") or "").lower() == target),
                None,
            )
            return FakeResult([dict(row)] if row else [])

        if "SELECT id, email, phone FROM auth_users WHERE role = %s" in normalized:
            role = str(params[0])
            rows = [
                {
                    "id": row.get("id"),
                    "email": row.get("email"),
                    "phone": row.get("phone"),
                }
                for row in self.auth_users
                if str(row.get("role") or "") == role
            ]
            return FakeResult(rows)

        if "FROM auth_users WHERE role = %s AND phone = %s LIMIT 1" in normalized:
            role, phone = params
            row = next(
                (
                    candidate
                    for candidate in self.auth_users
                    if str(candidate.get("role") or "") == str(role)
                    and str(candidate.get("phone") or "") == str(phone)
                ),
                None,
            )
            return FakeResult([dict(row)] if row else [])

        if "FROM auth_users WHERE role = %s AND phone = %s AND id <> %s LIMIT 1" in normalized:
            role, phone, excluded_id = params
            row = next(
                (
                    candidate
                    for candidate in self.auth_users
                    if str(candidate.get("role") or "") == str(role)
                    and str(candidate.get("phone") or "") == str(phone)
                    and int(candidate.get("id") or 0) != int(excluded_id)
                ),
                None,
            )
            return FakeResult([dict(row)] if row else [])

        if normalized.startswith("INSERT INTO auth_users"):
            (
                email,
                phone,
                full_name,
                role,
                role_display,
                password_hash,
                created_at,
                updated_at,
            ) = params
            self.auth_users.append(
                {
                    "id": self.next_auth_user_id,
                    "email": email,
                    "phone": phone,
                    "full_name": full_name,
                    "role": role,
                    "role_display": role_display,
                    "password_hash": password_hash,
                    "is_active": 1,
                    "must_change_password": 1,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )
            self.next_auth_user_id += 1
            return FakeResult([])

        if normalized.startswith("UPDATE auth_users SET email = %s, phone = %s, full_name = %s"):
            auth_user_id = int(params[-1])
            row = next(candidate for candidate in self.auth_users if int(candidate["id"]) == auth_user_id)
            row.update(
                {
                    "email": params[0],
                    "phone": params[1],
                    "full_name": params[2],
                    "role": params[3],
                    "role_display": params[4],
                    "password_hash": params[5],
                    "is_active": 1,
                    "must_change_password": params[6],
                    "updated_at": params[7],
                }
            )
            return FakeResult([])

        if normalized.startswith("UPDATE auth_users SET is_active = 0, updated_at = %s"):
            updated_at, auth_user_id = params
            row = next(candidate for candidate in self.auth_users if int(candidate["id"]) == int(auth_user_id))
            row["is_active"] = 0
            row["updated_at"] = updated_at
            return FakeResult([])

        if normalized.startswith("UPDATE auth_users SET phone = %s, is_active = 0, updated_at = %s"):
            phone, updated_at, auth_user_id = params
            row = next(candidate for candidate in self.auth_users if int(candidate["id"]) == int(auth_user_id))
            row["phone"] = phone
            row["is_active"] = 0
            row["updated_at"] = updated_at
            return FakeResult([])

        if normalized == "DELETE FROM auth_sessions WHERE username = %s":
            self.deleted_sessions.append(str(params[0]))
            return FakeResult([])

        if normalized == "DELETE FROM auth_phone_codes WHERE auth_user_id = %s":
            self.deleted_phone_codes.append(int(params[0]))
            return FakeResult([])

        raise AssertionError(f"Unexpected SQL: {normalized}")


def test_sync_mobile_auth_user_creates_mobile_ops_user_for_eligible_personnel():
    conn = FakeConnection(
        personnel_rows={
            7: {
                "id": 7,
                "full_name": "Cihan Yildiz",
                "role": "Bölge Müdürü",
                "status": "Aktif",
                "phone": "0532 111 22 33",
            }
        }
    )

    sync_mobile_auth_user_for_personnel(conn, personnel_id=7)

    assert len(conn.auth_users) == 1
    created = conn.auth_users[0]
    assert created["email"] == build_mobile_auth_email(7)
    assert created["phone"] == "5321112233"
    assert created["role"] == "mobile_ops"
    assert created["role_display"] == "Mobil Operasyon"
    assert created["is_active"] == 1
    assert created["must_change_password"] == 1


def test_sync_mobile_auth_user_deactivates_when_personnel_becomes_ineligible():
    conn = FakeConnection(
        personnel_rows={
            7: {
                "id": 7,
                "full_name": "Cihan Yildiz",
                "role": "Kurye",
                "status": "Pasif",
                "phone": "0532 111 22 33",
            }
        },
        auth_users=[
            {
                "id": 11,
                "email": build_mobile_auth_email(7),
                "phone": "5321112233",
                "full_name": "Cihan Yildiz",
                "role": "mobile_ops",
                "role_display": "Mobil Operasyon",
                "password_hash": "hashed",
                "is_active": 1,
                "must_change_password": 0,
            }
        ],
    )

    sync_mobile_auth_user_for_personnel(conn, personnel_id=7)

    assert conn.auth_users[0]["is_active"] == 0
    assert build_mobile_auth_email(7) in conn.deleted_sessions
    assert "5321112233" in conn.deleted_sessions
    assert conn.deleted_phone_codes == [11]


def test_sync_mobile_auth_users_creates_and_deactivates_across_bootstrap_pass():
    conn = FakeConnection(
        personnel_rows={
            7: {
                "id": 7,
                "full_name": "Cihan Yildiz",
                "role": "Bölge Müdürü",
                "status": "Aktif",
                "phone": "0532 111 22 33",
            }
        },
        auth_users=[
            {
                "id": 21,
                "email": build_mobile_auth_email(9),
                "phone": "5329998877",
                "full_name": "Eski Kullanici",
                "role": "mobile_ops",
                "role_display": "Mobil Operasyon",
                "password_hash": "hashed",
                "is_active": 1,
                "must_change_password": 0,
            }
        ],
    )

    sync_mobile_auth_users(conn)

    created = next(row for row in conn.auth_users if row["email"] == build_mobile_auth_email(7))
    orphan = next(row for row in conn.auth_users if row["email"] == build_mobile_auth_email(9))
    assert created["is_active"] == 1
    assert created["phone"] == "5321112233"
    assert orphan["is_active"] == 0


def test_sync_mobile_auth_user_releases_conflicting_phone_before_update():
    conn = FakeConnection(
        personnel_rows={
            7: {
                "id": 7,
                "full_name": "Cihan Yıldız",
                "role": "Bölge Müdürü",
                "status": "Aktif",
                "phone": "0532 999 88 77",
            }
        },
        auth_users=[
            {
                "id": 21,
                "email": build_mobile_auth_email(7),
                "phone": "5321112233",
                "full_name": "Cihan Yıldız",
                "role": "mobile_ops",
                "role_display": "Mobil Operasyon",
                "password_hash": "hashed",
                "is_active": 1,
                "must_change_password": 0,
            },
            {
                "id": 22,
                "email": build_mobile_auth_email(8),
                "phone": "5329998877",
                "full_name": "Eski Kullanıcı",
                "role": "mobile_ops",
                "role_display": "Mobil Operasyon",
                "password_hash": "hashed",
                "is_active": 1,
                "must_change_password": 0,
            },
        ],
    )

    sync_mobile_auth_user_for_personnel(conn, personnel_id=7)

    updated = next(row for row in conn.auth_users if int(row["id"]) == 21)
    released = next(row for row in conn.auth_users if int(row["id"]) == 22)
    assert updated["phone"] == "5329998877"
    assert updated["is_active"] == 1
    assert released["phone"] == ""
    assert released["is_active"] == 0
