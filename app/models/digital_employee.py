"""Repository for LLM-based and HTTP API-based digital employees."""

import base64
import json
import ssl
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

from app.models.db import get_connection


class DigitalEmployeeRepository:
    @staticmethod
    def _config(data: dict) -> dict:
        if data.get("emp_type") == "api":
            return {
                "api_url": data.get("api_url", ""),
                "api_method": data.get("api_method", "GET").upper(),
                "api_headers": data.get("api_headers", "{}"),
                "api_params": data.get("api_params", "{}"),
                "api_body_template": data.get("api_body_template", ""),
                "response_type": data.get("response_type", "json"),
                "api_auth_type": data.get("api_auth_type", "none"),
                "api_auth_value": data.get("api_auth_value", ""),
            }
        return {
            "model_id": int(data.get("model_id", 0) or 0),
            "system_prompt": data.get("system_prompt", ""),
            "skills": data.get("skills", ""),
            "use_crawl4ai": int(data.get("use_crawl4ai", 0) or 0),
            "crawl4ai_config": data.get("crawl4ai_config", ""),
            "temperature": float(data.get("temperature", 0.7)),
            "max_tokens": int(data.get("max_tokens", 2048)),
        }

    @staticmethod
    def create(data: dict) -> bool:
        try:
            with get_connection() as conn:
                conn.execute("""
                    INSERT INTO digital_employees (
                        name, description, avatar, emp_type, config_json,
                        status, enabled, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 1, 1,
                              datetime('now', 'localtime'), datetime('now', 'localtime'))
                """, (
                    data["name"], data.get("description", ""), data.get("avatar", "AI"),
                    data.get("emp_type", "llm"),
                    json.dumps(DigitalEmployeeRepository._config(data), ensure_ascii=False),
                ))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def update(emp_id: int, data: dict) -> bool:
        with get_connection() as conn:
            cursor = conn.execute("""
                UPDATE digital_employees
                SET name=?, description=?, avatar=?, emp_type=?, config_json=?,
                    updated_at=datetime('now', 'localtime')
                WHERE id=?
            """, (
                data["name"], data.get("description", ""), data.get("avatar", "AI"),
                data.get("emp_type", "llm"),
                json.dumps(DigitalEmployeeRepository._config(data), ensure_ascii=False), emp_id,
            ))
            conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def delete(emp_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM digital_employees WHERE id=?", (emp_id,))
            conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def toggle_status(emp_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT enabled FROM digital_employees WHERE id=?", (emp_id,)
            ).fetchone()
            if not row:
                return False
            enabled = 0 if row["enabled"] else 1
            conn.execute("""
                UPDATE digital_employees
                SET enabled=?, updated_at=datetime('now', 'localtime') WHERE id=?
            """, (enabled, emp_id))
            conn.commit()
        return bool(enabled)

    @staticmethod
    def _parse(row):
        if not row:
            return None
        item = dict(row)
        try:
            item["config"] = json.loads(item.pop("config_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            item["config"] = {}
        return item

    @staticmethod
    def get(emp_id: int):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM digital_employees WHERE id=?", (emp_id,)
            ).fetchone()
        return DigitalEmployeeRepository._parse(row)

    @staticmethod
    def get_all(page=1, page_size=20, search="", emp_type="", enabled_only=False) -> list:
        where = []
        params = []
        if search:
            where.append("(name LIKE ? OR description LIKE ?)")
            params.extend([f"%{search}%"] * 2)
        if emp_type:
            where.append("emp_type=?")
            params.append(emp_type)
        if enabled_only:
            where.append("enabled=1")
        clause = " WHERE " + " AND ".join(where) if where else ""
        offset = (max(1, page) - 1) * page_size
        with get_connection() as conn:
            rows = conn.execute(f"""
                SELECT * FROM digital_employees {clause}
                ORDER BY id DESC LIMIT ? OFFSET ?
            """, (*params, page_size, offset)).fetchall()
        return [DigitalEmployeeRepository._parse(row) for row in rows]

    @staticmethod
    def count(search="", emp_type="", enabled_only=False) -> int:
        where = []
        params = []
        if search:
            where.append("(name LIKE ? OR description LIKE ?)")
            params.extend([f"%{search}%"] * 2)
        if emp_type:
            where.append("emp_type=?")
            params.append(emp_type)
        if enabled_only:
            where.append("enabled=1")
        clause = " WHERE " + " AND ".join(where) if where else ""
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS count FROM digital_employees{clause}", params
            ).fetchone()
        return row["count"]

    @staticmethod
    def get_enabled_list() -> list:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM digital_employees WHERE enabled=1 ORDER BY name ASC
            """).fetchall()
        return [DigitalEmployeeRepository._parse(row) for row in rows]

    @staticmethod
    def get_public_enabled_list() -> list:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, description, avatar, emp_type
                FROM digital_employees WHERE enabled=1 ORDER BY name ASC
            """).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def execute_llm(emp_id: int, user_input: str) -> dict:
        """Synchronous admin preview; user-side chat uses the async gateway."""
        from app.models.ai_model import AIModelRepository
        from app.services.model_gateway import auth_headers, build_payload, completion_url

        employee = DigitalEmployeeRepository.get(emp_id)
        if not employee or employee["emp_type"] != "llm" or not employee["enabled"]:
            return {"ok": False, "message": "数字员工不存在、类型错误或已停用。"}
        config = employee["config"]
        model = AIModelRepository.get_enabled(config.get("model_id")) if config.get("model_id") else None
        model = model or AIModelRepository.get_default()
        if not model:
            return {"ok": False, "message": "没有可用模型，请先在模型引擎中完成配置。"}
        prompt = config.get("system_prompt") or "你是一名专业、可靠的数字员工。"
        payload_model = dict(model)
        payload_model["system_prompt"] = prompt
        payload_model["temperature"] = config.get("temperature", model.get("temperature", 0.7))
        payload_model["max_tokens"] = config.get("max_tokens", model.get("max_tokens", 2048))
        payload = build_payload(payload_model, [{"role": "user", "content": user_input}], stream=False)
        request = urllib.request.Request(
            completion_url(model["base_url"]),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=auth_headers(model),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read(1_000_001).decode("utf-8"))
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return {"ok": True, "message": content, "model_name": model["name"]}
        except (urllib.error.URLError, json.JSONDecodeError, KeyError) as exc:
            return {"ok": False, "message": f"执行失败：{exc}"}

    @staticmethod
    def execute_api(emp_id: int, user_input: str) -> dict:
        employee = DigitalEmployeeRepository.get(emp_id)
        if not employee or employee["emp_type"] != "api" or not employee["enabled"]:
            return {"ok": False, "message": "数字员工不存在、类型错误或已停用。"}
        config = employee["config"]
        api_url = (config.get("api_url") or "").strip()
        parsed_url = urllib.parse.urlsplit(api_url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            return {"ok": False, "message": "API 地址必须是有效的 HTTP/HTTPS 地址。"}
        method = (config.get("api_method") or "GET").upper()
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            return {"ok": False, "message": "不支持的请求方法。"}
        try:
            headers = json.loads(config.get("api_headers") or "{}")
            params = json.loads(config.get("api_params") or "{}")
        except (TypeError, json.JSONDecodeError):
            return {"ok": False, "message": "Headers 或 Params 不是有效 JSON。"}
        if not isinstance(headers, dict) or not isinstance(params, dict):
            return {"ok": False, "message": "Headers 和 Params 必须是 JSON 对象。"}
        headers.setdefault("User-Agent", "DataFinderAgentOS/1.0")
        auth_type = config.get("api_auth_type", "none")
        auth_value = config.get("api_auth_value", "")
        if auth_type == "bearer" and auth_value:
            headers["Authorization"] = "Bearer " + auth_value
        elif auth_type == "basic" and auth_value:
            headers["Authorization"] = "Basic " + base64.b64encode(auth_value.encode()).decode()
        api_url = api_url.replace("{{input}}", urllib.parse.quote(user_input))
        params = {
            key: value.replace("{{input}}", user_input) if isinstance(value, str) else value
            for key, value in params.items()
        }
        body_template = (config.get("api_body_template") or "").replace("{{input}}", user_input)
        body = None
        if method == "GET" and params:
            api_url += ("&" if "?" in api_url else "?") + urllib.parse.urlencode(params)
        elif body_template:
            body = body_template.encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(api_url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30, context=ssl.create_default_context()) as response:
                raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    return {"ok": False, "message": "API 响应超过 1MB 限制。"}
                text = raw.decode("utf-8", errors="replace")
                status = response.status
            if config.get("response_type", "json") == "json":
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = text
            else:
                data = text
            return {"ok": True, "data": data, "status": status}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "message": f"API 返回 HTTP {exc.code}。"}
        except urllib.error.URLError as exc:
            return {"ok": False, "message": f"API 请求失败：{exc.reason}"}
