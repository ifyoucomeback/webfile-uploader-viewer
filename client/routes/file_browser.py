"""本地目录与文件的分页浏览。"""

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from shared.file_http import file_http_error

from ..dependencies import local_browser

router = APIRouter()


@router.get("/api/files/browse")
async def browse_files(
    request: Request,
    root: str = "",
    path: str = "",
    page: int = 1,
    page_size: int = 50,
    keyword: str = "",
):
    browser = local_browser(request)
    try:
        return await run_in_threadpool(
            browser.browse, root, path, page, page_size, keyword
        )
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc
