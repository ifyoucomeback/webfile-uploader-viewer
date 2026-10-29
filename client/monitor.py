import os
import queue
import threading

from watchdog.observers import Observer

from .directory_events import DirectoryEventHandler


class DirectoryMonitor:
    def __init__(
        self,
        directories=None,
        include_extensions=None,
        exclude_extensions=None,
        interval=60,
        directory=None,
    ):
        # --------------------------------------------------------
        # 兼容旧调用方式
        #
        # DirectoryMonitor(
        #     directory="/data/video"
        # )
        # --------------------------------------------------------
        if directories is None:
            if directory:
                directories = [directory]
            else:
                directories = []
        self.directories = self._normalize_directories(directories)
        self.include_extensions = self._normalize_extensions(include_extensions or [])
        self.exclude_extensions = self._normalize_extensions(exclude_extensions or [])
        self.interval = interval
        # watchdog Observer
        self.observer = None
        # 文件变化事件队列
        self.event_queue = queue.Queue()
        # 当前文件列表缓存
        #
        # key = 完整路径
        # value = file_info
        #
        self.files = {}
        # 防止 Observer 启停过程中发生并发问题
        self._lock = threading.Lock()

    @staticmethod
    def _normalize_directories(directories):
        result = []
        if not isinstance(directories, list):
            return result
        for directory in directories:
            if not isinstance(directory, str):
                continue
            directory = directory.strip()
            if not directory:
                continue
            if directory not in result:
                result.append(directory)
        return result

    @staticmethod
    def _normalize_extensions(extensions):
        result = set()
        for extension in extensions:
            if not isinstance(extension, str):
                continue
            extension = extension.strip().lower()
            if not extension:
                continue
            if not extension.startswith("."):
                extension = "." + extension
            result.add(extension)
        return result

    def update_config(
        self,
        directories=None,
        include_extensions=None,
        exclude_extensions=None,
        interval=60,
        directory=None,
    ):
        # --------------------------------------------------------
        # 兼容旧调用方式
        # --------------------------------------------------------
        if directories is None:
            if directory:
                directories = [directory]
            else:
                directories = []
        directories = self._normalize_directories(directories)
        old_directories = sorted(
            set(
                os.path.abspath(directory)
                for directory in self.directories
                if directory
            )
        )
        new_directories = sorted(
            set(os.path.abspath(directory) for directory in directories if directory)
        )
        old_include_extensions = self.include_extensions
        old_exclude_extensions = self.exclude_extensions
        new_include_extensions = self._normalize_extensions(include_extensions or [])
        new_exclude_extensions = self._normalize_extensions(exclude_extensions or [])
        directories_changed = old_directories != new_directories
        filters_changed = (
            old_include_extensions != new_include_extensions
            or old_exclude_extensions != new_exclude_extensions
        )
        self.include_extensions = new_include_extensions
        self.exclude_extensions = new_exclude_extensions
        self.interval = interval
        self.directories = directories
        # --------------------------------------------------------
        # 目录发生变化，需要重新建立监控
        # --------------------------------------------------------
        if directories_changed:
            self.stop()
            self.start()
            return
        # --------------------------------------------------------
        # 过滤条件变化时重新扫描缓存
        # --------------------------------------------------------
        if filters_changed:
            self._rebuild_file_cache()

    def is_valid_file(self, filename):
        extension = os.path.splitext(filename)[1].lower()
        # 排除规则优先
        if extension in self.exclude_extensions:
            return False
        # 如果配置了包含列表，
        # 只允许包含列表中的扩展名
        if self.include_extensions:
            return extension in self.include_extensions
        # 没有包含列表时，
        # 允许所有非排除扩展名
        return True

    def _get_root_directory(self, file_path):
        """
        判断文件属于哪个监控根目录。

        返回绝对路径。
        """
        file_path = os.path.abspath(file_path)
        for directory in self.directories:
            root = os.path.abspath(directory)
            try:
                common_path = os.path.commonpath([file_path, root])
            except ValueError:
                continue
            if common_path == root:
                return root
        return None

    def _build_file_info(self, file_path):
        if not self.directories:
            return None
        file_path = os.path.abspath(file_path)
        if not os.path.isfile(file_path):
            return None
        if not self.is_valid_file(os.path.basename(file_path)):
            return None
        try:
            stat = os.stat(file_path)
        except OSError:
            return None
        monitor_directory = self._get_root_directory(file_path)
        if monitor_directory is None:
            return None
        try:
            relative_path = os.path.relpath(file_path, monitor_directory)
        except ValueError:
            return None
        relative_path = relative_path.replace(os.sep, "/")
        return {
            "path": file_path,
            "name": os.path.basename(file_path),
            "relative_path": relative_path,
            "root_directory": monitor_directory,
            "size": stat.st_size,
            "extension": os.path.splitext(os.path.basename(file_path))[1].lower(),
            "mtime": stat.st_mtime,
        }

    def _handle_file_event(self, file_path):
        file_info = self._build_file_info(file_path)
        if file_info is None:
            return
        file_path = file_info["path"]
        with self._lock:
            self.files[file_path] = file_info
        # 通知上传任务有文件发生变化
        self.event_queue.put(file_info)

    def _handle_file_deleted(self, file_path):
        file_path = os.path.abspath(file_path)
        with self._lock:
            self.files.pop(file_path, None)

    def _rebuild_file_cache(self):
        files = self._scan_files()
        with self._lock:
            self.files = {file_info["path"]: file_info for file_info in files}

    def _scan_files(self):
        if not self.directories:
            return []
        files = []
        # --------------------------------------------------------
        # 依次扫描所有监控目录
        # --------------------------------------------------------
        for monitor_directory in self.directories:
            if not os.path.isdir(monitor_directory):
                continue
            monitor_directory = os.path.abspath(monitor_directory)
            for root, _, filenames in os.walk(monitor_directory):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    file_info = self._build_file_info(full_path)
                    if file_info is not None:
                        files.append(file_info)
        return files

    def scan(self):
        """
        返回当前内存中的完整文件列表。

        注意：
        这里返回的是完整列表。

        网页分页在 app.py 的 API 层实现，
        不影响上传队列。
        """
        with self._lock:
            return list(self.files.values())

    def rescan(self):
        """重新读取磁盘，供启动补偿和手动全量扫描使用。"""
        self._rebuild_file_cache()
        return self.scan()

    def get_changed_files(self):
        """
        获取已经发生变化的文件。

        一次性取出当前队列中的所有变化，
        并按照文件路径去重。
        """
        changed = {}
        while True:
            try:
                file_info = self.event_queue.get_nowait()
            except queue.Empty:
                break
            changed[file_info["path"]] = file_info
        return list(changed.values())

    def start(self):
        """
        启动文件系统监控。
        """
        self.stop()
        # 先进行一次初始扫描
        self._rebuild_file_cache()
        if not self.directories:
            return
        handler = DirectoryEventHandler(self)
        observer = Observer()
        scheduled = False
        # --------------------------------------------------------
        # 为每个目录建立一个 recursive watch
        # --------------------------------------------------------
        for directory in self.directories:
            if not os.path.isdir(directory):
                continue
            observer.schedule(handler, os.path.abspath(directory), recursive=True)
            scheduled = True
        if not scheduled:
            return
        observer.start()
        self.observer = observer

    def stop(self):
        """
        停止文件系统监控。
        """
        observer = self.observer
        if observer is None:
            return
        try:
            observer.stop()
            observer.join()
        except Exception:
            pass
        finally:
            self.observer = None

    def get_interval(self):
        return self.interval
