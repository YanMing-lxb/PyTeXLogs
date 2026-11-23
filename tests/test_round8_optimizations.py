"""Round 8 回归：默认步骤规划、解析丢条目、展示/报告/CLI 契约。"""

import contextlib
import io
import json
from pathlib import Path

import pytest

from pytexlogs import (
    LogEntry,
    LogLevel,
    ParsedLog,
    aggregate_stats,
    parse_log_file,
    print_summary,
    run_pipeline,
    show_log_entries,
    to_json,
    write_report,
)
from pytexlogs.core.logkind import plan_default_steps, sniff_bib_tool, sniff_index_tool
from pytexlogs.core.models import BaseLogParser, ReportEntry, ToolResultReport
from pytexlogs.core.reftracker import RefChangeTracker
from pytexlogs.parsers.bibtex import BibtexParser
from pytexlogs.parsers.latex import LatexLogParser


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_run_pipeline_infers_jobname_from_auxdir(tmp_path: Path) -> None:
    _write(tmp_path / "main.tex", "\\documentclass{article}\n")
    _write(tmp_path / "main.log", "! Undefined control sequence.\nl.5 \\badcmd\n")

    report = run_pipeline(
        auxdir=tmp_path,
        print_terminal=False,
        summary_max_entries=None,
    )

    assert any(tr.tool_name == "pdflatex" and tr.entries for tr in report.tool_results)


def test_captured_outputs_append_to_default_steps(tmp_path: Path) -> None:
    report = run_pipeline(
        auxdir=tmp_path,
        captured_outputs={
            "biber": (
                "INFO - Found BibTeX data source 'refs.bib'\nWARN - I didn't find a database entry for 'missing'\n"
            )
        },
        print_terminal=False,
        summary_max_entries=None,
    )

    assert any(tr.tool_name == "biber" and tr.entries for tr in report.tool_results)


def test_parse_auxdir_with_captured_outputs_and_no_steps(tmp_path: Path) -> None:
    from pytexlogs import parse_auxdir

    results = parse_auxdir(
        "main",
        tmp_path,
        captured_outputs={"biber": "INFO - Found BibTeX data source 'refs.bib'\n"},
    )

    assert any(r.tool_name == "biber" for r in results)


def test_folded_missing_character_flushes_before_generic_warning() -> None:
    parsed = LatexLogParser(root_file="main.tex").parse(
        "Missing character: There is no 中\nLaTeX Warning: Something happened on input line 7.\n"
    )

    assert len(parsed.entries) == 2
    assert parsed.entries[0].text.startswith("Missing character:")
    assert "Something happened" in parsed.entries[1].text
    assert parsed.entries[1].line == 7


def test_bare_aux_error_is_not_duplicated() -> None:
    parsed = BibtexParser(root_file="main.tex").parse("This is BibTeX, Version 0.99\n---while reading file main.aux\n")

    assert len(parsed.entries) == 1
    entry = parsed.entries[0]
    assert entry.text == "---while reading file main.aux"
    assert entry.file.endswith("main.tex")


def test_print_summary_stream_uses_plain_labels() -> None:
    parsed = ParsedLog(
        category="compile",
        entries=[LogEntry(level=LogLevel.ERROR, file="a.tex", line=1, text="boom")],
    )
    buf = io.StringIO()
    result = print_summary([parsed], use_logger=False, stream=buf)

    assert "[一般编译]" in buf.getvalue()
    assert buf.getvalue().splitlines() == result.splitlines()


def test_print_summary_fallback_keeps_plain_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pytexlogs.display import printer as printer_module

    parsed = ParsedLog(
        category="compile",
        entries=[LogEntry(level=LogLevel.ERROR, file="a.tex", line=1, text="boom")],
    )
    monkeypatch.setattr(printer_module, "_RICH_CONSOLE", printer_module._FallbackConsole())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_summary([parsed], use_logger=False, stream=None)

    assert "[一般编译]" in buf.getvalue()


def test_write_report_failure_returns_none(tmp_path: Path) -> None:
    parent = tmp_path / "not-a-directory"
    parent.write_text("x", encoding="utf-8")
    report = run_pipeline(print_terminal=False)

    assert write_report(report, parent / "report.json") is None


def test_xlg_routes_to_xindy(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "main.xlg",
        "ERROR: bad index\nWARNING: weak\nOutput written on main.ind (2 pages).\n",
    )

    parsed = parse_log_file(path)

    assert parsed.tool_name == "xindy"
    assert len(parsed.entries) == 2


def test_stale_bcf_does_not_override_bibtex_header(tmp_path: Path) -> None:
    _write(tmp_path / "main.blg", "This is BibTeX, Version 0.99d\n")
    _write(tmp_path / "main.bcf", "<bcf:controlfile/>")

    assert sniff_bib_tool(tmp_path / "main.blg") == "bibtex"
    steps = plan_default_steps("main", tmp_path)
    assert "bibtex" in steps and "biber" not in steps


def test_ref_tracker_aux_markers_beat_stale_bcf(tmp_path: Path) -> None:
    _write(tmp_path / "main.aux", "\\citation{x}\n\\bibdata{refs}\n")
    _write(tmp_path / "main.bcf", "<bcf:controlfile/>")

    assert RefChangeTracker(tmp_path, "main").detect_mode() == "bibtex"


def test_cli_no_hints_applies_to_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from pytexlogs.cli.main import main

    log = _write(tmp_path / "main.log", "! Undefined control sequence.\nl.5 \\badcmd\n")
    assert main(["export", str(log), "--format", "json", "--no-hints"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload.get("hints", []) == []


def test_external_and_custom_categories_translate() -> None:
    for category, label in (("external", "External Tools"), ("custom", "Custom Parsing")):
        parsed = ParsedLog(
            category=category,
            entries=[LogEntry(level=LogLevel.WARNING, file="a.tex", line=1, text="m")],
        )
        output = print_summary([parsed], use_logger=False, language="en")
        assert label in output
        assert "外部工具" not in output and "自定义解析" not in output


def test_show_log_entries_accepts_report_objects() -> None:
    report = ToolResultReport(
        tool_name="custom",
        category="external",
        entries=[ReportEntry(level="error", file="a.tex", line=1, text="boom")],
    )
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        show_log_entries([report], use_logger=False)

    assert "a.tex" in out.getvalue()
    assert "外部工具" in out.getvalue()


def test_json_serializes_enum_level_as_value() -> None:
    report = ToolResultReport(
        tool_name="custom",
        category="compile",
        entries=[ReportEntry(level=LogLevel.ERROR, file="a.tex", line=1, text="x")],  # type: ignore[arg-type]
    )

    payload = json.loads(to_json([report]))

    assert payload["results"][0]["entries"][0]["level"] == "error"


def test_aggregate_stats_rejects_unknown_group_by() -> None:
    with pytest.raises(ValueError):
        aggregate_stats([], group_by="bogus")  # type: ignore[arg-type]


def test_parse_file_rejects_none_result(tmp_path: Path) -> None:
    class NoneParser(BaseLogParser):
        tool_name = "none"
        category = "custom"
        importance = "low"

        def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
            return None  # type: ignore[return-value]

    path = _write(tmp_path / "main.log", "text\n")

    with pytest.raises(TypeError):
        NoneParser().parse_file(path)


def test_file_stack_ignores_stray_closing_parenthesis() -> None:
    parsed = LatexLogParser(root_file="main.tex").parse(
        "(./chapter.tex\nSome text with ) closing\nLaTeX Warning: Something on input line 7.\n"
    )

    assert len(parsed.entries) == 1
    assert parsed.entries[0].file == "chapter.tex"


def test_sniff_index_tool_ignores_stale_xdy_when_idx_exists(
    tmp_path: Path,
) -> None:
    ilg = _write(tmp_path / "main.ilg", "No recognizable tool header\n")

    _write(tmp_path / "main.xdy", ";; stale\n")
    assert sniff_index_tool(ilg) == "xindy"

    _write(tmp_path / "main.idx", "\\indexentry{x}{1}\n")
    assert sniff_index_tool(ilg) == "makeindex"
