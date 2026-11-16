"""CSV 导出模块：将报告/条目导出为 CSV 格式字符串。"""

import csv
from io import StringIO
from typing import Any

from ..core.models import LogEntry, LogLevel
from .json_exporter import _flatten_to_entries, filter_by_level


def _collect_hints() -> dict[str, str]:
    """兼容旧接口：合并三张提示表（实际实现已迁到 :mod:`pytexlogs.hints`）。"""
    from ..hints import collect_hints

    return collect_hints()


def to_csv(obj: Any, *, min_level: LogLevel | None = None) -> str:
    """将三种输入导出为 CSV 字符串；表头严格为 file,line,level,category,tool,text,hint,source_path。"""
    from ..hints import hint_for_text

    obj = filter_by_level(obj, min_level)
    flat = _flatten_to_entries(obj)

    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["file", "line", "level", "category", "tool", "text", "hint", "source_path"])

    for entry, category, tool, source_path in flat:
        if not isinstance(entry, LogEntry):
            continue
        hint = hint_for_text(entry.text or "")
        hint_text = hint.text if hint else ""
        line_val = entry.line if entry.line else ""
        level_val = entry.level.value if hasattr(entry.level, "value") else str(entry.level)
        writer.writerow([
            entry.file or "",
            line_val,
            level_val,
            category or "",
            tool or "",
            " ".join((entry.text or "").splitlines()),
            hint_text,
            source_path or "",
        ])

    return buf.getvalue()
