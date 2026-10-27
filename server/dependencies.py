"""Web 会话与上传 PSK 的统一认证入口。"""

from fastapi import HTTPException, Request

SESSION_COOKIE_NAME = "web_session"


def require_web_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    session = request.app.state.services.auth.get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="登录已过期")
    return session


def require_root_session(request: Request):
    session = require_web_session(request)
    if not request.app.state.services.auth.is_root(session["username"]):
        raise HTTPException(
            status_code=403, detail="只有 root 用户可以执行用户管理操作"
        )
    return session


def require_upload_psk(request: Request):
    provided_psk = request.headers.get("X-Upload-PSK", "")
    if not request.app.state.services.auth.verify_upload_psk(provided_psk):
        raise HTTPException(status_code=401, detail="上传认证失败")
    return True
