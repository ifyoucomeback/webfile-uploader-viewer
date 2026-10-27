"""files HTTP 接口。"""

import asyncio

from fastapi import APIRouter, HTTPException, Request

from shared.file_http import file_http_error

from ..dependencies import (
    require_web_session,
)

router = APIRouter()


@router.get("/api/admin/files")
async def admin_files(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    client_name: str = "",
    keyword: str = "",
):
    services = request.app.state.services
    require_web_session(request)
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50
    if page_size > 500:
        page_size = 500
    files = services.uploads.list_files()
    if client_name:
        files = [item for item in files if item.get("client_name") == client_name]
    if keyword:
        keyword_lower = keyword.lower()
        files = [
            item
            for item in files
            if (
                keyword_lower in item.get("file_name", "").lower()
                or keyword_lower in item.get("relative_path", "").lower()
            )
        ]
    total = len(files)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "success": True,
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": files[start:end],
    }


@router.delete("/api/admin/file")
async def admin_delete_file(request: Request):
    services = request.app.state.services
    session = require_web_session(request)
    username = session["username"]
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求数据格式错误")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="请求数据必须是对象")
    client_name = data.get("client_name")
    relative_path = data.get("relative_path")
    if not isinstance(client_name, str) or not client_name:
        raise HTTPException(status_code=400, detail="client_name 不能为空")
    if not isinstance(relative_path, str) or not relative_path:
        raise HTTPException(status_code=400, detail="relative_path 不能为空")
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            services.uploads.delete_file,
            client_name,
            relative_path,
        )
        services.audit.write(
            username=username,
            action="delete_file",
            success=True,
            client_name=client_name,
            relative_path=relative_path,
            deleted_file=result.get("deleted_file", False),
            deleted_metadata=result.get("deleted_metadata", False),
        )
        return result
    except ValueError as e:
        services.audit.write(
            username=username,
            action="delete_file",
            success=False,
            client_name=client_name,
            relative_path=relative_path,
            error=str(e),
        )
        raise file_http_error(e) from e
    except Exception as e:
        services.audit.write(
            username=username,
            action="delete_file",
            success=False,
            client_name=client_name,
            relative_path=relative_path,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="删除文件失败")


@router.delete("/api/admin/files")
async def admin_delete_files(request: Request):
    services = request.app.state.services
    session = require_web_session(request)
    username = session["username"]
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求数据格式错误")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="请求数据必须是对象")
    files = data.get("files")
    if not isinstance(files, list):
        raise HTTPException(status_code=400, detail="files 必须是列表")
    if not files:
        raise HTTPException(status_code=400, detail="files 不能为空")
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, services.uploads.delete_files, files)
    except Exception as e:
        services.audit.write(
            username=username,
            action="delete_files",
            success=False,
            total=len(files),
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="批量删除失败")
    for item in result.get("items", []):
        if not isinstance(item, dict):
            continue
        services.audit.write(
            username=username,
            action="delete_file",
            success=item.get("success", False),
            client_name=item.get("client_name"),
            relative_path=item.get("relative_path"),
            deleted_file=item.get("deleted_file", False),
            deleted_metadata=item.get("deleted_metadata", False),
            error=item.get("error"),
        )
    services.audit.write(
        username=username,
        action="delete_files",
        success=result.get("success", False),
        total=result.get("total", 0),
        deleted=result.get("deleted", 0),
        failed=result.get("failed", 0),
    )
    return result
