"""按日期持久化操作审计。"""

import json
import os
import threading
from datetime import datetime


class AuditLogger:
    """按日期持久化操作审计。"""

    def __init__(self, upload_directory):
        self.directory = os.path.join(upload_directory, ".audit")
        self.guard = threading.Lock()

    def write(self, username, action, success, **details):
        try:
            os.makedirs(self.directory, mode=0o700, exist_ok=True)
            now = datetime.now().astimezone()
            log_file = os.path.join(self.directory, now.strftime("%Y-%m-%d") + ".log")
            record = {
                "time": now.isoformat(),
                "username": username,
                "action": action,
                "success": bool(success),
            }
            record.update(details)
            with self.guard:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f.flush()
        except Exception as e:
            print(f"[AUDIT] 写入审计日志失败: {e}")
