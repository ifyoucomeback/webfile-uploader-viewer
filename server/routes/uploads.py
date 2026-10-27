"""uploads HTTP 接口。"""

from fastapi import APIRouter, File, Form, Request, UploadFile

from ..dependencies import (
    require_upload_psk,
    require_web_session,
)

router = APIRouter()


@router.get("/api/upload/files")
async def upload_files(request: Request):
    services = request.app.state.services
    require_upload_psk(request)
    client_ip = request.client.host
    try:
        client_name = services.uploads.get_client_name(client_ip)
        files = services.uploads.list_files()
        items = []
        for item in files:
            if not isinstance(item, dict):
                continue
            if item.get("client_name") != client_name:
                continue
            items.append(
                {
                    "client_name": client_name,
                    "file_name": item.get("file_name", ""),
                    "relative_path": item.get("relative_path", ""),
                    "file_size": int(item.get("file_size", 0)),
                    "sha256": str(item.get("sha256", "")).lower(),
                }
            )
        return {
            "success": True,
            "client_name": client_name,
            "total": len(items),
            "files": items,
        }
    except Exception as e:
        print(f"[SYNC] 获取客户端文件列表失败: client={client_ip}, 错误={e}")
        return {"success": False, "error": "获取文件列表失败"}


@router.get("/api/admin/uploads")
async def admin_uploads(request: Request):
    services = request.app.state.services
    require_web_session(request)
    uploads = services.uploads.list_uploads()
    return {"success": True, "total": len(uploads), "items": uploads}


@router.post("/api/upload/init")
async def upload_init(request: Request):
    require_upload_psk(request)
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("请求数据必须是对象")
        return await request.app.state.services.coordinator.initialize(
            request.client.host, data
        )
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/api/upload/chunk")
async def upload_chunk(
    request: Request,
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk_offset: int = Form(...),
    chunk: UploadFile = File(...),
):
    require_upload_psk(request)
    try:
        return await request.app.state.services.coordinator.save_chunk(
            request.client.host,
            upload_id,
            chunk_index,
            chunk_offset,
            await chunk.read(),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/api/upload/complete")
async def upload_complete(request: Request):
    require_upload_psk(request)
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("请求数据必须是对象")
        return await request.app.state.services.coordinator.complete(
            request.client.host, data.get("upload_id")
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}
