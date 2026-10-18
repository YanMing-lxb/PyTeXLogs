"""Makeindex 索引 .ilg 日志解析器。"""

import re
from typing import Any

from ..core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog

# --- TeX Live 风格（## 前缀）------------------------------------------------
lines_read_re = re.compile(r"^##\s+(\d+)\s+lines read")
entries_re = re.compile(r"^##\s+(\d+)\s+entries accepted,\s*(\d+)\s+rejected")
warnings_issued_re = re.compile(r"^##\s+(\d+)\s+warnings issued")
processing_time_re = re.compile(r"Processing time:\s*([\d.]+)\s*sec")
error_re = re.compile(r"^!!\s+(.+)")
warning_line_re = re.compile(r"^Warning\s+line\s+(\d+)\s*:\s*(.+)")
warning_dash_re = re.compile(r"^Warning\s*--(.+)$")

# --- MiKTeX 风格（点进度 + ** 前缀）------------------------------------------
# TeX Live 用 `## 95 entries accepted`，MiKTeX 用 `....done (95 entries accepted, 0 rejected)`。
# 两种都要覆盖，否则 MiKTeX 用户的 .ilg 统计全部丢失。
miktex_entries_re = re.compile(
    r"done\s*\((\d+)\s+entries?\s+accepted,\s*(\d+)\s+rejected\)"
)
miktex_written_re = re.compile(r"done\s*\((\d+)\s+lines?\s+written,\s*(\d+)\s+warnings?\)")
# MiKTeX 用 `** Input style error (file = ..., line = 36):` 开头、续行以 `-- ` 缩进说明。
miktex_style_error_re = re.compile(r"^\*\*\s+(.+?)\s*\(file\s*=\s*(.+?),\s*line\s*=\s*(\d+)\)\s*:\s*$")
miktex_style_error_brief_re = re.compile(r"^\*\*\s+(.+)$")
miktex_redefined_re = re.compile(r"done\s*\((\d+)\s+attributes?\s+redefined,\s*(\d+)\s+ignored\)")


class MakeindexParser(BaseLogParser):
    """Makeindex 索引解析器：解析 .ilg 与 makeindex 输出。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 MakeindexParser：调用父类并设置 makeindex 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._lines_read = 0
        self._entries_accepted = 0
        self._entries_rejected = 0
        self._warnings_issued = 0
        self._processing_time_ms = 0.0
        self._style_errors = 0
        self._redefined = 0
        self._ignored = 0
        #: 上一条 `** Input style error (...):` 标题行，等待续行 `   -- xxx` 补齐正文。
        self._pending_style_error: LogEntry | None = None

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Makeindex .ilg 文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._lines_read = 0
        self._entries_accepted = 0
        self._entries_rejected = 0
        self._warnings_issued = 0
        self._processing_time_ms = 0.0
        self._style_errors = 0
        self._redefined = 0
        self._ignored = 0
        self._pending_style_error = None

        lines = log_text.split("\n")
        for line in lines:
            self._parse_line(line)

        stats: dict[str, Any] = {
            "lines_read": self._lines_read,
            "entries_accepted": self._entries_accepted,
            "entries_rejected": self._entries_rejected,
            "warnings_issued": self._warnings_issued,
            "processing_time_ms": self._processing_time_ms,
            "style_errors_count": self._style_errors,
            "redefined_count": self._redefined,
            "ignored_count": self._ignored,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="makeindex",
            category="index",
            importance="medium",
            stats=stats,
        )

    def _parse_line(self, line: str) -> None:
        line = line.strip("\x00")
        stripped = line.strip()

        # MiKTeX 的 style error 是两行结构：
        #   ** Input style error (file = xxx.ist, line = 36):
        #      -- Unknown specifier lethead_prefix.
        # 先接住标题行，等下一行续写正文。
        if self._pending_style_error is not None:
            if stripped.startswith("--"):
                detail = stripped[2:].strip()
                if detail:
                    self._pending_style_error.text = (
                        f"{self._pending_style_error.text}：{detail}"
                    )
                # 续行处理完毕，放行当前行继续走下面的分类逻辑：
                # 标题与续行必然成对出现，因此这里直接 return 是安全的。
                self._pending_style_error = None
                return
            # 没有续行（下一个标题紧跟上一个标题）：丢弃 pending，
            # 继续往下走，让当前行被正常识别为新的标题。
            self._pending_style_error = None

        m = lines_read_re.match(stripped)
        if m:
            self._lines_read = int(m.group(1))
            return

        m = entries_re.match(stripped)
        if m:
            self._entries_accepted = int(m.group(1))
            self._entries_rejected = int(m.group(2))
            return

        m = miktex_entries_re.search(stripped)
        if m:
            self._entries_accepted = int(m.group(1))
            self._entries_rejected = int(m.group(2))
            return

        m = warnings_issued_re.match(stripped)
        if m:
            self._warnings_issued = int(m.group(1))
            return

        m = miktex_written_re.search(stripped)
        if m:
            # `done (103 lines written, 0 warnings)`：MiKTeX 把 warnings 写在这里
            self._warnings_issued = int(m.group(2))
            return

        m = miktex_redefined_re.search(stripped)
        if m:
            self._redefined = int(m.group(1))
            self._ignored = int(m.group(2))
            return

        m = processing_time_re.search(stripped)
        if m:
            self._processing_time_ms = float(m.group(1)) * 1000
            return

        m = error_re.match(stripped)
        if m:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=self.root_file,
                    line=1,
                    text=m.group(1).strip(),
                )
            )
            return

        m = warning_line_re.match(stripped)
        if m:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=self.root_file,
                    line=int(m.group(1)),
                    text=m.group(2).strip(),
                )
            )
            return

        m = warning_dash_re.match(stripped)
        if m:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.WARNING,
                    file=self.root_file,
                    line=1,
                    text=m.group(1).strip(),
                )
            )
            return

        # MiKTeX style error：带文件名和行号的完整形式
        m = miktex_style_error_re.match(stripped)
        if m:
            self._style_errors += 1
            self._pending_style_error = LogEntry(
                level=LogLevel.ERROR,
                file=self._resolve_style_file(m.group(2)),
                line=int(m.group(3)),
                text=m.group(1).strip(),
            )
            self.build_log.append(self._pending_style_error)
            return

        # MiKTeX style error：不带括号的简写形式
        m = miktex_style_error_brief_re.match(stripped)
        if m:
            self._style_errors += 1
            self.build_log.append(
                LogEntry(
                    level=LogLevel.ERROR,
                    file=self.root_file,
                    line=1,
                    text=m.group(1).strip(),
                )
            )
            return

    def _resolve_style_file(self, filename: str) -> str:
        """.ist 样式文件路径保留原样（常用于判断 MiKTeX 版本差异）。"""
        return filename or self.root_file
