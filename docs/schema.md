# 数据库结构

系统使用 SQLite，数据库文件为 `database/finderos.db`。

## 权限系统

### `users`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 用户 ID |
| username | TEXT UNIQUE | 用户名 |
| password_hash | TEXT | PBKDF2-SHA256 密码摘要 |
| salt | TEXT | 独立随机盐 |
| role_id | INTEGER | 角色 ID，注册用户固定为 2 |
| status | INTEGER | 1 启用，0 禁用 |
| last_login | TEXT | 最近登录时间 |
| created_at | TEXT | 创建时间 |

默认角色：`System Admin` 只能登录后台；`Normal User` 只能登录用户侧。

### `roles` / `functions` / `role_functions` / `menus`

- `roles`：角色定义。
- `functions`：一级、二级功能及路由。
- `role_functions`：角色与功能多对多映射。
- `menus`：角色菜单显示顺序。

## 数据瞭望

### `data_sources`

保存采集源 URL、请求方法、固定参数、RequestHeaders、解析器、规则和测试状态。

### `warehouse_items`

保存瞭望采集结果，包括标题、URL、摘要、来源、发布时间、原始数据、深度采集标记与深度数据。

## 模型与数字员工

### `ai_models`

保存 OpenAI-compatible 模型连接、模型类型、系统提示词、采样参数、上下文数、最大 Token、启用状态和默认模型标记。

### `model_usage`

按请求记录输入 Token、输出 Token、总 Token、成功状态和响应延迟。

### `digital_employees`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 数字员工 ID |
| name | TEXT UNIQUE | @ 提及名称 |
| description | TEXT | 能力描述 |
| avatar | TEXT | 显示标识 |
| emp_type | TEXT | `llm` 或 `api` |
| config_json | TEXT | 模型/Prompt/Skill/Crawl4AI 或 API 配置 |
| enabled | INTEGER | 启用状态 |
| created_at / updated_at | TEXT | 创建和更新时间 |

## 用户侧会话

### `chat_conversations`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 会话 ID |
| user_id | INTEGER | 会话所属用户 |
| title | TEXT | 首条消息生成的任务标题 |
| model_id | INTEGER | 用户选择的模型 |
| created_at / updated_at | TEXT | 创建和更新时间 |

### `chat_messages`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 消息 ID |
| conversation_id | INTEGER | 所属会话 |
| role | TEXT | `user` 或 `assistant` |
| content | TEXT | 消息正文 |
| intent | TEXT | 白名单意图类型 |
| employee_id | INTEGER | 数字员工 ID，可空 |
| model_id | INTEGER | 实际执行模型 ID，可空 |
| report_json | TEXT | 按需生成的 ECharts 报表结构，可空 |
| created_at | TEXT | 创建时间 |

问数接口不保存或执行用户 SQL。数据库查询只存在于后端白名单指标实现中。
