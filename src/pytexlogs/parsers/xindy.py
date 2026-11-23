"""Xindy 索引 .alg 日志解析器实现。"""

from contextlib import suppress
from pathlib import Path
from typing import Any

from ..core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog
from .xindy_patterns import scan_xindy


class XindyParser(BaseLogParser):
    """Xindy 索引解析器：解析 .alg 日志输出。"""

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析 Xindy .alg 输出文本并返回 ParsedLog。"""
        if root_file:
            self.root_file = root_file

        # 注册表里 xindy 的 category 恒为 index；.glg 的术语表语义由
        # makeglossaries/GlossariesParser 负责，解析器不按后缀改写类别。
        category = "index"

        scan = scan_xindy(log_text)

        stats: dict[str, Any] = {
            "letter_groups_added": scan.letter_groups[-1] if scan.letter_groups else 0,
            "modules_loaded": len(scan.modules),
            "markup_rules": sum(scan.markup_rule_counts),
            "total_entries": scan.total_entries,
        }
        entries: list[LogEntry] = []
        file_ref = self.root_file or ""

        for text in scan.errors:
            entries.append(LogEntry(level=LogLevel.ERROR, file=file_ref, line=1, text=text))
        for text in scan.warnings:
            entries.append(LogEntry(level=LogLevel.WARNING, file=file_ref, line=1, text=text))
        for module in scan.modules:
            entries.append(
                LogEntry(
                    level=LogLevel.INFO,
                    file=file_ref,
                    line=1,
                    text=f"Loading module {module}",
                )
            )

        return ParsedLog(
            entries=entries,
            raw_text=log_text,
            source_path=getattr(self, "_source_path_hint", ""),
            tool_name="xindy",
            category=category,
            importance="medium",
            stats=stats,
        )

    def parse_file(self, log_path: str | Path, root_file: str | None = None) -> ParsedLog:
        """读取 xindy 日志文件并委托 parse 方法解析。"""
        path = Path(log_path)
        if not path.exists():
            return ParsedLog(
                source_path=str(path),
                tool_name="xindy",
                category="index",
                importance="medium",
                stats={
                    "letter_groups_added": 0,
                    "modules_loaded": 0,
                    "markup_rules": 0,
                    "total_entries": 0,
                },
            )
        text = self._read_log_text(path)
        self._source_path_hint = str(path)
        try:
            result = self.parse(text, root_file or self.root_file)
            result.source_path = str(path)
        finally:
            with suppress(AttributeError):
                delattr(self, "_source_path_hint")
        return result
