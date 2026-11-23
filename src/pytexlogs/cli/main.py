"""CLI 主入口：解析参数、调度子命令、输出结果。

0.5.0 的修正：
- 目录模式不再触发 ``run_pipeline`` 自带摘要，避免同一条警告打印 2~3 遍；
- ``--severity`` 同时作用于 text/json/csv/sarif（此前只有文本生效）；
- ``--baseline`` 只输出“本次新增/恶化”的条目，适合写作期盯回归；
- ``--fail-on`` 让 CI 能在出现 warning 时也失败。
"""

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
from ..core.models import (
    LogEntry,
    LogLevel,
    ParsedLog,
    ToolResultReport,
    level_from_value,
)
from ..core.stats import recompute_stats
from ..display import CATEGORY_LABEL, print_summary, set_summary_language
from ..display.formatter import _t as _summary_t
from ..display.formatter import display_width, resolve_summary_width
from ..exporters.csv_exporter import to_csv
from ..exporters.json_exporter import filter_by_level, to_json
from ..exporters.sarif_exporter import to_sarif
from .args import (
    _SEVERITY_LEVEL,
    _apply_editor_template,
    _detect_editor,
    _flatten_entries,
    _normalize_argv,
    build_parser,
)

__all__ = ["main"]

logger = logging.getLogger("pytexlogs.cli")

#: CLI 面向用户的提示文案（中英双语；`--lang en` 下不应再冒出中文）。
_MSG: dict[str, dict[str, str]] = {
    "zh": {
        "explain_empty": "请给出一段日志文本，例如：pytexlogs explain 'Missing character'",
        "explain_none": "没有匹配到内置建议；可先用 `pytexlogs <log>` 查看条目上下文。",
        "no_results": "（无解析结果。请传入 .log / .blg 或 aux 目录）",
        "no_new_entries": "（没有新增条目：--baseline/--severity 过滤后为空）",
        "parse_failures_header": "=== 解析失败 ===",
        "parse_failures_only": "存在解析失败，见上方解析失败列表",
        "parse_failure_warning": "warning: {tool} 解析失败: {type}: {msg}",
        "baseline_missing": "基线报告不存在：{path}（先用 --output 导出一次 JSON 报告）",
        "cli_error": "pytexlogs 执行失败：{type}: {msg}（设置 PYTEXLOGS_DEBUG=1 可查看堆栈）",
        "summary_title": "PyTeXLogs 摘要",
        "n_entries": "{n} 条",
        "n_errors": "{n} 个错误",
        "n_warnings": "{n} 个警告",
        "n_hints": "{n} 个提示",
        "by_category": "按类别",
        "by_parser": "按解析器",
        "colon": "：",
    },
    "en": {
        "explain_empty": "Provide a log snippet, e.g. pytexlogs explain 'Missing character'",
        "explain_none": "No built-in hint matched; run `pytexlogs <log>` to inspect entry context first.",
        "no_results": "(no parse result: pass a .log / .blg file or an aux directory)",
        "no_new_entries": "(no new entries: everything was filtered out by --baseline/--severity)",
        "parse_failures_header": "=== Parse Failures ===",
        "parse_failures_only": "Parse failures occurred; see the parse failures list above",
        "parse_failure_warning": "warning: failed to parse {tool}: {type}: {msg}",
        "baseline_missing": "Baseline report not found: {path} (export a JSON report with --output first)",
        "cli_error": "pytexlogs failed: {type}: {msg} (set PYTEXLOGS_DEBUG=1 for a traceback)",
        "summary_title": "PyTeXLogs",
        "n_entries": "{n} entries",
        "n_errors": "{n} errors",
        "n_warnings": "{n} warnings",
        "n_hints": "{n} hints",
        "by_category": "By category",
        "by_parser": "By parser",
        "colon": ": ",
    },
}


def _msg(key: str, lang: str | None = None, **fields: str) -> str:
    """取本地化提示文案；未知语言回退中文。"""
    table = _MSG.get((lang or "zh").lower(), _MSG["zh"])
    return table[key].format(**fields)


def _warn_parse_failures(failures: Sequence[tuple[str, dict[str, str]]], lang: str) -> None:
    """CSV/SARIF 没有条目行可承载失败信息，改写 stderr，保证 stdout 载荷干净。"""
    for tool, exc in failures:
        print(
            _msg(
                "parse_failure_warning",
                lang,
                tool=tool,
                type=exc.get("type") or "Error",
                msg=exc.get("message") or "",
            ),
            file=sys.stderr,
        )


def _configure_logging() -> None:
    """CLI 入口配置一次 stderr 日志，保证异常至少有可见输出。

    handler 必须挂在 ``pytexlogs`` 根 logger 上：引擎/解析器用
    ``pytexlogs.core.*`` / ``pytexlogs.parsers.*``，挂在 ``pytexlogs.cli`` 上再
    ``propagate=False`` 会让它们的 debug/info 永远继承到 root 的 WARNING。
    """
    root = logging.getLogger("pytexlogs")
    level = logging.DEBUG if os.environ.get("PYTEXLOGS_DEBUG") else logging.WARNING
    if root.handlers:
        root.setLevel(level)
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def _as_parsed_logs(results: list[ToolResultReport]) -> list[ParsedLog]:
    """报告模型 → 展示模型（``print_summary`` 需要枚举等级的 ``LogEntry``）。

    只服务展示层：导出（json/csv/sarif）与聚合都直接用报告模型，不再经这一层，
    因此这里只做一次最小转换，不承担任何统计/排序职责。
    """
    return [
        ParsedLog(
            entries=[
                LogEntry(
                    level=level_from_value(e.level),
                    file=e.file or "",
                    line=e.line or 0,
                    text=e.text or "",
                    error_pos_text=e.error_pos_text or "",
                )
                for e in tr.entries
            ],
            raw_text="",
            source_path=tr.source_path or "",
            tool_name=tr.tool_name,
            category=tr.category,
            importance=tr.importance,
            stats=dict(tr.stats),
        )
        for tr in results
    ]


def _iter_project_dirs(root: Path) -> list[Path]:
    """递归找出真正含日志/源码的目录，避免对空目录也跑一遍 pipeline。

    3.15 的 ``Path.walk`` 允许在遍历时裁剪 hidden 子目录，比先 ``rglob`` 出
    全部节点再过滤更直接；排序保持确定，避免不同文件系统返回顺序影响批量输出。
    """
    candidates: list[Path] = []
    for directory, dirnames, _files in root.walk():
        dirnames[:] = [name for name in dirnames if not name.startswith(".")]
        if any(directory.glob("*.log")) or any(directory.glob("*.tex")):
            candidates.append(directory)
    return sorted(candidates, key=lambda p: (p != root, p.as_posix()))


def _collect_from_paths(paths: Sequence[str], args: Any) -> list[ToolResultReport]:
    """从输入路径（文件/目录）收集解析结果。

    CLI 的规范类型是**报告模型**（``ToolResultReport``）：``run_pipeline`` 本来
    就产出它，单文件解析（``easy.parse_log_file``）再经
    ``ToolResultReport.from_parsed_log`` 折进来。0.5 在这里多绕了一层
    ``ToolResultReport → ToolResult → 再转回 dict``，同一份数据被抄了三遍。
    """
    from ..easy import parse_log_file as _parse_log_file

    all_results: list[ToolResultReport] = []
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
                all_results.extend(results.tool_results)
        elif p.is_file():
            root = str(args.root_file) if getattr(args, "root_file", None) else None
            parsed = _parse_log_file(p, root_file=root)
            all_results.append(ToolResultReport.from_parsed_log(parsed))
        else:
            print(f"warning: {p} 不是文件也不是目录，跳过", file=sys.stderr)
    return all_results


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

    def _size(path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return -1

    return max(logs, key=_size).stem


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


def _aggregate_stats(results: list[ToolResultReport], group_by: str) -> dict[str, int]:
    """聚合报告结果的统计信息（按 category / parser / level 计数）。

    口径与 :func:`pytexlogs.aggregate_stats` 完全一致：category/parser 按条目数
    聚合（不是工具结果 +1），level 动态覆盖全部等级（含 font/graphic/page）。
    这里直接委托 easy 层，避免 CLI 与便捷 API 各维护一张计数表再次漂移。
    """
    from ..easy import aggregate_stats

    return aggregate_stats(results, group_by=group_by)  # type: ignore[arg-type]


def _entry_key(level: str, file: str | None, line: int | None, text: str) -> str:
    """条目去重键：等级 + 文件 + 规范化文本。

    刻意不包含 ``line``：正文只在前面插入几行时，同一个问题会换行号，
    但不应被 baseline 当成“新增告警”。行号仍保留在报告和展示中。
    空白归一化避免日志折行差异造成误报。
    """
    normalized = " ".join((text or "").split())
    return f"{level}|{file or ''}|{normalized}"


def _filter_against_baseline(results: list[ToolResultReport], baseline_path: Path) -> list[ToolResultReport]:
    """只保留「上次报告里没有」的条目（新增或文本变化的回归）。"""
    from ..core.report import load_report

    report = load_report(baseline_path)
    seen: set[str] = set()
    for tr in report.tool_results:
        for e in tr.entries:
            seen.add(_entry_key(str(e.level), e.file, e.line, e.text))

    filtered: list[ToolResultReport] = []
    for tr in results:
        kept = [e for e in tr.entries if _entry_key(str(e.level), e.file, e.line, e.text) not in seen]
        stats = dict(tr.stats)
        recompute_stats(kept, stats)
        filtered.append(dataclasses.replace(tr, entries=kept, stats=stats))
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
    _configure_logging()
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        # 裸路径（``pytexlogs main.log``）在解析前补成 ``check main.log``：
        # 顶层 parser 没有 paths 位置参数，否则会以 invalid choice 退出。
        args = parser.parse_args(_normalize_argv(raw_argv))
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
    # --severity info/all 已经让过滤层保留提示级；展示层必须同步打开，
    # 否则用户看到“按 info 过滤”却只有 error/warning 两组。
    show_info = min_level.severity >= LogLevel.INFO.severity

    try:
        if args.subcmd is None:
            parser.print_help()
            return 0

        if args.subcmd == "demo":
            from ..integration_demo import run_demo

            run_demo(getattr(args, "width", None))
            return 0

        if args.subcmd == "explain":
            from ..hints import hint_for_text

            text = " ".join(getattr(args, "text", []) or [])
            if not text:
                print(_msg("explain_empty", lang), file=sys.stderr)
                return 2
            hint = hint_for_text(
                text,
                jobname=getattr(args, "jobname", None),
                root_file=str(args.root_file) if getattr(args, "root_file", None) else None,
                language=lang,
                tool_name=getattr(args, "tool", None),
            )
            if hint is None:
                print(_msg("explain_none", lang), file=sys.stderr)
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
            if not Path(baseline).exists():
                # 早退而不是让 FileNotFoundError 冒到顶层：后者会打出“CLI 异常”
                # 与堆栈，用户看不到真正的原因（路径写错还是没导出过）。
                print(_msg("baseline_missing", lang, path=str(baseline)), file=sys.stderr)
                return 2
            results = _filter_against_baseline(results, Path(baseline))

        def _has_errors() -> bool:
            return any(r.errors for r in results)

        def _has_warnings() -> bool:
            return any(r.warnings for r in results)

        entries_info, _min_lvl = _flatten_entries(results, severity)
        # 被 --severity / --baseline 过滤到空的解析结果不再占一行统计：
        # 否则摘要会打印 "By category: compile=1" 却一条条目都没有，看着像解析成功。
        # 但解析失败（parse_exception 非空、entries 为空）必须保留：它是用户与 CI
        # 唯一能看到解析器崩溃的信号，不能因为“没有条目”被静默丢弃。
        filtered_for_output = [r for r in filter_by_level(results, min_level) if r.entries or r.parse_exception]
        parse_failures: list[tuple[str, dict[str, str]]] = []
        for _result in filtered_for_output:
            if _result.parse_exception:
                parse_failures.append((_result.tool_name or "unknown", _result.parse_exception))
        has_displayable_entries = any(r.entries for r in filtered_for_output)

        output_text = ""
        if fmt == "json":
            output_text = to_json(filtered_for_output, language=lang, include_hints=show_hints)
        elif fmt == "csv":
            output_text = to_csv(filtered_for_output, language=lang, include_hints=show_hints)
            _warn_parse_failures(parse_failures, lang)
        elif fmt == "sarif":
            output_text = _json.dumps(
                to_sarif(filtered_for_output, language=lang, include_hints=show_hints),
                ensure_ascii=False,
                indent=2,
            )
            _warn_parse_failures(parse_failures, lang)
        else:
            lines: list[str] = []
            layout_width = resolve_summary_width(getattr(args, "width", None))
            if has_displayable_entries:
                # 只统计真正有展示条目的结果；解析失败的 0 条目结果不应
                # 冒出一行 "compile=0"。
                stats_c = {k: v for k, v in _aggregate_stats(filtered_for_output, group_by="category").items() if v}
                stats_p = {k: v for k, v in _aggregate_stats(filtered_for_output, group_by="parser").items() if v}
                level_stats = _aggregate_stats(filtered_for_output, group_by="level")
                n_errors = level_stats.get("error", 0)
                n_warnings = level_stats.get("warning", 0)
                n_hints = sum(v for k, v in level_stats.items() if k not in ("error", "warning"))
                total_entries = sum(level_stats.values())

                def _append_segments(prefix: str, segments: list[str]) -> None:
                    """统计行以「段」为最小单位折行，避免把 ``3 个警告`` 拆开。

                    续行缩进与首行正文起始列对齐；段之间用 `` · `` 连接。
                    """
                    continuation = " " * display_width(prefix)
                    line = prefix + segments[0]
                    for segment in segments[1:]:
                        candidate = f"{line} · {segment}"
                        if display_width(candidate) <= layout_width:
                            line = candidate
                        else:
                            lines.append(line)
                            line = continuation + segment
                    lines.append(line)

                header_segments = [
                    _msg("n_entries", lang, n=total_entries),
                    _msg("n_errors", lang, n=n_errors),
                    _msg("n_warnings", lang, n=n_warnings),
                ]
                if n_hints:
                    header_segments.append(_msg("n_hints", lang, n=n_hints))
                _append_segments(f"{_msg('summary_title', lang)} · ", header_segments)

                if stats_c:
                    _append_segments(
                        f"  {_msg('by_category', lang)}{_msg('colon', lang)}",
                        [f"{_summary_t(CATEGORY_LABEL.get(k, k))} {v}" for k, v in stats_c.items()],
                    )
                if stats_p:
                    _append_segments(
                        f"  {_msg('by_parser', lang)}{_msg('colon', lang)}",
                        [f"{k} {v}" for k, v in stats_p.items()],
                    )
                parsed_logs_list = _as_parsed_logs(filtered_for_output)
                hint_jobname = getattr(args, "jobname", None)
                if not hint_jobname:
                    # 单文件/目录输入通常没有显式 --jobname；从 source_path 的
                    # 文件名推断 main，避免 hint 使用子文件 intro.tex 当 jobname。
                    for _result in filtered_for_output:
                        if _result.source_path:
                            hint_jobname = Path(_result.source_path).stem
                            break
                hint_root_file = str(args.root_file) if getattr(args, "root_file", None) else None
                with _w.catch_warnings():
                    _w.simplefilter("ignore", DeprecationWarning)
                    # stream=StringIO：禁止 print_summary 直接写 stdout，否则它自己
                    # 打印一遍、我们再把返回值拼进 output_text，等于同条警告两遍。
                    summary_str = print_summary(
                        parsed_logs_list,
                        use_logger=False,
                        non_quiet=min_level != LogLevel.ERROR,
                        show_info=show_info,
                        max_entries=max_entries or None,
                        show_hints=show_hints,
                        language=lang,
                        jobname=hint_jobname,
                        root_file=hint_root_file,
                        stream=io.StringIO(),
                        width=layout_width,
                    )
                lines.append(summary_str.rstrip())
            if parse_failures:
                lines.append(_msg("parse_failures_header", lang))
                lines.extend(
                    f"{tool}: {exc.get('type') or 'Error'}: {exc.get('message') or ''}" for tool, exc in parse_failures
                )
                if not has_displayable_entries:
                    lines.append(_msg("parse_failures_only", lang))
            elif not filtered_for_output:
                lines.append(_msg("no_new_entries" if results else "no_results", lang))
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
    except Exception as exc:  # noqa: BLE001 — CLI 顶层兜底：必须给用户可见诊断
        logger.exception("CLI 异常")
        print(
            _msg("cli_error", lang, type=type(exc).__name__, msg=str(exc)),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
