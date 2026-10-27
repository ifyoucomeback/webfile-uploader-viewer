"""按客户端隔离的服务器实际存储目录浏览，关联上传元数据。"""

import json
from pathlib import Path

from shared.directory_listing import is_internal_name, list_directory
from shared.file_access import (
    FileAccessError,
    canonical_path,
    relative_parts,
    resolve_inside,
)


class ServerFileBrowser:
    def __init__(self, uploads):
        self.uploads = uploads

    def client_roots(self):
        base = Path(self.uploads.upload_directory)
        clients = {}
        if not base.is_dir():
            return clients
        for entry in base.iterdir():
            if entry.name.startswith(".") or not entry.is_dir() or entry.is_symlink():
                continue
            name = entry.name[:-1] if entry.name.endswith(".") else entry.name
            if not name:
                continue
            try:
                root = resolve_inside(base, entry.name)
            except FileAccessError:
                continue
            if name not in clients or entry.name.endswith("."):
                clients[name] = root
        return clients

    def clients(self):
        return [
            {"client_name": name, "storage_root": str(root)}
            for name, root in sorted(
                self.client_roots().items(), key=lambda item: item[0].casefold()
            )
        ]

    def root_path(self, client_name):
        if not isinstance(client_name, str):
            raise FileAccessError(400, "客户端名称必须是字符串")
        self.uploads.paths._safe_client_name(client_name)
        root = self.client_roots().get(client_name)
        if root is None:
            raise FileAccessError(404, "客户端存储目录不存在")
        return root

    def _safe_path(self, path):
        parts = relative_parts(path)
        if any(is_internal_name(part.casefold()) for part in parts):
            raise FileAccessError(403, "不能访问内部元数据、备份或暂存目录")
        return "/".join(parts)

    def resolve_file(self, client_name, path):
        return resolve_inside(
            self.root_path(client_name), self._safe_path(path), file_only=True
        )

    def _metadata(self, root, client_name, path):
        try:
            metadata_path = resolve_inside(
                root, ".metadata/" + path + ".json", file_only=True
            )
            if metadata_path.stat().st_size > 1024 * 1024:
                return {}
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(metadata, dict) or not isinstance(
                metadata.get("relative_path"), str
            ):
                return {}
            _, expected = self.uploads.paths._build_target_path(
                client_name, metadata["relative_path"]
            )
            if canonical_path(expected) != canonical_path(root / path):
                return {}
            return metadata
        except (OSError, ValueError):
            return {}

    def browse(self, client_name, path="", page=1, page_size=50, keyword=""):
        root = self.root_path(client_name)
        path = self._safe_path(path)
        result = list_directory(
            root, path, page, page_size, keyword, hide_internal=True
        )
        result.update(client_name=client_name, storage_root=str(root))
        for item in result["items"]:
            item["stored_path"] = str(root / item["path"])
            if item["kind"] == "file":
                metadata = self._metadata(root, client_name, item["path"])
                item["original_path"] = metadata.get("relative_path")
        return result

    def delete_file(self, client_name, path):
        root = self.root_path(client_name)
        target = self.resolve_file(client_name, path)
        lock = self.uploads.target_locks.get(str(target))
        with lock:
            if self.uploads.tasks.has_pending_target(target):
                raise FileAccessError(409, "该文件有未完成上传任务，暂不能删除")
            metadata = self._metadata(root, client_name, self._safe_path(path))
            if metadata:
                return self.uploads.files.delete_file(
                    client_name, metadata["relative_path"]
                )
            # 无元数据的实际文件仍可管理，不向旧索引伪造原始路径。
            metadata_file = None
            try:
                metadata_file = resolve_inside(
                    root, ".metadata/" + self._safe_path(path) + ".json", file_only=True
                )
            except FileAccessError as exc:
                if exc.status_code != 404:
                    raise
            target.unlink()
            if metadata_file is not None:
                metadata_file.unlink()
            return {
                "success": True,
                "client_name": client_name,
                "path": path,
                "target_path": str(target),
                "deleted_file": True,
                "deleted_metadata": metadata_file is not None,
            }
