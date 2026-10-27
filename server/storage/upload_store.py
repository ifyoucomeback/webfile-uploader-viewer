"""未完成上传任务、分片持久化及过期清理。"""

import hashlib
import json
import os
import shutil
import time
import uuid

from shared.file_access import canonical_path

from .checksums import calculate_file_sha256, validate_sha256


class UploadStore:
    """未完成上传任务、分片持久化及过期清理。"""

    def __init__(self, config, paths, resolver, upload_locks, target_locks):
        self.paths = paths
        self.resolver = resolver
        self.upload_locks = upload_locks
        self.target_locks = target_locks
        self.upload_directory = paths.upload_directory
        self.uploading_directory = os.path.abspath(
            config["storage"]["uploading_directory"]
        )
        self.chunk_size = int(config["upload"]["chunk_size"])
        self.max_file_size = int(config["upload"]["max_file_size"])
        self.incomplete_expire_days = int(config["upload"]["incomplete_expire_days"])
        self.min_free_space = int(config["upload"]["min_free_space"])
        os.makedirs(self.upload_directory, exist_ok=True)
        os.makedirs(self.uploading_directory, exist_ok=True)

    def is_upload_expired(self, metadata):
        expire_days = self.incomplete_expire_days
        if expire_days <= 0:
            return False
        updated_time = int(
            metadata.get("updated_time", metadata.get("created_time", 0))
        )
        if updated_time <= 0:
            return False
        expire_seconds = expire_days * 24 * 60 * 60
        return time.time() - updated_time > expire_seconds

    def has_pending_target(self, target_path):
        target = canonical_path(target_path)
        return any(
            not item.get("expired")
            and canonical_path(item.get("target_path", "")) == target
            for item in self.list_uploads()
        )

    def _remove_upload_directory(self, upload_id, upload_directory):
        if not upload_id:
            return False
        upload_id = str(upload_id)
        if len(upload_id) != 32 or any(
            c not in "0123456789abcdef" for c in upload_id.lower()
        ):
            print("[UPLOAD] " f"拒绝删除非法 upload_id: {upload_id}")
            return False
        upload_directory = os.path.abspath(upload_directory)
        uploading_directory = os.path.abspath(self.uploading_directory)
        if not upload_directory.startswith(uploading_directory + os.sep):
            print("[UPLOAD] " f"拒绝删除非法上传目录: " f"{upload_directory}")
            return False
        if os.path.basename(upload_directory) != upload_id:
            print("[UPLOAD] " f"拒绝删除非目标上传目录: " f"{upload_directory}")
            return False
        if not os.path.isdir(upload_directory):
            return True
        try:
            shutil.rmtree(upload_directory)
        except OSError as e:
            print(
                "[UPLOAD] "
                f"删除上传任务目录失败: "
                f"upload_id={upload_id}, "
                f"directory={upload_directory}, "
                f"错误: {e}"
            )
            return False
        return True

    def cancel_upload(self, upload_id):
        lock = self.upload_locks.get(upload_id)
        with lock:
            try:
                metadata, upload_directory = self._load_metadata(upload_id)
            except Exception as e:
                print(
                    "[UPLOAD] "
                    f"取消上传任务失败，"
                    f"读取任务失败: "
                    f"{upload_id}, 错误: {e}"
                )
                return False
            print(
                "[UPLOAD] "
                f"取消旧上传任务: "
                f"upload_id={upload_id}, "
                f"client={metadata.get('client_name', '')}, "
                f"relative_path="
                f"{metadata.get('relative_path', '')}"
            )
            return self._remove_upload_directory(upload_id, upload_directory)

    def cleanup_expired_upload(self, upload_id):
        lock = self.upload_locks.get(upload_id)
        with lock:
            try:
                metadata, upload_directory = self._load_metadata(upload_id)
            except Exception as e:
                print("[EXPIRE] " f"读取过期上传任务失败: " f"{upload_id}, 错误: {e}")
                return False
            if not self.is_upload_expired(metadata):
                return False
            print(
                "[EXPIRE] "
                f"清理过期上传任务: "
                f"upload_id={upload_id}, "
                f"directory={upload_directory}"
            )
            success = self._remove_upload_directory(upload_id, upload_directory)
            if not success:
                print("[EXPIRE] " f"过期上传任务清理失败: " f"upload_id={upload_id}")
                return False
            print("[EXPIRE] " f"过期上传任务清理完成: " f"upload_id={upload_id}")
            return True

    def check_disk_space(self, file_size):
        try:
            file_size = int(file_size)
        except Exception:
            raise ValueError("file_size 必须是整数")
        disk_usage = shutil.disk_usage(self.upload_directory)
        required_space = file_size + self.min_free_space
        if disk_usage.free < required_space:
            free_gib = disk_usage.free / 1024 / 1024 / 1024
            required_gib = required_space / 1024 / 1024 / 1024
            raise ValueError(
                "服务端磁盘空间不足: "
                f"可用空间={free_gib:.2f} GiB, "
                f"需要至少={required_gib:.2f} GiB"
            )

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
        if not client_ip:
            raise ValueError("无法获取客户端 IP")
        try:
            file_size = int(file_size)
        except Exception:
            raise ValueError("file_size 必须是整数")
        if file_size < 0:
            raise ValueError("file_size 不能小于 0")
        if self.max_file_size > 0 and file_size > self.max_file_size:
            raise ValueError("文件超过服务端允许的最大大小")
        sha256 = validate_sha256(sha256)
        client_name = self.resolver.get_client_name(client_ip)
        client_directory, target_path = self.paths._build_target_path(
            client_name, relative_path
        )
        target_lock = self.target_locks.get(target_path)
        with target_lock:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            # ------------------------------------------------
            # 这里不再判断正式文件是否相同。
            #
            # 只要是相同目标路径，就允许创建新的上传任务。
            #
            # 旧正式文件继续保留。
            # ------------------------------------------------
            self.check_disk_space(file_size)
            upload_id = uuid.uuid4().hex
            upload_directory = os.path.join(self.uploading_directory, upload_id)
            os.makedirs(upload_directory, exist_ok=False)
            total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
            now = int(time.time())
            metadata = {
                "upload_id": upload_id,
                "client_ip": client_ip,
                "client_name": client_name,
                "file_name": file_name,
                "relative_path": relative_path,
                "file_size": file_size,
                "file_extension": file_extension,
                "upload_time": upload_time,
                "sha256": sha256,
                "chunk_size": self.chunk_size,
                "total_chunks": total_chunks,
                "uploaded_chunks": [],
                "target_path": target_path,
                "created_time": now,
                "updated_time": now,
            }
            metadata_path = os.path.join(upload_directory, "metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            return {
                "status": "new",
                "upload_id": upload_id,
                "uploaded_chunks": [],
                "chunk_size": self.chunk_size,
            }

    def list_uploads(self):
        result = []
        if not os.path.isdir(self.uploading_directory):
            return result
        for upload_id in os.listdir(self.uploading_directory):
            upload_directory = os.path.join(self.uploading_directory, upload_id)
            if not os.path.isdir(upload_directory):
                continue
            metadata_path = os.path.join(upload_directory, "metadata.json")
            if not os.path.isfile(metadata_path):
                continue
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                file_size = int(metadata.get("file_size", 0))
                total_chunks = int(metadata.get("total_chunks", 0))
                uploaded_chunks = set(
                    int(index) for index in metadata.get("uploaded_chunks", [])
                )
                uploaded_count = len(uploaded_chunks)
                if total_chunks > 0:
                    progress = uploaded_count / total_chunks * 100
                else:
                    progress = 100
                target_path = metadata.get("target_path", "")
                try:
                    _, target_path = self.paths._build_target_path(
                        metadata.get("client_name", ""),
                        metadata.get("relative_path", ""),
                    )
                except Exception:
                    pass
                result.append(
                    {
                        "upload_id": metadata.get("upload_id", upload_id),
                        "client_ip": metadata.get("client_ip", ""),
                        "client_name": metadata.get("client_name", ""),
                        "file_name": metadata.get("file_name", ""),
                        "relative_path": metadata.get("relative_path", ""),
                        "file_size": file_size,
                        "file_extension": metadata.get("file_extension", ""),
                        "sha256": metadata.get("sha256", ""),
                        "total_chunks": total_chunks,
                        "uploaded_chunks": uploaded_count,
                        "progress": round(progress, 2),
                        "created_time": metadata.get("created_time", 0),
                        "updated_time": metadata.get("updated_time", 0),
                        "target_path": target_path,
                        "expired": self.is_upload_expired(metadata),
                    }
                )
            except Exception as e:
                print("[ADMIN] " "读取上传任务失败: " f"{upload_id}, 错误: {e}")
        result.sort(key=lambda item: item.get("updated_time", 0), reverse=True)
        return result

    def _load_metadata(self, upload_id):
        if not upload_id:
            raise ValueError("upload_id 不能为空")
        upload_id = str(upload_id)
        if len(upload_id) != 32 or any(
            c not in "0123456789abcdef" for c in upload_id.lower()
        ):
            raise ValueError("upload_id 无效")
        upload_directory = os.path.join(self.uploading_directory, upload_id)
        metadata_path = os.path.join(upload_directory, "metadata.json")
        if not os.path.isfile(metadata_path):
            raise ValueError("上传任务不存在")
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return (metadata, upload_directory)

    def get_upload_status(self, upload_id):
        metadata, _ = self._load_metadata(upload_id)
        expired = self.is_upload_expired(metadata)
        target_path = metadata.get("target_path", "")
        try:
            _, target_path = self.paths._build_target_path(
                metadata["client_name"], metadata["relative_path"]
            )
        except Exception:
            pass
        return {
            "upload_id": metadata["upload_id"],
            "client_ip": metadata["client_ip"],
            "client_name": metadata["client_name"],
            "file_name": metadata["file_name"],
            "relative_path": metadata["relative_path"],
            "file_size": metadata["file_size"],
            "file_extension": metadata.get("file_extension", ""),
            "sha256": metadata.get("sha256", ""),
            "chunk_size": metadata["chunk_size"],
            "total_chunks": metadata["total_chunks"],
            "uploaded_chunks": metadata.get("uploaded_chunks", []),
            "target_path": target_path,
            "created_time": metadata["created_time"],
            "updated_time": metadata["updated_time"],
            "expired": expired,
        }

    def save_chunk(self, upload_id, chunk_index, chunk_offset, chunk_data):
        lock = self.upload_locks.get(upload_id)
        with lock:
            metadata, upload_directory = self._load_metadata(upload_id)
            if self.is_upload_expired(metadata):
                self.cleanup_expired_upload(upload_id)
                raise ValueError("上传任务已经过期")
            try:
                chunk_index = int(chunk_index)
                chunk_offset = int(chunk_offset)
            except Exception:
                raise ValueError("chunk_index 和 chunk_offset 必须是整数")
            total_chunks = int(metadata["total_chunks"])
            file_size = int(metadata["file_size"])
            chunk_size = int(metadata["chunk_size"])
            if chunk_index < 0:
                raise ValueError("chunk_index 不能小于 0")
            if chunk_index >= total_chunks:
                raise ValueError("chunk_index 超出范围")
            expected_offset = chunk_index * chunk_size
            if chunk_offset != expected_offset:
                raise ValueError("chunk_offset 不正确")
            expected_size = min(chunk_size, file_size - expected_offset)
            actual_size = len(chunk_data)
            if actual_size != expected_size:
                raise ValueError(
                    f"分片大小错误: "
                    f"expected={expected_size}, "
                    f"actual={actual_size}"
                )
            chunk_path = os.path.join(upload_directory, f"{chunk_index:08d}.part")
            if os.path.isfile(chunk_path):
                existing_size = os.path.getsize(chunk_path)
                if existing_size == expected_size:
                    existing_sha256 = calculate_file_sha256(chunk_path)
                    incoming_sha256 = hashlib.sha256(chunk_data).hexdigest()
                    if existing_sha256 == incoming_sha256:
                        return {
                            "success": True,
                            "status": "exists",
                            "chunk_index": chunk_index,
                        }
            temporary_path = chunk_path + ".tmp"
            try:
                with open(temporary_path, "wb") as f:
                    f.write(chunk_data)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary_path, chunk_path)
            finally:
                if os.path.exists(temporary_path):
                    try:
                        os.remove(temporary_path)
                    except OSError:
                        pass
            uploaded_chunks = set(
                int(index) for index in metadata.get("uploaded_chunks", [])
            )
            uploaded_chunks.add(chunk_index)
            metadata["uploaded_chunks"] = sorted(uploaded_chunks)
            metadata["updated_time"] = int(time.time())
            metadata_path = os.path.join(upload_directory, "metadata.json")
            temporary_metadata_path = metadata_path + ".tmp"
            try:
                with open(temporary_metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary_metadata_path, metadata_path)
            finally:
                if os.path.exists(temporary_metadata_path):
                    try:
                        os.remove(temporary_metadata_path)
                    except OSError:
                        pass
            return {"success": True, "status": "uploaded", "chunk_index": chunk_index}
