"""CLI 参数解析与编辑器检测工具。

0.5.0 起的关键修正：
- 子命令的公共参数使用 ``argparse.SUPPRESS``，避免「写在子命令之前的全局选项
  被子命令默认值覆盖」（argparse 的经典坑）；
- 新增 ``--jobname`` / ``--fail-on`` / ``--max-entries`` / ``--baseline`` /
  ``--open-all``，并加入 ``explain`` 子命令；
- ``--dry-run`` 明确只影响 ``--open``。
"""

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
    "_normalize_argv",
    "build_parser",
    "shlex_split",
]

#: 已注册的子命令名。裸路径规范化时，首个位置 token 命中这些名字就不插入 check。
_SUBCMDS = frozenset({"check", "summary", "export", "explain", "demo"})

#: 顶层需要取值的选项。规范化扫描时不能把它们后面那个 token 当成位置参数。
_OPTIONS_WITH_VALUE = frozenset(
    {
        "--lang",
        "--format",
        "--output",
        "-o",
        "--severity",
        "--root-file",
        "--jobname",
        "--editor",
        "--max-entries",
        "--baseline",
        "--completion",
    }
)

_SEVERITY_LEVEL: dict[str, LogLevel] = {
    "error": LogLevel.ERROR,
    "warning": LogLevel.WARNING,
    "info": LogLevel.INFO,
    # "all" = 不过滤：取枚举里最后一级（0.6.1 起是 PAGE，因此也包含 TYPESET/
    # FONT/GRAPHIC）。0.5 把 all 映射成 INFO，正好漏掉最不严重的几类提示。
    "all": list(LogLevel)[-1],
    "error+warning": LogLevel.WARNING,
}


def shlex_split(s: str) -> list[str]:
    """安全的 shell 风格分词：优先 POSIX 模式，Windows 保留反斜杠路径。

    ``posix=True`` 会把 ``C:\\Program Files\\...`` 里的反斜杠当转义符，
    在 Windows 上启动编辑器会得到 ``C:Program Files...``。因此按平台选择
    ``posix``；解析失败再回退空格切分。
    """
    try:
        return _shlex.split(s, posix=os.name != "nt")
    except Exception:
        return s.split()


def _detect_editor(custom: str | None) -> list[str]:
    """检测可用的编辑器命令行参数列表。"""
    if custom and custom.startswith("custom:"):
        return shlex_split(custom[len("custom:") :])
    if custom and custom != "auto":
        return shlex_split(custom)
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
        cmd_name = Path(tokens[0]).name.lower() if tokens else ""
        if cmd_name in {"code", "code.exe", "code.cmd", "code.bat"}:
            out.append("--goto")
            out.append(f"{file}:{line}")
        else:
            out.append(f"{file}")
    return out


def _flatten_entries(
    obj: Any,
    severity: str = "error+warning",
) -> tuple[list[Any], LogLevel]:
    """将报告/结果/条目扁平化为 [(entry, category, tool, source_path)]。"""
    from ..core.models import (
        LogEntry,
        ParsedLog,
        ParsedPipelineReport,
        ReportEntry,
        ToolResult,
        ToolResultReport,
    )

    min_level = _SEVERITY_LEVEL.get(severity, LogLevel.WARNING)
    all_entries: list[tuple[LogEntry | ReportEntry, str, str, str]] = []
    bare_entries: list[LogEntry] = []

    if isinstance(obj, ParsedPipelineReport):
        raw_results: list[Any] = list(obj.tool_results)
    elif isinstance(obj, (ToolResult, ToolResultReport, ParsedLog)):
        raw_results = [obj]
    elif isinstance(obj, LogEntry):
        return _filter_by_level([obj], min_level), min_level
    elif isinstance(obj, list):
        raw_results = [o for o in obj if isinstance(o, (ToolResult, ToolResultReport, ParsedLog))]
        bare_entries = [o for o in obj if isinstance(o, LogEntry)]
    else:
        raw_results = []

    for r in raw_results:
        cat = getattr(r, "category", "")
        tname = getattr(r, "tool_name", "")
        sp = getattr(r, "source_path", "")
        entries_r = getattr(r, "entries", [])
        all_entries.extend((e, cat, tname, sp) for e in _filter_by_level(entries_r, min_level))
    all_entries.extend((e, "", "", "") for e in _filter_by_level(bare_entries, min_level))
    return all_entries, min_level


def _filter_by_level(entries: list[Any], min_level: LogLevel) -> list[Any]:
    """按最低严重级别过滤条目。

    严重度顺序唯一由 :class:`LogLevel` 的 ``severity`` 派生；不要在这里再维护
    一份字符串表。0.6.1 已把 TYPESET/FONT/GRAPHIC/PAGE 排在 INFO 之后，旧表
    （typesetting=2、info=6）会让 ``--severity info`` 反而保留提示级、滤掉 info。
    """
    threshold = int(min_level.severity)
    result: list[Any] = []
    for e in entries:
        entry_level = getattr(e, "level", None)
        if entry_level is None:
            continue
        if isinstance(entry_level, LogLevel):
            rank = int(entry_level.severity)
        elif isinstance(entry_level, str):
            try:
                rank = int(LogLevel(entry_level).severity)
            except ValueError:
                rank = int(LogLevel.INFO.severity)
        else:
            rank = int(getattr(entry_level, "severity", LogLevel.INFO.severity))
        if rank <= threshold:
            result.append(e)
    return result


def _add_common_args(parser: argparse.ArgumentParser, *, suppress: bool) -> None:
    """添加公共参数；``suppress=True`` 时不给默认值（供子 parser 共用，避免覆盖）。"""
    default = argparse.SUPPRESS if suppress else None
    parser.add_argument(
        "--lang",
        choices=("en", "zh"),
        default=(argparse.SUPPRESS if suppress else "zh"),
        help="摘要语言（zh / en），默认 zh",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=("text", "json", "csv", "sarif"),
        default=(argparse.SUPPRESS if suppress else "text"),
        help="输出格式：text/json/csv/sarif（默认 text）",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=(argparse.SUPPRESS if suppress else None),
        help="输出到文件（默认 stdout）",
    )
    parser.add_argument(
        "--severity",
        choices=("error", "warning", "info", "all", "error+warning"),
        default=(argparse.SUPPRESS if suppress else "error+warning"),
        help="仅展示/导出 ≥ 该严重度的条目（默认 error+warning）",
    )
    parser.add_argument(
        "--root-file",
        type=Path,
        default=(argparse.SUPPRESS if suppress else None),
        help="传给 parser 的主 .tex 路径（可选）",
    )
    parser.add_argument(
        "--jobname",
        default=default,
        help="目录模式的 jobname（默认取目录里首个带 \\documentclass 的 .tex）",
    )
    parser.add_argument(
        "--open",
        dest="do_open",
        action="store_true",
        default=(argparse.SUPPRESS if suppress else False),
        help="尝试对 ERROR 条目打开编辑器跳转（默认只开第一条）",
    )
    parser.add_argument(
        "--open-all",
        dest="open_all",
        action="store_true",
        default=(argparse.SUPPRESS if suppress else False),
        help="--open 时打开所有 ERROR 条目（默认只开第一条）",
    )
    parser.add_argument(
        "--editor",
        default=(argparse.SUPPRESS if suppress else "auto"),
        help='编辑器：auto | code | subl | nvim | gvim | custom:"code --goto %%f:%%l"',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=(argparse.SUPPRESS if suppress else False),
        help="仅打印 --open 将要执行的命令，不真的启动进程",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=(argparse.SUPPRESS if suppress else None),
        help="文本摘要每个分组最多展示 N 条（默认 10，0 表示不限制）",
    )
    parser.add_argument(
        "--no-hints",
        dest="no_hints",
        action="store_true",
        default=(argparse.SUPPRESS if suppress else False),
        help="不在摘要里追加可执行建议",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=(argparse.SUPPRESS if suppress else None),
        help="上次的报告 JSON；只输出本次新增/变化的条目",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=(argparse.SUPPRESS if suppress else False),
        help="目录模式递归扫描子目录（只处理含 .log/.tex 的目录）",
    )


def _build_common_args(parser: argparse.ArgumentParser) -> None:
    """添加非 --version 的公共参数（顶层带默认值）。"""
    _add_common_args(parser, suppress=False)


def _normalize_argv(argv: Sequence[str]) -> list[str]:
    """把裸路径输入改写成显式的 ``check`` 子命令。

    顶层 parser 刻意**不**注册 ``paths`` 位置参数：那会与 subparsers 抢占
    ``check`` / ``summary`` 等 token，导致 ``pytexlogs check main.log`` 把
    ``check`` 当成日志路径。因此 ``pytexlogs main.log`` 在解析前先在这里补上
    ``check``，使其与 ``pytexlogs check main.log`` 完全等价。

    扫描规则：跳过所有 ``-`` 开头的选项（需要取值的选项连同其值一起跳过，
    支持 ``--opt=value`` 内联写法）；``--`` 之后的 token 一律按位置参数处理；
    找到的第一个位置 token 若不是已知子命令，就在它前面插入 ``check``。
    """
    out: list[str] = []
    i = 0
    n = len(argv)
    positional_only = False
    dash_index: int | None = None
    while i < n:
        tok = argv[i]
        if not positional_only:
            if tok == "--":
                positional_only = True
                dash_index = len(out)
                out.append(tok)
                i += 1
                continue
            if tok.startswith("-") and tok != "-":
                out.append(tok)
                # --opt=value 的值已经内联在同一个 token 里，无需再跳。
                if "=" not in tok and tok in _OPTIONS_WITH_VALUE and i + 1 < n:
                    out.append(argv[i + 1])
                    i += 2
                    continue
                i += 1
                continue
        if tok not in _SUBCMDS:
            # 首个位置 token 是路径：插到 ``--`` 之前（无 ``--`` 时插在末尾），
            # 保证 ``--lang en -- main.log`` 变成 ``--lang en check -- main.log``。
            out.insert(dash_index if dash_index is not None else len(out), "check")
            out.extend(argv[i:])
            return out
        out.append(tok)
        out.extend(argv[i + 1 :])
        return out
    return out


def build_parser() -> argparse.ArgumentParser:
    """构建完整的 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="pytexlogs",
        description="PyTeXLogs: LaTeX 工具日志解析 CLI（零第三方硬依赖）。",
        epilog=(
            "示例：pytexlogs main.log | pytexlogs main.log --open | "
            "pytexlogs Build/ --jobname main --format sarif | pytexlogs explain 'Missing character'\n"
            "退出码：0=无错误；1=check 命中错误（或 --fail-on warning 时命中警告）；2=参数/运行异常。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"pytexlogs {__version__}")
    parser.add_argument(
        "--completion",
        choices=("bash", "zsh", "fish", "powershell"),
        help="输出指定 shell 的补全脚本后退出（bash/zsh/fish/powershell）",
    )
    _build_common_args(parser)
    common_parent = argparse.ArgumentParser(add_help=False)
    _add_common_args(common_parent, suppress=True)
    sub = parser.add_subparsers(dest="subcmd", metavar="<subcmd>")

    def _add_positional(subp: argparse.ArgumentParser) -> None:
        subp.add_argument(
            "paths",
            nargs="*",
            help="日志文件 / aux 目录（文件会直接 parse_log_file；目录会作为 auxdir 做全量解析）",
        )

    p_check = sub.add_parser("check", help="检查日志，发现 ERROR 则返回 exitcode=1", parents=[common_parent])
    _add_positional(p_check)
    p_check.add_argument(
        "--fail-on",
        choices=("error", "warning"),
        default=argparse.SUPPRESS,
        help="命中所选严重度时返回 1（默认 error）",
    )
    p_summary = sub.add_parser("summary", help="仅打印摘要（不返回 error exitcode）", parents=[common_parent])
    _add_positional(p_summary)
    p_export = sub.add_parser(
        "export",
        help="导出 JSON/CSV/SARIF（默认 stdout，--format 覆盖）",
        parents=[common_parent],
    )
    _add_positional(p_export)
    p_explain = sub.add_parser(
        "explain",
        help="查询某条日志文本对应的可执行建议（hint）",
        parents=[common_parent],
    )
    p_explain.add_argument("text", nargs="*", help="日志文本片段")
    p_explain.add_argument(
        "--tool",
        choices=("latex", "pdflatex", "xelatex", "lualatex", "bibtex", "biber"),
        default=argparse.SUPPRESS,
        help="日志来源工具；限定旧提示表，避免 Biber 的 WARN - 命中 LaTeX 警告",
    )
    sub.add_parser("demo", help="跑独立库内置演示（integration_demo.run_demo）")
    return parser
