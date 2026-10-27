"""客户端组件装配、共享状态、配置重载与关闭。"""

import asyncio

from .client_info import get_client_info
from .config import load_config
from .monitor import DirectoryMonitor
from .services.local_files import LocalFileBrowser
from .services.queue import FileQueue
from .services.recovery import UploadRecovery
from .services.sync import FileSynchronizer
from .services.workers import ClientWorkers
from .upload_settings import DEFAULT_CONCURRENT_UPLOADS
from .uploader import Uploader


class ClientApplication:
    """客户端组件装配、共享状态、配置重载与关闭。"""

    def __init__(self):
        self.config = load_config()
        self.client_info = get_client_info()
        self.monitor = DirectoryMonitor(
            directories=self.config["monitor"].get("directories", []),
            include_extensions=self.config["monitor"]["include_extensions"],
            exclude_extensions=self.config["monitor"]["exclude_extensions"],
            interval=self.config["monitor"]["interval"],
        )
        self.uploader = Uploader(config=self.config, client_info=self.client_info)
        self.running = True
        self.enabled = self.config["upload"].get("enabled", True)
        self.upload_queue = asyncio.Queue()
        self.queued_files = set()
        self.active_files = {}
        self.file_operation_lock = asyncio.Lock()
        self.max_concurrent_uploads = self.config["upload"].get(
            "max_concurrent_uploads", DEFAULT_CONCURRENT_UPLOADS
        )
        self.queue_event = asyncio.Event()
        self.sync_lock = asyncio.Lock()
        self.server_files = {}
        self.server_files_time = 0
        self.server_files_ttl = 60
        self.local_sha256_cache = {}
        self.pending_sync_files = set()
        self.queue = FileQueue(self)
        self.sync = FileSynchronizer(self)
        self.recovery = UploadRecovery(self)
        self.workers = ClientWorkers(self)
        self.local_files = LocalFileBrowser(self)

    def reload_config(self):
        self.config = load_config()
        self.enabled = self.config["upload"].get("enabled", True)
        self.max_concurrent_uploads = self.config["upload"].get(
            "max_concurrent_uploads", DEFAULT_CONCURRENT_UPLOADS
        )
        self.monitor.update_config(
            directories=self.config["monitor"].get("directories", []),
            include_extensions=self.config["monitor"]["include_extensions"],
            exclude_extensions=self.config["monitor"]["exclude_extensions"],
            interval=self.config["monitor"]["interval"],
        )
        self.uploader.server_host = self.config["server"]["host"]
        self.uploader.server_port = int(self.config["server"]["port"])
        self.uploader.base_url = (
            f"http://{self.uploader.server_host}:{self.uploader.server_port}"
        )
        self.uploader.update_bandwidth(self.config["upload"]["max_bandwidth"])
        self.uploader.upload_psk = self.config["upload"].get("psk", "")
        self.server_files = {}
        self.server_files_time = 0
        self.local_sha256_cache.clear()
        self.queue_event.set()

    async def shutdown(self):
        self.running = False
        print("[SYSTEM] 正在停止客户端...")
        self.queue_event.set()
        self.monitor.stop()
        await self.uploader.close()

    def add_file_to_queue(self, file_info):
        return self.queue.add_file_to_queue(file_info)

    async def refresh_server_files(self, force=False):
        return await self.sync.refresh_server_files(force)

    async def sync_file(self, file_info, force_refresh=False):
        return await self.sync.sync_file(file_info, force_refresh)

    async def sync_all_files(self, force_refresh=True):
        return await self.sync.sync_all_files(force_refresh)

    async def add_all_files_to_queue(self):
        return await self.sync.add_all_files_to_queue()

    async def add_initial_files(self):
        return await self.sync.add_initial_files()

    async def add_changed_files(self):
        return await self.sync.add_changed_files()

    async def process_file(self, file_info):
        return await self.workers.process_file(file_info)

    async def upload_loop(self):
        return await self.workers.upload_loop()

    async def monitor_loop(self):
        return await self.workers.monitor_loop()
