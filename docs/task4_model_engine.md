# 任务 4：模型引擎

## 页面入口

`/admin/model-engine`

## 功能

- OpenAI-compatible 模型新增、修改、删除、查询和分页。
- 模型分类：文本、图像、音频、视频、多模态、嵌入。
- 橱窗列表：桌面端每行 2 列，每页 6 条。
- 配置项：Provider、Base URL、API Key、模型标识、系统提示词、温度、Top P、上下文消息数和最大 Token。
- 支持模型连接测试。
- 支持 Chat Completions SSE 流式对话。
- 每个模型卡片融合显示 Prompt、Completion、Total Token 和调用次数。
- 支持设置默认模型；业务可通过 `AIModelRepository.get_default()` 获取默认服务。

## OpenAI-compatible 约定

系统向以下地址发送请求：

```text
{base_url}/chat/completions
```

如果 Base URL 已以 `/chat/completions` 结尾，则不会重复追加。请求使用 Bearer API Key，并发送：

```json
{
  "model": "模型标识",
  "messages": [],
  "temperature": 0.7,
  "top_p": 1.0,
  "max_tokens": 2048,
  "stream": true
}
```

为兼容 DeepSeek 和部分 OpenAI-compatible 中转服务，流式请求不强制发送可选的 `stream_options` 字段。兼容服务未返回 usage 时，系统使用字符长度进行保守估算，并在页面标记到累计统计中。

## DeepSeek 官方接入

模型表单提供“DeepSeek 官方”预设，选择后自动填写：

```text
Provider: DeepSeek
Base URL: https://api.deepseek.com
Model: deepseek-chat
```

API Key 必须填写 DeepSeek 控制台生成的有效密钥，不能把 `https://api.deepseek.com` 等接口地址填写到密钥字段。系统在浏览器和服务端均执行校验，并将 400、401、403、404、429 等上游错误转换为可操作的中文提示。

## 验证结论

使用本地 OpenAI-compatible 模拟服务完成端到端测试：

- 非流式连接测试：成功，返回 `CONNECTED`，记录 9 Token。
- SSE 流式对话：成功，客户端收到增量内容、`[DONE]` 和系统追加的 `usage` 事件。
- Token 统计：成功写入 `model_usage`。
- 测试模型和测试统计已在验证结束后删除，不污染正式配置。

真实第三方模型需要管理员在页面中填写对应 Base URL、模型标识和有效 API Key 后测试。

DeepSeek 实测结论：官方接口地址可达；原配置因 API Key 字段误填 URL 返回 HTTP 401。错误值已清理，模型标识已修正为 `deepseek-chat`。当前项目未保存有效 DeepSeek API Key，因此最终鉴权成功测试需在管理员填写真实密钥后执行。
