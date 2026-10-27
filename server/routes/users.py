"""users HTTP 接口。"""

import asyncio

from fastapi import APIRouter, HTTPException, Request

from ..dependencies import (
    require_root_session,
)

router = APIRouter()


@router.get("/api/admin/users")
async def admin_list_users(request: Request):
    services = request.app.state.services
    require_root_session(request)
    users = services.auth.list_web_users()
    return {"success": True, "users": users, "total": len(users)}


@router.post("/api/admin/users")
async def admin_create_user(request: Request):
    services = request.app.state.services
    session = require_root_session(request)
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求数据格式错误")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="请求数据必须是对象")
    username = data.get("username")
    password = data.get("password")
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: services.auth.create_web_user(username, password),
        )
    except ValueError as e:
        services.audit.write(
            session["username"],
            "create_user",
            False,
            target_username=username,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        services.audit.write(
            session["username"],
            "create_user",
            False,
            target_username=username,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="创建用户失败")
    services.audit.write(
        session["username"], "create_user", True, target_username=username
    )
    return {"success": True, "username": username}


@router.put("/api/admin/users/{username}/password")
async def admin_change_user_password(username: str, request: Request):
    services = request.app.state.services
    session = require_root_session(request)
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求数据格式错误")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="请求数据必须是对象")
    password = data.get("password")
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: services.auth.change_web_user_password(username, password),
        )
    except ValueError as e:
        services.audit.write(
            session["username"],
            "change_user_password",
            False,
            target_username=username,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        services.audit.write(
            session["username"],
            "change_user_password",
            False,
            target_username=username,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="修改密码失败")
    sessions_invalidated = services.auth.invalidate_user_sessions(username)
    services.audit.write(
        session["username"],
        "change_user_password",
        True,
        target_username=username,
        sessions_invalidated=sessions_invalidated,
    )
    return {
        "success": True,
        "username": username,
        "sessions_invalidated": sessions_invalidated,
    }


@router.delete("/api/admin/users/{username}")
async def admin_delete_user(username: str, request: Request):
    services = request.app.state.services
    session = require_root_session(request)
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: services.auth.delete_web_user(username)
        )
    except ValueError as e:
        services.audit.write(
            session["username"],
            "delete_user",
            False,
            target_username=username,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        services.audit.write(
            session["username"],
            "delete_user",
            False,
            target_username=username,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="删除用户失败")
    sessions_invalidated = services.auth.invalidate_user_sessions(username)
    services.audit.write(
        session["username"],
        "delete_user",
        True,
        target_username=username,
        sessions_invalidated=sessions_invalidated,
    )
    return {
        "success": True,
        "username": username,
        "sessions_invalidated": sessions_invalidated,
    }
