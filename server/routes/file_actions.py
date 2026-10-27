"""按实际存储路径删除文件，保留用户操作审计。"""

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from shared.file_http import file_http_error

from ..dependencies import require_web_session

router = APIRouter()


@router.delete("/api/admin/file-browser/file")
async def delete_file(request: Request):
    session = require_web_session(request)
    services = request.app.state.services
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(400, "请求数据格式错误") from exc
    if not isinstance(body, dict):
        raise HTTPException(400, "请求数据必须是对象")
    details = {
        "client_name": body.get("client_name"),
        "stored_relative_path": body.get("path"),
    }
    try:
        result = await run_in_threadpool(
            services.file_browser.delete_file, body.get("client_name"), body.get("path")
        )
    except (ValueError, OSError) as exc:
        services.audit.write(
            session["username"], "delete_stored_file", False, **details, error=str(exc)
        )
        raise file_http_error(exc) from exc
    services.audit.write(
        session["username"],
        "delete_stored_file",
        True,
        **details,
        target_path=result.get("target_path"),
        deleted_metadata=result.get("deleted_metadata", False),
    )
    return result
