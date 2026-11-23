"""Round 9 回归：.bcf 语义、CSV 注入、写盘失败原因、列表异常字段、展示入参。"""

import csv
import io
import json
from pathlib import Path

import pytest

from pytexlogs import (
    LogEntry,
    LogLevel,
    ParsedLog,
    ToolResult,
    ToolResultReport,
    ToolResultStats,
    parse_auxdir,
    parse_log_file,
    print_summary,
    run_pipeline,
    show_log_entries,
    to_csv,
    to_json,
)
from pytexlogs.core.registry import LogParserRegistry


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_bcf_is_not_generic_log_suffix_but_explicit_parse_works(
    tmp_path: Path,
) -> None:
    bcf = _write(
        tmp_path / "main.bcf",
        '<bcf:controlfile xmlns:bcf="http://biblatex.org/">'
        "<bcf:citekey>alpha</bcf:citekey>"
        "<bcf:citekey>alpha</bcf:citekey>"
        "<bcf:citekey>beta</bcf:citekey>"
        "</bcf:controlfile>",
    )
    registry = LogParserRegistry.get_default_registry()

    # .bcf 是 XML 控制文件，不再作为通用日志后缀参与后缀路由。
    assert ".bcf" not in registry.all_suffixes()
    assert registry.lookup_by_suffix(".bcf") == []

    parsed = parse_log_file(bcf)
    assert parsed.tool_name == "biber"
    assert parsed.entries == []
    assert parsed.stats["unique_citations"] == 2

    results = parse_auxdir("main", tmp_path)
    assert [r.tool_name for r in results] == ["biber"]
    assert results[0].stats.stats["unique_citations"] == 2


def test_csv_formula_cells_are_escaped() -> None:
    entry = LogEntry(
        level=LogLevel.ERROR,
        file="+file.tex",
        line=3,
        text='=HYPERLINK("https://example.invalid")',
    )

    rows = list(csv.reader(io.StringIO(to_csv([entry], include_hints=False))))

    assert rows[1][0] == "'+file.tex"
    assert rows[1][5].startswith("'=HYPERLINK")
    assert rows[1][5].endswith(")")  # 只加前缀，不丢失原文本


def test_run_pipeline_records_report_write_error(tmp_path: Path) -> None:
    blocked = _write(tmp_path / "blocked", "not a directory\n")

    report = run_pipeline(
        jobname="main",
        auxdir=tmp_path,
        steps=["pdflatex"],
        captured_outputs={"pdflatex": "! Undefined control sequence.\n"},
        write_report_file=True,
        report_path=blocked / "report.json",
        print_terminal=False,
    )

    assert "_report_path" not in report.custom_fields
    error = report.custom_fields["_report_write_error"]
    assert error.startswith("FileExistsError:")
    assert not (blocked / "report.json").exists()


def test_json_list_includes_parse_exception() -> None:
    result = ToolResultReport(
        tool_name="external",
        category="external",
        parse_exception={"type": "RuntimeError", "message": "parser boom"},
    )

    payload = json.loads(to_json([result]))

    assert payload["results"][0]["parse_exception"] == {
        "type": "RuntimeError",
        "message": "parser boom",
    }


def test_print_summary_plain_keeps_level_symbol() -> None:
    parsed = ParsedLog(
        entries=[LogEntry(level=LogLevel.ERROR, file="a.tex", line=1, text="boom")],
        tool_name="pdflatex",
        category="compile",
    )
    buf = io.StringIO()

    print_summary([parsed], use_logger=False, stream=buf)

    text = buf.getvalue()
    assert "[一般编译]" in text
    assert "[E]" in text


def test_reference_summary_plain_keeps_labels() -> None:
    buf = io.StringIO()

    print_summary(
        [],
        use_logger=False,
        ref_added_keys=["alpha"],
        ref_total=1,
        ref_key_counts={"alpha": 2},
        stream=buf,
    )

    text = buf.getvalue()
    assert "[+] [参考文献] 新增 1:" in text
    assert "(*) [参考文献] 引用 Top 5:" in text


def test_show_log_entries_accepts_tool_results_and_mixed_lists() -> None:
    parsed = ParsedLog(
        entries=[LogEntry(level=LogLevel.ERROR, file="a.tex", line=1, text="first")],
        tool_name="pdflatex",
        category="compile",
    )
    result = ToolResult(
        tool_name="biber",
        category="bibliography",
        entries=[LogEntry(level=LogLevel.WARNING, file="refs.bib", line=2, text="second")],
        stats=ToolResultStats(entries_count=1),
    )

    out = io.StringIO()
    with pytest.raises(TypeError):
        show_log_entries([object()], use_logger=False)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("sys.stdout", out)
        show_log_entries([parsed, result], use_logger=False)

    text = out.getvalue()
    assert "first" in text and "second" in text
    assert "一般编译" in text and "参考文献" in text
