"""Multi-user authentication and low-write presence analytics.

Passwords and sessions live in a small SQLite database separate from business
data. Signed session cookies are verified from an in-memory cache, while a
one-minute heartbeat persists presence and online duration.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


AUTH_COOKIE_NAME = "lakejob_session"
PASSWORD_ITERATIONS = 260_000
USERNAME_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9]{8,12}$")
PASSWORD_UPPER_RE = re.compile(r"[A-Z]")
PASSWORD_LOWER_RE = re.compile(r"[a-z]")
PASSWORD_DIGIT_RE = re.compile(r"[0-9]")
PASSWORD_SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")
ONLINE_WINDOW_SECONDS = 150
HEARTBEAT_WRITE_SECONDS = 50
DEFAULT_SUPERADMIN_USERNAME = "Admin"
DEFAULT_SUPERADMIN_PASSWORD = "123456*"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode((value + "=" * (-len(value) % 4)).encode("ascii"))


def _fingerprint(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:24]


class AuthManager:
    """SQLite-backed users with cached, signed sessions."""

    def __init__(self, path: Path, session_hours: int = 12, legacy_path: Optional[Path] = None):
        self.path = Path(path)
        self.session_seconds = max(1, min(int(session_hours), 24 * 30)) * 3600
        self._lock = threading.RLock()
        self._sessions: dict[str, dict] = {}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._init_db()
        if legacy_path:
            self._migrate_legacy(Path(legacy_path))
        self._ensure_superadmin()
        self._signing_key = self._load_signing_key()
        self._load_sessions()

    def _init_db(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_iterations INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                last_login_at INTEGER,
                last_seen_at INTEGER,
                login_count INTEGER NOT NULL DEFAULT 0,
                total_online_seconds INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                issued_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                last_seen_at INTEGER NOT NULL,
                ended_at INTEGER,
                active_seconds INTEGER NOT NULL DEFAULT 0,
                ip_hash TEXT,
                user_agent_hash TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, ended_at);
            CREATE INDEX IF NOT EXISTS idx_sessions_seen ON sessions(last_seen_at, ended_at);
            CREATE TABLE IF NOT EXISTS activity_daily (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                activity_date TEXT NOT NULL,
                online_seconds INTEGER NOT NULL DEFAULT 0,
                login_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(user_id, activity_date)
            );
            CREATE TABLE IF NOT EXISTS auth_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        columns = {row["name"] for row in self._db.execute("PRAGMA table_info(users)").fetchall()}
        if "must_change_password" not in columns:
            self._db.execute(
                "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0"
            )
        self._db.execute("INSERT OR IGNORE INTO auth_meta(key,value) VALUES('registration_enabled','true')")
        self._db.commit()

    def _migrate_legacy(self, legacy_path: Path) -> None:
        if self.user_count or not legacy_path.exists():
            return
        try:
            data = json.loads(legacy_path.read_text(encoding="utf-8"))
            if not data.get("username") or not data.get("password_hash"):
                return
            now = int(time.time())
            self._db.execute(
                """INSERT INTO users(username,password_salt,password_hash,password_iterations,role,created_at)
                   VALUES(?,?,?,?, 'superadmin', ?)""",
                (
                    data["username"],
                    data["password_salt"],
                    data["password_hash"],
                    int(data.get("password_iterations") or PASSWORD_ITERATIONS),
                    now,
                ),
            )
            if data.get("signing_key"):
                self._db.execute(
                    "INSERT OR REPLACE INTO auth_meta(key,value) VALUES('signing_key',?)",
                    (data["signing_key"],),
                )
            self._db.commit()
        except Exception:
            self._db.rollback()

    def _ensure_superadmin(self) -> None:
        """Create the documented local superadmin on a new installation."""
        existing_superadmin = self._db.execute(
            "SELECT id FROM users WHERE role='superadmin' LIMIT 1"
        ).fetchone()
        if existing_superadmin:
            return
        username = (
            os.getenv("MYJOB_SUPERADMIN_USERNAME")
            or os.getenv("LAKEJOB_SUPERADMIN_USERNAME")
            or DEFAULT_SUPERADMIN_USERNAME
        )
        password = (
            os.getenv("MYJOB_SUPERADMIN_PASSWORD")
            or os.getenv("LAKEJOB_SUPERADMIN_PASSWORD")
            or DEFAULT_SUPERADMIN_PASSWORD
        )
        uses_documented_default = (
            username == DEFAULT_SUPERADMIN_USERNAME
            and password == DEFAULT_SUPERADMIN_PASSWORD
        )
        if not uses_documented_default:
            username, password = self._validate_credentials(username, password)
        existing = self._db.execute(
            "SELECT id FROM users WHERE username=? COLLATE NOCASE", (username,)
        ).fetchone()
        if existing:
            salt = secrets.token_bytes(16)
            self._db.execute(
                """UPDATE users SET role='superadmin',is_active=1,must_change_password=1,
                          password_salt=?,password_hash=?,password_iterations=? WHERE id=?""",
                (
                    _b64encode(salt),
                    _b64encode(self._derive_password(password, salt)),
                    PASSWORD_ITERATIONS,
                    existing["id"],
                ),
            )
            self._db.commit()
            return
        self._insert_user(
            username,
            password,
            role="superadmin",
            must_change_password=True,
            validate_password=not uses_documented_default,
        )

    def _load_signing_key(self) -> bytes:
        row = self._db.execute("SELECT value FROM auth_meta WHERE key='signing_key'").fetchone()
        if row:
            return _b64decode(row["value"])
        key = secrets.token_bytes(32)
        self._db.execute(
            "INSERT INTO auth_meta(key,value) VALUES('signing_key',?)",
            (_b64encode(key),),
        )
        self._db.commit()
        return key

    def _load_sessions(self) -> None:
        now = int(time.time())
        rows = self._db.execute(
            """SELECT s.*,u.username,u.role,u.is_active,u.must_change_password FROM sessions s
               JOIN users u ON u.id=s.user_id
               WHERE s.ended_at IS NULL AND s.expires_at>? AND u.is_active=1""",
            (now,),
        ).fetchall()
        self._sessions = {
            row["id"]: {
                "sid": row["id"],
                "user_id": row["user_id"],
                "username": row["username"],
                "role": row["role"],
                "must_change_password": bool(row["must_change_password"]),
                "exp": row["expires_at"],
                "last_seen": row["last_seen_at"],
                "persisted_at": row["last_seen_at"],
            }
            for row in rows
        }

    @property
    def user_count(self) -> int:
        row = self._db.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
        return int(row["cnt"] if row else 0)

    @property
    def configured(self) -> bool:
        return self.user_count > 0

    @property
    def registration_enabled(self) -> bool:
        row = self._db.execute("SELECT value FROM auth_meta WHERE key='registration_enabled'").fetchone()
        return not row or row["value"] == "true"

    @staticmethod
    def _validate_username(username: str) -> str:
        username = str(username or "").strip()
        if not USERNAME_RE.fullmatch(username):
            raise ValueError("用户名必须为 8-12 位，只能包含英文字母和数字，且两者都要有")
        return username

    @staticmethod
    def _validate_password(password: str) -> str:
        password = str(password or "")
        if len(password) < 8:
            raise ValueError("密码必须为 8-128 位")
        if len(password) > 128:
            raise ValueError("密码必须为 8-128 位")
        if not PASSWORD_UPPER_RE.search(password):
            raise ValueError("密码必须包含至少一个英文大写字母")
        if not PASSWORD_LOWER_RE.search(password):
            raise ValueError("密码必须包含至少一个英文小写字母")
        if not PASSWORD_DIGIT_RE.search(password):
            raise ValueError("密码必须包含至少一个数字")
        if not PASSWORD_SPECIAL_RE.search(password):
            raise ValueError("密码必须包含至少一个特殊字符")
        return password

    @classmethod
    def _validate_credentials(cls, username: str, password: str) -> tuple[str, str]:
        username = cls._validate_username(username)
        password = cls._validate_password(password)
        return username, password

    @staticmethod
    def _derive_password(password: str, salt: bytes, iterations: int = PASSWORD_ITERATIONS) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)

    @staticmethod
    def _user_payload(row) -> dict:
        return {
            "id": int(row["id"]),
            "user_id": int(row["id"]),
            "username": row["username"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "must_change_password": bool(row["must_change_password"]),
        }

    def _insert_user(
        self,
        username: str,
        password: str,
        role: str,
        must_change_password: bool = False,
        validate_password: bool = True,
    ) -> dict:
        if role not in {"user", "admin", "superadmin"}:
            raise ValueError("无效的账号角色")
        if validate_password:
            username, password = self._validate_credentials(username, password)
        else:
            username = str(username or "").strip()
            password = str(password or "")
            if (
                role != "superadmin"
                or username != DEFAULT_SUPERADMIN_USERNAME
                or password != DEFAULT_SUPERADMIN_PASSWORD
            ):
                raise ValueError("默认超级管理员配置无效")
        salt = secrets.token_bytes(16)
        now = int(time.time())
        try:
            cursor = self._db.execute(
                """INSERT INTO users(
                       username,password_salt,password_hash,password_iterations,role,
                       is_active,must_change_password,created_at
                   ) VALUES(?,?,?,?,?,1,?,?)""",
                (
                    username,
                    _b64encode(salt),
                    _b64encode(self._derive_password(password, salt)),
                    PASSWORD_ITERATIONS,
                    role,
                    1 if must_change_password else 0,
                    now,
                ),
            )
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("用户名已存在") from exc
        row = self._db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
        return self._user_payload(row)

    def register(self, username: str, password: str) -> dict:
        """Register a normal web user. Public registration never grants admin roles."""
        with self._lock:
            if not self.registration_enabled:
                raise ValueError("当前已关闭新用户注册")
            return self._insert_user(username, password, role="user")

    def create_admin(self, username: str, password: str) -> dict:
        """Create an administrator from the protected superadmin console."""
        with self._lock:
            return self._insert_user(username, password, role="admin", must_change_password=True)

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM users WHERE username=? COLLATE NOCASE",
                (str(username or "").strip(),),
            ).fetchone()
            if not row or not row["is_active"]:
                return None
            try:
                actual = self._derive_password(
                    str(password or ""),
                    _b64decode(row["password_salt"]),
                    int(row["password_iterations"]),
                )
                expected = _b64decode(row["password_hash"])
            except Exception:
                return None
            return self._user_payload(row) if hmac.compare_digest(actual, expected) else None

    def _token(self, session: dict) -> str:
        payload = {
            "sid": session["sid"],
            "uid": session["user_id"],
            "sub": session["username"],
                "role": session["role"],
                "must_change_password": session["must_change_password"],
                "exp": session["exp"],
        }
        encoded = _b64encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode())
        signature = _b64encode(hmac.new(self._signing_key, encoded.encode("ascii"), hashlib.sha256).digest())
        return f"{encoded}.{signature}"

    def issue_token(self, user: dict, ip: str = "", user_agent: str = "") -> str:
        with self._lock:
            now = int(time.time())
            sid = _b64encode(secrets.token_bytes(18))
            session = {
                "sid": sid,
                "user_id": int(user["id"]),
                "username": user["username"],
                "role": user["role"],
                "must_change_password": bool(user.get("must_change_password")),
                "exp": now + self.session_seconds,
                "last_seen": now,
                "persisted_at": now,
            }
            self._db.execute(
                """INSERT INTO sessions(id,user_id,issued_at,expires_at,last_seen_at,ip_hash,user_agent_hash)
                   VALUES(?,?,?,?,?,?,?)""",
                (sid, user["id"], now, session["exp"], now, _fingerprint(ip), _fingerprint(user_agent)),
            )
            self._db.execute(
                """UPDATE users SET last_login_at=?,last_seen_at=?,login_count=login_count+1 WHERE id=?""",
                (now, now, user["id"]),
            )
            self._db.execute(
                """INSERT INTO activity_daily(user_id,activity_date,login_count) VALUES(?,?,1)
                   ON CONFLICT(user_id,activity_date) DO UPDATE SET login_count=login_count+1""",
                (user["id"], datetime.now().date().isoformat()),
            )
            self._db.commit()
            self._sessions[sid] = session
            return self._token(session)

    def verify_token(self, token: str) -> Optional[dict]:
        if not token:
            return None
        with self._lock:
            try:
                encoded, supplied_signature = token.split(".", 1)
                expected_signature = _b64encode(
                    hmac.new(self._signing_key, encoded.encode("ascii"), hashlib.sha256).digest()
                )
                if not hmac.compare_digest(supplied_signature, expected_signature):
                    return None
                payload = json.loads(_b64decode(encoded).decode("utf-8"))
                session = self._sessions.get(payload.get("sid"))
                if not session or session["exp"] <= int(time.time()):
                    return None
                if session["user_id"] != int(payload.get("uid") or 0):
                    return None
                return {
                    "sid": session["sid"],
                    "id": session["user_id"],
                    "user_id": session["user_id"],
                    "sub": session["username"],
                    "username": session["username"],
                    "role": session["role"],
                    "must_change_password": session["must_change_password"],
                    "exp": session["exp"],
                }
            except Exception:
                return None

    def heartbeat(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError("会话已失效")
            now = int(time.time())
            session["last_seen"] = now
            if now - session["persisted_at"] >= HEARTBEAT_WRITE_SECONDS:
                delta = min(max(0, now - session["persisted_at"]), 90)
                self._db.execute(
                    "UPDATE sessions SET last_seen_at=?,active_seconds=active_seconds+? WHERE id=?",
                    (now, delta, session_id),
                )
                self._db.execute(
                    "UPDATE users SET last_seen_at=?,total_online_seconds=total_online_seconds+? WHERE id=?",
                    (now, delta, session["user_id"]),
                )
                self._db.execute(
                    """INSERT INTO activity_daily(user_id,activity_date,online_seconds) VALUES(?,?,?)
                       ON CONFLICT(user_id,activity_date) DO UPDATE SET online_seconds=online_seconds+excluded.online_seconds""",
                    (session["user_id"], datetime.now().date().isoformat(), delta),
                )
                self._db.commit()
                session["persisted_at"] = now
            return {"online": True, "server_time": now}

    def end_session(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if not session:
                return
            now = int(time.time())
            delta = min(max(0, now - session["persisted_at"]), 90)
            self._db.execute(
                "UPDATE sessions SET ended_at=?,last_seen_at=?,active_seconds=active_seconds+? WHERE id=?",
                (now, now, delta, session_id),
            )
            self._db.execute(
                "UPDATE users SET last_seen_at=?,total_online_seconds=total_online_seconds+? WHERE id=?",
                (now, delta, session["user_id"]),
            )
            self._db.execute(
                """INSERT INTO activity_daily(user_id,activity_date,online_seconds) VALUES(?,?,?)
                   ON CONFLICT(user_id,activity_date) DO UPDATE SET online_seconds=online_seconds+excluded.online_seconds""",
                (session["user_id"], datetime.now().date().isoformat(), delta),
            )
            self._db.commit()

    def change_password(self, user_id: int, current_password: str, new_password: str) -> dict:
        with self._lock:
            row = self._db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not row or not self.authenticate(row["username"], current_password):
                raise ValueError("当前密码不正确")
            new_password = self._validate_password(new_password)
            salt = secrets.token_bytes(16)
            self._db.execute(
                """UPDATE users SET password_salt=?,password_hash=?,password_iterations=?,
                          must_change_password=0 WHERE id=?""",
                (_b64encode(salt), _b64encode(self._derive_password(new_password, salt)), PASSWORD_ITERATIONS, user_id),
            )
            for sid, session in list(self._sessions.items()):
                if session["user_id"] == user_id:
                    self._sessions.pop(sid, None)
                    self._db.execute("UPDATE sessions SET ended_at=? WHERE id=?", (int(time.time()), sid))
            self._db.commit()
            updated = self._db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return self._user_payload(updated)

    def set_registration_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO auth_meta(key,value) VALUES('registration_enabled',?)",
                ("true" if enabled else "false",),
            )
            self._db.commit()

    def set_user_active(self, actor_user_id: int, user_id: int, active: bool) -> dict:
        if actor_user_id == user_id and not active:
            raise ValueError("不能停用当前管理员账号")
        with self._lock:
            row = self._db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not row:
                raise ValueError("用户不存在")
            if not active and row["role"] == "superadmin":
                count = self._db.execute(
                    "SELECT COUNT(*) AS cnt FROM users WHERE role='superadmin' AND is_active=1"
                ).fetchone()["cnt"]
                if int(count or 0) <= 1:
                    raise ValueError("不能停用最后一个超级管理员")
            self._db.execute("UPDATE users SET is_active=? WHERE id=?", (1 if active else 0, user_id))
            if not active:
                for sid, session in list(self._sessions.items()):
                    if session["user_id"] == user_id:
                        self._sessions.pop(sid, None)
                        self._db.execute("UPDATE sessions SET ended_at=? WHERE id=?", (int(time.time()), sid))
            self._db.commit()
            row = self._db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return self._admin_user_row(row)

    def _admin_user_row(self, row) -> dict:
        now = int(time.time())
        return {
            "id": int(row["id"]),
            "username": row["username"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "must_change_password": bool(row["must_change_password"]),
            "online": bool(row["last_seen_at"] and now - int(row["last_seen_at"]) <= ONLINE_WINDOW_SECONDS),
            "created_at": row["created_at"],
            "last_login_at": row["last_login_at"],
            "last_seen_at": row["last_seen_at"],
            "login_count": int(row["login_count"] or 0),
            "total_online_seconds": int(row["total_online_seconds"] or 0),
        }

    def list_users(self, limit: int = 100) -> list[dict]:
        rows = self._db.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ?",
            (max(1, min(int(limit), 500)),),
        ).fetchall()
        return [self._admin_user_row(row) for row in rows]

    def get_user(self, user_id: int) -> Optional[dict]:
        row = self._db.execute("SELECT * FROM users WHERE id=?", (int(user_id),)).fetchone()
        return self._admin_user_row(row) if row else None

    def admin_overview(self, days: int = 7) -> dict:
        days = max(1, min(int(days), 30))
        now = int(time.time())
        today_start = int(datetime.combine(datetime.now().date(), datetime.min.time()).timestamp())
        totals = self._db.execute(
            """SELECT SUM(CASE WHEN role='user' THEN 1 ELSE 0 END) AS registered,
                      SUM(CASE WHEN role IN ('admin','superadmin') THEN 1 ELSE 0 END) AS admins,
                      SUM(CASE WHEN role='user' AND is_active=1 THEN 1 ELSE 0 END) AS enabled,
                      SUM(CASE WHEN role='user' AND last_seen_at>=? THEN 1 ELSE 0 END) AS active_today,
                      COALESCE(SUM(CASE WHEN role='user' THEN total_online_seconds ELSE 0 END),0) AS total_online_seconds,
                      COALESCE(SUM(CASE WHEN role='user' THEN login_count ELSE 0 END),0) AS total_logins
               FROM users""",
            (today_start,),
        ).fetchone()
        online = self._db.execute(
            """SELECT COUNT(DISTINCT s.user_id) AS cnt FROM sessions s
               JOIN users u ON u.id=s.user_id
               WHERE u.role='user' AND s.ended_at IS NULL AND s.last_seen_at>=?""",
            (now - ONLINE_WINDOW_SECONDS,),
        ).fetchone()["cnt"]
        series = []
        start_date = datetime.now().date() - timedelta(days=days - 1)
        for offset in range(days):
            day = start_date + timedelta(days=offset)
            day_text = day.isoformat()
            activity = self._db.execute(
                """SELECT COUNT(*) AS active_users,COALESCE(SUM(a.online_seconds),0) AS online_seconds,
                          COALESCE(SUM(a.login_count),0) AS logins
                   FROM activity_daily a JOIN users u ON u.id=a.user_id
                   WHERE u.role='user' AND a.activity_date=?""",
                (day_text,),
            ).fetchone()
            registrations = self._db.execute(
                """SELECT COUNT(*) AS cnt FROM users
                   WHERE role='user' AND date(created_at,'unixepoch','localtime')=?""",
                (day_text,),
            ).fetchone()["cnt"]
            series.append(
                {
                    "date": day_text,
                    "registrations": int(registrations or 0),
                    "active_users": int(activity["active_users"] or 0),
                    "online_seconds": int(activity["online_seconds"] or 0),
                    "logins": int(activity["logins"] or 0),
                }
            )
        recent_sessions = self._db.execute(
            """SELECT s.id,s.issued_at,s.last_seen_at,s.ended_at,s.active_seconds,u.username,u.role
               FROM sessions s JOIN users u ON u.id=s.user_id ORDER BY s.issued_at DESC LIMIT 12"""
        ).fetchall()
        return {
            "metrics": {
                "registered": int(totals["registered"] or 0),
                "admins": int(totals["admins"] or 0),
                "enabled": int(totals["enabled"] or 0),
                "online": int(online or 0),
                "active_today": int(totals["active_today"] or 0),
                "total_online_seconds": int(totals["total_online_seconds"] or 0),
                "total_logins": int(totals["total_logins"] or 0),
            },
            "series": series,
            "recent_sessions": [dict(row) for row in recent_sessions],
            "registration_enabled": self.registration_enabled,
            "online_window_seconds": ONLINE_WINDOW_SECONDS,
        }

    def close(self) -> None:
        with self._lock:
            self._db.close()


class LoginRateLimiter:
    """Small in-memory limiter; failed logins do not write to SQLite."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int:
        now = time.time()
        with self._lock:
            attempts = [stamp for stamp in self._attempts.get(key, []) if now - stamp < self.window_seconds]
            self._attempts[key] = attempts
            return 0 if len(attempts) < self.max_attempts else max(1, int(self.window_seconds - (now - attempts[0])))

    def failure(self, key: str) -> None:
        with self._lock:
            self._attempts.setdefault(key, []).append(time.time())

    def success(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
