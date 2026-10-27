"""判断请求是否对应当前上传或同一存储目标。"""


def is_same_upload(upload_status, file_name, relative_path, file_size, sha256):
    try:
        requested_file_size = int(file_size)
    except Exception:
        return False
    saved_sha256 = str(upload_status.get("sha256", "")).lower()
    requested_sha256 = str(sha256 or "").strip().lower()
    return (
        upload_status["file_name"] == file_name
        and upload_status["relative_path"] == relative_path
        and int(upload_status["file_size"]) == requested_file_size
        and saved_sha256 == requested_sha256
    )


def is_same_target(upload_status, client_name, relative_path):
    if not isinstance(upload_status, dict):
        return False
    return (
        upload_status.get("client_name") == client_name
        and upload_status.get("relative_path") == relative_path
    )
