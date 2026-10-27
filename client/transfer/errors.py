"""上传协议异常。"""


class UploadError(Exception):
    pass


class UploadBusyError(UploadError):
    def __init__(self, upload_info):
        self.upload_info = upload_info
        message = upload_info.get("message", "服务端当前正在上传其他文件")
        super().__init__(message)
