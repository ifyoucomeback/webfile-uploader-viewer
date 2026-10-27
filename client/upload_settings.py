"""上传并发配置的默认值和边界校验。"""

DEFAULT_CONCURRENT_UPLOADS = 1
MAX_CONCURRENT_UPLOADS = 5


def validate_concurrency(value):
    if type(value) is not int or not 1 <= value <= MAX_CONCURRENT_UPLOADS:
        raise ValueError("同时上传文件数必须是 1～5 的整数")
    return value
