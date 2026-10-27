"""文件操作错误到 HTTP 状态的统一转换。"""

from fastapi import HTTPException

from .file_access import FileAccessError


def file_http_error(error):
    if isinstance(error, FileAccessError):
        return HTTPException(error.status_code, str(error))
    if isinstance(error, FileNotFoundError):
        return HTTPException(404, "文件或目录已不存在，请刷新列表")
    if isinstance(error, PermissionError):
        return HTTPException(403, "没有权限操作该文件或目录")
    if isinstance(error, ValueError):
        return HTTPException(400, str(error))
    return HTTPException(500, "文件操作失败，请检查目录权限后重试")
