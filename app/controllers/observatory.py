"""Observatory collection, source management, and data warehouse handlers."""

import asyncio
import json
from urllib.parse import quote

import tornado.web

from app.controllers.base import AdminBaseHandler
from app.models.source import SourceRepository, WarehouseRepository
from app.services.collector import CollectorError, collect_source


def _page(handler):
    try:
        return max(1, int(handler.get_query_argument("page", "1")))
    except ValueError:
        return 1


class ObservatoryHandler(AdminBaseHandler):
    def get(self):
        sources = SourceRepository.list_sources(page=1, page_size=100, enabled_only=True)
        self.render(
            "admin/observatory.html", title="数据瞭望 - DataFinderAgentOS",
            username=self.current_user, sources=sources,
        )


class ObservatoryCollectHandler(AdminBaseHandler):
    async def post(self):
        try:
            payload = json.loads(self.request.body.decode("utf-8"))
            keyword = str(payload.get("keyword", "")).strip()
            source_ids = [int(item) for item in payload.get("source_ids", [])]
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.write_json({"ok": False, "message": "请求参数格式错误"}, 400)
        if not keyword:
            return self.write_json({"ok": False, "message": "请输入采集关键词"}, 400)
        if not source_ids:
            return self.write_json({"ok": False, "message": "请至少选择一个瞭源"}, 400)

        loop = asyncio.get_running_loop()
        items = []
        diagnostics = []
        for source_id in source_ids:
            source = SourceRepository.get(source_id)
            if not source or not source["enabled"]:
                continue
            try:
                collected = await loop.run_in_executor(
                    None, collect_source, source, keyword, 12
                )
                items.extend(collected)
                message = f"采集成功，共 {len(collected)} 条"
                SourceRepository.set_test_result(source_id, "success", message)
                diagnostics.append({"source": source["name"], "ok": True, "message": message})
            except CollectorError as exc:
                SourceRepository.set_test_result(source_id, "blocked", str(exc))
                diagnostics.append({"source": source["name"], "ok": False, "message": str(exc)})
        return self.write_json({
            "ok": bool(items), "items": items[:12], "total": len(items),
            "diagnostics": diagnostics,
            "message": "采集完成" if items else "未采集到可用数据，请查看瞭源诊断",
        })


class SourceManagementHandler(AdminBaseHandler):
    def get(self):
        page = _page(self)
        search = self.get_query_argument("search", "").strip()
        sources = SourceRepository.list_sources(page=page, page_size=20, search=search)
        total = SourceRepository.count(search)
        self.render(
            "admin/sources.html", title="瞭源管理 - DataFinderAgentOS",
            username=self.current_user, sources=sources, total=total,
            page=page, search=search, message=self.get_query_argument("message", ""),
            sources_json=json.dumps(sources, ensure_ascii=False),
        )

    def post(self):
        action = self.get_body_argument("action", "")
        source_id = int(self.get_body_argument("source_id", "0") or 0)
        message = "操作完成"
        try:
            if action in ("add", "edit"):
                data = {
                    "name": self.get_body_argument("name", "").strip(),
                    "base_url": self.get_body_argument("base_url", "").strip(),
                    "method": self.get_body_argument("method", "GET").upper(),
                    "keyword_param": self.get_body_argument("keyword_param", "word").strip(),
                    "fixed_params_json": self.get_body_argument("fixed_params_json", "{}").strip(),
                    "headers_json": self.get_body_argument("headers_json", "{}").strip(),
                    "parser_type": self.get_body_argument("parser_type", "generic_html").strip(),
                    "parser_rules_json": self.get_body_argument("parser_rules_json", "{}").strip(),
                    "enabled": int(self.get_body_argument("enabled", "1")),
                }
                if not data["name"] or not data["base_url"]:
                    raise ValueError("名称和请求地址不能为空")
                SourceRepository.save(data, source_id if action == "edit" else None)
                message = "瞭源已保存"
            elif action == "delete":
                SourceRepository.delete(source_id)
                message = "瞭源已删除"
            elif action == "toggle":
                SourceRepository.toggle(source_id)
                message = "瞭源状态已更新"
        except (ValueError, TypeError) as exc:
            message = str(exc)
        self.redirect("/admin/sources?message=" + quote(message))


class SourceTestHandler(AdminBaseHandler):
    async def post(self):
        source_id = int(self.get_body_argument("source_id", "0"))
        keyword = self.get_body_argument("keyword", "人工智能").strip() or "人工智能"
        source = SourceRepository.get(source_id)
        if not source:
            return self.write_json({"ok": False, "message": "瞭源不存在"}, 404)
        try:
            items = await asyncio.get_running_loop().run_in_executor(
                None, collect_source, source, keyword, 3
            )
            message = f"规则可用，测试采集到 {len(items)} 条数据"
            SourceRepository.set_test_result(source_id, "success", message)
            return self.write_json({"ok": True, "message": message, "items": items})
        except CollectorError as exc:
            SourceRepository.set_test_result(source_id, "blocked", str(exc))
            return self.write_json({"ok": False, "message": str(exc)})


class WarehouseHandler(AdminBaseHandler):
    def get(self):
        page = _page(self)
        search = self.get_query_argument("search", "").strip()
        items = WarehouseRepository.list_items(page=page, page_size=20, search=search)
        total = WarehouseRepository.count(search)
        self.render(
            "admin/warehouse.html", title="数据仓库 - DataFinderAgentOS",
            username=self.current_user, items=items, total=total,
            page=page, search=search,
        )

    def post(self):
        action = self.get_body_argument("action", "")
        if action == "delete":
            WarehouseRepository.delete(int(self.get_body_argument("item_id", "0")))
        elif action == "delete_many":
            ids = json.loads(self.get_body_argument("item_ids", "[]"))
            WarehouseRepository.delete_many(ids)
        self.redirect("/admin/warehouse")


class WarehouseSaveHandler(AdminBaseHandler):
    def post(self):
        try:
            payload = json.loads(self.request.body.decode("utf-8"))
            items = payload.get("items", [])
            if not isinstance(items, list) or not items:
                raise ValueError("请选择要保存的数据")
            inserted = WarehouseRepository.save_items(items)
            return self.write_json({
                "ok": True, "inserted": inserted,
                "message": f"已保存 {inserted} 条，重复数据已自动跳过",
            })
        except (ValueError, json.JSONDecodeError) as exc:
            return self.write_json({"ok": False, "message": str(exc)}, 400)


class WarehouseDetailHandler(AdminBaseHandler):
    def get(self, item_id):
        item = WarehouseRepository.get(int(item_id))
        if not item:
            return self.write_json({"ok": False, "message": "数据不存在"}, 404)
        return self.write_json({"ok": True, "item": item})
