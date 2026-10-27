"""downloads HTTP 接口。"""

import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from ..dependencies import require_web_session
from ..services.video_files import get_video_file

router = APIRouter()


@router.get("/api/video/download")
async def video_download(request: Request, client_name: str, relative_path: str):
    require_web_session(request)
    file_path = get_video_file(request, client_name, relative_path)
    file_name = os.path.basename(file_path)
    return FileResponse(
        file_path, media_type="application/octet-stream", filename=file_name
    )
