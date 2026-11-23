"""2026-11-22 审计修复的定向回归测试。

覆盖：过滤统计重算、参考文献摘要长键、.blg 自动识别、asymptote/minted
发现、biber 实例缓存、ParsedLog JSON、日志配置、编辑器跳转与报告扁平化。
"""

from __future__ import annotations

import importlib
import io
import json
import logging
from pathlib import Path

import pytest

from pytexlogs import filter_by_level, parse_log_file, run_pipeline, to_json
from pytexlogs.cli.args import _apply_editor_template, _detect_editor, _flatten_entries
from pytexlogs.core.models import (
    LogEntry,
    LogLevel,
    ParsedLog,
    ParsedPipelineReport,
    ToolResult,
    ToolResultReport,
    ToolResultStats,
)
from pytexlogs.core.registry import LogParserRegistry
from pytexlogs.parsers.biber import BiberParser
from pytexlogs.parsers.bibtex import BibtexParser
from pytexlogs.parsers.latex import LatexLogParser

_FIXTURES = Path(__file__).parent / "fixtures"


def test_filter_recomputes_all_derivable_stats() -> None:
    entries = [
        LogEntry(LogLevel.ERROR, "a.tex", 1, "boom"),
        LogEntry(LogLevel.TYPESET, "a.tex", 2, "Overfull \\hbox"),
    ]
    result = ToolResult(
        tool_name="pdflatex",
        category="compile",
        entries=entries,
        stats=ToolResultStats(
            2,
            {"error": 1, "warning": 0, "typesetting": 1, "overfull_boxes": 1},
        ),
    )

    filtered = filter_by_level([result], LogLevel.ERROR)[0]

    assert len(filtered.entries) == 1
    assert filtered.stats.entries_count == 1
    assert filtered.stats.stats["typesetting"] == 0
    assert filtered.stats.stats["overfull_boxes"] == 0
    assert filtered.stats.stats["errors_count"] == 1


def test_filtered_json_stats_match_entries() -> None:
    entries = [
        LogEntry(LogLevel.ERROR, "a.tex", 1, "boom"),
        LogEntry(LogLevel.TYPESET, "a.tex", 2, "Overfull \\hbox"),
    ]
    result = ToolResult(
        tool_name="pdflatex",
        category="compile",
        entries=entries,
        stats=ToolResultStats(2, {"error": 1, "typesetting": 1, "overfull_boxes": 1}),
    )

    payload = json.loads(to_json([result], min_level=LogLevel.ERROR))
    stats = payload["results"][0]["stats"]

    assert stats["entries_count"] == 1
    assert stats["stats"]["typesetting"] == 0
    assert stats["stats"]["overfull_boxes"] == 0


def test_parsed_log_json_and_filter_support() -> None:
    entries = [
        LogEntry(LogLevel.ERROR, "a.tex", 1, "boom"),
        LogEntry(LogLevel.INFO, "a.tex", 2, "note"),
    ]
    parsed = ParsedLog(
        entries=entries,
        tool_name="pdflatex",
        category="compile",
        stats={"entries_count": 2, "error": 1, "info": 1},
    )

    payload = json.loads(to_json(parsed))
    assert payload["results"][0]["tool_name"] == "pdflatex"
    assert len(payload["results"][0]["entries"]) == 2

    filtered = filter_by_level(parsed, LogLevel.ERROR)
    assert [e.level.value for e in filtered.entries] == ["error"]
    assert filtered.stats["entries_count"] == 1
    assert filtered.stats["info"] == 0


def test_long_reference_keys_do_not_break_summary() -> None:
    out = io.StringIO()
    # 这些长度组合会让 markup/plain 两套换行算法产生不同行数；修复后必须稳定输出。
    from pytexlogs.display import print_summary

    print_summary(
        [ParsedLog()],
        use_logger=False,
        ref_added_keys=["k" * 21, "k" * 5, "k" * 41, "k" * 121],
        ref_total=4,
        stream=out,
    )

    assert out.getvalue()


def test_biber_blg_auto_detected_by_single_file_api() -> None:
    fixture = _FIXTURES / "real_miktex" / "biber_case_mismatch.blg"
    parsed = parse_log_file(fixture)

    assert parsed.tool_name == "biber"
    assert len(parsed.entries) == 2
    assert {e.level for e in parsed.entries} == {LogLevel.WARNING}


def test_asymptote_discovers_non_jobname_asy_file(tmp_path: Path) -> None:
    (tmp_path / "main.log").write_text("This is pdfTeX, Version 3.14\n", encoding="utf-8")
    (tmp_path / "plot.asy").write_text("draw((0,0)--(1,1));\n", encoding="utf-8")

    report = run_pipeline(
        jobname="main",
        auxdir=tmp_path,
        steps=["pdflatex", "asymptote"],
        print_terminal=False,
    )

    assert report.pipeline.skipped_steps == []
    assert any(tr.tool_name == "asymptote" and tr.source_path.endswith("plot.asy") for tr in report.tool_results)


def test_biber_parser_reuse_clears_resolved_paths(tmp_path: Path) -> None:
    (tmp_path / "A").mkdir()
    (tmp_path / "B").mkdir()
    (tmp_path / "refs.bib").write_text("@book{k,title={T}}", encoding="utf-8")
    log = "[0] BibTeX.pm:1> INFO - Found BibTeX data source 'refs.bib'\n"

    parser = BiberParser(root_file=str(tmp_path / "A" / "main.tex"))
    parser.parse(log, root_file=str(tmp_path / "A" / "main.tex"))
    first = parser._resolved_paths["refs.bib"]

    parser.parse(log, root_file=str(tmp_path / "B" / "other.tex"))
    second = parser._resolved_paths["refs.bib"]

    assert first != second
    assert "B" in Path(second).parts


def test_bibtex_bare_while_reading_file_has_nonempty_message() -> None:
    parsed = BibtexParser(root_file="refs.tex").parse("---while reading file refs.aux\n", root_file="refs.tex")

    assert parsed.entries
    assert parsed.entries[0].text
    assert "while reading file" in parsed.entries[0].text


def test_registry_metadata_matches_parser_metadata() -> None:
    registry = LogParserRegistry.get_instance()
    for step in ("asymptote", "minted", "nomencl", "pythontex"):
        spec = registry.lookup(step)
        assert spec is not None
        parsed = spec.parser_cls().parse("", root_file="")
        assert (spec.category, spec.importance) == (parsed.category, parsed.importance)


def test_latex_nag_and_biblatex_specialized_branches_reachable() -> None:
    parsed = LatexLogParser(root_file="main.tex").parse(
        "Package nag Warning: Don't use math mode.\n"
        "Package biblatex Warning: Please (re)run Biber on the file:\n"
        "(biblatex) main on input line 12\n"
    )

    assert "Package nag Warning: Don't use math mode." in parsed.entries[0].text
    assert "(biblatex) main on input line 12" in parsed.entries[1].text


def test_cli_logging_idempotent_and_reaches_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("pytexlogs.cli.main")
    root = logging.getLogger("pytexlogs")
    child = logging.getLogger("pytexlogs.cli")

    old_handlers = list(root.handlers)
    old_level = root.level
    try:
        root.handlers.clear()
        monkeypatch.delenv("PYTEXLOGS_DEBUG", raising=False)
        for _ in range(3):
            module._configure_logging()

        assert len(root.handlers) == 1
        assert len(child.handlers) == 0
        assert child.propagate is True
        assert logging.getLogger("pytexlogs.core.engine").getEffectiveLevel() == logging.WARNING

        monkeypatch.setenv("PYTEXLOGS_DEBUG", "1")
        module._configure_logging()
        assert logging.getLogger("pytexlogs.core.engine").getEffectiveLevel() == logging.DEBUG
    finally:
        root.handlers[:] = old_handlers
        root.setLevel(old_level)


def test_windows_vscode_cmd_keeps_goto() -> None:
    assert _detect_editor("code --wait") == ["code", "--wait"]
    args = _apply_editor_template(["C:/Applications/vscode/code.CMD", "--wait"], "a.tex", 12)
    assert args[-2:] == ["--goto", "a.tex:12"]


def test_flatten_entries_supports_pipeline_report() -> None:
    entry = LogEntry(LogLevel.ERROR, "a.tex", 1, "boom")
    report = ParsedPipelineReport(
        tool_results=[
            ToolResultReport(
                tool_name="pdflatex",
                category="compile",
                entries=[entry],
                stats={"entries_count": 1},
            )
        ]
    )

    entries, _ = _flatten_entries(report)
    assert entries[0][0].text == "boom"
    assert entries[0][1] == "compile"
    assert entries[0][2] == "pdflatex"


def test_demo_prints_single_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    from pytexlogs import integration_demo

    output = io.StringIO()
    monkeypatch.setattr("sys.stdout", output)
    integration_demo.run_demo()

    assert output.getvalue().count("错误汇总") == 1
    assert output.getvalue().count("警告汇总") == 1


def test_csv_can_skip_hint_computation() -> None:
    from pytexlogs import to_csv

    entry = LogEntry(LogLevel.ERROR, "a.tex", 1, "Undefined control sequence.")
    parsed = ParsedLog(entries=[entry], tool_name="pdflatex", category="compile")

    header, row = to_csv(parsed, include_hints=False).splitlines()
    assert header == "file,line,level,category,tool,text,hint,source_path"
    assert row.split(",")[6] == ""


def test_register_uses_parser_class_metadata() -> None:
    from pytexlogs.core.models import BaseLogParser

    class _LintParser(BaseLogParser):
        category = "lint"
        importance = "medium"

        def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
            return ParsedLog(tool_name="lint", category=self.category, importance=self.importance)

    registry = LogParserRegistry()
    registry.register("lint", _LintParser)

    spec = registry.lookup("lint")
    assert spec is not None
    assert (spec.category, spec.importance) == ("lint", "medium")


def test_xindy_parser_counts_basic_stats() -> None:
    from pytexlogs.parsers.xindy import XindyParser

    parsed = XindyParser(root_file="main.glg").parse(
        'Loading module "texindy"...\n'
        "Added 3 letter groups\n"
        "Markup rules: 12 rules\n"
        "Total entries: 7\n"
        "WARNING: unknown attribute\n"
    )

    assert parsed.category == "index"
    assert parsed.stats["modules_loaded"] == 1
    assert parsed.stats["letter_groups_added"] == 3
    assert parsed.stats["markup_rules"] == 12
    assert parsed.stats["total_entries"] == 7
    assert any(e.level == LogLevel.WARNING for e in parsed.entries)


def test_biber_unique_citations_reads_bcf(tmp_path: Path) -> None:
    """Biber 日志只给数量；unique_citations 必须从同目录 .bcf 去重。"""
    bcf = tmp_path / "main.bcf"
    bcf.write_text(
        '<bcf:controlfile xmlns:bcf="http://biblatex.ctan.org">'
        "<bcf:section>"
        '<bcf:citekey order="1">alpha</bcf:citekey>'
        '<bcf:citekey order="2">beta</bcf:citekey>'
        '<bcf:citekey order="3">alpha</bcf:citekey>'
        "</bcf:section>"
        "</bcf:controlfile>",
        encoding="utf-8",
    )
    blg = tmp_path / "main.blg"
    blg.write_text(
        "[164] Biber.pm:1002> INFO - Found 3 citekeys in bib section 0\n",
        encoding="utf-8",
    )

    parsed = BiberParser().parse_file(blg, root_file=str(tmp_path / "main.tex"))

    assert parsed.stats["total_citations"] == 3
    assert parsed.stats["unique_citations"] == 2


def test_external_and_custom_categories_are_not_folded() -> None:
    """第三方 category 不再折叠进 compile，摘要有独立分组。"""
    from pytexlogs.display.formatter import CATEGORY_LABEL, _group_by

    entry = LogEntry(LogLevel.WARNING, "x.log", 1, "third-party warning")
    parsed = ParsedLog(
        entries=[entry],
        tool_name="mychktex",
        category="custom",
        importance="low",
    )

    grouped = _group_by([parsed])

    assert grouped["warning"]["custom"] == [entry]
    assert "custom" in CATEGORY_LABEL
    assert "external" in CATEGORY_LABEL
