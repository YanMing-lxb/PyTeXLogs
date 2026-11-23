"""CSV 导出模块：将报告/条目导出为 CSV 格式字符串。"""

import csv
from io import StringIO
from pathlib import Path
from typing import Any

from ..core.models import LogEntry, LogLevel
from .json_exporter import _flatten_to_entries, filter_by_level

#: CSV 单元格若以这些字符开头，Excel/LibreOffice 可能按公式解释；加单引号前缀。
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe_cell(value: str) -> str:
    """防 CSV 公式注入：保留原值，只对可疑前缀加 ``'`` 让表格软件按文本处理。"""
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value


def to_csv(
    obj: Any,
    *,
    min_level: LogLevel | None = None,
    language: str | None = None,
    include_hints: bool = True,
) -> str:
    """将三种输入导出为 CSV 字符串；表头严格为 file,line,level,category,tool,text,hint,source_path。

    ``language`` 为可选提示语言：``"en"`` 时 ``hint`` 列取英文说明（缺失回退
    中文），``None``/其他值保持默认中文。表头与其他列不变。
    ``include_hints=False`` 时跳过逐行 hint 计算（大日志导出可显著省时），
    ``hint`` 列保留为空字符串。
    以 ``= + - @`` 等开头的文本会加 ``'`` 前缀，防止表格软件把日志内容
    当作公式执行；其余内容保持不变。
    """
    from ..hints import hint_for_entry

    obj = filter_by_level(obj, min_level)
    flat = _flatten_to_entries(obj)

    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["file", "line", "level", "category", "tool", "text", "hint", "source_path"])

    for entry, category, tool, source_path in flat:
        if not isinstance(entry, LogEntry):
            continue
        hint_text = ""
        if include_hints:
            hint = hint_for_entry(
                entry,
                jobname=Path(source_path).stem if source_path else None,
                tool_name=tool or None,
                language=language,
            )
            hint_text = hint.text if hint else ""
        line_val = entry.line if entry.line else ""
        level_val = entry.level.value if hasattr(entry.level, "value") else str(entry.level)
        writer.writerow(
            [
                _csv_safe_cell(entry.file or ""),
                line_val,
                level_val,
                _csv_safe_cell(category or ""),
                _csv_safe_cell(tool or ""),
                _csv_safe_cell(" ".join((entry.text or "").splitlines())),
                _csv_safe_cell(hint_text),
                _csv_safe_cell(source_path or ""),
            ]
        )

    return buf.getvalue()
