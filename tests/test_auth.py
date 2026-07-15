import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import myjob_server
from app_auth import (
    PASSWORD_ITERATIONS,
    AuthManager,
    DEFAULT_SUPERADMIN_PASSWORD,
    DEFAULT_SUPERADMIN_USERNAME,
    LoginRateLimiter,
    _b64encode,
)


USER_PASSWORD = "Strong@123"


def test_auth_manager_bootstraps_superadmin_and_never_grants_admin_on_registration(tmp_path: Path):
    path = tmp_path / "auth.db"
    manager = AuthManager(path, session_hours=1)
    try:
        superadmin = manager.authenticate(DEFAULT_SUPERADMIN_USERNAME, DEFAULT_SUPERADMIN_PASSWORD)
        assert superadmin is not None
        assert superadmin["role"] == "superadmin"
        assert superadmin["must_change_password"] is True

        user = manager.register("User0001", USER_PASSWORD)
        assert user["role"] == "user"
        assert manager.authenticate("User0001", USER_PASSWORD)["role"] == "user"
        assert USER_PASSWORD.encode() not in path.read_bytes()

        token = manager.issue_token(user)
        session = manager.verify_token(token)
        assert session["username"] == "User0001"
        manager.end_session(session["sid"])
        assert manager.verify_token(token) is None
    finally:
        manager.close()


@pytest.mark.parametrize(
    "username",
    [
        "abcdefgh",
        "12345678",
        "User123",
        "User123456789",
        "user_name",
        "user-name",
        "中文User123",
    ],
)
def test_new_user_and_admin_username_rules(username: str, tmp_path: Path):
    manager = AuthManager(tmp_path / "auth.db")
    try:
        with pytest.raises(ValueError, match="8-12"):
            manager.register(username, USER_PASSWORD)
        with pytest.raises(ValueError, match="8-12"):
            manager.create_admin(username, USER_PASSWORD)
    finally:
        manager.close()


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Sh1!", "8-128"),
        ("A" * 125 + "a1!x", "8-128"),
        ("NOLOWERCASE1!", "小写"),
        ("nouppercase1!", "大写"),
        ("NoDigits!!", "数字"),
        ("NoSpecial1", "特殊"),
    ],
)
def test_new_user_and_admin_password_rules(password: str, message: str, tmp_path: Path):
    manager = AuthManager(tmp_path / "auth.db")
    try:
        with pytest.raises(ValueError, match=message):
            manager.register("User0001", password)
        with pytest.raises(ValueError, match=message):
            manager.create_admin("Admin001", password)
    finally:
        manager.close()


def test_legacy_credentials_can_login_and_change_to_a_compliant_password(tmp_path: Path):
    path = tmp_path / "auth.db"
    manager = AuthManager(path)
    legacy_username = "legacy-user"
    legacy_password = "oldpass"
    salt = b"legacy-user-salt"
    try:
        manager._db.execute(
            """INSERT INTO users(
                   username,password_salt,password_hash,password_iterations,role,created_at
               ) VALUES(?,?,?,?, 'user', ?)""",
            (
                legacy_username,
                _b64encode(salt),
                _b64encode(manager._derive_password(legacy_password, salt)),
                PASSWORD_ITERATIONS,
                int(time.time()),
            ),
        )
        manager._db.commit()

        legacy_user = manager.authenticate(legacy_username, legacy_password)
        assert legacy_user is not None
        with pytest.raises(ValueError, match="大写"):
            manager.change_password(legacy_user["id"], legacy_password, "stillweak1!")

        updated = manager.change_password(legacy_user["id"], legacy_password, "Modern@123")
        assert updated["username"] == legacy_username
        assert manager.authenticate(legacy_username, "Modern@123") is not None
    finally:
        manager.close()


def test_presence_heartbeat_is_low_frequency_and_counts_user_time(tmp_path: Path):
    manager = AuthManager(tmp_path / "auth.db")
    try:
        user = manager.register("Heartbeat1", USER_PASSWORD)
        session = manager.verify_token(manager.issue_token(user))
        before = manager.admin_overview()["metrics"]["total_online_seconds"]

        manager.heartbeat(session["sid"])
        assert manager.admin_overview()["metrics"]["total_online_seconds"] == before

        manager._sessions[session["sid"]]["persisted_at"] -= 61
        manager.heartbeat(session["sid"])
        overview = manager.admin_overview()
        assert overview["metrics"]["online"] == 1
        assert overview["metrics"]["total_online_seconds"] >= 60
        assert overview["series"][-1]["active_users"] == 1
    finally:
        manager.close()


def test_api_registration_admin_portal_permissions_and_account_controls(tmp_path: Path, monkeypatch):
    manager = AuthManager(tmp_path / "auth.db")
    monkeypatch.setattr(myjob_server, "auth_manager", manager)
    monkeypatch.setattr(myjob_server, "login_limiter", LoginRateLimiter())
    admin_client = TestClient(myjob_server.app)
    user_client = TestClient(myjob_server.app)
    try:
        assert user_client.get("/api/health").status_code == 200
        protected = user_client.get("/api/resumes/master")
        assert protected.status_code == 401
        assert protected.json()["code"] == "AUTH_REQUIRED"

        status = user_client.get("/api/auth/status").json()
        assert status["registration_enabled"] is True
        assert status["authenticated"] is False

        invalid_username = user_client.post(
            "/api/auth/register",
            json={"username": "web-user", "password": "WebUser@123"},
        )
        assert invalid_username.status_code == 422
        assert "8-12" in invalid_username.json()["detail"]

        invalid_password = user_client.post(
            "/api/auth/register",
            json={"username": "WebUser01", "password": "lowercase1!"},
        )
        assert invalid_password.status_code == 422
        assert "大写" in invalid_password.json()["detail"]

        registration = user_client.post(
            "/api/auth/register",
            json={"username": "WebUser01", "password": "WebUser@123", "role": "admin"},
        )
        assert registration.status_code == 201
        assert registration.json()["user"]["role"] == "user"
        assert registration.json()["user"]["role"] not in {"admin", "superadmin"}
        assert user_client.get("/api/resumes/master").status_code == 200
        assert user_client.get("/api/admin/overview").status_code == 403
        assert user_client.post("/api/auth/heartbeat").status_code == 200

        admin_login = admin_client.post(
            "/api/admin/login",
            json={"username": DEFAULT_SUPERADMIN_USERNAME, "password": DEFAULT_SUPERADMIN_PASSWORD},
        )
        assert admin_login.status_code == 200
        assert admin_login.json()["user"]["role"] == "superadmin"
        assert admin_client.get("/api/admin/overview").status_code == 403

        rejected_password_change = admin_client.post(
            "/api/auth/change-password",
            json={"current_password": DEFAULT_SUPERADMIN_PASSWORD, "new_password": "NoSpecial1"},
        )
        assert rejected_password_change.status_code == 422
        assert "特殊" in rejected_password_change.json()["detail"]

        password_change = admin_client.post(
            "/api/auth/change-password",
            json={"current_password": DEFAULT_SUPERADMIN_PASSWORD, "new_password": "NewAdmin@123"},
        )
        assert password_change.status_code == 200
        assert password_change.json()["user"]["must_change_password"] is False

        overview = admin_client.get("/api/admin/overview")
        assert overview.status_code == 200
        assert overview.json()["metrics"]["registered"] == 1
        assert overview.json()["metrics"]["admins"] == 1

        invalid_admin = admin_client.post(
            "/api/admin/accounts",
            json={"username": "ops-admin", "password": "OpsAdmin@123"},
        )
        assert invalid_admin.status_code == 422
        assert "8-12" in invalid_admin.json()["detail"]

        created_admin = admin_client.post(
            "/api/admin/accounts",
            json={"username": "OpsAdmin01", "password": "OpsAdmin@123"},
        )
        assert created_admin.status_code == 200
        assert created_admin.json()["user"]["role"] == "admin"
        assert created_admin.json()["user"]["must_change_password"] is True

        users = admin_client.get("/api/admin/users").json()["users"]
        web_user = next(item for item in users if item["username"] == "WebUser01")
        disabled = admin_client.put(f"/api/admin/users/{web_user['id']}/status", json={"active": False})
        assert disabled.status_code == 200
        assert disabled.json()["user"]["is_active"] is False

        assert user_client.get("/api/resumes/master").status_code == 401
        failed_login = user_client.post(
            "/api/auth/login", json={"username": "WebUser01", "password": "WebUser@123"}
        )
        assert failed_login.status_code == 401

        registration_toggle = admin_client.put("/api/admin/registration", json={"enabled": False})
        assert registration_toggle.status_code == 200
        blocked_registration = TestClient(myjob_server.app).post(
            "/api/auth/register",
            json={"username": "Second002", "password": "Second@456"},
        )
        assert blocked_registration.status_code == 422
    finally:
        admin_client.close()
        user_client.close()
        manager.close()


def test_normal_user_cannot_use_admin_login(tmp_path: Path, monkeypatch):
    manager = AuthManager(tmp_path / "auth.db")
    monkeypatch.setattr(myjob_server, "auth_manager", manager)
    monkeypatch.setattr(myjob_server, "login_limiter", LoginRateLimiter())
    manager.register("Normal001", USER_PASSWORD)
    client = TestClient(myjob_server.app)
    try:
        response = client.post(
            "/api/admin/login", json={"username": "Normal001", "password": USER_PASSWORD}
        )
        assert response.status_code == 401
    finally:
        client.close()
        manager.close()


def test_admin_accounts_cannot_use_normal_user_login(tmp_path: Path, monkeypatch):
    manager = AuthManager(tmp_path / "auth.db")
    monkeypatch.setattr(myjob_server, "auth_manager", manager)
    monkeypatch.setattr(myjob_server, "login_limiter", LoginRateLimiter())
    admin = manager.create_admin("OpsAdmin01", USER_PASSWORD)
    credentials = (
        (DEFAULT_SUPERADMIN_USERNAME, DEFAULT_SUPERADMIN_PASSWORD, "superadmin"),
        (admin["username"], USER_PASSWORD, "admin"),
    )
    try:
        for username, password, role in credentials:
            with TestClient(myjob_server.app) as client:
                rejected = client.post(
                    "/api/auth/login", json={"username": username, "password": password}
                )
                assert rejected.status_code == 401

                accepted = client.post(
                    "/api/admin/login", json={"username": username, "password": password}
                )
                assert accepted.status_code == 200
                assert accepted.json()["user"]["role"] == role
    finally:
        manager.close()


def test_root_and_admin_routes_prefer_built_vue_frontend():
    assert 'id="app"' in myjob_server.index().body.decode("utf-8")
