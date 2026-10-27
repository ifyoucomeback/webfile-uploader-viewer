"""HTTP 会话、连接健康检查与远端文件查询。"""

import asyncio
import time

import aiohttp

from .errors import UploadError


class UploadConnection:
    """HTTP 会话、连接健康检查与远端文件查询。"""

    def __init__(self, uploader):
        self.uploader = uploader
        self._start_lock = asyncio.Lock()

    async def start(self):
        async with self._start_lock:
            if self.uploader._session is not None:
                return
            timeout = aiohttp.ClientTimeout(
                total=None, connect=5, sock_connect=5, sock_read=60
            )
            self.uploader._session = aiohttp.ClientSession(timeout=timeout)
            self.uploader.health_check_running = True
            self.uploader.health_check_task = asyncio.create_task(
                self._health_check_loop()
            )

    async def close(self):
        self.uploader.health_check_running = False
        if self.uploader.health_check_task is not None:
            self.uploader.health_check_task.cancel()
            try:
                await self.uploader.health_check_task
            except asyncio.CancelledError:
                pass
            self.uploader.health_check_task = None
        if self.uploader._session is not None:
            await self.uploader._session.close()
            self.uploader._session = None

    async def _health_check_loop(self):
        while self.uploader.health_check_running:
            try:
                await self._check_server_connection()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._set_server_disconnected(e)
            try:
                await asyncio.sleep(self.uploader.health_check_interval)
            except asyncio.CancelledError:
                break

    async def _check_server_connection(self):
        if self.uploader._session is None:
            self._set_server_disconnected("HTTP session 未启动")
            return
        try:
            async with self.uploader._session.get(
                f"{self.uploader.base_url}/api/health"
            ) as response:
                if response.status != 200:
                    self._set_server_disconnected(f"HTTP {response.status}")
                    return
                try:
                    result = await response.json()
                except Exception:
                    self._set_server_disconnected("服务端返回的不是有效 JSON")
                    return
                if result.get("success", False):
                    self._set_server_connected()
                else:
                    self._set_server_disconnected("服务端 health 检查失败")
        except Exception as e:
            self._set_server_disconnected(e)

    def _set_server_connected(self):
        self.uploader.server_connected = True
        self.uploader.last_server_success_time = time.time()
        self.uploader.last_server_error = None

    def _set_server_disconnected(self, error):
        self.uploader.server_connected = False
        self.uploader.last_server_error = str(error)

    def _get_upload_headers(self):
        if not self.uploader.upload_psk:
            raise UploadError("未配置上传认证 PSK")
        return {"X-Upload-PSK": self.uploader.upload_psk}

    async def get_server_files(self):
        if self.uploader._session is None:
            await self.start()
        try:
            async with self.uploader._session.get(
                f"{self.uploader.base_url}/api/upload/files",
                headers=self._get_upload_headers(),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    self._set_server_disconnected(
                        RuntimeError(f"HTTP {response.status}: {text}")
                    )
                    raise UploadError(
                        f"获取服务端文件列表失败: {response.status} {text}"
                    )
                result = await response.json()
                self._set_server_connected()
        except UploadError:
            raise
        except Exception as e:
            self._set_server_disconnected(e)
            raise UploadError(f"获取服务端文件列表连接失败: {e}")
        if not result.get("success", False):
            raise UploadError(f"服务端文件列表请求失败: {result}")
        return result.get("files", [])
