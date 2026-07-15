# 瞭望与问数系统 (DataFinderAgentOS) v0.1

基于 Tornado 异步 Web 框架构建的轻量级数据查询与分析平台。

## 技术栈

- **后端**: Python 3.11 + Tornado 6.x
- **数据库**: SQLite3 (零外部依赖，开箱即用)
- **前端**: Layui 2.9.x + 原生 HTML/CSS/JS

## 快速开始

### 1. 创建虚拟环境并安装依赖

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 创建管理员账号

```powershell
python make_admin.py
```

默认管理员账号: `admin` / `123456`

### 3. 启动服务

```powershell
python main.py
```

服务启动后访问:
- **前台登录**: http://localhost:10010/
- **后台管理**: http://localhost:10010/admin/

## 项目结构

```
DataFinderAgentOS/
├── main.py                    # 应用主入口
├── make_admin.py              # 管理员创建脚本
├── requirements.txt           # Python 依赖
├── database/                  # SQLite 数据库文件
├── docs/                      # 项目文档
├── test/                      # 单元测试
└── app/
    ├── controllers/           # 控制器层
    │   ├── base.py            # 公共基类
    │   ├── auth.py            # 登录/注册/登出
    │   ├── home.py            # 用户首页/个人中心
    │   └── admin.py           # 后台管理
    ├── models/                # 数据访问层
    │   ├── db.py              # 数据库连接
    │   └── user.py            # 用户仓储
    ├── templates/             # Tornado 模板
    │   ├── login.html         # 登录页
    │   ├── regist.html        # 注册页
    │   ├── index.html         # 用户首页
    │   ├── profile.html       # 个人中心
    │   └── admin/             # 后台模板
    └── static/                # 静态资源
        ├── css/
        └── js/
```

## 安全特性

- XSRF 防护 (Cookie + Token)
- PBKDF2-SHA256 密码哈希 (100,000 轮迭代)
- SQL 参数化查询 (防注入)
- 常量时间密码比较 (防时序攻击)
- 前端 SHA256 密码预处理

## 运行测试

```powershell
python test/test_user_models.py
```
