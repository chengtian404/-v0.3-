# 接口说明

## 用户侧页面

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/` | 普通用户登录 |
| GET/POST | `/register` | 普通用户注册，固定绑定 Normal User 角色 |
| GET/POST | `/logout` | 退出用户侧 |
| GET | `/index` | AI 对话工作台 |
| GET/POST | `/profile` | 个人中心与密码修改 |

## 用户侧聊天接口

所有接口要求登录普通用户账号，写请求要求 Tornado XSRF Header。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/chat/bootstrap` | 返回模型、数字员工和会话列表 |
| GET/POST | `/api/chat/conversations` | 查询或新建会话 |
| GET/DELETE | `/api/chat/conversations/{id}` | 查询会话消息或删除会话 |
| POST | `/api/chat/messages` | 发送消息并执行意图调度 |

### POST `/api/chat/conversations`

```json
{"model_id": 1}
```

`model_id` 可省略；省略时普通问答使用后台默认模型。

### POST `/api/chat/messages`

```json
{
  "conversation_id": 12,
  "model_id": 1,
  "message": "生成用户状态分布图表"
}
```

响应的 `intent` 为以下白名单之一：

- `general_chat`：普通模型问答
- `database_query`：安全数据库问数，只返回文本指标
- `data_report`：安全数据库问数并返回 ECharts 报表结构
- `digital_employee`：通过 `@名称` 调度数字员工
- `employee_not_found`：提及的数字员工不存在

数据库问数不接受 SQL，也不会在响应中返回 SQL。`report` 仅在识别为报表意图时返回。

## 后台管理接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/admin/login` | 管理员登录 |
| GET | `/admin` | 管理仪表盘 |
| GET/POST | `/admin/users` | 用户管理 |
| GET/POST | `/admin/roles` | 角色管理 |
| GET/POST | `/admin/role-functions` | 角色功能授权 |
| GET/POST | `/admin/functions` | 功能管理 |
| GET/POST | `/admin/menus` | 菜单管理 |
| GET/POST | `/admin/observatory` | 瞭望采集 |
| POST | `/admin/observatory/collect` | 执行采集 |
| GET/POST | `/admin/sources` | 瞭源管理 |
| POST | `/admin/sources/test` | 测试瞭源规则 |
| GET/POST | `/admin/warehouse` | 数据仓库管理 |
| POST | `/admin/warehouse/save` | 保存采集结果 |
| GET | `/admin/warehouse/{id}` | 仓库详情 |
| GET/POST | `/admin/model-engine` | 模型引擎管理 |
| POST | `/admin/model-engine/test` | 模型连接测试 |
| POST | `/admin/model-engine/chat` | 模型 SSE 对话 |
| GET/POST | `/admin/digital-employees` | 数字员工管理与预览 |
| GET | `/admin/digital-employees/api` | 数字员工元数据接口 |
