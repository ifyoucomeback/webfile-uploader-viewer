"""已完成文件的索引、元数据和删除；不负责上传或 HTTP 下载。"""

import json
import os

from shared.file_access import FileAccessError


class FileRepository:
    """已完成文件的索引、元数据和删除；不负责上传或 HTTP 下载。"""

    def __init__(self, paths, locks):
        self.paths = paths
        self.locks = locks
        self.upload_directory = paths.upload_directory
        self.has_pending_upload = None

    def _write_file_metadata(self, metadata):
        client_name = self.paths._safe_client_name(metadata["client_name"])
        client_directory, _ = self.paths._build_target_path(
            client_name, metadata["relative_path"]
        )
        metadata_path = self.paths._build_metadata_path(
            client_directory, metadata["relative_path"]
        )
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        temporary_path = metadata_path + ".tmp"
        try:
            with open(temporary_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary_path, metadata_path)
        finally:
            if os.path.exists(temporary_path):
                try:
                    os.remove(temporary_path)
                except OSError:
                    pass

    def list_files(self):
        result = []
        if not os.path.isdir(self.upload_directory):
            return result
        for physical_client_name in os.listdir(self.upload_directory):
            client_directory = os.path.join(self.upload_directory, physical_client_name)
            if not os.path.isdir(client_directory):
                continue
            if physical_client_name == ".uploading":
                continue
            if physical_client_name.endswith("."):
                client_name = physical_client_name[:-1]
            else:
                client_name = physical_client_name
            if not client_name:
                continue
            metadata_directory = os.path.join(client_directory, ".metadata")
            if not os.path.isdir(metadata_directory):
                continue
            for root, dirs, files in os.walk(metadata_directory):
                for filename in files:
                    if not filename.endswith(".json"):
                        continue
                    metadata_path = os.path.join(root, filename)
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                        relative_path = metadata.get("relative_path")
                        if not relative_path:
                            continue
                        _, target_path = self.paths._build_target_path(
                            client_name, relative_path
                        )
                        if not os.path.isfile(target_path):
                            continue
                        actual_size = os.path.getsize(target_path)
                        result.append(
                            {
                                "client_name": metadata.get("client_name", client_name),
                                "client_ip": metadata.get("client_ip", ""),
                                "file_name": metadata.get("file_name", ""),
                                "relative_path": relative_path,
                                "file_size": actual_size,
                                "file_extension": metadata.get("file_extension", ""),
                                "upload_time": metadata.get("upload_time", ""),
                                "completed_time": metadata.get("completed_time", 0),
                                "sha256": metadata.get("sha256", ""),
                                "target_path": target_path,
                            }
                        )
                    except Exception as e:
                        print(f"[ADMIN] 读取文件元数据失败: {metadata_path}, 错误: {e}")
        result.sort(key=lambda item: item.get("completed_time", 0), reverse=True)
        return result

    def delete_file(self, client_name, relative_path):
        client_directory, target_path = self.paths._build_target_path(
            client_name, relative_path
        )
        metadata_path = self.paths._build_metadata_path(client_directory, relative_path)
        target_lock = self.locks.get(target_path)
        with target_lock:
            if self.has_pending_upload and self.has_pending_upload(target_path):
                raise FileAccessError(409, "该文件有未完成上传任务，暂不能删除")
            file_exists = os.path.isfile(target_path)
            metadata_exists = os.path.isfile(metadata_path)
            if not file_exists and not metadata_exists:
                raise ValueError("文件和对应元数据都不存在")
            deleted_file = False
            deleted_metadata = False
            if file_exists:
                try:
                    os.remove(target_path)
                    deleted_file = True
                except OSError as e:
                    raise ValueError(f"删除文件失败: {e}")
            if metadata_exists:
                try:
                    os.remove(metadata_path)
                    deleted_metadata = True
                except OSError as e:
                    raise ValueError(f"文件已删除，但元数据删除失败: {e}")
            metadata_directory = os.path.dirname(metadata_path)
            metadata_root = os.path.abspath(os.path.join(client_directory, ".metadata"))
            current_directory = metadata_directory
            while current_directory != metadata_root and current_directory.startswith(
                metadata_root + os.sep
            ):
                try:
                    os.rmdir(current_directory)
                except OSError:
                    break
                current_directory = os.path.dirname(current_directory)
            return {
                "success": True,
                "client_name": client_name,
                "relative_path": relative_path,
                "target_path": target_path,
                "metadata_path": metadata_path,
                "deleted_file": deleted_file,
                "deleted_metadata": deleted_metadata,
            }

    def delete_files(self, files):
        if not isinstance(files, list):
            raise ValueError("files 必须是列表")
        results = []
        deleted_count = 0
        failed_count = 0
        for item in files:
            if not isinstance(item, dict):
                results.append({"success": False, "error": "删除项目必须是对象"})
                failed_count += 1
                continue
            client_name = item.get("client_name")
            relative_path = item.get("relative_path")
            try:
                result = self.delete_file(client_name, relative_path)
                results.append(result)
                deleted_count += 1
            except Exception as e:
                results.append(
                    {
                        "success": False,
                        "client_name": client_name,
                        "relative_path": relative_path,
                        "error": str(e),
                    }
                )
                failed_count += 1
        return {
            "success": failed_count == 0,
            "total": len(files),
            "deleted": deleted_count,
            "failed": failed_count,
            "items": results,
        }
