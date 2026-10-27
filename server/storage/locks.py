"""供文件删除和上传提交共同使用的线程锁。"""

import threading

from shared.file_access import canonical_path


class StorageLocks:
    def __init__(self, normalize_paths=False):
        self._locks = {}
        self._guard = threading.Lock()
        self.normalize_paths = normalize_paths

    def get(self, key):
        if self.normalize_paths:
            key = canonical_path(key)
        with self._guard:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]
