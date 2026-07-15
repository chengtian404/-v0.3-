"""SQLite connection and idempotent schema initialization."""

import json
import os
import sqlite3


def project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


DB_PATH = os.path.join(project_root(), "database", "finderos.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role_id INTEGER NOT NULL DEFAULT 2,
            status INTEGER NOT NULL DEFAULT 1,
            last_login TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            is_system INTEGER NOT NULL DEFAULT 0,
            status INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS functions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL,
            icon TEXT NOT NULL DEFAULT 'layui-icon-file',
            route TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            status INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS role_functions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            function_id INTEGER NOT NULL,
            UNIQUE(role_id, function_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            function_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            UNIQUE(role_id, function_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            base_url TEXT NOT NULL,
            method TEXT NOT NULL DEFAULT 'GET',
            keyword_param TEXT NOT NULL DEFAULT 'word',
            fixed_params_json TEXT NOT NULL DEFAULT '{}',
            headers_json TEXT NOT NULL DEFAULT '{}',
            parser_type TEXT NOT NULL DEFAULT 'baidu_news',
            parser_rules_json TEXT NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1,
            last_test_status TEXT NOT NULL DEFAULT 'untested',
            last_test_message TEXT NOT NULL DEFAULT '',
            last_test_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS warehouse_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            source_name TEXT NOT NULL DEFAULT '',
            keyword TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL DEFAULT '',
            publisher TEXT NOT NULL DEFAULT '',
            published_at TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL DEFAULT '{}',
            deep_collected INTEGER NOT NULL DEFAULT 0,
            deep_data_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            UNIQUE(url)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            model_name TEXT NOT NULL,
            model_type TEXT NOT NULL DEFAULT 'text',
            provider TEXT NOT NULL DEFAULT 'OpenAI Compatible',
            base_url TEXT NOT NULL DEFAULT 'https://api.openai.com/v1',
            api_key TEXT NOT NULL DEFAULT '',
            system_prompt TEXT NOT NULL DEFAULT '你是一名乐于助人的智能助手。',
            top_p REAL NOT NULL DEFAULT 1.0,
            context_count INTEGER NOT NULL DEFAULT 10,
            max_tokens INTEGER NOT NULL DEFAULT 2048,
            temperature REAL NOT NULL DEFAULT 0.7,
            enabled INTEGER NOT NULL DEFAULT 1,
            is_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL,
            request_type TEXT NOT NULL DEFAULT 'chat',
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            success INTEGER NOT NULL DEFAULT 1,
            latency_ms INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS digital_employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            avatar TEXT NOT NULL DEFAULT 'AI',
            emp_type TEXT NOT NULL DEFAULT 'llm',
            config_json TEXT NOT NULL DEFAULT '{}',
            status INTEGER NOT NULL DEFAULT 1,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT '新对话',
            model_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            intent TEXT NOT NULL DEFAULT 'general_chat',
            employee_id INTEGER,
            model_id INTEGER,
            report_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)


def _seed_roles(conn: sqlite3.Connection) -> None:
    conn.execute("""
        INSERT OR IGNORE INTO roles (id, name, description, is_system)
        VALUES (1, 'System Admin', '系统管理员，只允许登录后台管理系统', 1)
    """)
    conn.execute("""
        INSERT OR IGNORE INTO roles (id, name, description, is_system)
        VALUES (2, 'Normal User', '普通用户，只允许登录用户侧系统', 1)
    """)


def _seed_baidu_source(conn: sqlite3.Connection) -> None:
    default_headers = json.dumps({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://news.baidu.com/",
        "Cache-Control": "no-cache",
    }, ensure_ascii=False)
    fixed_params = json.dumps(
        {"tn": "news", "from": "news", "cl": "2", "rn": "20", "ct": "1"},
        ensure_ascii=False,
    )
    parser_rules = json.dumps({
        "item": "div.result-op, div.result",
        "title": "h3 a",
        "summary": ".c-summary, .c-span-last",
        "image": "img",
        "meta": ".c-author, .c-color-gray2",
    }, ensure_ascii=False)
    conn.execute("""
        INSERT OR IGNORE INTO data_sources (
            name, base_url, method, keyword_param, fixed_params_json,
            headers_json, parser_type, parser_rules_json, enabled
        ) VALUES (?, ?, 'GET', 'word', ?, ?, 'baidu_news', ?, 1)
    """, ("百度新闻", "https://news.baidu.com/ns", fixed_params, default_headers, parser_rules))
    conn.execute("UPDATE data_sources SET name='百度新闻' WHERE base_url='https://news.baidu.com/ns'")


def _deduplicate_digital_employee_function(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id FROM functions WHERE route='/admin/digital-employees' ORDER BY id"
    ).fetchall()
    if len(rows) <= 1:
        return
    keep_id = rows[0]["id"]
    duplicate_ids = [row["id"] for row in rows[1:]]
    for duplicate_id in duplicate_ids:
        conn.execute("""
            INSERT OR IGNORE INTO role_functions (role_id, function_id)
            SELECT role_id, ? FROM role_functions WHERE function_id=?
        """, (keep_id, duplicate_id))
        conn.execute("""
            INSERT OR IGNORE INTO menus (role_id, function_id, sort_order)
            SELECT role_id, ?, sort_order FROM menus WHERE function_id=?
        """, (keep_id, duplicate_id))
        conn.execute("DELETE FROM role_functions WHERE function_id=?", (duplicate_id,))
        conn.execute("DELETE FROM menus WHERE function_id=?", (duplicate_id,))
        conn.execute("DELETE FROM functions WHERE id=?", (duplicate_id,))


def _seed_functions(conn: sqlite3.Connection) -> None:
    entries = [
        ("数据瞭望", "layui-icon-search", "/admin/observatory", 10),
        ("瞭源管理", "layui-icon-link", "/admin/sources", 11),
        ("数据仓库", "layui-icon-table", "/admin/warehouse", 12),
        ("模型引擎", "layui-icon-engine", "/admin/model-engine", 20),
        ("数字员工", "layui-icon-face-smile", "/admin/digital-employees", 25),
    ]
    for name, icon, route, sort_order in entries:
        conn.execute("""
            INSERT INTO functions (name, parent_id, icon, route, sort_order)
            SELECT ?, 0, ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM functions WHERE route=?)
        """, (name, icon, route, sort_order, route))
        conn.execute(
            "UPDATE functions SET name=?, icon=?, sort_order=? WHERE route=?",
            (name, icon, sort_order, route),
        )

    localized_names = {
        "/admin": "仪表盘",
        "/admin/users": "用户管理",
        "/admin/roles": "角色管理",
        "/admin/functions": "功能管理",
        "/admin/menus": "菜单管理",
    }
    for route, name in localized_names.items():
        conn.execute("UPDATE functions SET name=? WHERE route=?", (name, route))

    rows = conn.execute("""
        SELECT id FROM functions
        WHERE route IN (
            '/admin/observatory', '/admin/sources', '/admin/warehouse',
            '/admin/model-engine', '/admin/digital-employees'
        )
    """).fetchall()
    for row in rows:
        conn.execute(
            "INSERT OR IGNORE INTO role_functions (role_id, function_id) VALUES (1, ?)",
            (row["id"],),
        )
        conn.execute(
            "INSERT OR IGNORE INTO menus (role_id, function_id, sort_order) VALUES (1, ?, 0)",
            (row["id"],),
        )


def _seed_digital_employees(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) AS count FROM digital_employees").fetchone()["count"]:
        return
    employees = [
        (
            "文案编写", "根据主题撰写、改写和润色企业文案", "文", "llm",
            {
                "model_id": 0,
                "system_prompt": "你是企业文案专员，负责撰写、改写和润色准确、克制、专业的中文文案。",
                "skills": "文案撰写、摘要、润色、标题生成",
                "use_crawl4ai": 0,
                "crawl4ai_config": "",
                "temperature": 0.7,
                "max_tokens": 2048,
            },
        ),
        (
            "天气", "查询指定城市的实时天气数据", "天", "api",
            {
                "api_url": "https://wttr.in/{{input}}?format=j1",
                "api_method": "GET",
                "api_headers": json.dumps({"Accept": "application/json"}, ensure_ascii=False),
                "api_params": "{}",
                "api_body_template": "",
                "response_type": "json",
                "api_auth_type": "none",
                "api_auth_value": "",
            },
        ),
        (
            "采集专员", "辅助执行数据采集、整理和深度解析任务", "采", "llm",
            {
                "model_id": 0,
                "system_prompt": "你是数据采集专员，负责分析采集目标、整理数据并给出结构化结果。不得绕过授权或访问受限数据。",
                "skills": "采集规划、数据整理、深度解析",
                "use_crawl4ai": 1,
                "crawl4ai_config": json.dumps({"output": "markdown"}, ensure_ascii=False),
                "temperature": 0.3,
                "max_tokens": 2048,
            },
        ),
    ]
    for name, description, avatar, emp_type, config in employees:
        conn.execute("""
            INSERT INTO digital_employees (
                name, description, avatar, emp_type, config_json, enabled
            )
            SELECT ?, ?, ?, ?, ?, 1
            WHERE NOT EXISTS (SELECT 1 FROM digital_employees WHERE name=?)
        """, (name, description, avatar, emp_type, json.dumps(config, ensure_ascii=False), name))


def init_db() -> None:
    with get_connection() as conn:
        _create_tables(conn)
        _seed_roles(conn)
        _seed_baidu_source(conn)
        _deduplicate_digital_employee_function(conn)
        _seed_functions(conn)
        _seed_digital_employees(conn)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_functions_unique_route "
            "ON functions(route) WHERE route <> ''"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_warehouse_created "
            "ON warehouse_items(created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_model "
            "ON model_usage(model_id, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_conversations_user "
            "ON chat_conversations(user_id, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation "
            "ON chat_messages(conversation_id, id)"
        )
        conn.commit()
