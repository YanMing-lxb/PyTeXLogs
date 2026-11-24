"""0.6.3 摘要版式：可配置宽度、悬挂缩进与 CJK 宽度回归。"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from pytexlogs.cli.main import main
from pytexlogs.core.models import LogEntry, LogLevel, ParsedLog
from pytexlogs.display import print_summary
from pytexlogs.display.formatter import display_width, resolve_summary_width
from pytexlogs.display.printer import show_log_entries

_REAL_LOG = Path(__file__).parent / "fixtures" / "real_miktex" / "pdflatex_undefined_cite_ref.log"


def _parsed(*entries: LogEntry) -> list[ParsedLog]:
    return [ParsedLog(entries=list(entries), tool_name="latex", category="compile")]


def _summary(entries: list[LogEntry], **kwargs: object) -> str:
    defaults = {
        "use_logger": False,
        "stream": StringIO(),
        "width": 48,
        "show_hints": False,
    }
    defaults.update(kwargs)
    return print_summary(_parsed(*entries), **defaults)


def test_resolve_summary_width_clamps_to_minimum() -> None:
    assert resolve_summary_width(None) == 74
    assert resolve_summary_width(10) == 40
    assert resolve_summary_width(60) == 60


def test_long_entry_hanging_indent_and_width() -> None:
    entry = LogEntry(
        level=LogLevel.ERROR,
        file="main.tex",
        line=12,
        text=(
            "Undefined control sequence with a deliberately long message "
            "that must wrap onto several continuation lines without "
            "losing the alignment of the entry text."
        ),
    )
    summary = _summary([entry], width=48)
    lines = summary.splitlines()
    entry_index = next(i for i, line in enumerate(lines) if "--> " in line)
    text_start = display_width(lines[entry_index].split("--> ", 1)[0] + "--> ")
    continuation = lines[entry_index + 1]

    assert continuation.startswith(" " * text_start)
    assert continuation[text_start:].strip()
    assert all(display_width(line) <= 48 for line in lines)


def test_separators_keep_legacy_style() -> None:
    entry = LogEntry(
        level=LogLevel.WARNING,
        file="main.tex",
        line=15,
        text="LaTeX Warning: Reference `sec:intro' undefined.",
    )
    lines = _summary([entry], width=48).splitlines()

    assert any(line.startswith("=") and "警告汇总 · 1" in line and line.endswith("=") for line in lines)
    assert any(line.startswith("+-- [一般编译] · 1 -") for line in lines)
    assert not any(line.startswith("─") for line in lines)


def test_cjk_title_and_entry_wrap_by_display_width() -> None:
    entry = LogEntry(
        level=LogLevel.WARNING,
        file="main.tex",
        line=7,
        text="中文提示信息需要按终端显示列折行，而不是按字符个数计算，" * 2,
    )
    summary = _summary([entry], width=48)
    lines = summary.splitlines()
    title_line = next(line for line in lines if "警告汇总" in line)
    entry_index = next(i for i, line in enumerate(lines) if "--> " in line)
    text_start = display_width(lines[entry_index].split("--> ", 1)[0] + "--> ")

    assert display_width(title_line) == 48
    assert lines[entry_index + 1].startswith(" " * text_start)
    assert all(display_width(line) <= 48 for line in lines)
    assert not any(line.lstrip().startswith(tuple("，。；：、")) for line in lines)


def test_reference_total_and_top_cited_spacing() -> None:
    zh = print_summary(
        [],
        use_logger=False,
        stream=StringIO(),
        ref_total=12,
        ref_unchanged=8,
        width=48,
    )
    assert "[参考文献] 共 12 篇，未变动 8 篇" in zh
    assert "篇 ，" not in zh

    en = print_summary(
        [],
        use_logger=False,
        stream=StringIO(),
        ref_total=12,
        ref_unchanged=8,
        ref_key_counts={"KeyA": 5, "KeyB": 3},
        language="en",
        width=48,
    )
    assert "Total 12, Unchanged 8" in en
    assert "12 ,Unchanged" not in en
    top_lines = [line for line in en.splitlines() if line.lstrip().startswith("(1)")]
    assert top_lines
    assert all(display_width(line) <= 48 for line in en.splitlines())


def test_hint_and_command_hanging_indent() -> None:
    entry = LogEntry(
        level=LogLevel.WARNING,
        file="main.tex",
        line=3,
        text="LaTeX Warning: Citation `Smith2020' undefined on input line 3.",
    )
    summary = _summary([entry], width=60, show_hints=True, hint_style="full", jobname="main")
    lines = summary.splitlines()
    hint_index = next(i for i, line in enumerate(lines) if "↳" in line)
    command_index = next(i for i, line in enumerate(lines) if "$ biber main" in line)

    assert lines[hint_index].startswith("        ↳ ")
    assert lines[hint_index + 1].startswith("          ")
    assert lines[command_index].startswith("          $ biber main")
    assert all(display_width(line) <= 60 for line in lines)


def test_brief_hint_is_one_line_without_commands() -> None:
    """默认 brief：只给一行说明，不把安装/排查命令塞进摘要。"""
    entry = LogEntry(
        level=LogLevel.WARNING,
        file="main.tex",
        line=3,
        text="LaTeX Warning: Citation `Smith2020' undefined on input line 3.",
    )
    summary = _summary([entry], width=60, show_hints=True, jobname="main")
    assert "先看 `.blg`" in summary
    assert "$ biber main" not in summary


def test_width_is_forwarded_by_show_log_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_print_summary(*args: object, **kwargs: object) -> str:
        captured.update(kwargs)
        return ""

    monkeypatch.setattr("pytexlogs.display.printer.print_summary", fake_print_summary)
    show_log_entries(
        LogEntry(level=LogLevel.ERROR, file="main.tex", line=1, text="boom"),
        use_logger=False,
        width=52,
    )
    assert captured["width"] == 52


def test_run_pipeline_forwards_summary_width(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_print_summary(*args: object, **kwargs: object) -> str:
        captured.update(kwargs)
        return ""

    monkeypatch.setattr("pytexlogs.core.engine.print_summary", fake_print_summary)
    log = tmp_path / "main.log"
    log.write_text(
        "This is pdfTeX\n! Undefined control sequence.\nl.7 \\badcommand\n",
        encoding="utf-8",
    )

    from pytexlogs.core.engine import run_pipeline

    run_pipeline(
        jobname="main",
        auxdir=tmp_path,
        steps=["pdflatex"],
        print_terminal=True,
        summary_width=52,
    )
    assert captured["width"] == 52


def test_cli_width_option(capsys: pytest.CaptureFixture[str]) -> None:
    assert _REAL_LOG.exists()
    code = main(
        [
            "check",
            str(_REAL_LOG),
            "--width",
            "48",
            "--severity",
            "all",
            "--no-hints",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert out.strip()
    assert all(display_width(line) <= 48 for line in out.splitlines())
