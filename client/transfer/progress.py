"""每个文件独立的上传进度，避免并发任务覆盖彼此的状态。"""

import time


class UploadProgress:
    def __init__(self, file_info):
        self.file_info = dict(file_info)
        self.uploaded_bytes = 0
        self.speed = 0
        self.sha256 = None
        self.stage = "hashing"
        self._last_time = time.monotonic()

    def update(self, uploaded_bytes, transferred=True):
        now = time.monotonic()
        elapsed = now - self._last_time
        if transferred and elapsed > 0:
            self.speed = max(0, uploaded_bytes - self.uploaded_bytes) / elapsed
        self.uploaded_bytes = uploaded_bytes
        self._last_time = now

    def snapshot(self):
        return {
            "path": self.file_info["path"],
            "name": self.file_info["name"],
            "relative_path": self.file_info.get(
                "relative_path", self.file_info["name"]
            ),
            "size": int(self.file_info["size"]),
            "uploaded_bytes": self.uploaded_bytes,
            "speed": self.speed if time.monotonic() - self._last_time < 5 else 0,
            "sha256": self.sha256,
            "stage": self.stage,
        }
