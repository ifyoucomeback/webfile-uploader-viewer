"""监控目录内的本地文件浏览和删除，与上传调度共享操作锁。"""

import os

from starlette.concurrency import run_in_threadpool

from shared.directory_listing import list_directory
from shared.file_access import FileAccessError, canonical_path, resolve_inside


class LocalFileBrowser:
    def __init__(self, app):
        self.app = app

    def roots(self):
        seen, roots = set(), []
        for value in self.app.monitor.directories:
            path = os.path.abspath(value)
            if os.path.normcase(path) in seen:
                continue
            seen.add(os.path.normcase(path))
            roots.append(
                {
                    "name": path,
                    "root": path,
                    "path": "",
                    "kind": "directory",
                    "size": None,
                    "preview_kind": "none",
                    "available": os.path.isdir(path),
                }
            )
        return roots

    def root_path(self, root):
        if not isinstance(root, str) or "\x00" in root:
            raise FileAccessError(400, "监控目录格式错误")
        for item in self.roots():
            if os.path.normcase(root) == os.path.normcase(item["root"]):
                return item["root"]
        raise FileAccessError(403, "只能访问当前配置的监控目录")

    def browse(self, root="", path="", page=1, page_size=50, keyword=""):
        if not root:
            if path:
                raise FileAccessError(400, "请先选择监控目录")
            roots = [
                item
                for item in self.roots()
                if keyword.casefold() in item["name"].casefold()
            ]
            return {
                "success": True,
                "root": "",
                "path": "",
                "absolute_path": "",
                "parent_path": None,
                "page": 1,
                "page_size": max(1, len(roots)),
                "total": len(roots),
                "total_pages": 1 if roots else 0,
                "items": roots,
            }
        result = list_directory(self.root_path(root), path, page, page_size, keyword)
        result["root"] = root
        for item in result["items"]:
            item["root"] = root
            item["absolute_path"] = os.path.join(root, *item["path"].split("/"))
            if item["kind"] == "file":
                key = canonical_path(os.path.join(root, item["path"]))
                item["busy"] = any(
                    canonical_path(active) == key for active in self.app.active_files
                )
        return result

    def resolve_file(self, root, path):
        return resolve_inside(self.root_path(root), path, file_only=True)

    async def delete_file(self, root, path):
        async with self.app.file_operation_lock:
            target = self.resolve_file(root, path)
            key = canonical_path(target)
            if any(
                canonical_path(active) == key for active in self.app.active_files
            ) or self.app.uploader.is_uploading(target):
                raise FileAccessError(409, "文件正在上传，完成后才能删除")
            await run_in_threadpool(target.unlink)
            self.app.queue.remove_pending(target)
            for retry_path in list(self.app.workers.retrying):
                if canonical_path(retry_path) == key:
                    self.app.workers.cancel_retry(retry_path)
                    self.app.queued_files.discard(retry_path)
            self.app.pending_sync_files = {
                p for p in self.app.pending_sync_files if canonical_path(p) != key
            }
            self.app.monitor._handle_file_deleted(str(target))
            self.app.queue_event.set()
            return {"success": True, "path": path, "deleted_file": True}
