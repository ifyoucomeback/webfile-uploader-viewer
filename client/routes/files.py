"""客户端 files 接口。"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/files")
async def get_files(request: Request, page: int = 1, page_size: int = 50):
    application = request.app.state.runtime.application
    if application is None:
        return {
            "items": [],
            "page": 1,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
        }
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50
    if page_size > 200:
        page_size = 200
    files = application.monitor.scan()
    files.sort(key=lambda item: item.get("path", ""))
    total = len(files)
    if total == 0:
        return {
            "items": [],
            "page": 1,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
        }
    total_pages = (total + page_size - 1) // page_size
    if page > total_pages:
        page = total_pages
    start = (page - 1) * page_size
    end = start + page_size
    items = files[start:end]
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
