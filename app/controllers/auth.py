"""User-side login, registration and logout handlers."""

import hashlib
import re

from app.controllers.base import BaseHandler
from app.models.user import UserRepository


def _legacy_browser_hash(password: str) -> str:
    """Compatibility for accounts created by the legacy browser-hashed form."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class LoginHandler(BaseHandler):
    def get(self):
        if self.current_user:
            user = UserRepository.get_user_by_username(self.current_user)
            if user and user["role_name"] == "Normal User":
                return self.redirect("/index")
            if user and user["role_name"] == "System Admin":
                self.clear_cookie("username")
        self.render("login.html", title="用户登录 - 瞭望与问数系统", error=None, username="")

    def post(self):
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "")
        if not username or not password:
            return self.render(
                "login.html", title="用户登录 - 瞭望与问数系统",
                error="请输入用户名和密码。", username=username,
            )
        verified = UserRepository.verify_user(username, password)
        if not verified:
            verified = UserRepository.verify_user(username, _legacy_browser_hash(password))
        if not verified:
            return self.render(
                "login.html", title="用户登录 - 瞭望与问数系统",
                error="用户名或密码错误，或账号已被禁用。", username=username,
            )
        user = UserRepository.get_user_by_username(username)
        if not user or user["role_name"] != "Normal User":
            return self.render(
                "login.html", title="用户登录 - 瞭望与问数系统",
                error="管理员账号请从后台管理入口登录。", username=username,
            )
        UserRepository.update_last_login(username)
        self.set_secure_cookie("username", username, httponly=True, samesite="Lax")
        self.redirect("/index")


class RegistHandler(BaseHandler):
    USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fff]{3,32}$")

    def get(self):
        if self.current_user:
            return self.redirect("/index")
        self.render("register.html", title="注册账号 - 瞭望与问数系统", error=None, username="")

    def post(self):
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "")
        password2 = self.get_body_argument("password2", "")
        error = None
        if not self.USERNAME_PATTERN.fullmatch(username):
            error = "用户名需为 3-32 位中文、字母、数字或下划线。"
        elif len(password) < 8:
            error = "密码至少需要 8 位。"
        elif password != password2:
            error = "两次输入的密码不一致。"
        if error:
            return self.render(
                "register.html", title="注册账号 - 瞭望与问数系统",
                error=error, username=username,
            )
        if not UserRepository.create_user(username, password, role_id=2):
            return self.render(
                "register.html", title="注册账号 - 瞭望与问数系统",
                error="用户名已存在，请更换后重试。", username=username,
            )
        self.set_secure_cookie("username", username, httponly=True, samesite="Lax")
        self.redirect("/index")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("username")
        self.redirect("/")

    def post(self):
        self.clear_cookie("username")
        self.redirect("/")
