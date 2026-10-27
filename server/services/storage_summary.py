"""汇总客户端活动和磁盘使用情况。"""

import shutil


class StorageSummary:
    """汇总客户端活动和磁盘使用情况。"""

    def __init__(self, files, tasks):
        self.files = files
        self.tasks = tasks
        self.upload_directory = files.upload_directory

    def list_clients(self):
        clients = {}
        for item in self.files.list_files():
            client_name = item.get("client_name", "")
            if not client_name:
                continue
            if client_name not in clients:
                clients[client_name] = {
                    "client_name": client_name,
                    "client_ip": item.get("client_ip", ""),
                    "file_count": 0,
                    "uploading_count": 0,
                    "last_activity": 0,
                }
            client = clients[client_name]
            client["file_count"] += 1
            completed_time = int(item.get("completed_time", 0) or 0)
            if completed_time > client["last_activity"]:
                client["last_activity"] = completed_time
        for item in self.tasks.list_uploads():
            client_name = item.get("client_name", "")
            if not client_name:
                continue
            if client_name not in clients:
                clients[client_name] = {
                    "client_name": client_name,
                    "client_ip": item.get("client_ip", ""),
                    "file_count": 0,
                    "uploading_count": 0,
                    "last_activity": 0,
                }
            client = clients[client_name]
            client["uploading_count"] += 1
            updated_time = int(item.get("updated_time", 0) or 0)
            if updated_time > client["last_activity"]:
                client["last_activity"] = updated_time
        result = list(clients.values())
        result.sort(key=lambda item: item.get("last_activity", 0), reverse=True)
        return result

    def get_storage_info(self):
        usage = shutil.disk_usage(self.upload_directory)
        total = usage.total
        used = usage.used
        free = usage.free
        if total > 0:
            used_percent = used / total * 100
        else:
            used_percent = 0
        return {
            "path": self.upload_directory,
            "total": total,
            "used": used,
            "free": free,
            "used_percent": round(used_percent, 2),
        }
