"""Task 4 便捷 API 与统计聚合测试（TR-4.1 ~ TR-4.4）。"""
from pathlib import Path

from pytexlogs import (
    LogEntry,
    LogLevel,
    ToolResult,
    aggregate_stats,
    filter_severity,
    parse_log_file,
    parse_log_text,
)

_FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_parse_log_file():
    """TR-4.1：parse_log_file 返回 ParsedLog，source_path 与 errors 均合规。"""
    log_path = _FIXTURE_DIR / "sample.log"
    parsed = parse_log_file(str(log_path))
    assert parsed.source_path.endswith("sample.log")
    assert len(parsed.errors) >= 1


def test_parse_log_text():
    """TR-4.2：parse_log_text 对 Undefined control sequence 产生 1+ ERROR。"""
    text = "main.tex:42: Undefined control sequence \\foo"
    parsed = parse_log_text(text)
    assert len(parsed.errors) >= 1


def test_filter_severity():
    """TR-4.3：filter_severity([INFO, WARNING, ERROR], min_level=WARNING) 长度 = 2。"""
    e_info = LogEntry(level=LogLevel.INFO, file="a.tex", line=1, text="info")
    e_warn = LogEntry(level=LogLevel.WARNING, file="a.tex", line=2, text="warn")
    e_err = LogEntry(level=LogLevel.ERROR, file="a.tex", line=3, text="err")
    filtered = filter_severity([e_info, e_warn, e_err], min_level=LogLevel.WARNING)
    assert len(filtered) == 2
    assert LogLevel.INFO not in [e.level for e in filtered]


def test_aggregate_stats():
    """TR-4.4：aggregate_stats group_by=parser/level/category 均返回正确键值对。"""
    r1 = ToolResult(
        tool_name="pdflatex",
        category="compile",
        entries=[
            LogEntry(level=LogLevel.ERROR, file="a.tex", line=1, text="e1"),
            LogEntry(level=LogLevel.ERROR, file="a.tex", line=2, text="e2"),
            LogEntry(level=LogLevel.ERROR, file="a.tex", line=3, text="e3"),
        ],
    )
    r2 = ToolResult(
        tool_name="bibtex",
        category="bibliography",
        entries=[
            LogEntry(level=LogLevel.WARNING, file="a.bib", line=10, text="w1"),
            LogEntry(level=LogLevel.WARNING, file="a.bib", line=20, text="w2"),
        ],
    )
    results = [r1, r2]
    assert aggregate_stats(results, group_by="parser") == {"pdflatex": 3, "bibtex": 2}
    assert aggregate_stats(results, group_by="level") == {"error": 3, "warning": 2}
    assert aggregate_stats(results, group_by="category") == {"compile": 3, "bibliography": 2}
