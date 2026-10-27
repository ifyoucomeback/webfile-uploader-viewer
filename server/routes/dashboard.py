"""dashboard HTTP 接口。"""

from fastapi import APIRouter, Request

from ..dependencies import require_web_session

router = APIRouter()


@router.get("/api/admin/dashboard")
async def admin_dashboard(request: Request):
    services = request.app.state.services
    require_web_session(request)
    files = services.uploads.list_files()
    uploads = services.uploads.list_uploads()
    clients = services.uploads.list_clients()
    storage = services.uploads.get_storage_info()
    total_file_size = sum(int(item.get("file_size", 0)) for item in files)
    return {
        "success": True,
        "files": {"count": len(files), "size": total_file_size},
        "uploads": {"count": len(uploads)},
        "clients": {"count": len(clients)},
        "storage": storage,
    }
