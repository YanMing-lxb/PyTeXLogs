"""第 4 轮导出层回归（任务 16–18）。

- 16. ``to_json`` 支持异构 list（``ToolResultReport`` + ``ToolResult`` 混合），
  逐项分派；``stats`` 为 dict 或 ``ToolResultStats`` 都不得 ``AttributeError``；
- 17. ``to_json([ParsedLog])`` 输出结构化 dict，不得退化成 repr 字符串；
- 18. ``report_schema`` 取 ``REPORT_SCHEMA_VERSION`` 常量，不硬编码 ``1``。
"""

import json

from pytexlogs import (
    LogEntry,
    LogLevel,
    ToolResult,
    ToolResultReport,
    ToolResultStats,
    run_pipeline,
    to_json,
)
from pytexlogs.core.models import REPORT_SCHEMA_VERSION, ReportEntry
from pytexlogs.parsers.latex import LatexLogParser

_SAMPLE_LOG = "! Undefined control sequence.\nl.5 \\foobar\n"


def _mixed_results() -> list[object]:
    report_model = ToolResultReport(
        tool_name="bibtex",
        category="bibliography",
        importance="medium",
        source_path="main.blg",
        entries=[
            ReportEntry(level="warning", file="refs.bib", line=10, text="w1"),
        ],
        stats={"entries_count": 1, "warning": 1},
    )
    runtime_model = ToolResult(
        tool_name="pdflatex",
        category="compile",
        source_path="main.log",
        entries=[
            LogEntry(level=LogLevel.ERROR, file="main.tex", line=5, text="e1"),
        ],
        stats=ToolResultStats(entries_count=1, stats={"error": 1}),
    )
    return [report_model, runtime_model]


def test_mixed_list_json_dispatches_per_item() -> None:
    """任务 16：报告模型 + 运行时模型混合列表逐项序列化，不抛 AttributeError。"""
    raw = to_json(_mixed_results(), include_hints=False)
    data = json.loads(raw)

    results = data["results"]
    assert len(results) == 2

    report_item, tool_item = results
    # 报告模型：stats 为 dict 形状。
    assert report_item["tool_name"] == "bibtex"
    assert report_item["category"] == "bibliography"
    assert isinstance(report_item["stats"], dict)
    assert report_item["entries"][0]["text"] == "w1"

    # 运行时模型：ToolResultStats 也能结构化成 dict。
    assert tool_item["tool_name"] == "pdflatex"
    assert tool_item["category"] == "compile"
    assert tool_item["entries"][0]["text"] == "e1"
    # stats 不能是对象 repr 字符串。
    assert isinstance(tool_item["stats"], dict)


def test_json_parsed_log_list_is_structured() -> None:
    """任务 17：``[ParsedLog]`` 导出结构化字段，不输出 repr 字符串。"""
    parsed = LatexLogParser(root_file="main.tex").parse(_SAMPLE_LOG)
    raw = to_json([parsed], include_hints=False)
    data = json.loads(raw)

    results = data["results"]
    assert len(results) == 1
    item = results[0]
    for key in ("tool_name", "category", "importance", "source_path", "stats", "entries"):
        assert key in item, f"缺少结构化字段 {key}"
    assert isinstance(item["entries"], list)
    assert item["entries"][0]["text"] == "Undefined control sequence."
    # 不得出现对象 repr（``<... object at 0x...>``）。
    assert "<" not in raw.split('"text"')[1][:40]


def test_to_json_single_log_entry_is_structured() -> None:
    """追加 A：单条 ``LogEntry`` 顶层入参必须结构化序列化，不得抛 TypeError / repr 兜底。"""
    entry = LogEntry(level=LogLevel.ERROR, file="main.tex", line=5, text="e1")

    raw = to_json(entry, include_hints=False)
    data = json.loads(raw)

    assert isinstance(data["results"], list)
    assert len(data["results"]) == 1
    item = data["results"][0]
    assert item["level"] == "error"
    assert item["file"] == "main.tex"
    assert item["line"] == 5
    assert item["text"] == "e1"
    # 不得出现对象 repr。
    assert "<" not in raw


def test_to_json_log_entry_list_still_works() -> None:
    """追加 A：``[LogEntry]`` 列表入参继续结构化输出。"""
    entries = [
        LogEntry(level=LogLevel.WARNING, file="a.tex", line=1, text="w1"),
        LogEntry(level=LogLevel.FONT, file="a.tex", line=2, text="f1"),
    ]
    raw = to_json(entries, include_hints=False)
    data = json.loads(raw)

    assert [e["text"] for e in data["results"]] == ["w1", "f1"]
    assert data["results"][1]["level"] == "font"


def test_report_schema_uses_constant() -> None:
    """任务 18：导出的 ``report_schema`` 与 ``REPORT_SCHEMA_VERSION`` 常量一致。"""
    report = run_pipeline(captured_outputs={"pdflatex": _SAMPLE_LOG})
    data = json.loads(to_json(report, include_hints=False))

    assert data["report_schema"] == REPORT_SCHEMA_VERSION
