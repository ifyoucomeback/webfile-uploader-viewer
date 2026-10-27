"""本地文件下载。"""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from shared.file_http import file_http_error

from ..dependencies import local_browser

router = APIRouter()


@router.get("/api/files/download")
async def download_file(request: Request, root: str, path: str):
    browser = local_browser(request)
    try:
        file_path = browser.resolve_file(root, path)
        return FileResponse(
            file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
            headers={"X-Content-Type-Options": "nosniff"},
        )
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc
