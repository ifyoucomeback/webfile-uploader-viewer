"""每个应用独立的上传协调锁、客户端任务映射与任务恢复。"""

import asyncio
import os


class UploadRuntime:
    """每个应用独立的上传协调锁、客户端任务映射与任务恢复。"""

    def __init__(self, config, upload_manager):
        self.config = config
        self.upload_manager = upload_manager
        self.client_uploads = {}
        self.client_uploads_guard = asyncio.Lock()
        self.client_init_locks = {}
        self.client_init_locks_guard = asyncio.Lock()
        self.upload_locks = {}
        self.upload_locks_guard = asyncio.Lock()

    async def get_client_init_lock(self, client_ip):
        async with self.client_init_locks_guard:
            if client_ip not in self.client_init_locks:
                self.client_init_locks[client_ip] = asyncio.Lock()
            return self.client_init_locks[client_ip]

    async def get_upload_lock(self, upload_id):
        async with self.upload_locks_guard:
            if upload_id not in self.upload_locks:
                self.upload_locks[upload_id] = asyncio.Lock()
            return self.upload_locks[upload_id]

    async def get_client_uploads(self, client_ip):
        async with self.client_uploads_guard:
            return list(self.client_uploads.get(client_ip, {}))

    async def get_client_upload(self, client_ip):
        uploads = await self.get_client_uploads(client_ip)
        return uploads[0] if uploads else None

    async def owns_upload(self, client_ip, upload_id):
        async with self.client_uploads_guard:
            return upload_id in self.client_uploads.get(client_ip, {})

    async def set_client_upload(self, client_ip, upload_id):
        async with self.client_uploads_guard:
            self.client_uploads.setdefault(client_ip, {})[upload_id] = True

    async def clear_client_upload(self, client_ip, upload_id):
        async with self.client_uploads_guard:
            uploads = self.client_uploads.get(client_ip)
            if uploads is not None:
                uploads.pop(upload_id, None)
                if not uploads:
                    self.client_uploads.pop(client_ip, None)

    def load_incomplete_uploads(self):
        """恢复所有未完成目标；同一目标若有旧重复任务，只采用最新一份。"""
        directory = os.path.abspath(self.config["storage"]["uploading_directory"])
        if not os.path.isdir(directory):
            return
        candidates = {}
        for upload_id in os.listdir(directory):
            try:
                metadata, _ = self.upload_manager._load_metadata(upload_id)
                client_ip = metadata.get("client_ip")
                if metadata.get("upload_id") != upload_id or not client_ip:
                    continue
                if self.upload_manager.is_upload_expired(metadata):
                    self.upload_manager.cleanup_expired_upload(upload_id)
                    continue
                _, target = self.upload_manager._build_target_path(
                    metadata["client_name"], metadata["relative_path"]
                )
                key = (client_ip, os.path.normcase(target))
                timestamp = int(
                    metadata.get("updated_time", metadata.get("created_time", 0))
                )
                previous = candidates.get(key)
                if previous is None or timestamp > previous[0]:
                    candidates[key] = (timestamp, upload_id)
            except Exception as exc:
                print(f"[RECOVERY] 读取任务失败: {upload_id}, 错误: {exc}")
        self.client_uploads.clear()
        for (client_ip, _), (_, upload_id) in sorted(
            candidates.items(), key=lambda item: item[1]
        ):
            self.client_uploads.setdefault(client_ip, {})[upload_id] = True
        print(f"[RECOVERY] 恢复 {len(candidates)} 个未完成上传任务")

    def find_expired_upload_candidates(self):
        candidates = []
        try:
            uploads = self.upload_manager.list_uploads()
        except Exception as e:
            print(f"[CLEANUP] 扫描上传任务失败: {e}")
            return candidates
        for upload in uploads:
            if not isinstance(upload, dict):
                continue
            if not upload.get("expired", False):
                continue
            upload_id = upload.get("upload_id")
            if not isinstance(upload_id, str) or not upload_id:
                continue
            candidates.append((upload_id, upload.get("client_ip")))
        return candidates

    async def cleanup_expired_upload_runtime(self, upload_id, client_ip):
        upload_lock = await self.get_upload_lock(upload_id)
        async with upload_lock:
            loop = asyncio.get_running_loop()
            try:
                cleaned = await loop.run_in_executor(
                    None, self.upload_manager.cleanup_expired_upload, upload_id
                )
            except Exception as e:
                print(f"[CLEANUP] 清理过期上传任务失败: {upload_id}, 错误: {e}")
                return False
        if cleaned and client_ip:
            await self.clear_client_upload(client_ip, upload_id)
        if cleaned:
            print(f"[CLEANUP] 清理过期上传任务成功: upload_id={upload_id}")
        return cleaned

    async def cleanup_expired_uploads_runtime(self):
        loop = asyncio.get_running_loop()
        candidates = await loop.run_in_executor(
            None, self.find_expired_upload_candidates
        )
        if not candidates:
            return 0
        cleaned = 0
        for upload_id, client_ip in candidates:
            try:
                if await self.cleanup_expired_upload_runtime(upload_id, client_ip):
                    cleaned += 1
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[CLEANUP] 处理过期上传任务失败: {upload_id}, 错误: {e}")
        return cleaned
