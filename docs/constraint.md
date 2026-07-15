# 全局约束 (constraint.md)

> 本文档由 AI 自动维护，用于约束当前项目的全局开发规范与技术边界。

## 1. 技术约束

- **语言**: Python 3.11 (venv 中的解释器版本)
- **Web 框架**: Tornado (`tornado.web` / `tornado.ioloop` / `tornado.httpserver`)
- **数据库**: SQLite3 (`sqlite3` 内置模块，零外部依赖)，DB 文件 `database/finderos.db`
- **模板**: Tornado 原生模板 (`{% extends %}` / `{% block %}` / `{% module xsrf_form_html() %}`)
- **前端**: Layui 2.x + 原生 HTML + CSS + JS (未引入构建工具与前端框架)
- **虚拟环境**: `venv/`；一切依赖安装与运行必须激活 venv

## 2. 运行约束

- 入口文件: `app.py`
- 监听端口: `10010`
- 启动命令 (Windows PowerShell):
  ```powershell
  .\venv\Scripts\Activate.ps1
  python app.py
  ```
- 启动前 `init_db()` 自动创建表结构，无需手动建库

## 3. 目录约束

| 目录 | 用途 | 变更规则 |
|------|------|---------|
| `app/controllers/` | Controller 层，一个业务一个文件 | 新增业务需新建文件 |
| `app/models/` | Model 层，Repository 模式 | 每个表一个文件 |
| `app/templates/` | Tornado 原生模板 | 按模块分目录 |
| `app/static/` | 静态资源 (CSS/JS/图片) | 按类型分目录 |

## 4. 安全规范

- `set_secure_cookie`: `xsrf_cookies=True` + 模板 `{% module xsrf_form_html() %}`
- SQL 注入防护: 全部使用 `?` 参数占位符
- 密码存储: 盐 + PBKDF2-SHA256 100K 轮，使用 `secrets.compare_digest()` 常量时间比较
- 登录拦截: `login_url="/"` + `@tornado.web.authenticated`
- 前端传输: 密码提交前使用 SHA256 预处理，杜绝明文传输

## 5. 数据模型

```sql
users 表:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  username      TEXT    NOT NULL UNIQUE
  password_hash TEXT    NOT NULL
  salt          TEXT    NOT NULL
  role          TEXT    NOT NULL DEFAULT 'user'
  status        INTEGER NOT NULL DEFAULT 1
  last_login    TEXT
  created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
```

## 6. 配色方案

- 主题色: 深青 / 青碧色系 (`#0d7377` / `#14a3a8` / `#32e0c4`)
- 深色背景: `#0a1628` (深海暗色)
- 侧边栏: `#1a2332`
