"""Glossaries 术语表 .glg 日志解析器实现。"""

import re
from contextlib import suppress
from pathlib import Path
from typing import Any

from ..core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog
from .index_patterns import (
    entries_re,
    error_re,
    miktex_entries_re,
    miktex_style_error_brief_re,
    miktex_style_error_re,
    warning_dash_re,
    warning_line_re,
    warnings_issued_re,
)
from .xindy_patterns import scan_xindy


class GlossariesParser(BaseLogParser):
    """Glossaries 术语表解析器：解析 .glg 与 Makeindex 类输出。"""

    def __init__(self, root_file: str | None = None) -> None:
        """初始化 GlossariesParser：调用父类并设置 glossaries 默认工具元数据。"""
        super().__init__(root_file)
        self.build_log: list[LogEntry] = []
        self._main_entries = 0
        self._acronym_entries = 0
        self._symbol_entries = 0
        self._warnings_count = 0
        #: 上一条 `** Input style error (...):` 标题行，等待 `--` 续行补正文。
        self._pending_style_error: LogEntry | None = None

    def _detect_format(self, log_text: str) -> str:
        head = "\n".join(log_text.split("\n")[:50])
        if "Loading module" in head or re.search(r"Added\s+\d+\s+letter\s+groups?", head):
            return "xindy"
        return "makeindex"

    def _suffix_to_field(self, source_path: str) -> str:
        suffix = Path(source_path).suffix.lower()
        if suffix == ".alg":
            return "acronym_entries"
        if suffix == ".slg":
            return "symbol_entries"
        return "main_entries"

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Glossaries 输出文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file
        elif not self.root_file:
            self.root_file = "main.tex"

        self.build_log.clear()
        self._main_entries = 0
        self._acronym_entries = 0
        self._symbol_entries = 0
        self._warnings_count = 0
        self._pending_style_error = None

        fmt = self._detect_format(log_text)
        entries_count = 0

        if fmt == "xindy":
            entries_count, warnings = self._parse_xindy(log_text)
            self._warnings_count = warnings
        else:
            entries_count, warnings = self._parse_makeindex(log_text)
            self._warnings_count = warnings

        source_path = getattr(self, "_source_path_hint", "")
        field = self._suffix_to_field(source_path)
        setattr(self, f"_{field}", entries_count)

        stats: dict[str, Any] = {
            "main_entries": self._main_entries,
            "acronym_entries": self._acronym_entries,
            "symbol_entries": self._symbol_entries,
            "warnings_count": self._warnings_count,
        }

        return ParsedLog(
            entries=self.build_log[:],
            raw_text=log_text,
            source_path=source_path,
            tool_name="glossaries",
            category="glossary",
            importance="medium",
            stats=stats,
        )

    def parse_file(self, log_path: str | Path, root_file: str | None = None) -> ParsedLog:
        """读取 glossaries 日志文件并委托 parse 方法解析。"""
        path = Path(log_path)
        if not path.exists():
            return ParsedLog(
                source_path=str(path),
                tool_name="glossaries",
                category="glossary",
                importance="medium",
                stats={
                    "main_entries": 0,
                    "acronym_entries": 0,
                    "symbol_entries": 0,
                    "warnings_count": 0,
                },
            )
        text = self._read_log_text(path)
        self._source_path_hint = str(path)
        try:
            result = self.parse(text, root_file or self.root_file)
            result.source_path = str(path)
            stats_copy = dict(result.stats)
            stats_copy["main_entries"] = self._main_entries
            stats_copy["acronym_entries"] = self._acronym_entries
            stats_copy["symbol_entries"] = self._symbol_entries
            stats_copy["warnings_count"] = self._warnings_count
            result.stats = stats_copy
        finally:
            with suppress(AttributeError):
                delattr(self, "_source_path_hint")
        return result

    def _parse_makeindex(self, log_text: str) -> tuple[int, int]:
        file_ref = self.root_file
        entries_count = 0
        warnings = 0
        warning_entries_seen = 0
        for raw_line in log_text.split("\n"):
            line = raw_line.strip()

            # MiKTeX style error 是两行结构：标题行 + `-- 明细` 续行。
            if self._pending_style_error is not None:
                if line.startswith("--"):
                    detail = line[2:].strip()
                    if detail:
                        self._pending_style_error.text = f"{self._pending_style_error.text}：{detail}"
                    self._pending_style_error = None
                    continue
                self._pending_style_error = None

            m = entries_re.match(line)
            if m:
                entries_count = int(m.group(1))
                continue
            m = miktex_entries_re.search(line)
            if m:
                entries_count = int(m.group(1))
                continue
            m = warnings_issued_re.match(line)
            if m:
                warnings = int(m.group(1))
                continue
            m = miktex_style_error_re.match(line)
            if m:
                self._pending_style_error = LogEntry(
                    level=LogLevel.ERROR,
                    file=m.group(2) or "",
                    line=int(m.group(3)),
                    text=m.group(1).strip(),
                )
                self.build_log.append(self._pending_style_error)
                continue
            m = miktex_style_error_brief_re.match(line)
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
                warning_entries_seen += 1
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
                warning_entries_seen += 1
                continue
        return entries_count, max(warnings, warning_entries_seen)

    def _parse_xindy(self, log_text: str) -> tuple[int, int]:
        file_ref = self.root_file
        scan = scan_xindy(log_text)

        for text in scan.errors:
            self.build_log.append(LogEntry(level=LogLevel.ERROR, file=file_ref, line=1, text=text))
        for text in scan.warnings:
            self.build_log.append(LogEntry(level=LogLevel.WARNING, file=file_ref, line=1, text=text))
        for module in scan.modules:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.INFO,
                    file=file_ref,
                    line=1,
                    text=f"Loading module {module}",
                )
            )
        for count in scan.letter_groups:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.INFO,
                    file=file_ref,
                    line=1,
                    text=f"Added {count} letter groups",
                )
            )
        for _ in scan.markup_rule_counts:
            self.build_log.append(
                LogEntry(
                    level=LogLevel.INFO,
                    file=file_ref,
                    line=1,
                    text="Markup rules processed",
                )
            )
        return scan.total_entries, len(scan.warnings)
