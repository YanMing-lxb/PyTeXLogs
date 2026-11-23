"""JSON 导出模块：将报告/条目序列化为 JSON 格式。"""

import dataclasses
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..core.models import (
    REPORT_SCHEMA_VERSION,
    LogEntry,
    LogLevel,
    ParsedLog,
    ParsedPipelineReport,
    ReportEntry,
    ToolResult,
    ToolResultReport,
    ToolResultStats,
    level_from_value,
)
from ..core.stats import recompute_stats
from ..version import __version__


def _hint_payload(
    entry: LogEntry,
    category: str,
    tool: str,
    source_path: str,
    *,
    jobname: str | None = None,
    root_file: str | None = None,
    language: str | None = None,
) -> dict[str, Any] | None:
    """为导出层条目生成结构化 hint；无匹配时返回 ``None``。

    不把 hint 塞回 ``LogEntry`` / ``ReportEntry``，避免改变既有数据模型与
    JSON 条目字段集合；导出层只新增一个独立的 ``hints`` 数组。

    ``language`` 为可选透传：``"en"`` 时 hint 的 ``text`` 取英文说明（缺失时
    回退中文）；``None``/其他值保持默认中文。``text_en`` 双字段始终保留。
    """
    from ..hints import hint_for_entry

    context_job = jobname or (Path(source_path).stem if source_path else None)
    hint = hint_for_entry(
        entry,
        jobname=context_job,
        root_file=root_file,
        tool_name=tool or None,
        language=language,
    )
    if hint is None:
        return None
    return {
        "file": entry.file or "",
        "line": entry.line or 0,
        "level": entry.level.value if hasattr(entry.level, "value") else str(entry.level),
        "category": category or "",
        "tool": tool or "",
        "text": entry.text or "",
        "source_path": source_path or "",
        "hint": {
            "rule_id": hint.rule_id,
            "kind": hint.kind,
            "text": hint.text,
            "text_en": hint.text_en,
            "commands": list(hint.commands),
        },
    }


def _collect_export_hints(
    flat: list[tuple[LogEntry, str, str, str]],
    *,
    jobname: str | None = None,
    root_file: str | None = None,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """把扁平条目转成 ``hints`` 数组，保持条目顺序并跳过无匹配项。"""
    result: list[dict[str, Any]] = []
    for entry, category, tool, source_path in flat:
        payload = _hint_payload(
            entry,
            category,
            tool,
            source_path,
            jobname=jobname,
            root_file=root_file,
            language=language,
        )
        if payload is not None:
            result.append(payload)
    return result


def _report_entry_to_log_entry(entry: ReportEntry) -> LogEntry:
    """报告条目（level 为字符串）→ 运行时条目（level 为枚举）。

    报告模型为了 JSON 兼容把等级存成字符串，导出 CSV/SARIF 与展示层需要枚举
    才能比较严重度；转换只在这里做一次，避免每个导出器各写一张映射表。
    """
    return LogEntry(
        level=level_from_value(entry.level),
        file=entry.file or "",
        line=entry.line or 0,
        text=entry.text or "",
        error_pos_text=entry.error_pos_text or "",
    )


def _result_to_dict(tr: ToolResultReport) -> dict[str, Any]:
    """``ToolResultReport`` → 与 ``ToolResult`` 一致的导出形状。

    刻意与 :func:`dataclasses.asdict` 对齐（``tool_name/category/importance/
    source_path/entries/stats``），这样 CLI 从 ToolResult 切到报告模型后，
    ``--format json`` 的消费方拿到的字段名不变；条目只保留 file/line/text
    等公共字段，不输出报告内部使用的来源字段。解析器抛异常时额外输出
    ``parse_exception``，让列表输入也能看到失败原因。
    """
    payload: dict[str, Any] = {
        "tool_name": tr.tool_name,
        "category": tr.category,
        "importance": tr.importance,
        "source_path": tr.source_path or "",
        "entries": [
            {
                "level": e.level.value if hasattr(e.level, "value") else str(e.level),
                "file": e.file or "",
                "line": e.line or 0,
                "text": e.text or "",
                "error_pos_text": e.error_pos_text or "",
            }
            for e in tr.entries
        ],
        "stats": {
            "entries_count": tr.stats.get("entries_count", len(tr.entries)),
            "stats": {key: value for key, value in tr.stats.items() if key != "entries_count"},
        },
    }
    if tr.parse_exception is not None:
        payload["parse_exception"] = tr.parse_exception
    return payload


def _log_entry_to_dict(entry: LogEntry) -> dict[str, Any]:
    """运行时条目（枚举等级）→ JSON 兼容 dict。"""
    return {
        "level": entry.level.value if hasattr(entry.level, "value") else str(entry.level),
        "file": entry.file or "",
        "line": entry.line or 0,
        "text": entry.text or "",
        "error_pos_text": entry.error_pos_text or "",
    }


def _tool_result_to_dict(tr: ToolResult) -> dict[str, Any]:
    """``ToolResult``（含 ``ToolResultStats``）→ ``dataclasses.asdict`` 结构化 dict。"""
    return dataclasses.asdict(tr)


def _parsed_log_to_dict(plog: ParsedLog) -> dict[str, Any]:
    """``ParsedLog`` → 结构化 dict；不输出对象 repr。"""
    return {
        "tool_name": plog.tool_name,
        "category": plog.category,
        "importance": plog.importance,
        "source_path": plog.source_path or "",
        "entries": [_log_entry_to_dict(e) for e in plog.entries],
        "stats": dict(plog.stats),
    }


def _entry_rank(entry: Any) -> int:
    """取条目的严重度序号（越小越严重），未知按 INFO。"""
    level = getattr(entry, "level", LogLevel.INFO)
    if hasattr(level, "severity"):
        return int(level.severity)
    value = str(getattr(level, "value", level))
    try:
        return int(LogLevel(value).severity)
    except ValueError:
        return int(LogLevel.INFO.severity)


def filter_by_level(obj: Any, min_level: LogLevel | None) -> Any:
    """按严重度过滤任意受支持输入；返回同类型对象（必要时做浅拷贝）。

    报告对象会重建 ``tool_results`` 与 ``severity_counts``，保证导出的 JSON
    与 ``--severity`` 的语义一致（0.4.x 里导出器忽略该参数，是个真实缺陷）。
    """
    if min_level is None or obj is None:
        return obj

    if isinstance(obj, ParsedPipelineReport):
        report = dataclasses.replace(obj)
        new_results: list[Any] = []
        severity_counts: dict[str, dict[str, int]] = {}
        for tr in obj.tool_results:
            new_tr = _filter_report_result(tr, min_level)
            new_results.append(new_tr)
            cat = new_tr.category
            bucket = severity_counts.setdefault(cat, dict(_EMPTY_SEVERITY_BUCKET))
            for e in new_tr.entries:
                level_value = getattr(e, "level", "info")
                lvl = level_value.value if hasattr(level_value, "value") else str(level_value)
                if lvl in bucket:
                    bucket[lvl] += 1
                bucket["total"] += 1
        report.tool_results = new_results
        report.severity_counts = severity_counts
        return report

    if isinstance(obj, ToolResultReport):
        return _filter_report_result(obj, min_level)

    if isinstance(obj, ParsedLog):
        return _filter_parsed_log(obj, min_level)

    if isinstance(obj, list):
        filtered: list[Any] = []
        for item in obj:
            if isinstance(item, ToolResultReport):
                filtered.append(_filter_report_result(item, min_level))
            elif isinstance(item, ParsedLog):
                filtered.append(_filter_parsed_log(item, min_level))
            elif isinstance(item, ToolResult):
                kept = [e for e in item.entries if _entry_rank(e) <= int(min_level.severity)]
                new_stats = dict(item.stats.stats)
                recompute_stats(kept, new_stats)
                filtered.append(
                    dataclasses.replace(
                        item,
                        entries=kept,
                        stats=ToolResultStats(
                            entries_count=len(kept),
                            stats=new_stats,
                        ),
                    )
                )
            elif isinstance(item, LogEntry):
                if _entry_rank(item) <= int(min_level.severity):
                    filtered.append(item)
            else:
                filtered.append(item)
        return filtered

    return obj


#: 分级桶由枚举派生，避免 font/graphic/page 只计入 total 却没有自己的键。
_EMPTY_SEVERITY_BUCKET: dict[str, int] = {
    **{level.value: 0 for level in LogLevel},
    "total": 0,
}


def _filter_report_result(tr: ToolResultReport, min_level: LogLevel) -> ToolResultReport:
    """按严重度过滤单个报告结果，并重算全部可推导统计。"""
    kept = [e for e in tr.entries if _entry_rank(e) <= int(min_level.severity)]
    stats = dict(tr.stats)
    recompute_stats(kept, stats)
    return dataclasses.replace(tr, entries=kept, stats=stats)


def _filter_parsed_log(plog: ParsedLog, min_level: LogLevel) -> ParsedLog:
    """按严重度过滤单个运行时解析结果，并重算可推导统计。

    列表输入里的 ``ParsedLog`` 曾经被原样透传，导致
    ``to_json([parsed], min_level=ERROR)`` 与单对象入口行为不一致；抽成
    共用函数后，单个与列表分支永远走同一套过滤口径。
    """
    kept = [e for e in plog.entries if _entry_rank(e) <= int(min_level.severity)]
    stats = dict(plog.stats)
    recompute_stats(kept, stats)
    return dataclasses.replace(plog, entries=kept, stats=stats)


def _flatten_to_entries(
    obj: Any,
) -> list[tuple[LogEntry, str, str, str]]:
    """将输入统一扁平化为 [(LogEntry, category, tool, source_path)]。

    支持的输入类型：
    - ParsedPipelineReport: 从 tool_results 提取
    - list[ToolResultReport]: CLI 的规范输入（报告模型）
    - list[ToolResult]: 从每个 ToolResult 提取
    - list[LogEntry]: 直接使用条目
    - ParsedLog: 从单个解析结果提取
    """
    result: list[tuple[LogEntry, str, str, str]] = []
    if isinstance(obj, ParsedPipelineReport):
        result.extend(
            (
                _report_entry_to_log_entry(e),
                tr.category or "",
                tr.tool_name or "",
                tr.source_path or "",
            )
            for tr in obj.tool_results
            for e in tr.entries
        )
    elif isinstance(obj, ParsedLog):
        result.extend((e, obj.category or "", obj.tool_name or "", obj.source_path or "") for e in obj.entries)
    elif isinstance(obj, LogEntry):
        result.append((obj, "", "", ""))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, ToolResultReport):
                result.extend(
                    (
                        _report_entry_to_log_entry(e),
                        item.category or "",
                        item.tool_name or "",
                        item.source_path or "",
                    )
                    for e in item.entries
                )
            elif isinstance(item, ToolResult):
                result.extend(
                    (e, item.category or "", item.tool_name or "", item.source_path or "") for e in item.entries
                )
            elif isinstance(item, ParsedLog):
                result.extend(
                    (e, item.category or "", item.tool_name or "", item.source_path or "") for e in item.entries
                )
            elif isinstance(item, LogEntry):
                result.append((item, "", "", ""))
    return result


def report_to_dict(report: ParsedPipelineReport) -> dict[str, Any]:
    """将 ParsedPipelineReport 递归转为 dict；若 references.key_counts 非空但 top_cited 为空则自动补 Top10。"""
    d = dataclasses.asdict(report)
    refs = d.get("references")
    if isinstance(refs, dict):
        kc = refs.get("key_counts")
        tc = refs.get("top_cited")
        if kc and not tc:
            refs["top_cited"] = [{"key": str(k), "count": int(c)} for k, c in Counter(kc).most_common(10)]
    return d


def to_json(
    obj: Any,
    *,
    min_level: LogLevel | None = None,
    include_hints: bool = True,
    language: str | None = None,
    **json_kwargs: Any,
) -> str:
    """将 ParsedPipelineReport / ParsedLog / list[ToolResult] / list[LogEntry] / 单条 LogEntry 序列化为 JSON 字符串。

    Args:
        min_level: 只导出严重度不低于该等级的条目（``None`` 表示不过滤）。
        include_hints: 是否追加顶层 ``hints`` 数组（结构化可执行建议）。
            设为 ``False`` 可得到 0.6.1 之前的载荷形状。
        language: 可选提示语言；``"en"`` 时 hint 的 ``text`` 取英文说明（缺失
            回退中文），``None``/其他值保持默认中文。``text``/``text_en`` 双
            字段始终保留，``kind``/``commands``/``rule_id`` 不受影响。
    """
    obj = filter_by_level(obj, min_level)
    export_hints: list[dict[str, Any]] = []
    if include_hints:
        if isinstance(obj, ParsedPipelineReport):
            export_hints = _collect_export_hints(
                _flatten_to_entries(obj),
                jobname=obj.jobname or None,
                root_file=obj.root_file or None,
                language=language,
            )
        elif isinstance(obj, list):
            export_hints = _collect_export_hints(_flatten_to_entries(obj), language=language)
        elif isinstance(obj, LogEntry):
            export_hints = _collect_export_hints(_flatten_to_entries(obj), language=language)
        elif isinstance(obj, ParsedLog):
            export_hints = _collect_export_hints(_flatten_to_entries(obj), language=language)
    data: dict[str, Any]
    if isinstance(obj, ParsedPipelineReport):
        data = report_to_dict(obj)
        data["__format__"] = "pytexlogs-json-v1"
        data["pytexlogs_version"] = __version__
        # 明确区分「报告导出 schema」与状态文件 schema（两者含义不同，曾经同名混淆）
        data["report_schema"] = REPORT_SCHEMA_VERSION
        data["meta"] = {
            "jobname": obj.jobname,
            "root_file": obj.root_file,
            "auxdir": obj.auxdir,
            "total_steps": obj.pipeline.total_steps,
            "attempted_steps": obj.pipeline.attempted_steps,
            "skipped_steps": obj.pipeline.skipped_steps,
            "duration_ms": obj.pipeline.duration_ms,
        }
    elif isinstance(obj, list):
        if not obj:
            data = {"results": [], "__format__": "pytexlogs-json-v1", "pytexlogs_version": __version__}
        else:
            results: list[Any] = []
            for item in obj:
                if isinstance(item, ToolResultReport):
                    results.append(_result_to_dict(item))
                elif isinstance(item, ToolResult):
                    results.append(_tool_result_to_dict(item))
                elif isinstance(item, ParsedLog):
                    results.append(_parsed_log_to_dict(item))
                elif isinstance(item, LogEntry):
                    results.append(dataclasses.asdict(item))
                else:
                    raise TypeError(
                        f"to_json 不支持列表项类型 {type(item).__name__}；"
                        "支持 ToolResultReport / ToolResult / ParsedLog / LogEntry"
                    )
            data = {
                "results": results,
                "__format__": "pytexlogs-json-v1",
                "pytexlogs_version": __version__,
            }
    elif isinstance(obj, LogEntry):
        data = {
            "results": [_log_entry_to_dict(obj)],
            "__format__": "pytexlogs-json-v1",
            "pytexlogs_version": __version__,
        }
    elif isinstance(obj, ParsedLog):
        data = {
            "results": [_parsed_log_to_dict(obj)],
            "__format__": "pytexlogs-json-v1",
            "pytexlogs_version": __version__,
        }
    else:
        raise TypeError(
            f"to_json 不支持输入类型 {type(obj).__name__}；支持 ParsedPipelineReport / 上述列表类型 / LogEntry"
        )

    if include_hints and isinstance(obj, (ParsedPipelineReport, list, LogEntry, ParsedLog)):
        data["hints"] = export_hints

    kwargs: dict[str, Any] = {
        "ensure_ascii": False,
        "indent": 2,
        "default": lambda o: o.value if isinstance(o, LogLevel) else str(o),
    }
    kwargs.update(json_kwargs)
    return json.dumps(data, **kwargs)
