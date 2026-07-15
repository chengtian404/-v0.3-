"""
menu.py -- menus table repository
Menus are role+function mappings with sort ordering.
"""

from app.models.db import get_connection


class MenuRepository:

    @staticmethod
    def get_role_menus(role_id: int) -> list:
        """Get menus for a role, joining with functions. Returns flat list with parent/child."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT m.id, m.function_id, m.sort_order,
                   f.name, f.icon, f.route, f.parent_id
                   FROM menus m
                   JOIN functions f ON m.function_id = f.id
                   WHERE m.role_id = ? AND f.status = 1
                   ORDER BY f.parent_id ASC, m.sort_order ASC, f.id ASC""",
                (role_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def update_menu_order(role_id: int, menu_data: list) -> None:
        """Update menu sort order. menu_data is list of {id: menu_id, sort_order: int}."""
        with get_connection() as conn:
            for item in menu_data:
                conn.execute(
                    "UPDATE menus SET sort_order = ? WHERE id = ? AND role_id = ?",
                    (item["sort_order"], item["id"], role_id),
                )
            conn.commit()

    @staticmethod
    def sync_role_menus(role_id: int) -> None:
        """Sync menus from role_functions: add new, remove stale."""
        with get_connection() as conn:
            # Get current role_functions
            rf = conn.execute(
                "SELECT function_id FROM role_functions WHERE role_id = ?",
                (role_id,),
            ).fetchall()
            rf_ids = set(r["function_id"] for r in rf)
            # Get current menus
            menus = conn.execute(
                "SELECT function_id FROM menus WHERE role_id = ?",
                (role_id,),
            ).fetchall()
            menu_ids = set(m["function_id"] for m in menus)
            # Add missing
            for fid in rf_ids - menu_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO menus (role_id, function_id, sort_order) VALUES (?, ?, 0)",
                    (role_id, fid),
                )
            # Remove stale
            for fid in menu_ids - rf_ids:
                conn.execute(
                    "DELETE FROM menus WHERE role_id = ? AND function_id = ?",
                    (role_id, fid),
                )
            conn.commit()

    @staticmethod
    def get_menu_preview(role_id: int) -> list:
        """Return a nested tree for menu preview (similar to sidebar rendering)."""
        MenuRepository.sync_role_menus(role_id)
        menus = MenuRepository.get_role_menus(role_id)
        # Build tree: parents first, attach children
        parent_map = {}
        children_map = {}
        for m in menus:
            if m["parent_id"] == 0:
                parent_map[m["function_id"]] = {
                    "id": m["id"],
                    "function_id": m["function_id"],
                    "name": m["name"],
                    "icon": m["icon"],
                    "route": m["route"],
                    "sort_order": m["sort_order"],
                    "children": [],
                }
            else:
                children_map.setdefault(m["parent_id"], []).append(m)
        result = []
        for fid, node in sorted(parent_map.items(), key=lambda x: x[1]["sort_order"]):
            if fid in children_map:
                for c in sorted(children_map[fid], key=lambda x: x["sort_order"]):
                    node["children"].append({
                        "id": c["id"],
                        "function_id": c["function_id"],
                        "name": c["name"],
                        "icon": c["icon"],
                        "route": c["route"],
                        "sort_order": c["sort_order"],
                    })
            result.append(node)
        return result