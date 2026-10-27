"""按实际存储路径进行文本和视频预览。"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from shared.file_http import file_http_error
from shared.file_preview import read_text_preview
from shared.file_streaming import video_response

from ..dependencies import require_web_session

router = APIRouter()


@router.get("/api/admin/file-browser/preview")
async def preview_text(request: Request, client_name: str, path: str):
    require_web_session(request)
    try:
        file_path = request.app.state.services.file_browser.resolve_file(
            client_name, path
        )
        result = await run_in_threadpool(read_text_preview, file_path)
        return JSONResponse(result, headers={"Cache-Control": "no-store"})
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc


@router.get("/api/admin/file-browser/stream")
async def preview_video(request: Request, client_name: str, path: str):
    require_web_session(request)
    try:
        file_path = request.app.state.services.file_browser.resolve_file(
            client_name, path
        )
        return video_response(file_path, request)
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc
