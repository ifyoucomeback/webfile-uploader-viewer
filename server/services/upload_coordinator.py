"""协调每个客户端最多五个文件任务，按目标独立续传、替换和校验归属。"""

from starlette.concurrency import run_in_threadpool

from .upload_identity import is_same_target, is_same_upload

MAX_CLIENT_UPLOADS = 5


class UploadCoordinator:
    def __init__(self, uploads, runtime):
        self.uploads = uploads
        self.runtime = runtime

    async def initialize(self, client_ip, data):
        lock = await self.runtime.get_client_init_lock(client_ip)
        async with lock:
            client_name = await run_in_threadpool(
                self.uploads.get_client_name, client_ip
            )
            # 修改旧任务前先验证新请求，避免无效请求清除已有断点。
            self.uploads.validate_sha256(data.get("sha256"))
            self.uploads._build_target_path(client_name, data.get("relative_path"))
            file_size = int(data.get("file_size"))
            if file_size < 0 or (
                self.uploads.tasks.max_file_size > 0
                and file_size > self.uploads.tasks.max_file_size
            ):
                raise ValueError("文件大小超出服务端允许范围")
            pending = []
            for upload_id in await self.runtime.get_client_uploads(client_ip):
                existing = await self._handle_existing(
                    client_ip, client_name, upload_id, data
                )
                if existing is None:
                    continue
                if existing.get("status") in ("uploading", "error"):
                    return existing
                pending.append(existing)
            if len(pending) >= MAX_CLIENT_UPLOADS:
                return {
                    **pending[0],
                    "status": "busy",
                    "uploads": pending,
                    "message": "该客户端已有 5 个未完成任务，请先恢复其中的文件",
                }
            result = await run_in_threadpool(
                self.uploads.init_upload,
                client_ip=client_ip,
                file_name=data.get("file_name"),
                relative_path=data.get("relative_path"),
                file_size=file_size,
                file_extension=data.get("file_extension"),
                upload_time=data.get("upload_time"),
                sha256=data.get("sha256"),
            )
            if result.get("status") in ("new", "uploading") and result.get("upload_id"):
                await self.runtime.set_client_upload(client_ip, result["upload_id"])
            return result

    async def _handle_existing(self, client_ip, client_name, upload_id, data):
        lock = await self.runtime.get_upload_lock(upload_id)
        async with lock:
            try:
                status = await run_in_threadpool(
                    self.uploads.get_upload_status, upload_id
                )
            except ValueError:
                await self.runtime.clear_client_upload(client_ip, upload_id)
                return None
            if status.get("expired", False):
                removed = await run_in_threadpool(
                    self.uploads.cleanup_expired_upload, upload_id
                )
            elif is_same_upload(
                status,
                data.get("file_name"),
                data.get("relative_path"),
                data.get("file_size"),
                data.get("sha256"),
            ):
                return {
                    "status": "uploading",
                    "upload_id": upload_id,
                    "uploaded_chunks": status["uploaded_chunks"],
                    "chunk_size": status["chunk_size"],
                }
            elif is_same_target(status, client_name, data.get("relative_path")):
                removed = await run_in_threadpool(self.uploads.cancel_upload, upload_id)
            else:
                return status
            if not removed:
                return {"status": "error", "error": "无法清理旧上传任务，请稍后重试"}
            await self.runtime.clear_client_upload(client_ip, upload_id)
            return None

    async def save_chunk(
        self, client_ip, upload_id, chunk_index, chunk_offset, chunk_data
    ):
        lock = await self.runtime.get_upload_lock(upload_id)
        async with lock:
            if not await self.runtime.owns_upload(client_ip, upload_id):
                return {"success": False, "error": "upload_id 不属于当前客户端"}
            return await run_in_threadpool(
                self.uploads.save_chunk,
                upload_id,
                chunk_index,
                chunk_offset,
                chunk_data,
            )

    async def complete(self, client_ip, upload_id):
        if not upload_id:
            return {"success": False, "error": "upload_id 不能为空"}
        lock = await self.runtime.get_upload_lock(upload_id)
        async with lock:
            if not await self.runtime.owns_upload(client_ip, upload_id):
                return {"success": False, "error": "upload_id 不属于当前客户端"}
            try:
                status = await run_in_threadpool(
                    self.uploads.get_upload_status, upload_id
                )
            except ValueError:
                await self.runtime.clear_client_upload(client_ip, upload_id)
                return {
                    "success": False,
                    "status": "not_found",
                    "error": "上传任务不存在",
                }
            if status.get("expired", False):
                if await run_in_threadpool(
                    self.uploads.cleanup_expired_upload, upload_id
                ):
                    await self.runtime.clear_client_upload(client_ip, upload_id)
                return {
                    "success": False,
                    "status": "expired",
                    "error": "上传任务已经过期",
                }
            result = await run_in_threadpool(self.uploads.complete_upload, upload_id)
            if result.get("status") in ("completed", "expired"):
                await self.runtime.clear_client_upload(client_ip, upload_id)
            return result
