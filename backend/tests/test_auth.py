from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select

from backend.auth.security import ALGORITHM
from backend.config import settings
from backend.database.models import User


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_ok_and_role_is_student(client, db_session):
    response = client.post(
        "/auth/register",
        json={
            "name": "New User",
            "email": "new@example.com",
            "password": "CorrectHorseBatteryStaple1!",
            "role": "admin",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "student"
    user = db_session.scalar(select(User).where(User.email == "new@example.com"))
    assert user.role == "student"
    assert user.password_hash != "CorrectHorseBatteryStaple1!"
    assert user.password_hash.startswith("$2")


def test_duplicate_email_and_weak_password(client):
    body = {"name": "User", "email": "dup@example.com", "password": "CorrectHorseBatteryStaple1!"}
    assert client.post("/auth/register", json=body).status_code == 201
    duplicate = client.post("/auth/register", json=body)
    assert duplicate.status_code == 409
    weak = client.post(
        "/auth/register",
        json={"name": "Weak", "email": "weak@example.com", "password": "short"},
    )
    assert weak.status_code == 422


def test_login_ok_and_invalid_login_is_indistinguishable(client, student_user):
    valid = client.post(
        "/auth/login",
        json={"email": student_user.email, "password": "CorrectHorseBatteryStaple1!"},
    )
    assert valid.status_code == 200
    assert valid.json()["token_type"] == "bearer"
    bad_password = client.post(
        "/auth/login", json={"email": student_user.email, "password": "wrong"}
    )
    unknown = client.post(
        "/auth/login", json={"email": "unknown@example.com", "password": "wrong"}
    )
    assert bad_password.status_code == unknown.status_code == 401
    assert bad_password.json() == unknown.json()


def test_auth_token_failures(client):
    assert client.get("/auth/me").status_code == 401
    expired = jwt.encode(
        {"sub": "1", "role": "student", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    assert client.get("/auth/me", headers=auth(expired)).status_code == 401
    tampered = expired[:-1] + ("a" if expired[-1] != "a" else "b")
    assert client.get("/auth/me", headers=auth(tampered)).status_code == 401


def test_inactive_user_is_blocked(client, db_session, student_user, student_token):
    student_user.is_active = False
    db_session.commit()
    response = client.get("/auth/me", headers=auth(student_token))
    assert response.status_code == 403
    login = client.post(
        "/auth/login",
        json={"email": student_user.email, "password": "CorrectHorseBatteryStaple1!"},
    )
    assert login.status_code == 401


def test_role_permissions_matrix(client, student_token, staff_token, admin_token):
    cases = [
        (None, 401),
        (student_token, 403),
        (staff_token, 200),
        (admin_token, 200),
    ]
    for token, expected in cases:
        headers = auth(token) if token else {}
        assert client.get("/admin/users", headers=headers).status_code == expected
        assert client.get("/admin/notices", headers=headers).status_code == expected
        assert client.get("/admin/feedback", headers=headers).status_code == expected
        assert client.get("/admin/stats", headers=headers).status_code == expected
    for token, expected in ((None, 401), (student_token, 403), (staff_token, 200), (admin_token, 200)):
        headers = auth(token) if token else {}
        response = client.get("/documents", headers=headers)
        assert response.status_code == expected


def test_student_cannot_manage_notices_or_documents(client, student_token):
    headers = auth(student_token)
    assert client.post("/notices", json={"title": "x", "content": "y"}, headers=headers).status_code == 403
    assert client.put("/notices/1", json={"title": "x"}, headers=headers).status_code == 403
    assert client.delete("/notices/1", headers=headers).status_code == 403
    upload = client.post(
        "/documents/upload",
        files={"file": ("x.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 403
