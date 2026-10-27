"""auth HTTP 接口。"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..dependencies import SESSION_COOKIE_NAME, require_web_session

router = APIRouter()


@router.post("/api/auth/login")
async def auth_login(request: Request):
    services = request.app.state.services
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求数据格式错误")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="请求数据必须是对象")
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str):
        raise HTTPException(status_code=400, detail="username 不能为空")
    if not isinstance(password, str):
        raise HTTPException(status_code=400, detail="password 不能为空")
    user = services.auth.authenticate_user(username, password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = services.auth.create_session(user["username"])
    response = JSONResponse({"success": True, "username": user["username"]})
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=int(services.auth.session_expire_seconds),
        path="/",
    )
    return response


@router.post("/api/auth/logout")
async def auth_logout(request: Request):
    services = request.app.state.services
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        services.auth.delete_session(token)
    response = JSONResponse({"success": True})
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/api/auth/me")
async def auth_me(request: Request):
    session = require_web_session(request)
    return {
        "success": True,
        "username": session["username"],
        "created_time": session["created_time"],
        "last_activity": session["last_activity"],
        "expire_time": session["expire_time"],
    }
