"""客户端 status 接口。"""

from fastapi import APIRouter, Query, Request

from ..client_info import get_client_info

router = APIRouter()


@router.get("/api/client")
async def get_client(request: Request):
    application = request.app.state.runtime.application
    if application is not None:
        return application.client_info
    return get_client_info()


@router.get("/api/status")
async def get_status(request: Request, include_queue: bool = True):
    application = request.app.state.runtime.application
    if application is None:
        return {
            "running": False,
            "enabled": False,
            "server_connected": False,
            "last_server_success_time": None,
            "last_server_error": None,
            "current": None,
            "currents": [],
            "active_count": 0,
            "max_concurrent_uploads": 1,
            "retrying": [],
            "queue": [],
            "queue_count": 0,
            "uploading": False,
            "speed": 0,
        }
    uploader_status = application.uploader.get_status()
    queue_items = []
    for item in application.queue.snapshot() if include_queue else ():
        queue_items.append(
            {
                "path": item["path"],
                "name": item["name"],
                "relative_path": item.get("relative_path", item["name"]),
                "size": item["size"],
                "extension": item.get("extension", ""),
            }
        )
    return {
        "running": application.running,
        "enabled": application.enabled,
        "client": application.client_info,
        "directories": (application.monitor.directories),
        "interval": (application.monitor.interval),
        "max_bandwidth": (application.uploader.max_bandwidth),
        "server_connected": (uploader_status["server_connected"]),
        "last_server_success_time": (uploader_status["last_server_success_time"]),
        "last_server_error": (uploader_status["last_server_error"]),
        "uploading": (uploader_status["uploading"]),
        "current": (uploader_status["current"]),
        "currents": uploader_status["currents"],
        "active_count": len(application.active_files),
        "max_concurrent_uploads": application.max_concurrent_uploads,
        "retrying": (
            list(application.workers.retrying.values()) if include_queue else []
        ),
        "retry_count": len(application.workers.retrying),
        "queue": queue_items,
        "queue_count": application.upload_queue.qsize(),
        "speed": (uploader_status["speed"]),
        "bandwidth": uploader_status["bandwidth"],
    }


@router.get("/api/queue")
async def get_queue(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    application = request.app.state.runtime.application
    if application is None:
        return {
            "success": True,
            "page": 1,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
            "items": [],
        }
    result = application.queue.page(page, page_size)
    result["items"] = [
        {
            "name": item["name"],
            "relative_path": item.get("relative_path", item["name"]),
            "size": item["size"],
            "extension": item.get("extension", ""),
        }
        for item in result["items"]
    ]
    return result
