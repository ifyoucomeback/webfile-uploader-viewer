"""两端视频预览共用的单段 HTTP Range 响应。"""

import mimetypes
import re
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from .file_access import FileAccessError
from .file_preview import preview_kind


def video_response(file_path, request):
    if preview_kind(file_path) != "video":
        raise FileAccessError(415, "此格式不支持视频预览，请下载后查看")
    file_path = Path(file_path)
    size = file_path.stat().st_size
    media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    headers = {"Accept-Ranges": "bytes", "X-Content-Type-Options": "nosniff"}
    value = request.headers.get("range")
    if not value:
        return FileResponse(file_path, media_type=media_type, headers=headers)
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", value.strip())
    if not match or not any(match.groups()) or size == 0:
        raise HTTPException(
            416, "Range 格式或范围错误", headers={"Content-Range": f"bytes */{size}"}
        )
    left, right = match.groups()
    if left:
        start, end = int(left), int(right) if right else size - 1
    else:
        length = int(right)
        if length <= 0:
            raise HTTPException(
                416, "Range 范围错误", headers={"Content-Range": f"bytes */{size}"}
            )
        start, end = max(0, size - length), size - 1
    if start >= size or end < start:
        raise HTTPException(
            416, "Range 范围错误", headers={"Content-Range": f"bytes */{size}"}
        )
    end = min(end, size - 1)
    length = end - start + 1

    def chunks():
        with file_path.open("rb") as stream:
            stream.seek(start)
            remaining = length
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers.update(
        {"Content-Length": str(length), "Content-Range": f"bytes {start}-{end}/{size}"}
    )
    return StreamingResponse(
        chunks(), status_code=206, media_type=media_type, headers=headers
    )
