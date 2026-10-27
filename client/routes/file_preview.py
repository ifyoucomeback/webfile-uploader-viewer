"""本地文本与视频预览，视频支持 Range 拖动播放。"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from shared.file_http import file_http_error
from shared.file_preview import read_text_preview
from shared.file_streaming import video_response

from ..dependencies import local_browser

router = APIRouter()


@router.get("/api/files/preview")
async def preview_text(request: Request, root: str, path: str):
    browser = local_browser(request)
    try:
        file_path = browser.resolve_file(root, path)
        result = await run_in_threadpool(read_text_preview, file_path)
        return JSONResponse(result, headers={"Cache-Control": "no-store"})
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc


@router.get("/api/files/stream")
async def preview_video(request: Request, root: str, path: str):
    browser = local_browser(request)
    try:
        return video_response(browser.resolve_file(root, path), request)
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc
