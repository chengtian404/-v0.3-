"""
app.py -- DataFinderAgentOS main entry point
Tornado-based web framework. Frontend + Admin dual access.
"""

import os
import tornado.ioloop
import tornado.web
from tornado.httpserver import HTTPServer
from tornado.netutil import bind_sockets

from app.controllers.auth import LoginHandler, LogoutHandler, RegistHandler
from app.controllers.home import IndexHandler, ProfileHandler
from app.controllers.chat import (
    ChatBootstrapHandler, ChatConversationsHandler,
    ChatConversationHandler, UserChatHandler,
)
from app.controllers.admin import (
    AdminLoginHandler, AdminIndexHandler,
    AdminUsersHandler, AdminLogoutHandler,
    AdminRoleHandler, AdminRoleFunctionHandler,
    AdminFunctionHandler, AdminMenuHandler,
)
from app.controllers.observatory import (
    ObservatoryHandler, ObservatoryCollectHandler,
    SourceManagementHandler, SourceTestHandler,
    WarehouseHandler, WarehouseSaveHandler, WarehouseDetailHandler,
)
from app.controllers.digital_employee import (
    DigitalEmployeeHandler, DigitalEmployeeApiHandler,
)
from app.controllers.model_engine import (
    ModelEngineHandler, ModelTestHandler, ModelChatHandler,
)
from app.models.db import init_db


def make_app() -> tornado.web.Application:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return tornado.web.Application(
        [
            # ========== Frontend routes ==========
            (r"/",          LoginHandler),
            (r"/register",  RegistHandler),
            (r"/logout",    LogoutHandler),
            (r"/index",     IndexHandler),
            (r"/profile",   ProfileHandler),
            (r"/api/chat/bootstrap/?", ChatBootstrapHandler),
            (r"/api/chat/conversations/?", ChatConversationsHandler),
            (r"/api/chat/conversations/(\d+)/?", ChatConversationHandler),
            (r"/api/chat/messages/?", UserChatHandler),

            # ========== Admin routes ==========
            (r"/admin/?",               AdminIndexHandler),
            (r"/admin/login/?",         AdminLoginHandler),
            (r"/admin/logout/?",        AdminLogoutHandler),
            (r"/admin/users/?",         AdminUsersHandler),
            (r"/admin/roles/?",         AdminRoleHandler),
            (r"/admin/role-functions/?", AdminRoleFunctionHandler),
            (r"/admin/functions/?",     AdminFunctionHandler),
            (r"/admin/menus/?",         AdminMenuHandler),
            (r"/admin/observatory/?",   ObservatoryHandler),
            (r"/admin/observatory/collect/?", ObservatoryCollectHandler),
            (r"/admin/sources/?",       SourceManagementHandler),
            (r"/admin/sources/test/?",  SourceTestHandler),
            (r"/admin/warehouse/?",     WarehouseHandler),
            (r"/admin/warehouse/save/?", WarehouseSaveHandler),
            (r"/admin/warehouse/(\d+)/?", WarehouseDetailHandler),
            (r"/admin/model-engine/?",  ModelEngineHandler),
            (r"/admin/model-engine/test/?", ModelTestHandler),
            (r"/admin/model-engine/chat/?", ModelChatHandler),
            (r"/admin/digital-employees/?", DigitalEmployeeHandler),
            (r"/admin/digital-employees/api/?", DigitalEmployeeApiHandler),
        ],
        template_path=os.path.join(base_dir, "app", "templates"),
        static_path=os.path.join(base_dir, "app", "static"),
        cookie_secret="datafinderagentos-token-2026",
        login_url="/",
        xsrf_cookies=True,
        autoreload=False,
    )


if __name__ == "__main__":
    init_db()
    app = make_app()
    server = HTTPServer(app)
    configured_port = os.environ.get("PORT")
    requested_port = int(configured_port or "10010")
    candidate_ports = [requested_port] if configured_port else [10010, 18081, 18082, 18083]
    sockets = None
    port = requested_port
    for candidate in candidate_ports:
        try:
            sockets = bind_sockets(candidate)
            port = candidate
            break
        except OSError:
            continue
    if sockets is None:
        raise OSError("无法绑定服务端口，请检查 10010 或设置 PORT 环境变量")
    server.add_sockets(sockets)
    print("=" * 56)
    print("  DataFinderAgentOS v0.1")
    print(f"  Frontend: http://localhost:{port}/")
    print(f"  Admin:    http://localhost:{port}/admin/")
    print("=" * 56)
    tornado.ioloop.IOLoop.current().start()
