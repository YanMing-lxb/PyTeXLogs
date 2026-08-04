"""pytexlogs.parsers Entry Point 测试桩：一个最小的 ChkTeX 伪 parser。"""

from pytexlogs.core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog


class ChktexParser(BaseLogParser):
    category = "lint"
    importance = "medium"

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        entries: list[LogEntry] = []
        for line_no, line in enumerate(log_text.splitlines(), start=1):
            if "ChkTeX" in line and line.startswith("Warning"):
                entries.append(
                    LogEntry(
                        level=LogLevel.WARNING,
                        file=root_file or "unknown.tex",
                        line=line_no,
                        text=line.strip(),
                    )
                )
        return ParsedLog(entries=entries, raw_text=log_text, category=self.category, importance=self.importance)  # type: ignore[call-arg]
