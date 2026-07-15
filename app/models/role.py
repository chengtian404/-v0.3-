"""
role.py -- roles table repository
"""

import sqlite3
from app.models.db import get_connection


class RoleRepository:

    @staticmethod
    def create_role(name: str, description: str = "") -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO roles (name, description, is_system) VALUES (?, ?, 0)",
                    (name, description),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def update_role(role_id: int, name: str, description: str) -> bool:
        try:
            with get_connection() as conn:
                # system roles (id 1 and 2) cannot be edited
                row = conn.execute("SELECT is_system FROM roles WHERE id = ?", (role_id,)).fetchone()
                if not row or row["is_system"] == 1:
                    return False
                conn.execute(
                    "UPDATE roles SET name = ?, description = ? WHERE id = ?",
                    (name, description, role_id),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def delete_role(role_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute("SELECT is_system FROM roles WHERE id = ?", (role_id,)).fetchone()
            if not row or row["is_system"] == 1:
                return False
            # check if any users are assigned to this role
            user_count = conn.execute("SELECT COUNT(*) AS cnt FROM users WHERE role_id = ?", (role_id,)).fetchone()
            if user_count and user_count["cnt"] > 0:
                return False
            conn.execute("DELETE FROM role_functions WHERE role_id = ?", (role_id,))
            conn.execute("DELETE FROM menus WHERE role_id = ?", (role_id,))
            conn.execute("DELETE FROM roles WHERE id = ?", (role_id,))
            conn.commit()
            return True

    @staticmethod
    def get_role_count() -> int:
        with get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM roles").fetchone()
        return row["cnt"] if row else 0

    @staticmethod
    def get_all_roles(page: int = 1, page_size: int = 20) -> list:
        offset = (page - 1) * page_size
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, description, is_system, status, created_at FROM roles ORDER BY id ASC LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_all_roles_simple() -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name FROM roles WHERE status = 1 ORDER BY id ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_role_functions(role_id: int) -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT function_id FROM role_functions WHERE role_id = ?",
                (role_id,),
            ).fetchall()
        return [r["function_id"] for r in rows]

    @staticmethod
    def set_role_functions(role_id: int, function_ids: list) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM role_functions WHERE role_id = ?", (role_id,))
            for fid in function_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO role_functions (role_id, function_id) VALUES (?, ?)",
                    (role_id, fid),
                )
            conn.commit()