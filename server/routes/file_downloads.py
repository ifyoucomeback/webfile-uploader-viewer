"""按实际存储路径下载所选客户端文件。"""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from shared.file_http import file_http_error

from ..dependencies import require_web_session

router = APIRouter()


@router.get("/api/admin/file-browser/download")
async def download_file(request: Request, client_name: str, path: str):
    require_web_session(request)
    try:
        file_path = request.app.state.services.file_browser.resolve_file(
            client_name, path
        )
        return FileResponse(
            file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
            headers={"X-Content-Type-Options": "nosniff"},
        )
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc
