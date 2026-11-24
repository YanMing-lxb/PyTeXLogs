"""2026-11-24：brief 提示、非 ASCII bib 键、makeindex 降级、去重与页脚。"""

from io import StringIO

from pytexlogs import hint_for_text, print_summary
from pytexlogs.core.models import LogEntry, LogLevel, ParsedLog
from pytexlogs.parsers.makeindex import MakeindexParser

_BIB_WARNING = 'Warning--I didn\'t find a database entry for "AboulKhail.Erişen_2303"'


def test_bib_key_non_ascii_rule_has_brief():
    hint = hint_for_text(_BIB_WARNING, tool_name="bibtex")
    assert hint is not None
    assert hint.rule_id == "bib_key_non_ascii"
    assert "非 ASCII" in hint.brief
    assert hint.brief != hint.text


def test_ascii_missing_entry_falls_back_to_legacy_hint():
    ascii_warning = 'Warning--I didn\'t find a database entry for "Smith2020"'
    hint = hint_for_text(ascii_warning, tool_name="bibtex")
    assert hint is None or hint.rule_id != "bib_key_non_ascii"


def test_makeindex_unknown_specifier_is_warning() -> None:
    text = (
        "** Input style error (file = nomencl.ist, line = 41):\n"
        "   -- Unknown specifier lethead_prefix\n"
        "done (101 lines written, 0 warnings)\n"
    )
    log = MakeindexParser(root_file="main.tex").parse(text)
    style_entries = [e for e in log.entries if "Input style error" in e.text]
    assert style_entries
    assert all(e.level is LogLevel.WARNING for e in style_entries)


def test_other_makeindex_style_error_stays_error() -> None:
    text = "** Input style error (file = nomencl.ist, line = 7):\n   -- Bad sort key\n"
    log = MakeindexParser(root_file="main.tex").parse(text)
    style_entries = [e for e in log.entries if "Input style error" in e.text]
    assert style_entries
    assert all(e.level is LogLevel.ERROR for e in style_entries)


def _summary(entries: list[LogEntry]) -> str:
    return print_summary(
        [ParsedLog(entries=entries, tool_name="latex")],
        use_logger=False,
        show_hints=True,
        stream=StringIO(),
        width=70,
        jobname="main",
    )


def test_footer_without_errors_does_not_ask_to_fix_errors() -> None:
    entry = LogEntry(level=LogLevel.WARNING, file="main.tex", line=3, text="LaTeX Warning: Citation `X' undefined")
    summary = _summary([entry])
    assert "先修上面的 ERROR" not in summary
    assert "按 file:line 核对上面的警告" in summary


def test_duplicate_hints_are_printed_once() -> None:
    entry = LogEntry(
        level=LogLevel.WARNING,
        file="main.tex",
        line=3,
        text="LaTeX Warning: Citation `Smith2020' undefined on input line 3.",
    )
    duplicate = LogEntry(
        level=LogLevel.WARNING,
        file="main.log",
        line=3,
        text="LaTeX Warning: Citation `Smith2020' undefined on input line 3.",
    )
    summary = _summary([entry, duplicate])
    assert summary.count("引用键 `Smith2020` 未定义") == 1


def test_latin1_log_is_not_replaced_with_replacement_chars(tmp_path) -> None:
    """TeX 直接吐出的 8-bit 日志（Eri\\xb3en）不能被 U+FFFD 替换掉。"""
    from pytexlogs.utils.encoding import read_log_text

    log = tmp_path / "main.blg"
    log.write_bytes(b'Warning--I didn\'t find a database entry for "Eri\xb3en"')
    text = read_log_text(log)
    assert "Eri" in text
    assert "\ufffd" not in text
