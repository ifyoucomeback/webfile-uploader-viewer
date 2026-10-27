"""Root 与普通 Web 用户的认证和持久化。"""

import hmac
import threading

from ..config import save_config
from .passwords import PasswordHasher


class UserStore:
    """Root 与普通 Web 用户的认证和持久化。"""

    def __init__(self, config):
        self.config = config
        auth_config = config.get("auth", {})
        root = auth_config.get("root", {})
        if not isinstance(root, dict):
            root = {}
        self.root_username = root.get("username", "root")
        self.root_password_hash = root.get("password_hash", "")
        users = auth_config.get("web_users", [])
        self.web_users = users if isinstance(users, list) else []
        self.web_users_guard = threading.Lock()

    def is_root(self, username):
        """
        判断指定用户名是否为 Root。

        Root 不是通过 web_users 保存的普通用户。
        """
        if not isinstance(username, str):
            return False
        if not isinstance(self.root_username, str):
            return False
        return hmac.compare_digest(username, self.root_username)

    def get_web_user(self, username):
        """
        获取普通 Web 用户。

        找到返回用户字典的副本。
        不存在返回 None。

        Root 不属于 web_users。
        """
        if not isinstance(username, str):
            return None
        with self.web_users_guard:
            for user in self.web_users:
                if not isinstance(user, dict):
                    continue
                stored_username = user.get("username")
                if not isinstance(stored_username, str):
                    continue
                if hmac.compare_digest(username, stored_username):
                    return dict(user)
        return None

    def list_web_users(self):
        """
        返回所有普通 Web 用户。

        不返回 password_hash。
        """
        users = []
        with self.web_users_guard:
            for user in self.web_users:
                if not isinstance(user, dict):
                    continue
                username = user.get("username")
                if not isinstance(username, str):
                    continue
                users.append({"username": username})
        return users

    def create_web_user(self, username, password):
        """
        创建普通 Web 用户。

        Root 账号不能通过此方法创建。

        返回：

        {
            "username": "test"
        }
        """
        if not isinstance(username, str):
            raise ValueError("username 必须是字符串")
        if not isinstance(password, str):
            raise ValueError("password 必须是字符串")
        username = username.strip()
        if not username:
            raise ValueError("username 不能为空")
        if not password:
            raise ValueError("password 不能为空")
        if len(username) > 64:
            raise ValueError("username 长度不能超过 64 个字符")
        if self.is_root(username):
            raise ValueError("不能创建与 root 相同的用户名")
        password_hash = PasswordHasher.hash_password(password)
        with self.web_users_guard:
            for user in self.web_users:
                if not isinstance(user, dict):
                    continue
                stored_username = user.get("username")
                if not isinstance(stored_username, str):
                    continue
                if hmac.compare_digest(username, stored_username):
                    raise ValueError("用户名已经存在")
            new_user = {"username": username, "password_hash": password_hash}
            self.web_users.append(new_user)
            self.config.setdefault("auth", {})
            self.config["auth"]["web_users"] = self.web_users
            try:
                save_config(self.config)
            except Exception:
                self.web_users.pop()
                self.config["auth"]["web_users"] = self.web_users
                raise
        return {"username": username}

    def delete_web_user(self, username):
        """
        删除普通 Web 用户。

        Root 不能删除。
        """
        if not isinstance(username, str):
            raise ValueError("username 必须是字符串")
        username = username.strip()
        if not username:
            raise ValueError("username 不能为空")
        if self.is_root(username):
            raise ValueError("不能删除 root 用户")
        with self.web_users_guard:
            delete_index = None
            for index, user in enumerate(self.web_users):
                if not isinstance(user, dict):
                    continue
                stored_username = user.get("username")
                if not isinstance(stored_username, str):
                    continue
                if hmac.compare_digest(username, stored_username):
                    delete_index = index
                    break
            if delete_index is None:
                raise ValueError("用户不存在")
            deleted_user = self.web_users.pop(delete_index)
            self.config.setdefault("auth", {})
            self.config["auth"]["web_users"] = self.web_users
            try:
                save_config(self.config)
            except Exception:
                self.web_users.insert(delete_index, deleted_user)
                self.config["auth"]["web_users"] = self.web_users
                raise
        return {"username": username}

    def change_web_user_password(self, username, password):
        """
        修改普通 Web 用户密码。

        Root 不通过此方法修改。
        """
        if not isinstance(username, str):
            raise ValueError("username 必须是字符串")
        if not isinstance(password, str):
            raise ValueError("password 必须是字符串")
        username = username.strip()
        if not username:
            raise ValueError("username 不能为空")
        if not password:
            raise ValueError("password 不能为空")
        if self.is_root(username):
            raise ValueError("root 密码不能通过普通用户密码接口修改")
        new_password_hash = PasswordHasher.hash_password(password)
        with self.web_users_guard:
            target_user = None
            for user in self.web_users:
                if not isinstance(user, dict):
                    continue
                stored_username = user.get("username")
                if not isinstance(stored_username, str):
                    continue
                if hmac.compare_digest(username, stored_username):
                    target_user = user
                    break
            if target_user is None:
                raise ValueError("用户不存在")
            old_password_hash = target_user.get("password_hash")
            target_user["password_hash"] = new_password_hash
            self.config.setdefault("auth", {})
            self.config["auth"]["web_users"] = self.web_users
            try:
                save_config(self.config)
            except Exception:
                target_user["password_hash"] = old_password_hash
                self.config["auth"]["web_users"] = self.web_users
                raise
        return {"username": username}

    def reload_web_users(self, config):
        """
        使用新的 config 更新 Web 用户配置。

        主要用于配置发生外部变化时重新加载。
        """
        if not isinstance(config, dict):
            raise ValueError("config 必须是字典")
        auth_config = config.get("auth", {})
        if not isinstance(auth_config, dict):
            auth_config = {}
        web_users = auth_config.get("web_users", [])
        if not isinstance(web_users, list):
            web_users = []
        with self.web_users_guard:
            self.config = config
            self.web_users = web_users
        return True

    def authenticate_user(self, username, password):
        """
        验证 Web 用户。

        Root 和普通 Web 用户都可以登录。

        成功返回：

        {
            "username": "root"
        }

        失败返回 None。
        """
        if not isinstance(username, str):
            return None
        if not isinstance(password, str):
            return None
        # ========================================================
        # Root 用户
        # ========================================================
        if (
            isinstance(self.root_username, str)
            and isinstance(self.root_password_hash, str)
            and self.root_username
            and self.root_password_hash
        ):
            if hmac.compare_digest(username, self.root_username):
                if PasswordHasher.verify_password(password, self.root_password_hash):
                    return {"username": self.root_username}
                return None
        # ========================================================
        # 普通 Web 用户
        #
        # 这里增加 web_users_guard。
        #
        # 管理线程可能同时修改用户列表，
        # 登录线程不能在列表修改过程中直接遍历。
        # ========================================================
        with self.web_users_guard:
            for user in self.web_users:
                if not isinstance(user, dict):
                    continue
                stored_username = user.get("username")
                stored_password_hash = user.get("password_hash")
                if not isinstance(stored_username, str):
                    continue
                if not isinstance(stored_password_hash, str):
                    continue
                if not hmac.compare_digest(username, stored_username):
                    continue
                if not PasswordHasher.verify_password(password, stored_password_hash):
                    return None
                return {"username": stored_username}
        return None
