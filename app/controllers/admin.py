"""
admin.py -- Admin backend controllers
- AdminLoginHandler: admin login page
- AdminIndexHandler: admin dashboard
- AdminUsersHandler: user management (CRUD, pagination, search)
- AdminRoleHandler: role management (CRUD, function tree assignment)
- AdminFunctionHandler: function/feature management (CRUD, pagination, disable)
- AdminMenuHandler: menu ordering and preview
- AdminLogoutHandler: admin logout
"""

import json
import tornado.web

from app.controllers.base import BaseHandler, AdminBaseHandler
from app.models.user import UserRepository
from app.models.role import RoleRepository
from app.models.function import FunctionRepository
from app.models.menu import MenuRepository


# ==================== Login / Logout ====================

class AdminLoginHandler(BaseHandler):
    def get(self):
        if self.get_secure_cookie("admin_username"):
            self.redirect("/admin")
            return
        self.render("admin/login.html", title="后台管理系统 - DataFinderAgentOS", error=None)

    def post(self):
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "")
        if not username or not password:
            self.set_status(400)
            return self.render("admin/login.html", title="后台管理系统 - DataFinderAgentOS",
                               error="请输入账号和密码")
        if not UserRepository.verify_user(username, password):
            self.set_status(401)
            return self.render("admin/login.html", title="后台管理系统 - DataFinderAgentOS",
                               error="账号或密码不正确")
        user = UserRepository.get_user_by_username(username)
        if user["role_name"] != "System Admin":
            self.set_status(403)
            return self.render("admin/login.html", title="后台管理系统 - DataFinderAgentOS",
                               error="只有系统管理员可以访问后台")
        UserRepository.update_last_login(username)
        legacy_username = self.get_secure_cookie("username")
        if legacy_username and legacy_username.decode("utf-8") == username:
            self.clear_cookie("username")
        self.set_secure_cookie(
            "admin_username", username, httponly=True, samesite="Lax"
        )
        self.redirect("/admin")

    def get_login_url(self):
        return "/admin/login"


class AdminIndexHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.current_user)
        user_count = UserRepository.get_user_count()
        role_count = RoleRepository.get_role_count()
        func_count = FunctionRepository.get_function_count()
        self.render("admin/index.html", title="管理仪表盘 - DataFinderAgentOS",
                    username=self.current_user, user=user,
                    user_count=user_count, role_count=role_count, func_count=func_count)

    def get_login_url(self):
        return "/admin/login"


class AdminLogoutHandler(BaseHandler):
    def post(self):
        self.clear_cookie("admin_username")
        self.redirect("/admin/login")


# ==================== User Management ====================

class AdminUsersHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_query_argument("page", "1"))
        search = self.get_query_argument("search", "")
        users = UserRepository.get_all_users(page=page, page_size=20, search=search)
        total = UserRepository.get_user_count(search=search)
        roles = RoleRepository.get_all_roles_simple()
        self.render("admin/users.html", title="用户管理 - DataFinderAgentOS",
                    username=self.current_user, users=users, page=page,
                    total=total, search=search, roles=roles,
                    msg=None, msg_type=None)

    @tornado.web.authenticated
    def post(self):
        action = self.get_body_argument("action", "")
        if action == "toggle_status":
            target = self.get_body_argument("target", "")
            if target != "admin":
                UserRepository.toggle_user_status(target)
        elif action == "delete":
            target = self.get_body_argument("target", "")
            if target != "admin":
                UserRepository.delete_user(target)
        elif action == "add":
            new_username = self.get_body_argument("new_username", "").strip()
            new_password = self.get_body_argument("new_password", "")
            role_id = int(self.get_body_argument("role_id", "2"))
            if new_username and new_password:
                UserRepository.create_user(new_username, new_password, role_id)
        elif action == "edit":
            edit_username = self.get_body_argument("edit_username", "").strip()
            edit_role_id = int(self.get_body_argument("edit_role_id", "2"))
            edit_password = self.get_body_argument("edit_password", "").strip()
            pw = edit_password if edit_password else None
            UserRepository.update_user(edit_username, role_id=edit_role_id, password=pw)
        self.redirect(f"/admin/users?page={self.get_body_argument('page', '1')}&search={self.get_body_argument('search', '')}")

    def get_login_url(self):
        return "/admin/login"


# ==================== Role Management ====================

class AdminRoleHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_query_argument("page", "1"))
        roles = RoleRepository.get_all_roles(page=page, page_size=20)
        total = RoleRepository.get_role_count()
        tree = FunctionRepository.get_function_tree()
        self.render("admin/roles.html", title="角色管理 - DataFinderAgentOS",
                    username=self.current_user, roles=roles, page=page,
                    total=total, tree=json.dumps(tree),
                    msg=None, msg_type=None)

    @tornado.web.authenticated
    def post(self):
        action = self.get_body_argument("action", "")
        if action == "add":
            name = self.get_body_argument("role_name", "").strip()
            desc = self.get_body_argument("role_desc", "").strip()
            if name:
                RoleRepository.create_role(name, desc)
        elif action == "edit":
            role_id = int(self.get_body_argument("role_id", "0"))
            name = self.get_body_argument("role_name", "").strip()
            desc = self.get_body_argument("role_desc", "").strip()
            if role_id and name:
                RoleRepository.update_role(role_id, name, desc)
        elif action == "delete":
            role_id = int(self.get_body_argument("role_id", "0"))
            if role_id:
                RoleRepository.delete_role(role_id)
        self.redirect("/admin/roles")

    def get_login_url(self):
        return "/admin/login"


class AdminRoleFunctionHandler(AdminBaseHandler):
    """JSON API: get/set role-function assignments"""
    @tornado.web.authenticated
    def get(self):
        role_id = int(self.get_query_argument("role_id", "0"))
        func_ids = RoleRepository.get_role_functions(role_id)
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"role_id": role_id, "function_ids": func_ids}))

    @tornado.web.authenticated
    def post(self):
        role_id = int(self.get_body_argument("role_id", "0"))
        func_ids = json.loads(self.get_body_argument("function_ids", "[]"))
        RoleRepository.set_role_functions(role_id, func_ids)
        MenuRepository.sync_role_menus(role_id)
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"ok": True}))

    def get_login_url(self):
        return "/admin/login"


# ==================== Function Management ====================

class AdminFunctionHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_query_argument("page", "1"))
        search = self.get_query_argument("search", "")
        functions = FunctionRepository.get_all_functions(page=page, page_size=20, search=search)
        total = FunctionRepository.get_function_count(search=search)
        all_funcs = FunctionRepository.get_all_functions_simple()
        self.render("admin/functions.html", title="功能管理 - DataFinderAgentOS",
                    username=self.current_user, functions=functions, page=page,
                    total=total, search=search, all_funcs=all_funcs,
                    msg=None, msg_type=None)

    @tornado.web.authenticated
    def post(self):
        action = self.get_body_argument("action", "")
        if action == "add":
            name = self.get_body_argument("func_name", "").strip()
            parent_id = int(self.get_body_argument("parent_id", "0"))
            icon = self.get_body_argument("func_icon", "layui-icon-file")
            route = self.get_body_argument("func_route", "").strip()
            sort_order = int(self.get_body_argument("sort_order", "0"))
            if name:
                FunctionRepository.create_function(name, parent_id, icon, route, sort_order)
        elif action == "edit":
            func_id = int(self.get_body_argument("func_id", "0"))
            name = self.get_body_argument("func_name", "").strip()
            parent_id = int(self.get_body_argument("parent_id", "0"))
            icon = self.get_body_argument("func_icon", "layui-icon-file")
            route = self.get_body_argument("func_route", "").strip()
            sort_order = int(self.get_body_argument("sort_order", "0"))
            status = int(self.get_body_argument("func_status", "1"))
            if func_id and name:
                FunctionRepository.update_function(func_id, name, parent_id, icon, route, sort_order, status)
        elif action == "toggle_status":
            func_id = int(self.get_body_argument("func_id", "0"))
            FunctionRepository.toggle_function_status(func_id)
        elif action == "delete":
            func_id = int(self.get_body_argument("func_id", "0"))
            FunctionRepository.delete_function(func_id)
        self.redirect(f"/admin/functions?page={self.get_body_argument('page', '1')}&search={self.get_body_argument('search', '')}")

    def get_login_url(self):
        return "/admin/login"


# ==================== Menu Management ====================

class AdminMenuHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        roles = RoleRepository.get_all_roles_simple()
        role_id = int(self.get_query_argument("role_id", "1"))
        menus = MenuRepository.get_menu_preview(role_id)
        self.render("admin/menus.html", title="菜单管理 - DataFinderAgentOS",
                    username=self.current_user, roles=roles, selected_role=role_id,
                    menus=json.dumps(menus),
                    msg=None, msg_type=None)

    @tornado.web.authenticated
    def post(self):
        role_id = int(self.get_body_argument("role_id", "1"))
        menu_order = json.loads(self.get_body_argument("menu_order", "[]"))
        MenuRepository.update_menu_order(role_id, menu_order)
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"ok": True}))

    def get_login_url(self):
        return "/admin/login"
