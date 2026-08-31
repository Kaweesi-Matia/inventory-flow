from app.models.user import UserRole
from tests.conftest import auth_headers, make_user


def test_register_creates_sales_user_by_default(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "newuser@test.dev", "password": "Password123!", "full_name": "New User"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "SALES_USER"


def test_register_respects_selected_role(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "newadmin@test.dev",
            "password": "Password123!",
            "full_name": "New Admin",
            "role": "ADMIN",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "ADMIN"


def test_register_duplicate_email_fails(client, db):
    make_user(db, email="dupe@test.dev")
    resp = client.post(
        "/api/auth/register",
        json={"email": "dupe@test.dev", "password": "Password123!", "full_name": "Dupe"},
    )
    assert resp.status_code == 409


def test_login_wrong_password_fails(client, db):
    make_user(db, email="loginuser@test.dev")
    resp = client.post(
        "/api/auth/login-json", json={"email": "loginuser@test.dev", "password": "WrongPass1!"}
    )
    assert resp.status_code == 401


def test_login_success_returns_token(client, db):
    make_user(db, email="loginok@test.dev")
    resp = client.post(
        "/api/auth/login-json", json={"email": "loginok@test.dev", "password": "Password123!"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_me_requires_authentication(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, db):
    make_user(db, email="whoami@test.dev", role=UserRole.INVENTORY_MANAGER)
    headers = auth_headers(client, "whoami@test.dev")
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "whoami@test.dev"


def test_change_password_wrong_current_fails(client, db):
    make_user(db, email="changepw@test.dev")
    headers = auth_headers(client, "changepw@test.dev")
    resp = client.put(
        "/api/auth/change-password",
        json={"current_password": "WrongOne1!", "new_password": "NewPass123!"},
        headers=headers,
    )
    assert resp.status_code == 400
