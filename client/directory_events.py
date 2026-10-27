"""文件系统事件到目录缓存的适配。"""

from watchdog.events import FileSystemEventHandler


class DirectoryEventHandler(FileSystemEventHandler):
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor

    def on_created(self, event):
        if event.is_directory:
            return
        self.monitor._handle_file_event(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self.monitor._handle_file_event(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        # 原文件删除
        self.monitor._handle_file_deleted(event.src_path)
        # 新文件出现
        self.monitor._handle_file_event(event.dest_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        self.monitor._handle_file_deleted(event.src_path)
