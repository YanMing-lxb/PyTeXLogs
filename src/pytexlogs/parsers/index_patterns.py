"""索引/术语表日志解析器共用的正则。

Makeindex、Glossaries、Nomencl 三个解析器历史上各自维护了一份几乎相同的
正则表，升级时容易只改一处导致 MiKTeX/TeX Live 口径漂移。这里集中定义，
各模块用同名 import 保持原有属性仍可访问。
"""

import re

__all__ = [
    "entries_re",
    "error_re",
    "lines_read_re",
    "miktex_entries_re",
    "miktex_redefined_re",
    "miktex_style_error_brief_re",
    "miktex_style_error_re",
    "miktex_written_re",
    "processing_time_re",
    "warning_dash_re",
    "warning_line_re",
    "warnings_issued_re",
]

# TeX Live 风格（## 前缀）
lines_read_re = re.compile(r"^##\s+(\d+)\s+lines read")
entries_re = re.compile(r"^##\s+(\d+)\s+entries accepted,\s*(\d+)\s+rejected")
warnings_issued_re = re.compile(r"^##\s+(\d+)\s+warnings issued")
processing_time_re = re.compile(r"Processing time:\s*([\d.]+)\s*sec")
error_re = re.compile(r"^!!\s+(.+)")
warning_line_re = re.compile(r"^Warning\s+line\s+(\d+)\s*:\s*(.+)")
warning_dash_re = re.compile(r"^Warning\s*--(.+)$")

# MiKTeX 风格（点进度 + ** 前缀）
miktex_entries_re = re.compile(r"done\s*\((\d+)\s+entries?\s+accepted,\s*(\d+)\s+rejected\)")
miktex_written_re = re.compile(r"done\s*\((\d+)\s+lines?\s+written,\s*(\d+)\s+warnings?\)")
miktex_style_error_re = re.compile(r"^\*\*\s+(.+?)\s*\(file\s*=\s*(.+?),\s*line\s*=\s*(\d+)\)\s*:\s*$")
miktex_style_error_brief_re = re.compile(r"^\*\*\s+(.+)$")
miktex_redefined_re = re.compile(r"done\s*\((\d+)\s+attributes?\s+redefined,\s*(\d+)\s+ignored\)")
