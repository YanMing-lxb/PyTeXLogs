"""日志中相对路径的统一解析。

BibTeX/Biber 的 `.blg` 只记录数据库文件名；解析出的路径要与主文件同目录，
同时保留原字符串作为失败回退。各解析器仍需自己的缓存，这里只提供纯函数。
"""

from pathlib import Path


def resolve_relative_path(filename: str, root_file: str) -> str:
    """把 ``filename`` 解析为相对 ``root_file`` 同目录的绝对路径。"""
    if not filename:
        return root_file
    root_dir = Path(root_file).parent
    try:
        return str((root_dir / filename).resolve())
    except OSError, RuntimeError:
        return filename


def resolve_relative_path_from(filename: str, root_file: str, source_hint: str | None = None) -> str:
    """把 ``filename`` 锚定到实际存在的目录。

    依次尝试 ``source_hint``（日志真实路径）同目录、``root_file`` 同目录、
    当前目录；第一个 ``dir / filename`` 存在的候选优先。``root_file`` 常是
    缺省的 ``"main.tex"``，其父目录为 ``"."``，只按它解析会把 auxdir 里的
    数据库文件错误地指到进程 CWD，所以先把日志同目录放在最前。
    """
    if not filename:
        return root_file

    path = Path(filename)
    if path.is_absolute():
        return str(path)

    dirs: list[Path] = []
    if source_hint:
        dirs.append(Path(source_hint).parent)
    if root_file:
        root_dir = Path(root_file).parent
        if root_dir not in dirs:
            dirs.append(root_dir)
    cwd = Path(".")
    if cwd not in dirs:
        dirs.append(cwd)

    for directory in dirs:
        candidate = directory / filename
        if candidate.exists():
            try:
                return str(candidate.resolve())
            except OSError, RuntimeError:
                return str(candidate)

    return str(dirs[0] / filename)
