"""JSON 导出模块：将报告/条目序列化为 JSON 格式。"""

import dataclasses
import json
from collections import Counter
from typing import Any

from ..core.models import (
    LogEntry,
    LogLevel,
    ParsedLog,
    ParsedPipelineReport,
    ReportEntry,
    ToolResult,
)
from ..version import __version__


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


def _filter_flat(
    flat: list[tuple[LogEntry, str, str, str]],
    min_level: LogLevel | None,
) -> list[tuple[LogEntry, str, str, str]]:
    """按最低严重度过滤扁平条目。"""
    if min_level is None:
        return flat
    threshold = int(min_level.severity)
    return [item for item in flat if _entry_rank(item[0]) <= threshold]


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
            kept = [e for e in tr.entries if _entry_rank(e) <= int(min_level.severity)]
            new_tr = dataclasses.replace(tr, entries=kept)
            new_tr.stats = dict(tr.stats)
            new_tr.stats["entries_count"] = len(kept)
            new_results.append(new_tr)
            cat = new_tr.category
            bucket = severity_counts.setdefault(
                cat, {"error": 0, "warning": 0, "typesetting": 0, "info": 0, "total": 0}
            )
            for e in kept:
                lvl = str(getattr(e, "level", "info"))
                if lvl in bucket:
                    bucket[lvl] += 1
                bucket["total"] += 1
        report.tool_results = new_results
        report.severity_counts = severity_counts
        return report

    if isinstance(obj, list):
        filtered: list[Any] = []
        for item in obj:
            if isinstance(item, ToolResult):
                kept = [e for e in item.entries if _entry_rank(e) <= int(min_level.severity)]
                clone = dataclasses.replace(item, entries=kept)
                clone.stats = dataclasses.replace(
                    item.stats,
                    entries_count=len(kept),
                    stats=dict(item.stats.stats),
                )
                clone.stats.stats["entries_count"] = len(kept)
                filtered.append(clone)
            elif isinstance(item, LogEntry):
                if _entry_rank(item) <= int(min_level.severity):
                    filtered.append(item)
            else:
                filtered.append(item)
        return filtered

    return obj


def _flatten_to_entries(
    obj: Any,
) -> list[tuple[LogEntry, str, str, str]]:
    """将输入统一扁平化为 [(LogEntry, category, tool, source_path)]。

    支持的输入类型：
    - ParsedPipelineReport: 从 tool_results 提取
    - list[ToolResult]: 从每个 ToolResult 提取
    - list[LogEntry]: 直接使用条目
    - ParsedLog: 从单个解析结果提取
    """
    result: list[tuple[LogEntry, str, str, str]] = []
    if isinstance(obj, ParsedPipelineReport):
        for tr in obj.tool_results:
            for e in tr.entries:
                if isinstance(e, ReportEntry):
                    lvl_map = {
                        "error": LogLevel.ERROR,
                        "warning": LogLevel.WARNING,
                        "typesetting": LogLevel.TYPESET,
                        "info": LogLevel.INFO,
                        "font": LogLevel.FONT,
                        "graphic": LogLevel.GRAPHIC,
                        "page": LogLevel.PAGE,
                    }
                    log_entry = LogEntry(
                        level=lvl_map.get(e.level, LogLevel.INFO),
                        file=e.file or "",
                        line=e.line or 0,
                        text=e.text or "",
                        error_pos_text=e.error_pos_text or "",
                    )
                    result.append(
                        (log_entry, tr.category or "", tr.tool_name or "", tr.source_path or "")
                    )
    elif isinstance(obj, ParsedLog):
        for e in obj.entries:
            result.append(
                (e, obj.category or "", obj.tool_name or "", obj.source_path or "")
            )
    elif isinstance(obj, list):
        if not obj:
            return result
        first = obj[0]
        if isinstance(first, ToolResult):
            for tr in obj:
                for e in tr.entries:
                    result.append(
                        (e, tr.category or "", tr.tool_name or "", tr.source_path or "")
                    )
        elif isinstance(first, ParsedLog):
            for plog in obj:
                for e in plog.entries:
                    result.append(
                        (e, plog.category or "", plog.tool_name or "", plog.source_path or "")
                    )
        elif isinstance(first, LogEntry):
            for e in obj:
                result.append((e, "", "", ""))
    return result


def report_to_dict(report: ParsedPipelineReport) -> dict[str, Any]:
    """将 ParsedPipelineReport 递归转为 dict；若 references.key_counts 非空但 top_cited 为空则自动补 Top10。"""
    d = dataclasses.asdict(report)
    refs = d.get("references")
    if isinstance(refs, dict):
        kc = refs.get("key_counts")
        tc = refs.get("top_cited")
        if kc and not tc:
            refs["top_cited"] = [
                {"key": str(k), "count": int(c)} for k, c in Counter(kc).most_common(10)
            ]
    return d


def to_json(
    obj: Any,
    *,
    min_level: LogLevel | None = None,
    **json_kwargs: Any,
) -> str:
    """将 ParsedPipelineReport / list[ToolResult] / list[LogEntry] 序列化为 JSON 字符串。

    Args:
        min_level: 只导出严重度不低于该等级的条目（``None`` 表示不过滤）。
    """
    obj = filter_by_level(obj, min_level)
    data: dict[str, Any]
    if isinstance(obj, ParsedPipelineReport):
        data = report_to_dict(obj)
        data["__format__"] = "pytexlogs-json-v1"
        data["pytexlogs_version"] = __version__
        # 明确区分「报告导出 schema」与状态文件 schema（两者含义不同，曾经同名混淆）
        data["report_schema"] = 1
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
            first = obj[0]
            if isinstance(first, ToolResult):
                data = {
                    "results": [dataclasses.asdict(tr) for tr in obj],
                    "__format__": "pytexlogs-json-v1",
                    "pytexlogs_version": __version__,
                }
            elif isinstance(first, LogEntry):
                data = {
                    "results": [dataclasses.asdict(e) for e in obj],
                    "__format__": "pytexlogs-json-v1",
                    "pytexlogs_version": __version__,
                }
            else:
                data = {
                    "results": list(obj),
                    "__format__": "pytexlogs-json-v1",
                    "pytexlogs_version": __version__,
                }
    else:
        data = {"input": str(obj), "__format__": "pytexlogs-json-v1", "pytexlogs_version": __version__}

    kwargs: dict[str, Any] = {
        "ensure_ascii": False,
        "indent": 2,
        "default": lambda o: o.value if isinstance(o, LogLevel) else str(o),
    }
    kwargs.update(json_kwargs)
    return json.dumps(data, **kwargs)
