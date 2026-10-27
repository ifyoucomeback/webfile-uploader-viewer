"""客户端 tasks 接口。"""

from fastapi import APIRouter, Request

from ..config import load_config, save_config

router = APIRouter()


@router.post("/api/task")
async def update_task(request: Request, data: dict):
    application = request.app.state.runtime.application
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        return {"success": False, "error": "enabled 必须是 true 或 false"}
    config = load_config()
    if "upload" not in config:
        config["upload"] = {}
    config["upload"]["enabled"] = enabled
    save_config(config)
    if application is not None:
        application.enabled = enabled
        application.config = config
        if enabled:
            await application.add_changed_files()
            if not application.upload_queue.empty():
                application.queue_event.set()
    return {"success": True, "enabled": enabled}


@router.post("/api/upload-all")
async def upload_all(request: Request):
    application = request.app.state.runtime.application
    if application is None:
        return {"success": False, "error": "客户端尚未启动"}
    result = await application.add_all_files_to_queue()
    if result["added"] > 0:
        application.queue_event.set()
    return {
        "success": True,
        "scanned": result["scanned"],
        "added": result["added"],
        "enabled": application.enabled,
    }
