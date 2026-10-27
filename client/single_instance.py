"""进程实例锁：Linux 使用 flock，Windows 使用 msvcrt。"""

import os

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class SingleInstance:
    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.fd = None

    def acquire(self):
        if self.fd is not None:
            return
        fd = open(self.lock_file, "a+")
        try:
            fd.seek(0)
            if os.name == "nt":
                msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            fd.close()
            raise RuntimeError("客户端已经在运行，不能启动第二个实例") from exc
        self.fd = fd
        fd.seek(0)
        fd.truncate()
        fd.write(str(os.getpid()))
        fd.flush()

    def release(self):
        fd, self.fd = self.fd, None
        if fd is not None:
            try:
                fd.seek(0)
                if os.name == "nt":
                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
            finally:
                fd.close()
