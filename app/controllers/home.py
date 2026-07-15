"""User-side workspace and profile handlers."""

from app.controllers.base import FrontendBaseHandler
from app.models.user import UserRepository


class IndexHandler(FrontendBaseHandler):
    def get(self):
        user = UserRepository.get_user_by_username(self.current_user)
        self.render(
            "index.html",
            title="智能工作台 - 瞭望与问数系统",
            username=self.current_user,
            user=dict(user),
        )


class ProfileHandler(FrontendBaseHandler):
    def get(self):
        user = UserRepository.get_user_by_username(self.current_user)
        self.render(
            "profile.html", title="个人中心 - 瞭望与问数系统",
            username=self.current_user, user=user, msg=None, msg_type=None,
        )

    def post(self):
        user = UserRepository.get_user_by_username(self.current_user)
        old_password = self.get_body_argument("old_password", "")
        new_password = self.get_body_argument("new_password", "")
        confirm_password = self.get_body_argument("new_password2", "")
        if len(new_password) < 8:
            message = "新密码至少需要 8 位。"
            message_type = "error"
        elif new_password != confirm_password:
            message = "两次输入的新密码不一致。"
            message_type = "error"
        elif UserRepository.change_password(self.current_user, old_password, new_password):
            message = "密码修改成功。"
            message_type = "success"
        else:
            message = "原密码不正确。"
            message_type = "error"
        self.render(
            "profile.html", title="个人中心 - 瞭望与问数系统",
            username=self.current_user, user=user, msg=message, msg_type=message_type,
        )
