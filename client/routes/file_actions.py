"""本地文件删除，不删除服务端副本。"""

from fastapi import APIRouter, HTTPException, Request

from shared.file_http import file_http_error

from ..dependencies import local_browser

router = APIRouter()


@router.delete("/api/files/file")
async def delete_file(request: Request):
    browser = local_browser(request)
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(400, "请求数据格式错误") from exc
    if not isinstance(body, dict):
        raise HTTPException(400, "请求数据必须是对象")
    try:
        return await browser.delete_file(body.get("root"), body.get("path"))
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc
