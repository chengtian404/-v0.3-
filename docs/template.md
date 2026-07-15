# 模板规范 (template.md)

> 本文档由人类维护，规定当前项目的模板规范要求，AI 编码时需严格遵守。

## 模板引擎

Tornado 原生模板引擎，语法基于 Python 的 `{% %}` 和 `{{ }}`。

## 模板继承链

### 前台用户侧
```
base.html (用户侧公共基础模板)
  ├── login.html     (用户登录页)
  ├── register.html  (用户注册页)
  ├── index.html     (用户登录后首页)
  └── profile.html   (用户个人中心)
```

### 后台管理侧
```
admin/base.html (后台管理侧公共基础模板)
  ├── admin/login.html  (后台登录页)
  ├── admin/index.html  (后台仪表盘)
  └── admin/users.html  (用户管理页)
```

## 模板规范

1. **命名规范**: 全部小写字母，单词间用下划线或连字符，扩展名为 `.html`
2. **Block 命名**:
   - `{% block title %}` — 页面标题
   - `{% block head %}` — 页面专属 CSS/样式
   - `{% block content %}` 或 `{% block body %}` — 页面主体内容
   - `{% block scripts %}` — 页面专属 JS
3. **静态资源引用**: 使用 `{{ static_url('css/xxx.css') }}` 确保缓存更新
4. **XSRF 防护**: 所有 POST 表单内必须包含 `{% module xsrf_form_html() %}`
5. **编码**: 统一使用 UTF-8，meta 标签声明 `charset="UTF-8"`

## 前端框架

- **Layui 2.9.x**: CDN 引入，使用其布局、表单、表格、导航等组件
- **原生 JS**: 不引入 jQuery 等额外依赖，直接使用 Layui 内置的 `layui.use()` 模块化方式
- **CSS**: 支持内联 `<style>` 和独立 CSS 文件两种方式

## 管理后台布局

采用 Layui 经典的后台布局方案:
```
layui-layout-admin
  ├── layui-header   (顶部导航栏 — LOGO + 用户信息 + 退出)
  ├── layui-side     (左侧菜单栏 — 导航菜单)
  ├── layui-body     (主内容区域)
  └── layui-footer   (底部版权信息)
```
