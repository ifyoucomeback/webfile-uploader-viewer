"""clients HTTP 接口。"""

from fastapi import APIRouter, Request

from ..dependencies import require_web_session

router = APIRouter()


@router.get("/api/admin/clients")
async def admin_clients(request: Request):
    services = request.app.state.services
    require_web_session(request)
    clients = services.uploads.list_clients()
    return {"success": True, "total": len(clients), "items": clients}
