"""后台维护的启动、停止及取消处理。"""

import asyncio
import logging

from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


class MaintenanceService:
    def __init__(self, auth, runtime, interval=300):
        self.auth = auth
        self.runtime = runtime
        self.interval = interval
        self.task = None

    async def start(self):
        await run_in_threadpool(self.runtime.load_incomplete_uploads)
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run())

    async def stop(self):
        task, self.task = self.task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def run(self):
        while True:
            try:
                self.auth.cleanup_expired_sessions()
            except Exception:
                logger.exception("清理过期 Session 失败")
            try:
                await self.runtime.cleanup_expired_uploads_runtime()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("清理过期上传任务失败")
            await asyncio.sleep(self.interval)
