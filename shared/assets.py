"""两端文件浏览器的公共静态资源位置。"""

from pathlib import Path

STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"
