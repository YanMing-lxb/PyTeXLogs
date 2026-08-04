"""CLI 主入口：解析参数、调度子命令、输出结果。"""

import json as _json
import logging
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
from ..exporters.json_exporter import to_json
from ..exporters.sarif_exporter import to_sarif
from .args import (
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


def _collect_from_paths(paths: Sequence[str], args: Any) -> list[ToolResult]:
    """从输入路径（文件/目录）收集解析结果，统一返回 ToolResult 列表。"""
    from ..easy import parse_log_file as _parse_log_file

    all_tool_results: list[ToolResult] = []
    for raw in paths or []:
        p = Path(raw)
        if p.is_dir():
            jobname = args.root_file.stem if args.root_file else None
            jobname_here = jobname or _find_tex_in_dir(p)
            results = run_pipeline(jobname=jobname_here or "pytexlogs_default", auxdir=str(p))
            for trr in results.tool_results:
                all_tool_results.append(_tool_result_report_to_tool_result(trr))
        elif p.is_file():
            root = str(args.root_file) if args.root_file else None
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
    """在目录中查找第一个 .tex 文件的 stem。"""
    for f in sorted(d.glob("*.tex")):
        return f.stem
    return None


def _open_entries(entries_info: Sequence[Any], args: Any) -> None:
    """对 ERROR 级别条目尝试打开编辑器跳转。"""
    tokens = _detect_editor(args.editor)
    if not tokens:
        logger.warning("未检测到可用编辑器（--editor=auto 失败），跳过 --open")
        return
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
        line = getattr(entry, "line", None)
        line = max(1, line if line is not None else 1)
        cmd = _apply_editor_template(tokens, file, line)
        if args.dry_run:
            print(f"[dry-run open] $ {' '.join(cmd)}", file=sys.stderr)
            continue
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            logger.warning("无法启动编辑器命令 %r: %s", " ".join(cmd), exc)


def _tool_results_to_parsed_logs(results: Sequence[Any]) -> list[ParsedLog]:
    """将 ToolResult 列表转换为 ParsedLog 列表。"""
    parsed_logs_list: list[ParsedLog] = []
    for r in results:
        stats_obj = getattr(r, "stats", None)
        stats_dict = getattr(stats_obj, "stats", {}) if stats_obj is not None else {}
        pl = ParsedLog(
            entries=getattr(r, "entries", []),
            raw_text=getattr(r, "raw_text", ""),
            source_path=getattr(r, "source_path", ""),
            tool_name=getattr(r, "tool_name", ""),
            category=getattr(r, "category", ""),
            importance=getattr(r, "importance", "low"),
            stats=stats_dict,
        )
        parsed_logs_list.append(pl)
    return parsed_logs_list


def main(argv: list[str] | None = None) -> int:
    """CLI 主函数：解析参数、执行子命令、返回退出码。"""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    set_summary_language(args.lang or "zh")

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

        results = _collect_from_paths(getattr(args, "paths", []), args)
        if not results:
            cwd = Path.cwd()
            if _find_tex_in_dir(cwd):
                results = _collect_from_paths([str(cwd)], args)

        def _has_errors() -> bool:
            return any(r.stats.stats.get("error", 0) > 0 for r in results)

        entries_info, _min_lvl = _flatten_entries(results, args.severity)

        output_text = ""
        if args.fmt == "json":
            output_text = to_json(results)
        elif args.fmt == "csv":
            output_text = to_csv(results)
        elif args.fmt == "sarif":
            output_text = _json.dumps(to_sarif(results), ensure_ascii=False, indent=2)
        else:
            lines: list[str] = []
            if results:
                lines.append("=== PyTeXLogs Summary ===")
                stats_c = _aggregate_stats(results, group_by="category")
                stats_p = _aggregate_stats(results, group_by="parser")
                stats_l = _aggregate_stats(results, group_by="level")
                lines.append("By category: " + ", ".join(f"{k}={v}" for k, v in stats_c.items()) or "(empty)")
                lines.append("By parser:   " + ", ".join(f"{k}={v}" for k, v in stats_p.items()) or "(empty)")
                lines.append("By level:    " + ", ".join(f"{k}={v}" for k, v in stats_l.items()) or "(empty)")
                for entry, cat, tool, src in entries_info:
                    level_str = entry.level.value if hasattr(entry.level, "value") else str(entry.level)
                    lines.append(
                        f"[{level_str.upper():7s}] {entry.file}:{entry.line} "
                        f"({cat}/{tool}) {entry.text}"
                    )
                lines.append("---")
                with _w.catch_warnings():
                    _w.simplefilter("ignore", DeprecationWarning)
                    parsed_logs_list = _tool_results_to_parsed_logs(results)
                    summary_str = print_summary(parsed_logs_list, use_logger=False, non_quiet=True)
                    lines.append(summary_str.rstrip())
            else:
                lines.append("（无解析结果。请传入 .log / .blg 或 aux 目录）")
            output_text = "\n".join(lines)

        if args.output is not None:
            args.output.write_text(output_text, encoding="utf-8")
        else:
            sys.stdout.write(output_text)
            if not output_text.endswith("\n"):
                sys.stdout.write("\n")

        if args.do_open:
            _open_entries(entries_info, args)

        if args.subcmd == "check":
            return 1 if _has_errors() else 0
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception:
        logger.exception("CLI 异常")
        return 2


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


if __name__ == "__main__":
    raise SystemExit(main())