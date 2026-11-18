"""日志解析流水线门面：对外暴露 run_pipeline 作为唯一入口。"""

import logging
import re
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..display.printer import print_summary
from .logkind import plan_default_steps
from .manager import LogParserManager
from .models import (
    REPORT_SCHEMA_VERSION,
    ConfigIgnoredReport,
    LogEntry,
    LogLevel,
    ParsedLog,
    ParsedPipelineReport,
    PipelineMeta,
    ReferencesReport,
    ReportEntry,
    ToolResultReport,
    level_from_value,
)
from .reftracker import RefChangeTracker

logger = logging.getLogger(__name__)

#: 合法等级字符串集合：直接由枚举派生，报告与统计共用同一口径。
_LEVEL_VALUES: frozenset[str] = frozenset(level.value for level in LogLevel)


def run_pipeline(
    jobname: str | None = None,
    auxdir: str | Path | None = None,
    steps: list[str] | None = None,
    captured_outputs: dict[str, str] | None = None,
    ignore_patterns: list[str] | None = None,
    project_config: dict[str, Any] | None = None,
    root_file: str | None = None,
    write_report_file: bool = False,
    report_path: str | Path | None = None,
    print_terminal: bool | None = None,
    ref_tracker_translate_fn: Callable[[str], str] | None = None,
    pytexmk_version: str | None = None,
    text_len_fn: Callable[[str], int] | None = None,
    *,
    language: str | None = None,
    summary_max_entries: int | None = None,
) -> ParsedPipelineReport:
    """入口函数：日志发现 → 解析 → 汇总 → 终端打印 → 报告写盘 → 返回结构化报告。

    0.6.1 起只保留这一套签名：0.4/0.5 的 ``tex_engine/tex_output/bibtex_output/
    biber_output/other_engine_outputs/quiet`` 旧位置参数与 ``write_report`` 旧名
    已删除，调用方需统一用 ``steps`` + ``captured_outputs`` + ``write_report_file``。
    """
    if captured_outputs is None:
        captured_outputs = {}

    if jobname is None or auxdir is None:
        _td: Path | None = Path(tempfile.mkdtemp(prefix="pytexlogs_aux_"))
        jobname = jobname or "pytexlogs_default_job"
        auxdir = auxdir or str(_td)
    else:
        _td = None

    try:
        effective_pytexmk_version = pytexmk_version or "unknown"
        if steps is None:
            # 按实际存在的日志文件规划，避免同一份 .blg/.ilg/.log 被多个 parser 重复消费
            steps = plan_default_steps(jobname, auxdir)
        if print_terminal is None:
            print_terminal = True
        return _run_pipeline_impl(
            jobname=jobname,
            auxdir=auxdir,
            steps=steps,
            captured_outputs=captured_outputs,
            ignore_patterns=ignore_patterns,
            project_config=project_config,
            root_file=root_file,
            write_report_file=write_report_file,
            report_path=report_path,
            print_terminal=print_terminal,
            ref_tracker_translate_fn=ref_tracker_translate_fn,
            pytexmk_version=effective_pytexmk_version,
            text_len_fn=text_len_fn,
            language=language,
            summary_max_entries=summary_max_entries,
        )
    finally:
        if _td is not None:
            import shutil as _sh
            _sh.rmtree(_td, ignore_errors=True)


def _entry_to_report(entry: Any) -> ReportEntry:
    """把运行时条目对象统一转成报告条目（唯一的 LogEntry → ReportEntry 转换点）。

    0.6.1 起不再接受"解析器返回 dict 条目"的旧形态：内置解析器都返回
    ``LogEntry``，dict 兼容层只会掩盖第三方解析器的类型错误。
    """
    if isinstance(entry, ReportEntry):
        return entry
    level = getattr(entry, "level", "info")
    level = getattr(level, "value", level)
    level_str = str(level)
    if level_str not in _LEVEL_VALUES:
        level_str = "info"
    line = getattr(entry, "line", None)
    return ReportEntry(
        level=level_str,
        file=getattr(entry, "file", None) or None,
        line=int(line) if line is not None else None,
        text=getattr(entry, "text", "") or "",
        error_pos_text=getattr(entry, "error_pos_text", None) or None,
    )


def _run_pipeline_impl(
    jobname: str,
    auxdir: str | Path,
    steps: list[str],
    captured_outputs: dict[str, str],
    ignore_patterns: list[str] | None,
    project_config: dict[str, Any] | None,
    root_file: str | None,
    write_report_file: bool,
    report_path: str | Path | None,
    print_terminal: bool,
    ref_tracker_translate_fn: Callable[[str], str] | None,
    pytexmk_version: str,
    text_len_fn: Callable[[str], int] | None,
    language: str | None = None,
    summary_max_entries: int | None = None,
) -> ParsedPipelineReport:

    auxdir_path = Path(auxdir)
    auxdir_path.mkdir(parents=True, exist_ok=True)

    captured_outputs = captured_outputs or {}
    ignore_patterns = ignore_patterns or []
    project_config = project_config or {}

    t0 = time.perf_counter()
    manager = LogParserManager()

    skipped_steps: list[str] = []
    tool_reports: list[ToolResultReport] = []
    # 已消费的日志文件：同一份 .blg/.ilg/.log 只允许一个 step 解析，
    # 防止自定义 steps 列表里同时出现 bibtex/biber 时统计翻倍。
    consumed_paths: dict[Path, str] = {}

    for step in steps:
        spec = manager.registry.lookup(step)
        if spec is None:
            skipped_steps.append(step)
            continue

        log_text: str | None = None
        log_path: Path | None = None

        if step in captured_outputs:
            log_text = captured_outputs[step]
            log_path = None
        else:
            log_path = spec.default_discover(jobname, auxdir_path)
            if log_path is not None:
                try:
                    resolved = log_path.resolve()
                except OSError:
                    resolved = log_path
                if resolved in consumed_paths:
                    logger.debug(
                        "step %s 的日志 %s 已被 step %s 消费，跳过以避免重复解析",
                        step, log_path, consumed_paths[resolved],
                    )
                    skipped_steps.append(step)
                    continue
                consumed_paths[resolved] = step
                try:
                    log_text = spec.parser_cls(root_file=root_file)._read_log_text(log_path)
                except OSError:
                    log_text = None

        if log_text is None:
            skipped_steps.append(step)
            continue

        parse_exception: dict[str, str] | None = None
        parsed: ParsedLog | None = None

        try:
            parsed = spec.parser_cls(root_file=root_file).parse(log_text, root_file=root_file)
        except Exception as exc:  # noqa: BLE001 — 单个解析器崩溃不能中断整条流水线
            logger.warning("step %s 解析失败: %s", step, exc, exc_info=True)
            parse_exception = {"type": type(exc).__name__, "message": str(exc)}

        entries = list(parsed.entries) if isinstance(parsed, ParsedLog) else []
        report_entries = [_entry_to_report(entry) for entry in entries]

        stats: dict[str, Any] = {}
        if isinstance(parsed, ParsedLog) and isinstance(parsed.stats, dict):
            stats.update(parsed.stats)
        level_counts = Counter(entry.level for entry in report_entries)
        stats.update(dict(level_counts))
        stats["entries_count"] = len(report_entries)

        tool_report = ToolResultReport(
            tool_name=step,
            category=spec.category,
            importance=spec.importance,
            source_path=str(log_path) if log_path else None,
            entries=report_entries,
            stats=stats,
            parse_exception=parse_exception,
        )
        tool_reports.append(tool_report)

    duration_ms = int((time.perf_counter() - t0) * 1000)
    pipeline_meta = PipelineMeta(
        total_steps=len(steps),
        attempted_steps=len(steps) - len(skipped_steps),
        skipped_steps=skipped_steps,
        duration_ms=duration_ms,
    )

    ref_report = ReferencesReport()
    ref_added: list[str] = []
    ref_removed: list[str] = []
    ref_current_keys: list[str] = []
    ref_key_counts: dict[str, int] = {}
    try:
        tracker = RefChangeTracker(auxdir_path, jobname, translate_fn=ref_tracker_translate_fn)
        raw_keys, ref_key_counts = tracker.extract_current_with_counts()
        old_keys = tracker.load_cache()
        diff = tracker.diff(raw_keys, old_keys)
        ref_added = sorted(diff.get('added', set()))
        ref_removed = sorted(diff.get('removed', set()))
        ref_unchanged = sorted(diff.get('unchanged', set()))
        ref_current_keys = sorted(set(raw_keys))
        ref_report = ReferencesReport(
            current_keys=ref_current_keys,
            added=ref_added,
            removed=ref_removed,
            unchanged=ref_unchanged,
            key_counts=ref_key_counts,
            top_cited=[
                {"key": k, "count": c}
                for k, c in Counter(ref_key_counts).most_common(10)
            ],
        )
        try:
            tracker.save_cache(ref_current_keys, key_counts=ref_key_counts)
        except Exception as _e:
            logger.debug("保存参考文献缓存失败（不影响主流程）: %s", _e)
    except Exception as e:
        logger.warning("参考文献跟踪失败: %s", e, exc_info=True)
        ref_report = ReferencesReport()

    severity_counts: dict[str, dict[str, int]] = {}
    # 分级桶按枚举动态生成：0.5 只写死 error/warning/typesetting/info，
    # 导致 font/graphic/page 条目进了 total 却没有自己的桶，统计自相矛盾。
    _empty_buckets = {**{value: 0 for value in _LEVEL_VALUES}, "total": 0}
    for tool in tool_reports:
        cat = tool.category
        bucket = severity_counts.setdefault(cat, dict(_empty_buckets))
        for _se in tool.entries:
            lvl = _se.level
            if lvl in bucket:
                bucket[lvl] += 1
            bucket["total"] += 1

    config_ignored_report = ConfigIgnoredReport(
        ignore_patterns=list(ignore_patterns),
        suppressed_entries=[],
        original_severity_counts={},
    )

    if ignore_patterns:
        original_severity_counts = deepcopy(severity_counts)
        config_ignored_report.original_severity_counts = original_severity_counts

        compiled_patterns = [re.compile(p) for p in ignore_patterns]

        for tool in tool_reports:
            cat = tool.category
            remaining_entries: list[ReportEntry] = []
            for _te in tool.entries:
                suppressed = False
                for p in compiled_patterns:
                    if p.search(_te.text):
                        suppressed = True
                        break
                if suppressed:
                    config_ignored_report.suppressed_entries.append(_te)
                    lvl = _te.level
                    if cat in severity_counts and lvl in severity_counts[cat]:
                        severity_counts[cat][lvl] -= 1
                    if cat in severity_counts:
                        severity_counts[cat]['total'] -= 1
                else:
                    remaining_entries.append(_te)
            tool.entries = remaining_entries
            tool.stats['entries_count'] = len(remaining_entries)

    report = ParsedPipelineReport(
        schema_version=REPORT_SCHEMA_VERSION,
        generated_at=datetime.now(tz=UTC).isoformat(),
        pytexmk_version=pytexmk_version,
        jobname=jobname,
        root_file=root_file or '',
        auxdir=str(auxdir_path),
        pipeline=pipeline_meta,
        severity_counts=severity_counts,
        tool_results=tool_reports,
        references=ref_report,
        config_ignored=config_ignored_report,
        custom_fields={},
    )

    if print_terminal:
        parsed_logs_for_summary: list[ParsedLog] = []
        for tool in tool_reports:
            plog_entries = [
                LogEntry(
                    level=level_from_value(entry.level),
                    file=entry.file or "",
                    line=entry.line if entry.line is not None else 0,
                    text=entry.text,
                    error_pos_text=entry.error_pos_text or "",
                )
                for entry in tool.entries
            ]
            plog = ParsedLog(
                entries=plog_entries,
                raw_text='',
                source_path=tool.source_path or '',
                tool_name=tool.tool_name,
                category=tool.category,
                importance=tool.importance,
                stats=tool.stats,
            )
            parsed_logs_for_summary.append(plog)

        print_summary(
            parsed_logs_for_summary,
            use_logger=False,
            non_quiet=True,
            ref_change_report=None,
            ref_added_keys=ref_added,
            ref_removed_keys=ref_removed,
            ref_total=len(ref_current_keys),
            ref_unchanged=len(ref_unchanged),
            ref_key_counts=ref_key_counts,
            text_len_fn=text_len_fn,
            language=language,
            max_entries=summary_max_entries,
        )

    if write_report_file:
        from .report import write_report as _write_report

        default_report_path = auxdir_path / f"{jobname}.pytexmk-report.json"
        actual_path = Path(report_path) if report_path else default_report_path
        try:
            result_path = _write_report(report, actual_path)
        except Exception:  # 报告写盘失败不能影响编译主流程
            logger.warning("报告写入失败: %s", actual_path, exc_info=True)
            result_path = None
        if result_path is not None:
            report.custom_fields['_report_path'] = str(result_path)

    return report
