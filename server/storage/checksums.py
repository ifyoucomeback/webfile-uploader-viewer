"""文件与分片校验。"""

import hashlib


def validate_sha256(sha256):
    if not isinstance(sha256, str):
        raise ValueError("sha256 必须是字符串")
    sha256 = sha256.strip().lower()
    if len(sha256) != 64:
        raise ValueError("sha256 必须是 64 位十六进制字符串")
    if any(c not in "0123456789abcdef" for c in sha256):
        raise ValueError("sha256 必须是十六进制字符串")
    return sha256


def calculate_file_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(1024 * 1024)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()
