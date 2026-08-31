"""
Tests run against a real PostgreSQL database (set TEST_DATABASE_URL, or
they fall back to DATABASE_URL with a `_test` suffix convention). We use
Postgres rather than SQLite because the whole point of this project is
Postgres-specific behavior: row-level locking, CHECK constraints, ENUM
types, and NUMERIC precision — none of which SQLite enforces the same
way, so a SQLite test suite would give false confidence.
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.database.base import Base
from app.database.connection import get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.warehouse import Warehouse, WarehouseStatus

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://supplychainx:supplychainx@localhost:5432/supplychainx_test",
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, role=UserRole.ADMIN, email=None):
    user = User(
        email=email or f"{uuid.uuid4().hex[:8]}@test.dev",
        hashed_password=hash_password("Password123!"),
        full_name="Test User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_warehouse(db, code=None):
    warehouse = Warehouse(name="Test Warehouse", code=code or f"WH-{uuid.uuid4().hex[:6]}", status=WarehouseStatus.ACTIVE)
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


def auth_headers(client, email, password="Password123!"):
    resp = client.post("/api/auth/login-json", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
