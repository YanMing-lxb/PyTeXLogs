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
from .logkind import _append_captured_steps, plan_default_steps
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
from .stats import recompute_stats

logger = logging.getLogger(__name__)

#: 合法等级字符串集合：直接由枚举派生，报告与统计共用同一口径。
_LEVEL_VALUES: frozenset[str] = frozenset(level.value for level in LogLevel)


def _compile_ignore_patterns(
    ignore_patterns: list[str],
) -> list[re.Pattern[str]]:
    """逐项编译忽略正则；非法项（``re.error``）记 warning 后跳过，不崩流水线。

    报告里的 ``config_ignored.ignore_patterns`` 仍保留用户请求的原始列表；
    非法项只是不参与过滤。
    """
    compiled: list[re.Pattern[str]] = []
    for raw in ignore_patterns:
        try:
            compiled.append(re.compile(raw))
        except re.error as exc:
            logger.warning("忽略规则 %r 不是合法正则，已跳过: %s", raw, exc)
    return compiled


def _infer_jobname(auxdir: str | Path, root_file: str | None) -> str | None:
    """未显式给 jobname 时，从 root_file 或 auxdir 里的真实产物推断。

    目录里通常同时有 ``main.tex`` 与 ``main.log``。优先 ``.log`` 是因为日志
    文件名就是编译 jobname；没有日志时再看带 ``\\documentclass`` 的 ``.tex``。
    """
    if root_file:
        return Path(root_file).stem

    aux = Path(auxdir)
    if not aux.is_dir():
        return None

    main_log = aux / "main.log"
    if main_log.is_file():
        return main_log.stem

    logs = sorted(
        (p for p in aux.glob("*.log") if p.is_file()),
        key=lambda p: p.name,
    )
    if logs:
        return logs[0].stem

    tex_files = sorted((p for p in aux.glob("*.tex") if p.is_file()), key=lambda p: p.name)
    for tex in tex_files:
        try:
            with tex.open(encoding="utf-8", errors="ignore") as f:
                head = f.read(65536)
        except OSError:
            continue
        if "\\documentclass" in head:
            return tex.stem
    return tex_files[0].stem if tex_files else None


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
    summary_max_entries: int | None = 20,
    summary_width: int | None = None,
) -> ParsedPipelineReport:
    """入口函数：日志发现 → 解析 → 汇总 → 终端打印 → 报告写盘 → 返回结构化报告。

    0.6.1 起只保留这一套签名：0.4/0.5 的 ``tex_engine/tex_output/bibtex_output/
    biber_output/other_engine_outputs/quiet`` 旧位置参数与 ``write_report`` 旧名
    已删除，调用方需统一用 ``steps`` + ``captured_outputs`` + ``write_report_file``。

    ``summary_max_entries`` 默认每个「等级 × 类别」组只打印 20 条，避免库调用
    一份大日志时刷屏；显式传 ``None`` 可恢复全量输出。``summary_width`` 用于
    按调用方控制台宽度覆盖默认 74 列版式。
    """
    if captured_outputs is None:
        captured_outputs = {}

    if jobname is None and auxdir is not None:
        jobname = _infer_jobname(auxdir, root_file)

    if jobname is None or auxdir is None:
        _td: Path | None = Path(tempfile.mkdtemp(prefix="pytexlogs_aux_"))
        jobname = jobname or "pytexlogs_default_job"
        auxdir = auxdir or str(_td)
    else:
        _td = None

    try:
        effective_pytexmk_version = pytexmk_version or "unknown"
        if steps is None:
            # 按实际存在的日志文件规划，避免同一份 .blg/.ilg/.log 被多个 parser 重复消费；
            # captured_outputs 的 key 也必须进入步骤，否则 biber 等纯文本输出会被静默忽略。
            steps = _append_captured_steps(plan_default_steps(jobname, auxdir), captured_outputs)
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
            summary_width=summary_width,
            ephemeral_auxdir=_td is not None,
        )
    finally:
        if _td is not None:
            import shutil as _sh

            _sh.rmtree(_td, ignore_errors=True)


def _coerce_line(value: Any) -> int | None:
    """把条目行号容错转成 int：None 保持 None，非法值回退 0 并记 debug。

    第三方解析器可能给出 ``"12a"`` 之类的脏行号；这里不能让它把整条流水线
    打断（异常发生在 manager 保护之外）。
    """
    if value is None:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        logger.debug("条目行号不是整数，回退 0: %r", value)
        return 0


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
        line=_coerce_line(line),
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
    summary_width: int | None = None,
    ephemeral_auxdir: bool = False,
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

    for outcome in manager.iter_steps(
        jobname,
        auxdir_path,
        steps,
        captured_outputs,
        root_file=root_file,
        dedupe_by_parser=False,
        captured_source_prefix=None,
    ):
        spec = outcome.spec
        if spec is None:
            skipped_steps.append(outcome.step)
            continue
        if outcome.error is None and outcome.skipped:
            skipped_steps.append(outcome.step)
            continue

        parse_exception: dict[str, str] | None = None
        if outcome.error is not None:
            parse_exception = {
                "type": type(outcome.error).__name__,
                "message": str(outcome.error),
            }

        parsed = outcome.parsed
        entries = list(parsed.entries) if isinstance(parsed, ParsedLog) else []
        report_entries = [_entry_to_report(entry) for entry in entries]

        stats: dict[str, Any] = {}
        if isinstance(parsed, ParsedLog) and isinstance(parsed.stats, dict):
            stats.update(parsed.stats)
        recompute_stats(report_entries, stats)

        tool_report = ToolResultReport(
            tool_name=outcome.step,
            category=spec.category,
            importance=spec.importance,
            source_path=str(outcome.log_path) if outcome.log_path else None,
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
    ref_unchanged: list[str] = []
    ref_current_keys: list[str] = []
    ref_key_counts: dict[str, int] = {}
    try:
        tracker = RefChangeTracker(auxdir_path, jobname, translate_fn=ref_tracker_translate_fn)
        mode = tracker.detect_mode()
        if mode != "unknown":
            raw_keys, ref_key_counts = tracker.extract_current_with_counts(mode)
            old_keys = tracker.load_cache()
            diff = tracker.diff(raw_keys, old_keys)
            ref_added = sorted(diff.get("added", set()))
            ref_removed = sorted(diff.get("removed", set()))
            ref_unchanged = sorted(diff.get("unchanged", set()))
            ref_current_keys = sorted(set(raw_keys))
            # 只有确实检测到 aux/bcf 引用源文件才回写缓存。
            try:
                tracker.save_cache(ref_current_keys, key_counts=ref_key_counts)
            except Exception as _e:
                logger.debug("保存参考文献缓存失败（不影响主流程）: %s", _e)
        else:
            # 无 aux/bcf（unknown 模式）：当前引用源缺失，raw_keys 为空。
            # 既不能 diff（否则旧键会被误判为 removed），也不能回写（否则旧缓存
            # 被清空）；缓存文件原样保留在磁盘上，但报告侧不得拿旧缓存键冒充
            # 当前键——current_keys/key_counts/unchanged/added/removed 全部为空。
            pass
        ref_report = ReferencesReport(
            current_keys=ref_current_keys,
            added=ref_added,
            removed=ref_removed,
            unchanged=ref_unchanged,
            key_counts=ref_key_counts,
            top_cited=[{"key": k, "count": c} for k, c in Counter(ref_key_counts).most_common(10)],
        )
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

        compiled_patterns = _compile_ignore_patterns(ignore_patterns)

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
                        severity_counts[cat]["total"] -= 1
                else:
                    remaining_entries.append(_te)
            tool.entries = remaining_entries
            recompute_stats(tool.entries, tool.stats)

    report = ParsedPipelineReport(
        schema_version=REPORT_SCHEMA_VERSION,
        generated_at=datetime.now(tz=UTC).isoformat(),
        pytexmk_version=pytexmk_version,
        jobname=jobname,
        root_file=root_file or "",
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
                raw_text="",
                source_path=tool.source_path or "",
                tool_name=tool.tool_name,
                category=tool.category,
                importance=tool.importance,
                stats=tool.stats,
            )
            parsed_logs_for_summary.append(plog)

        # ``run_pipeline`` 未给 jobname 时会落到内部占位名；这个占位名只用于
        # 临时 auxdir，不能泄漏到 hint，否则用户会看到 ``biber pytexlogs_default_job``。
        hint_jobname = None if jobname == "pytexlogs_default_job" else jobname
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
            jobname=hint_jobname,
            root_file=root_file,
            width=summary_width,
        )

    if write_report_file:
        from .report import _write_report_impl

        # 内部临时 auxdir 在 finally 会被删除，默认报告不能落在那里，
        # 否则 ``_report_path`` 指向一个已消失的文件。
        report_dir = Path.cwd() if ephemeral_auxdir else auxdir_path
        default_report_path = report_dir / f"{jobname}.pytexmk-report.json"
        actual_path = Path(report_path) if report_path else default_report_path
        write_error: str | None = None
        try:
            result_path, write_error = _write_report_impl(report, actual_path)
        except Exception as e:  # 报告写盘失败不能影响编译主流程
            logger.warning("报告写入失败: %s", actual_path, exc_info=True)
            result_path = None
            write_error = f"{type(e).__name__}: {e}"
        if result_path is not None:
            report.custom_fields["_report_path"] = str(result_path)
        elif write_error:
            report.custom_fields["_report_write_error"] = write_error

    return report
