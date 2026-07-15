"""Repositories for collection sources and warehouse records."""

import json
import sqlite3
from datetime import datetime

from app.models.db import get_connection


class SourceRepository:
    @staticmethod
    def list_sources(page=1, page_size=20, search="", enabled_only=False):
        where = []
        params = []
        if search:
            where.append("(name LIKE ? OR base_url LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if enabled_only:
            where.append("enabled = 1")
        clause = " WHERE " + " AND ".join(where) if where else ""
        offset = (max(1, page) - 1) * page_size
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM data_sources{clause} ORDER BY id DESC LIMIT ? OFFSET ?",
                (*params, page_size, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def count(search=""):
        params = []
        clause = ""
        if search:
            clause = " WHERE name LIKE ? OR base_url LIKE ?"
            params = [f"%{search}%", f"%{search}%"]
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS count FROM data_sources{clause}", params
            ).fetchone()
        return row["count"]

    @staticmethod
    def get(source_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM data_sources WHERE id = ?", (source_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def save(data, source_id=None):
        values = (
            data["name"], data["base_url"], data.get("method", "GET"),
            data.get("keyword_param", "word"), data.get("fixed_params_json", "{}"),
            data.get("headers_json", "{}"), data.get("parser_type", "generic_html"),
            data.get("parser_rules_json", "{}"), int(data.get("enabled", 1)),
        )
        try:
            json.loads(values[4])
            json.loads(values[5])
            json.loads(values[7])
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON 配置格式错误：{exc.msg}") from exc
        try:
            with get_connection() as conn:
                if source_id:
                    conn.execute("""
                        UPDATE data_sources SET name=?, base_url=?, method=?, keyword_param=?,
                        fixed_params_json=?, headers_json=?, parser_type=?, parser_rules_json=?,
                        enabled=?, updated_at=datetime('now', 'localtime') WHERE id=?
                    """, (*values, source_id))
                else:
                    conn.execute("""
                        INSERT INTO data_sources (
                            name, base_url, method, keyword_param, fixed_params_json,
                            headers_json, parser_type, parser_rules_json, enabled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, values)
                conn.commit()
            return True
        except sqlite3.IntegrityError as exc:
            raise ValueError("瞭源名称已存在") from exc

    @staticmethod
    def delete(source_id):
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM data_sources WHERE id = ?", (source_id,))
            conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def toggle(source_id):
        with get_connection() as conn:
            conn.execute(
                "UPDATE data_sources SET enabled = CASE enabled WHEN 1 THEN 0 ELSE 1 END, "
                "updated_at=datetime('now', 'localtime') WHERE id=?",
                (source_id,),
            )
            conn.commit()

    @staticmethod
    def set_test_result(source_id, status, message):
        with get_connection() as conn:
            conn.execute("""
                UPDATE data_sources SET last_test_status=?, last_test_message=?,
                last_test_at=?, updated_at=datetime('now', 'localtime') WHERE id=?
            """, (
                status, message[:500], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), source_id,
            ))
            conn.commit()


class WarehouseRepository:
    @staticmethod
    def save_items(items):
        inserted = 0
        with get_connection() as conn:
            for item in items:
                try:
                    conn.execute("""
                        INSERT INTO warehouse_items (
                            source_id, source_name, keyword, title, url, summary,
                            image_url, publisher, published_at, raw_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item.get("source_id"), item.get("source_name", ""),
                        item.get("keyword", ""), item.get("title", ""),
                        item.get("url", ""), item.get("summary", ""),
                        item.get("image_url", ""), item.get("publisher", ""),
                        item.get("published_at", ""),
                        json.dumps(item, ensure_ascii=False),
                    ))
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue
            conn.commit()
        return inserted

    @staticmethod
    def list_items(page=1, page_size=20, search=""):
        offset = (max(1, page) - 1) * page_size
        params = []
        clause = ""
        if search:
            clause = " WHERE title LIKE ? OR summary LIKE ? OR publisher LIKE ? OR keyword LIKE ?"
            params = [f"%{search}%"] * 4
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM warehouse_items{clause} ORDER BY id DESC LIMIT ? OFFSET ?",
                (*params, page_size, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def count(search=""):
        params = []
        clause = ""
        if search:
            clause = " WHERE title LIKE ? OR summary LIKE ? OR publisher LIKE ? OR keyword LIKE ?"
            params = [f"%{search}%"] * 4
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS count FROM warehouse_items{clause}", params
            ).fetchone()
        return row["count"]

    @staticmethod
    def get(item_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM warehouse_items WHERE id=?", (item_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def delete(item_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM warehouse_items WHERE id=?", (item_id,))
            conn.commit()

    @staticmethod
    def delete_many(item_ids):
        clean_ids = [int(item_id) for item_id in item_ids if str(item_id).isdigit()]
        if not clean_ids:
            return 0
        placeholders = ",".join("?" for _ in clean_ids)
        with get_connection() as conn:
            cursor = conn.execute(
                f"DELETE FROM warehouse_items WHERE id IN ({placeholders})", clean_ids
            )
            conn.commit()
        return cursor.rowcount
