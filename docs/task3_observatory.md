# 任务 3 / 3.2：数据瞭望子系统

## 已实现模块

### 数据瞭望 `/admin/observatory`

- A 区：关键词输入和采集命令。
- B 区：读取已启用的瞭源规则，可多选参与本次采集。
- C 区：采集结果橱窗，桌面端每行 3 列，最多展示 12 条。
- 支持单选、全选，并将选中数据保存到数据仓库。
- 每个瞭源返回独立诊断，安全验证页不会作为业务数据。

### 瞭源管理 `/admin/sources`

- 支持新增、修改、删除、启用/停用、搜索、列表、20 条/页分页。
- 规则字段包括 URL、GET 参数、关键词参数、RequestHeaders、解析器类型和 CSS Selector。
- “测试”操作会真实发起请求并持久化最近测试状态、消息和时间。
- 已自动落库百度新闻规则。

### 数据仓库 `/admin/warehouse`

- 保存采集结果并按原文 URL 去重。
- 支持列表、搜索、20 条/页分页、查看、单条删除、批量删除。
- 包含“深度采集：是/否”字段。
- 已预留深度采集任务面板和深度数据查看悬浮窗。

## 采集流程

```text
关键词 + 已选瞭源
        |
        v
URL 固定参数 + keyword_param
        |
        v
RequestHeaders 模拟 GET 请求
        |
        v
安全验证检测 / CSS Selector 解析
        |
        v
标准化新闻数据 -> 用户选择 -> 数据仓库去重入库
```

## 百度新闻默认规则

- URL：`https://news.baidu.com/ns`
- 关键词参数：`word`
- 固定参数：`tn=news&from=news&cl=2&rn=20&ct=1`
- 解析器：`baidu_news`
- 请求头：Chrome User-Agent、Accept、Accept-Language、Referer、Cache-Control

百度可能间歇返回安全验证页。采集器通过页面标题和 `mkdjump` 特征识别该响应，并返回 `blocked`，管理员可在瞭源管理中重新测试。
