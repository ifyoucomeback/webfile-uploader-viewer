"""应用服务装配；组件之间显式共享存储与运行状态。"""

from dataclasses import dataclass

from ..auth import AuthManager
from ..upload_manager import UploadManager
from .audit import AuditLogger
from .file_browser import ServerFileBrowser
from .maintenance import MaintenanceService
from .upload_coordinator import UploadCoordinator
from .upload_runtime import UploadRuntime


@dataclass
class ServerServices:
    config: dict
    uploads: UploadManager
    auth: AuthManager
    audit: AuditLogger
    runtime: UploadRuntime
    maintenance: MaintenanceService
    coordinator: UploadCoordinator
    file_browser: ServerFileBrowser

    @classmethod
    def build(cls, config):
        uploads = UploadManager(config)
        auth = AuthManager(config)
        runtime = UploadRuntime(config, uploads)
        return cls(
            config,
            uploads,
            auth,
            AuditLogger(uploads.upload_directory),
            runtime,
            MaintenanceService(auth, runtime),
            UploadCoordinator(uploads, runtime),
            ServerFileBrowser(uploads),
        )
