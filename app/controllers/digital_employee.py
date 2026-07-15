"""digital_employee.py -- Digital Employee management controller."""

import json
import tornado.web

from app.controllers.base import AdminBaseHandler
from app.models.digital_employee import DigitalEmployeeRepository
from app.models.ai_model import AIModelRepository


def _script_json(value):
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


class DigitalEmployeeHandler(AdminBaseHandler):
    def get(self):
        page = max(1, int(self.get_query_argument("page", "1")))
        search = self.get_query_argument("search", "").strip()
        emp_type = self.get_query_argument("type", "").strip()
        employees = DigitalEmployeeRepository.get_all(page=page, page_size=20, search=search, emp_type=emp_type)
        total = DigitalEmployeeRepository.count(search=search, emp_type=emp_type)
        models = AIModelRepository.list_models(page=1, page_size=999)
        self.render(
            "admin/digital_employees.html",
            title="数字员工 - DataFinderAgentOS",
            username=self.current_user,
            employees=employees,
            employees_json=_script_json(employees),
            models_json=_script_json([dict(m) for m in models]),
            total=total, page=page, search=search,
            selected_type=emp_type, models=models,
            msg=None, msg_type=None,
        )

    def post(self):
        action = self.get_body_argument("action", "").strip()
        if action == "add":
            data = {
                "name": self.get_body_argument("name", "").strip(),
                "description": self.get_body_argument("description", "").strip(),
                "avatar": self.get_body_argument("avatar", "").strip() or '🤖',
                "emp_type": self.get_body_argument("emp_type", "llm"),
                "model_id": int(self.get_body_argument("model_id", "0")),
                "system_prompt": self.get_body_argument("system_prompt", "").strip(),
                "skills": self.get_body_argument("skills", "").strip(),
                "use_crawl4ai": int(self.get_body_argument("use_crawl4ai", "0")),
                "crawl4ai_config": self.get_body_argument("crawl4ai_config", "").strip(),
                "temperature": float(self.get_body_argument("temperature", "0.7")),
                "max_tokens": int(self.get_body_argument("max_tokens", "2048")),
                "api_url": self.get_body_argument("api_url", "").strip(),
                "api_method": self.get_body_argument("api_method", "GET").strip(),
                "api_headers": self.get_body_argument("api_headers", "{}").strip(),
                "api_params": self.get_body_argument("api_params", "{}").strip(),
                "api_body_template": self.get_body_argument("api_body_template", "").strip(),
                "response_type": self.get_body_argument("response_type", "json").strip(),
                "api_auth_type": self.get_body_argument("api_auth_type", "none").strip(),
                "api_auth_value": self.get_body_argument("api_auth_value", "").strip(),
            }
            if data["name"]:
                DigitalEmployeeRepository.create(data)
        elif action == "edit":
            emp_id = int(self.get_body_argument("emp_id", "0"))
            if emp_id:
                data = {
                    "name": self.get_body_argument("name", "").strip(),
                    "description": self.get_body_argument("description", "").strip(),
                    "avatar": self.get_body_argument("avatar", "").strip() or '🤖',
                    "emp_type": self.get_body_argument("emp_type", "llm"),
                    "model_id": int(self.get_body_argument("model_id", "0")),
                    "system_prompt": self.get_body_argument("system_prompt", "").strip(),
                    "skills": self.get_body_argument("skills", "").strip(),
                    "use_crawl4ai": int(self.get_body_argument("use_crawl4ai", "0")),
                    "crawl4ai_config": self.get_body_argument("crawl4ai_config", "").strip(),
                    "temperature": float(self.get_body_argument("temperature", "0.7")),
                    "max_tokens": int(self.get_body_argument("max_tokens", "2048")),
                    "api_url": self.get_body_argument("api_url", "").strip(),
                    "api_method": self.get_body_argument("api_method", "GET").strip(),
                    "api_headers": self.get_body_argument("api_headers", "{}").strip(),
                    "api_params": self.get_body_argument("api_params", "{}").strip(),
                    "api_body_template": self.get_body_argument("api_body_template", "").strip(),
                    "response_type": self.get_body_argument("response_type", "json").strip(),
                    "api_auth_type": self.get_body_argument("api_auth_type", "none").strip(),
                    "api_auth_value": self.get_body_argument("api_auth_value", "").strip(),
                }
                if data["name"]:
                    DigitalEmployeeRepository.update(emp_id, data)
        elif action == "toggle_status":
            emp_id = int(self.get_body_argument("emp_id", "0"))
            if emp_id:
                DigitalEmployeeRepository.toggle_status(emp_id)
        elif action == "delete":
            emp_id = int(self.get_body_argument("emp_id", "0"))
            if emp_id:
                DigitalEmployeeRepository.delete(emp_id)
        elif action == "execute":
            emp_id = int(self.get_body_argument("emp_id", "0"))
            user_input = self.get_body_argument("user_input", "").strip()
            if emp_id:
                emp = DigitalEmployeeRepository.get(emp_id)
                if emp and emp["emp_type"] == "api":
                    result = DigitalEmployeeRepository.execute_api(emp_id, user_input)
                else:
                    result = DigitalEmployeeRepository.execute_llm(emp_id, user_input)
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps(result, ensure_ascii=False))
                return
        elif action == "preview":
            """Preview API digital employee response."""
            emp_id = int(self.get_body_argument("emp_id", "0"))
            user_input = self.get_body_argument("user_input", "").strip()
            if emp_id:
                result = DigitalEmployeeRepository.execute_api(emp_id, user_input)
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps(result, ensure_ascii=False))
                return
        self.redirect("/admin/digital-employees")


class DigitalEmployeeApiHandler(AdminBaseHandler):
    """JSON-only API handler for digital employee operations."""
    def get(self):
        action = self.get_query_argument("action", "list")
        if action == "get":
            emp_id = int(self.get_query_argument("id", "0"))
            emp = DigitalEmployeeRepository.get(emp_id)
            self.write_json(emp if emp else {"ok": False, "message": "Not found"})
        elif action == "list_enabled":
            employees = DigitalEmployeeRepository.get_enabled_list()
            self.write_json(employees)
        else:
            self.write_json({"ok": False, "message": "Unknown action"})
