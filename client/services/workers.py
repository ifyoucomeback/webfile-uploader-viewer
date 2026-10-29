"""按 FIFO 分派文件，动态控制并发，并独立安排失败任务的重试。"""

import asyncio
import os
import time

from ..upload_settings import MAX_CONCURRENT_UPLOADS
from ..uploader import UploadBusyError


class ClientWorkers:
    def __init__(self, app):
        self.app = app
        self.tasks = {}
        self.retry_tasks = {}
        self.retrying = {}

    async def process_file(self, file_info):
        path = file_info["path"]
        print(f"[UPLOAD] 开始上传: {path}")
        result = await self.app.uploader.upload(file_info)
        if result.get("status") in ("exists", "uploaded"):
            self.app.server_files[self.app.sync._file_key(file_info)] = {
                "file_name": file_info.get("name", os.path.basename(path)),
                "relative_path": os.path.abspath(path),
                "file_size": result.get("size", file_info.get("size", 0)),
                "sha256": result.get("sha256", file_info.get("sha256")),
            }
            self.app.server_files_time = asyncio.get_running_loop().time()
            print(f"[OK] 上传完成: {path}")
        return result

    async def upload_loop(self):
        try:
            await self.app.uploader.start()
            while self.app.running:
                self.app.queue_event.clear()
                while True:
                    async with self.app.file_operation_lock:
                        limit = min(
                            MAX_CONCURRENT_UPLOADS,
                            max(1, self.app.max_concurrent_uploads),
                        )
                        if (
                            not self.app.enabled
                            or len(self.tasks) >= limit
                            or self.app.upload_queue.empty()
                        ):
                            break
                        file_info = self.app.upload_queue.get_nowait()
                        path = file_info["path"]
                        if path in self.app.active_files:
                            self.app.upload_queue.task_done()
                            continue
                        self.app.active_files[path] = file_info
                        task = asyncio.create_task(self._upload_one(file_info))
                        self.tasks[path] = task
                        task.add_done_callback(
                            lambda done, path=path: self._completed(path, done)
                        )
                try:
                    await asyncio.wait_for(self.app.queue_event.wait(), timeout=1)
                except asyncio.TimeoutError:
                    pass
        finally:
            tasks = list(self.tasks.values()) + list(self.retry_tasks.values())
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            self.tasks.clear()
            self.retry_tasks.clear()
            self.retrying.clear()

    def _completed(self, path, task):
        if self.tasks.get(path) is task:
            self.tasks.pop(path, None)
        if not task.cancelled() and task.exception() is not None:
            print(f"[UPLOAD LOOP ERROR] {path}: {task.exception()}")
        self.app.queue_event.set()

    async def _upload_one(self, file_info):
        path = file_info["path"]
        try:
            await self.process_file(file_info)
        except UploadBusyError as exc:
            if not self.app.recovery._prioritize_recovered_upload(
                exc.upload_info, file_info
            ):
                self._schedule_retry(file_info, exc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[UPLOAD ERROR] {path}: {exc}")
            self._schedule_retry(file_info, exc)
        finally:
            self.app.active_files.pop(path, None)
            self.app.upload_queue.task_done()
            queued = any(item["path"] == path for item in self.app.queue.snapshot())
            if not queued and path not in self.retrying:
                self.app.queued_files.discard(path)
                if path in self.app.pending_sync_files and self.app.running:
                    self.app.pending_sync_files.discard(path)
                    # 上传中发生变化的文件重新排队；暂停时也保留待处理项。
                    self.app.queue.add_file_to_queue(file_info)
            self.app.queue_event.set()

    def _schedule_retry(self, file_info, error):
        path = file_info["path"]
        self.cancel_retry(path)
        interval = self.app.monitor.get_interval()
        if interval <= 0:
            interval = 60
        self.retrying[path] = {
            **file_info,
            "retry_at": time.time() + interval,
            "error": str(error),
        }
        self.retry_tasks[path] = asyncio.create_task(self._retry(file_info, interval))

    async def _retry(self, file_info, interval):
        path = file_info["path"]
        try:
            await asyncio.sleep(interval)
            if self.app.running:
                self.app.queue._ensure_file_in_queue(file_info)
                self.app.queue_event.set()
        finally:
            if self.retry_tasks.get(path) is asyncio.current_task():
                self.retry_tasks.pop(path, None)
                self.retrying.pop(path, None)
            if path not in self.app.active_files and not any(
                item["path"] == path for item in self.app.queue.snapshot()
            ):
                self.app.queued_files.discard(path)

    def cancel_retry(self, path):
        task = self.retry_tasks.pop(path, None)
        self.retrying.pop(path, None)
        if task is not None:
            task.cancel()

    async def monitor_loop(self):
        self.app.monitor.start()
        try:
            while self.app.running:
                # 首次成功前持续检查，网络暂时不可用时也不会丢失启动同步。
                await self.app.sync.add_initial_files()
                await self.app.sync.add_changed_files()
                await asyncio.sleep(0.2)
        finally:
            self.app.monitor.stop()
