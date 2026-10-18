"""Nomencl 符号表 .nlg 日志解析器实现。"""

import re
from typing import Any

from ..core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog

entries_re = re.compile(r"^##\s+(\d+)\s+entries accepted,\s*(\d+)\s+rejected")
error_re = re.compile(r"^!!\s+(.+)")
warning_line_re = re.compile(r"^Warning\s+line\s+(\d+)\s*:\s*(.+)")
warning_dash_re = re.compile(r"^Warning--(.+)")

# MiKTeX 用 `....done (N entries accepted, M rejected)` 而非 `##` 前缀。
miktex_entries_re = re.compile(r"done\s*\((\d+)\s+entries?\s+accepted,\s*(\d+)\s+rejected\)")
# MiKTeX 用 `** Input style error (file = ..., line = N):` 报告 .ist 语法问题，
# 续行以 `   -- 说明` 给出具体原因。nomencl.ist 在 MiKTeX 上几乎必然触发。
miktex_style_error_re = re.compile(r"^\*\*\s+(.+?)\s*\(file\s*=\s*(.+?),\s*line\s*=\s*(\d+)\)\s*:\s*$")
miktex_style_error_brief_re = re.compile(r"^\*\*\s+(.+)$")


class NomenclParser(BaseLogParser):
    """Nomencl 符号表解析器：解析 .nlg 日志。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 NomenclParser：调用父类并设置 nomencl 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._nomenclature_entries = 0
        self._style_errors = 0
        #: 上一条待补正文的 MiKTeX style error 标题行。
        self._pending_style_error: LogEntry | None = None

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Nomencl .nlg 文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._nomenclature_entries = 0
        self._style_errors = 0
        self._pending_style_error = None

        self._scan_makeindex(log_text)

        stats: dict[str, Any] = {
            "nomenclature_entries": self._nomenclature_entries,
            "style_errors_count": self._style_errors,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            tool_name="nomencl",
            category="glossary",
            importance="low",
            stats=stats,
        )

    def _scan_makeindex(self, log_text: str) -> None:
        file_ref = self.root_file
        for raw_line in log_text.split("\n"):
            line = raw_line.strip()

            # 接住上一条 style error 的续行
            if self._pending_style_error is not None:
                if line.startswith("--"):
                    detail = line[2:].strip()
                    if detail:
                        self._pending_style_error.text = f"{self._pending_style_error.text}：{detail}"
                    self._pending_style_error = None
                    continue
                self._pending_style_error = None

            m = entries_re.match(line) or miktex_entries_re.search(line)
            if m:
                self._nomenclature_entries = int(m.group(1))
                continue

            m = miktex_style_error_re.match(line)
            if m:
                self._style_errors += 1
                entry = LogEntry(
                    level=LogLevel.ERROR,
                    file=m.group(2).strip() or file_ref,
                    line=int(m.group(3)),
                    text=m.group(1).strip(),
                )
                self.build_log.append(entry)
                self._pending_style_error = entry
                continue

            m = miktex_style_error_brief_re.match(line)
            if m:
                self._style_errors += 1
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.ERROR,
                        file=file_ref,
                        line=1,
                        text=m.group(1).strip(),
                    )
                )
                continue

            m = error_re.match(line)
            if m:
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.ERROR,
                        file=file_ref,
                        line=1,
                        text=m.group(1).strip(),
                    )
                )
                continue
            m = warning_line_re.match(line)
            if m:
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.WARNING,
                        file=file_ref,
                        line=int(m.group(1)),
                        text=m.group(2).strip(),
                    )
                )
                continue
            m = warning_dash_re.match(line)
            if m:
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.WARNING,
                        file=file_ref,
                        line=1,
                        text=m.group(1).strip(),
                    )
                )
                continue
