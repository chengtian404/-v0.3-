"""OpenAI-compatible model engine management and SSE chat handlers."""

import json
import time

import tornado.web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPClientError

from app.controllers.base import AdminBaseHandler
from app.models.ai_model import AIModelRepository
from app.services.model_gateway import (
    auth_headers, build_payload, completion_url, estimate_tokens, test_model,
    upstream_error_message, validate_model_config,
)


MODEL_TYPES = ["text", "image", "audio", "video", "multimodal", "embedding"]
MODEL_TYPE_LABELS = {
    "text": "文本", "image": "图像", "audio": "音频",
    "video": "视频", "multimodal": "多模态", "embedding": "嵌入",
}


def _script_json(value):
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


class ModelEngineHandler(AdminBaseHandler):
    def get(self):
        try:
            page = max(1, int(self.get_query_argument("page", "1")))
        except ValueError:
            page = 1
        search = self.get_query_argument("search", "").strip()
        model_type = self.get_query_argument("type", "").strip()
        models = AIModelRepository.list_models(page, 6, search, model_type)
        self.render(
            "admin/model_engine.html", title="模型引擎 - DataFinderAgentOS",
            username=self.current_user, models=models,
            models_json=_script_json(models),
            total=AIModelRepository.count(search, model_type), page=page,
            search=search, selected_type=model_type, model_types=MODEL_TYPES,
            model_type_labels=MODEL_TYPE_LABELS,
        )

    def post(self):
        action = self.get_body_argument("action", "")
        model_id = int(self.get_body_argument("model_id", "0") or 0)
        if action in ("add", "edit"):
            data = {
                "name": self.get_body_argument("name", "").strip(),
                "model_name": self.get_body_argument("model_name", "").strip(),
                "model_type": self.get_body_argument("model_type", "text"),
                "provider": self.get_body_argument("provider", "OpenAI Compatible").strip(),
                "base_url": self.get_body_argument("base_url", "").strip(),
                "api_key": self.get_body_argument("api_key", "").strip(),
                "system_prompt": self.get_body_argument("system_prompt", "").strip(),
                "top_p": self.get_body_argument("top_p", "1"),
                "context_count": self.get_body_argument("context_count", "10"),
                "max_tokens": self.get_body_argument("max_tokens", "2048"),
                "temperature": self.get_body_argument("temperature", "0.7"),
                "enabled": self.get_body_argument("enabled", "1"),
            }
            if not data["name"] or not data["model_name"] or not data["base_url"]:
                raise tornado.web.HTTPError(400, "模型名称、模型标识和 Base URL 不能为空")
            existing = AIModelRepository.get(model_id) if action == "edit" else None
            if action == "edit" and not existing:
                raise tornado.web.HTTPError(404, "模型不存在")
            try:
                validate_model_config(data, (existing or {}).get("api_key", ""))
                AIModelRepository.save(data, model_id if action == "edit" else None)
            except ValueError as exc:
                raise tornado.web.HTTPError(400, str(exc)) from exc
        elif action == "delete":
            AIModelRepository.delete(model_id)
        elif action == "default":
            AIModelRepository.set_default(model_id)
        self.redirect("/admin/model-engine")


class ModelTestHandler(AdminBaseHandler):
    async def post(self):
        model_id = int(self.get_body_argument("model_id", "0"))
        model = AIModelRepository.get(model_id)
        if not model:
            return self.write_json({"ok": False, "message": "模型不存在"}, 404)
        result = await test_model(model)
        AIModelRepository.log_usage(
            model_id, result["prompt_tokens"], result["completion_tokens"],
            result["ok"], result["latency_ms"], "test",
        )
        return self.write_json(result)


class ModelChatHandler(AdminBaseHandler):
    async def post(self):
        try:
            payload_in = json.loads(self.request.body.decode("utf-8"))
            model_id = int(payload_in.get("model_id", 0))
            messages = payload_in.get("messages", [])
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.write_json({"ok": False, "message": "对话参数格式错误"}, 400)
        model = AIModelRepository.get(model_id)
        if not model or not model["enabled"]:
            return self.write_json({"ok": False, "message": "模型不存在或已停用"}, 404)
        try:
            validate_model_config(model)
        except ValueError as exc:
            return self.write_json({"ok": False, "message": str(exc)}, 400)

        request_payload = build_payload(model, messages, stream=True)
        upstream_chunks = []
        started = time.perf_counter()
        self.set_header("Content-Type", "text/event-stream; charset=UTF-8")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")

        def on_chunk(chunk):
            upstream_chunks.append(chunk)
            if not self._finished:
                self.write(chunk)
                self.flush()

        request = HTTPRequest(
            completion_url(model["base_url"]), method="POST",
            headers=auth_headers(model), body=json.dumps(request_payload),
            streaming_callback=on_chunk, request_timeout=120, connect_timeout=15,
        )
        success = True
        error_message = ""
        try:
            await AsyncHTTPClient().fetch(request)
        except HTTPClientError as exc:
            success = False
            error_message = upstream_error_message(exc)

        raw = b"".join(upstream_chunks).decode("utf-8", errors="replace")
        prompt_tokens = 0
        completion_tokens = 0
        completion_text = []
        for line in raw.splitlines():
            if not line.startswith("data:"):
                continue
            value = line[5:].strip()
            if not value or value == "[DONE]":
                continue
            try:
                event = json.loads(value)
            except json.JSONDecodeError:
                continue
            usage = event.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
            completion_tokens = usage.get("completion_tokens", completion_tokens)
            delta = (event.get("choices") or [{}])[0].get("delta", {}).get("content")
            if delta:
                completion_text.append(delta)
        if not prompt_tokens:
            prompt_tokens = estimate_tokens(json.dumps(request_payload["messages"], ensure_ascii=False))
        if not completion_tokens:
            completion_tokens = estimate_tokens("".join(completion_text))
        latency_ms = int((time.perf_counter() - started) * 1000)
        AIModelRepository.log_usage(
            model_id, prompt_tokens, completion_tokens, success, latency_ms, "chat"
        )
        if error_message:
            self.write("event: error\ndata: " + json.dumps({"message": error_message}, ensure_ascii=False) + "\n\n")
        self.write("event: usage\ndata: " + json.dumps({
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency_ms,
        }, ensure_ascii=False) + "\n\n")
        self.finish()
