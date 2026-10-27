"""恢复服务端断点任务并调整上传顺序。"""

import os


class UploadRecovery:
    """恢复服务端断点任务并调整上传顺序。"""

    def __init__(self, app):
        self.app = app

    def _is_same_file(self, file_info, upload_info):
        if not file_info:
            return False
        if not upload_info:
            return False
        try:
            local_path = self.app.queue._normalize_path(file_info.get("path", ""))
            server_path = self.app.queue._normalize_path(
                upload_info.get("relative_path", "")
            )
            local_name = str(file_info.get("name", ""))
            server_name = str(upload_info.get("file_name", ""))
            local_size = int(file_info.get("size", -1))
            server_size = int(upload_info.get("file_size", -1))
            if not local_path:
                return False
            if not server_path:
                return False
            if local_path != server_path:
                return False
            if local_name != server_name:
                return False
            if local_size != server_size:
                return False
            return True
        except Exception:
            return False

    def _find_recovered_file(self, upload_info):
        if not upload_info:
            return None
        for item in self.app.queue.snapshot():
            if self._is_same_file(item, upload_info):
                return item
        try:
            files = self.app.monitor.scan()
        except Exception as e:
            print(f"[RESUME] 扫描本地文件失败: {type(e).__name__}: {e}")
            return None
        for item in files:
            if self._is_same_file(item, upload_info):
                return item
        return None

    def _prioritize_recovered_upload(self, upload_info, current_file_info):
        if not upload_info:
            return False
        current_path = self.app.queue._normalize_path(
            (current_file_info or {}).get("path", "")
        )
        candidates = upload_info.get("uploads") or [upload_info]
        recovered_file = None
        for candidate in candidates:
            item = self._find_recovered_file(candidate)
            if item is None:
                continue
            path = self.app.queue._normalize_path(item.get("path", ""))
            # 其他工作任务正在传的文件不能再次插队，否则会重复上传同一路径。
            if path in self.app.active_files and path != current_path:
                continue
            recovered_file = item
            break
        if recovered_file is None:
            print("[RESUME] " "服务端断点任务对应的本地文件不存在")
            return False
        recovered_path = self.app.queue._normalize_path(recovered_file.get("path", ""))
        if not recovered_path:
            print("[RESUME] " "服务端断点任务对应文件路径无效")
            return False
        if not os.path.isfile(recovered_path):
            print(f"[RESUME] 服务端断点文件已经不存在: {recovered_path}")
            return False
        self.app.workers.cancel_retry(recovered_path)
        self.app.queue.prioritize(recovered_file)
        self.app.queued_files.add(recovered_path)
        if current_file_info is not None:
            current_path = self.app.queue._normalize_path(
                current_file_info.get("path", "")
            )
            if (
                current_path
                and current_path != recovered_path
                and os.path.isfile(current_path)
            ):
                self.app.workers.cancel_retry(current_path)
                self.app.queue.prioritize(current_file_info, index=1)
                self.app.queued_files.add(current_path)
        print(f"[RESUME] 已将服务端断点任务移到队列最前面: {recovered_path}")
        if current_file_info is not None:
            current_path = current_file_info.get("path")
            print(f"[RESUME] 当前文件将在断点任务完成后继续: {current_path}")
        else:
            print("[RESUME] " "当前没有需要重新排队的文件")
        self.app.queue_event.set()
        return True
