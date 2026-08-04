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
    **json_kwargs: Any,
) -> str:
    """将 ParsedPipelineReport / list[ToolResult] / list[LogEntry] 序列化为 JSON 字符串。"""
    data: dict[str, Any]
    if isinstance(obj, ParsedPipelineReport):
        data = report_to_dict(obj)
        data["__format__"] = "pytexlogs-json-v1"
        data["pytexlogs_version"] = __version__
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

    kwargs: dict[str, Any] = {"ensure_ascii": False, "indent": 2}
    kwargs.update(json_kwargs)
    return json.dumps(data, **kwargs)