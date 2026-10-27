"""文件预览类型识别，以及有大小上限的纯文本读取。"""

import codecs
from pathlib import Path

from .file_access import FileAccessError

TEXT_EXTENSIONS = {
    ".txt",
    ".log",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".md",
    ".rst",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".conf",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    ".py",
    ".sh",
    ".bat",
    ".ps1",
    ".sql",
    ".toml",
    ".c",
    ".h",
    ".cpp",
    ".java",
    ".go",
    ".rs",
    ".srt",
    ".vtt",
    ".env",
}
VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".ogv",
    ".ogg",
    ".m4v",
    ".mov",
    ".mkv",
    ".avi",
    ".mts",
    ".m2ts",
}
TEXT_PREVIEW_LIMIT = 256 * 1024


def preview_kind(path):
    suffix = Path(path).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in TEXT_EXTENSIONS or not suffix or Path(path).name.lower() == ".env":
        return "text"
    return "none"


def read_text_preview(path):
    if preview_kind(path) != "text":
        raise FileAccessError(415, "此格式不支持文本预览，请下载后查看")
    with open(path, "rb") as stream:
        raw = stream.read(TEXT_PREVIEW_LIMIT + 1)
    truncated = len(raw) > TEXT_PREVIEW_LIMIT
    raw = raw[:TEXT_PREVIEW_LIMIT]
    encodings = (
        ["utf-16"]
        if raw.startswith((b"\xff\xfe", b"\xfe\xff"))
        else ["utf-8-sig", "gb18030"]
    )
    if b"\x00" in raw and encodings != ["utf-16"]:
        raise FileAccessError(415, "该文件包含二进制内容，请下载后查看")
    text = None
    for encoding in encodings:
        try:
            # 分段截取可能正好切断一个多字节字符，只忽略末尾未完成的字符。
            text = codecs.getincrementaldecoder(encoding)().decode(
                raw, final=not truncated
            )
        except UnicodeDecodeError:
            continue
        break
    if text is None or any(ord(char) < 32 and char not in "\t\r\n\f" for char in text):
        raise FileAccessError(415, "无法识别为受支持的文本，请下载后查看")
    return {
        "success": True,
        "text": text,
        "encoding": encoding,
        "truncated": truncated,
        "limit": TEXT_PREVIEW_LIMIT,
        "file_size": Path(path).stat().st_size,
    }
