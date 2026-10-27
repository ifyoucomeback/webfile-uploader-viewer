"""存储路径校验与构造。"""

import os


class StoragePaths:
    """存储路径校验与构造。"""

    def __init__(self, upload_directory):
        self.upload_directory = os.path.abspath(upload_directory)

    def _safe_absolute_path(self, absolute_path):
        if not isinstance(absolute_path, str):
            raise ValueError("relative_path 必须是字符串")
        absolute_path = absolute_path.strip()
        if not absolute_path:
            raise ValueError("relative_path 不能为空")
        if "\x00" in absolute_path:
            raise ValueError("relative_path 包含非法字符")
        absolute_path = absolute_path.replace("\\", "/")
        if not absolute_path.startswith("/"):
            raise ValueError("relative_path 必须是绝对路径")
        parts = absolute_path.split("/")
        safe_parts = []
        for part in parts:
            if not part:
                continue
            if part in (".", ".."):
                raise ValueError("relative_path 包含非法路径")
            if "\x00" in part:
                raise ValueError("relative_path 包含非法字符")
            safe_parts.append(part)
        if not safe_parts:
            raise ValueError("relative_path 无效")
        return safe_parts

    def _safe_client_name(self, client_name):
        if not client_name:
            raise ValueError("客户端名称不能为空")
        client_name = str(client_name).strip()
        if (
            client_name in (".", "..")
            or "/" in client_name
            or "\\" in client_name
            or "\x00" in client_name
        ):
            raise ValueError("客户端名称包含非法路径")
        return client_name

    def _build_storage_relative_path(self, absolute_path):
        parts = self._safe_absolute_path(absolute_path)
        if len(parts) == 1:
            return parts[0]
        file_name = parts[-1]
        directory_parts = parts[:-1]
        if len(directory_parts) == 1:
            return os.path.join(directory_parts[0], file_name)
        parent_directory = ".".join(directory_parts[:-1])
        last_directory = directory_parts[-1]
        return os.path.join(parent_directory, last_directory, file_name)

    def _build_target_path(self, client_name, absolute_path):
        client_name = self._safe_client_name(client_name)
        storage_relative_path = self._build_storage_relative_path(absolute_path)
        client_directory = os.path.abspath(
            os.path.join(self.upload_directory, client_name + ".")
        )
        if not client_directory.startswith(self.upload_directory + os.sep):
            raise ValueError("客户端目录非法")
        target_path = os.path.abspath(
            os.path.join(client_directory, storage_relative_path)
        )
        if not (
            target_path == client_directory
            or target_path.startswith(client_directory + os.sep)
        ):
            raise ValueError("目标路径非法")
        return (client_directory, target_path)

    def _build_metadata_path(self, client_directory, absolute_path):
        storage_relative_path = self._build_storage_relative_path(absolute_path)
        metadata_directory = os.path.abspath(
            os.path.join(client_directory, ".metadata")
        )
        metadata_path = os.path.abspath(
            os.path.join(metadata_directory, storage_relative_path + ".json")
        )
        if not (
            metadata_path == metadata_directory
            or metadata_path.startswith(metadata_directory + os.sep)
        ):
            raise ValueError("元数据路径非法")
        return metadata_path
