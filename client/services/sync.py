"""本地与服务端文件索引比较及按需同步。"""

import asyncio
import hashlib
import os


class FileSynchronizer:
    """本地与服务端文件索引比较及按需同步。"""

    def __init__(self, app):
        self.app = app

    @staticmethod
    def _file_key(file_info):
        path = os.path.abspath(os.path.normpath(str(file_info.get("path", ""))))
        return (path, str(file_info.get("name", os.path.basename(path))))

    @staticmethod
    def _server_key(item):
        path = str(item.get("relative_path", ""))
        try:
            path = os.path.abspath(os.path.normpath(path))
        except Exception:
            path = ""
        return (path, str(item.get("file_name", "")))

    @staticmethod
    def _sha256_file(file_path):
        digest = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(1024 * 1024)
                if not data:
                    break
                digest.update(data)
        return digest.hexdigest()

    async def _get_local_sha256(self, file_info):
        path = self.app.queue._normalize_path(file_info.get("path", ""))
        if not path or not os.path.isfile(path):
            return None
        try:
            stat = os.stat(path)
        except OSError:
            return None
        key = (path, stat.st_size, stat.st_mtime_ns)
        cached = self.app.local_sha256_cache.get(path)
        if cached and cached[0] == key:
            return cached[1]
        loop = asyncio.get_running_loop()
        sha256 = await loop.run_in_executor(None, self._sha256_file, path)
        try:
            stat2 = os.stat(path)
        except OSError:
            return None
        if stat2.st_size != stat.st_size or stat2.st_mtime_ns != stat.st_mtime_ns:
            return None
        self.app.local_sha256_cache[path] = (key, sha256)
        return sha256

    async def refresh_server_files(self, force=False):
        now = asyncio.get_running_loop().time()
        if not force and now - self.app.server_files_time < self.app.server_files_ttl:
            return self.app.server_files
        async with self.app.sync_lock:
            now = asyncio.get_running_loop().time()
            if (
                not force
                and now - self.app.server_files_time < self.app.server_files_ttl
            ):
                return self.app.server_files
            files = await self.app.uploader.get_server_files()
            server_files = {}
            for item in files:
                key = self._server_key(item)
                if key[0]:
                    server_files[key] = item
            self.app.server_files = server_files
            self.app.server_files_time = now
            print(f"[SYNC] 获取服务端文件列表: {len(self.app.server_files)} 个")
            return self.app.server_files

    def _queue_sync_file(self, file_info, path):
        added = self.app.queue.add_file_to_queue(file_info)
        if not added and path in self.app.queued_files:
            self.app.pending_sync_files.add(path)
        return added

    async def sync_file(self, file_info, force_refresh=False):
        if not self.app.enabled:
            return False
        path = self.app.queue._normalize_path(file_info.get("path", ""))
        if not path or not os.path.isfile(path):
            return False
        file_info = dict(file_info)
        file_info["path"] = path
        try:
            stat = os.stat(path)
        except OSError:
            return False
        file_info["size"] = stat.st_size
        file_info["mtime"] = stat.st_mtime
        if force_refresh:
            await self.refresh_server_files(True)
        server_file = self.app.server_files.get(self._file_key(file_info))
        if server_file is None:
            print(f"[SYNC] 服务端不存在，加入上传: {path}")
            return self._queue_sync_file(file_info, path)
        server_size = int(server_file.get("file_size", -1))
        if server_size != stat.st_size:
            print(f"[SYNC] 大小不同，加入上传: {path}")
            return self._queue_sync_file(file_info, path)
        server_sha256 = str(server_file.get("sha256") or "").lower()
        if not server_sha256:
            print(f"[SYNC] 服务端无 SHA256，加入上传: {path}")
            return self._queue_sync_file(file_info, path)
        local_sha256 = await self._get_local_sha256(file_info)
        if not local_sha256:
            print(f"[SYNC] 文件正在变化，暂不加入队列: {path}")
            return False
        if local_sha256.lower() == server_sha256:
            print(f"[SKIP] 文件已同步: {path}")
            return False
        print(f"[SYNC] SHA256 不同，加入上传: {path}")
        return self._queue_sync_file(file_info, path)

    async def sync_all_files(self, force_refresh=True):
        files = self.app.monitor.scan()
        await self.refresh_server_files(force_refresh)
        added = 0
        for file_info in files:
            if await self.sync_file(file_info):
                added += 1
        return {"scanned": len(files), "added": added}

    async def add_all_files_to_queue(self):
        return await self.sync_all_files(True)

    async def add_initial_files(self):
        try:
            result = await self.sync_all_files(True)
            print(
                f"[STARTUP] 初始同步: 发现 {result['scanned']} 个文件，需要上传 {result['added']} 个文件"
            )
        except Exception as e:
            print(f"[STARTUP SYNC ERROR] {type(e).__name__}: {e}")

    async def add_changed_files(self):
        if not self.app.enabled:
            self.app.monitor.get_changed_files()
            return
        changed_files = self.app.monitor.get_changed_files()
        if not changed_files:
            return
        try:
            await self.refresh_server_files(False)
        except Exception as e:
            print(f"[SYNC ERROR] 获取服务端文件列表失败: {type(e).__name__}: {e}")
            return
        for file_info in changed_files:
            try:
                await self.sync_file(file_info)
            except Exception as e:
                print(
                    f"[SYNC ERROR] {file_info.get('path', '')}: {type(e).__name__}: {e}"
                )
