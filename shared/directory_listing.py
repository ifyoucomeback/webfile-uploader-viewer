"""只枚举当前目录，文件夹优先排序，并对结果分页。"""

import os
import re
from pathlib import Path

from .file_access import FileAccessError, relative_parts, resolve_inside
from .file_preview import preview_kind

INTERNAL_NAMES = {".metadata", ".audit", ".uploading"}


def is_internal_name(name):
    name = name.casefold()
    return (
        name in INTERNAL_NAMES
        or re.search(r"\.replace\.[0-9a-f]{32}\.bak$", name) is not None
    )


def list_directory(
    root, path="", page=1, page_size=50, keyword="", hide_internal=False
):
    parts = relative_parts(path)
    directory = resolve_inside(root, path)
    if not directory.is_dir():
        raise FileAccessError(400, "请选择一个目录")
    entries = []
    with os.scandir(directory) as scan:
        for entry in scan:
            if entry.is_symlink() or (hide_internal and is_internal_name(entry.name)):
                continue
            if keyword and keyword.casefold() not in entry.name.casefold():
                continue
            try:
                if getattr(Path(entry.path), "is_junction", lambda: False)():
                    continue
                is_directory = entry.is_dir(follow_symlinks=False)
                if not is_directory and not entry.is_file(follow_symlinks=False):
                    continue
                stat = entry.stat(follow_symlinks=False)
            except (FileNotFoundError, PermissionError, OSError):
                continue
            entries.append(
                {
                    "name": entry.name,
                    "kind": "directory" if is_directory else "file",
                    "path": "/".join(parts + [entry.name]),
                    "size": None if is_directory else stat.st_size,
                    "modified_time": stat.st_mtime,
                    "preview_kind": (
                        "none" if is_directory else preview_kind(entry.name)
                    ),
                }
            )
    entries.sort(
        key=lambda item: (
            item["kind"] != "directory",
            item["name"].casefold(),
            item["name"],
        )
    )
    page_size = min(200, max(1, page_size))
    total_pages = (len(entries) + page_size - 1) // page_size
    page = min(max(1, page), total_pages or 1)
    return {
        "success": True,
        "path": "/".join(parts),
        "absolute_path": str(directory),
        "parent_path": "/".join(parts[:-1]) if parts else None,
        "page": page,
        "page_size": page_size,
        "total": len(entries),
        "total_pages": total_pages,
        "items": entries[(page - 1) * page_size : page * page_size],
    }
