"""Conversation and message persistence for the user-side chat workspace."""

import json

from app.models.db import get_connection


class ChatRepository:
    @staticmethod
    def list_conversations(user_id: int, limit: int = 50) -> list:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT c.id, c.title, c.model_id, c.created_at, c.updated_at,
                       COUNT(m.id) AS message_count
                FROM chat_conversations c
                LEFT JOIN chat_messages m ON m.conversation_id=c.id
                WHERE c.user_id=?
                GROUP BY c.id
                ORDER BY c.updated_at DESC, c.id DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def create_conversation(user_id: int, model_id=None, title: str = "新对话") -> dict:
        with get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO chat_conversations (user_id, title, model_id)
                VALUES (?, ?, ?)
            """, (user_id, title, model_id))
            conversation_id = cursor.lastrowid
            conn.commit()
        return ChatRepository.get_conversation(conversation_id, user_id)

    @staticmethod
    def get_conversation(conversation_id: int, user_id: int):
        with get_connection() as conn:
            row = conn.execute("""
                SELECT id, user_id, title, model_id, created_at, updated_at
                FROM chat_conversations
                WHERE id=? AND user_id=?
            """, (conversation_id, user_id)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def update_conversation(conversation_id: int, user_id: int, *, title=None, model_id=None) -> bool:
        assignments = ["updated_at=datetime('now', 'localtime')"]
        params = []
        if title is not None:
            assignments.append("title=?")
            params.append(title)
        if model_id is not None:
            assignments.append("model_id=?")
            params.append(model_id)
        params.extend([conversation_id, user_id])
        with get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE chat_conversations SET {', '.join(assignments)} WHERE id=? AND user_id=?",
                params,
            )
            conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def delete_conversation(conversation_id: int, user_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM chat_conversations WHERE id=? AND user_id=?",
                (conversation_id, user_id),
            ).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM chat_messages WHERE conversation_id=?", (conversation_id,))
            conn.execute("DELETE FROM chat_conversations WHERE id=?", (conversation_id,))
            conn.commit()
        return True

    @staticmethod
    def add_message(
        conversation_id: int,
        role: str,
        content: str,
        *,
        intent: str = "general_chat",
        employee_id=None,
        model_id=None,
        report=None,
    ) -> dict:
        report_json = json.dumps(report, ensure_ascii=False) if report else None
        with get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO chat_messages (
                    conversation_id, role, content, intent,
                    employee_id, model_id, report_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id, role, content, intent,
                employee_id, model_id, report_json,
            ))
            message_id = cursor.lastrowid
            conn.execute("""
                UPDATE chat_conversations
                SET updated_at=datetime('now', 'localtime')
                WHERE id=?
            """, (conversation_id,))
            row = conn.execute(
                "SELECT * FROM chat_messages WHERE id=?", (message_id,)
            ).fetchone()
            conn.commit()
        result = dict(row)
        result["report"] = json.loads(result.pop("report_json")) if result["report_json"] else None
        return result

    @staticmethod
    def list_messages(conversation_id: int, user_id: int) -> list:
        conversation = ChatRepository.get_conversation(conversation_id, user_id)
        if not conversation:
            return []
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT id, conversation_id, role, content, intent,
                       employee_id, model_id, report_json, created_at
                FROM chat_messages
                WHERE conversation_id=?
                ORDER BY id ASC
            """, (conversation_id,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["report"] = json.loads(item.pop("report_json")) if item["report_json"] else None
            result.append(item)
        return result

    @staticmethod
    def model_history(conversation_id: int, user_id: int, limit: int = 20) -> list:
        messages = ChatRepository.list_messages(conversation_id, user_id)
        history = []
        for item in messages[-limit:]:
            if item["role"] not in ("user", "assistant"):
                continue
            history.append({"role": item["role"], "content": item["content"]})
        return history

    @staticmethod
    def count_messages(conversation_id: int) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM chat_messages WHERE conversation_id=?",
                (conversation_id,),
            ).fetchone()
        return row["count"]
