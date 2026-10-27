"""客户端后台任务与进程锁的完整生命周期。"""

import asyncio
from pathlib import Path

from .application import ClientApplication
from .single_instance import SingleInstance

BASE_DIR = Path(__file__).resolve().parent


class ClientRuntime:
    def __init__(self, application_factory=ClientApplication, lock_file=None):
        self.application_factory = application_factory
        self.application = None
        self.tasks = []
        self.instance = SingleInstance(lock_file or BASE_DIR / "client.lock")

    async def start(self):
        self.instance.acquire()
        try:
            self.application = self.application_factory()
            self.tasks = [
                asyncio.create_task(self.application.monitor_loop()),
                asyncio.create_task(self.application.upload_loop()),
            ]
        except BaseException:
            await self.stop()
            raise

    async def stop(self):
        try:
            # Workers must stop before their HTTP session and monitor are closed.
            if self.application is not None:
                self.application.running = False
                self.application.queue_event.set()
            for task in self.tasks:
                task.cancel()
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks.clear()
            if self.application is not None:
                await self.application.shutdown()
        finally:
            self.application = None
            self.instance.release()
