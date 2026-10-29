"""分片上传、断点恢复和上传完成协议。"""

import asyncio
import hashlib
import os
import time
from functools import partial

import aiohttp

from .errors import UploadBusyError, UploadError


class UploadProtocol:
    """分片上传、断点恢复和上传完成协议。"""

    def __init__(self, uploader, progress):
        self.uploader = uploader
        self.progress = progress

    def _calculate_file_sha256(self, file_path):
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as file:
                while True:
                    data = file.read(1024 * 1024)
                    if not data:
                        break
                    sha256.update(data)
        except OSError as e:
            raise UploadError(f"计算文件 SHA-256 失败: {file_path}, {e}")
        return sha256.hexdigest()

    def _normalize_uploaded_chunks(self, value, total_chunks):
        """
        兼容服务端不同版本的 uploaded_chunks 返回格式。

        支持：

            [0, 1, 2, 3]

        以及：

            4

        当服务端返回整数 4 时，
        表示前 4 个分片已经完成，
        即：

            [0, 1, 2, 3]

        最终统一返回 set[int]。
        """
        if value is None:
            return set()
        # ----------------------------------------------------
        # 服务端返回：
        #
        # uploaded_chunks = 4
        # ----------------------------------------------------
        if isinstance(value, int):
            count = max(0, min(value, total_chunks))
            return set(range(count))
        # ----------------------------------------------------
        # 服务端返回：
        #
        # uploaded_chunks = [0, 1, 2, 3]
        # ----------------------------------------------------
        if isinstance(value, (list, tuple, set)):
            result = set()
            for item in value:
                try:
                    chunk_index = int(item)
                except (TypeError, ValueError):
                    continue
                if 0 <= chunk_index < total_chunks:
                    result.add(chunk_index)
            return result
        return set()

    async def _upload_file(self, file_info):
        file_path = file_info["path"]
        if not os.path.isfile(file_path):
            raise UploadError(f"文件不存在: {file_path}")
        file_size = os.path.getsize(file_path)
        if file_size != file_info["size"]:
            raise UploadError(f"文件大小发生变化: {file_path}")
        file_name = file_info["name"]
        # ----------------------------------------------------
        # 服务端目前保存的是文件绝对路径。
        #
        # 不使用 monitor.py 的 relative_path，
        # 因为那个字段是相对于监控根目录的路径。
        # ----------------------------------------------------
        relative_path = os.path.abspath(file_path)
        extension = file_info["extension"]
        print(f"[SHA256] 开始计算: {file_path}")
        loop = asyncio.get_running_loop()
        file_sha256 = await loop.run_in_executor(
            None, partial(self._calculate_file_sha256, file_path)
        )
        current_file_size = os.path.getsize(file_path)
        if current_file_size != file_size:
            raise UploadError(f"计算 SHA-256 后文件大小发生变化: {file_path}")
        self.progress.sha256 = file_sha256
        self.progress.stage = "uploading"
        print(f"[SHA256] 计算完成: {file_sha256}")
        upload_time = int(time.time())
        init_data = {
            "client_ip": self.uploader.client_info["ip"],
            "client_name": self.uploader.client_info["name"],
            "file_name": file_name,
            "relative_path": relative_path,
            "file_size": file_size,
            "file_extension": extension,
            "upload_time": upload_time,
            "sha256": file_sha256,
        }
        try:
            async with self.uploader._session.post(
                f"{self.uploader.base_url}/api/upload/init",
                json=init_data,
                headers=self.uploader.connection._get_upload_headers(),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    self.uploader.connection._set_server_connected()
                    raise UploadError(f"初始化上传失败: {response.status} {text}")
                result = await response.json()
                self.uploader.connection._set_server_connected()
        except UploadError:
            raise
        except Exception as e:
            self.uploader.connection._set_server_disconnected(e)
            raise UploadError(f"连接服务端失败: {e}")
        chunk_size = int(result.get("chunk_size", self.uploader.chunk_size))
        if chunk_size <= 0:
            raise UploadError("服务端返回无效的分片大小")
        status = result.get("status")
        if status == "exists":
            self.progress.update(file_size, transferred=False)
            return {
                "success": True,
                "status": "exists",
                "file": file_path,
                "size": file_size,
                "sha256": file_sha256,
            }
        if status == "busy":
            server_file_name = result.get("file_name")
            server_relative_path = result.get("relative_path")
            server_file_size = result.get("file_size")
            server_sha256 = str(result.get("sha256", "")).lower()
            same_file = (
                server_file_name == file_name
                and os.path.abspath(str(server_relative_path or ""))
                == os.path.abspath(relative_path)
                and int(server_file_size if server_file_size is not None else -1)
                == int(file_size)
                and server_sha256 == file_sha256.lower()
            )
            if same_file:
                print(f"[RESUME] 发现服务端断点任务，继续上传: {file_path}")
                upload_id = result.get("upload_id")
                if not upload_id:
                    raise UploadError("服务端断点任务没有返回 " "upload_id")
                total_chunks = (file_size + chunk_size - 1) // chunk_size
                uploaded_chunks = self._normalize_uploaded_chunks(
                    result.get("uploaded_chunks", []), total_chunks
                )
                print(
                    f"[RESUME] upload_id={upload_id}, 已完成分片={sorted(uploaded_chunks)}"
                )
            else:
                raise UploadBusyError(result)
        else:
            if status not in ("new", "uploading"):
                raise UploadError(
                    result.get("error") or f"服务端返回未知状态: {status}"
                )
            upload_id = result.get("upload_id")
            if not upload_id:
                raise UploadError("服务端没有返回 upload_id")
            total_chunks = (file_size + chunk_size - 1) // chunk_size
            uploaded_chunks = self._normalize_uploaded_chunks(
                result.get("uploaded_chunks", []), total_chunks
            )
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        uploaded_bytes = 0
        with open(file_path, "rb") as file:
            for chunk_index in range(total_chunks):
                chunk_offset = chunk_index * chunk_size
                actual_chunk_size = min(chunk_size, file_size - chunk_offset)
                if chunk_index in uploaded_chunks:
                    file.seek(actual_chunk_size, os.SEEK_CUR)
                    uploaded_bytes += actual_chunk_size
                    self.progress.update(uploaded_bytes, transferred=False)
                    continue
                chunk_data = file.read(actual_chunk_size)
                if len(chunk_data) != actual_chunk_size:
                    raise UploadError(f"读取文件失败: {file_path}")
                await self._upload_chunk(
                    upload_id=upload_id,
                    chunk_index=chunk_index,
                    chunk_offset=chunk_offset,
                    chunk_data=chunk_data,
                )
                uploaded_bytes += actual_chunk_size
                self.progress.update(uploaded_bytes)
        final_file_size = os.path.getsize(file_path)
        if final_file_size != file_size:
            raise UploadError(f"上传过程中文件大小发生变化: {file_path}")
        self.progress.stage = "completing"
        self.progress.speed = 0
        await self._complete_upload(upload_id=upload_id, file_info=file_info)
        return {
            "success": True,
            "status": "uploaded",
            "file": file_path,
            "size": file_size,
            "sha256": file_sha256,
        }

    async def _upload_chunk(self, upload_id, chunk_index, chunk_offset, chunk_data):
        form = aiohttp.FormData()
        form.add_field("upload_id", str(upload_id))
        form.add_field("chunk_index", str(chunk_index))
        form.add_field("chunk_offset", str(chunk_offset))
        form.add_field(
            "chunk",
            self.uploader.iter_upload_data(chunk_data),
            filename=f"chunk_{chunk_index}",
            content_type="application/octet-stream",
        )
        try:
            async with self.uploader._session.post(
                f"{self.uploader.base_url}/api/upload/chunk",
                data=form,
                headers=self.uploader.connection._get_upload_headers(),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    self.uploader.connection._set_server_connected()
                    raise UploadError(
                        f"分片上传失败: chunk={chunk_index}, status={response.status}, {text}"
                    )
                result = await response.json()
                self.uploader.connection._set_server_connected()
        except UploadError:
            raise
        except Exception as e:
            self.uploader.connection._set_server_disconnected(e)
            raise UploadError(f"分片上传连接失败: chunk={chunk_index}, {e}")
        if not result.get("success", False):
            raise UploadError(f"服务端拒绝分片: chunk={chunk_index}")

    async def _complete_upload(self, upload_id, file_info):
        data = {
            "upload_id": upload_id,
            "file_name": file_info["name"],
            "relative_path": os.path.abspath(file_info["path"]),
            "file_size": file_info["size"],
            "file_extension": file_info["extension"],
        }
        try:
            async with self.uploader._session.post(
                f"{self.uploader.base_url}/api/upload/complete",
                json=data,
                headers=self.uploader.connection._get_upload_headers(),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    self.uploader.connection._set_server_connected()
                    raise UploadError(f"完成上传失败: {response.status} {text}")
                result = await response.json()
                self.uploader.connection._set_server_connected()
        except UploadError:
            raise
        except Exception as e:
            self.uploader.connection._set_server_disconnected(e)
            raise UploadError(f"完成上传连接失败: {e}")
        if not result.get("success", False):
            if result.get("status") == "sha256_mismatch":
                raise UploadError(
                    f"服务端 SHA-256 校验失败: client={result.get('client_sha256')}, server={result.get('server_sha256')}"
                )
            raise UploadError(f"服务端没有确认上传完成: {result}")
