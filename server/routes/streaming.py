"""保留原有视频播放地址，复用两端共用的 Range 实现。"""

from fastapi import APIRouter, Request

from shared.file_http import file_http_error
from shared.file_streaming import video_response

from ..dependencies import require_web_session
from ..services.video_files import get_video_file

router = APIRouter()


@router.get("/api/video/stream")
async def video_stream(request: Request, client_name: str, relative_path: str):
    require_web_session(request)
    try:
        return video_response(
            get_video_file(request, client_name, relative_path), request
        )
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc
