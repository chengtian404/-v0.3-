"""
function.py -- functions table repository
Supports 2-level hierarchy (parent_id = 0 for top-level).
"""

from app.models.db import get_connection


class FunctionRepository:

    @staticmethod
    def create_function(name: str, parent_id: int = 0, icon: str = "layui-icon-file",
                        route: str = "", sort_order: int = 0) -> bool:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO functions (name, parent_id, icon, route, sort_order) VALUES (?, ?, ?, ?, ?)",
                (name, parent_id, icon, route, sort_order),
            )
            conn.commit()
        return True

    @staticmethod
    def update_function(func_id: int, name: str, parent_id: int = 0,
                        icon: str = "layui-icon-file", route: str = "",
                        sort_order: int = 0, status: int = 1) -> bool:
        with get_connection() as conn:
            conn.execute(
                "UPDATE functions SET name=?, parent_id=?, icon=?, route=?, sort_order=?, status=? WHERE id=?",
                (name, parent_id, icon, route, sort_order, status, func_id),
            )
            conn.commit()
        return True

    @staticmethod
    def delete_function(func_id: int) -> bool:
        with get_connection() as conn:
            # Delete children first
            conn.execute("DELETE FROM functions WHERE parent_id = ?", (func_id,))
            conn.execute("DELETE FROM role_functions WHERE function_id = ?", (func_id,))
            conn.execute("DELETE FROM menus WHERE function_id = ?", (func_id,))
            conn.execute("DELETE FROM functions WHERE id = ?", (func_id,))
            conn.commit()
        return True

    @staticmethod
    def toggle_function_status(func_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute("SELECT status FROM functions WHERE id = ?", (func_id,)).fetchone()
            if row is None:
                return False
            new_status = 0 if row["status"] == 1 else 1
            conn.execute("UPDATE functions SET status = ? WHERE id = ?", (new_status, func_id))
            conn.commit()
            return new_status == 1

    @staticmethod
    def get_function_count(search: str = "") -> int:
        with get_connection() as conn:
            if search:
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM functions WHERE name LIKE ?",
                    (f"%{search}%",),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) AS cnt FROM functions").fetchone()
        return row["cnt"] if row else 0

    @staticmethod
    def get_all_functions(page: int = 1, page_size: int = 20, search: str = "") -> list:
        offset = (page - 1) * page_size
        with get_connection() as conn:
            if search:
                rows = conn.execute(
                    """SELECT f.*, p.name AS parent_name FROM functions f
                       LEFT JOIN functions p ON f.parent_id = p.id
                       WHERE f.name LIKE ?
                       ORDER BY f.sort_order ASC, f.id ASC LIMIT ? OFFSET ?""",
                    (f"%{search}%", page_size, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT f.*, p.name AS parent_name FROM functions f
                       LEFT JOIN functions p ON f.parent_id = p.id
                       ORDER BY f.sort_order ASC, f.id ASC LIMIT ? OFFSET ?""",
                    (page_size, offset),
                ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_function_tree() -> list:
        """Return all functions as a nested tree for Layui tree component."""
        with get_connection() as conn:
            parents = conn.execute(
                "SELECT id, name FROM functions WHERE parent_id = 0 AND status = 1 ORDER BY sort_order ASC, id ASC"
            ).fetchall()
            tree = []
            for p in parents:
                node = {"id": p["id"], "name": p["name"], "children": []}
                children = conn.execute(
                    "SELECT id, name FROM functions WHERE parent_id = ? AND status = 1 ORDER BY sort_order ASC, id ASC",
                    (p["id"],),
                ).fetchall()
                for c in children:
                    node["children"].append({"id": c["id"], "name": c["name"]})
                tree.append(node)
        return tree

    @staticmethod
    def get_all_functions_simple() -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name FROM functions WHERE status = 1 ORDER BY sort_order ASC, id ASC"
            ).fetchall()
        return [dict(r) for r in rows]