"""合并与校验分片，提交正式文件并在失败时回滚替换。"""

import hashlib
import os
import time

from .checksums import validate_sha256


class UploadCommitter:
    """合并与校验分片，提交正式文件并在失败时回滚替换。"""

    def __init__(self, tasks, files, paths, upload_locks, target_locks):
        self.tasks = tasks
        self.files = files
        self.paths = paths
        self.upload_locks = upload_locks
        self.target_locks = target_locks

    def complete_upload(self, upload_id):
        upload_lock = self.upload_locks.get(upload_id)
        with upload_lock:
            metadata, upload_directory = self.tasks._load_metadata(upload_id)
            if self.tasks.is_upload_expired(metadata):
                self.tasks.cleanup_expired_upload(upload_id)
                return {
                    "success": False,
                    "status": "expired",
                    "error": "上传任务已经过期",
                }
            file_size = int(metadata["file_size"])
            total_chunks = int(metadata["total_chunks"])
            client_sha256 = validate_sha256(metadata.get("sha256"))
            uploaded_chunks = set(
                int(index) for index in metadata.get("uploaded_chunks", [])
            )
            expected_chunks = set(range(total_chunks))
            missing_chunks = expected_chunks - uploaded_chunks
            if missing_chunks:
                return {
                    "success": False,
                    "status": "incomplete",
                    "missing_chunks": sorted(missing_chunks),
                }
            for chunk_index in range(total_chunks):
                chunk_path = os.path.join(upload_directory, f"{chunk_index:08d}.part")
                if not os.path.isfile(chunk_path):
                    return {
                        "success": False,
                        "status": "incomplete",
                        "missing_chunks": [chunk_index],
                    }
            temporary_file, total_written, sha256 = self._assemble_chunks(
                upload_directory, total_chunks
            )
            if total_written != file_size:
                if os.path.exists(temporary_file):
                    try:
                        os.remove(temporary_file)
                    except OSError:
                        pass
                return {
                    "success": False,
                    "status": "size_mismatch",
                    "expected_size": file_size,
                    "actual_size": total_written,
                }
            server_sha256 = sha256.hexdigest()
            if server_sha256 != client_sha256:
                if os.path.exists(temporary_file):
                    try:
                        os.remove(temporary_file)
                    except OSError:
                        pass
                return {
                    "success": False,
                    "status": "sha256_mismatch",
                    "client_sha256": client_sha256,
                    "server_sha256": server_sha256,
                }
            # ------------------------------------------------
            # 构造正式目标路径
            # ------------------------------------------------
            return self._commit(
                upload_id,
                metadata,
                upload_directory,
                temporary_file,
                total_written,
                server_sha256,
            )

    def _assemble_chunks(self, upload_directory, total_chunks):
        """流式合并分片，同时计算实际大小与摘要。"""
        temporary_file = os.path.join(upload_directory, "assembled.tmp")
        sha256 = hashlib.sha256()
        total_written = 0
        try:
            with open(temporary_file, "wb") as output:
                for chunk_index in range(total_chunks):
                    chunk_path = os.path.join(
                        upload_directory, f"{chunk_index:08d}.part"
                    )
                    with open(chunk_path, "rb") as chunk_file:
                        while True:
                            data = chunk_file.read(1024 * 1024)
                            if not data:
                                break
                            output.write(data)
                            sha256.update(data)
                            total_written += len(data)
                output.flush()
                os.fsync(output.fileno())
        except Exception:
            if os.path.exists(temporary_file):
                try:
                    os.remove(temporary_file)
                except OSError:
                    pass
            raise
        return temporary_file, total_written, sha256

    def _commit(
        self,
        upload_id,
        metadata,
        upload_directory,
        temporary_file,
        total_written,
        server_sha256,
    ):
        """持有目标锁完成替换和元数据提交，失败时恢复旧文件。"""
        client_directory, target_path = self.paths._build_target_path(
            metadata["client_name"], metadata["relative_path"]
        )
        metadata["target_path"] = target_path
        target_lock = self.target_locks.get(target_path)
        # ------------------------------------------------
        # 最终替换阶段才获取 target_path 锁
        # ------------------------------------------------
        with target_lock:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            old_file_backup = None
            old_file_exists = os.path.isfile(target_path)
            # --------------------------------------------
            # 如果旧文件存在：
            # 不直接删除。
            #
            # 先在同一目录改名为临时备份。
            # 这样 os.replace() 仍然是同文件系统原子操作。
            # --------------------------------------------
            if old_file_exists:
                old_file_backup = target_path + ".replace." + upload_id + ".bak"
                try:
                    os.replace(target_path, old_file_backup)
                except OSError as e:
                    try:
                        os.remove(temporary_file)
                    except OSError:
                        pass
                    return {
                        "success": False,
                        "status": "replace_prepare_failed",
                        "error": ("无法准备替换旧文件: " f"{e}"),
                        "file": target_path,
                    }
            # --------------------------------------------
            # 新文件进入正式路径
            # --------------------------------------------
            try:
                os.replace(temporary_file, target_path)
            except Exception as e:
                # 新文件替换失败。
                # 如果旧文件已经移动到备份位置，
                # 立即恢复旧文件。
                if old_file_backup is not None:
                    try:
                        if os.path.exists(target_path):
                            os.remove(target_path)
                    except OSError:
                        pass
                    try:
                        os.replace(old_file_backup, target_path)
                    except OSError as restore_error:
                        print(
                            "[REPLACE] "
                            "新文件替换失败，"
                            "且旧文件恢复失败: "
                            f"target={target_path}, "
                            f"错误={restore_error}"
                        )
                        return {
                            "success": False,
                            "status": ("replace_failed_restore_failed"),
                            "error": ("新文件替换失败，" "且旧文件恢复失败"),
                            "replace_error": str(e),
                            "restore_error": str(restore_error),
                            "file": target_path,
                        }
                return {
                    "success": False,
                    "status": "replace_failed",
                    "error": (f"新文件进入正式路径失败: {e}"),
                    "file": target_path,
                }
            completed_time = int(time.time())
            metadata["sha256"] = server_sha256
            metadata["completed_time"] = completed_time
            metadata["updated_time"] = completed_time
            metadata.pop("uploaded_chunks", None)
            metadata.pop("chunk_size", None)
            metadata.pop("total_chunks", None)
            # --------------------------------------------
            # 写入正式文件元数据
            # --------------------------------------------
            try:
                self.files._write_file_metadata(metadata)
            except Exception as e:
                print("[METADATA] " f"写入元数据失败: " f"{target_path}, 错误: {e}")
                # 删除新文件
                try:
                    if os.path.exists(target_path):
                        os.remove(target_path)
                except OSError as cleanup_error:
                    print(
                        "[METADATA] "
                        "新文件删除失败: "
                        f"{target_path}, "
                        f"错误: {cleanup_error}"
                    )
                    if old_file_backup is not None:
                        return {
                            "success": False,
                            "status": ("metadata_error_file_cleanup_failed"),
                            "error": ("元数据写入失败，" "且新文件无法删除"),
                            "metadata_error": str(e),
                            "file_cleanup_error": str(cleanup_error),
                            "file": target_path,
                            "size": total_written,
                            "sha256": server_sha256,
                        }
                    return {
                        "success": False,
                        "status": ("metadata_error_file_cleanup_failed"),
                        "error": ("元数据写入失败，" "且新文件无法删除"),
                        "metadata_error": str(e),
                        "file_cleanup_error": str(cleanup_error),
                        "file": target_path,
                        "size": total_written,
                        "sha256": server_sha256,
                    }
                # ----------------------------------------
                # 恢复旧正式文件
                # ----------------------------------------
                if old_file_backup is not None:
                    try:
                        os.replace(old_file_backup, target_path)
                        print(
                            "[METADATA] "
                            "元数据写入失败，"
                            "旧视频文件已经恢复: "
                            f"{target_path}"
                        )
                    except OSError as restore_error:
                        print(
                            "[METADATA] "
                            "元数据写入失败，"
                            "且旧视频文件恢复失败: "
                            f"{target_path}, "
                            f"错误: {restore_error}"
                        )
                        return {
                            "success": False,
                            "status": ("metadata_error_restore_failed"),
                            "error": ("元数据写入失败，" "且旧视频文件恢复失败"),
                            "metadata_error": str(e),
                            "restore_error": str(restore_error),
                            "file": target_path,
                            "size": total_written,
                            "sha256": server_sha256,
                        }
                # ----------------------------------------
                # 清理上传任务目录
                # ----------------------------------------
                try:
                    for filename in os.listdir(upload_directory):
                        file_path = os.path.join(upload_directory, filename)
                        try:
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        except OSError:
                            pass
                    try:
                        os.rmdir(upload_directory)
                    except OSError:
                        pass
                except Exception:
                    pass
                return {
                    "success": False,
                    "status": "metadata_error",
                    "error": (
                        "视频文件校验成功，" "但元数据写入失败；" "已经恢复原正式文件"
                    ),
                    "metadata_error": str(e),
                    "file": target_path,
                    "size": total_written,
                    "sha256": server_sha256,
                }
            # --------------------------------------------
            # 元数据写入成功
            #
            # 到这里新文件已经正式生效。
            # 删除旧文件备份。
            # --------------------------------------------
            if old_file_backup is not None:
                try:
                    os.remove(old_file_backup)
                except OSError as e:
                    print(
                        "[REPLACE] "
                        "新文件已经成功替换旧文件，"
                        "但旧文件备份删除失败: "
                        f"{old_file_backup}, "
                        f"错误: {e}"
                    )
            # --------------------------------------------
            # 清理上传任务目录
            # --------------------------------------------
            for filename in os.listdir(upload_directory):
                file_path = os.path.join(upload_directory, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except OSError:
                    pass
            try:
                os.rmdir(upload_directory)
            except OSError:
                pass
            return {
                "success": True,
                "status": "completed",
                "file": target_path,
                "size": total_written,
                "sha256": server_sha256,
                "overwritten": old_file_exists,
            }
