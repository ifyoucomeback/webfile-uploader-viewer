"""storage HTTP 接口。"""

from fastapi import APIRouter, Request

from ..dependencies import require_web_session

router = APIRouter()


@router.get("/api/admin/storage")
async def admin_storage(request: Request):
    services = request.app.state.services
    require_web_session(request)
    return {
        "success": True,
        "storage": services.uploads.get_storage_info(),
    }
