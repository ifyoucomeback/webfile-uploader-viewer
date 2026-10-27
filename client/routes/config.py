"""客户端 config 接口。"""

from fastapi import APIRouter, HTTPException, Request

from ..config import load_config, save_config
from ..upload_settings import DEFAULT_CONCURRENT_UPLOADS, validate_concurrency

router = APIRouter()


@router.get("/api/config")
async def get_config(request: Request):
    return load_config()


@router.post("/api/config")
async def update_config(request: Request, config: dict):
    application = request.app.state.runtime.application
    current_config = load_config()
    for section in ("server", "monitor", "upload"):
        if section in config and not isinstance(config[section], dict):
            raise HTTPException(status_code=400, detail=f"{section} 必须是对象")
        config[section] = {**current_config.get(section, {}), **config.get(section, {})}
    if "directories" not in config["monitor"]:
        old_directory = config["monitor"].get("directory", "")
        if old_directory:
            config["monitor"]["directories"] = [old_directory]
        else:
            config["monitor"]["directories"] = []
    if "directory" in config["monitor"]:
        del config["monitor"]["directory"]
    if "enabled" not in config["upload"]:
        config["upload"]["enabled"] = current_config.get("upload", {}).get(
            "enabled", True
        )
    if "psk" not in config["upload"]:
        config["upload"]["psk"] = current_config.get("upload", {}).get("psk", "")
    elif not isinstance(config["upload"]["psk"], str):
        config["upload"]["psk"] = str(config["upload"]["psk"])
    concurrency = config["upload"].get(
        "max_concurrent_uploads",
        current_config.get("upload", {}).get(
            "max_concurrent_uploads", DEFAULT_CONCURRENT_UPLOADS
        ),
    )
    try:
        config["upload"]["max_concurrent_uploads"] = validate_concurrency(concurrency)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_config(config)
    if application is not None:
        application.reload_config()
    return {"success": True, "config": load_config()}
