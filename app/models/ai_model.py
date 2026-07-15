"""Repository for OpenAI-compatible model connections and token usage."""

import sqlite3

from app.models.db import get_connection


class AIModelRepository:
    @staticmethod
    def list_enabled() -> list:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, model_name, model_type, provider, is_default
                FROM ai_models
                WHERE enabled=1 AND model_type IN ('text', 'multimodal')
                ORDER BY is_default DESC, id ASC
            """).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def list_models(page=1, page_size=6, search="", model_type=""):
        where = []
        params = []
        if search:
            where.append("(m.name LIKE ? OR m.model_name LIKE ? OR m.provider LIKE ?)")
            params.extend([f"%{search}%"] * 3)
        if model_type:
            where.append("m.model_type=?")
            params.append(model_type)
        clause = " WHERE " + " AND ".join(where) if where else ""
        offset = (max(1, page) - 1) * page_size
        with get_connection() as conn:
            rows = conn.execute(f"""
                SELECT m.*,
                       COALESCE(SUM(u.prompt_tokens), 0) AS prompt_tokens,
                       COALESCE(SUM(u.completion_tokens), 0) AS completion_tokens,
                       COALESCE(SUM(u.total_tokens), 0) AS total_tokens,
                       COUNT(u.id) AS call_count
                FROM ai_models m
                LEFT JOIN model_usage u ON u.model_id=m.id
                {clause}
                GROUP BY m.id
                ORDER BY m.is_default DESC, m.id DESC
                LIMIT ? OFFSET ?
            """, (*params, page_size, offset)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            api_key = item.pop("api_key", "")
            item["has_api_key"] = bool(api_key)
            item["api_key_invalid"] = api_key.lower().startswith(("http://", "https://"))
            result.append(item)
        return result

    @staticmethod
    def count(search="", model_type=""):
        where = []
        params = []
        if search:
            where.append("(name LIKE ? OR model_name LIKE ? OR provider LIKE ?)")
            params.extend([f"%{search}%"] * 3)
        if model_type:
            where.append("model_type=?")
            params.append(model_type)
        clause = " WHERE " + " AND ".join(where) if where else ""
        with get_connection() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS count FROM ai_models{clause}", params).fetchone()
        return row["count"]

    @staticmethod
    def get(model_id):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM ai_models WHERE id=?", (model_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_enabled(model_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ai_models WHERE id=? AND enabled=1", (model_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_default():
        with get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM ai_models
                WHERE enabled=1 AND model_type IN ('text', 'multimodal')
                ORDER BY is_default DESC, id ASC LIMIT 1
            """).fetchone()
        return dict(row) if row else None

    @staticmethod
    def save(data, model_id=None):
        values = (
            data["name"], data["model_name"], data.get("model_type", "text"),
            data.get("provider", "OpenAI Compatible"), data["base_url"].rstrip("/"),
            data.get("system_prompt", "你是一名乐于助人的智能助手。"),
            float(data.get("top_p", 1.0)), int(data.get("context_count", 10)),
            int(data.get("max_tokens", 2048)), float(data.get("temperature", 0.7)),
            int(data.get("enabled", 1)),
        )
        try:
            with get_connection() as conn:
                if model_id:
                    if data.get("api_key"):
                        conn.execute("""
                            UPDATE ai_models SET name=?, model_name=?, model_type=?, provider=?,
                            base_url=?, system_prompt=?, top_p=?, context_count=?, max_tokens=?,
                            temperature=?, enabled=?, api_key=?,
                            updated_at=datetime('now', 'localtime') WHERE id=?
                        """, (*values, data["api_key"], model_id))
                    else:
                        conn.execute("""
                            UPDATE ai_models SET name=?, model_name=?, model_type=?, provider=?,
                            base_url=?, system_prompt=?, top_p=?, context_count=?, max_tokens=?,
                            temperature=?, enabled=?, updated_at=datetime('now', 'localtime')
                            WHERE id=?
                        """, (*values, model_id))
                else:
                    conn.execute("""
                        INSERT INTO ai_models (
                            name, model_name, model_type, provider, base_url, system_prompt,
                            top_p, context_count, max_tokens, temperature, enabled, api_key
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (*values, data.get("api_key", "")))
                conn.commit()
            return True
        except sqlite3.IntegrityError as exc:
            raise ValueError("模型显示名称已存在") from exc

    @staticmethod
    def delete(model_id):
        with get_connection() as conn:
            conn.execute("UPDATE chat_conversations SET model_id=NULL WHERE model_id=?", (model_id,))
            conn.execute("DELETE FROM model_usage WHERE model_id=?", (model_id,))
            conn.execute("DELETE FROM ai_models WHERE id=?", (model_id,))
            conn.commit()

    @staticmethod
    def set_default(model_id):
        with get_connection() as conn:
            conn.execute("UPDATE ai_models SET is_default=0")
            conn.execute("UPDATE ai_models SET is_default=1, enabled=1 WHERE id=?", (model_id,))
            conn.commit()

    @staticmethod
    def log_usage(model_id, prompt_tokens, completion_tokens, success, latency_ms, request_type="chat"):
        prompt_tokens = int(prompt_tokens)
        completion_tokens = int(completion_tokens)
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO model_usage (
                    model_id, request_type, prompt_tokens, completion_tokens,
                    total_tokens, success, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                model_id, request_type, prompt_tokens, completion_tokens,
                prompt_tokens + completion_tokens, int(bool(success)), int(latency_ms),
            ))
            conn.commit()
