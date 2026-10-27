"""内存会话创建、验证、注销与过期清理。"""

import secrets
import threading
import time


class SessionStore:
    """内存会话创建、验证、注销与过期清理。"""

    SESSION_TOKEN_BYTES = 32

    def __init__(self, expire_hours=12):
        self.session_expire_hours = float(expire_hours)
        self.session_expire_seconds = self.session_expire_hours * 3600
        self.sessions = {}
        self.sessions_guard = threading.Lock()

    def create_session(self, username):
        """
        创建 Web Session。

        返回 Session Token。
        """
        if not isinstance(username, str) or not username:
            raise ValueError("username cannot be empty")
        token = secrets.token_urlsafe(self.SESSION_TOKEN_BYTES)
        now = time.time()
        session = {
            "username": username,
            "created_time": now,
            "last_activity": now,
            "expire_time": (now + self.session_expire_seconds),
        }
        with self.sessions_guard:
            self.sessions[token] = session
        return token

    def get_session(self, token):
        """
        获取并验证 Session。

        Session 有效时返回 Session 信息。
        无效或过期时返回 None。

        每次有效访问都会更新 last_activity。

        expire_time 不会因为访问而无限延长。
        """
        if not isinstance(token, str):
            return None
        if not token:
            return None
        now = time.time()
        with self.sessions_guard:
            session = self.sessions.get(token)
            if session is None:
                return None
            if now >= session["expire_time"]:
                del self.sessions[token]
                return None
            session["last_activity"] = now
            return {
                "username": session["username"],
                "created_time": session["created_time"],
                "last_activity": session["last_activity"],
                "expire_time": session["expire_time"],
            }

    def delete_session(self, token):
        """
        删除 Session。

        返回：

        True  = Session 存在并成功删除
        False = Session 不存在
        """
        if not isinstance(token, str):
            return False
        with self.sessions_guard:
            if token not in self.sessions:
                return False
            del self.sessions[token]
            return True

    def cleanup_expired_sessions(self):
        """
        清理已经过期的 Session。

        返回清理数量。
        """
        now = time.time()
        removed = 0
        with self.sessions_guard:
            expired_tokens = [
                token
                for token, session in self.sessions.items()
                if now >= session["expire_time"]
            ]
            for token in expired_tokens:
                del self.sessions[token]
                removed += 1
        return removed

    def invalidate_user_sessions(self, username):
        if not isinstance(username, str) or not username:
            return 0
        with self.sessions_guard:
            tokens = [
                token
                for token, session in self.sessions.items()
                if session.get("username") == username
            ]
            for token in tokens:
                del self.sessions[token]
        return len(tokens)
