"""CLI 参数解析与编辑器检测工具。"""

import argparse
import os
import shlex as _shlex
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..core.models import LogLevel
from ..version import __version__

__all__ = [
    "_SEVERITY_LEVEL",
    "_apply_editor_template",
    "_build_common_args",
    "_detect_editor",
    "_flatten_entries",
    "build_parser",
    "shlex_split",
]

_SEVERITY_LEVEL: dict[str, LogLevel] = {
    "error": LogLevel.ERROR,
    "warning": LogLevel.WARNING,
    "info": LogLevel.INFO,
    "all": LogLevel.INFO,
    "error+warning": LogLevel.WARNING,
}


def shlex_split(s: str) -> list[str]:
    """安全的 shell 风格分词：优先 POSIX 模式，失败回退空格切分。"""
    try:
        return _shlex.split(s, posix=True)
    except Exception:
        return s.split()


def _detect_editor(custom: str | None) -> list[str]:
    """检测可用的编辑器命令行参数列表。"""
    if custom and custom.startswith("custom:"):
        return custom[len("custom:"):].split()
    if custom and custom != "auto":
        return [custom]
    for env in ("VISUAL", "EDITOR"):
        v = os.environ.get(env)
        if v:
            return shlex_split(v)
    for name in ("code", "subl", "nvim", "gvim", "notepad"):
        p = shutil.which(name)
        if p:
            return [p]
    return []


def _apply_editor_template(tokens: Sequence[str], file: str, line: int) -> list[str]:
    """对编辑器命令行 tokens 应用 %f/%l 模板替换。"""
    out: list[str] = []
    for t in tokens:
        if "%f" in t or "%l" in t or "%L" in t:
            new_t = t.replace("%f", file).replace("%L", str(line)).replace("%l", str(line))
            out.append(new_t)
        else:
            out.append(t)
    if not any("%" in tok for tok in tokens):
        cmd_name = tokens[0] if tokens else ""
        if cmd_name.endswith(("code", "code.exe")):
            out.append("--goto")
            out.append(f"{file}:{line}")
        else:
            out.append(f"{file}")
    return out


def _flatten_entries(
    obj: Any,
    severity: str = "error+warning",
) -> tuple[list[Any], LogLevel]:
    """将 ParsedPipelineReport 或 ToolResult 列表扁平化为 (entry, cat, tool, src) 列表。"""
    from ..core.models import LogEntry, ReportEntry, ToolResult, ToolResultReport

    min_level = _SEVERITY_LEVEL.get(severity, LogLevel.WARNING)
    all_entries: list[tuple[LogEntry | ReportEntry, str, str, str]] = []
    raw_results: list[Any]

    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        raw_results = [obj]
    elif isinstance(obj, list):
        raw_results = [o for o in obj if isinstance(o, (ToolResult, ToolResultReport))]
        if not raw_results:
            entries: list[LogEntry] = [o for o in obj if isinstance(o, LogEntry)]
            return _filter_by_level(entries, min_level), min_level
    else:
        raw_results = []

    for r in raw_results:
        cat = getattr(r, "category", "")
        tname = getattr(r, "tool_name", "")
        sp = getattr(r, "source_path", "")
        entries_r = getattr(r, "entries", [])
        for e in _filter_by_level(entries_r, min_level):
            all_entries.append((e, cat, tname, sp))
    return all_entries, min_level


def _filter_by_level(entries: list[Any], min_level: LogLevel) -> list[Any]:
    """按最低严重级别过滤条目。

    级别顺序：error(0) < warning(1) < typesetting(2) < font(3) < graphic(4) < page(5) < info(6)。
    """
    result: list[Any] = []
    level_order = {"error": 0, "warning": 1, "typesetting": 2, "font": 3, "graphic": 4, "page": 5, "info": 6}
    min_val_int = level_order.get(str(min_level.value), 7)
    for e in entries:
        entry_level = getattr(e, "level", None)
        if entry_level is None:
            continue
        # Handle LogLevel enum
        if hasattr(entry_level, "value"):
            entry_val_int = level_order.get(str(entry_level.value), 7)
            if entry_val_int <= min_val_int:
                result.append(e)
        # Handle string level (from ReportEntry)
        elif isinstance(entry_level, str):
            entry_val_int = level_order.get(entry_level, 7)
            if entry_val_int <= min_val_int:
                result.append(e)
    return result


def _build_common_args(parser: argparse.ArgumentParser) -> None:
    """添加非 --version 的公共参数（供顶层 + 各子 parser parents 共享）。"""
    parser.add_argument("--lang", choices=("en", "zh"), default="zh", help="摘要语言（zh / en），默认 zh")
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=("text", "json", "csv", "sarif"),
        default="text",
        help="输出格式：text/json/csv/sarif（默认 text）",
    )
    parser.add_argument("--output", "-o", type=Path, default=None, help="输出到文件（默认 stdout）")
    parser.add_argument(
        "--severity",
        choices=("error", "warning", "info", "all", "error+warning"),
        default="error+warning",
        help="仅展示/导出 ≥ 该严重度的条目（默认 error+warning）",
    )
    parser.add_argument("--root-file", type=Path, default=None, help="传给 parser 的主 .tex 路径（可选）")
    parser.add_argument("--open", dest="do_open", action="store_true", help="尝试对 ERROR 条目打开编辑器跳转")
    parser.add_argument(
        "--editor",
        default="auto",
        help='编辑器：auto | code | subl | nvim | gvim | custom:"code --goto %%f:%%l"',
    )
    parser.add_argument("--dry-run", action="store_true", help="仅打印 --open 命令，不真的启动进程")


def build_parser() -> argparse.ArgumentParser:
    """构建完整的 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="pytexlogs",
        description="PyTeXLogs: 11+ LaTeX 工具日志解析 CLI（零第三方硬依赖）。",
    )
    parser.add_argument("--version", action="version", version=f"pytexlogs {__version__}")
    _build_common_args(parser)
    common_parent = argparse.ArgumentParser(add_help=False)
    _build_common_args(common_parent)
    sub = parser.add_subparsers(dest="subcmd", metavar="<subcmd>")

    def _add_positional(subp: argparse.ArgumentParser) -> None:
        subp.add_argument(
            "paths",
            nargs="*",
            help="日志文件 / aux 目录（文件会直接 parse_log_file；目录会作为 auxdir 做 run() 全量解析）",
        )

    p_check = sub.add_parser("check", help="检查日志，发现 ERROR 则返回 exitcode=1", parents=[common_parent])
    _add_positional(p_check)
    p_summary = sub.add_parser("summary", help="仅打印摘要（不返回 error exitcode）", parents=[common_parent])
    _add_positional(p_summary)
    p_export = sub.add_parser(
        "export",
        help="导出 JSON/CSV/SARIF（默认 stdout，--format 覆盖）",
        parents=[common_parent],
    )
    _add_positional(p_export)
    sub.add_parser("demo", help="跑独立库内置演示（integration_demo.run_demo）")
    return parser