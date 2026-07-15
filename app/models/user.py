"""
user.py -- users table repository
PBKDF2-SHA256 + random salt, 100k iterations. All SQL uses ? placeholders.
Uses role_id (FK to roles table) instead of role string.
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime

from app.models.db import get_connection


def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex()


class UserRepository:

    @staticmethod
    def create_user(username: str, password: str, role_id: int = 2) -> bool:
        salt = secrets.token_bytes(16)
        password_hash = _hash_password(password, salt)
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, salt, role_id) VALUES (?, ?, ?, ?)",
                    (username, password_hash, salt.hex(), role_id),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def verify_user(username: str, password: str) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT password_hash, salt, status FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return False
        if row["status"] == 0:
            return False
        salt = bytes.fromhex(row["salt"])
        computed_hash = _hash_password(password, salt)
        return secrets.compare_digest(computed_hash, row["password_hash"])

    @staticmethod
    def update_last_login(username: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE username = ?",
                (now, username),
            )
            conn.commit()

    @staticmethod
    def get_user_by_username(username: str):
        with get_connection() as conn:
            return conn.execute(
                """SELECT u.id, u.username, u.role_id, r.name AS role_name,
                   u.status, u.last_login, u.created_at
                   FROM users u LEFT JOIN roles r ON u.role_id = r.id
                   WHERE u.username = ?""",
                (username,),
            ).fetchone()

    @staticmethod
    def get_user_count(search: str = "") -> int:
        with get_connection() as conn:
            if search:
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM users WHERE username LIKE ?",
                    (f"%{search}%",),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
        return row["cnt"] if row else 0

    @staticmethod
    def get_all_users(page: int = 1, page_size: int = 20, search: str = "") -> list:
        offset = (page - 1) * page_size
        with get_connection() as conn:
            if search:
                rows = conn.execute(
                    """SELECT u.id, u.username, u.role_id, r.name AS role_name,
                       u.status, u.last_login, u.created_at
                       FROM users u LEFT JOIN roles r ON u.role_id = r.id
                       WHERE u.username LIKE ?
                       ORDER BY u.id DESC LIMIT ? OFFSET ?""",
                    (f"%{search}%", page_size, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT u.id, u.username, u.role_id, r.name AS role_name,
                       u.status, u.last_login, u.created_at
                       FROM users u LEFT JOIN roles r ON u.role_id = r.id
                       ORDER BY u.id DESC LIMIT ? OFFSET ?""",
                    (page_size, offset),
                ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def update_user(username: str, role_id: int = None, password: str = None) -> bool:
        with get_connection() as conn:
            if password:
                salt = secrets.token_bytes(16)
                password_hash = _hash_password(password, salt)
                if role_id is not None:
                    conn.execute(
                        "UPDATE users SET role_id = ?, password_hash = ?, salt = ? WHERE username = ?",
                        (role_id, password_hash, salt.hex(), username),
                    )
                else:
                    conn.execute(
                        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
                        (password_hash, salt.hex(), username),
                    )
            elif role_id is not None:
                conn.execute(
                    "UPDATE users SET role_id = ? WHERE username = ?",
                    (role_id, username),
                )
            else:
                return False
            conn.commit()
        return True

    @staticmethod
    def toggle_user_status(username: str) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT status FROM users WHERE username = ?", (username,)
            ).fetchone()
            if row is None:
                return False
            new_status = 0 if row["status"] == 1 else 1
            conn.execute(
                "UPDATE users SET status = ? WHERE username = ?",
                (new_status, username),
            )
            conn.commit()
            return new_status == 1

    @staticmethod
    def delete_user(username: str) -> bool:
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM users WHERE username = ?", (username,)
            )
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def change_password(username: str, old_password: str, new_password: str) -> bool:
        if not UserRepository.verify_user(username, old_password):
            return False
        salt = secrets.token_bytes(16)
        password_hash = _hash_password(new_password, salt)
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
                (password_hash, salt.hex(), username),
            )
            conn.commit()
        return True