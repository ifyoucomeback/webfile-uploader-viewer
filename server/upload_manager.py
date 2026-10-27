"""上传服务的兼容入口；具体职责由独立组件承担。"""

import os

from .services.client_resolver import ClientResolver
from .services.storage_summary import StorageSummary
from .storage.checksums import calculate_file_sha256, validate_sha256
from .storage.file_repository import FileRepository
from .storage.locks import StorageLocks
from .storage.paths import StoragePaths
from .storage.upload_commit import UploadCommitter
from .storage.upload_store import UploadStore


class UploadManager:
    """上传服务的兼容入口；具体职责由独立组件承担。"""

    def __init__(self, config):
        self.config = config
        self.paths = StoragePaths(config["storage"]["upload_directory"])
        self.upload_directory = self.paths.upload_directory
        self.uploading_directory = os.path.abspath(
            config["storage"]["uploading_directory"]
        )
        self.resolver = ClientResolver(config)
        self.upload_locks = StorageLocks()
        self.target_locks = StorageLocks(normalize_paths=True)
        self.files = FileRepository(self.paths, self.target_locks)
        self.tasks = UploadStore(
            config, self.paths, self.resolver, self.upload_locks, self.target_locks
        )
        self.files.has_pending_upload = self.tasks.has_pending_target
        self.committer = UploadCommitter(
            self.tasks, self.files, self.paths, self.upload_locks, self.target_locks
        )
        self.summary = StorageSummary(self.files, self.tasks)

    def _safe_absolute_path(self, absolute_path):
        return self.paths._safe_absolute_path(absolute_path)

    def _safe_client_name(self, client_name):
        return self.paths._safe_client_name(client_name)

    def _build_storage_relative_path(self, absolute_path):
        return self.paths._build_storage_relative_path(absolute_path)

    def _build_target_path(self, client_name, absolute_path):
        return self.paths._build_target_path(client_name, absolute_path)

    def _build_metadata_path(self, client_directory, absolute_path):
        return self.paths._build_metadata_path(client_directory, absolute_path)

    def _write_file_metadata(self, metadata):
        return self.files._write_file_metadata(metadata)

    def list_files(self):
        return self.files.list_files()

    def delete_file(self, client_name, relative_path):
        return self.files.delete_file(client_name, relative_path)

    def delete_files(self, files):
        return self.files.delete_files(files)

    def is_upload_expired(self, metadata):
        return self.tasks.is_upload_expired(metadata)

    def _remove_upload_directory(self, upload_id, upload_directory):
        return self.tasks._remove_upload_directory(upload_id, upload_directory)

    def cancel_upload(self, upload_id):
        return self.tasks.cancel_upload(upload_id)

    def cleanup_expired_upload(self, upload_id):
        return self.tasks.cleanup_expired_upload(upload_id)

    def check_disk_space(self, file_size):
        return self.tasks.check_disk_space(file_size)

    def init_upload(
        self,
        client_ip,
        file_name,
        relative_path,
        file_size,
        file_extension,
        upload_time,
        sha256,
    ):
        return self.tasks.init_upload(
            client_ip,
            file_name,
            relative_path,
            file_size,
            file_extension,
            upload_time,
            sha256,
        )

    def list_uploads(self):
        return self.tasks.list_uploads()

    def _load_metadata(self, upload_id):
        return self.tasks._load_metadata(upload_id)

    def get_upload_status(self, upload_id):
        return self.tasks.get_upload_status(upload_id)

    def save_chunk(self, upload_id, chunk_index, chunk_offset, chunk_data):
        return self.tasks.save_chunk(upload_id, chunk_index, chunk_offset, chunk_data)

    def complete_upload(self, upload_id):
        return self.committer.complete_upload(upload_id)

    def list_clients(self):
        return self.summary.list_clients()

    def get_storage_info(self):
        return self.summary.get_storage_info()

    def reverse_dns(self, ip):
        return self.resolver.reverse_dns(ip)

    def get_client_name(self, client_ip):
        return self.resolver.get_client_name(client_ip)

    validate_sha256 = staticmethod(validate_sha256)
    calculate_file_sha256 = staticmethod(calculate_file_sha256)

    def _get_upload_lock(self, upload_id):
        return self.upload_locks.get(upload_id)

    def _get_target_lock(self, target_path):
        return self.target_locks.get(target_path)
