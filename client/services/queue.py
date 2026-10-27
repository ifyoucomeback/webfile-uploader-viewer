"""本地上传队列去重、移除和入队。"""

import os

from shared.file_access import canonical_path


class FileQueue:
    """本地上传队列去重、移除和入队。"""

    def __init__(self, app):
        self.app = app

    def add_file_to_queue(self, file_info):
        file_path = self._normalize_path(file_info.get("path", ""))
        if not file_path or file_path in self.app.queued_files:
            return False
        if not os.path.isfile(file_path):
            return False
        file_info = dict(file_info)
        file_info["path"] = file_path
        try:
            stat = os.stat(file_path)
            file_info["size"] = stat.st_size
            file_info["mtime"] = stat.st_mtime
        except OSError:
            return False
        self.app.queued_files.add(file_path)
        self.app.upload_queue.put_nowait(file_info)
        self.app.queue_event.set()
        print(f"[QUEUE] 加入上传队列: {file_path}")
        return True

    def _normalize_path(self, file_path):
        if not isinstance(file_path, str):
            return ""
        if not file_path:
            return ""
        try:
            return os.path.abspath(os.path.normpath(file_path))
        except Exception:
            return ""

    def _remove_file_from_queue(self, file_info):
        if not file_info:
            return False
        target_path = self._normalize_path(file_info.get("path", ""))
        if not target_path:
            return False
        queue = self.app.upload_queue._queue
        for item in list(queue):
            item_path = self._normalize_path(item.get("path", ""))
            if item_path == target_path:
                try:
                    queue.remove(item)
                    return True
                except ValueError:
                    return False
        return False

    def _ensure_file_in_queue(self, file_info):
        if not file_info:
            return False
        file_path = file_info.get("path")
        if not file_path:
            return False
        file_path = self._normalize_path(file_path)
        if not file_path:
            return False
        file_info = dict(file_info)
        file_info["path"] = file_path
        if not os.path.isfile(file_path):
            return False
        for item in list(self.app.upload_queue._queue):
            item_path = self._normalize_path(item.get("path", ""))
            if item_path == file_path:
                return True
        try:
            stat = os.stat(file_path)
            file_info["size"] = stat.st_size
            file_info["mtime"] = stat.st_mtime
        except OSError:
            return False
        self.app.queued_files.add(file_path)
        self.app.upload_queue.put_nowait(file_info)
        return True

    def snapshot(self):
        return list(self.app.upload_queue._queue)

    def remove_pending(self, path):
        key = canonical_path(path)
        queue = self.app.upload_queue._queue
        for item in list(queue):
            if canonical_path(item["path"]) == key:
                queue.remove(item)
                self.app.upload_queue.task_done()
                self.app.queued_files.discard(item["path"])

    def prioritize(self, file_info, index=0):
        """移动已有项；新项通过 put_nowait 入队，保持 join/task_done 计数一致。"""
        if not self._ensure_file_in_queue(file_info):
            return False
        path = self._normalize_path(file_info.get("path", ""))
        queue = self.app.upload_queue._queue
        item = next(item for item in queue if item["path"] == path)
        queue.remove(item)
        queue.insert(index, item)
        return True
