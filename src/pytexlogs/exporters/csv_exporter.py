"""CSV 导出模块：将报告/条目导出为 CSV 格式字符串。"""

import csv
from io import StringIO
from typing import Any

from ..core.models import LogEntry
from .json_exporter import _flatten_to_entries


def _collect_hints() -> dict[str, str]:
    """合并 LATEX_LOG_HINTS / BIBTEX_ERROR_HINTS / BIBER_WARNING_HINTS 为一个大字典。"""
    from ..parsers.biber import BIBER_WARNING_HINTS
    from ..parsers.bibtex import BIBTEX_ERROR_HINTS
    from ..parsers.latex import LATEX_LOG_HINTS

    merged: dict[str, str] = {}
    merged.update(LATEX_LOG_HINTS)
    merged.update(BIBTEX_ERROR_HINTS)
    merged.update(BIBER_WARNING_HINTS)
    return merged


def to_csv(obj: Any) -> str:
    """将三种输入导出为 CSV 字符串；表头严格为 file,line,level,category,tool,text,hint,source_path。"""
    hints = _collect_hints()
    flat = _flatten_to_entries(obj)

    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["file", "line", "level", "category", "tool", "text", "hint", "source_path"])

    for entry, category, tool, source_path in flat:
        if not isinstance(entry, LogEntry):
            continue
        hint_text = ""
        for key, value in hints.items():
            if key in entry.text:
                hint_text = value
                break
        line_val = entry.line if entry.line else ""
        level_val = entry.level.value if hasattr(entry.level, "value") else str(entry.level)
        writer.writerow([
            entry.file or "",
            line_val,
            level_val,
            category or "",
            tool or "",
            entry.text or "",
            hint_text,
            source_path or "",
        ])

    return buf.getvalue()