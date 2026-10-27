"""共享 HTTP 连接和总带宽，为每个上传文件维护独立进度。"""

import asyncio
import os

from shared.file_access import canonical_path

from .transfer.connection import UploadConnection
from .transfer.errors import UploadBusyError, UploadError
from .transfer.progress import UploadProgress
from .transfer.protocol import UploadProtocol
from .upload_settings import MAX_CONCURRENT_UPLOADS

__all__ = ["Uploader", "UploadError", "UploadBusyError"]


class Uploader:
    def __init__(self, config, client_info):
        self.config = config
        self.client_info = client_info
        self.server_host = config["server"]["host"]
        self.server_port = int(config["server"]["port"])
        self.max_bandwidth = int(config["upload"]["max_bandwidth"])
        self.upload_psk = config["upload"].get("psk", "")
        self.base_url = f"http://{self.server_host}:{self.server_port}"
        self.chunk_size = 1024 * 1024
        self._session = None
        self._slots = asyncio.Semaphore(MAX_CONCURRENT_UPLOADS)
        self._bandwidth_lock = asyncio.Lock()
        self._progress = {}
        self._upload_tasks = set()
        self.server_connected = False
        self.last_server_success_time = None
        self.last_server_error = None
        self.health_check_interval = 5
        self.health_check_task = None
        self.health_check_running = False
        self.connection = UploadConnection(self)

    async def upload(self, file_info):
        task = asyncio.current_task()
        self._upload_tasks.add(task)
        try:
            # 调度器负责用户设定的并发数，这里额外保证硬上限不超过 5。
            async with self._slots:
                await self.start()
                path = os.path.abspath(file_info["path"])
                if path in self._progress:
                    raise UploadError(f"文件正在上传: {path}")
                progress = UploadProgress(file_info)
                self._progress[path] = progress
                try:
                    return await UploadProtocol(self, progress)._upload_file(file_info)
                finally:
                    self._progress.pop(path, None)
        finally:
            self._upload_tasks.discard(task)

    async def _limit_bandwidth(self, data_size):
        # 所有文件共享限速锁，避免并发数增加后总带宽也成倍增加。
        async with self._bandwidth_lock:
            if self.max_bandwidth > 0:
                await asyncio.sleep(data_size / self.max_bandwidth)

    def update_bandwidth(self, max_bandwidth):
        self.max_bandwidth = int(max_bandwidth)

    def is_uploading(self, path):
        key = canonical_path(path)
        return any(canonical_path(active) == key for active in self._progress)

    def get_status(self):
        currents = [progress.snapshot() for progress in self._progress.values()]
        return {
            "uploading": bool(currents),
            "current": currents[0] if currents else None,
            "currents": currents,
            "active_count": len(currents),
            "speed": sum(item["speed"] for item in currents),
            "server_connected": self.server_connected,
            "last_server_success_time": self.last_server_success_time,
            "last_server_error": self.last_server_error,
        }

    async def start(self):
        await self.connection.start()

    async def close(self):
        tasks = [
            task for task in self._upload_tasks if task is not asyncio.current_task()
        ]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.connection.close()

    async def get_server_files(self):
        return await self.connection.get_server_files()
