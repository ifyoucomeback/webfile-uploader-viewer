"""选择客户端后，按服务器实际目录浏览文件。"""

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from shared.file_http import file_http_error

from ..dependencies import require_web_session

router = APIRouter()


@router.get("/api/admin/file-browser/clients")
async def browser_clients(request: Request):
    require_web_session(request)
    try:
        items = await run_in_threadpool(request.app.state.services.file_browser.clients)
        return {"success": True, "items": items, "total": len(items)}
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc


@router.get("/api/admin/file-browser")
async def browse_files(
    request: Request,
    client_name: str,
    path: str = "",
    page: int = 1,
    page_size: int = 50,
    keyword: str = "",
):
    require_web_session(request)
    try:
        return await run_in_threadpool(
            request.app.state.services.file_browser.browse,
            client_name,
            path,
            page,
            page_size,
            keyword,
        )
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc
