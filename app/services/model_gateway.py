"""OpenAI-compatible Chat Completions client helpers."""

import json
import time
from urllib.parse import urlparse

from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPClientError


DEEPSEEK_API_HOST = "api.deepseek.com"


def completion_url(base_url):
    base = (base_url or "").rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def auth_headers(model):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if model.get("api_key"):
        headers["Authorization"] = "Bearer " + model["api_key"]
    return headers


def is_deepseek_official(model):
    """Return whether a model points at DeepSeek's official API."""
    try:
        hostname = urlparse((model.get("base_url") or "").strip()).hostname or ""
    except ValueError:
        return False
    return hostname.lower() == DEEPSEEK_API_HOST


def validate_model_config(model, existing_api_key=""):
    """Validate connection fields before saving or sending a request."""
    base_url = (model.get("base_url") or "").strip()
    try:
        parsed = urlparse(base_url)
        valid_url = parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        valid_url = False
    if not valid_url:
        raise ValueError("基础接口地址必须是有效的 HTTP 或 HTTPS 地址。")

    api_key = (model.get("api_key") or existing_api_key or "").strip()
    if api_key.lower().startswith(("http://", "https://")):
        raise ValueError("接口密钥不能填写 URL，请粘贴模型服务控制台生成的 API Key。")
    if is_deepseek_official(model) and not api_key:
        raise ValueError("DeepSeek 官方接口需要 API Key，请先在 DeepSeek 控制台创建并填写密钥。")


def upstream_error_message(exc):
    """Convert an upstream HTTP failure into a useful, non-secret message."""
    status = getattr(exc, "code", None)
    response = getattr(exc, "response", None)
    detail = ""
    if response is not None and response.body:
        body = response.body.decode("utf-8", errors="replace").strip()
        try:
            payload = json.loads(body)
            error = payload.get("error", payload) if isinstance(payload, dict) else {}
            if isinstance(error, dict):
                detail = str(error.get("message") or error.get("error_msg") or "").strip()
            elif isinstance(error, str):
                detail = error.strip()
        except json.JSONDecodeError:
            if body and not body.lstrip().startswith("<"):
                detail = body[:300]

    messages = {
        400: "请求参数不被模型服务接受，请检查模型标识和参数配置。",
        401: "鉴权失败，API Key 无效、填错或尚未生效。",
        402: "模型账户余额不足或计费状态异常。",
        403: "当前 API Key 没有调用该模型的权限。",
        404: "接口或模型不存在，请检查基础接口地址和模型标识。",
        429: "模型服务请求过于频繁或额度已用尽。",
    }
    if status in messages:
        message = f"{messages[status]}（HTTP {status}）"
    elif status:
        message = f"模型服务请求失败（HTTP {status}）。"
    else:
        message = "无法连接模型服务，请检查网络和接口地址。"
    if detail:
        message += f" 上游信息：{detail}"
    return message


def build_payload(model, messages, stream=False):
    context_count = max(1, int(model.get("context_count", 10)))
    trimmed = list(messages)[-context_count:]
    system_prompt = (model.get("system_prompt") or "").strip()
    if system_prompt:
        trimmed.insert(0, {"role": "system", "content": system_prompt})
    payload = {
        "model": model["model_name"],
        "messages": trimmed,
        "temperature": float(model.get("temperature", 0.7)),
        "top_p": float(model.get("top_p", 1.0)),
        "max_tokens": int(model.get("max_tokens", 2048)),
        "stream": bool(stream),
    }
    return payload


def estimate_tokens(text):
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


async def test_model(model):
    try:
        validate_model_config(model)
    except ValueError as exc:
        return {
            "ok": False, "message": str(exc), "prompt_tokens": 0,
            "completion_tokens": 0, "latency_ms": 0,
        }
    payload = build_payload(
        model,
        [{"role": "user", "content": "Reply with exactly: CONNECTED"}],
        stream=False,
    )
    started = time.perf_counter()
    request = HTTPRequest(
        completion_url(model["base_url"]), method="POST",
        headers=auth_headers(model), body=json.dumps(payload),
        request_timeout=30, connect_timeout=12,
    )
    try:
        response = await AsyncHTTPClient().fetch(request)
        data = json.loads(response.body.decode("utf-8"))
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens") or estimate_tokens(json.dumps(payload["messages"], ensure_ascii=False))
        completion_tokens = usage.get("completion_tokens") or estimate_tokens(content)
        return {
            "ok": True, "message": content or "连接成功",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    except HTTPClientError as exc:
        return {
            "ok": False, "message": upstream_error_message(exc), "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return {
            "ok": False, "message": "模型服务返回了无法解析的响应，请确认接口兼容 Chat Completions。",
            "prompt_tokens": 0, "completion_tokens": 0,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }


async def complete_chat(model, messages, system_prompt=None):
    """Perform one non-streaming OpenAI-compatible chat completion."""
    try:
        validate_model_config(model)
    except ValueError as exc:
        return {
            "ok": False, "content": "", "message": str(exc),
            "prompt_tokens": 0, "completion_tokens": 0, "latency_ms": 0,
        }
    payload_model = dict(model)
    if system_prompt is not None:
        payload_model["system_prompt"] = system_prompt
    payload = build_payload(payload_model, messages, stream=False)
    started = time.perf_counter()
    request = HTTPRequest(
        completion_url(model["base_url"]),
        method="POST",
        headers=auth_headers(model),
        body=json.dumps(payload, ensure_ascii=False),
        request_timeout=90,
        connect_timeout=15,
    )
    try:
        response = await AsyncHTTPClient().fetch(request)
        data = json.loads(response.body.decode("utf-8"))
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens") or estimate_tokens(
            json.dumps(payload["messages"], ensure_ascii=False)
        )
        completion_tokens = usage.get("completion_tokens") or estimate_tokens(content)
        return {
            "ok": True,
            "content": content.strip() or "模型未返回文本内容。",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    except HTTPClientError as exc:
        return {
            "ok": False,
            "content": "",
            "message": upstream_error_message(exc),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return {
            "ok": False,
            "content": "",
            "message": "模型服务返回了无法解析的响应，请确认接口兼容 Chat Completions。",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
