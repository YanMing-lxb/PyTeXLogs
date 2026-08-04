"""Nomencl 符号表 .nlg 日志解析器实现。"""

import re
from typing import Any

from ..core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog

entries_re = re.compile(r"^##\s+(\d+)\s+entries accepted,\s*(\d+)\s+rejected")
error_re = re.compile(r"^!!\s+(.+)")
warning_line_re = re.compile(r"^Warning\s+line\s+(\d+)\s*:\s*(.+)")
warning_dash_re = re.compile(r"^Warning--(.+)")


class NomenclParser(BaseLogParser):
    """Nomencl 符号表解析器：解析 .nlg 日志。"""
    def __init__(self, root_file: str | None = None) -> None:
        """初始化 NomenclParser：调用父类并设置 nomencl 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._nomenclature_entries = 0

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Nomencl .nlg 文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._nomenclature_entries = 0

        self._scan_makeindex(log_text)

        stats: dict[str, Any] = {
            "nomenclature_entries": self._nomenclature_entries,
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
        for line in log_text.split("\n"):
            m = entries_re.match(line)
            if m:
                self._nomenclature_entries = int(m.group(1))
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