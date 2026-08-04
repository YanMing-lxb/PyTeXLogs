"""编码辅助函数与路径解析工具。"""

from pathlib import Path

FALLBACK_ENCODINGS: tuple[str, ...] = (
    "utf-8",
    "utf-8-sig",
    "gbk",
    "gb18030",
    "latin-1",
)


def read_log_text(log_path: str | Path) -> str:
    """读取日志文件，多编码兜底。"""
    path = Path(log_path)
    data = path.read_bytes()
    for encoding in FALLBACK_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def resolve_path(file_path: str, root_file: str | None = None) -> str:
    """解析文件路径，将相对路径转换为绝对路径。"""
    if not file_path:
        return ""
    path = Path(file_path)
    if path.is_absolute():
        return str(path)
    if root_file:
        root_dir = Path(root_file).parent
        try:
            return str((root_dir / file_path).resolve())
        except Exception:
            return file_path
    return file_path