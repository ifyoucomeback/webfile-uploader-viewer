"""限定根目录内的文件访问和相对路径校验。"""

import ntpath
import os
from pathlib import Path


class FileAccessError(ValueError):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


def canonical_path(path):
    return os.path.normcase(os.path.realpath(path))


def relative_parts(path):
    if not isinstance(path, str) or "\x00" in path:
        raise FileAccessError(400, "文件路径格式错误")
    path = path.replace("\\", "/")
    if path.startswith("/") or ntpath.splitdrive(path)[0]:
        raise FileAccessError(400, "请使用根目录内的相对路径")
    parts = [part for part in path.split("/") if part]
    if any(part in (".", "..") for part in parts):
        raise FileAccessError(400, "路径不能包含 . 或 ..")
    if os.name == "nt" and any(
        part.endswith((".", " ")) or ":" in part for part in parts
    ):
        raise FileAccessError(400, "路径包含 Windows 不支持的名称或数据流")
    return parts


def resolve_inside(root, path="", file_only=False):
    try:
        base = Path(root).resolve(strict=True)
        if not base.is_dir():
            raise FileAccessError(404, "根目录不存在")
        candidate = base
        for part in relative_parts(path):
            candidate = candidate / part
            if (
                candidate.is_symlink()
                or getattr(candidate, "is_junction", lambda: False)()
            ):
                raise FileAccessError(403, "不能通过符号链接访问文件")
        target = candidate.resolve(strict=True)
        if os.path.commonpath(
            [canonical_path(base), canonical_path(target)]
        ) != canonical_path(base):
            raise FileAccessError(403, "文件超出允许访问的目录")
        if file_only and not target.is_file():
            raise FileAccessError(400, "请选择一个普通文件")
        return target
    except FileNotFoundError as exc:
        raise FileAccessError(404, "文件或目录已不存在，请刷新列表") from exc
    except PermissionError as exc:
        raise FileAccessError(403, "没有权限访问该文件或目录") from exc
    except (OSError, RuntimeError) as exc:
        raise FileAccessError(400, "文件路径无效或暂时无法访问") from exc
