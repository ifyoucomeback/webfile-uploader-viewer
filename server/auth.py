"""认证兼容入口：组合用户、密码及会话服务。"""

import hmac

from .security.passwords import PasswordHasher
from .security.sessions import SessionStore
from .security.users import UserStore


class AuthManager:
    """认证兼容入口：组合用户、密码及会话服务。"""

    def __init__(self, config):
        self.config = config
        auth_config = config.get("auth", {})
        self.upload_psk = auth_config.get("upload_psk", "")
        self.users = UserStore(config)
        self.session_store = SessionStore(auth_config.get("session_expire_hours", 12))
        self.session_expire_seconds = self.session_store.session_expire_seconds

    hash_password = PasswordHasher.hash_password
    verify_password = PasswordHasher.verify_password

    def verify_upload_psk(self, provided_psk):
        """
        验证客户端上传 PSK。

        使用恒定时间比较。
        """
        if not self.upload_psk:
            return False
        if not isinstance(provided_psk, str):
            return False
        return hmac.compare_digest(provided_psk, self.upload_psk)

    def is_root(self, username):
        return self.users.is_root(username)

    def get_web_user(self, username):
        return self.users.get_web_user(username)

    def list_web_users(self):
        return self.users.list_web_users()

    def create_web_user(self, username, password):
        return self.users.create_web_user(username, password)

    def delete_web_user(self, username):
        return self.users.delete_web_user(username)

    def change_web_user_password(self, username, password):
        return self.users.change_web_user_password(username, password)

    def reload_web_users(self, config):
        return self.users.reload_web_users(config)

    def authenticate_user(self, username, password):
        return self.users.authenticate_user(username, password)

    def create_session(self, username):
        return self.session_store.create_session(username)

    def get_session(self, token):
        return self.session_store.get_session(token)

    def delete_session(self, token):
        return self.session_store.delete_session(token)

    def cleanup_expired_sessions(self):
        return self.session_store.cleanup_expired_sessions()

    def invalidate_user_sessions(self, username):
        return self.session_store.invalidate_user_sessions(username)
