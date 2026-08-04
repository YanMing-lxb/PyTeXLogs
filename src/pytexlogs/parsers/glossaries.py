"""Glossaries 术语表 .glg 日志解析器实现。"""

import re
from pathlib import Path
from typing import Any

from ..core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog

entries_re = re.compile(r"^##\s+(\d+)\s+entries accepted,\s*(\d+)\s+rejected")
warnings_issued_re = re.compile(r"^##\s+(\d+)\s+warnings issued")
error_re = re.compile(r"^!!\s+(.+)")
warning_line_re = re.compile(r"^Warning\s+line\s+(\d+)\s*:\s*(.+)")
warning_dash_re = re.compile(r"^Warning\s*--(.+)$")

xindy_error_re = re.compile(r"^ERROR:\s*(.+)")
xindy_warning_re = re.compile(r"^WARNING:\s*(.+)")
xindy_loading_module_re = re.compile(r"Loading module\s+(.+)")
xindy_letter_groups_re = re.compile(r"Added\s+(\d+)\s+letter groups")
xindy_markup_rules_re = re.compile(r"Markup( \S+)?\s*.*?(\d+)\s+rules?")
xindy_total_entries_re = re.compile(r"Total entries:\s*(\d+)")


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
            try:
                delattr(self, "_source_path_hint")
            except AttributeError:
                pass
        return result

    def _parse_makeindex(self, log_text: str) -> tuple[int, int]:
        file_ref = self.root_file
        entries_count = 0
        warnings = 0
        warning_entries_seen = 0
        for line in log_text.split("\n"):
            m = entries_re.match(line)
            if m:
                entries_count = int(m.group(1))
                continue
            m = warnings_issued_re.match(line)
            if m:
                warnings = int(m.group(1))
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
        entries_count = 0
        warnings = 0
        for line in log_text.split("\n"):
            m = xindy_error_re.match(line)
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
            m = xindy_warning_re.match(line)
            if m:
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.WARNING,
                        file=file_ref,
                        line=1,
                        text=m.group(1).strip(),
                    )
                )
                warnings += 1
                continue
            m = xindy_loading_module_re.match(line)
            if m:
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.INFO,
                        file=file_ref,
                        line=1,
                        text=f"Loading module {m.group(1).strip()}",
                    )
                )
                continue
            m = xindy_letter_groups_re.search(line)
            if m:
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.INFO,
                        file=file_ref,
                        line=1,
                        text=f"Added {m.group(1)} letter groups",
                    )
                )
                continue
            m = xindy_markup_rules_re.search(line)
            if m:
                self.build_log.append(
                    LogEntry(
                        level=LogLevel.INFO,
                        file=file_ref,
                        line=1,
                        text="Markup rules processed",
                    )
                )
                continue
            m = xindy_total_entries_re.search(line)
            if m:
                entries_count = max(entries_count, int(m.group(1)))
                continue
            fallback = re.search(r"(\d+)\s+entries?", line)
            if fallback:
                entries_count = max(entries_count, int(fallback.group(1)))
                continue
        return entries_count, warnings