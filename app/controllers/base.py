"""Shared Tornado request handlers."""

import json

import tornado.web


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        username = self.get_secure_cookie("username")
        return username.decode("utf-8") if username else None

    def write_json(self, data, status=200):
        self.set_status(status)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.finish(json.dumps(data, ensure_ascii=False))

    def write_error(self, status_code, **kwargs):
        messages = {
            400: "请求参数不正确",
            403: "没有访问权限",
            404: "页面不存在",
            500: "服务器内部错误",
        }
        self.set_header("Content-Type", "text/html; charset=UTF-8")
        self.finish(f"<h2>{status_code}</h2><p>{messages.get(status_code, '请求失败')}</p>")


class FrontendBaseHandler(BaseHandler):
    """Require an authenticated active normal-user account."""

    def prepare(self):
        if not self.current_user:
            self.redirect("/")
            self.finish()
            return
        from app.models.user import UserRepository

        user = UserRepository.get_user_by_username(self.current_user)
        if not user or user["status"] != 1 or user["role_name"] != "Normal User":
            self.clear_cookie("username")
            raise tornado.web.HTTPError(403)

    def get_login_url(self):
        return "/"


class AdminBaseHandler(BaseHandler):
    """Require an authenticated active system-admin account."""

    def get_current_user(self):
        username = self.get_secure_cookie("admin_username")
        return username.decode("utf-8") if username else None

    def prepare(self):
        if not self.current_user:
            self.redirect("/admin/login")
            self.finish()
            return
        from app.models.user import UserRepository

        user = UserRepository.get_user_by_username(self.current_user)
        if not user or user["status"] != 1 or user["role_name"] != "System Admin":
            self.clear_cookie("admin_username")
            raise tornado.web.HTTPError(403)

    def get_login_url(self):
        return "/admin/login"
