"""CLI 主入口：解析参数、调度子命令、输出结果。

0.5.0 的修正：
- 目录模式不再触发 ``run_pipeline`` 自带摘要，避免同一条警告打印 2~3 遍；
- ``--severity`` 同时作用于 text/json/csv/sarif（此前只有文本生效）；
- ``--baseline`` 只输出“本次新增/恶化”的条目，适合写作期盯回归；
- ``--fail-on`` 让 CI 能在出现 warning 时也失败。
"""

from __future__ import annotations

import dataclasses
import io
import json as _json
import locale
import logging
import os
import subprocess
import sys
import warnings as _w
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..core.engine import run_pipeline
from ..core.models import LogEntry, LogLevel, ParsedLog, ToolResult, ToolResultReport, ToolResultStats
from ..display import print_summary, set_summary_language
from ..exporters.csv_exporter import to_csv
from ..exporters.json_exporter import filter_by_level, to_json
from ..exporters.sarif_exporter import to_sarif
from .args import (
    _SEVERITY_LEVEL,
    _apply_editor_template,
    _detect_editor,
    _flatten_entries,
    build_parser,
)

__all__ = ["main"]

logger = logging.getLogger("pytexlogs.cli")

_LEVEL_STRING_TO_ENUM = {
    "error": LogLevel.ERROR,
    "warning": LogLevel.WARNING,
    "typesetting": LogLevel.INFO,
    "font": LogLevel.INFO,
    "graphic": LogLevel.INFO,
    "page": LogLevel.INFO,
    "info": LogLevel.INFO,
}


def _tool_result_report_to_tool_result(trr: ToolResultReport) -> ToolResult:
    """将 ToolResultReport 转换为 ToolResult（统一数据类型）。"""
    entries: list[LogEntry] = []
    for e in trr.entries:
        level = _LEVEL_STRING_TO_ENUM.get(str(e.level), LogLevel.INFO)
        entries.append(LogEntry(
            level=level,
            file=e.file or "",
            line=e.line or 0,
            text=e.text or "",
            error_pos_text=e.error_pos_text or "",
        ))
    error_count = sum(1 for e in entries if e.level == LogLevel.ERROR)
    warning_count = sum(1 for e in entries if e.level == LogLevel.WARNING)
    importance: str = trr.importance
    if error_count > 0:
        importance = "high"
    elif warning_count > 0:
        importance = "medium"
    return ToolResult(
        tool_name=trr.tool_name,
        category=trr.category,
        importance=importance,
        source_path=trr.source_path or "",
        raw_text="",
        entries=entries,
        stats=ToolResultStats(
            entries_count=len(entries),
            stats=trr.stats if trr.stats else {"error": error_count, "warning": warning_count},
        ),
    )


def _iter_project_dirs(root: Path) -> list[Path]:
    """递归找出真正含日志/源码的目录，避免对空目录也跑一遍 pipeline。"""
    candidates = [root] + sorted(
        p for p in root.rglob("*")
        if p.is_dir() and not any(part.startswith(".") for part in p.relative_to(root).parts)
    )
    return [
        d for d in candidates
        if any(d.glob("*.log")) or any(d.glob("*.tex"))
    ]


def _collect_from_paths(paths: Sequence[str], args: Any) -> list[ToolResult]:
    """从输入路径（文件/目录）收集解析结果，统一返回 ToolResult 列表。"""
    from ..easy import parse_log_file as _parse_log_file

    all_tool_results: list[ToolResult] = []
    for raw in paths or []:
        p = Path(raw)
        if p.is_dir():
            dirs = _iter_project_dirs(p) if getattr(args, "recursive", False) else [p]
            for d in dirs:
                jobname = getattr(args, "jobname", None) or (
                    args.root_file.stem if getattr(args, "root_file", None) else None
                )
                jobname_here = jobname or _find_tex_in_dir(d) or _find_jobname_from_logs(d) or "pytexlogs_default"
                # print_terminal=False：摘要由本 CLI 统一渲染，否则同一条警告会打印两遍
                results = run_pipeline(
                    jobname=jobname_here,
                    auxdir=str(d),
                    print_terminal=False,
                    root_file=str(args.root_file) if getattr(args, "root_file", None) else None,
                )
                for trr in results.tool_results:
                    all_tool_results.append(_tool_result_report_to_tool_result(trr))
        elif p.is_file():
            root = str(args.root_file) if getattr(args, "root_file", None) else None
            parsed = _parse_log_file(p, root_file=root)
            tr = ToolResult(
                tool_name=p.suffix.lstrip(".") or "unknown",
                category="compile",
                importance="high" if parsed.errors else "medium" if parsed.warnings else "low",
                source_path=str(p),
                raw_text=parsed.raw_text,
                entries=parsed.entries,
                stats=ToolResultStats(
                    entries_count=len(parsed.entries),
                    stats={"error": len(parsed.errors), "warning": len(parsed.warnings)},
                ),
            )
            all_tool_results.append(tr)
        else:
            print(f"warning: {p} 不是文件也不是目录，跳过", file=sys.stderr)
    return all_tool_results


def _find_tex_in_dir(d: Path) -> str | None:
    """在目录里找「带 \\documentclass 的 .tex」的 stem；找不到再退回首个 .tex。"""
    candidates = sorted(d.glob("*.tex"))
    for f in candidates:
        try:
            # 只读头部即可判断 \documentclass；不要先把整份大文件读进内存。
            with f.open("r", encoding="utf-8", errors="ignore") as fh:
                head = fh.read(65536)
        except OSError:
            continue
        if "\\documentclass" in head:
            return f.stem
    return candidates[0].stem if candidates else None


def _find_jobname_from_logs(d: Path) -> str | None:
    """目录里没有 .tex 时，用体积最大的 .log 的 stem 作为 jobname。

    Build/Auxiliary 目录通常只有 ``main.log``，这是最常见的场景；取最大的
    那个可以避开 ``latexmk`` 留下的零字节占位日志。
    """
    logs = [p for p in d.glob("*.log") if p.is_file()]
    if not logs:
        return None
    return max(logs, key=lambda p: p.stat().st_size).stem


def _open_entries(entries_info: Sequence[Any], args: Any) -> None:
    """对 ERROR 级别条目尝试打开编辑器跳转（默认只开第一条，--open-all 全开）。"""
    tokens = _detect_editor(getattr(args, "editor", None))
    if not tokens:
        logger.warning("未检测到可用编辑器（--editor=auto 失败），跳过 --open")
        return
    opened = 0
    open_all = bool(getattr(args, "open_all", False))
    for entry, _cat, _tool, _src in entries_info:
        entry_level = getattr(entry, "level", None)
        is_error = False
        if hasattr(entry_level, "value"):
            is_error = entry_level == LogLevel.ERROR
        elif isinstance(entry_level, str):
            is_error = entry_level == "error"
        if not is_error:
            continue
        file = getattr(entry, "file", None) or "unknown.tex"
        line = int(getattr(entry, "line", 0) or 1)
        cmd = _apply_editor_template(tokens, file, line)
        if getattr(args, "dry_run", False):
            print(f"[dry-run open] $ {' '.join(cmd)}", file=sys.stderr)
        else:
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError as exc:
                logger.warning("启动编辑器失败: %s", exc)
        opened += 1
        if not open_all:
            break
    if opened == 0:
        logger.info("没有 ERROR 条目可跳转")


def _aggregate_stats(results: list[ToolResult], group_by: str) -> dict[str, int]:
    """聚合 ToolResult 的统计信息。"""
    stats: dict[str, int] = {}
    for r in results:
        if group_by == "category":
            key = r.category or "unknown"
        elif group_by == "parser":
            key = r.tool_name or "unknown"
        elif group_by == "level":
            err_count = r.stats.stats.get("error", 0)
            warn_count = r.stats.stats.get("warning", 0)
            info_count = r.stats.stats.get("info", 0)
            stats["error"] = stats.get("error", 0) + err_count
            stats["warning"] = stats.get("warning", 0) + warn_count
            stats["info"] = stats.get("info", 0) + info_count
            continue
        else:
            key = "unknown"
        stats[key] = stats.get(key, 0) + 1
    return stats


def _entry_key(level: str, file: str | None, line: int | None, text: str) -> str:
    """条目去重键：等级 + 文件 + 规范化文本。

    刻意不包含 ``line``：正文只在前面插入几行时，同一个问题会换行号，
    但不应被 baseline 当成“新增告警”。行号仍保留在报告和展示中。
    空白归一化避免日志折行差异造成误报。
    """
    normalized = " ".join((text or "").split())
    return f"{level}|{file or ''}|{normalized}"


def _filter_against_baseline(results: list[ToolResult], baseline_path: Path) -> list[ToolResult]:
    """只保留「上次报告里没有」的条目（新增或文本变化的回归）。"""
    from ..core.report import load_report

    report = load_report(baseline_path)
    seen: set[str] = set()
    for tr in report.tool_results:
        for e in tr.entries:
            seen.add(_entry_key(str(e.level), e.file, e.line, e.text))

    filtered: list[ToolResult] = []
    for tr in results:
        kept = [
            e for e in tr.entries
            if _entry_key(
                e.level.value if hasattr(e.level, "value") else str(e.level),
                e.file, e.line, e.text,
            ) not in seen
        ]
        clone = dataclasses.replace(tr, entries=kept)
        clone.stats = ToolResultStats(
            entries_count=len(kept),
            stats={
                **tr.stats.stats,
                "error": sum(1 for e in kept if e.level == LogLevel.ERROR),
                "warning": sum(1 for e in kept if e.level == LogLevel.WARNING),
            },
        )
        filtered.append(clone)
    return filtered


def _default_lang() -> str:
    """按环境变量/系统 locale 选摘要语言，默认中文。"""
    env = os.environ.get("PYTEXLOGS_LANG") or os.environ.get("LANG") or ""
    try:
        sys_lang = locale.getlocale()[0] or ""
    except Exception:
        sys_lang = ""
    if env.lower().startswith("en") or sys_lang.lower().startswith("en"):
        return "en"
    return "zh"


def main(argv: list[str] | None = None) -> int:
    """CLI 主函数：解析参数、执行子命令、返回退出码。"""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    if getattr(args, "completion", None):
        from .completion import render_completion

        # 补全脚本必须是纯文本，不能混入语言/版本/摘要输出。
        sys.stdout.write(render_completion(args.completion, parser))
        return 0

    lang = getattr(args, "lang", None) or _default_lang()
    set_summary_language(lang)

    severity = getattr(args, "severity", "error+warning")
    fmt = getattr(args, "fmt", "text")
    max_entries = getattr(args, "max_entries", None)
    if max_entries is None:
        max_entries = 10
    show_hints = not getattr(args, "no_hints", False)
    min_level = _SEVERITY_LEVEL.get(severity, LogLevel.WARNING)

    try:
        if args.subcmd is None:
            if not getattr(args, "paths", None):
                parser.print_help()
                return 0
            args.subcmd = "check"

        if args.subcmd == "demo":
            from ..integration_demo import run_demo

            run_demo()
            return 0

        if args.subcmd == "explain":
            from ..hints import hint_for_text

            text = " ".join(getattr(args, "text", []) or [])
            if not text:
                print("请给出一段日志文本，例如：pytexlogs explain 'Missing character'")
                return 2
            hint = hint_for_text(
                text,
                jobname=getattr(args, "jobname", None),
                root_file=str(args.root_file) if getattr(args, "root_file", None) else None,
                language=lang,
            )
            if hint is None:
                print("没有匹配到内置建议；可先用 `pytexlogs <log>` 查看条目上下文。")
                return 1
            print(hint.text)
            for cmd in hint.commands:
                print(f"  $ {cmd}")
            return 0

        results = _collect_from_paths(getattr(args, "paths", []), args)
        if not results:
            cwd = Path.cwd()
            if _find_tex_in_dir(cwd):
                results = _collect_from_paths([str(cwd)], args)

        baseline = getattr(args, "baseline", None)
        if baseline:
            results = _filter_against_baseline(results, Path(baseline))

        def _has_errors() -> bool:
            return any(r.stats.stats.get("error", 0) > 0 for r in results)

        def _has_warnings() -> bool:
            return any(r.stats.stats.get("warning", 0) > 0 for r in results)

        entries_info, _min_lvl = _flatten_entries(results, severity)
        filtered_for_output = filter_by_level(results, min_level)

        output_text = ""
        if fmt == "json":
            output_text = to_json(filtered_for_output)
        elif fmt == "csv":
            output_text = to_csv(filtered_for_output)
        elif fmt == "sarif":
            output_text = _json.dumps(to_sarif(filtered_for_output), ensure_ascii=False, indent=2)
        else:
            lines: list[str] = []
            if filtered_for_output:
                stats_c = _aggregate_stats(filtered_for_output, group_by="category")
                stats_p = _aggregate_stats(filtered_for_output, group_by="parser")
                lines.append("=== PyTeXLogs Summary ===")
                if stats_c:
                    lines.append("By category: " + ", ".join(f"{k}={v}" for k, v in stats_c.items()))
                if stats_p:
                    lines.append("By parser:   " + ", ".join(f"{k}={v}" for k, v in stats_p.items()))
                parsed_logs_list = [
                    ParsedLog(
                        entries=list(tr.entries),
                        raw_text="",
                        source_path=tr.source_path,
                        tool_name=tr.tool_name,
                        category=tr.category,
                        importance=tr.importance,
                        stats=tr.stats.stats,
                    )
                    for tr in filtered_for_output
                ]
                with _w.catch_warnings():
                    _w.simplefilter("ignore", DeprecationWarning)
                    # stream=StringIO：禁止 print_summary 直接写 stdout，否则它自己
                    # 打印一遍、我们再把返回值拼进 output_text，等于同条警告两遍。
                    summary_str = print_summary(
                        parsed_logs_list,
                        use_logger=False,
                        non_quiet=min_level != LogLevel.ERROR,
                        max_entries=max_entries or None,
                        show_hints=show_hints,
                        language=lang,
                        stream=io.StringIO(),
                    )
                lines.append(summary_str.rstrip())
            else:
                lines.append("（无解析结果。请传入 .log / .blg 或 aux 目录）")
            output_text = "\n".join(lines)

        if getattr(args, "output", None) is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output_text, encoding="utf-8")
        else:
            sys.stdout.write(output_text)
            if not output_text.endswith("\n"):
                sys.stdout.write("\n")

        if getattr(args, "do_open", False):
            _open_entries(entries_info, args)

        if args.subcmd == "check":
            fail_on = getattr(args, "fail_on", "error")
            if fail_on == "warning":
                return 1 if (_has_errors() or _has_warnings()) else 0
            return 1 if _has_errors() else 0
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception:
        logger.exception("CLI 异常")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
